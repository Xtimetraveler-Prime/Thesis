#!/usr/bin/env python3
"""Verify 64-byte physical P03.3b2 A53 policy+adapter probe mailbox."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

FIELDS = (
    "magic", "schema", "result", "fail_code",
    "mmio_id", "mmio_version", "capabilities", "ps_width_raw",
    "resident_config0", "page_bytes", "pages_completed",
    "dispatches_completed", "logical_dispatches", "barriers",
    "initial_page_ins", "runtime_fault",
)
EXPECTED_FIXED = {
    "magic": 0x50333342,
    "schema": 1,
    "result": 0x600D600D,
    "fail_code": 0,
    "mmio_id": 0x4C543302,
    "mmio_version": 0x00010000,
    "capabilities": 0x0001031F,
    "page_bytes": 438272,
    "pages_completed": 1,
    "dispatches_completed": 2,
    "logical_dispatches": 2,
    "barriers": 2,
    "initial_page_ins": 1,
    "runtime_fault": 0,
}


def verify(path: Path, manifest: Path) -> bool:
    data = path.read_bytes()
    if len(data) != 64:
        print(f"FAIL: P03.3b2 mailbox size {len(data)} != 64 bytes", file=sys.stderr)
        return False
    words = dict(zip(FIELDS, struct.unpack("<16I", data)))
    expected_config0 = int(
        json.loads(manifest.read_text(encoding="utf-8"))["expected_config0"], 16
    ) & 0xFFFFFFFF
    expected = dict(EXPECTED_FIXED, resident_config0=expected_config0)
    errors = []
    for key, value in expected.items():
        if words[key] != value:
            errors.append(
                f"{key}: actual=0x{words[key]:08X} expected=0x{value:08X}"
            )
    ps_width = (words["ps_width_raw"] >> 8) & 0x3
    if ps_width != 2:
        errors.append(
            f"ps_width_bits: actual_selector={ps_width} expected=2 (128-bit)"
        )
    if errors:
        for issue in errors:
            print(f"FAIL: P03.3b2 {issue}", file=sys.stderr)
        print(
            "FAIL: P03.3b2 standalone hardware-adapter probe "
            f"(result=0x{words['result']:08X}, fail_code={words['fail_code']}, "
            f"runtime_fault={words['runtime_fault']})",
            file=sys.stderr,
        )
        return False
    print(
        "PASS: P03.3b2 physical A53 adapter probe "
        f"ps_width=128 id=0x{words['mmio_id']:08X} "
        f"config0=0x{words['resident_config0']:08X} "
        f"page_bytes={words['page_bytes']} "
        f"page_ins={words['initial_page_ins']} "
        f"dispatches={words['logical_dispatches']} "
        f"barriers={words['barriers']}"
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    return 0 if verify(args.mailbox, args.manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())
