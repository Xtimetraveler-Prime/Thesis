#!/usr/bin/env python3
"""Generate the deterministic M13.6 candidate findings record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.m13_findings import (
    build_m13_6_findings,
    render_m13_6_findings_markdown,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
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
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/m13_6/m13_6_findings.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("build/m13_6/m13_6_findings.md"),
    )
    args = parser.parse_args()

    findings = build_m13_6_findings(
        _load(args.crosswalk),
        _load(args.directed_findings),
        _load(args.hardware_closure),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_m13_6_findings_markdown(findings), encoding="utf-8")

    summary = findings["summary"]
    print(
        "M13.6 findings candidate PASS: "
        f"crosswalk={summary['crosswalk_rows']} "
        f"directed={summary['directed_probes']} "
        f"agreements={summary['directed_agreements']} "
        f"adjudications={summary['directed_adjudications']} "
        f"A/B={summary['class_A_or_B_findings']} "
        f"scope={summary['explicit_project_scope_exclusions']} "
        f"m12_revalidation={summary['m12_revalidation_required']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
