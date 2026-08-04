import json

import pytest

from neuromorphic_twin import (
    NeuronConfig,
    NeuromorphicCore,
    Synapse,
    WeightFormat,
    WeightSignMode,
    encode_static_weight,
)
from neuromorphic_twin.comparison import (
    ComparisonScenario,
    build_brian2loihi_synapse_groups,
    read_trace_json,
    run_python_backend,
    validate_brian2loihi_scenario,
    write_trace_json,
)


def _config() -> NeuronConfig:
    return NeuronConfig(
        current_decay=0,
        voltage_decay=0,
        threshold=1_000_000,
        reset_voltage=0,
        refractory_ticks=1,
    )


def _encoded_synapse() -> Synapse:
    return Synapse.encoded(
        axon_id=0,
        target_neuron=0,
        mantissa=-127,
        weight_format=WeightFormat(
            exponent=2,
            num_weight_bits=6,
            sign_mode=WeightSignMode.MIXED,
        ),
    )


def test_encoded_synapse_preserves_source_format_and_effective_weight() -> None:
    synapse = _encoded_synapse()
    expected = encode_static_weight(
        -127,
        WeightFormat(
            exponent=2,
            num_weight_bits=6,
            sign_mode=WeightSignMode.MIXED,
        ),
    )

    assert synapse.is_encoded
    assert synapse.encoding == expected
    assert synapse.weight == expected.effective_weight


def test_encoded_synapse_rejects_inconsistent_effective_weight() -> None:
    encoding = encode_static_weight(3, WeightFormat(exponent=1))

    with pytest.raises(ValueError, match="encoding.effective_weight"):
        Synapse(
            axon_id=0,
            target_neuron=0,
            weight=encoding.effective_weight + 64,
            encoding=encoding,
        )


def test_encoded_and_integer_synapses_drive_identical_core_path() -> None:
    encoded = Synapse.encoded(0, 0, 124, WeightFormat())
    integer = Synapse(0, 0, encoded.weight)
    encoded_core = NeuromorphicCore([_config()], [encoded])
    integer_core = NeuromorphicCore([_config()], [integer])

    for axons in ((0,), (), (0,)):
        assert encoded_core.step(axons) == integer_core.step(axons)


def test_python_trace_preserves_encoded_synapse_metadata() -> None:
    synapse = _encoded_synapse()
    scenario = ComparisonScenario.build(
        name="encoded-trace-metadata",
        neuron_configs=[_config()],
        synapses=[synapse],
        input_schedule=[(0,), ()],
    )

    trace = run_python_backend(scenario)
    assert len(trace.synapses) == 1
    descriptor = trace.synapses[0]
    assert descriptor.is_encoded
    assert descriptor.axon_id == 0
    assert descriptor.target_neuron == 0
    assert descriptor.effective_weight == synapse.weight
    assert descriptor.requested_mantissa == -127
    assert descriptor.quantized_mantissa == -120
    assert descriptor.exponent == 2
    assert descriptor.num_weight_bits == 6
    assert descriptor.sign_mode == "mixed"
    assert descriptor.clipped is False


def test_trace_v2_json_round_trip_preserves_encoding(tmp_path) -> None:
    scenario = ComparisonScenario.build(
        name="encoded-json-round-trip",
        neuron_configs=[_config()],
        synapses=[_encoded_synapse()],
        input_schedule=[(0,)],
    )
    trace = run_python_backend(scenario)
    path = write_trace_json(trace, tmp_path / "trace.json")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "neuromorphic-twin-trace-v2"
    assert payload["synapses"][0]["encoding"]["requested_mantissa"] == -127
    assert payload["synapses"][0]["encoding"]["sign_mode"] == "mixed"
    assert read_trace_json(path) == trace


def test_trace_v1_json_remains_readable(tmp_path) -> None:
    path = tmp_path / "legacy-trace.json"
    path.write_text(
        json.dumps(
            {
                "schema": "neuromorphic-twin-trace-v1",
                "backend": "legacy",
                "scenario": "legacy-scenario",
                "metadata": {},
                "ticks": [
                    {
                        "tick": 0,
                        "current_before": [0],
                        "voltage_before": [0],
                        "current_after": [64],
                        "voltage_after": [64],
                        "spikes": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    trace = read_trace_json(path)
    assert trace.synapses == ()
    assert trace.ticks[0].current_after == (64,)


def test_generic_brian_adapter_groups_encoded_and_legacy_formats() -> None:
    shared_mixed = WeightFormat(
        exponent=2,
        num_weight_bits=6,
        sign_mode=WeightSignMode.MIXED,
    )
    synapses = [
        Synapse.encoded(0, 0, -127, shared_mixed),
        Synapse(1, 0, 64),
        Synapse.encoded(2, 0, 125, shared_mixed),
        Synapse(3, 0, -64),
        Synapse.encoded(4, 0, 3, WeightFormat(exponent=1)),
    ]
    scenario = ComparisonScenario.build(
        name="encoded-adapter-grouping",
        neuron_configs=[_config()],
        synapses=synapses,
        input_schedule=[(0, 1, 2, 3, 4)],
    )

    validate_brian2loihi_scenario(scenario)
    groups = build_brian2loihi_synapse_groups(scenario)

    assert len(groups) == 4

    mixed, legacy_positive, legacy_negative, encoded_positive = groups
    assert mixed.weight_format == shared_mixed
    assert mixed.scenario_indices == (0, 2)
    assert mixed.axon_ids == (0, 2)
    assert mixed.target_neurons == (0, 0)
    assert mixed.mantissas == (-127, 125)

    assert legacy_positive.weight_format == WeightFormat()
    assert legacy_positive.scenario_indices == (1,)
    assert legacy_positive.mantissas == (1,)

    assert legacy_negative.weight_format == WeightFormat(
        sign_mode=WeightSignMode.INHIBITORY
    )
    assert legacy_negative.scenario_indices == (3,)
    assert legacy_negative.mantissas == (-1,)

    assert encoded_positive.weight_format == WeightFormat(exponent=1)
    assert encoded_positive.scenario_indices == (4,)
    assert encoded_positive.mantissas == (3,)
