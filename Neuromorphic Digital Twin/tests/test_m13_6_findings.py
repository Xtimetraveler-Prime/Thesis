from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from neuromorphic_twin.m13_findings import (
    BRIAN2LOIHI_PIN,
    CATALYST_PIN,
    EXPECTED_PROJECT_SCOPE_EXCLUSIONS,
    M13_6_CANDIDATE_STATUS,
    M13_6_FINDINGS_SCHEMA,
    PROJECT_M12_BASELINE,
    build_m13_6_findings,
    render_m13_6_findings_markdown,
    validate_m13_evidence_inputs,
    validate_tracked_m13_6_findings,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return json.loads((ROOT / "references" / name).read_text(encoding="utf-8"))


def _inputs() -> tuple[dict, dict, dict]:
    return (
        _load("m13_2_feature_crosswalk.json"),
        _load("m13_4_candidate_findings.json"),
        _load("m13_5_closure.json"),
    )


def test_build_freezes_zero_ab_change_control_result() -> None:
    findings = build_m13_6_findings(*_inputs())

    assert findings["schema"] == M13_6_FINDINGS_SCHEMA
    assert findings["status"] == M13_6_CANDIDATE_STATUS
    assert findings["summary"] == {
        "crosswalk_rows": 19,
        "directed_probes": 12,
        "directed_agreements": 6,
        "directed_adjudications": 6,
        "resolved_class_H_harness_findings": 2,
        "class_A_or_B_findings": 0,
        "explicit_project_scope_exclusions": 8,
        "project_baseline_changed": False,
        "m12_revalidation_required": False,
        "strongest_catalyst_hardware_boundary": "source-supported routed implementation",
    }
    assert findings["source_pins"]["project_m12_baseline"] == PROJECT_M12_BASELINE
    assert findings["source_pins"]["catalyst_n1"] == CATALYST_PIN
    assert findings["source_pins"]["brian2loihi"] == BRIAN2LOIHI_PIN
    assert findings["change_control"]["observed_trigger_findings"] == 0
    assert findings["change_control"]["project_baseline_status"] == "frozen_unchanged"
    assert findings["change_control"]["normative_specification_update_required"] is False
    assert findings["change_control"]["hls_rtl_regeneration_required"] is False
    assert findings["change_control"]["m12_physical_revalidation_required"] is False


def test_directed_adjudications_preserve_probe_classes() -> None:
    findings = build_m13_6_findings(*_inputs())
    rows = {row["probe_id"]: row for row in findings["directed_adjudications"]}

    assert {probe: row["classes"] for probe, row in rows.items()} == {
        "P03-negative-rounding": ["C"],
        "P06-signed-synaptic-drive": ["C"],
        "P07-weight-encoding-boundaries": ["C", "G"],
        "P09-event-multiplicity": ["G"],
        "P10-recurrent-timing": ["D"],
        "P11-state-saturation": ["E", "G"],
    }
    assert rows["P03-negative-rounding"]["first_divergence"]["project_and_brian2loihi"] == [-47]
    assert rows["P03-negative-rounding"]["first_divergence"]["catalyst_rtl_cuba"] == [-46]
    assert rows["P06-signed-synaptic-drive"]["first_divergence"]["project_and_brian2loihi"] == [-128]
    assert rows["P06-signed-synaptic-drive"]["first_divergence"]["catalyst_cpu_sync"] == [0]
    assert rows["P10-recurrent-timing"]["first_divergence"] == {
        "field": "source_spike_to_target_spike_lag",
        "project_fpga_v1": 1,
        "catalyst_cpu_sync": 1,
        "brian2loihi_0_5_2": None,
    }


def test_resolved_harness_findings_cannot_mutate_baseline() -> None:
    findings = build_m13_6_findings(*_inputs())
    rows = findings["resolved_harness_findings"]

    assert [row["finding_id"] for row in rows] == ["H01", "H02"]
    assert all(row["class"] == "H" for row in rows)
    assert all(row["status"] == "resolved_before_accepted_m13_4_snapshot" for row in rows)
    assert all(row["baseline_effect"] == "none" for row in rows)


def test_scope_and_hardware_limits_are_explicit() -> None:
    findings = build_m13_6_findings(*_inputs())
    rows = {row["finding_id"]: row for row in findings["scope_and_comparison_findings"]}

    assert tuple(rows["S01"]["crosswalk_rows"]) == EXPECTED_PROJECT_SCOPE_EXCLUSIONS
    assert rows["S02"]["strongest_catalyst_boundary"] == "source-supported routed implementation"
    assert rows["S03"]["withheld"] == {
        "latency_throughput": "withheld",
        "power_energy": "withheld",
        "physical_catalyst_execution": False,
    }
    assert "performance or efficiency ranking" in findings["claim_boundary"]["not_claimed_as_universal_loihi_semantics"][-1]


def test_experiment_handoff_covers_registry_without_promoting_status() -> None:
    findings = build_m13_6_findings(*_inputs())
    rows = {row["experiment_id"]: row for row in findings["experiment_handoff"]}

    assert set(rows) == {"E01", "E02", "E03", "E04", "E05", "E06"}
    assert rows["E02"]["evidence"] == ["D03"]
    assert rows["E03"]["evidence"] == ["D05"]
    assert rows["E04"]["evidence"] == ["D01", "D02", "D06"]
    assert rows["E06"]["evidence"] == ["S02", "S03"]
    assert rows["E05"]["action"] == "defer_until_single-factor_variants_are_frozen"


def test_rendered_summary_states_remaining_independent_gate() -> None:
    findings = build_m13_6_findings(*_inputs())
    markdown = render_m13_6_findings_markdown(findings)

    assert "Class-A/B findings: 0" in markdown
    assert PROJECT_M12_BASELINE in markdown
    assert "No normative specification change, HLS/RTL regeneration, or M12 physical revalidation is required." in markdown
    assert "Independent local source-level reproduction is the remaining gate" in markdown


def test_class_ab_drift_is_rejected() -> None:
    crosswalk, directed, hardware = _inputs()
    directed = deepcopy(directed)
    directed["summary"]["class_A_or_B"] = 1
    directed["summary"]["m12_revalidation_required"] = True

    with pytest.raises(ValueError, match="M13.4 summary drifted"):
        validate_m13_evidence_inputs(crosswalk, directed, hardware)


def test_hardware_claim_boundary_drift_is_rejected() -> None:
    crosswalk, directed, hardware = _inputs()
    hardware = deepcopy(hardware)
    hardware["comparison_limits"]["physical_catalyst_execution"] = True

    with pytest.raises(ValueError, match="M13.5 comparison limits drifted"):
        build_m13_6_findings(crosswalk, directed, hardware)


def test_tracked_candidate_matches_deterministic_regeneration() -> None:
    tracked = _load("m13_6_findings.json")
    validate_tracked_m13_6_findings(tracked, *_inputs())
