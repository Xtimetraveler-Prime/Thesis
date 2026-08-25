from __future__ import annotations

from pathlib import Path

import pytest

from neuromorphic_twin.fpga_core_capacity import (
    FPGA_CORE_CAPACITY_V1,
    pack_neuron_config_word,
    pack_neuron_state_word,
    unpack_neuron_state_word,
)
from neuromorphic_twin.model import NeuronConfig, NeuronState
from neuromorphic_twin.neuron_array_reference import step_packed_neuron_array_v1


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1" / "neuron_array_controller_v1.sv"
RUNNER = ROOT / "rtl" / "core_v1" / "run_m11_5_2_sim.sh"


def test_packed_neuron_array_matches_frozen_neuron_semantics() -> None:
    states = (
        NeuronState(current=0, voltage=0, refractory_remaining=0),
        NeuronState(current=5, voltage=7, refractory_remaining=0),
        NeuronState(current=0, voltage=0, refractory_remaining=0),
    )
    configs = (
        NeuronConfig(
            current_decay=0,
            voltage_decay=0,
            threshold=100,
            reset_voltage=0,
        ),
        NeuronConfig(
            current_decay=2048,
            voltage_decay=0,
            threshold=10,
            reset_voltage=0,
            refractory_ticks=3,
        ),
        NeuronConfig(
            current_decay=2048,
            voltage_decay=0,
            threshold=100,
            reset_voltage=-100,
        ),
    )

    result = step_packed_neuron_array_v1(
        tuple(pack_neuron_state_word(state) for state in states),
        tuple(pack_neuron_config_word(config) for config in configs),
        (10, 5, -3),
    )

    assert tuple(unpack_neuron_state_word(word) for word in result.state_words) == (
        NeuronState(current=10, voltage=10, refractory_remaining=0),
        NeuronState(current=5, voltage=0, refractory_remaining=2),
        NeuronState(current=-1, voltage=-3, refractory_remaining=0),
    )
    assert result.spikes == (False, True, False)


def test_packed_neuron_array_rejects_invalid_shapes_and_accumulator_width() -> None:
    state = pack_neuron_state_word(NeuronState())
    config = pack_neuron_config_word(
        NeuronConfig(
            current_decay=0,
            voltage_decay=0,
            threshold=1,
            reset_voltage=0,
        )
    )

    with pytest.raises(ValueError, match="at least one neuron"):
        step_packed_neuron_array_v1((), (), ())
    with pytest.raises(ValueError, match="config_words length"):
        step_packed_neuron_array_v1((state,), (), (0,))
    with pytest.raises(ValueError, match="synaptic_inputs length"):
        step_packed_neuron_array_v1((state,), (config,), ())
    with pytest.raises(ValueError, match="signed 64 bits"):
        step_packed_neuron_array_v1((state,), (config,), (1 << 63,))
    with pytest.raises(TypeError, match="synaptic inputs"):
        step_packed_neuron_array_v1((state,), (config,), (True,))


def test_packed_neuron_array_enforces_physical_neuron_capacity() -> None:
    state = pack_neuron_state_word(NeuronState())
    config = pack_neuron_config_word(
        NeuronConfig(
            current_decay=0,
            voltage_decay=0,
            threshold=1,
            reset_voltage=0,
        )
    )
    count = FPGA_CORE_CAPACITY_V1.max_neurons + 1

    with pytest.raises(ValueError, match="physical capacity"):
        step_packed_neuron_array_v1(
            (state,) * count,
            (config,) * count,
            (0,) * count,
        )


def test_m11_5_2_rtl_freezes_memory_and_handshake_boundaries() -> None:
    text = RTL.read_text(encoding="utf-8")

    assert "parameter integer MAX_NEURONS = 256" in text
    assert "logic [63:0]  neuron_state_mem" in text
    assert "logic [127:0] neuron_config_mem" in text
    assert "logic signed [63:0] synaptic_accum_mem" in text
    assert "(controller_state == S_HLS_WAIT_READY) && !hls_ap_ready;" in text
    assert "if (hls_ap_done)" in text
    assert "result_valid != 4'b1111" in text
    assert "if (!busy)" in text
    assert "tick             <= tick + 32'd1;" in text


def test_m11_5_2_vendor_simulation_runner_is_source_controlled() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    assert 'EXPECTED_VERSION="2025.2"' in text
    assert "xvlog --sv" in text
    assert "xelab tb_neuron_array_controller_v1" in text
    assert 'xsim "$SNAPSHOT"' in text
