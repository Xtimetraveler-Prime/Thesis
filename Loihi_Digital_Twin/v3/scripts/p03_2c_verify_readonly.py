#!/usr/bin/env python3
"""Decode Cortex-A53-generated read-only MMIO evidence from the DDR mailbox."""

from __future__ import annotations

import argparse
from pathlib import Path
import struct
import sys

MAGIC = 0x50335244
VERSION = 1
COMPLETE = 0xC0DEF00D
PASS_RESULT = 0x600D600D
EXPECTED = (0x4C543302, 0x00010000, 0x0001031F, 0xD1A60018)
ADDRESSES = (0xA4000000, 0xA4000004, 0xA4000008, 0xA4000018)


def verify(path: Path) -> bool:
    data = path.read_bytes()
    if len(data) != 64:
        print(f"FAIL: A53 read-only mailbox has {len(data)} bytes, expected 64")
        return False
    words = struct.unpack("<16I", data)
    magic, version, result, count = words[:4]
    actual = words[4:8]
    expected_from_app = words[8:12]
    mask, complete, mmio_base, mailbox_base = words[12:16]

    print(f"P03_2C_A53_MAGIC=0x{magic:08X}")
    print(f"P03_2C_A53_RESULT=0x{result:08X}")
    print(f"P03_2C_A53_COMPLETE=0x{complete:08X}")
    for address, observed, wanted in zip(ADDRESSES, actual, EXPECTED):
        status = "PASS" if observed == wanted else "FAIL"
        print(
            f"{status}: Cortex-A53 MMIO 0x{address:08X} "
            f"returned 0x{observed:08X}, expected 0x{wanted:08X}"
        )
    checks = [
        ("magic", magic == MAGIC),
        ("format version", version == VERSION),
        ("read count", count == 4),
        ("expected constants", expected_from_app == EXPECTED),
        ("completion marker", complete == COMPLETE),
        ("result", result == PASS_RESULT),
        ("match mask", mask == 0xF),
        ("MMIO base", mmio_base == ADDRESSES[0]),
        ("mailbox address", mailbox_base == 0x43FF0000),
        ("all reads", actual == EXPECTED),
    ]
    bad = [name for name, okay in checks if not okay]
    if bad:
        print(
            "FAIL: P03.2c A53 read-only diagnostic (" + ", ".join(bad) + ")",
            file=sys.stderr,
        )
        if magic != MAGIC or complete != COMPLETE:
            print(
                "INFO: A53 ELF may not have executed to completion; a frozen "
                "Linux instance is not sufficient evidence of MMIO failure.",
                file=sys.stderr,
            )
        return False
    print("PASS: P03.2c read-only Cortex-A53 MMIO diagnostic")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox", type=Path, required=True)
    args = parser.parse_args()
    return 0 if verify(args.mailbox) else 1


if __name__ == "__main__":
    raise SystemExit(main())
