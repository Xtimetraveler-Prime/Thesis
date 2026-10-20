"""P07-B.3c1 P03 raw 64-bit packet → independently trusted B1.3 wire.

Uses real original B1.2 compiled synthetic fixtures and original Python B1.3
encode oracle; no B2 official TEST, real FPGA, frozen B2 assets, or A53 ELF.
"""
from __future__ import annotations

import ctypes as C
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess

import pytest
from loihi_twin_v2.p06_b13_streaming import (
    decode_ingress_frame, encode_ingress_frame, encode_packet_frame,
)
from test_p06_b13_streaming import fixture_result
from test_p07_b2b_transaction import PacketBinding, Route, U8, U16

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 98432
MAX_CORE = 27
MAX_WORDS = 8192


class CoreWords(C.Structure):
    _fields_ = [
        ("source_core", U8), ("slot", U8), ("packet_count", U16),
        ("words", C.POINTER(C.c_uint64)),
    ]


class Capture(C.Structure):
    _fields_ = [
        ("core_count", C.c_uint32), ("word_count", C.c_uint32),
        ("count", C.c_uint32 * MAX_CORE),
        ("words", C.c_uint64 * MAX_WORDS),
    ]


READER = C.CFUNCTYPE(C.c_int, C.c_void_p, U8, U16,
                     C.POINTER(C.c_uint64))


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "P07-B.3c requires native C11"
    output = tmp_path_factory.mktemp("p07_b3c1") / "libp07_b3c.so"
    subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-shared", "-fPIC",
        "-I", str(ROOT / "software/p07/include"),
        "-I", str(ROOT / "software/p03/include"),
        "-I", str(ROOT / "software/p05/include"),
        str(ROOT / "software/p07/p07_b3c_packet_bridge.c"),
        str(ROOT / "software/p07/p07_b2_packet.c"),
        str(ROOT / "software/p03/p03_hw_adapter.c"),
        "-o", str(output),
    ], check=True, capture_output=True, text=True)
    lib = C.CDLL(str(output))
    lib.p07_b3c_encode_frame.argtypes = [
        C.POINTER(CoreWords), C.c_size_t, C.c_uint32,
        C.POINTER(PacketBinding), C.c_void_p, C.c_size_t,
        C.c_void_p, C.c_size_t, C.c_void_p, C.c_size_t,
        C.POINTER(C.c_size_t),
    ]
    lib.p07_b3c_encode_frame.restype = C.c_int
    lib.p07_b3c_capture_core.argtypes = [
        C.POINTER(Capture), C.c_uint32, U8, C.c_uint32,
        C.POINTER(C.c_uint64), C.c_size_t, READER, C.c_void_p,
    ]
    lib.p07_b3c_capture_core.restype = C.c_int
    return lib


def _routes(result):
    return sorted(
        (core.core_id, desc.source_compartment,
         dst.destination_core, dst.destination_axon)
        for core in result.compiled.logical_deployment.core_configs
        for desc in core.output_routes for dst in desc.routes
    )


def _binding(result):
    config = result.compiled.logical_deployment.core_configs
    tuples = _routes(result)
    routes = (Route * max(1, len(tuples)))()
    for i, line in enumerate(tuples):
        routes[i] = Route(*line)
    compartments = (U16 * len(config))(*(
        len(core.compartments) for core in config
    ))
    bind = PacketBinding(
        len(config), len(tuples), routes, compartments,
        (U8 * 32).from_buffer_copy(bytes.fromhex(result.compiled.fingerprint)),
        (U8 * 32).from_buffer_copy(bytes.fromhex(
            result.capacity_audit["audit_sha256"])),
    )
    return bind, routes, compartments


def _p03_word(p):
    return (
        p.destination_core
        | (p.destination_axon << 7)
        | (p.source_compartment << 19)
        | (p.target_timestep << 29)
        | (1 << 61)
    )


def _vectors(core_count, packets):
    groups = [[] for _ in range(core_count)]
    for packet in packets:
        groups[packet.source_core].append(_p03_word(packet))
    # P03 packet readback need not be sorted in B1.3 wire order.
    owners = []
    batch = (CoreWords * core_count)()
    for core, group in enumerate(groups):
        group = group[::-1]
        words = (C.c_uint64 * max(1, len(group)))(*group)
        owners.append(words)
        batch[core] = CoreWords(
            core, core % 3, len(group),
            C.cast(words, C.POINTER(C.c_uint64)),
        )
    return batch, owners


def _call(lib, binding, batches, tick, spikes, *,
          scratch_cap=MAX_BYTES, frame_cap=MAX_BYTES, expected=0):
    scratch = C.create_string_buffer(scratch_cap)
    frame = C.create_string_buffer(b"Z" * frame_cap)
    written = C.c_size_t(0xBAD)
    rawspikes = (U16 * max(2, 2 * len(spikes)))()
    for j, (core, compartment) in enumerate(spikes):
        rawspikes[2 * j], rawspikes[2 * j + 1] = core, compartment
    old = frame.raw
    rc = lib.p07_b3c_encode_frame(
        batches, len(batches), tick, C.byref(binding),
        rawspikes if spikes else None, len(spikes),
        scratch, scratch_cap, frame, frame_cap, C.byref(written),
    )
    assert rc == expected, (rc, expected)
    if rc != 0:
        assert written.value == 0xBAD
        assert frame.raw == old, "incomplete rejected frame leaked"
        return None
    return frame.raw[:written.value]


