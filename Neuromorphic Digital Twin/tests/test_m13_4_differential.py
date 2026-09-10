from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuromorphic_twin.comparison.m13_differential import (
    CATALYST_PIN,
    M13_4_DIFFERENTIAL_SCHEMA,
    build_m13_4_common_cases,
    compare_normalized_payloads,
    parse_catalyst_cuba_log,
)


FINDINGS = Path("references/m13_4_candidate_findings.json")
EXPECTED_PROBE_IDS = {
    "P01-current-impulse-decay",
    "P02-voltage-decay",
    "P03-negative-rounding",
    "P04-threshold-boundary",
    "P05-refractory-release",
    "P06-signed-synaptic-drive",
    "P07-weight-encoding-boundaries",
    "P08-fanin-fanout",
    "P09-event-multiplicity",
    "P10-recurrent-timing",
    "P11-state-saturation",
    "P12-simultaneous-spikes",
}


def _cuba_log() -> str:
    positive = [
        (0, 512, 0),
        (1, 256, 512),
        (2, 128, 512),
        (3, 64, 384),
        (4, 32, 256),
    ]
    negative = [
        (0, -64, 0),
        (1, -46, -64),
        (2, -33, -110),
        (3, -23, -143),
    ]
    lines = []
    for case, rows in (("positive", positive), ("negative", negative)):
        for tick, current, voltage in rows:
            lines.append(
                f"M13_4_CUBA|case={case}|native_tick={tick}|current={current}|"
                f"voltage={voltage}|refractory=0|spike=0"
            )
    lines.append("M13_4_CUBA_DONE")
    return "\n".join(lines) + "\n"


def test_m13_4_common_cases_cover_frozen_transforms() -> None:
    cases = build_m13_4_common_cases()
    assert set(cases) == {
        "threshold",
        "refractory",
        "mixed_drive",
        "cuba_positive",
        "cuba_negative",
        "negative_drive",
        "simultaneous",
    }
    assert cases["cuba_positive"].scenario_class == "rtl_cuba_isolated_impulse"
    assert cases["cuba_negative"].scenario_class == "rtl_cuba_isolated_impulse"
    assert cases["threshold"].scenario_class == "cpu_direct_drive"


def test_catalyst_cuba_parser_preserves_native_ticks_and_isolation(tmp_path: Path) -> None:
    path = tmp_path / "native.log"
    path.write_text(_cuba_log(), encoding="utf-8")
    parsed = parse_catalyst_cuba_log(path)

    assert parsed["positive"]["catalyst_commit"] == CATALYST_PIN
    assert parsed["negative"]["catalyst_commit"] == CATALYST_PIN
    assert len(parsed["positive"]["ticks"]) == 5
    assert len(parsed["negative"]["ticks"]) == 4
    assert parsed["negative"]["ticks"][0]["current_after"] == [-64]
    assert parsed["negative"]["ticks"][0]["voltage_after"] == [0]
    assert parsed["negative"]["ticks"][1]["current_after"] == [-46]


def test_catalyst_cuba_parser_fails_closed_on_incomplete_log(tmp_path: Path) -> None:
    path = tmp_path / "native.log"
    path.write_text(_cuba_log().replace("M13_4_CUBA_DONE\n", ""), encoding="utf-8")
    with pytest.raises(ValueError, match="lacks completion marker"):
        parse_catalyst_cuba_log(path)


def test_normalized_comparison_reports_first_divergent_quantity() -> None:
    reference = {
        "ticks": [
            {"canonical_tick": 0, "current_after": [-47], "voltage_after": [-64]},
            {"canonical_tick": 1, "current_after": [-35], "voltage_after": [-111]},
        ]
    }
    catalyst = {
        "ticks": [
            {"canonical_tick": 0, "current_after": [-46], "voltage_after": [-64]},
            {"canonical_tick": 1, "current_after": [-33], "voltage_after": [-110]},
        ]
    }
    result = compare_normalized_payloads(
        reference,
        {"catalyst_rtl_cuba": catalyst},
        fields=("current_after", "voltage_after"),
    )
    assert result.equal is False
    assert result.compared_values == 1
    assert result.first_divergence == {
        "implementation": "catalyst_rtl_cuba",
        "canonical_tick": 0,
        "field": "current_after",
        "reference": [-47],
        "candidate": [-46],
    }


def test_candidate_findings_cover_all_probes_without_ab_change_control() -> None:
    data = json.loads(FINDINGS.read_text(encoding="utf-8"))
    assert data["schema"] == "neuromorphic-twin-m13-directed-findings-v1"
    assert data["status"] == "validated_complete"
    assert data["independent_validation"]["focused_tests_passed"] == 30
    assert data["independent_validation"]["full_project_tests_passed"] == 331
    assert data["independent_validation"]["directed_probe_summary"]["class_A_or_B"] == 0
    assert {row["probe_id"] for row in data["results"]} == EXPECTED_PROBE_IDS
    assert len(data["results"]) == 12
    assert data["summary"] == {
        "probes": 12,
        "agreement": 6,
        "architectural_difference": 3,
        "partial_scope": 1,
        "non_comparable": 2,
        "class_A_or_B": 0,
        "m12_revalidation_required": False,
    }
    classes = {c for row in data["results"] for c in row["discrepancy_classes"]}
    assert not ({"A", "B"} & classes)
    assert data["change_control"]["project_baseline_changed"] is False
    assert data["change_control"]["m12_evidence_superseded"] is False
    assert len(data["resolved_harness_findings"]) == 2
    assert all(item["class"] == "H" for item in data["resolved_harness_findings"])


def test_candidate_findings_pin_the_same_external_baselines() -> None:
    data = json.loads(FINDINGS.read_text(encoding="utf-8"))
    assert data["source_pins"]["catalyst_n1"] == CATALYST_PIN
    assert data["source_pins"]["project_m12"] == "80a502ec6dfc4c8d61372089b08c9a584ad65f85"
    assert data["source_pins"]["brian2loihi"] == "d54676cb113e48dc886615a0b589bb0e4bccbca4"
    assert M13_4_DIFFERENTIAL_SCHEMA == "neuromorphic-twin-m13-directed-differential-v1"
