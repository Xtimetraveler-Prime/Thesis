from neuromorphic_twin import NeuronConfig, NeuromorphicCore, Synapse


def test_one_axon_can_fan_out_to_multiple_neurons() -> None:
    configs = [
        NeuronConfig(current_decay=0, voltage_decay=0, threshold=100),
        NeuronConfig(current_decay=0, voltage_decay=0, threshold=100),
    ]
    core = NeuromorphicCore(
        configs,
        [
            Synapse(axon_id=3, target_neuron=0, weight=4),
            Synapse(axon_id=3, target_neuron=1, weight=-2),
        ],
    )

    trace = core.step([3])
    assert trace.synaptic_input == (4, -2)
    assert trace.current_after == (4, -2)
    assert trace.voltage_after == (4, -2)


def test_repeated_axon_spikes_accumulate_in_same_tick() -> None:
    core = NeuromorphicCore(
        [NeuronConfig(current_decay=0, voltage_decay=0, threshold=100)],
        [Synapse(axon_id=0, target_neuron=0, weight=3)],
    )
    trace = core.step([0, 0])
    assert trace.synaptic_input == (6,)


def test_trace_is_tick_indexed_and_core_reset_is_deterministic() -> None:
    core = NeuromorphicCore(
        [NeuronConfig(current_decay=0, voltage_decay=0, threshold=100)],
        [Synapse(axon_id=0, target_neuron=0, weight=2)],
    )
    first = core.step([0])
    second = core.step([])
    assert first.tick == 0
    assert second.tick == 1

    core.reset()
    replay = core.step([0])
    assert replay == first
