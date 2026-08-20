import pytest

from neuromorphic_twin import (
    NeuronConfig,
    NeuromorphicCore,
    SpikeRoute,
    Synapse,
)
from neuromorphic_twin.comparison.model import ComparisonScenario
from neuromorphic_twin.comparison.io import read_trace_json, write_trace_json
from neuromorphic_twin.comparison.python_backend import run_python_backend


def _config(threshold: int = 5) -> NeuronConfig:
    return NeuronConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=threshold,
    )


def test_output_spike_is_delivered_at_next_tick_boundary() -> None:
    core = NeuromorphicCore(
        [_config(), _config(100)],
        [
            Synapse(axon_id=0, target_neuron=0, weight=6),
            Synapse(axon_id=7, target_neuron=1, weight=3),
        ],
        spike_routes=[SpikeRoute(source_neuron=0, target_axon=7)],
    )

    emitted = core.step([0])
    delivered = core.step()

    assert emitted.synaptic_input == (6, 0)
    assert emitted.recurrent_input_axons == ()
    assert emitted.routed_output_axons == (7,)
    assert delivered.input_axons == (7,)
    assert delivered.external_input_axons == ()
    assert delivered.recurrent_input_axons == (7,)
    assert delivered.synaptic_input == (0, 3)


def test_external_events_precede_recurrent_events_without_merging() -> None:
    core = NeuromorphicCore(
        [_config()],
        [Synapse(axon_id=0, target_neuron=0, weight=6)],
        spike_routes=[SpikeRoute(0, 0)],
    )

    core.step([0])
    trace = core.step([4, 0])

    assert trace.external_input_axons == (4, 0)
    assert trace.recurrent_input_axons == (0,)
    assert trace.input_axons == (4, 0, 0)
    assert trace.synaptic_input == (12,)


def test_simultaneous_spikes_route_in_neuron_and_declaration_order() -> None:
    core = NeuromorphicCore(
        [_config(), _config(), _config(100)],
        [
            Synapse(0, 0, 6),
            Synapse(0, 1, 6),
            Synapse(7, 2, 1),
            Synapse(8, 2, 10),
            Synapse(9, 2, 100),
        ],
        spike_routes=[
            SpikeRoute(1, 9),
            SpikeRoute(0, 8),
            SpikeRoute(0, 7),
        ],
    )

    emitted = core.step([0])
    delivered = core.step()

    assert tuple(spike.neuron_id for spike in emitted.spikes) == (0, 1)
    assert emitted.routed_output_axons == (8, 7, 9)
    assert delivered.recurrent_input_axons == (8, 7, 9)
    assert delivered.synaptic_input == (0, 0, 111)


def test_two_spikes_to_same_axon_preserve_event_multiplicity() -> None:
    core = NeuromorphicCore(
        [_config(), _config(), _config(100)],
        [Synapse(0, 0, 6), Synapse(0, 1, 6), Synapse(6, 2, 4)],
        spike_routes=[SpikeRoute(0, 6), SpikeRoute(1, 6)],
    )

    core.step([0])
    trace = core.step()

    assert trace.recurrent_input_axons == (6, 6)
    assert trace.synaptic_input == (0, 0, 8)


def test_self_recurrent_route_forms_deterministic_tick_chain() -> None:
    core = NeuromorphicCore(
        [_config()],
        [Synapse(0, 0, 6)],
        spike_routes=[SpikeRoute(0, 0)],
    )

    traces = [core.step([0]), core.step(), core.step(), core.step()]

    assert [trace.input_axons for trace in traces] == [(0,), (0,), (0,), (0,)]
    assert [tuple(s.neuron_id for s in trace.spikes) for trace in traces] == [
        (0,),
        (0,),
        (0,),
        (0,),
    ]


def test_reset_discards_pending_recurrent_events() -> None:
    core = NeuromorphicCore(
        [_config()],
        [Synapse(0, 0, 6)],
        spike_routes=[SpikeRoute(0, 0)],
    )

    core.step([0])
    core.reset()
    trace = core.step()

    assert trace.tick == 0
    assert trace.input_axons == ()
    assert trace.recurrent_input_axons == ()
    assert trace.spikes == ()


def test_routes_validate_source_target_and_duplicates() -> None:
    with pytest.raises(ValueError, match="source_neuron"):
        SpikeRoute(-1, 0)
    with pytest.raises(ValueError, match="target_axon"):
        SpikeRoute(0, -1)
    with pytest.raises(ValueError, match="outside"):
        NeuromorphicCore([_config()], spike_routes=[SpikeRoute(1, 0)])
    with pytest.raises(ValueError, match="duplicate"):
        NeuromorphicCore(
            [_config()],
            spike_routes=[SpikeRoute(0, 2), SpikeRoute(0, 2)],
        )


def test_comparison_scenario_runs_recurrent_routes() -> None:
    scenario = ComparisonScenario.build(
        name="recurrent-chain",
        neuron_configs=[_config()],
        synapses=[Synapse(0, 0, 6)],
        spike_routes=[SpikeRoute(0, 0)],
        input_schedule=[(0,), (), ()],
    )

    trace = run_python_backend(scenario)

    assert [tick.spikes for tick in trace.ticks] == [(0,), (0,), (0,)]


def test_routing_trace_v3_round_trip(tmp_path) -> None:
    scenario = ComparisonScenario.build(
        name="routing-trace",
        neuron_configs=[_config()],
        synapses=[Synapse(0, 0, 6)],
        spike_routes=[SpikeRoute(0, 0)],
        input_schedule=[(0,), ()],
    )
    trace = run_python_backend(scenario)

    path = write_trace_json(trace, tmp_path / "trace.json")
    restored = read_trace_json(path)

    assert restored == trace
    assert restored.spike_routes == (SpikeRoute(0, 0),)
    assert restored.ticks[0].routed_output_axons == (0,)
    assert restored.ticks[1].recurrent_input_axons == (0,)
