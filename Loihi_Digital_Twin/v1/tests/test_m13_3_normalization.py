from __future__ import annotations

from pathlib import Path

import pytest

from neuromorphic_twin.comparison.m13_normalization import (
    M13NormalizationError,
    M13_3_SCHEMA,
    M13_NORMALIZED_TRACE_SCHEMA,
    M13_CATALYST_NATIVE_TRACE_SCHEMA,
    backend_trace_to_normalized_payload,
    build_catalyst_cpu_native_plan,
    build_catalyst_rtl_cuba_native_plan,
    build_small_translation_corpus,
    canonical_decay_to_catalyst_rtl,
    canonical_effective_weight_to_brian_mantissa,
    canonical_effective_weight_to_catalyst,
    canonical_refractory_to_catalyst,
    canonical_threshold_to_brian_mantissa,
    canonical_threshold_to_catalyst,
    catalyst_cpu_native_to_normalized_payload,
    catalyst_cuba_native_tick_for_canonical,
    catalyst_rtl_cuba_native_to_normalized_payload,
    catalyst_threshold_to_canonical,
    collapse_external_drive,
    load_normalization_spec,
)
from neuromorphic_twin.comparison.model import BackendTick, BackendTrace, ComparisonScenario
from neuromorphic_twin.model import NeuronConfig, Synapse


EXPECTED_PINS = {
    "project_m12_baseline": "80a502ec6dfc4c8d61372089b08c9a584ad65f85",
    "m13_2_crosswalk_merge": "49ab7be6dfce427979622b585165b59bbbfbc2da",
    "catalyst_n1": "1806bb4b4114d7671e5648fa75b7b83b3a8d5543",
    "brian2loihi": "d54676cb113e48dc886615a0b589bb0e4bccbca4",
}


def _cases_by_name():
    return {case.name: case for case in build_small_translation_corpus()}


def test_frozen_spec_identity_and_source_pins() -> None:
    spec = load_normalization_spec()
    assert spec["schema"] == M13_3_SCHEMA
    assert spec["status"] == "frozen"
    assert spec["version"] == 1
    assert spec["source_pins"] == EXPECTED_PINS
    assert set(spec["comparison_categories"]) == {
        "exact",
        "transformed",
        "qualitative",
        "non_comparable",
    }


def test_spec_does_not_adjudicate_m13_discrepancies() -> None:
    raw = Path("references/m13_3_normalization_spec.json").read_text(encoding="utf-8")
    assert '"discrepancy_class"' not in raw
    assert '"classification"' not in raw
    assert '"verdict"' not in raw
    assert '"baseline_mutation"' not in raw


def test_small_translation_corpus_is_frozen() -> None:
    cases = build_small_translation_corpus()
    assert [(case.name, case.scenario_class) for case in cases] == [
        ("m13-3-threshold-boundary", "cpu_direct_drive"),
        ("m13-3-refractory-release", "cpu_direct_drive"),
        ("m13-3-signed-drive", "cpu_direct_drive"),
        ("m13-3-isolated-cuba-decay", "rtl_cuba_isolated_impulse"),
    ]


def test_threshold_transforms_are_algebraically_inverse() -> None:
    assert canonical_threshold_to_brian_mantissa(256) == 4
    assert canonical_threshold_to_catalyst(256) == 257
    assert catalyst_threshold_to_canonical(257) == 256

    with pytest.raises(M13NormalizationError, match="multiple of 64"):
        canonical_threshold_to_catalyst(255)
    with pytest.raises(M13NormalizationError, match="multiple of 64"):
        canonical_threshold_to_brian_mantissa(257)
    with pytest.raises(M13NormalizationError):
        canonical_threshold_to_catalyst(32768)


def test_refractory_transform_uses_semantic_next_eligible_tick() -> None:
    assert canonical_refractory_to_catalyst(1) == 0
    assert canonical_refractory_to_catalyst(3) == 2
    assert canonical_refractory_to_catalyst(64) == 63
    with pytest.raises(M13NormalizationError):
        canonical_refractory_to_catalyst(0)
    with pytest.raises(M13NormalizationError):
        canonical_refractory_to_catalyst(65)


