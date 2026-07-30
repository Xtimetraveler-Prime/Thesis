"""Single-neuron state transition."""

from __future__ import annotations

from dataclasses import dataclass

from .arithmetic import ArithmeticConfig, round_away_from_zero
from .model import DECAY_SCALE, NeuronConfig, NeuronState


@dataclass(frozen=True, slots=True)
class NeuronStepResult:
    state: NeuronState
    spiked: bool


def _decay(value: int, decay: int) -> int:
    """Return the amount removed from ``value`` during this tick."""

    return round_away_from_zero(value * decay, DECAY_SCALE)


def step_neuron(
    state: NeuronState,
    config: NeuronConfig,
    synaptic_input: int,
    arithmetic: ArithmeticConfig | None = None,
) -> NeuronStepResult:
    """Advance one current-based LIF neuron by one algorithmic tick.

    Loihi-compatible deterministic update contract currently under test:

    1. Add this tick's delivered synaptic input to previous current.
    2. Voltage sees that pre-decay working current.
    3. Decay the working current to obtain stored next current.
    4. During refractory state, hold voltage at reset.
    5. Otherwise decay previous voltage and add working current plus bias.
    6. Test threshold; on a spike, reset voltage and load the number of future
       blocked ticks. The spike tick itself counts toward ``refractory_ticks``,
       so a spike at tick ``t`` is next eligible at
       ``t + refractory_ticks``.
    """

    arithmetic = arithmetic or ArithmeticConfig()

    current_for_voltage = arithmetic.apply(
        state.current + int(synaptic_input)
    )
    next_current = arithmetic.apply(
        current_for_voltage
        - _decay(current_for_voltage, config.current_decay)
    )

    if state.refractory_remaining > 0:
        return NeuronStepResult(
            state=NeuronState(
                current=next_current,
                voltage=arithmetic.apply(config.reset_voltage),
                refractory_remaining=state.refractory_remaining - 1,
            ),
            spiked=False,
        )

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
        refractory = max(config.refractory_ticks - 1, 0)
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
