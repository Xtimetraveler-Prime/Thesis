"""Single-neuron state transition.

This module is intentionally pure: one state + one configuration + one input
produce one next state and one spike flag. Pure transitions are easy to test,
compare with Brian2Loihi, and translate into RTL/HLS later.
"""

from __future__ import annotations

from dataclasses import dataclass

from .arithmetic import ArithmeticConfig, round_away_from_zero
from .model import DECAY_SCALE, NeuronConfig, NeuronState


@dataclass(frozen=True, slots=True)
class NeuronStepResult:
    state: NeuronState
    spiked: bool


def _decay(value: int, decay: int) -> int:
    """Return the amount removed from `value` during this tick."""

    return round_away_from_zero(value * decay, DECAY_SCALE)


def step_neuron(
    state: NeuronState,
    config: NeuronConfig,
    synaptic_input: int,
    arithmetic: ArithmeticConfig | None = None,
) -> NeuronStepResult:
    """Advance one current-based LIF neuron by one algorithmic tick.

    Phase-1 update contract:
      1. Decay the previous synaptic current.
      2. Add all input weights delivered during this tick.
      3. If refractory, hold voltage at reset and decrement the counter.
      4. Otherwise decay voltage and add current plus bias.
      5. Test threshold; on a spike, reset voltage and load refractory count.

    The order is written explicitly because update scheduling is part of a
    neuromorphic architecture. We will verify this contract against
    Brian2Loihi before calling it Loihi-compatible.
    """

    arithmetic = arithmetic or ArithmeticConfig()

    # Synaptic events are applied before the neuron-state update.
    #
    # `current_for_voltage` is the current visible to the voltage equation
    # during this tick. The stored current state is then decayed separately.
    current_for_voltage = arithmetic.apply(
        state.current + int(synaptic_input)
    )

    next_current = arithmetic.apply(
        current_for_voltage
        - _decay(current_for_voltage, config.current_decay)
    )

    if state.refractory_remaining > 0:
        next_state = NeuronState(
            current=next_current,
            voltage=arithmetic.apply(config.reset_voltage),
            refractory_remaining=state.refractory_remaining - 1,
        )
        return NeuronStepResult(state=next_state, spiked=False)

    voltage = state.voltage - _decay(
        state.voltage,
        config.voltage_decay,
    )

    voltage = arithmetic.apply(
        voltage + current_for_voltage + config.bias
    )

    spiked = voltage > config.threshold
    if spiked:
        voltage = arithmetic.apply(config.reset_voltage)
        refractory = config.refractory_ticks
    else:
        refractory = 0

    

    return NeuronStepResult(
        state=NeuronState(
            current=next_current,
            voltage=voltage,
            refractory_remaining=refractory,
        ),
        spiked=spiked,
    )
