#!/usr/bin/env python3
"""Deterministic two-logical-core packet and dirty-page acceptance fixture.

Unlike P03.2c, this exercise deliberately causes two real HLS spikes:
  timestep 0: core0 input axon10 -> packet(core1, axon11, timestep1);
  timestep 1: core1 consumes axon11 -> packet(core0, axon20, timestep2).
Core0's initial DDR event0[0]=10 differs from the final routed DDR word20,
so packet routing is not spuriously accepted by unchanged fixture memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2 import (
    CompartmentConfig, InputAxonBinding, LogicalCoreConfig, OutputRoute,
    OutputRouteEntry, P03_REQUIRED_ARITHMETIC, SynapseEntry,
    SynapseTemplate, export_paged_hardware_image,
)
from loihi_twin_v2.ddr_abi import build_initial_ddr_context_record

DDR_BASE = 0x40000000
MAILBOX = 0x43FF0000
RECORD = 0x80000
EVENT0 = 0x54000
EVENT1 = 0x58000


def core(core_id: int) -> LogicalCoreConfig:
    # One 3-weight synapse into a 1-threshold compartment guarantees a
    # spike for a single accepted event under the P03 SAT24 profile.
    inputs = (InputAxonBinding(10, 0), InputAxonBinding(20, 0)) if core_id == 0 else (
        InputAxonBinding(11, 0),
    )
    dst_core, dst_axon = ((1, 11) if core_id == 0 else (0, 20))
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(CompartmentConfig(
            current_decay=4096, voltage_decay=0, threshold=1,
        ),),
        input_axons=inputs,
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 3),)),),
        output_routes=(OutputRouteEntry(
            0, (OutputRoute(dst_core, dst_axon),),
        ),),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def packet(dst: int, axon: int, step: int) -> int:
    return dst | (axon << 7) | (step << 29) | (1 << 61)


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    deployment = export_paged_hardware_image((core(0), core(1)),
                                            resident_context_count=1)
    assert deployment.logical_core_ids == (0, 1)
    assert deployment.initial_resident_core_ids == (0,)
    info = []
    for core_id in (0, 1):
        image = deployment.backing_by_logical_core[core_id].image
        record = build_initial_ddr_context_record(
            deployment.backing_by_logical_core[core_id],
            event0_words=(10,) if core_id == 0 else (),
        )
        assert len(record) == RECORD
        out = output / f"core{core_id}_initial.bin"
        out.write_bytes(record)
        metadata = (
            core_id | (image.compartment_count << 7) |
            (image.synapse_count << 18) | (image.route_count << 34)
        )
        info.append({
            "id": core_id,
            "metadata": metadata,
            "config0": image.config_words[0] & 0xFFFFFFFF,
            "sha256": hashlib.sha256(record).hexdigest(),
        })
    (output / "mailbox_zero.bin").write_bytes(bytes(64))
    (output / "p03_3b3_fixture.h").write_text(
        f"""#ifndef P03_3B3_FIXTURE_H
#define P03_3B3_FIXTURE_H
#include <stdint.h>
#define P03_B3_MAILBOX ((uintptr_t)0x{MAILBOX:08X}u)
#define P03_B3_RECORD0 ((uintptr_t)0x{DDR_BASE:08X}u)
#define P03_B3_RECORD1 ((uintptr_t)0x{DDR_BASE + RECORD:08X}u)
#define P03_B3_META0 UINT64_C(0x{info[0]['metadata']:016X})
#define P03_B3_META1 UINT64_C(0x{info[1]['metadata']:016X})
#define P03_B3_CONFIG0 UINT32_C(0x{info[0]['config0']:08X})
#define P03_B3_CONFIG1 UINT32_C(0x{info[1]['config0']:08X})
#define P03_B3_EXPECT_PACKET0 UINT64_C(0x{packet(1,11,1):016X})
#define P03_B3_EXPECT_PACKET1 UINT64_C(0x{packet(0,20,2):016X})
#define P03_B3_EXPECT_EVENT1_CORE1 UINT32_C(11)
#define P03_B3_EXPECT_EVENT0_CORE0 UINT32_C(20)
#define P03_B3_EXPECT_INITIAL_EVENT0_CORE0 UINT32_C(10)
#define P03_B3_PAGE_IN_BYTES UINT32_C(438272)
#define P03_B3_PAGE_OUT_BYTES UINT32_C(106496)
#endif
""", encoding="utf-8",
    )
    manifest = {
        "schema": "p03-3b3-directed-packet-page-roundtrip-v1",
        "record_base": f"0x{DDR_BASE:08X}",
        "record_bytes": RECORD,
        "mailbox_base": f"0x{MAILBOX:08X}",
        "core0": info[0],
        "core1": info[1],
        "event0_offset": EVENT0,
        "event1_offset": EVENT1,
        "input_event0_core0": 10,
        "first_packet": f"0x{packet(1,11,1):016X}",
        "last_packet": f"0x{packet(0,20,2):016X}",
        "expected_event1_core1": 11,
        "expected_event0_core0": 20,
        "expected_dispatches": 4,
        "expected_barriers": 2,
        "expected_routed_packets": 2,
        "expected_initial_page_ins": 1,
        "expected_page_ins": 3,
        "expected_page_outs": 3,
        "expected_page_completed": 7,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("PASS: P03.3b3 two-core golden packet/page fixture generated "
          f"first=0x{packet(1,11,1):016X} last=0x{packet(0,20,2):016X}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    generate(parser.parse_args().output_dir)
