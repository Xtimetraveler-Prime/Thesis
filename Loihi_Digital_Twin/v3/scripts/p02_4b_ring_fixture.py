#!/usr/bin/env python3
"""Generate/verify the P02.4b five-over-three physical paging workload.

The workload is intentionally small enough for JTAG/VIO orchestration while
still exercising the semantics P02 must prove physically:

- five logical cores backed by K26 DDR;
- three resident physical context slots;
- one physical HLS engine;
- state persistence across eviction/reload;
- logical-destination packet routing independent of residency;
- CURRENT/NEXT event-bank alternation;
- global per-timestep barrier;
- mutable DDR writeback and later page-in.

The external host remains the control plane in P02.4b.  Complete non-resident
context images are authoritative in K26 DDR, not in PC RAM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalChip,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    P03_REQUIRED_ARITHMETIC,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
    export_paged_hardware_image,
)
from loihi_twin_v2.ddr_abi import (
    P02_DDR_BANK_LAYOUT,
    P02_DDR_CONTEXT_STRIDE_BYTES,
    build_initial_ddr_context_record,
    ddr_context_address,
)
from loihi_twin_v2.hardware_p03 import pack_compartment_state, pack_output_packet


BACKING_BASE = 0x40000000
LOGICAL_CORES = tuple(range(5))
RESIDENT_SLOTS = 3
TIMESTEPS = 7
SERVICE_ORDER = LOGICAL_CORES

BANKS = {bank.name: bank for bank in P02_DDR_BANK_LAYOUT}
STATIC_BANKS = ("config", "axon", "synapse", "route_descriptor", "route")
MUTABLE_BANKS = ("state", "event0", "event1", "trace", "packet")


def _hex(value: int, bits: int) -> str:
    return f"0x{value & ((1 << bits) - 1):0{(bits + 3) // 4}X}"


def _trace_word(before: int, synaptic_input: int, after: int, spike: bool) -> int:
    return (
        (before & ((1 << 64) - 1))
        | ((synaptic_input & ((1 << 64) - 1)) << 64)
        | ((after & ((1 << 64) - 1)) << 128)
        | ((1 if spike else 0) << 192)
    )


def _ring_core(core_id: int) -> LogicalCoreConfig:
    next_core = (core_id + 1) % len(LOGICAL_CORES)
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(
            CompartmentConfig(
                current_decay=4096,
                voltage_decay=0,
                threshold=5,
            ),
        ),
        input_axons=(InputAxonBinding(10 + core_id, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 3),)),),
        output_routes=(
            OutputRouteEntry(
                0,
                (OutputRoute(next_core, 10 + next_core),),
            ),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def make_workload() -> tuple[LogicalCoreConfig, ...]:
    return tuple(_ring_core(core_id) for core_id in LOGICAL_CORES)


def _write_word(record: bytearray, bank_name: str, index: int, value: int) -> None:
    bank = BANKS[bank_name]
    if not 0 <= index < bank.depth:
        raise ValueError(f"{bank_name} index {index} out of range")
    if not 0 <= value < (1 << (bank.word_bytes * 8)):
        raise ValueError(f"{bank_name}[{index}] does not fit bank width")
    start = bank.offset + index * bank.word_bytes
    record[start : start + bank.word_bytes] = value.to_bytes(bank.word_bytes, "little")


def _read_word(record: bytes, bank_name: str, index: int) -> int:
    bank = BANKS[bank_name]
    start = bank.offset + index * bank.word_bytes
    return int.from_bytes(record[start : start + bank.word_bytes], "little")


def _record_sha(record: bytes) -> str:
    return hashlib.sha256(record).hexdigest()


def generate(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    configs = make_workload()
    hardware = export_paged_hardware_image(configs, resident_context_count=RESIDENT_SLOTS)
    if hardware.logical_core_ids != LOGICAL_CORES:
        raise AssertionError("P02.4b logical core IDs drifted")
    if hardware.initial_resident_core_ids != (0, 1, 2):
        raise AssertionError("P02.4b initial residency drifted")

    backing = hardware.backing_by_logical_core

    initial_records: dict[int, bytes] = {}
    expected_records: dict[int, bytearray] = {}
    for core_id in LOGICAL_CORES:
        record = build_initial_ddr_context_record(backing[core_id])
        initial_records[core_id] = record
        expected_records[core_id] = bytearray(record)
        (output_dir / f"core{core_id}_initial.bin").write_bytes(record)

    # Raw mutable-bank model. Counts are control-plane metadata; raw words remain
    # in the double-buffered event banks after a bank is consumed.
    event_words = {
        core_id: {0: [0] * 4096, 1: [0] * 4096}
        for core_id in LOGICAL_CORES
    }
    event_counts = {
        core_id: {0: 0, 1: 0}
        for core_id in LOGICAL_CORES
    }
    packet_words = {core_id: [0] * 4096 for core_id in LOGICAL_CORES}
    trace_words = {core_id: [0] * 1024 for core_id in LOGICAL_CORES}

    chip = LogicalChip(configs)
    dispatch_rows: list[dict[str, object]] = []
    timestep_rows: list[dict[str, object]] = []
    trace_digest = hashlib.sha256()

    for timestep in range(TIMESTEPS):
        current_bank = timestep & 1
        next_bank = 1 - current_bank

        external = tuple(
            SpikePacket(
                target_timestep=timestep,
                destination_core=core_id,
                destination_axon=10 + core_id,
            )
            for core_id in LOGICAL_CORES
        )

        # Mirror the physical harness: prior routed events already occupy the
        # current bank, then one external event is appended for each core before
        # that core's dispatch.
        for packet in external:
            core_id = packet.destination_core
            addr = event_counts[core_id][current_bank]
            event_words[core_id][current_bank][addr] = packet.destination_axon
            event_counts[core_id][current_bank] += 1

        traces = chip.evaluate(
            external_packets=external,
            service_order=SERVICE_ORDER,
        )
        trace_by_core = {trace.logical_core_id: trace for trace in traces}

        routed_packets: list[dict[str, int]] = []
        for core_id in SERVICE_ORDER:
            trace = trace_by_core[core_id]
            expected_event_count = len(trace.packet_in)
            modeled_event_count = event_counts[core_id][current_bank]
            if modeled_event_count != expected_event_count:
                raise AssertionError(
                    f"event count mismatch t={timestep} core={core_id}: "
                    f"model={modeled_event_count} trace={expected_event_count}"
                )

            before = pack_compartment_state(trace.compartment_state_before[0].state)
            after = pack_compartment_state(trace.compartment_state_after[0].state)
            synaptic = sum(
                contribution.weight
                for contribution in trace.synaptic_contributions
                if contribution.target_compartment == 0
            )
            spike = 0 in set(trace.spikes_out)
            trace_word = _trace_word(before, synaptic, after, spike)
            trace_words[core_id][0] = trace_word

            packets = [pack_output_packet(packet) for packet in trace.packets_out]
            for index, word in enumerate(packets):
                packet_words[core_id][index] = word
            for packet in trace.packets_out:
                routed_packets.append(
                    {
                        "source_core": core_id,
                        "destination_core": packet.destination_core,
                        "destination_axon": packet.destination_axon,
                        "target_timestep": packet.target_timestep,
                        "word": pack_output_packet(packet),
                    }
                )

            dispatch_rows.append(
                {
                    "timestep": timestep,
                    "core_id": core_id,
                    "event_bank": current_bank,
                    "event_count": expected_event_count,
                    "state_after": after,
                    "trace_word": trace_word,
                    "spike_count": len(trace.spikes_out),
                    "packets": packets,
                }
            )

            # After dispatch, the current bank is logically consumed. Raw words
            # are intentionally left in place; only the count returns to zero.
            event_counts[core_id][current_bank] = 0

        chip.drain_packets()
        chip_trace = chip.advance()
        trace_digest.update(repr(chip_trace.normalized()).encode("utf-8"))
        trace_digest.update(b"\n")

        # Mirror host routing after every logical core has completed. Packets are
        # appended to destination NEXT banks by logical destination ID.
        for item in routed_packets:
            if item["target_timestep"] != timestep + 1:
                raise AssertionError("P02.4b packet target timestep drifted")
            dest = item["destination_core"]
            addr = event_counts[dest][next_bank]
            if addr >= 4096:
                raise AssertionError("P02.4b event bank overflow")
            event_words[dest][next_bank][addr] = item["destination_axon"]
            event_counts[dest][next_bank] += 1

        timestep_rows.append(
            {
                "timestep": timestep,
                "current_bank": current_bank,
                "next_bank": next_bank,
                "routed_packets": routed_packets,
                "next_event_counts": {
                    str(core_id): event_counts[core_id][next_bank]
                    for core_id in LOGICAL_CORES
                },
            }
        )

    final_states: dict[int, int] = {}
    final_packets: dict[int, list[int]] = {}
    final_traces: dict[int, int] = {}
    for core_id in LOGICAL_CORES:
        state_word = pack_compartment_state(chip.cores[core_id].states[0])
        final_states[core_id] = state_word
        final_packets[core_id] = packet_words[core_id][:]
        final_traces[core_id] = trace_words[core_id][0]

        record = expected_records[core_id]
        _write_word(record, "state", 0, state_word)
        for bank_index, bank_name in ((0, "event0"), (1, "event1")):
            for index, value in enumerate(event_words[core_id][bank_index]):
                if value:
                    _write_word(record, bank_name, index, value)
        _write_word(record, "trace", 0, trace_words[core_id][0])
        for index, value in enumerate(packet_words[core_id]):
            if value:
                _write_word(record, "packet", index, value)

        expected = bytes(record)
        (output_dir / f"core{core_id}_expected.bin").write_bytes(expected)

    # Tcl vectors keep the hardware driver simple and deterministic.
    lines = [
        "# Generated by scripts/p02_4b_ring_fixture.py. Do not edit.",
        f"set P02B_TIMESTEPS {TIMESTEPS}",
        "set P02B_SERVICE_ORDER {" + " ".join(map(str, SERVICE_ORDER)) + "}",
        "set P02B_INITIAL_RESIDENCY {0 1 2}",
        "array set P02B_RECORD_BASE {"
        + " ".join(
            f"{core_id} {_hex(ddr_context_address(BACKING_BASE, core_id), 64)}"
            for core_id in LOGICAL_CORES
        )
        + "}",
        "array set P02B_EXTERNAL_AXON {"
        + " ".join(f"{core_id} {10 + core_id}" for core_id in LOGICAL_CORES)
        + "}",
        "array set P02B_COMPARTMENT_COUNT {"
        + " ".join(
            f"{core_id} {backing[core_id].image.compartment_count}"
            for core_id in LOGICAL_CORES
        )
        + "}",
        "array set P02B_SYNAPSE_COUNT {"
        + " ".join(
            f"{core_id} {backing[core_id].image.synapse_count}"
            for core_id in LOGICAL_CORES
        )
        + "}",
        "array set P02B_ROUTE_COUNT {"
        + " ".join(
            f"{core_id} {backing[core_id].image.route_count}"
            for core_id in LOGICAL_CORES
        )
        + "}",
    ]

    lines.append("array set P02B_EXPECT_CONFIG0 {")
    for core_id in LOGICAL_CORES:
        lines.append(f"  {core_id} {_hex(backing[core_id].image.config_words[0], 128)}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_INITIAL_STATE0 {")
    for core_id in LOGICAL_CORES:
        lines.append(f"  {core_id} {_hex(backing[core_id].image.state_words[0], 64)}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_AXON_INDEX {")
    for core_id in LOGICAL_CORES:
        seeds = backing[core_id].image.axon_words
        if len(seeds) != 1:
            raise AssertionError("P02.4b ring expects exactly one sparse axon descriptor")
        lines.append(f"  {core_id} {seeds[0].index}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_AXON_WORD {")
    for core_id in LOGICAL_CORES:
        seeds = backing[core_id].image.axon_words
        lines.append(f"  {core_id} {_hex(seeds[0].word, 64)}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_SYNAPSE0 {")
    for core_id in LOGICAL_CORES:
        lines.append(f"  {core_id} {_hex(backing[core_id].image.synapse_words[0], 64)}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_ROUTE_DESC0 {")
    for core_id in LOGICAL_CORES:
        seeds = backing[core_id].image.route_descriptor_words
        if len(seeds) != 1 or seeds[0].index != 0:
            raise AssertionError("P02.4b ring expects route descriptor 0")
        lines.append(f"  {core_id} {_hex(seeds[0].word, 32)}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_ROUTE0 {")
    for core_id in LOGICAL_CORES:
        lines.append(f"  {core_id} {_hex(backing[core_id].image.route_words[0], 32)}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_EVENT_COUNT {")
    for row in dispatch_rows:
        lines.append(f"  {row['timestep']},{row['core_id']} {row['event_count']}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_STATE {")
    for row in dispatch_rows:
        lines.append(
            f"  {row['timestep']},{row['core_id']} {_hex(int(row['state_after']), 64)}"
        )
    lines.append("}")

    lines.append("array set P02B_EXPECT_SPIKES {")
    for row in dispatch_rows:
        lines.append(f"  {row['timestep']},{row['core_id']} {row['spike_count']}")
    lines.append("}")

    lines.append("array set P02B_EXPECT_PACKETS {")
    for row in dispatch_rows:
        words = " ".join(_hex(int(word), 64) for word in row["packets"])
        lines.append(f"  {row['timestep']},{row['core_id']} {{{words}}}")
    lines.append("}")

    lines.append("array set P02B_FINAL_STATE {")
    for core_id in LOGICAL_CORES:
        lines.append(f"  {core_id} {_hex(final_states[core_id], 64)}")
    lines.append("}")

    final_next_bank = TIMESTEPS & 1
    lines.append(f"set P02B_FINAL_NEXT_BANK {final_next_bank}")
    lines.append("array set P02B_FINAL_NEXT_EVENTS {")
    for core_id in LOGICAL_CORES:
        count = event_counts[core_id][final_next_bank]
        words = " ".join(str(event_words[core_id][final_next_bank][i]) for i in range(count))
        lines.append(f"  {core_id} {{{words}}}")
    lines.append("}")
    (output_dir / "p02_4b_vectors.tcl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest: dict[str, object] = {
        "schema": "p02-4b-five-over-three-ring-v1",
        "logical_core_ids": list(LOGICAL_CORES),
        "logical_core_count": len(LOGICAL_CORES),
        "resident_context_count": RESIDENT_SLOTS,
        "physical_engine_count": 1,
        "timesteps": TIMESTEPS,
        "service_order": list(SERVICE_ORDER),
        "initial_residency": [0, 1, 2],
        "backing_base": f"0x{BACKING_BASE:08X}",
        "record_bytes": P02_DDR_CONTEXT_STRIDE_BYTES,
        "trace_fingerprint": trace_digest.hexdigest(),
        "dispatch_count": len(dispatch_rows),
        "expected_packet_count_total": sum(
            len(row["packets"]) for row in dispatch_rows
        ),
        "initial_record_sha256": {
            str(core_id): _record_sha(initial_records[core_id])
            for core_id in LOGICAL_CORES
        },
        "expected_final_record_sha256": {
            str(core_id): _record_sha(bytes(expected_records[core_id]))
            for core_id in LOGICAL_CORES
        },
        "final_state_words": {
            str(core_id): _hex(final_states[core_id], 64)
            for core_id in LOGICAL_CORES
        },
        "final_next_bank": final_next_bank,
        "final_next_events": {
            str(core_id): event_words[core_id][final_next_bank][
                : event_counts[core_id][final_next_bank]
            ]
            for core_id in LOGICAL_CORES
        },
        "authoritative_backing": "k26-ddr",
        "host_role": "control-routing-bookkeeping-only",
    }
    manifest["manifest_fingerprint"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return manifest


def verify(fixture_dir: Path, dump_dir: Path) -> dict[str, object]:
    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    results: dict[str, object] = {}
    for core_id in LOGICAL_CORES:
        actual_path = dump_dir / f"core{core_id}_after.bin"
        expected_path = fixture_dir / f"core{core_id}_expected.bin"
        actual = actual_path.read_bytes()
        expected = expected_path.read_bytes()
        if len(actual) != P02_DDR_CONTEXT_STRIDE_BYTES:
            raise ValueError(
                f"core {core_id} dump size {len(actual)} != {P02_DDR_CONTEXT_STRIDE_BYTES}"
            )
        if actual != expected:
            mismatch = next(
                index
                for index, (a, e) in enumerate(zip(actual, expected, strict=True))
                if a != e
            )
            bank_name = "header-or-reserved"
            for bank in P02_DDR_BANK_LAYOUT:
                if bank.offset <= mismatch < bank.end:
                    bank_name = bank.name
                    break
            raise ValueError(
                f"core {core_id} final record mismatch at 0x{mismatch:05X} "
                f"({bank_name}): actual=0x{actual[mismatch]:02X} "
                f"expected=0x{expected[mismatch]:02X}"
            )
        results[str(core_id)] = {
            "sha256": _record_sha(actual),
            "state0": _hex(_read_word(actual, "state", 0), 64),
        }
        expected_sha = manifest["expected_final_record_sha256"][str(core_id)]
        if results[str(core_id)]["sha256"] != expected_sha:
            raise ValueError(f"core {core_id} final SHA-256 drifted")

    return {
        "schema": manifest["schema"],
        "manifest_fingerprint": manifest["manifest_fingerprint"],
        "records": results,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--output-dir", type=Path, required=True)

    check = sub.add_parser("verify")
    check.add_argument("--fixture-dir", type=Path, required=True)
    check.add_argument("--dump-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        if args.command == "generate":
            manifest = generate(args.output_dir)
            print(json.dumps(manifest, indent=2, sort_keys=True))
            print(
                "PASS: P02.4b five-over-three golden fixture generated "
                f"dispatches={manifest['dispatch_count']} "
                f"packets={manifest['expected_packet_count_total']} "
                f"trace={manifest['trace_fingerprint']}"
            )
            return 0

        result = verify(args.fixture_dir, args.dump_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        print("PASS: P02.4b all five DDR backing records match golden final images")
        return 0
    except (OSError, ValueError, AssertionError) as exc:
        print(f"FAIL: P02.4b fixture: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
