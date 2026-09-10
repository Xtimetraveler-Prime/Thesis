#!/usr/bin/env python3
"""Validate the tracked M13.6 candidate against all frozen M13 evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.m13_findings import validate_tracked_m13_6_findings


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--findings",
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

    tracked = _load(args.findings)
    crosswalk = _load(args.crosswalk)
    directed = _load(args.directed_findings)
    hardware = _load(args.hardware_closure)
    validate_tracked_m13_6_findings(tracked, crosswalk, directed, hardware)

    summary = tracked["summary"]
    change = tracked["change_control"]
    print(
        "M13.6 tracked findings PASS: "
        f"status={tracked['status']} "
        f"probes={summary['directed_probes']} "
        f"agreements={summary['directed_agreements']} "
        f"adjudications={summary['directed_adjudications']} "
        f"A/B={summary['class_A_or_B_findings']} "
        f"scope={summary['explicit_project_scope_exclusions']} "
        f"baseline={change['project_baseline_status']} "
        f"m12_revalidation={change['m12_physical_revalidation_required']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
