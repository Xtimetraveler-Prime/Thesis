"""B1.3 host-only independent frame, route, fanout, epoch and overflow tests.

No downloaded dataset, trained checkpoint, physical DDR, FPGA access, firmware
changes or sealed MNIST TEST. Test vectors have analytically known spikes.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import struct
import zlib

import pytest

from loihi_twin_v2.compiler import (
    InputPopulationSpec, InputProjectionSpec, NetworkSpec, PopulationSpec,
    ProjectionConnection, ProjectionSpec,
)
from loihi_twin_v2.compartment import CompartmentConfig
from loihi_twin_v2.packet import SpikePacket
from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b13_streaming import (
    B13_HEADER_BYTES, B13StreamError, B13_INGRESS_MAGIC, B13_PACKETS_MAGIC,
    StreamingEpochGuard, decode_ingress_frame, decode_packet_frame,
    encode_ingress_frame, encode_packet_frame,
)
from loihi_twin_v2.p06_input_contract import pixel_spikes, INPUT_TICKS, TOTAL_TICKS


def fixture_result(*, hidden=3, compartments_per_core=2):
    hi = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
    out = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)
    network = NetworkSpec(
        populations=(PopulationSpec("h", hidden, hi),
                     PopulationSpec("z", 2, out)),
        input_populations=(InputPopulationSpec("pixels", 784),),
        input_projections=(InputProjectionSpec(
            "input", "pixels", "h",
            tuple(ProjectionConnection(pixel, neuron, 1)
                  for pixel in range(784) for neuron in range(hidden)),
        ),),
        projections=(ProjectionSpec(
            "hidden_out", "h", "z",
            tuple(ProjectionConnection(neuron, target, 2)
                  for neuron in range(hidden) for target in range(2)),
        ),),
    )
    return compile_synapse_aware(network, B12Options(
        readout_population="z", compartments_per_core=compartments_per_core,
    ))


def rechecksum(raw: bytes) -> bytes:
    """Independent little-endian B1.3 CRC repair for adversarial forgery."""
    work = bytearray(raw)
    # The 11th uint32 starts at byte 48; the 12th is header CRC at byte 52.
    struct.pack_into("<I", work, 48, zlib.crc32(work[128:]))
    struct.pack_into("<I", work, 52, 0)
    struct.pack_into("<I", work, 52, zlib.crc32(work[:128]))
    return bytes(work)


def _packets_from_trace(trace):
    return tuple(packet for core in trace.cores for packet in core.packets_out)


def test_wire_layout_independent_known_offsets_exact_route_counts_and_sha_binding():
    result = fixture_result()
    pixels = bytes([255] * 784)
    raw = encode_ingress_frame(result, pixels)
    # Independent on-wire decode: magic8, 14 LE uint32, two raw SHA256s, then <HHH routes/pixels.
    magic, *words = struct.unpack_from("<8s14I", raw)
    assert magic == B13_INGRESS_MAGIC
    assert len(raw) == 128 + 784 * 2 * 6 + 784
    assert words[:10] == [1, 128, 784 * 2 * 6 + 784, 784 * 2, 3, 784, 25, 26, 6, 784]
    assert raw[64:96] == bytes.fromhex(result.compiled.fingerprint)
    assert raw[96:128] == bytes.fromhex(result.capacity_audit["audit_sha256"])
    assert struct.unpack_from("<HHH", raw, 128) == (0, 0, 0)
    assert struct.unpack_from("<HHH", raw, 134) == (0, 1, 0)
    assert struct.unpack_from("<HHH", raw, 140) == (1, 0, 1)
    envelope = decode_ingress_frame(raw, result)
    assert envelope.image_sha256 == hashlib.sha256(pixels).hexdigest()
    assert len(envelope.routes) == 1568
    assert envelope.events(0) == result.compiled.external_packets(
        "pixels", range(784), target_timestep=0)
    assert len(envelope.events(25)) == 0


def test_ingress_requires_strict_784_channels_not_p07_one_core_and_rejects_unsupported_shapes():
    result = fixture_result()
    assert len({r.destination_core for r in result.compiled.ingress_routes}) == 2
    with pytest.raises(B13StreamError, match="784"):
        encode_ingress_frame(result, bytes([255] * 783))
    with pytest.raises(B13StreamError, match="784"):
        encode_ingress_frame(result, "not raw bytes")
    truncated = encode_ingress_frame(result, bytes([0] * 784))[:-1]
    with pytest.raises(B13StreamError, match="length"):
        decode_ingress_frame(truncated, result)
    # Track A P07's only-one-core format must not silently accept our 2-core fanout.
    assert len(encode_ingress_frame(result, bytes(784))) > 128 + (784 * 2 + 784)


def test_ingress_crc_sha_magic_reserved_flags_and_route_substitution_fail_closed():
    result = fixture_result()
    raw = encode_ingress_frame(result, bytes([255] * 784))
    variants = (
        (b"P07A1IN1" + raw[8:], "magic"),
        (raw[:-1] + bytes([raw[-1] ^ 1]), "payload CRC"),
        (raw[:65] + bytes([raw[65] ^ 1]) + raw[66:], "SHA256"),
        (raw[:12] + bytes([raw[12] ^ 1]) + raw[13:], "header"),
        (rechecksum(raw[:128] + bytes([raw[128] ^ 1]) + raw[129:]), "routes differ"),
    )
    for mutated, pattern in variants:
        with pytest.raises(B13StreamError, match=pattern):
            decode_ingress_frame(mutated, result)
    corrupted_flags = bytearray(raw)
    struct.pack_into("<I", corrupted_flags, 56, 1)
    with pytest.raises(B13StreamError, match="reserved"):
        decode_ingress_frame(rechecksum(corrupted_flags), result)


def test_packet_frame_independent_le_decode_and_packet_origin_next_fanout():
    result = fixture_result()
    compiled = result.compiled
    chip = compiled.build_chip()
    ing = decode_ingress_frame(encode_ingress_frame(result, bytes([255] * 784)), result)
    trace = chip.step(ing.events(0))
    emitted = _packets_from_trace(trace)
    assert len(emitted) == 3
    raw = encode_packet_frame(result, emitted, emitted_timestep=0)
    magic, *values = struct.unpack_from("<8s14I", raw)
    assert magic == B13_PACKETS_MAGIC
    assert values[:8] == [1, 128, 3 * 12, 0, 3, 3, 12, 4096]
    assert len(raw) == 128 + 36
    decoded = decode_packet_frame(raw, result, emitted_timestep=0)
    assert decoded == tuple(sorted(emitted, key=lambda p: p.logical_key))
    assert all(p.target_timestep == 1 and p.source_timestep == 0 for p in decoded)
    # Manually decode first packet (target:uint32, 4 × uint16).
    first = struct.unpack_from("<IHHHH", raw, 128)
    assert first == (1, 0, 0, 2, 0)


def test_26_tick_all_255_two_hidden_cores_to_readout_numeric_schedule_parity():
    result = fixture_result()
    raw = encode_ingress_frame(result, bytes([255] * 784))
    snapshots = []
    for order, reversed_drain in (((0, 1, 2), False), ((2, 1, 0), True)):
        guard = StreamingEpochGuard(result, raw)
        chip = result.compiled.build_chip()
        assert guard.static_worst_case()["current_worst_per_core"] == [784, 784, 3]
        assert guard.static_worst_case()["all_255_over_25_ticks_external_events"] == 39200
        trace_snapshots = []
        for tick in range(TOTAL_TICKS):
            expected_pixels = range(784) if tick < INPUT_TICKS else ()
            assert pixel_spikes(bytes([255] * 784), tick) == tuple(expected_pixels)
            trace = chip.step(
                guard.ingress.events(tick), service_order=order,
                reverse_packet_drain=reversed_drain)
            outgoing = _packets_from_trace(trace)
            wire = encode_packet_frame(result, outgoing, emitted_timestep=tick)
            source_spikes = tuple((c.logical_core_id, neuron)
                                  for c in trace.cores for neuron in c.spikes_out)
            receipt = guard.step(wire, source_spikes=source_spikes)
            assert receipt.tick == tick
            assert receipt.current_bank == tick % 2
            assert receipt.current_events_by_core == (
                (784, 784, 0 if tick == 0 else 3) if tick < 25 else (0, 0, 3)
            )
            assert receipt.new_routed_next_packets == (3 if tick < 25 else 0)
            assert receipt.external_packets == (1568 if tick < 25 else 0)
            assert receipt.routed_current_packets == (0 if tick == 0 else 3)
            assert [len(core.spikes_out) for core in trace.cores] == [
                2 if tick < 25 else 0, 1 if tick < 25 else 0, 0 if tick == 0 else 2]
            assert tuple(sorted(outgoing, key=lambda p: p.logical_key)) == receipt.emitted_next_packets
            trace_snapshots.append((
                receipt.current_events_by_core,
                tuple(c.spikes_out for c in trace.cores),
                tuple((s.state.current, s.state.voltage, s.state.refractory_remaining)
                      for c in trace.cores for s in c.compartment_state_after),
            ))
        assert guard.current_tick == TOTAL_TICKS
        with pytest.raises(B13StreamError, match="already completed"):
            guard.step(encode_packet_frame(result, (), emitted_timestep=26))
        snapshots.append(tuple(trace_snapshots))
    assert snapshots[0] == snapshots[1]


def test_packet_partial_fanout_duplicate_wrong_route_and_wrong_epoch_rejected():
    result = fixture_result()
    first = result.compiled.build_chip().step(
        decode_ingress_frame(encode_ingress_frame(result, bytes([255] * 784)),
                             result).events(0))
    full = _packets_from_trace(first)
    assert len(full) == 3
    # The default fixture has exactly ONE packet per emitting hidden neuron:
    # a single destination axon expands into both readout compartments.
    # Dropping a whole one-packet origin is detectable ONLY with source-spike
    # provenance (tested separately), not with packet payload alone.
    for invalid, pattern in (
        (full + (full[0],), "fanout"),
        ((replace(full[0], destination_axon=25), *full[1:]), "route table"),
        ((replace(full[0], source_timestep=1), *full[1:]), "NEXT"),
        ((replace(full[0], target_timestep=0), *full[1:]), "NEXT"),
        ((replace(full[0], source_core=None), *full[1:]), "source core"),
    ):
        with pytest.raises(B13StreamError, match=pattern):
            encode_packet_frame(result, tuple(invalid), emitted_timestep=0)
    # A different topology really has 2 destination COREs per hidden source.
    # Dropping ONE of the two packet routes must now fail even without a trace.
    split = fixture_result(compartments_per_core=1)
    split_ingress = decode_ingress_frame(
        encode_ingress_frame(split, bytes([255] * 784)), split)
    split_trace = split.compiled.build_chip().step(split_ingress.events(0))
    split_emitted = _packets_from_trace(split_trace)
    assert len(split_emitted) == 6
    with pytest.raises(B13StreamError, match="fanout"):
        encode_packet_frame(split, split_emitted[:-1], emitted_timestep=0)

    original = encode_packet_frame(result, full, emitted_timestep=0)
    modified_tick = bytearray(original)
    struct.pack_into("<I", modified_tick, 128, 2)
    with pytest.raises(B13StreamError, match="NEXT"):
        decode_packet_frame(rechecksum(modified_tick), result, emitted_timestep=0)
    with pytest.raises(B13StreamError, match="epoch"):
        decode_packet_frame(original, result, emitted_timestep=1)


def test_declared_firing_source_prevents_total_packet_group_omission():
    result = fixture_result()
    initial = result.compiled.build_chip().step(
        decode_ingress_frame(encode_ingress_frame(result, bytes([255] * 784)),
                             result).events(0))
    full = _packets_from_trace(initial)
    first_origin = (full[0].source_core, full[0].source_compartment)
    omitted = tuple(p for p in full
                    if (p.source_core, p.source_compartment) != first_origin)
    # Omission of a *complete* origin is indistinguishable from silence unless
    # the source trace accompanies the packet frame.
    frame = encode_packet_frame(result, omitted, emitted_timestep=0)
    guard = StreamingEpochGuard(result, encode_ingress_frame(result, bytes([255] * 784)))
    with pytest.raises(B13StreamError, match="source spike provenance"):
        guard.step(frame, source_spikes=tuple(
            (core.logical_core_id, neuron)
            for core in initial.cores for neuron in core.spikes_out))
    assert guard.current_tick == 0
    assert guard._pending == ()
    with pytest.raises(B13StreamError, match="spurious"):
        guard.step(encode_packet_frame(result, full, emitted_timestep=0),
                   source_spikes=(first_origin,))
    assert guard.current_tick == 0


def test_packet_decoder_rejects_reordered_but_otherwise_valid_frame():
    """Keep the wire's canonical order check after semantic validation.

    Both packets are unchanged valid routes at the correct NEXT epoch;
    only their record order changes, with CRC32s recomputed. This
    distinguishes ordering enforcement from the semantic rejection in
    the mutated NEXT-tick and destination-axon regressions.
    """
    result = fixture_result()
    envelope = decode_ingress_frame(
        encode_ingress_frame(result, bytes([255] * 784)), result)
    trace = result.compiled.build_chip().step(envelope.events(0))
    canonical = encode_packet_frame(
        result, _packets_from_trace(trace), emitted_timestep=0)
    assert len(canonical) == B13_HEADER_BYTES + 3 * 12
    unsorted = bytearray(canonical)
    first = canonical[B13_HEADER_BYTES:B13_HEADER_BYTES + 12]
    second = canonical[B13_HEADER_BYTES + 12:B13_HEADER_BYTES + 24]
    unsorted[B13_HEADER_BYTES:B13_HEADER_BYTES + 12] = second
    unsorted[B13_HEADER_BYTES + 12:B13_HEADER_BYTES + 24] = first
    with pytest.raises(B13StreamError, match="noncanonical B1.3 packet frame order"):
        decode_packet_frame(rechecksum(bytes(unsorted)), result, emitted_timestep=0)


def test_packet_header_crc_payload_crc_and_unknown_destination_are_rejected():
    result = fixture_result()
    full = _packets_from_trace(result.compiled.build_chip().step(
        decode_ingress_frame(encode_ingress_frame(result, bytes([255] * 784)),
                             result).events(0)))
    raw = encode_packet_frame(result, full, emitted_timestep=0)
    with pytest.raises(B13StreamError, match="payload CRC"):
        decode_packet_frame(raw[:-1] + bytes([raw[-1] ^ 0x01]),
                            result, emitted_timestep=0)
    corrupt = bytearray(raw)
    corrupt[8] ^= 0x04
    with pytest.raises(B13StreamError, match="version"):
        decode_packet_frame(bytes(corrupt), result, emitted_timestep=0)
    forged = bytearray(raw)
    struct.pack_into("<H", forged, 128 + 10, 100)
    with pytest.raises(B13StreamError, match="route table"):
        decode_packet_frame(rechecksum(forged), result, emitted_timestep=0)


def test_epoch_guard_rejects_overflow_without_advancing_or_dropping_queued_packets():
    result = fixture_result()
    guard = StreamingEpochGuard(result, encode_ingress_frame(result, bytes([255] * 784)))
    empty_frame = encode_packet_frame(result, (), emitted_timestep=0)
    # Adversarial B1.3 NEXT staging from a hypothetical upstream transport;
    # not claimed reachable from this small fixture's valid route graph.
    one = SpikePacket(target_timestep=0, destination_core=0, destination_axon=0)
    guard._pending = tuple(one for _ in range(3313))
    prior = guard._pending
    with pytest.raises(B13StreamError, match="CURRENT event bank overflow"):
        guard.step(empty_frame)
    assert guard.current_tick == 0
    assert guard._pending == prior
    guard._pending = tuple(one for _ in range(3312))
    receipt = guard.step(empty_frame)
    assert receipt.current_events_by_core[0] == 4096
    assert guard.current_tick == 1
    assert guard._pending == ()


def test_final_drain_epoch_rejects_lossy_next_packet_and_stays_transactional():
    result = fixture_result()
    guard = StreamingEpochGuard(result, encode_ingress_frame(result, bytes([255] * 784)))
    for tick in range(25):
        guard.step(encode_packet_frame(result, (), emitted_timestep=tick))
    assert guard.current_tick == 25
    legal_outbound = result.compiled.build_chip().step(guard.ingress.events(0))
    # Move a known VALID route fanout to a hypothetical tick-25 source spike.
    # The wire record must encode, but the final drain guard must reject it.
    source_packets = tuple(replace(p, source_timestep=25, target_timestep=26)
                           for p in _packets_from_trace(legal_outbound))
    frame = encode_packet_frame(result, source_packets, emitted_timestep=25)
    with pytest.raises(B13StreamError, match="final drain"):
        guard.step(frame)
    assert guard.current_tick == 25
    assert guard._pending == ()


@pytest.mark.skipif(
    __import__("os").environ.get("P06_B13_FULL_SYNTHETIC") != "1",
    reason="optional full 27-core × 784 fanout B1.3 mapping/ABI audit",
)
def test_full_27_core_1000_hidden_multicast_abi_exact_counts():
    from test_p06_b12_partition import synthetic_dense
    result = compile_synapse_aware(synthetic_dense(1000), B12Options(readout_population="z"))
    assert result.capacity_audit["logical_core_count"] == 27
    ingress_raw = encode_ingress_frame(result, bytes([255] * 784))
    assert len(ingress_raw) == 128 + (26 * 784 * 6) + 784
    guard = StreamingEpochGuard(result, ingress_raw)
    summary = guard.static_worst_case()
    assert summary["ingress_routes"] == 20384
    assert summary["all_255_input_tick_external_events"] == 20384
    assert summary["all_255_over_25_ticks_external_events"] == 509600
    assert summary["external_per_core"] == [784] * 26 + [0]
    assert summary["prior_routed_per_core"] == [0] * 26 + [1000]
    assert summary["max_core_current_bank_events"] == 1000
    assert summary["max_core_emitted_packets"] == 39
    assert summary["p05_diagnostic_stream_compatible"] is False
    assert summary["physical_execution"] == "NOT_TESTED"
    # Verify all 26 fanout destinations receive each active pixel one time.
    assert len(guard.ingress.events(0)) == 20384
    assert len(guard.ingress.events(25)) == 0