def test_effective_weight_transforms_preserve_integer_drive() -> None:
    assert canonical_effective_weight_to_brian_mantissa(320) == 5
    assert canonical_effective_weight_to_brian_mantissa(-64) == -1
    assert canonical_effective_weight_to_catalyst(320) == 320
    assert canonical_effective_weight_to_catalyst(-16384) == -16384

    with pytest.raises(M13NormalizationError, match="divisible by 64"):
        canonical_effective_weight_to_brian_mantissa(65)
    with pytest.raises(M13NormalizationError, match="mantissa"):
        canonical_effective_weight_to_brian_mantissa(16384)
    with pytest.raises(M13NormalizationError, match="signed int16"):
        canonical_effective_weight_to_catalyst(32768)


def test_catalyst_rtl_decay_domain_and_tick_alignment() -> None:
    assert canonical_decay_to_catalyst_rtl(0) == 0
    assert canonical_decay_to_catalyst_rtl(2048) == 2048
    assert canonical_decay_to_catalyst_rtl(4095) == 4095
    with pytest.raises(M13NormalizationError, match="12-bit"):
        canonical_decay_to_catalyst_rtl(4096)

    assert catalyst_cuba_native_tick_for_canonical(0) == 1
    assert catalyst_cuba_native_tick_for_canonical(7) == 8
    with pytest.raises(M13NormalizationError):
        catalyst_cuba_native_tick_for_canonical(-1)


def test_signed_drive_collapse_is_exact_and_preserves_multiplicity() -> None:
    case = _cases_by_name()["m13-3-signed-drive"]
    assert collapse_external_drive(case.scenario) == ((128,), (0,))

    repeated = ComparisonScenario.build(
        name="repeat-collapse",
        neuron_configs=[
            NeuronConfig(
                current_decay=4096,
                voltage_decay=0,
                threshold=4096,
                reset_voltage=0,
                refractory_ticks=1,
            )
        ],
        synapses=[Synapse(0, 0, 64)],
        input_schedule=[(0, 0)],
    )
    assert collapse_external_drive(repeated) == ((128,),)


def test_threshold_cpu_plan_freezes_t_plus_one_and_direct_drive() -> None:
    case = _cases_by_name()["m13-3-threshold-boundary"]
    plan = build_catalyst_cpu_native_plan(case)
    assert plan["backend"] == "catalyst_cpu_sync"
    assert plan["neuron_params"] == [
        {"threshold": 257, "leak": 0, "resting": 0, "refrac": 0}
    ]
    assert plan["direct_current_schedule"] == [[256], [64]]
    assert plan["normalization"]["current"] == "non_comparable"


def test_refractory_cpu_plan_freezes_r_minus_one() -> None:
    case = _cases_by_name()["m13-3-refractory-release"]
    plan = build_catalyst_cpu_native_plan(case)
    assert plan["neuron_params"][0]["threshold"] == 257
    assert plan["neuron_params"][0]["refrac"] == 2
    assert plan["direct_current_schedule"][:4] == [[320], [320], [320], [320]]


def test_cpu_direct_drive_rejects_non_equivalent_decay_configuration() -> None:
    scenario = ComparisonScenario.build(
        name="bad-cpu-decay",
        neuron_configs=[
            NeuronConfig(
                current_decay=2048,
                voltage_decay=0,
                threshold=256,
                reset_voltage=0,
                refractory_ticks=1,
            )
        ],
        synapses=[Synapse(0, 0, 64)],
        input_schedule=[(0,)],
    )
    from neuromorphic_twin.comparison.m13_normalization import M13CommonCase

    case = M13CommonCase(
        name=scenario.name,
        scenario_class="cpu_direct_drive",
        question="must reject hidden persistent current",
        scenario=scenario,
    )
    with pytest.raises(M13NormalizationError, match="current_decay=4096"):
        build_catalyst_cpu_native_plan(case)


