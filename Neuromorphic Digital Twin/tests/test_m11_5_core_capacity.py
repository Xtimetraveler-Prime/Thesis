from __future__ import annotations

import pytest

from neuromorphic_twin.fpga_core_capacity import (
    FPGA_CORE_CAPACITY_SCHEMA,
    FPGA_CORE_CAPACITY_V1,
    MAX_AXONS,
    MAX_EXTERNAL_EVENTS_PER_TICK,
    MAX_NEURONS,
    MAX_RECURRENT_EVENTS_PER_TICK,
    MAX_ROUTES,
    MAX_SYNAPSES,
    NEURON_CONFIG_RESERVED_MASK,
    estimate_fpga_core_storage_v1,
    pack_neuron_config_word,
    pack_neuron_state_word,
    unpack_neuron_config_word,
    unpack_neuron_state_word,
)
from neuromorphic_twin.fpga_weight_storage import MAX_WEIGHT_FORMATS
from neuromorphic_twin.model import NeuronConfig, NeuronState
from neuromorphic_twin.specification import ID_MAX, REFRACTORY_MAX, STATE_MAX, STATE_MIN


def test_m11_5_capacity_profile_is_finite_and_m10_m08_compatible() -> None:
    assert FPGA_CORE_CAPACITY_SCHEMA == "neuromorphic-twin-fpga-core-capacity-v1"
    assert MAX_NEURONS == 256
    assert MAX_AXONS == 1024
    assert MAX_SYNAPSES == 4096
    assert MAX_ROUTES == 4096
    assert MAX_EXTERNAL_EVENTS_PER_TICK == 4096
    assert MAX_RECURRENT_EVENTS_PER_TICK == 4096

    assert FPGA_CORE_CAPACITY_V1.max_neurons <= ID_MAX + 1
    assert FPGA_CORE_CAPACITY_V1.max_axons <= ID_MAX + 1
    assert FPGA_CORE_CAPACITY_V1.max_weight_formats == MAX_WEIGHT_FORMATS == 16


def test_m11_5_capacity_only_storage_estimate_is_locked() -> None:
    estimate = estimate_fpga_core_storage_v1()

    assert estimate.neuron_state_bits == 16_384
    assert estimate.neuron_config_bits == 32_768
    assert estimate.synaptic_accumulator_bits == 16_384
    assert estimate.weight_format_bits == 256
    assert estimate.synapse_bits == 131_072
    assert estimate.axon_row_pointer_bits == 32_800
    assert estimate.route_target_bits == 65_536
    assert estimate.route_row_pointer_bits == 8_224
    assert estimate.external_event_bits == 65_536
    assert estimate.recurrent_event_bits == 131_072
    assert estimate.spike_flag_bits == 256
    assert estimate.total_bits == 500_288
    assert estimate.bram36_lower_bound == 14


def test_m11_5_capacity_validation_rejects_overflow() -> None:
    FPGA_CORE_CAPACITY_V1.validate_image_counts(
        neuron_count=MAX_NEURONS,
        axon_count=MAX_AXONS,
        synapse_count=MAX_SYNAPSES,
        weight_format_count=MAX_WEIGHT_FORMATS,
        route_count=MAX_ROUTES,
    )

    with pytest.raises(ValueError, match="neuron_count"):
        FPGA_CORE_CAPACITY_V1.validate_image_counts(
            neuron_count=MAX_NEURONS + 1,
            axon_count=0,
            synapse_count=0,
            weight_format_count=0,
            route_count=0,
        )

    with pytest.raises(ValueError, match="at least one neuron"):
        FPGA_CORE_CAPACITY_V1.validate_image_counts(
            neuron_count=0,
            axon_count=0,
            synapse_count=0,
            weight_format_count=0,
            route_count=0,
        )


def test_m11_5_neuron_state_word_round_trips_boundaries() -> None:
    cases = (
        NeuronState(current=0, voltage=0, refractory_remaining=0),
        NeuronState(
            current=STATE_MIN,
            voltage=STATE_MAX,
            refractory_remaining=REFRACTORY_MAX,
        ),
        NeuronState(current=-1, voltage=1, refractory_remaining=0x1234),
    )

    for state in cases:
        assert unpack_neuron_state_word(pack_neuron_state_word(state)) == state

    assert (
        pack_neuron_state_word(
            NeuronState(current=-1, voltage=1, refractory_remaining=0x1234)
        )
        == 0x1234000001FFFFFF
    )


def test_m11_5_neuron_config_word_round_trips_boundaries() -> None:
    cases = (
        NeuronConfig(
            current_decay=0,
            voltage_decay=0,
            threshold=1,
            bias=0,
            reset_voltage=0,
            refractory_ticks=0,
        ),
        NeuronConfig(
            current_decay=4096,
            voltage_decay=4096,
            threshold=STATE_MAX,
            bias=STATE_MIN,
            reset_voltage=STATE_MIN,
            refractory_ticks=REFRACTORY_MAX,
        ),
        NeuronConfig(
            current_decay=1,
            voltage_decay=4096,
            threshold=100,
            bias=-2,
            reset_voltage=-3,
            refractory_ticks=0x55AA,
        ),
    )

    for config in cases:
        assert unpack_neuron_config_word(pack_neuron_config_word(config)) == config

    assert (
        pack_neuron_config_word(cases[-1])
        == 0x156ABFFFFF7FFFFF8000192000001
    )


def test_m11_5_config_reserved_bits_are_rejected() -> None:
    config = NeuronConfig(
        current_decay=0,
        voltage_decay=0,
        threshold=1,
        reset_voltage=0,
    )
    valid_word = pack_neuron_config_word(config)
    reserved_bit = NEURON_CONFIG_RESERVED_MASK & -NEURON_CONFIG_RESERVED_MASK
    assert reserved_bit != 0

    with pytest.raises(ValueError, match="reserved bits"):
        unpack_neuron_config_word(valid_word | reserved_bit)
