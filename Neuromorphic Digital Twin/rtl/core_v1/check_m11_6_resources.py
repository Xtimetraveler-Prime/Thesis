#!/usr/bin/env python3
"""Validate M11.6 implemented K26 resource usage from existing Vivado reports.

Vivado 2025.2 does not always emit a literal `Block RAM Tile` row in the
implemented top-level utilization report. Use that report for CLB/DSP/URAM and
the dedicated RAM-utilization report for RAMB36/RAMB18. BRAM tiles are counted
conservatively as RAMB36 + ceil(RAMB18/2), which cannot understate physical tile
consumption.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import re


def table_row(path: Path, prefixes: tuple[str, ...]) -> tuple[int, int] | None:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        fields = [field.strip() for field in line.strip().strip("|").split("|")]
        if len(fields) < 2 or not any(fields[0].startswith(p) for p in prefixes):
            continue
        numbers: list[int] = []
        for field in fields[1:]:
            token = field.replace(",", "")
            if re.fullmatch(r"-?\d+", token):
                numbers.append(int(token))
        if len(fields) >= 5:
            try:
                used = int(fields[1].replace(",", ""))
                available = int(fields[4].replace(",", ""))
                return used, available
            except ValueError:
                pass
        if len(numbers) >= 2:
            return numbers[0], numbers[-1]
    return None


def primitive_used(path: Path, prefixes: tuple[str, ...]) -> int:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        fields = [field.strip() for field in line.strip().strip("|").split("|")]
        if len(fields) < 2 or not any(fields[0].startswith(p) for p in prefixes):
            continue
        try:
            return int(fields[1].replace(",", ""))
        except ValueError:
            continue
    raise SystemExit(f"ERROR: could not locate RAM utilization row: {prefixes}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("utilization", type=Path)
    parser.add_argument("ram_utilization", type=Path)
    args = parser.parse_args()

    for path in (args.utilization, args.ram_utilization):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"ERROR: missing or empty M11.6 report: {path}")

    specs = (
        (("CLB LUTs",), "CLB_LUT", 117120),
        (("CLB Registers",), "CLB_REG", 234240),
        (("DSPs",), "DSP", 1248),
        (("URAM",), "URAM", 64),
    )
    summary: list[str] = []
    failed = False
    for prefixes, label, frozen_capacity in specs:
        parsed = table_row(args.utilization, prefixes)
        if parsed is None:
            raise SystemExit(f"ERROR: could not locate utilization row: {prefixes[0]}")
        used, report_capacity = parsed
        # The frozen K26 capacity is normative; also reject a surprising report
        # capacity so a wrong-part project cannot accidentally pass this check.
        if report_capacity != frozen_capacity:
            raise SystemExit(
                f"ERROR: {label} capacity mismatch: report={report_capacity}, "
                f"expected={frozen_capacity}"
            )
        summary.append(f"{label}={used}/{frozen_capacity}")
        failed |= used > frozen_capacity

    ramb36 = primitive_used(args.ram_utilization, ("RAMB36/FIFO", "RAMB36E2", "RAMB36"))
    ramb18 = primitive_used(args.ram_utilization, ("RAMB18", "RAMB18E2"))
    bram_tiles = ramb36 + math.ceil(ramb18 / 2)
    summary.insert(2, f"BRAM_TILE<={bram_tiles}/144 (RAMB36={ramb36}, RAMB18={ramb18})")
    failed |= bram_tiles > 144

    if failed:
        raise SystemExit("ERROR: M11.6 implemented design exceeds K26 physical resource capacity")

    print("M11.6 implementation resource check passed: " + ", ".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
