#!/usr/bin/env python3
"""Verify the physical P03.2c A53 MMIO smoke mailbox."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys

MAILBOX_MAGIC = 0x50333243
MAILBOX_VERSION = 1
MAILBOX_PASS = 0x600D600D
P03_MMIO_ID = 0x4C543302
P03_MMIO_VERSION = 0x00010000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mailbox", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    data = args.mailbox.read_bytes()
    if len(data) != 64:
        print(f"FAIL: P03.2c mailbox size {len(data)} != 64", file=sys.stderr)
        return 1

    words = struct.unpack("<16I", data)
    (
        magic,
        version,
        result,
        fail_code,
        mmio_id,
        mmio_version,
        capabilities,
        global_status,
        page_status,
        page_bytes,
        page_read_bursts,
        page_write_bursts,
        debug_status,
        resident_config0,
        dispatch_status,
        dispatch_completed,
    ) = words

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected_config0 = int(manifest["expected_config0"], 16)

    checks = [
        ("magic", magic, MAILBOX_MAGIC),
        ("version", version, MAILBOX_VERSION),
        ("result", result, MAILBOX_PASS),
        ("fail_code", fail_code, 0),
        ("mmio_id", mmio_id, P03_MMIO_ID),
        ("mmio_version", mmio_version, P03_MMIO_VERSION),
        ("page_done", (page_status >> 1) & 1, 1),
        ("page_errors", page_status & 0xFC, 0),
        ("page_bytes", page_bytes, manifest["expected_page_bytes"]),
        ("page_read_bursts", page_read_bursts, manifest["expected_page_read_bursts"]),
        ("page_write_bursts", page_write_bursts, manifest["expected_page_write_bursts"]),
        ("debug_done", (debug_status >> 1) & 1, 1),
        ("debug_rvalid", (debug_status >> 2) & 1, 1),
        ("debug_errors", debug_status & 0x18, 0),
        ("resident_config0", resident_config0, expected_config0 & 0xFFFFFFFF),
        ("dispatch_done", (dispatch_status >> 1) & 1, 1),
        ("dispatch_errors", dispatch_status & 0x7C, 0),
        ("dispatch_completed", dispatch_completed, 1),
    ]

    failures = []
    for label, actual, expected in checks:
        if actual != expected:
            failures.append(
                f"{label}: actual=0x{actual:X} expected=0x{int(expected):X}"
            )

    required_caps = 0x0001031F
    if capabilities != required_caps:
        failures.append(
            f"capabilities: actual=0x{capabilities:X} expected=0x{required_caps:X}"
        )
    if global_status != 0:
        failures.append(f"global_status: actual=0x{global_status:X} expected=0")

    if failures:
        for failure in failures:
            print(f"FAIL: P03.2c {failure}", file=sys.stderr)
        return 1

    print(
        "PASS: P03.2c mailbox verified "
        f"id=0x{mmio_id:08X} capabilities=0x{capabilities:08X} "
        f"page_bytes={page_bytes} config0=0x{resident_config0:08X} "
        f"dispatches={dispatch_completed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
