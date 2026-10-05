"""Single-compartment v2 execution primitive.

The v2.0 profile intentionally preserves the validated FPGA-v1 neuron-step
arithmetic while placing it behind a new compartment interface. This module has
no runtime dependency on the v1 package.
"""

from __future__ import annotations

from dataclasses import dataclass

from .arithmetic import ArithmeticConfig, round_away_from_zero


DECAY_SCALE = 4096


@dataclass(frozen=True, slots=True)
class CompartmentConfig:
    current_decay: int
    voltage_decay: int
    threshold: int
    bias: int = 0
    reset_voltage: int = 0
    refractory_ticks: int = 0
    parent_compartment: int | None = None
    root_compartment: int | None = None

    def __post_init__(self) -> None:
        for name, value in (("current_decay", self.current_decay), ("voltage_decay", self.voltage_decay)):
            if not 0 <= value <= DECAY_SCALE:
                raise ValueError(f"{name} must be in [0, {DECAY_SCALE}]")
        if self.threshold <= self.reset_voltage:
            raise ValueError("threshold must be greater than reset_voltage")
        if self.refractory_ticks < 0:
            raise ValueError("refractory_ticks cannot be negative")
        if self.parent_compartment is not None and self.parent_compartment < 0:
            raise ValueError("parent_compartment cannot be negative")
        if self.root_compartment is not None and self.root_compartment < 0:
            raise ValueError("root_compartment cannot be negative")


@dataclass(frozen=True, slots=True)
class CompartmentState:
    current: int = 0
    voltage: int = 0
    refractory_remaining: int = 0

    def __post_init__(self) -> None:
        if self.refractory_remaining < 0:
            raise ValueError("refractory_remaining cannot be negative")


@dataclass(frozen=True, slots=True)
class CompartmentStepResult:
    state: CompartmentState
    spiked: bool


def _decay(value: int, decay: int) -> int:
    return round_away_from_zero(value * decay, DECAY_SCALE)


def step_compartment(
    state: CompartmentState,
    config: CompartmentConfig,
    synaptic_input: int,
    arithmetic: ArithmeticConfig | None = None,
) -> CompartmentStepResult:
    """Advance the v2.0 single-compartment compatibility profile by one tick."""

    arithmetic = arithmetic or ArithmeticConfig()
    current_for_voltage = arithmetic.apply(state.current + int(synaptic_input))
    next_current = arithmetic.apply(
        current_for_voltage - _decay(current_for_voltage, config.current_decay)
    )

    if state.refractory_remaining > 0:
        return CompartmentStepResult(
            state=CompartmentState(
                current=next_current,
                voltage=arithmetic.apply(config.reset_voltage),
                refractory_remaining=state.refractory_remaining - 1,
            ),
            spiked=False,
        )

    voltage = state.voltage - _decay(state.voltage, config.voltage_decay)
    voltage = arithmetic.apply(voltage + current_for_voltage + config.bias)
    spiked = voltage > config.threshold
    if spiked:
        voltage = arithmetic.apply(config.reset_voltage)
        refractory = max(config.refractory_ticks - 1, 0)
    else:
        refractory = 0

    return CompartmentStepResult(
        state=CompartmentState(
            current=next_current,
            voltage=voltage,
            refractory_remaining=refractory,
        ),
        spiked=spiked,
    )
