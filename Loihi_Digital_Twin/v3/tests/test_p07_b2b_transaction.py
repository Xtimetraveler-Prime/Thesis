"""P07-B.2b source-independent C11 NEXT vector vs accepted Python B1.3.

Synthetic TRAIN-free networks only; no frozen B2 mutation, physical DDR,
board programming, or B2 official MNIST TEST.
"""
from __future__ import annotations

import ctypes as C
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import pytest
from test_p06_b13_streaming import fixture_result, rechecksum
from loihi_twin_v2.p06_b13_streaming import (
    StreamingEpochGuard, encode_ingress_frame, encode_packet_frame,
)
from loihi_twin_v2.p06_input_contract import TOTAL_TICKS

ROOT = Path(__file__).resolve().parents[1]
MAX_CORES = 126
MAX_PENDING = 8192
U8 = C.c_uint8
U16 = C.c_uint16
U32 = C.c_uint32


class Route(C.Structure):
    _fields_ = [("source_core", U16), ("source_compartment", U16),
                ("destination_core", U16), ("destination_axon", U16)]


class Event(C.Structure):
    _fields_ = [("core_id", U16), ("axon_id", U16)]


class IngressBinding(C.Structure):
    _fields_ = [("core_count", U32), ("route_count", U32),
                ("trusted_routes", C.c_void_p), ("trusted_routes_bytes", C.c_size_t),
                ("compiled_sha256", U8 * 32), ("capacity_sha256", U8 * 32)]


class IngressView(C.Structure):
    _fields_ = [("wire", C.c_void_p), ("wire_bytes", C.c_size_t),
                ("routes", C.c_void_p), ("pixels", C.c_void_p),
                ("route_count", U32), ("core_count", U32)]


class PacketBinding(C.Structure):
    _fields_ = [("core_count", U32), ("route_count", U32),
                ("routes", C.POINTER(Route)),
                ("compartments_per_core", C.POINTER(U16)),
                ("compiled_sha256", U8 * 32), ("capacity_sha256", U8 * 32)]


class Tx(C.Structure):
    _fields_ = [("ingress", C.POINTER(IngressView)),
                ("binding", C.POINTER(PacketBinding)),
                ("pending", C.POINTER(Event)), ("pending_capacity", C.c_size_t),
                ("tick", U32), ("pending_count", U32),
                ("pending_by_core", U32 * MAX_CORES)]


class Receipt(C.Structure):
    _fields_ = [("tick", U32), ("current_bank", U32), ("external_events", U32),
                ("routed_current", U32), ("routed_next", U32),
                ("current_by_core", U32 * MAX_CORES),
                ("next_by_core", U32 * MAX_CORES),
                ("emitted_by_core", U32 * MAX_CORES),
                ("packet_payload_crc32", U32), ("ordered_next_crc32", U32)]


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "C11 compiler required for the P07-B.2b gate"
    output = tmp_path_factory.mktemp("p07b2b_transaction") / "libp07b2b.so"
    subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-fPIC", "-shared",
        "-I", str(ROOT / "software/p07/include"),
        str(ROOT / "software/p07/p07_b2_ingress.c"),
        str(ROOT / "software/p07/p07_b2_packet.c"),
        str(ROOT / "software/p07/p07_b2b_transaction.c"),
        "-o", str(output),
    ], check=True, capture_output=True, text=True)
    lib = C.CDLL(str(output))
    lib.p07_b2_decode_ingress.argtypes = [
        C.c_void_p, C.c_size_t, C.POINTER(IngressBinding), C.POINTER(IngressView)]
    lib.p07_b2_decode_ingress.restype = C.c_int
    lib.p07_b2b_transaction_init.argtypes = [
        C.POINTER(Tx), C.POINTER(IngressView), C.POINTER(PacketBinding),
        C.POINTER(Event), C.c_size_t]
    lib.p07_b2b_transaction_init.restype = C.c_int
    lib.p07_b2b_transaction_step.argtypes = [
        C.POINTER(Tx), C.c_void_p, C.c_size_t, C.c_void_p,
        C.c_size_t, C.POINTER(Receipt)]
    lib.p07_b2b_transaction_step.restype = C.c_int
    return lib


def state_bytes(obj):
    return C.string_at(C.addressof(obj), C.sizeof(obj))


def packet_routes(result):
    return sorted(
        (core.core_id, entry.source_compartment,
         dst.destination_core, dst.destination_axon)
        for core in result.compiled.logical_deployment.core_configs
        for entry in core.output_routes for dst in entry.routes
    )


