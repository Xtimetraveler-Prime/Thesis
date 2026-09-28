import pytest

from neuromorphic_twin import (
    ID_BITS,
    ID_MAX,
    REFRACTORY_MAX,
    STATE_MAX,
    STATE_MIN,
    NeuronConfig,
    NeuronState,
    validate_input_axons_v1,
    validate_neuron_state_v1,
)
from neuromorphic_twin.fpga_weight_storage import (
    AXON_ID_BITS,
    MAX_AXON_ID,
    MAX_TARGET_NEURON,
    SYNAPSE_TARGET_BITS,
)


def test_m10_identifier_widths_match_frozen_m08_storage_contract() -> None:
    assert ID_BITS == AXON_ID_BITS == SYNAPSE_TARGET_BITS == 16
    assert ID_MAX == MAX_AXON_ID == MAX_TARGET_NEURON == 65535


def test_runtime_input_axons_obey_v1_width_and_preserve_event_sequence() -> None:
    assert validate_input_axons_v1([0, ID_MAX, 0]) == (0, ID_MAX, 0)

    with pytest.raises(ValueError, match="unsigned 16 bits"):
        validate_input_axons_v1([ID_MAX + 1])
    with pytest.raises(ValueError, match="unsigned 16 bits"):
        validate_input_axons_v1([-1])
    with pytest.raises(TypeError, match="must be ints"):
        validate_input_axons_v1([True])


def test_injected_state_must_fit_frozen_v1_registers() -> None:
    validate_neuron_state_v1(
        NeuronState(
            current=STATE_MIN,
            voltage=STATE_MAX,
            refractory_remaining=REFRACTORY_MAX,
        )
    )

    with pytest.raises(ValueError, match="current"):
        validate_neuron_state_v1(NeuronState(current=STATE_MAX + 1))
    with pytest.raises(ValueError, match="voltage"):
        validate_neuron_state_v1(NeuronState(voltage=STATE_MIN - 1))
    with pytest.raises(ValueError, match="refractory_remaining"):
        validate_neuron_state_v1(
            NeuronState(refractory_remaining=REFRACTORY_MAX + 1)
        )


def test_threshold_must_remain_strictly_above_reset_voltage() -> None:
    with pytest.raises(ValueError, match="threshold must be greater than reset_voltage"):
        NeuronConfig(
            current_decay=0,
            voltage_decay=0,
            threshold=0,
            reset_voltage=0,
        )
