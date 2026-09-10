#!/usr/bin/env python3
"""Validate a regenerated M13.4 report against the committed candidate findings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("build/m13_4/differential/directed-report.json"),
    )
    parser.add_argument(
        "--findings",
        type=Path,
        default=Path("references/m13_4_candidate_findings.json"),
    )
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    findings = json.loads(args.findings.read_text(encoding="utf-8"))

    expected_summary = findings["summary"]
    observed_summary = report["summary"]
    for key in ("agreement", "architectural_difference", "partial_scope", "non_comparable", "class_A_or_B"):
        if observed_summary.get(key) != expected_summary.get(key):
            raise SystemExit(
                f"M13.4 summary mismatch for {key}: "
                f"expected={expected_summary.get(key)!r} observed={observed_summary.get(key)!r}"
            )

    expected_rows = {row["probe_id"]: row for row in findings["results"]}
    observed_rows = {row["probe_id"]: row for row in report["results"]}
    if set(expected_rows) != set(observed_rows):
        raise SystemExit(
            "M13.4 probe-id set changed: "
            f"expected={sorted(expected_rows)} observed={sorted(observed_rows)}"
        )

    for probe_id, expected in expected_rows.items():
        observed = observed_rows[probe_id]
        if observed.get("status") != expected.get("status"):
            raise SystemExit(
                f"{probe_id} status mismatch: expected={expected.get('status')} "
                f"observed={observed.get('status')}"
            )
        if observed.get("discrepancy_classes") != expected.get("discrepancy_classes"):
            raise SystemExit(
                f"{probe_id} discrepancy classes changed: "
                f"expected={expected.get('discrepancy_classes')} "
                f"observed={observed.get('discrepancy_classes')}"
            )
        if observed.get("requires_m12_revalidation"):
            raise SystemExit(f"{probe_id} unexpectedly requires M12 revalidation")

    p03 = observed_rows["P03-negative-rounding"]["first_divergence"]
    if not (
        p03.get("canonical_tick") == 0
        and p03.get("field") == "current_after"
        and p03.get("reference") == [-47]
        and p03.get("candidate") == [-46]
    ):
        raise SystemExit(f"P03 first divergence changed: {p03!r}")

    p06 = observed_rows["P06-signed-synaptic-drive"]["first_divergence"]
    if not (
        p06.get("canonical_tick") == 0
        and p06.get("field") == "voltage_after"
        and p06.get("reference") == [-128]
        and p06.get("candidate") == [0]
    ):
        raise SystemExit(f"P06 first divergence changed: {p06!r}")

    p10 = observed_rows["P10-recurrent-timing"]["first_divergence"]
    expected_lags = {
        "project_fpga_v1": 1,
        "catalyst_cpu_sync": 1,
        "brian2loihi_0_5_2": None,
    }
    if p10.get("field") != "source_spike_to_target_spike_lag" or p10.get("values") != expected_lags:
        raise SystemExit(f"P10 recurrent lag finding changed: {p10!r}")

    p08 = observed_rows["P08-fanin-fanout"]["observation"]
    if p08.get("fanin_target") != 192 or p08.get("fanout_targets") != [64, 128, 192]:
        raise SystemExit(f"P08 logical graph observation changed: {p08!r}")

    print(
        "M13.4 candidate findings PASS: "
        f"probes={len(observed_rows)} agreement={observed_summary['agreement']} "
        f"architectural_difference={observed_summary['architectural_difference']} "
        f"partial_scope={observed_summary['partial_scope']} "
        f"non_comparable={observed_summary['non_comparable']} "
        f"class_A_or_B={observed_summary['class_A_or_B']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
