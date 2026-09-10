from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuromorphic_twin.comparison.brian2loihi_backend import (
    UnsupportedScenarioError,
    validate_brian2loihi_scenario,
)
from neuromorphic_twin.comparison.conformance import build_directed_cases
from neuromorphic_twin.comparison.m13_directed_probes import (
    M13NormalizationNotFrozen,
    M13_3_EXPECTED_SCHEMA,
    M13_4_REQUIRED_PROBE_CLASSES,
    load_probe_catalog,
    pre_normalization_reuse_names,
    require_frozen_m13_3,
)
from neuromorphic_twin.comparison.model import ComparisonScenario
from neuromorphic_twin.comparison.weight_conformance import build_weight_conformance_cases
from neuromorphic_twin.model import NeuronConfig, SpikeRoute, Synapse


def test_m13_4_catalog_covers_every_planned_probe_class() -> None:
    data = load_probe_catalog()
    assert len(data["probes"]) == 12
    assert M13_4_REQUIRED_PROBE_CLASSES <= {probe["probe_class"] for probe in data["probes"]}
    assert data["summary"]["required_probe_classes_covered"] == len(M13_4_REQUIRED_PROBE_CLASSES)


def test_m13_4_keeps_normalized_comparison_blocked_until_m13_3() -> None:
    data = load_probe_catalog()
    gate = data["normalization_gate"]
    assert gate["state"] == "blocked_m13_3_not_frozen"
    assert gate["normalized_comparison_allowed"] is False
    assert gate["required_schema"] == M13_3_EXPECTED_SCHEMA
    assert all(probe["participation"]["catalyst_n1"] == "blocked_by_m13_3" for probe in data["probes"])


def test_m13_4_catalog_does_not_prejudge_discrepancies() -> None:
    raw = Path("references/m13_4_probe_catalog.json").read_text(encoding="utf-8")
    assert '"discrepancy_class"' not in raw
    assert '"classification"' not in raw
    assert '"verdict"' not in raw


def test_m13_4_reused_project_brian_case_names_exist() -> None:
    data = load_probe_catalog()
    reuse = pre_normalization_reuse_names(data)
    directed = {case.name for case in build_directed_cases()}
    weights = {case.name for case in build_weight_conformance_cases()}
    assert set(reuse["directed_cases"]) <= directed
    assert set(reuse["weight_cases"]) <= weights
    assert len(reuse["directed_cases"]) == 12
    assert len(reuse["weight_cases"]) == 15


def test_m13_4_requires_missing_m13_3_spec_to_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(M13NormalizationNotFrozen, match="not frozen"):
        require_frozen_m13_3(tmp_path / "missing.json")


def test_m13_4_rejects_wrong_or_unfrozen_m13_3_spec(tmp_path: Path) -> None:
    path = tmp_path / "normalization.json"
    path.write_text(json.dumps({"schema": "wrong", "status": "frozen"}), encoding="utf-8")
    with pytest.raises(M13NormalizationNotFrozen, match="unexpected M13.3 schema"):
        require_frozen_m13_3(path)

    path.write_text(json.dumps({"schema": M13_3_EXPECTED_SCHEMA, "status": "draft"}), encoding="utf-8")
    with pytest.raises(M13NormalizationNotFrozen, match="not frozen"):
        require_frozen_m13_3(path)


def test_m13_4_accepts_only_explicitly_frozen_m13_3_spec(tmp_path: Path) -> None:
    path = tmp_path / "normalization.json"
    payload = {"schema": M13_3_EXPECTED_SCHEMA, "status": "frozen", "version": 1}
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert require_frozen_m13_3(path) == payload


def test_brian2loihi_adapter_rejects_unmapped_recurrent_routes() -> None:
    scenario = ComparisonScenario.build(
        name="m13-recurrent-guard",
        neuron_configs=[
            NeuronConfig(
                current_decay=0,
                voltage_decay=0,
                threshold=64,
                refractory_ticks=1,
            )
        ],
        synapses=[Synapse(axon_id=0, target_neuron=0, weight=64)],
        input_schedule=[(0,), ()],
        spike_routes=[SpikeRoute(source_neuron=0, target_axon=0)],
    )
    with pytest.raises(UnsupportedScenarioError, match="does not map ComparisonScenario spike_routes"):
        validate_brian2loihi_scenario(scenario)
