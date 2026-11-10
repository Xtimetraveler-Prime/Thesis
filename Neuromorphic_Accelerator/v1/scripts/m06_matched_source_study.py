#!/usr/bin/env python3
"""Reproducible M06 native-only locality x block-size AXI-traffic experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m06_matched_experiment import source_only_sweep


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.output.exists():
            raise ValueError("choose a NEW output path; no overwrite of original evidence")
        parent = a.output.parent.resolve(strict=True)
        if not parent.is_dir():
            raise ValueError("output folder must already exist")
        results = source_only_sweep()
        with a.output.open("x", encoding="utf-8") as fp:
            json.dump(results, fp, indent=2, sort_keys=True)
            fp.write("\n")
    except (OSError, ValueError, AssertionError) as exc:
        print(f"M06 SOURCE EXPERIMENT FAIL: {exc}", file=sys.stderr)
        return 2
    print("M06 SOURCE-ONLY role-isomorphic neural + 256/128 modeled AXI traffic "
          f"PASS ({results['schema_rows']} cases); actual vendor/DDR NOT RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
