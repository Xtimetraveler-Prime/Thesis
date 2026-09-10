#!/usr/bin/env python3
"""Reparse preserved M13.5 native Vivado reports and verify normalized JSON."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.m13_native_report_validation import verify_native_report_regeneration


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path("build/m13_5/catalyst-k26-vivado"),
    )
    args = parser.parse_args()

    result = verify_native_report_regeneration(args.evidence_dir)
    timing = result["timing"]
    print(
        "M13.5 native report regeneration PASS: "
        f"part={result['target_part']} vivado={result['vivado']} "
        f"WNS={timing['wns_ns']:.3f}ns WHS={timing['whs_ns']:.3f}ns"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
