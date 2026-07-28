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


def test_threshold_reset_and_refractory() -> None:
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
    assert first.state.refractory_remaining == 2

    second = step_neuron(first.state, config, synaptic_input=0)
    assert second.spiked is False
    assert second.state.voltage == 0
    assert second.state.refractory_remaining == 1


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