def test_isolated_cuba_plan_freezes_decay_threshold_and_warmup() -> None:
    case = _cases_by_name()["m13-3-isolated-cuba-decay"]
    plan = build_catalyst_rtl_cuba_native_plan(case)
    params = plan["neuron_params"][0]
    assert params["threshold"] == 8193
    assert params["decay_u_param_id_17"] == 2048
    assert params["decay_v_param_id_16"] == 2048
    assert params["refrac_absolute"] == 0
    assert plan["required_settings"]["scale_u_enable"] is False
    assert plan["normalization"]["warmup_native_ticks"] == 1
    assert plan["ext_current_schedule"] == [[512], [0], [0], [0]]


def test_isolated_cuba_plan_rejects_later_external_input() -> None:
    from neuromorphic_twin.comparison.m13_normalization import M13CommonCase

    scenario = ComparisonScenario.build(
        name="bad-cuba-schedule",
        neuron_configs=[
            NeuronConfig(
                current_decay=2048,
                voltage_decay=2048,
                threshold=8192,
                reset_voltage=0,
                refractory_ticks=1,
            )
        ],
        synapses=[Synapse(0, 0, 512)],
        input_schedule=[(0,), (0,)],
    )
    case = M13CommonCase(
        name=scenario.name,
        scenario_class="rtl_cuba_isolated_impulse",
        question="later input must not be hidden by tick shift",
        scenario=scenario,
    )
    with pytest.raises(M13NormalizationError, match="no external input after tick 0"):
        build_catalyst_rtl_cuba_native_plan(case)


def test_catalyst_cpu_normalization_marks_current_non_comparable() -> None:
    native = {
        "schema": M13_CATALYST_NATIVE_TRACE_SCHEMA,
        "backend": "catalyst_cpu_sync",
        "profile": "direct-current-equivalent",
        "scenario": "x",
        "ticks": [
            {
                "native_tick": 0,
                "direct_current": [256],
                "potential_before": [0],
                "refractory_before": [0],
                "potential_after": [256],
                "refractory_after": [0],
                "spikes": [],
            }
        ],
    }
    normalized = catalyst_cpu_native_to_normalized_payload(native)
    assert normalized["schema"] == M13_NORMALIZED_TRACE_SCHEMA
    assert normalized["ticks"][0]["current_after"] is None
    assert normalized["ticks"][0]["voltage_after"] == [256]
    assert normalized["ticks"][0]["canonical_tick"] == 0


def test_catalyst_cuba_normalization_drops_only_frozen_warmup_tick() -> None:
    native = {
        "scenario": "cuba",
        "ticks": [
            {
                "native_tick": 0,
                "current_after": [512],
                "voltage_after": [0],
                "spikes": [],
            },
            {
                "native_tick": 1,
                "current_after": [256],
                "voltage_after": [512],
                "spikes": [],
            },
            {
                "native_tick": 2,
                "current_after": [128],
                "voltage_after": [512],
                "spikes": [],
            },
        ],
    }
    normalized = catalyst_rtl_cuba_native_to_normalized_payload(native)
    assert [tick["canonical_tick"] for tick in normalized["ticks"]] == [0, 1]
    assert [tick["native_tick"] for tick in normalized["ticks"]] == [1, 2]
    assert normalized["ticks"][0]["current_after"] == [256]
    assert normalized["ticks"][0]["voltage_after"] == [512]


def test_backend_trace_normalization_preserves_native_tick_and_state() -> None:
    trace = BackendTrace(
        backend="fake",
        scenario="trace",
        ticks=(
            BackendTick(
                tick=0,
                current_before=(0,),
                voltage_before=(0,),
                current_after=(64,),
                voltage_after=(128,),
                spikes=(),
            ),
        ),
    )
    normalized = backend_trace_to_normalized_payload(
        trace,
        implementation="project_fpga_v1",
        profile="comparison-scenario",
    )
    assert normalized["ticks"] == [
        {
            "canonical_tick": 0,
            "native_tick": 0,
            "current_after": [64],
            "voltage_after": [128],
            "refractory_after": None,
            "spikes": [],
        }
    ]
