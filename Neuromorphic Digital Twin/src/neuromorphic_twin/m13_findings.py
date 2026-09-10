"""M13.6 final findings adjudication and change-control helpers.

The module consumes the already-frozen M13.2 architectural crosswalk, M13.4
directed findings, and M13.5 hardware closure.  It does not execute external
models and it never mutates the validated M10/M12 computational baseline.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

M13_6_FINDINGS_SCHEMA = "neuromorphic-twin-m13-final-findings-v1"
M13_6_CANDIDATE_STATUS = "candidate_frozen_pending_independent_validation"

DISCREPANCY_TAXONOMY: dict[str, str] = {
    "A": "project implementation defect",
    "B": "project interpretation/specification incomplete or inconsistent with stronger Loihi evidence",
    "C": "Catalyst N1 makes a different architectural choice",
    "D": "Brian2Loihi makes or exposes a different modeling choice",
    "E": "published Loihi evidence is ambiguous or insufficient",
    "F": "comparison mapping/normalization issue",
    "G": "feature is unsupported or outside the project's validated subset",
    "H": "test/capture/tooling defect",
}

EXPECTED_DIRECTED_RESULTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "P03-negative-rounding": ("architectural_difference", ("C",)),
    "P06-signed-synaptic-drive": ("architectural_difference", ("C",)),
    "P07-weight-encoding-boundaries": ("partial_scope", ("C", "G")),
    "P09-event-multiplicity": ("non_comparable", ("G",)),
    "P10-recurrent-timing": ("architectural_difference", ("D",)),
    "P11-state-saturation": ("non_comparable", ("E", "G")),
}

EXPECTED_AGREEMENTS = (
    "P01-current-impulse-decay",
    "P02-voltage-decay",
    "P04-threshold-boundary",
    "P05-refractory-release",
    "P08-fanin-fanout",
    "P12-simultaneous-spikes",
)

EXPECTED_PROJECT_SCOPE_EXCLUSIONS = (
    "dendritic-compartments",
    "synaptic-delay",
    "synapse-memory-organization",
    "routing-network",
    "learning-plasticity",
    "management-host-control",
    "multicore-noc",
    "async-execution",
)

PROJECT_M12_BASELINE = "80a502ec6dfc4c8d61372089b08c9a584ad65f85"
CATALYST_PIN = "1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
BRIAN2LOIHI_PIN = "d54676cb113e48dc886615a0b589bb0e4bccbca4"
M13_3_MERGE = "32cc170ced02af834ed48b9533b245db1f65641d"
M13_4_MERGE = "54c7840dff765d585e7ff236845b085007405c05"
M13_5_MERGE = "95f83ed5c1b47d5ad37badfaa091ce24dad2efed"


def _rows_by_id(rows: list[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    indexed = {str(row[key]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"duplicate {key} in M13 evidence")
    return indexed


def validate_m13_evidence_inputs(
    crosswalk: Mapping[str, Any],
    directed: Mapping[str, Any],
    hardware: Mapping[str, Any],
) -> None:
    """Fail closed if an upstream M13 evidence authority drifted."""

    if crosswalk.get("schema") != "neuromorphic-twin-m13-feature-crosswalk-v1":
        raise ValueError("unexpected M13.2 crosswalk schema")
    if crosswalk.get("project_baseline_commit") != PROJECT_M12_BASELINE:
        raise ValueError("M13.2 project baseline pin drifted")
    if crosswalk.get("catalyst_commit") != CATALYST_PIN:
        raise ValueError("M13.2 Catalyst pin drifted")
    if crosswalk.get("brian2loihi_commit") != BRIAN2LOIHI_PIN:
        raise ValueError("M13.2 Brian2Loihi pin drifted")
    crosswalk_summary = crosswalk.get("summary", {})
    if crosswalk_summary.get("row_count") != 19:
        raise ValueError("M13.2 crosswalk must contain 19 rows")
    if tuple(crosswalk_summary.get("common_subset_no", ())) != EXPECTED_PROJECT_SCOPE_EXCLUSIONS:
        raise ValueError("M13.2 explicit project-scope exclusions drifted")

    if directed.get("schema") != "neuromorphic-twin-m13-directed-findings-v1":
        raise ValueError("unexpected M13.4 findings schema")
    if directed.get("status") != "validated_complete":
        raise ValueError("M13.4 findings are not validated complete")
    if directed.get("normalization", {}).get("merge_commit") != M13_3_MERGE:
        raise ValueError("M13.4 normalization pin drifted")
    pins = directed.get("source_pins", {})
    if pins.get("project_m12") != PROJECT_M12_BASELINE:
        raise ValueError("M13.4 project baseline pin drifted")
    if pins.get("catalyst_n1") != CATALYST_PIN:
        raise ValueError("M13.4 Catalyst pin drifted")
    if pins.get("brian2loihi") != BRIAN2LOIHI_PIN:
        raise ValueError("M13.4 Brian2Loihi pin drifted")

    dsummary = directed.get("summary", {})
    expected_summary = {
        "probes": 12,
        "agreement": 6,
        "architectural_difference": 3,
        "partial_scope": 1,
        "non_comparable": 2,
        "class_A_or_B": 0,
        "m12_revalidation_required": False,
    }
    for key, value in expected_summary.items():
        if dsummary.get(key) != value:
            raise ValueError(f"M13.4 summary drifted for {key}")

    directed_rows = _rows_by_id(list(directed.get("results", ())), "probe_id")
    if set(directed_rows) != set(EXPECTED_AGREEMENTS) | set(EXPECTED_DIRECTED_RESULTS):
        raise ValueError("M13.4 probe-id set drifted")
    for probe_id in EXPECTED_AGREEMENTS:
        row = directed_rows[probe_id]
        if row.get("status") != "agreement" or row.get("discrepancy_classes") != []:
            raise ValueError(f"M13.4 agreement drifted for {probe_id}")
    for probe_id, (status, classes) in EXPECTED_DIRECTED_RESULTS.items():
        row = directed_rows[probe_id]
        if row.get("status") != status or tuple(row.get("discrepancy_classes", ())) != classes:
            raise ValueError(f"M13.4 adjudication input drifted for {probe_id}")

    harness = list(directed.get("resolved_harness_findings", ()))
    if len(harness) != 2 or any(row.get("class") != "H" for row in harness):
        raise ValueError("M13.4 resolved Class-H findings drifted")
    change = directed.get("change_control", {})
    if change.get("project_baseline_changed") is not False:
        raise ValueError("M13.4 unexpectedly changed project baseline")
    if change.get("m12_evidence_superseded") is not False:
        raise ValueError("M13.4 unexpectedly superseded M12 evidence")

    if hardware.get("schema") != "neuromorphic-twin-m13-hardware-closure-v1":
        raise ValueError("unexpected M13.5 hardware closure schema")
    if hardware.get("status") != "validated_complete":
        raise ValueError("M13.5 hardware closure is not validated complete")
    hpins = hardware.get("source_pins", {})
    if hpins.get("m13_4_main_merge") != M13_4_MERGE:
        raise ValueError("M13.5 M13.4 pin drifted")
    if hpins.get("project_m12_merge") != PROJECT_M12_BASELINE:
        raise ValueError("M13.5 project baseline pin drifted")
    if hpins.get("catalyst_commit") != CATALYST_PIN:
        raise ValueError("M13.5 Catalyst pin drifted")
    if hardware.get("strongest_catalyst_boundary") != "source-supported routed implementation":
        raise ValueError("M13.5 strongest Catalyst boundary drifted")
    if hardware.get("comparison_limits") != {
        "latency_throughput": "withheld",
        "power_energy": "withheld",
        "physical_catalyst_execution": False,
    }:
        raise ValueError("M13.5 comparison limits drifted")
    if hardware.get("routed_timing", {}).get("catalyst") != {"wns_ns": 0.001, "whs_ns": 0.013}:
        raise ValueError("M13.5 Catalyst routed timing drifted")


def build_m13_6_findings(
    crosswalk: Mapping[str, Any],
    directed: Mapping[str, Any],
    hardware: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the deterministic candidate M13.6 findings record."""

    validate_m13_evidence_inputs(crosswalk, directed, hardware)
    drows = _rows_by_id(list(directed["results"]), "probe_id")

    adjudications: list[dict[str, Any]] = []
    experiment_links = {
        "P03-negative-rounding": ["E04"],
        "P06-signed-synaptic-drive": ["E04"],
        "P07-weight-encoding-boundaries": ["E02"],
        "P09-event-multiplicity": ["E05"],
        "P10-recurrent-timing": ["E03"],
        "P11-state-saturation": ["E04"],
    }
    action_by_status = {
        "architectural_difference": "retain_project_baseline_document_difference",
        "partial_scope": "retain_project_baseline_limit_claim_to_common_subset",
        "non_comparable": "retain_project_baseline_withhold_cross_implementation_equality_claim",
    }
    for probe_id in EXPECTED_DIRECTED_RESULTS:
        source = drows[probe_id]
        row: dict[str, Any] = {
            "finding_id": f"D{len(adjudications) + 1:02d}",
            "probe_id": probe_id,
            "status": source["status"],
            "classes": list(source["discrepancy_classes"]),
            "finding": source["finding"],
            "change_control_action": action_by_status[source["status"]],
            "experiment_links": experiment_links[probe_id],
        }
        if "first_divergence" in source:
            row["first_divergence"] = deepcopy(source["first_divergence"])
        adjudications.append(row)

    resolved_harness = [
        {
            "finding_id": f"H{idx:02d}",
            "class": "H",
            "status": "resolved_before_accepted_m13_4_snapshot",
            "issue": source["issue"],
            "resolution": source["resolution"],
            "baseline_effect": "none",
        }
        for idx, source in enumerate(directed["resolved_harness_findings"], start=1)
    ]

    scope_findings = [
        {
            "finding_id": "S01",
            "classes": ["G"],
            "status": "intentional_project_scope_boundary",
            "crosswalk_rows": list(EXPECTED_PROJECT_SCOPE_EXCLUSIONS),
            "finding": (
                "FPGA-v1 intentionally excludes dendritic compartments, general programmable synaptic delays, "
                "native synapse-memory equivalence, inter-core routing/NoC, online learning, Loihi-like management "
                "processors, multicore scaling, and asynchronous/quiescence execution."
            ),
            "change_control_action": "document_scope_do_not_expand_m12_baseline",
        },
        {
            "finding_id": "S02",
            "classes": ["G"],
            "status": "catalyst_physical_execution_not_source_supported",
            "finding": (
                "The pinned Catalyst K26-class source reproduces through routed implementation but does not supply "
                "the complete KV260 board integration needed for attributable physical execution."
            ),
            "strongest_catalyst_boundary": hardware["strongest_catalyst_boundary"],
            "change_control_action": "retain_routed_boundary_do_not_claim_physical_catalyst_execution",
            "experiment_links": ["E06"],
        },
        {
            "finding_id": "S03",
            "classes": ["F"],
            "status": "hardware_metric_comparison_limited",
            "finding": (
                "M13.5 routed timing and resource totals are contextual only because target part strings, configured "
                "capacity, architectural scope, host/debug infrastructure, and execution evidence differ."
            ),
            "withheld": deepcopy(hardware["comparison_limits"]),
            "change_control_action": "withhold_efficiency_fmax_latency_power_and_physical_winner_claims",
            "experiment_links": ["E06"],
        },
    ]

    handoff = [
        {
            "experiment_id": "E01",
            "action": "retain",
            "evidence": ["P01-current-impulse-decay", "P02-voltage-decay", "P04-threshold-boundary", "P05-refractory-release"],
            "guardrail": "Treat altered update ordering as an explicit counterfactual; the validated FPGA-v1 schedule remains the baseline.",
        },
        {
            "experiment_id": "E02",
            "action": "prioritize_common-effective-weight_then_encoding-variant",
            "evidence": ["D03"],
            "guardrail": "Catalyst native encoding is not field-for-field equivalent to the project/Brian2Loihi source encoding; compare delivered effective weight first.",
        },
        {
            "experiment_id": "E03",
            "action": "retain_with_m13_recurrence_context",
            "evidence": ["D05"],
            "guardrail": "Project and Catalyst synchronous recurrence support a one-tick lag; the Brian2Loihi null result is an emulator/modeling finding, not a Loihi ground-truth variant.",
        },
        {
            "experiment_id": "E04",
            "action": "expand_candidate_variants",
            "evidence": ["D01", "D02", "D06"],
            "guardrail": "Alternative negative rounding, sub-rest clamping, and overflow policies are architecture counterfactuals unless stronger Loihi evidence establishes one as normative.",
        },
        {
            "experiment_id": "E05",
            "action": "defer_until_single-factor_variants_are_frozen",
            "evidence": ["D01", "D02", "D03", "D04", "D05", "D06"],
            "guardrail": "Do not combine architecture differences before isolated variants are independently validated.",
        },
        {
            "experiment_id": "E06",
            "action": "use_m13_5_as_context_not_efficiency_baseline",
            "evidence": ["S02", "S03"],
            "guardrail": "Fair FPGA cost experiments should compare controlled project variants on the same target/tool boundary; raw Catalyst totals are contextual only.",
        },
    ]

    return {
        "schema": M13_6_FINDINGS_SCHEMA,
        "status": M13_6_CANDIDATE_STATUS,
        "milestone": "M13.6",
        "source_pins": {
            "m13_5_main_merge": M13_5_MERGE,
            "project_m12_baseline": PROJECT_M12_BASELINE,
            "m13_3_normalization_merge": M13_3_MERGE,
            "m13_4_main_merge": M13_4_MERGE,
            "catalyst_n1": CATALYST_PIN,
            "brian2loihi": BRIAN2LOIHI_PIN,
        },
        "evidence_authorities": {
            "architectural_crosswalk": "references/m13_2_feature_crosswalk.json",
            "directed_findings": "references/m13_4_candidate_findings.json",
            "hardware_closure": "references/m13_5_closure.json",
        },
        "discrepancy_taxonomy": deepcopy(DISCREPANCY_TAXONOMY),
        "summary": {
            "crosswalk_rows": 19,
            "directed_probes": 12,
            "directed_agreements": 6,
            "directed_adjudications": 6,
            "resolved_class_H_harness_findings": 2,
            "class_A_or_B_findings": 0,
            "explicit_project_scope_exclusions": 8,
            "project_baseline_changed": False,
            "m12_revalidation_required": False,
            "strongest_catalyst_hardware_boundary": hardware["strongest_catalyst_boundary"],
        },
        "accepted_agreements": [
            {"probe_id": probe_id, "finding": drows[probe_id]["finding"]}
            for probe_id in EXPECTED_AGREEMENTS
        ],
        "directed_adjudications": adjudications,
        "resolved_harness_findings": resolved_harness,
        "scope_and_comparison_findings": scope_findings,
        "change_control": {
            "trigger_classes": ["A", "B"],
            "observed_trigger_findings": 0,
            "project_baseline_status": "frozen_unchanged",
            "project_baseline_commit": PROJECT_M12_BASELINE,
            "normative_specification_update_required": False,
            "hls_rtl_regeneration_required": False,
            "m12_evidence_superseded": False,
            "m12_physical_revalidation_required": False,
            "reason": (
                "No accepted M13 discrepancy is Class A or B. Classes C-G are retained as architectural, "
                "modeling, ambiguity, normalization, or scope findings; resolved Class-H issues affected only the audit harness."
            ),
        },
        "claim_boundary": {
            "three_way_directed_agreements": list(EXPECTED_AGREEMENTS),
            "qualified_project_catalyst_recurrent_support": {
                "probe_id": "P10-recurrent-timing",
                "source_to_target_spike_lag_ticks": 1,
                "brian2loihi_result": "no target effect observed at the pinned native probe boundary",
            },
            "weight_common_envelope": "13 of 15 project/Brian2Loihi effective-weight cases fit Catalyst signed-int16 and agree exactly",
            "not_claimed_as_universal_loihi_semantics": [
                "project SAT24 overflow/saturation policy",
                "global ordering of coincident spike/event messages",
                "same-source same-tick external event multiplicity across all backends",
                "Catalyst negative CUBA rounding or sub-rest clamp behavior as Loihi ground truth",
                "Brian2Loihi recurrent null behavior as Loihi ground truth",
                "asynchronous/quiescence execution in FPGA-v1",
                "physical Catalyst KV260 execution from the pinned routed-only source boundary",
                "performance or efficiency ranking from M13.5 raw resource/timing totals",
            ],
        },
        "experiment_handoff": handoff,
        "closure_decision": {
            "candidate_m13_result": "freeze_project_baseline_and_document_differences",
            "requires_new_external_or_physical_evidence_before_independent_validation": False,
            "next_gate": "independent local reproduction of M13.6 source-level findings and full regression",
        },
    }


