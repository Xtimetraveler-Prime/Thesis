import json

import pytest

from neuromorphic_twin import NeuronConfig, Synapse
from neuromorphic_twin.comparison import (
    BackendTick,
    BackendTrace,
    ComparisonScenario,
    UnsupportedScenarioError,
    compare_traces,
    effective_weight_to_mantissa,
    format_report,
    read_trace_json,
    run_python_backend,
    validate_brian2loihi_scenario,
    write_trace_json,
)


def _trace(backend: str, voltage: int = 7) -> BackendTrace:
    return BackendTrace(
        backend=backend,
        scenario="unit",
        ticks=(
            BackendTick(
                tick=0,
                current_before=(0,),
                voltage_before=(0,),
                current_after=(7,),
                voltage_after=(voltage,),
                spikes=(),
            ),
        ),
    )


def test_equal_traces_pass() -> None:
    report = compare_traces(_trace("reference"), _trace("candidate"))
    assert report.passed
    assert "PASS" in format_report(report)


def test_mismatch_identifies_tick_field_and_neuron() -> None:
    report = compare_traces(_trace("reference"), _trace("candidate", voltage=8))
    assert not report.passed
    assert report.mismatches[0].tick == 0
    assert report.mismatches[0].field == "voltage_after"
    assert report.mismatches[0].neuron_id == 0


def test_python_backend_normalizes_core_trace() -> None:
    scenario = ComparisonScenario.build(
        name="python-backend",
        neuron_configs=[
            NeuronConfig(
                current_decay=0,
                voltage_decay=0,
                threshold=100,
            )
        ],
        synapses=[Synapse(axon_id=0, target_neuron=0, weight=7)],
        input_schedule=[(0,), ()],
    )
    trace = run_python_backend(scenario)
    assert trace.ticks[0].current_after == (7,)
    assert trace.ticks[1].voltage_after == (14,)


def test_trace_json_round_trip(tmp_path) -> None:
    original = _trace("backend")
    output = write_trace_json(original, tmp_path / "trace.json")
    assert read_trace_json(output) == original
    payload = json.loads(output.read_text())
    assert payload["schema"] == "neuromorphic-twin-trace-v3"


def test_loihi_mapping_uses_sixty_four_unit_weight_steps() -> None:
    assert effective_weight_to_mantissa(128) == 2
    assert effective_weight_to_mantissa(-64) == -1
    with pytest.raises(UnsupportedScenarioError):
        effective_weight_to_mantissa(65)


def test_loihi_adapter_rejects_bias_and_duplicate_input_events() -> None:
    biased = ComparisonScenario.build(
        name="biased",
        neuron_configs=[
            NeuronConfig(
                current_decay=0,
                voltage_decay=0,
                threshold=256,
                bias=1,
                refractory_ticks=1,
            )
        ],
        input_schedule=[()],
    )
    with pytest.raises(UnsupportedScenarioError, match="bias"):
        validate_brian2loihi_scenario(biased)

    duplicate = ComparisonScenario.build(
        name="duplicate",
        neuron_configs=[
            NeuronConfig(
                current_decay=0,
                voltage_decay=0,
                threshold=256,
                refractory_ticks=1,
            )
        ],
        synapses=[Synapse(axon_id=0, target_neuron=0, weight=64)],
        input_schedule=[(0, 0)],
    )
    with pytest.raises(UnsupportedScenarioError, match="repeats"):
        validate_brian2loihi_scenario(duplicate)