@pytest.mark.parametrize("partition", [1, 2])
def test_genuine_compiled_b12_b13_packet_wire_byte_identical(native, partition):
    result = fixture_result(compartments_per_core=partition)
    binding, routes, compartments = _binding(result)
    raw = encode_ingress_frame(result, bytes([255]) * 784)
    envelope = decode_ingress_frame(raw, result)
    trace = result.compiled.build_chip().step(envelope.events(0))
    emitted = tuple(packet for core in trace.cores for packet in core.packets_out)
    spikes = tuple(sorted((core.logical_core_id, neuron)
                   for core in trace.cores for neuron in core.spikes_out))
    batches, owners = _vectors(binding.core_count, emitted)
    expected = encode_packet_frame(result, emitted, emitted_timestep=0)
    assert _call(native, binding, batches, 0, spikes) == expected
    assert _call(native, binding, _vectors(binding.core_count, ())[0],
                 25, ()) == encode_packet_frame(
                     result, (), emitted_timestep=25)


def test_rejected_p03_semantic_bitfields_and_partial_fanout(native):
    result = fixture_result(compartments_per_core=2)
    binding, routes, compartments = _binding(result)
    ingress = decode_ingress_frame(
        encode_ingress_frame(result, bytes([255]) * 784), result)
    trace = result.compiled.build_chip().step(ingress.events(0))
    packets = tuple(packet for core in trace.cores for packet in core.packets_out)
    spikes = tuple(sorted((core.logical_core_id, n)
                   for core in trace.cores for n in core.spikes_out))
    batches, owners = _vectors(binding.core_count, packets)
    assert _call(native, binding, batches, 0, spikes) is not None
    for mutant, code in (
        (lambda w: w & ~(1 << 61), -2),             # not spike
        (lambda w: w | (1 << 62), -2),              # reserved
        (lambda w: w + (1 << 29), -2),              # incorrect NEXT tick
        (lambda w: (w & ~0x7F) | 127, -2),          # invalid destination
        (lambda w: w ^ (1 << 7), -5),               # CRC-valid but wrong route axon
    ):
        modified = _vectors(binding.core_count, packets)[0]
        target = next(x for x in modified if x.packet_count)
        target.words[0] = mutant(target.words[0])
        _call(native, binding, modified, 0, spikes, expected=code)
    # Entire emitting source omitted. Only independent spike provenance can
    # detect it; the B1.3 transport itself is still a valid empty frame.
    empty, _ = _vectors(binding.core_count, ())
    _call(native, binding, empty, 0, spikes, expected=-5)
    # One routed packet omitted but the remainder still valid.
    if len(packets) > 1:
        partial, _ = _vectors(binding.core_count, packets[1:])
        _call(native, binding, partial, 0, spikes, expected=-5)
    # Wrong capacity supplied by the caller must fail without output writes.
    _call(native, binding, batches, 0, spikes, frame_cap=127, expected=-3)
    # Wrong provenance: one source silently removed, still a valid frame.
    if spikes:
        _call(native, binding, batches, 0, spikes[1:], expected=-5)


def test_capture_callbacks_do_not_publish_partial_readback(native):
    capture = Capture()
    workspace = (C.c_uint64 * 4096)()
    ctx = C.c_uint32(123)
    @READER
    def good(cookie, slot, index, out):
        assert slot == 1
        out[0] = (1 << 61) | (1 << 29) | index
        return 0
    @READER
    def fail_midway(cookie, slot, index, out):
        if index == 1:
            return -1
        out[0] = 0x1234
        return 0
    cookie = C.cast(C.byref(ctx), C.c_void_p)
    rc = native.p07_b3c_capture_core(
        C.byref(capture), 0, 1, 2, workspace, 4096, good, cookie)
    assert rc == 0
    assert capture.core_count == 1 and capture.word_count == 2
    assert tuple(capture.words[:2]) == (
        (1 << 61) | (1 << 29), (1 << 61) | (1 << 29) | 1)
    before = C.string_at(C.addressof(capture), C.sizeof(capture))
    rc = native.p07_b3c_capture_core(
        C.byref(capture), 1, 1, 2, workspace, 4096, fail_midway, cookie)
    assert rc == -4
    assert C.string_at(C.addressof(capture), C.sizeof(capture)) == before
    assert native.p07_b3c_capture_core(
        C.byref(capture), 1, 1, 4097, workspace, 4096, good, cookie) == -3
    assert C.string_at(C.addressof(capture), C.sizeof(capture)) == before
    assert native.p07_b3c_capture_core(
        C.byref(capture), 1, 1, 1, workspace, 4096, good, cookie) == 0
    assert capture.core_count == 2 and capture.word_count == 3