def render_m13_6_findings_markdown(findings: Mapping[str, Any]) -> str:
    """Render a compact, thesis-facing summary of a built findings record."""

    summary = findings["summary"]
    change = findings["change_control"]
    lines = [
        "# M13.6 Candidate Final Findings",
        "",
        f"Status: `{findings['status']}`",
        "",
        "## Audit closure summary",
        "",
        f"- M13.2 architectural rows: {summary['crosswalk_rows']}",
        f"- M13.4 directed probes: {summary['directed_probes']}",
        f"- directed agreements: {summary['directed_agreements']}",
        f"- adjudicated non-agreement/scope probe outcomes: {summary['directed_adjudications']}",
        f"- resolved Class-H harness findings: {summary['resolved_class_H_harness_findings']}",
        f"- Class-A/B findings: {summary['class_A_or_B_findings']}",
        f"- strongest Catalyst hardware boundary: {summary['strongest_catalyst_hardware_boundary']}",
        "",
        "## Change-control decision",
        "",
        f"Project baseline: `{change['project_baseline_status']}` at `{change['project_baseline_commit']}`.",
        "No normative specification change, HLS/RTL regeneration, or M12 physical revalidation is required.",
        "",
        "## Adjudicated directed findings",
        "",
    ]
    for row in findings["directed_adjudications"]:
        classes = ",".join(row["classes"])
        lines.append(f"- **{row['finding_id']} / {row['probe_id']} [{classes}]** — {row['finding']}")
    lines.extend([
        "",
        "## Scope and comparison boundaries",
        "",
    ])
    for row in findings["scope_and_comparison_findings"]:
        classes = ",".join(row["classes"])
        lines.append(f"- **{row['finding_id']} [{classes}]** — {row['finding']}")
    lines.extend([
        "",
        "## M13.6 candidate decision",
        "",
        "Freeze the validated FPGA-v1 project baseline. Preserve the C/D/E/F/G findings and resolved H defects as explicit audit results instead of forcing artificial agreement. Independent local source-level reproduction is the remaining gate before M13.6/M13 are marked complete.",
        "",
    ])
    return "\n".join(lines)


def validate_tracked_m13_6_findings(
    tracked: Mapping[str, Any],
    crosswalk: Mapping[str, Any],
    directed: Mapping[str, Any],
    hardware: Mapping[str, Any],
) -> None:
    """Require a tracked candidate record to equal deterministic regeneration."""

    expected = build_m13_6_findings(crosswalk, directed, hardware)
    if tracked != expected:
        raise ValueError("tracked M13.6 findings do not match deterministic regeneration")
