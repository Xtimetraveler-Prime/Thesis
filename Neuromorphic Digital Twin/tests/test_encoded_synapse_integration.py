import json
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
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
    run_brian2loihi_backend_with_weights,
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


def _mixed_group_scenario() -> ComparisonScenario:
    shared_mixed = WeightFormat(
        exponent=2,
        num_weight_bits=6,
        sign_mode=WeightSignMode.MIXED,
    )
    return ComparisonScenario.build(
        name="encoded-adapter-grouping",
        neuron_configs=[_config()],
        synapses=[
            Synapse.encoded(0, 0, -127, shared_mixed),
            Synapse(1, 0, 64),
            Synapse.encoded(2, 0, 125, shared_mixed),
            Synapse(3, 0, -64),
            Synapse.encoded(4, 0, 3, WeightFormat(exponent=1)),
        ],
        input_schedule=[(0, 1, 2, 3, 4)],
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
    scenario = _mixed_group_scenario()

    validate_brian2loihi_scenario(scenario)
    groups = build_brian2loihi_synapse_groups(scenario)

    assert len(groups) == 4

    mixed, legacy_positive, legacy_negative, encoded_positive = groups
    assert mixed.weight_format == WeightFormat(
        exponent=2,
        num_weight_bits=6,
        sign_mode=WeightSignMode.MIXED,
    )
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


def test_generic_backend_restores_w_act_to_scenario_order(monkeypatch) -> None:
    brian2 = ModuleType("brian2")
    brian2.prefs = SimpleNamespace(codegen=SimpleNamespace(target=None))
    brian2.start_scope = lambda: None

    brian2_loihi = ModuleType("brian2_loihi")
    sign_modes = SimpleNamespace(MIXED=1, EXCITATORY=2, INHIBITORY=3)

    class FakeNeuronGroup:
        def __init__(self, size, **kwargs):
            self.I = np.zeros(size, dtype=int)
            self.v = np.zeros(size, dtype=int)

    class FakeSpikeGeneratorGroup:
        def __init__(self, size, indices, times):
            self.size = size
            self.indices = tuple(indices)
            self.times = tuple(times)

    class FakeSynapses:
        def __init__(
            self,
            source,
            target,
            *,
            w_exp,
            sign_mode,
            num_weight_bits,
        ):
            self.w_exp = w_exp
            self.sign_mode = sign_mode
            self.num_weight_bits = num_weight_bits
            self.w_act = np.asarray([], dtype=int)

        def connect(self, *, i, j):
            self.i = tuple(i)
            self.j = tuple(j)

        @property
        def w(self):
            return self._w

        @w.setter
        def w(self, values):
            self._w = np.asarray(values, dtype=int)
            marker = (
                self.w_exp * 1_000
                + self.num_weight_bits * 10_000
                + self.sign_mode * 100_000
            )
            self.w_act = self._w + marker

    class FakeSpikeMonitor:
        def __init__(self, neurons):
            self.i = []

    class FakeNetwork:
        def __init__(self, *objects):
            self.objects = objects

        def run(self, ticks):
            return None

    brian2_loihi.LoihiNetwork = FakeNetwork
    brian2_loihi.LoihiNeuronGroup = FakeNeuronGroup
    brian2_loihi.LoihiSpikeGeneratorGroup = FakeSpikeGeneratorGroup
    brian2_loihi.LoihiSpikeMonitor = FakeSpikeMonitor
    brian2_loihi.LoihiSynapses = FakeSynapses
    brian2_loihi.synapse_sign_mode = sign_modes

    monkeypatch.setitem(sys.modules, "brian2", brian2)
    monkeypatch.setitem(sys.modules, "brian2_loihi", brian2_loihi)

    scenario = _mixed_group_scenario()
    run = run_brian2loihi_backend_with_weights(scenario)

    assert run.effective_weights == (
        -127 + 2_000 + 60_000 + 100_000,
        1 + 80_000 + 200_000,
        125 + 2_000 + 60_000 + 100_000,
        -1 + 80_000 + 300_000,
        3 + 1_000 + 80_000 + 200_000,
    )
    assert dict(run.trace.metadata)["synapse_group_count"] == "4"
    assert run.trace.synapses == run_python_backend(scenario).synapses
