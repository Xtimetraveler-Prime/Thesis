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


def test_one_tick_refractory_core_can_spike_on_consecutive_ticks() -> None:
    core = NeuromorphicCore(
        [
            NeuronConfig(
                current_decay=4096,
                voltage_decay=0,
                threshold=256,
                refractory_ticks=1,
            )
        ],
        [Synapse(axon_id=0, target_neuron=0, weight=320)],
    )

    traces = [core.step([0]) for _ in range(4)]
    spike_ticks = [
        trace.tick
        for trace in traces
        if tuple(spike.neuron_id for spike in trace.spikes) == (0,)
    ]

    assert spike_ticks == [0, 1, 2, 3]


def test_three_tick_refractory_core_spikes_every_third_tick() -> None:
    core = NeuromorphicCore(
        [
            NeuronConfig(
                current_decay=4096,
                voltage_decay=0,
                threshold=256,
                refractory_ticks=3,
            )
        ],
        [Synapse(axon_id=0, target_neuron=0, weight=320)],
    )

    traces = [core.step([0]) for _ in range(7)]
    spike_ticks = [
        trace.tick
        for trace in traces
        if tuple(spike.neuron_id for spike in trace.spikes) == (0,)
    ]

    assert spike_ticks == [0, 3, 6]