class Context:
    def __init__(self, native, result, pixels):
        raw = encode_ingress_frame(result, pixels)
        self.raw = C.create_string_buffer(raw)
        self.result = result
        expected_routes = sorted(
            (r.input_index, r.destination_core, r.destination_axon)
            for r in result.compiled.ingress_routes
        )
        trusted_map = b"".join(struct.pack("<HHH", *r) for r in expected_routes)
        self.map = C.create_string_buffer(trusted_map)
        fingerprint = bytes.fromhex(result.compiled.fingerprint)
        audit = bytes.fromhex(result.capacity_audit["audit_sha256"])
        core_count = len(result.compiled.logical_deployment.core_configs)
        self.ib = IngressBinding(core_count, len(expected_routes), C.addressof(self.map),
                                 len(trusted_map), (U8 * 32).from_buffer_copy(fingerprint),
                                 (U8 * 32).from_buffer_copy(audit))
        self.view = IngressView()
        assert native.p07_b2_decode_ingress(self.raw, len(raw),
                                            C.byref(self.ib), C.byref(self.view)) == 0
        bindings = packet_routes(result)
        self.routes = (Route * max(1, len(bindings)))()
        for i, binding in enumerate(bindings):
            self.routes[i] = Route(*binding)
        self.compartments = (U16 * core_count)(*(
            len(core.compartments)
            for core in result.compiled.logical_deployment.core_configs
        ))
        self.pb = PacketBinding(
            core_count, len(bindings), C.cast(self.routes, C.POINTER(Route)),
            self.compartments,
            (U8 * 32).from_buffer_copy(fingerprint),
            (U8 * 32).from_buffer_copy(audit))
        self.pending = (Event * MAX_PENDING)()
        self.tx = Tx()
        self.receipt = Receipt()
        self.native = native
        assert native.p07_b2b_transaction_init(
            C.byref(self.tx), C.byref(self.view), C.byref(self.pb),
            self.pending, MAX_PENDING) == 0

    def step(self, frame, source_spikes, *, expected=0):
        # Buffer lifetime extends through synchronous C call.
        wire = C.create_string_buffer(frame)
        origins = (U16 * (max(1, len(source_spikes)) * 2))()
        for i, (core, neuron) in enumerate(source_spikes):
            origins[2 * i] = core
            origins[2 * i + 1] = neuron
        before = (state_bytes(self.tx), state_bytes(self.receipt),
                  state_bytes(self.pending))
        status = self.native.p07_b2b_transaction_step(
            C.byref(self.tx), wire, len(frame),
            origins if source_spikes else None, len(source_spikes),
            C.byref(self.receipt))
        # The expected native status is explicit for BOTH successful and
        # rejected transactions. In particular, negative tests must not
        # accidentally be subjected to the default success-only assertion.
        assert status == expected, (
            f"native transaction status {status}, expected {expected}"
        )
        if status != 0:
            assert before == (state_bytes(self.tx), state_bytes(self.receipt),
                              state_bytes(self.pending)), "rejection mutated bank/state/receipt"
        return status

    def pending_tuples(self):
        return tuple((v.core_id, v.axon_id) for v in self.pending[:self.tx.pending_count])


def _canonical_next_crc(packets):
    return zlib.crc32(b"".join(struct.pack("<HH", p.destination_core,
                                          p.destination_axon) for p in packets))


@pytest.mark.parametrize("partition", [1, 2])
@pytest.mark.parametrize("pixels", [
    bytes(784), bytes([255]) * 784,
    bytes((i * 19 + 47) % 256 for i in range(784)),
])
def test_26_tick_real_b13_frame_vs_native_C_and_python_guard(native, partition, pixels):
    result = fixture_result(compartments_per_core=partition)
    ctx = Context(native, result, pixels)
    guard = StreamingEpochGuard(result, encode_ingress_frame(result, pixels))
    chip = result.compiled.build_chip()
    for tick in range(TOTAL_TICKS):
        trace = chip.step(guard.ingress.events(tick))
        emitted = tuple(p for core in trace.cores for p in core.packets_out)
        source_spikes = tuple(sorted((core.logical_core_id, neuron)
                             for core in trace.cores for neuron in core.spikes_out))
        frame = encode_packet_frame(result, emitted, emitted_timestep=tick)
        expected = guard.step(frame, source_spikes=source_spikes)
        assert ctx.step(frame, source_spikes) == 0
        r = ctx.receipt
        assert r.tick == expected.tick == tick
        assert r.current_bank == expected.current_bank == tick % 2
        assert r.external_events == expected.external_packets
        assert r.routed_current == expected.routed_current_packets
        assert r.routed_next == expected.new_routed_next_packets
        ncores = len(result.compiled.logical_deployment.core_configs)
        assert tuple(r.current_by_core[:ncores]) == expected.current_events_by_core
        assert tuple(r.next_by_core[:ncores]) == expected.next_events_by_core
        assert tuple(r.emitted_by_core[:ncores]) == expected.emitted_packets_by_core
        assert r.packet_payload_crc32 == zlib.crc32(frame[128:])
        assert r.ordered_next_crc32 == _canonical_next_crc(expected.emitted_next_packets)
        assert ctx.pending_tuples() == tuple(
            (p.destination_core, p.destination_axon)
            for p in expected.emitted_next_packets
        )
    assert ctx.tx.tick == guard.current_tick == 26
    with pytest.raises(Exception, match="already completed"):
        guard.step(encode_packet_frame(result, (), emitted_timestep=25))
    assert ctx.step(encode_packet_frame(result, (), emitted_timestep=25),
                    (), expected=-8) == -8


