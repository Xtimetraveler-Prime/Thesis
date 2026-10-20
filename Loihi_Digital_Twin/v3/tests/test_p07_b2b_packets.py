"""P07-B.2b native C11 vs accepted Python B1.3 packet/epoch oracle.

All graphs are synthetic TRAIN-free; neither frozen B2 bytes nor MNIST TEST
are accessed, and nothing communicates with the KV260.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import struct
import subprocess
import zlib

import pytest

from loihi_twin_v2.packet import SpikePacket
from loihi_twin_v2.p06_b13_streaming import (
    StreamingEpochGuard, decode_ingress_frame, encode_ingress_frame,
    encode_packet_frame,
)
from test_p06_b13_streaming import fixture_result
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    import shutil
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "P07-B.2b requires host C11 compiler"
    binary = tmp_path_factory.mktemp("p07b2b_c11") / "p07_b2b_native"
    subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(ROOT / "software/p07/include"),
        str(ROOT / "software/p07/p07_b2_ingress.c"),
        str(ROOT / "software/p07/p07_b2_packet.c"),
        str(ROOT / "tests/native/p07_b2b_packet_harness.c"),
        "-o", str(binary),
    ], check=True, capture_output=True, text=True)
    return binary


def _routes_and_lengths(result):
    rows = sorted(
        (core.core_id, entry.source_compartment, route.destination_core, route.destination_axon)
        for core in result.compiled.logical_deployment.core_configs
        for entry in core.output_routes
        for route in entry.routes
    )
    counts = [len(core.compartments)
              for core in result.compiled.logical_deployment.core_configs]
    assert len(counts) == len({core.core_id for core in result.compiled.logical_deployment.core_configs})
    return rows, counts


def _real_scenario(result, pixels):
    ingress = encode_ingress_frame(result, pixels)
    envelope = decode_ingress_frame(ingress, result)
    guard = StreamingEpochGuard(result, ingress)
    chip = result.compiled.build_chip()
    stream, receipts = [], []
    for tick in range(26):
        trace = chip.step(envelope.events(tick))
        packets = tuple(packet for core in trace.cores for packet in core.packets_out)
        spikes = tuple((core.logical_core_id, comp)
                       for core in trace.cores for comp in core.spikes_out)
        wire = encode_packet_frame(result, packets, emitted_timestep=tick)
        receipts.append(guard.step(wire, source_spikes=spikes))
        stream.append((wire, spikes))
    assert guard.current_tick == 26
    return ingress, stream, receipts


def _bundle(entries):
    return b"".join(
        struct.pack("<II", len(frame), len(spikes)) +
        b"".join(struct.pack("<HH", *origin) for origin in spikes) + frame
        for frame, spikes in entries
    )


def _native_run(native, tmp_path, ingress, routes, compartments, compiled, audit, entries,
                *, inject=None):
    prefix = tmp_path / "wire"
    prefix.mkdir(exist_ok=True)
    paths = [prefix / item for item in
             ("ingress.bin", "ingress_map.bin", "trusted_routes.bin",
              "compartments.bin", "epochs.bin")]
    paths[0].write_bytes(ingress)
    map_count = struct.unpack_from("<I", ingress, 20)[0]
    paths[1].write_bytes(ingress[128:128 + map_count * 6])
    paths[2].write_bytes(b"".join(struct.pack("<HHHH", *row) for row in routes))
    paths[3].write_bytes(b"".join(struct.pack("<H", n) for n in compartments))
    paths[4].write_bytes(_bundle(entries))
    args = [str(native), *(str(path) for path in paths[:4]),
            compiled, audit, str(paths[4]), str(len(compartments))]
    if inject is not None:
        args.append(str(inject))
    proc = subprocess.run(args, capture_output=True, text=True)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert proc.stdout.splitlines()[-1].startswith("P07_B2B_NATIVE_PACKET_PASS=1")
    return proc.stdout.splitlines()


def _recrc(raw):
    mutable = bytearray(raw)
    struct.pack_into("<I", mutable, 48, zlib.crc32(mutable[128:]))
    struct.pack_into("<I", mutable, 52, 0)
    struct.pack_into("<I", mutable, 52, zlib.crc32(mutable[:128]))
    return bytes(mutable)


def _receipt_line(receipt, wire):
    checksum = zlib.crc32(b"".join(
        struct.pack("<III", receipt.current_events_by_core[core],
                    receipt.next_events_by_core[core],
                    receipt.emitted_packets_by_core[core])
        for core in range(len(receipt.current_events_by_core))
    ))
    pending = zlib.crc32(b"".join(
        struct.pack("<HH", p.destination_core, p.destination_axon)
        for p in receipt.emitted_next_packets
    ))
    return ("B2_STEP", str(receipt.tick), str(receipt.current_bank),
            str(receipt.external_packets), str(receipt.routed_current_packets),
            str(receipt.new_routed_next_packets),
            f"{zlib.crc32(wire[128:]):08x}", f"{checksum:08x}", f"{pending:08x}")


@pytest.mark.parametrize("pixels", [
    bytes([255] * 784), bytes(784),
    bytes((i * 13 + 17) % 256 for i in range(784)),
])
@pytest.mark.parametrize("split_readout", [False, True])
def test_compiled_b13_26tick_packet_and_bank_parity(native, tmp_path, pixels, split_readout):
    result = fixture_result(compartments_per_core=1 if split_readout else 2)
    ingress, entries, receipts = _real_scenario(result, pixels)
    routes, compartments = _routes_and_lengths(result)
    actual = _native_run(native, tmp_path, ingress, routes, compartments,
                         result.compiled.fingerprint,
                         result.capacity_audit["audit_sha256"], entries)
    assert [tuple(line.split()) for line in actual[:-1]] == [
        _receipt_line(receipt, entries[tick][0])
        for tick, receipt in enumerate(receipts)
    ]
    assert actual[-1] == "P07_B2B_NATIVE_PACKET_PASS=1 steps=26 rejected=0 records=26"


@pytest.fixture(scope="module")
def noisy_case():
    result = fixture_result(compartments_per_core=1)
    ingress, entries, receipts = _real_scenario(result, bytes([255] * 784))
    routes, compartments = _routes_and_lengths(result)
    return result, ingress, entries, receipts, routes, compartments


@pytest.mark.parametrize("fault,expected", [
    ("wrong_magic", -2), ("wrong_version", -2),
    ("bad_header_crc", -4), ("bad_payload_crc", -4),
    ("wrong_compiled_digest", -3), ("wrong_capacity_digest", -3),
    ("reserved_header", -2), ("wrong_epoch", -5), ("wrong_count", -5),
    ("wrong_target", -6), ("invented_axon", -6),
    ("reorder", -7), ("duplicate", -7), ("partial_fanout", -6),
    ("missing_source", -6), ("missing_provenance", -8),
    ("duplicate_provenance", -8),
])
def test_crc_repaired_semantic_fault_rejected_without_advancing(
    native, tmp_path, noisy_case, fault, expected
):
    result, ingress, entries, receipts, routes, compartments = noisy_case
    first, spikes = entries[0]
    assert len(spikes) >= 2 and struct.unpack_from("<I", first, 24)[0] >= 3
    frame = bytearray(first)
    wrong_spikes = spikes
    if fault == "wrong_magic":
        frame[:8] = b"P05Gxxxx"
    elif fault == "wrong_version":
        struct.pack_into("<I", frame, 8, 2)
    elif fault == "bad_header_crc":
        frame[52] ^= 1
    elif fault == "bad_payload_crc":
        frame[-1] ^= 1
    elif fault == "wrong_compiled_digest":
        frame[64] ^= 1
    elif fault == "wrong_capacity_digest":
        frame[96] ^= 1
    elif fault == "reserved_header":
        frame[56] = 1
    elif fault == "wrong_epoch":
        struct.pack_into("<I", frame, 20, 1)
    elif fault == "wrong_count":
        struct.pack_into("<I", frame, 24, 10000)
    elif fault == "wrong_target":
        struct.pack_into("<I", frame, 128, 2)
    elif fault == "invented_axon":
        struct.pack_into("<H", frame, 128 + 10, 4095)
    elif fault == "reorder":
        frame[128:140], frame[140:152] = frame[140:152], frame[128:140]
    elif fault == "duplicate":
        frame[140:152] = frame[128:140]
    elif fault == "partial_fanout":
        # One origin in split-readout B1.2 has routes to TWO readout cores.
        # Remove one packet while keeping the remaining frame well formed.
        target_origin = struct.unpack_from("<HH", frame, 128 + 4)
        for k in range(struct.unpack_from("<I", frame, 24)[0] - 1, -1, -1):
            offset = 128 + 12*k
            if struct.unpack_from("<HH", frame, offset + 4) == target_origin:
                del frame[offset:offset + 12]
                break
        struct.pack_into("<I", frame, 16, len(frame) - 128)
        struct.pack_into("<I", frame, 24, (len(frame) - 128) // 12)
    elif fault == "missing_source":
        # Remove every packet from a real emitting source; the separate
        # source-spike list still contains that source, exposing the loss.
        origin = struct.unpack_from("<HH", frame, 128 + 4)
        body = [frame[128 + 12*k:128 + 12*(k + 1)]
                for k in range(struct.unpack_from("<I", frame, 24)[0])]
        body = [pkt for pkt in body if struct.unpack_from("<HH", pkt, 4) != origin]
        frame = bytearray(frame[:128] + b"".join(body))
        struct.pack_into("<I", frame, 16, len(frame) - 128)
        struct.pack_into("<I", frame, 24, len(body))
    elif fault == "missing_provenance":
        wrong_spikes = spikes[1:]
    elif fault == "duplicate_provenance":
        wrong_spikes = spikes + spikes[:1]
    if fault not in ("bad_header_crc", "bad_payload_crc", "wrong_magic", "wrong_version",
                     "reserved_header"):
        frame = bytearray(_recrc(frame))
    actual = _native_run(native, tmp_path, ingress, routes, compartments,
                         result.compiled.fingerprint,
                         result.capacity_audit["audit_sha256"],
                         [(bytes(frame), wrong_spikes), *entries])
    assert actual[0] == f"B2_REJECT 0 {expected}"
    assert [tuple(line.split()) for line in actual[1:-1]] == [
        _receipt_line(receipt, entries[i][0]) for i, receipt in enumerate(receipts)
    ]
    assert actual[-1] == "P07_B2B_NATIVE_PACKET_PASS=1 steps=26 rejected=1 records=27"


def test_last_tick_valid_b13_packet_frame_rejected_atomically(native, tmp_path, noisy_case):
    result, ingress, entries, receipts, routes, compartments = noisy_case
    old, spike_sources = entries[0]
    forged = bytearray(old)
    struct.pack_into("<I", forged, 20, 25)
    for pos in range(128, len(forged), 12):
        struct.pack_into("<I", forged, pos, 26)
    forged = _recrc(forged)
    actual = _native_run(native, tmp_path, ingress, routes, compartments,
                         result.compiled.fingerprint,
                         result.capacity_audit["audit_sha256"],
                         [*entries[:25], (forged, spike_sources), entries[25]])
    assert actual[25] == "B2_REJECT 25 -11"
    assert actual[-1] == "P07_B2B_NATIVE_PACKET_PASS=1 steps=26 rejected=1 records=27"


@pytest.mark.parametrize("inject,rejected", [(3312, False), (3313, True)])
def test_4096_current_capacity_vs_4097_rejection_and_retry(
    native, tmp_path, noisy_case, inject, rejected
):
    result, ingress, entries, receipts, routes, compartments = noisy_case
    actual = _native_run(native, tmp_path, ingress, routes, compartments,
                         result.compiled.fingerprint,
                         result.capacity_audit["audit_sha256"],
                         ([entries[0]] if rejected else []) + entries, inject=inject)
    if rejected:
        assert actual[0] == "B2_REJECT 0 -9"
        assert [tuple(line.split()) for line in actual[1:-1]] == [
            _receipt_line(receipt, entries[i][0]) for i, receipt in enumerate(receipts)
        ]
    else:
        # 784 external events into core 0 plus 3,312 preexisting routed
        # events = exactly 4,096 CURRENT. Injection is a synthetic/unreachable
        # adversarial bank snapshot, NOT a real emitted packet frame.
        assert actual[0].startswith("B2_STEP 0 0 1568 3312 ")
    assert actual[-1] == (
        f"P07_B2B_NATIVE_PACKET_PASS=1 steps=26 rejected={int(rejected)} "
        f"records={27 if rejected else 26}"
    )


def _pack_frame(magic, values, comp, audit, payload):
    numbers = list(values)
    numbers[10] = zlib.crc32(payload)
    numbers[11] = 0
    header = bytearray(struct.pack("<8s14I", magic, *numbers)
                       + bytes.fromhex(comp) + bytes.fromhex(audit))
    struct.pack_into("<I", header, 52, zlib.crc32(header))
    return bytes(header) + payload


def test_synthetic_27_core_26tick_transport_fanout(native, tmp_path):
    # NOT a trained B2 deployment: synthetic transport profile only.
    image = bytes([255] * 784)
    input_routes = tuple((pixel, core, pixel) for pixel in range(784) for core in range(26))
    input_map = b"".join(struct.pack("<HHH", *r) for r in input_routes)
    comp = hashlib.sha256(b"b2b synthetic compiled" + input_map).hexdigest()
    audit = hashlib.sha256(b"b2b synthetic capacity" + input_map).hexdigest()
    ingress = _pack_frame(b"P06B13I1",
                          (1, 128, len(input_map)+784, len(input_routes), 27, 784,
                           25, 26, 6, 784, 0, 0, 0, 0),
                          comp, audit, input_map+image)
    routes = [(core, 0, 26, core) for core in range(26)]
    emitted = b"".join(struct.pack("<IHHHH", tick+1, core, 0, 26, core)
                       for core in range(26) for tick in ())  # filled below
    assert not emitted
    entries = []
    for tick in range(26):
        frame_packets = (b"".join(struct.pack("<IHHHH", tick+1, core, 0, 26, core)
                                  for core in range(26)) if tick < 25 else b"")
        frame = _pack_frame(b"P06B13R1",
                            (1, 128, len(frame_packets), tick, len(frame_packets)//12, 27,
                             12, 4096, 0, 0, 0, 0, 0, 0),
                            comp, audit, frame_packets)
        entries.append((frame, tuple((core, 0) for core in range(26)) if tick < 25 else ()))
    actual = _native_run(native, tmp_path, ingress, routes, [1]*26+[10],
                         comp, audit, entries)
    rows = [line.split() for line in actual[:-1]]
    assert len(rows) == 26
    for tick, row in enumerate(rows):
        assert row[:3] == ["B2_STEP", str(tick), str(tick % 2)]
        assert int(row[3]) == (20384 if tick < 25 else 0)
        assert int(row[4]) == (0 if tick == 0 else 26)
        assert int(row[5]) == (26 if tick < 25 else 0)
    assert actual[-1] == "P07_B2B_NATIVE_PACKET_PASS=1 steps=26 rejected=0 records=26"
