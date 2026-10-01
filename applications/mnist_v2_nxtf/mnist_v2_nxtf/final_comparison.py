"""P08.5.2 thesis-facing NxTF comparison derived from the accepted P08.5.1 ledger.

This module does not define new experimental measurements.  It validates the
frozen P08.5.1 ledger identity, selects only ledger-authorized comparisons, and
renders a bounded thesis-facing report plus a machine-readable interpretation
summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .comparison_ledger import (
    COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
    CONTEXT_ONLY,
    DIRECTLY_COMPARABLE,
    NOT_COMPARABLE,
    PROJECT_SPECIFIC,
    build_ledger,
)

REPORT_SCHEMA = "p08-nxtf-final-comparison-v1"
REPORT_STATUS = "P08_5_2_FINAL_COMPARISON_REVIEW_PENDING"
REPORT_JSON = "p08_5_final_comparison.json"
REPORT_MARKDOWN = "p08_5_final_comparison.md"

ACCEPTED_LEDGER_FINGERPRINT = (
    "574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d"
)

CROSS_SYSTEM_TABLE = [
    "dataset",
    "class_count",
    "network_family",
    "algorithmic_timesteps",
    "ann_test_error",
    "snn_test_error",
    "ann_to_snn_error_increase",
    "neuron_count",
    "trainable_parameters",
    "expanded_connections",
    "shared_weight_accounting",
    "mapped_core_count",
    "native_loihi_energy",
    "native_loihi_latency",
]

PROJECT_IMPLEMENTATION_TABLE = [
    "resident_context_count",
    "physical_engine_count",
    "representative_forward_page_loads",
    "representative_internal_packet_traffic",
    "fpga_pl_clock",
    "representative_physical_dispatch_cycles",
    "representative_physical_dispatch_time",
    "fpga_uram",
    "fpga_setup_slack",
    "physical_conformance_scope",
]

AUTHORIZED_NUMERIC_CROSS_SYSTEM = [
    "ann_test_error",
    "snn_test_error",
    "ann_to_snn_error_increase",
]

FORBIDDEN_DERIVED_CROSS_SYSTEM = [
    "shared_weight_accounting",
    "mapped_core_count",
    "native_loihi_energy",
    "native_loihi_latency",
]


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _rows_by_id(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in ledger["rows"]}


def _safe_delta(row: dict[str, Any]) -> float:
    if not row["allow_numeric_delta"]:
        raise ValueError(f"{row['id']}: ledger does not authorize a numeric delta")
    left = row["nxtf"]["value"]
    right = row["project"]["value"]
    if isinstance(left, bool) or isinstance(right, bool):
        raise ValueError(f"{row['id']}: boolean values are not numeric comparison inputs")
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        raise ValueError(f"{row['id']}: numeric delta requires numeric values on both sides")
    return float(right - left)


def _percent(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def _percentage_points(value: float) -> str:
    return f"{100.0 * value:.2f} percentage points"


def build_report() -> dict[str, Any]:
    ledger = build_ledger()
    if ledger["ledger_fingerprint"] != ACCEPTED_LEDGER_FINGERPRINT:
        raise ValueError("accepted P08.5.1 ledger fingerprint drifted")

    rows = _rows_by_id(ledger)
    numeric = {
        metric_id: _safe_delta(rows[metric_id])
        for metric_id in AUTHORIZED_NUMERIC_CROSS_SYSTEM
    }

    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": REPORT_STATUS,
        "ledger_schema": ledger["schema"],
        "accepted_ledger_fingerprint": ACCEPTED_LEDGER_FINGERPRINT,
        "accepted_identities": ledger["accepted_identities"],
        "cross_system_metric_ids": list(CROSS_SYSTEM_TABLE),
        "project_implementation_metric_ids": list(PROJECT_IMPLEMENTATION_TABLE),
        "authorized_numeric_cross_system_metric_ids": list(AUTHORIZED_NUMERIC_CROSS_SYSTEM),
        "forbidden_derived_cross_system_metric_ids": list(FORBIDDEN_DERIVED_CROSS_SYSTEM),
        "numeric_comparisons": {
            "ann_test_error_gap_fraction": numeric["ann_test_error"],
            "ann_test_error_gap_percentage_points": 100.0 * numeric["ann_test_error"],
            "snn_test_error_gap_fraction": numeric["snn_test_error"],
            "snn_test_error_gap_percentage_points": 100.0 * numeric["snn_test_error"],
            "ann_to_snn_error_increase_gap_fraction": numeric["ann_to_snn_error_increase"],
            "ann_to_snn_error_increase_gap_percentage_points": 100.0 * numeric["ann_to_snn_error_increase"],
        },
        "bounded_findings": [
            {
                "id": "same_task_and_horizon",
                "basis": DIRECTLY_COMPARABLE,
                "metric_ids": ["dataset", "class_count", "algorithmic_timesteps"],
                "text": (
                    "Both experiments use the MNIST ten-class task and a primary 100-algorithmic-timestep inference horizon."
                ),
            },
            {
                "id": "ann_accuracy_gap",
                "basis": COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
                "metric_ids": ["ann_test_error"],
                "numeric_delta_metric_id": "ann_test_error",
                "text": (
                    "The published NxTF ANN error is 0.74%, while the accepted reconstructed project ANN error is 1.26%; "
                    "the project error is therefore 0.52 percentage points higher. The comparison is useful but is not an exact-paper-model reproduction because the unpublished benchmark topology/checkpoint was not recovered."
                ),
            },
            {
                "id": "snn_accuracy_gap",
                "basis": COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
                "metric_ids": ["snn_test_error"],
                "numeric_delta_metric_id": "snn_test_error",
                "text": (
                    "At 100 timesteps, the published NxTF converted-SNN error is 0.79% and the accepted project SNN error is 1.76%, "
                    "a 0.97-percentage-point higher error for the project reconstruction."
                ),
            },
            {
                "id": "conversion_loss_gap",
                "basis": COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
                "metric_ids": ["ann_to_snn_error_increase"],
                "numeric_delta_metric_id": "ann_to_snn_error_increase",
                "text": (
                    "NxTF reports a 0.05-percentage-point ANN-to-SNN error increase, whereas the project reconstruction increases by 0.50 percentage points; "
                    "the conversion-loss increase is 0.45 percentage points larger in the project result. This does not isolate conversion as the cause of the overall cross-system accuracy difference."
                ),
            },
            {
                "id": "structural_scale_correspondence",
                "basis": COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
                "metric_ids": ["neuron_count", "trainable_parameters", "expanded_connections"],
                "text": (
                    "The reconstruction is close to the published aggregate problem scale: NxTF reports approximately 4k neurons, approximately 7k trainable parameters, and approximately 341k discrete connections; "
                    "the project contains 4,218 neurons, 7,006 trainable parameters, and 338,880 expanded connections. Because the paper values are rounded and the exact graph is unrecovered, no precision ratio or exact-match claim is made."
                ),
            },
            {
                "id": "mapping_and_sharing_context",
                "basis": CONTEXT_ONLY,
                "metric_ids": ["shared_weight_accounting", "mapped_core_count"],
                "text": (
                    "NxTF reports 6,746 shared weights and 14 Loihi neurocores, while P06 reports 64,235 project stored/shared entries and five project logical cores. "
                    "These are contextual side-by-side values only: the storage representations, partitioners, and compiler/resource models differ, so no efficiency ratio is derived."
                ),
            },
            {
                "id": "project_virtualization_observation",
                "basis": PROJECT_SPECIFIC,
                "metric_ids": [
                    "mapped_core_count",
                    "resident_context_count",
                    "physical_engine_count",
                    "representative_forward_page_loads",
                    "representative_internal_packet_traffic",
                ],
                "text": (
                    "The accepted project deployment contains five logical cores executed with three resident K26 context slots and one physical HLS engine. "
                    "For the frozen representative sample under forward paging, P08.4.2 records 497 page loads and 17,910 internal packets. These are FPGA-v2 implementation observations, not native-Loihi measurements."
                ),
            },
            {
                "id": "physical_dispatch_observation",
                "basis": PROJECT_SPECIFIC,
                "metric_ids": [
                    "fpga_pl_clock",
                    "representative_physical_dispatch_cycles",
                    "representative_physical_dispatch_time",
                    "fpga_uram",
                    "fpga_setup_slack",
                    "physical_conformance_scope",
                ],
                "text": (
                    "The routed K26 shell closes the requested 100 MHz clock with +0.734 ns worst setup slack and uses 47 URAM288 primitives. "
                    "The representative logical-core-4 timestep-99 physical dispatch requires 3,865 PL cycles, or 38.65 microseconds at 100 MHz, and exactly reproduces the accepted state/trace/output evidence. "
                    "That observation is one deep-core dispatch, not end-to-end sample latency."
                ),
            },
            {
                "id": "native_physical_metrics_noncomparable",
                "basis": NOT_COMPARABLE,
                "metric_ids": ["native_loihi_energy", "native_loihi_latency"],
                "text": (
                    "The paper's 0.66 mJ/sample and 6.65 ms/sample native-Loihi measurements remain published context only. "
                    "P08 did not establish equivalent workload-specific K26 energy or end-to-end latency measurements, so no FPGA-versus-Loihi energy or latency conclusion is drawn."
                ),
            },
            {
                "id": "physical_scope_boundary",
                "basis": PROJECT_SPECIFIC,
                "metric_ids": ["physical_conformance_scope"],
                "text": (
                    "Complete 100-timestep paging and service-order invariance are established by P08.4.2 software conformance. P08.4.3b physically validates a representative real MNIST page replacement and deep-core dispatch; it does not claim an end-to-end JTAG replay of the complete inference."
                ),
            },
        ],
        "explicit_nonclaims": [
            "The project does not claim recovery of the exact unpublished NxTF MNIST topology or checkpoint.",
            "The project does not claim that P06 stored/shared entries are equivalent to NxTF native shared-weight storage.",
            "The project does not claim that five P06 logical cores are directly equivalent to five Loihi neurocores or that five versus fourteen establishes mapping efficiency.",
            "The project does not claim a K26 energy-per-sample result comparable to the paper's 0.66 mJ/sample.",
            "The project does not claim end-to-end K26 sample latency comparable to the paper's 6.65 ms/sample.",
            "The 3,865-cycle / 38.65-microsecond observation is one representative deep-core dispatch, not full-sample inference latency.",
            "The project does not claim that the entire 100-timestep representative inference was physically replayed end-to-end over JTAG.",
            "No model or conversion policy was selected or retuned in response to the official-test result.",
        ],
        "guardrails": dict(ledger["guardrails"]),
    }

    validate_report(report, ledger=ledger)
    report["report_fingerprint"] = _fingerprint(report)
    return report


def validate_report(report: dict[str, Any], *, ledger: dict[str, Any] | None = None) -> None:
    if ledger is None:
        ledger = build_ledger()
    if ledger["ledger_fingerprint"] != ACCEPTED_LEDGER_FINGERPRINT:
        raise ValueError("accepted comparison ledger fingerprint drifted")
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError("final comparison schema drifted")
    if report.get("status") != REPORT_STATUS:
        raise ValueError("final comparison status drifted")
    if report.get("accepted_ledger_fingerprint") != ACCEPTED_LEDGER_FINGERPRINT:
        raise ValueError("final comparison is not bound to accepted P08.5.1 ledger")
    if report.get("accepted_identities") != ledger["accepted_identities"]:
        raise ValueError("accepted P08 identities drifted in final comparison")

    rows = _rows_by_id(ledger)
    known = set(rows)
    for field in ("cross_system_metric_ids", "project_implementation_metric_ids"):
        values = report.get(field)
        if not isinstance(values, list) or not values:
            raise ValueError(f"{field} must be a nonempty list")
        unknown = set(values) - known
        if unknown:
            raise ValueError(f"{field} contains unknown ledger metrics: {sorted(unknown)}")

    if report.get("authorized_numeric_cross_system_metric_ids") != AUTHORIZED_NUMERIC_CROSS_SYSTEM:
        raise ValueError("authorized numeric comparison set drifted")
    if report.get("forbidden_derived_cross_system_metric_ids") != FORBIDDEN_DERIVED_CROSS_SYSTEM:
        raise ValueError("forbidden derived comparison set drifted")

    for metric_id in AUTHORIZED_NUMERIC_CROSS_SYSTEM:
        row = rows[metric_id]
        if not row["allow_numeric_delta"]:
            raise ValueError(f"{metric_id}: report attempted unauthorized numeric comparison")
        if row["comparison_class"] != COMPARABLE_WITH_RECONSTRUCTION_CAVEAT:
            raise ValueError(f"{metric_id}: expected reconstruction-caveat classification")

    for metric_id in FORBIDDEN_DERIVED_CROSS_SYSTEM:
        row = rows[metric_id]
        if row["allow_numeric_delta"]:
            raise ValueError(f"{metric_id}: forbidden derived comparison became numeric")
        if row["comparison_class"] not in {CONTEXT_ONLY, NOT_COMPARABLE}:
            raise ValueError(f"{metric_id}: forbidden derived comparison class drifted")

    expected_numeric = {
        "ann_test_error_gap_fraction": 0.0052,
        "ann_test_error_gap_percentage_points": 0.52,
        "snn_test_error_gap_fraction": 0.0097,
        "snn_test_error_gap_percentage_points": 0.97,
        "ann_to_snn_error_increase_gap_fraction": 0.0045,
        "ann_to_snn_error_increase_gap_percentage_points": 0.45,
    }
    numeric = report.get("numeric_comparisons")
    if not isinstance(numeric, dict):
        raise ValueError("numeric_comparisons must be a mapping")
    for key, expected in expected_numeric.items():
        actual = numeric.get(key)
        if not isinstance(actual, (int, float)) or abs(float(actual) - expected) > 1e-12:
            raise ValueError(f"{key}: final comparison numeric anchor drifted")

    findings = report.get("bounded_findings")
    if not isinstance(findings, list) or not findings:
        raise ValueError("bounded findings are required")
    finding_ids = [finding.get("id") for finding in findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise ValueError("bounded finding IDs must be unique")

    for finding in findings:
        metric_ids = finding.get("metric_ids")
        if not isinstance(metric_ids, list) or not metric_ids:
            raise ValueError(f"{finding.get('id')}: metric_ids required")
        if set(metric_ids) - known:
            raise ValueError(f"{finding.get('id')}: unknown ledger metric")
        basis = finding.get("basis")
        if basis not in {
            DIRECTLY_COMPARABLE,
            COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
            CONTEXT_ONLY,
            PROJECT_SPECIFIC,
            NOT_COMPARABLE,
        }:
            raise ValueError(f"{finding.get('id')}: invalid comparison basis")
        numeric_metric = finding.get("numeric_delta_metric_id")
        if numeric_metric is not None:
            if numeric_metric not in AUTHORIZED_NUMERIC_CROSS_SYSTEM:
                raise ValueError(f"{finding.get('id')}: unauthorized numeric cross-system delta")
            if numeric_metric not in metric_ids:
                raise ValueError(f"{finding.get('id')}: numeric metric must be cited by finding")
        if basis in {CONTEXT_ONLY, NOT_COMPARABLE} and numeric_metric is not None:
            raise ValueError(f"{finding.get('id')}: contextual/non-comparable finding may not derive a delta")
        if not finding.get("text"):
            raise ValueError(f"{finding.get('id')}: finding text required")

    if report.get("guardrails") != ledger["guardrails"]:
        raise ValueError("final comparison guardrails drifted from ledger")
    if any(value is not False for value in report["guardrails"].values()):
        raise ValueError("all final comparison overclaim guardrails must remain false")

    nonclaims = report.get("explicit_nonclaims")
    if not isinstance(nonclaims, list) or len(nonclaims) < 8:
        raise ValueError("explicit final non-claims are incomplete")


def _display(side: dict[str, Any]) -> str:
    value = side["value"]
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _render_table(rows: dict[str, dict[str, Any]], metric_ids: list[str], *, project_only: bool = False) -> list[str]:
    if project_only:
        lines = [
            "| Metric | FPGA-v2 P08 value | Unit | Boundary |",
            "|---|---:|---|---|",
        ]
        for metric_id in metric_ids:
            row = rows[metric_id]
            lines.append(
                f"| {row['label']} | {_display(row['project'])} | {row['unit']} | {row['comparison_class']} |"
            )
        return lines

    lines = [
        "| Metric | NxTF reference | FPGA-v2 P08 | Unit | Comparison boundary |",
        "|---|---:|---:|---|---|",
    ]
    for metric_id in metric_ids:
        row = rows[metric_id]
        lines.append(
            f"| {row['label']} | {_display(row['nxtf'])} | {_display(row['project'])} | {row['unit']} | {row['comparison_class']} |"
        )
    return lines


def render_markdown(report: dict[str, Any], *, ledger: dict[str, Any] | None = None) -> str:
    if ledger is None:
        ledger = build_ledger()
    validate_report({key: value for key, value in report.items() if key != "report_fingerprint"}, ledger=ledger)
    rows = _rows_by_id(ledger)

    numeric = report["numeric_comparisons"]
    lines = [
        "# P08.5.2 — Final NxTF / FPGA-v2 MNIST Comparison",
        "",
        "This report is generated from the independently accepted P08.5.1 comparison ledger. It distinguishes direct comparisons, reconstruction-bounded comparisons, contextual quantities, project-specific FPGA measurements, and non-comparable physical metrics.",
        "",
        f"Accepted ledger fingerprint: `{ACCEPTED_LEDGER_FINGERPRINT}`",
        "",
        "## Cross-system comparison",
        "",
    ]
    lines.extend(_render_table(rows, report["cross_system_metric_ids"]))
    lines.extend(
        [
            "",
            "## Quantitative interpretation",
            "",
            (
                f"At the same 100-timestep primary horizon, the project's ANN error is {_percentage_points(numeric['ann_test_error_gap_fraction'])} higher than the published NxTF ANN error, "
                f"and the project's converted-SNN error is {_percentage_points(numeric['snn_test_error_gap_fraction'])} higher than the published NxTF SNN error. "
                f"The ANN-to-SNN error increase is {_percentage_points(numeric['ann_to_snn_error_increase_gap_fraction'])} larger for the project reconstruction."
            ),
            "",
            "These are bounded accuracy comparisons, not exact-reproduction errors: the project matches the published aggregate scale closely but uses a source-bounded reconstructed topology/checkpoint and a different mapper/runtime implementation.",
            "",
            "The structural comparison is therefore descriptive rather than ratio-based. NxTF reports approximately 4k neurons, approximately 7k trainable parameters, and approximately 341k discrete connections; P08 contains 4,218 neurons, 7,006 trainable parameters, and 338,880 expanded connections.",
            "",
            "The 6,746 NxTF shared weights versus 64,235 P06 stored/shared entries and the 14 Loihi neurocores versus five P06 logical cores are retained only as context. The underlying storage and compiler/resource models differ, so those pairs do not support efficiency ratios.",
            "",
            "## FPGA-v2 implementation observations",
            "",
        ]
    )
    lines.extend(_render_table(rows, report["project_implementation_metric_ids"], project_only=True))
    lines.extend(
        [
            "",
            "The five-logical-core deployment is virtualized over three resident K26 contexts and one physical HLS engine. For the frozen representative sample, forward paging records 497 page loads and 17,910 internal packets.",
            "",
            "The routed physical shell closes the requested 100 MHz clock with +0.734 ns setup slack and uses 47 URAM288 primitives. The physically checked logical-core-4 timestep-99 dispatch takes 3,865 cycles, equivalent to 38.65 microseconds at 100 MHz, and matches all accepted state/trace/output evidence. This is one deep-core dispatch, not full-sample latency.",
            "",
            "## Published physical metrics that remain non-comparable",
            "",
            "NxTF reports 0.66 mJ/sample and 6.65 ms/sample on native Loihi. P08 has no equivalent workload-specific K26 energy measurement and no end-to-end K26 sample-latency measurement. Those published values are therefore contextual only and are not used to claim an FPGA energy or latency advantage/disadvantage.",
            "",
            "## Bounded findings",
            "",
        ]
    )
    for finding in report["bounded_findings"]:
        lines.append(f"- **{finding['id']}** [{finding['basis']}]: {finding['text']}")
    lines.extend(
        [
            "",
            "## Explicit non-claims",
            "",
        ]
    )
    lines.extend(f"- {text}" for text in report["explicit_nonclaims"])
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "The strongest defensible result is that a transparent FPGA implementation of the project's source-backed Loihi-like manycore architecture can execute a reconstructed deep frame-based MNIST SNN at the same 100-timestep algorithmic horizon, with aggregate network scale close to the published NxTF benchmark and with independently validated software paging plus representative physical K26 dispatch conformance. The observed accuracy gap and the differences in compiler/storage/physical execution boundaries remain part of the result rather than being normalized away.",
            "",
            f"Report fingerprint: `{report['report_fingerprint']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    ledger = build_ledger()
    report = build_report()
    (output / REPORT_JSON).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / REPORT_MARKDOWN).write_text(
        render_markdown(report, ledger=ledger), encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the bounded P08.5.2 NxTF comparison report")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    report = write_report(args.output_dir)
    numeric = report["numeric_comparisons"]
    print(
        "PASS: P08.5.2 report "
        f"ledger={report['accepted_ledger_fingerprint']} fingerprint={report['report_fingerprint']}"
    )
    print(
        "PASS: P08.5.2 accuracy gaps "
        f"ann_pp={numeric['ann_test_error_gap_percentage_points']:.2f} "
        f"snn_pp={numeric['snn_test_error_gap_percentage_points']:.2f} "
        f"conversion_pp={numeric['ann_to_snn_error_increase_gap_percentage_points']:.2f}"
    )
    print(
        "PASS: P08.5.2 structural boundary "
        "approx_scale_only=true shared_weight_ratio=false mapped_core_ratio=false"
    )
    print(
        "PASS: P08.5.2 physical boundary "
        "energy_direct=false latency_direct=false dispatch_is_sample_latency=false full_jtag_replay=false"
    )
    print(
        "PASS: P08.5.2 project implementation "
        "logical_cores=5 resident_contexts=3 physical_engines=1 page_loads=497 packets=17910 "
        "clock_mhz=100 dispatch_cycles=3865 dispatch_us=38.65 uram=47 wns_ns=0.734"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
