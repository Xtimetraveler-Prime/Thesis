#!/usr/bin/env python3
"""Validate the final M13.6/M13 closure against the frozen candidate/evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.m13_closure import validate_m13_6_closure


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--closure",
        type=Path,
        default=Path("references/m13_6_closure.json"),
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=Path("references/m13_6_findings.json"),
    )
    parser.add_argument(
        "--crosswalk",
        type=Path,
        default=Path("references/m13_2_feature_crosswalk.json"),
    )
    parser.add_argument(
        "--directed-findings",
        type=Path,
        default=Path("references/m13_4_candidate_findings.json"),
    )
    parser.add_argument(
        "--hardware-closure",
        type=Path,
        default=Path("references/m13_5_closure.json"),
    )
    args = parser.parse_args()

    candidate_bytes = args.candidate.read_bytes()
    closure = _load(args.closure)
    validate_m13_6_closure(
        closure,
        _load(args.candidate),
        candidate_bytes,
        _load(args.crosswalk),
        _load(args.directed_findings),
        _load(args.hardware_closure),
    )

    summary = closure["accepted_summary"]
    print(
        "M13.6 closure validated: "
        f"status={closure['status']} "
        f"M13={closure['milestones']['M13']} "
        f"agreements={summary['directed_agreements']} "
        f"adjudications={summary['directed_adjudications']} "
        f"A/B={summary['class_A_or_B_findings']} "
        f"baseline={closure['change_control']['project_baseline_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