def test_corrupt_crc_sha_header_route_fanout_order_and_retry(native):
    result = fixture_result(compartments_per_core=1)
    pixels = bytes([255] * 784)
    ctx = Context(native, result, pixels)
    g = StreamingEpochGuard(result, encode_ingress_frame(result, pixels))
    trace = result.compiled.build_chip().step(g.ingress.events(0))
    full = tuple(p for core in trace.cores for p in core.packets_out)
    sources = tuple(sorted((core.logical_core_id, n)
                  for core in trace.cores for n in core.spikes_out))
    good = encode_packet_frame(result, full, emitted_timestep=0)
    # (malformed wire, exact expected C status). Checking exact error
    # families prevents a checksum/length failure from masquerading as
    # semantic source-fanout validation.
    variants = [
        (b"P05G0000" + good[8:], -2),  # P07_B2_HEADER
        (good[:-1] + bytes([good[-1] ^ 1]), -4),  # P07_B2_CRC
        (good[:64] + bytes([good[64] ^ 1]) + good[65:], -3),  # DIGEST
    ]
    invalid = bytearray(good)
    struct.pack_into("<I", invalid, 128, 2)  # wrong target epoch
    variants.append((rechecksum(bytes(invalid)), -9))
    invalid = bytearray(good)
    invalid[128 + 8] = 100  # invalid destination core
    variants.append((rechecksum(bytes(invalid)), -9))
    invalid = bytearray(good)
    invalid[128:140], invalid[140:152] = invalid[140:152], invalid[128:140]
    variants.append((rechecksum(bytes(invalid)), -9))
    # Drop one of two fanout destination cores for one origin, retaining CRC.
    dropped = bytearray(good[:128] + good[140:])
    # Repair the *dimensions* as well as CRCs, so this is a structurally
    # valid packet frame whose single missing route fails FANOUT validation.
    struct.pack_into("<I", dropped, 16, len(dropped) - 128)
    struct.pack_into("<I", dropped, 24, (len(dropped) - 128) // 12)
    variants.append((rechecksum(bytes(dropped)), -9))
    # Remove entire origin group; only independent PL spike provenance can
    # detect this omission. The empty frame itself is a valid wire frame.
    variants.append((encode_packet_frame(result, (), emitted_timestep=0), -9))
    for bad, expected_code in variants:
        assert ctx.step(bad, sources, expected=expected_code) == expected_code
        assert ctx.tx.tick == 0
    # Also reject duplicated declared emitting origin without any state change.
    assert ctx.step(good, sources + sources[:1], expected=-9) == -9
    # Correct packet for the same epoch succeeds after every failed attempt.
    assert ctx.step(good, sources) == 0
    assert ctx.tx.tick == 1


def test_current_4096_pass_4097_fail_and_retry(native):
    result = fixture_result(compartments_per_core=2)
    ctx = Context(native, result, bytes([255]) * 784)
    empty = encode_packet_frame(result, (), emitted_timestep=0)
    # In this fixture core 0 receives 784 external events. Hypothetical
    # staged 3312 prior routed packets yields exactly 4096 CURRENT events.
    ctx.tx.pending_count = 3313
    ctx.tx.pending_by_core[0] = 3313
    for i in range(3313):
        ctx.pending[i] = Event(0, 0)
    assert ctx.step(empty, (), expected=-7) == -7
    ctx.tx.pending_count = 3312
    ctx.tx.pending_by_core[0] = 3312
    assert ctx.step(empty, ()) == 0
    assert ctx.receipt.current_by_core[0] == 4096
    assert ctx.tx.tick == 1


def test_final_tick_rejection_does_not_discard_next(native):
    result = fixture_result(compartments_per_core=2)
    pixels = bytes([255]) * 784
    ctx = Context(native, result, pixels)
    empty_frames = [encode_packet_frame(result, (), emitted_timestep=i) for i in range(26)]
    for frame in empty_frames[:25]:
        assert ctx.step(frame, ()) == 0
    # An otherwise legal route emitted on the drain tick is forbidden.
    trace = result.compiled.build_chip().step(
        StreamingEpochGuard(result, encode_ingress_frame(result, pixels)).ingress.events(0))
    emitted = tuple(p for core in trace.cores for p in core.packets_out)
    shifted = tuple(type(p)(
        target_timestep=26, destination_core=p.destination_core,
        destination_axon=p.destination_axon, source_core=p.source_core,
        source_compartment=p.source_compartment, source_timestep=25,
    ) for p in emitted)
    last = encode_packet_frame(result, shifted, emitted_timestep=25)
    sources = tuple(sorted((c.logical_core_id, n)
                  for c in trace.cores for n in c.spikes_out))
    assert ctx.step(last, sources, expected=-10) == -10
    assert ctx.tx.tick == 25
    assert ctx.step(empty_frames[25], ()) == 0
    assert ctx.tx.tick == 26
