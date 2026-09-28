from neuromorphic_twin import NeuronConfig, NeuronState, step_neuron


def test_neuron_accumulates_current_and_voltage() -> None:
    config = NeuronConfig(
        current_decay=0,
        voltage_decay=0,
        threshold=100,
    )
    result = step_neuron(NeuronState(), config, synaptic_input=7)
    assert result.state.current == 7
    assert result.state.voltage == 7
    assert result.spiked is False


def test_threshold_reset_loads_only_future_refractory_ticks() -> None:
    config = NeuronConfig(
        current_decay=0,
        voltage_decay=0,
        threshold=10,
        reset_voltage=0,
        refractory_ticks=2,
    )

    first = step_neuron(NeuronState(), config, synaptic_input=11)
    assert first.spiked is True
    assert first.state.voltage == 0

    # The spike tick counts as the first configured refractory tick, so only
    # one future tick remains blocked.
    assert first.state.refractory_remaining == 1

    second = step_neuron(first.state, config, synaptic_input=0)
    assert second.spiked is False
    assert second.state.voltage == 0
    assert second.state.refractory_remaining == 0


def test_one_tick_refractory_allows_a_spike_on_the_next_tick() -> None:
    config = NeuronConfig(
        current_decay=4096,
        voltage_decay=0,
        threshold=10,
        reset_voltage=0,
        refractory_ticks=1,
    )

    first = step_neuron(NeuronState(), config, synaptic_input=11)
    assert first.spiked is True
    assert first.state.refractory_remaining == 0

    second = step_neuron(first.state, config, synaptic_input=11)
    assert second.spiked is True
    assert second.state.refractory_remaining == 0


def test_three_tick_refractory_releases_on_tick_three() -> None:
    config = NeuronConfig(
        current_decay=4096,
        voltage_decay=0,
        threshold=10,
        reset_voltage=0,
        refractory_ticks=3,
    )

    tick_0 = step_neuron(NeuronState(), config, synaptic_input=11)
    assert tick_0.spiked is True
    assert tick_0.state.refractory_remaining == 2

    tick_1 = step_neuron(tick_0.state, config, synaptic_input=11)
    assert tick_1.spiked is False
    assert tick_1.state.refractory_remaining == 1

    tick_2 = step_neuron(tick_1.state, config, synaptic_input=11)
    assert tick_2.spiked is False
    assert tick_2.state.refractory_remaining == 0

    tick_3 = step_neuron(tick_2.state, config, synaptic_input=11)
    assert tick_3.spiked is True
    assert tick_3.state.refractory_remaining == 2


def test_refractory_ticks_hold_voltage_but_continue_current_updates() -> None:
    config = NeuronConfig(
        current_decay=0,
        voltage_decay=0,
        threshold=10,
        reset_voltage=0,
        refractory_ticks=3,
    )

    tick_0 = step_neuron(NeuronState(), config, synaptic_input=11)
    assert tick_0.spiked is True
    assert tick_0.state.current == 11
    assert tick_0.state.voltage == 0
    assert tick_0.state.refractory_remaining == 2

    tick_1 = step_neuron(tick_0.state, config, synaptic_input=5)
    assert tick_1.spiked is False
    assert tick_1.state.current == 16
    assert tick_1.state.voltage == 0
    assert tick_1.state.refractory_remaining == 1

    tick_2 = step_neuron(tick_1.state, config, synaptic_input=7)
    assert tick_2.spiked is False
    assert tick_2.state.current == 23
    assert tick_2.state.voltage == 0
    assert tick_2.state.refractory_remaining == 0


def test_release_tick_without_drive_does_not_force_a_spike() -> None:
    config = NeuronConfig(
        current_decay=4096,
        voltage_decay=0,
        threshold=10,
        reset_voltage=0,
        refractory_ticks=3,
    )

    tick_0 = step_neuron(NeuronState(), config, synaptic_input=11)
    tick_1 = step_neuron(tick_0.state, config, synaptic_input=0)
    tick_2 = step_neuron(tick_1.state, config, synaptic_input=0)
    tick_3 = step_neuron(tick_2.state, config, synaptic_input=0)

    assert tick_3.state.refractory_remaining == 0
    assert tick_3.state.voltage == 0
    assert tick_3.spiked is False


def test_decay_rounds_away_from_zero() -> None:
    config = NeuronConfig(
        current_decay=1024,  # 1/4 decay
        voltage_decay=0,
        threshold=100,
    )
    result = step_neuron(
        NeuronState(current=5, voltage=0),
        config,
        synaptic_input=0,
    )
    # ceil(5/4) = 2 is removed, leaving 3.
    assert result.state.current == 3


def test_new_input_is_visible_before_current_decay() -> None:
    config = NeuronConfig(
        current_decay=2048,  # one-half decay
        voltage_decay=0,
        threshold=1000,
    )

    result = step_neuron(
        NeuronState(current=0, voltage=0),
        config,
        synaptic_input=128,
    )

    # Voltage sees the full newly delivered current.
    assert result.state.voltage == 128

    # The stored current is decayed after input delivery.
    assert result.state.current == 64


def test_current_decay_sequence_matches_loihi_order() -> None:
    config = NeuronConfig(
        current_decay=2048,
        voltage_decay=0,
        threshold=10000,
    )

    state = NeuronState()

    first = step_neuron(state, config, synaptic_input=128)
    assert first.state.current == 64

    second = step_neuron(first.state, config, synaptic_input=0)
    assert second.state.current == 32

    third = step_neuron(second.state, config, synaptic_input=0)
    assert third.state.current == 16
