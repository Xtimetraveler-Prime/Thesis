#!/usr/bin/env python3
"""Generate the deterministic P03.2c A53-side MMIO smoke fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    P03_REQUIRED_ARITHMETIC,
    SynapseEntry,
    SynapseTemplate,
    export_paged_hardware_image,
)
from loihi_twin_v2.ddr_abi import build_initial_ddr_context_record


BACKING_BASE = 0x40000000
MAILBOX_BASE = 0x43FF0000
RECORD_BYTES = 0x80000


def _ring_core(core_id: int) -> LogicalCoreConfig:
    next_core = (core_id + 1) % 5
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


def generate(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = tuple(_ring_core(core_id) for core_id in range(5))
    deployment = export_paged_hardware_image(
        configs,
        resident_context_count=3,
    )
    if deployment.logical_core_ids != (0, 1, 2, 3, 4):
        raise AssertionError("P03.2c accepted ring logical-core IDs drifted")
    if deployment.initial_resident_core_ids != (0, 1, 2):
        raise AssertionError("P03.2c accepted ring initial residency drifted")
    backing = deployment.backing_by_logical_core[0]
    record = build_initial_ddr_context_record(backing)
    if len(record) != RECORD_BYTES:
        raise AssertionError("P03.2c backing record size drifted")

    image = backing.image
    metadata = (
        0
        | (image.compartment_count << 7)
        | (image.synapse_count << 18)
        | (image.route_count << 34)
        | (0 << 47)
    )
    config0 = image.config_words[0]

    (output_dir / "core0_initial.bin").write_bytes(record)
    (output_dir / "mailbox_zero.bin").write_bytes(bytes(64))
    (output_dir / "p03_2c_fixture.h").write_text(
        f"""#ifndef P03_2C_FIXTURE_H
#define P03_2C_FIXTURE_H

#include <stdint.h>

#define P03_SMOKE_RECORD_BASE ((uintptr_t)0x{BACKING_BASE:08X}u)
#define P03_SMOKE_MAILBOX_BASE ((uintptr_t)0x{MAILBOX_BASE:08X}u)
#define P03_SMOKE_EXPECT_CONFIG0 UINT32_C(0x{config0 & 0xFFFFFFFF:08X})
#define P03_SMOKE_DISPATCH_METADATA UINT64_C(0x{metadata:016X})
#define P03_SMOKE_EXPECT_PAGE_BYTES UINT32_C(438272)
#define P03_SMOKE_EXPECT_PAGE_READ_BURSTS UINT32_C(1712)
#define P03_SMOKE_EXPECT_PAGE_WRITE_BURSTS UINT32_C(0)

#endif
""",
        encoding="utf-8",
    )
    sha = hashlib.sha256(record).hexdigest()
    manifest = {
        "schema": "p03-2c-a53-mmio-smoke-v1",
        "record_base": f"0x{BACKING_BASE:08X}",
        "mailbox_base": f"0x{MAILBOX_BASE:08X}",
        "record_sha256": sha,
        "expected_config0": f"0x{config0:X}",
        "dispatch_metadata": f"0x{metadata:X}",
        "expected_page_bytes": 438272,
        "expected_page_read_bursts": 1712,
        "expected_page_write_bursts": 0,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "PASS: P03.2c smoke fixture generated "
        f"record_sha256={sha} "
        f"config0=0x{config0:X} metadata=0x{metadata:X}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    generate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
