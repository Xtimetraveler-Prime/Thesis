#!/usr/bin/env python3
"""Compare a failed P02.4b physical DDR dump with the initial static images."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

from loihi_twin_v2.ddr_abi import P02_DDR_BANK_LAYOUT, P02_DDR_CONTEXT_STRIDE_BYTES

STATIC = ("config", "axon", "synapse", "route_descriptor", "route")
BANKS = {bank.name: bank for bank in P02_DDR_BANK_LAYOUT}


def first_mismatch(left: bytes, right: bytes) -> int | None:
    for i, (a, b) in enumerate(zip(left, right, strict=True)):
        if a != b:
            return i
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--dump-dir", type=Path, required=True)
    args = parser.parse_args()

    any_static_failure = False
    for core in range(5):
        initial_path = args.fixture_dir / f"core{core}_initial.bin"
        current_path = args.dump_dir / f"core{core}_after.bin"
        initial = initial_path.read_bytes()
        current = current_path.read_bytes()
        if len(initial) != P02_DDR_CONTEXT_STRIDE_BYTES or len(current) != P02_DDR_CONTEXT_STRIDE_BYTES:
            raise ValueError(f"core {core} record size mismatch")

        print(
            f"P02_4B_FORENSIC_CORE={core} "
            f"initial_sha256={hashlib.sha256(initial).hexdigest()} "
            f"current_sha256={hashlib.sha256(current).hexdigest()}"
        )

        for name in STATIC:
            bank = BANKS[name]
            expected = initial[bank.offset:bank.end]
            actual = current[bank.offset:bank.end]
            mismatch = first_mismatch(actual, expected)
            if mismatch is None:
                print(
                    f"PASS: P02.4b forensic static bank preserved "
                    f"logical_core={core} bank={name}"
                )
                continue

            any_static_failure = True
            absolute = bank.offset + mismatch
            print(
                f"FAIL: P02.4b forensic static bank changed "
                f"logical_core={core} bank={name} "
                f"record_offset=0x{absolute:05X} "
                f"actual=0x{actual[mismatch]:02X} expected=0x{expected[mismatch]:02X}"
            )

        route = BANKS["route"]
        route0_actual = int.from_bytes(
            current[route.offset:route.offset + route.word_bytes], "little"
        )
        route0_expected = int.from_bytes(
            initial[route.offset:route.offset + route.word_bytes], "little"
        )
        print(
            f"P02_4B_FORENSIC_ROUTE0 core={core} "
            f"actual=0x{route0_actual:08X} expected=0x{route0_expected:08X}"
        )

    if any_static_failure:
        print("FAIL: P02.4b forensic DDR static-bank integrity changed")
        return 1

    print("PASS: P02.4b forensic all DDR static banks preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
