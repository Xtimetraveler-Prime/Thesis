from __future__ import annotations

from pathlib import Path
import sys

import pytest

from loihi_twin_v2.arithmetic import ArithmeticConfig, OverflowMode
from loihi_twin_v2.compartment import CompartmentConfig, CompartmentState, step_compartment


V1_SRC = Path(__file__).resolve().parents[2] / "v1" / "src"
sys.path.insert(0, str(V1_SRC))

from neuromorphic_twin.arithmetic import ArithmeticConfig as V1ArithmeticConfig  # noqa: E402
from neuromorphic_twin.arithmetic import OverflowMode as V1OverflowMode  # noqa: E402
from neuromorphic_twin.model import NeuronConfig as V1NeuronConfig  # noqa: E402
from neuromorphic_twin.model import NeuronState as V1NeuronState  # noqa: E402
from neuromorphic_twin.neuron import step_neuron as v1_step_neuron  # noqa: E402


@pytest.mark.parametrize(
    "state,config,synaptic_input,arithmetic",
    [
        (CompartmentState(), CompartmentConfig(0, 0, 10), 4, ArithmeticConfig()),
        (CompartmentState(current=9, voltage=3), CompartmentConfig(2048, 1024, 100), -5, ArithmeticConfig()),
        (CompartmentState(), CompartmentConfig(4096, 4096, 5, refractory_ticks=3), 6, ArithmeticConfig()),
        (CompartmentState(current=-7, voltage=-3), CompartmentConfig(1024, 2048, 30, bias=-2), -5, ArithmeticConfig()),
        (CompartmentState(current=7, voltage=7), CompartmentConfig(0, 0, 12), 7, ArithmeticConfig(5, OverflowMode.SATURATE)),
        (CompartmentState(current=7, voltage=7), CompartmentConfig(0, 0, 12), 7, ArithmeticConfig(5, OverflowMode.WRAP)),
        (CompartmentState(current=5, voltage=0, refractory_remaining=2), CompartmentConfig(2048, 0, 10, reset_voltage=-1, refractory_ticks=3), 4, ArithmeticConfig()),
    ],
)
def test_v2_compartment_matches_frozen_v1_neuron_step(state, config, synaptic_input, arithmetic):
    v2_result = step_compartment(state, config, synaptic_input, arithmetic)
    v1_result = v1_step_neuron(
        V1NeuronState(
            current=state.current,
            voltage=state.voltage,
            refractory_remaining=state.refractory_remaining,
        ),
        V1NeuronConfig(
            current_decay=config.current_decay,
            voltage_decay=config.voltage_decay,
            threshold=config.threshold,
            bias=config.bias,
            reset_voltage=config.reset_voltage,
            refractory_ticks=config.refractory_ticks,
        ),
        synaptic_input,
        V1ArithmeticConfig(
            state_bits=arithmetic.state_bits,
            overflow=V1OverflowMode(arithmetic.overflow.value),
        ),
    )
    assert v2_result.spiked == v1_result.spiked
    assert v2_result.state.current == v1_result.state.current
    assert v2_result.state.voltage == v1_result.state.voltage
    assert v2_result.state.refractory_remaining == v1_result.state.refractory_remaining
