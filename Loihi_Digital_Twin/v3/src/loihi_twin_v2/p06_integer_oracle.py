"""Independent P06-A2.1 scalar oracle for the accepted P03 integer LIF contract.

This module intentionally does NOT import the existing arithmetic/compartment,
LogicalChip, compiler, or hardware-image modules. Those are differential-test
subjects, not sources of numerical results for this reference.

Scope: one neuron update and the signed 64-bit synaptic accumulator. Packet
routing, input encoding, per-image reset and network readout belong to later
P06-A2 gates. This is NOT an FPGA execution or a trained classifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


STATE_BITS = 24
STATE_MIN = -(1 << (STATE_BITS - 1))
STATE_MAX = (1 << (STATE_BITS - 1)) - 1
ACC_BITS = 64
ACC_MIN = -(1 << (ACC_BITS - 1))
ACC_MAX = (1 << (ACC_BITS - 1)) - 1
DECAY_DENOMINATOR = 4096
REFRACTORY_MAX = (1 << 16) - 1


def _require_int(name: str, value: int) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer, not {type(value).__name__}")


def _check_range(name: str, value: int, low: int, high: int) -> None:
    _require_int(name, value)
    if not low <= value <= high:
        raise ValueError(f"{name} must be in [{low}, {high}]")


@dataclass(frozen=True, slots=True)
class LIFParameters:
    current_decay: int
    voltage_decay: int
    threshold: int
    bias: int = 0
    reset_voltage: int = 0
    refractory_ticks: int = 0

    def __post_init__(self) -> None:
        _check_range("current_decay", self.current_decay, 0, DECAY_DENOMINATOR)
        _check_range("voltage_decay", self.voltage_decay, 0, DECAY_DENOMINATOR)
        for name in ("threshold", "bias", "reset_voltage"):
            _check_range(name, getattr(self, name), STATE_MIN, STATE_MAX)
        _check_range("refractory_ticks", self.refractory_ticks, 0, REFRACTORY_MAX)
        if self.threshold <= self.reset_voltage:
            raise ValueError("threshold must exceed reset_voltage")


@dataclass(frozen=True, slots=True)
class LIFState:
    current: int = 0
    voltage: int = 0
    refractory_remaining: int = 0

    def __post_init__(self) -> None:
        _check_range("current", self.current, STATE_MIN, STATE_MAX)
        _check_range("voltage", self.voltage, STATE_MIN, STATE_MAX)
        _check_range("refractory_remaining", self.refractory_remaining, 0, REFRACTORY_MAX)


@dataclass(frozen=True, slots=True)
class LIFStep:
    state: LIFState
    spiked: bool
    current_work: int
    voltage_pre_threshold: int | None


def saturate24(value: int) -> int:
    """Clamp a wide signed intermediate to one 24-bit signed state value."""
    _require_int("value", value)
    if value < STATE_MIN:
        return STATE_MIN
    if value > STATE_MAX:
        return STATE_MAX
    return value


def round_div4096_away(value: int) -> int:
    """Round a signed integer quotient away from zero (including negatives)."""
    _require_int("value", value)
    quotient, remainder = divmod(abs(value), DECAY_DENOMINATOR)
    magnitude = quotient + (1 if remainder else 0)
    return -magnitude if value < 0 else magnitude


def wrap64(value: int) -> int:
    """Represent HLS ap_int<64> addition without Python's unbounded-int semantics."""
    _require_int("value", value)
    return ((value - ACC_MIN) % (1 << ACC_BITS)) + ACC_MIN


def accumulate_synapses(weights: Iterable[int]) -> int:
    """Expand effective signed-24-bit weights into a 64-bit HLS accumulator.

    Legal P03 workloads cannot overflow this accumulator: even 4096 events
    each traversing all 32768 stored entries contribute < 2**51 in magnitude.
    The explicit wrap defines the underlying ap_int<64> operation nonetheless.
    """
    accumulated = 0
    for weight in weights:
        _check_range("synaptic weight", weight, STATE_MIN, STATE_MAX)
        accumulated = wrap64(accumulated + weight)
    return accumulated


def lif_step(state: LIFState, config: LIFParameters, synaptic_input: int) -> LIFStep:
    """Evaluate one P03-style timestep in the exact hardware operation order.

    Current addition saturates BEFORE current decay. Current decay changes the
    saved current, but the pre-decay current contributes to this tick's voltage.
    Voltage decays separately; bias and current then enter one saturating sum.
    Refractory ticks still update current but hold voltage at reset, and neither
    the refractory nor the spike case retroactively changes current_after.
    """
    if not isinstance(state, LIFState) or not isinstance(config, LIFParameters):
        raise TypeError("expected LIFState and LIFParameters")
    _check_range("synaptic_input", synaptic_input, ACC_MIN, ACC_MAX)

    current_work = saturate24(state.current + synaptic_input)
    current_removed = round_div4096_away(current_work * config.current_decay)
    current_after = saturate24(current_work - current_removed)

    if state.refractory_remaining:
        return LIFStep(
            state=LIFState(current_after, config.reset_voltage, state.refractory_remaining - 1),
            spiked=False,
            current_work=current_work,
            voltage_pre_threshold=None,
        )

    voltage_removed = round_div4096_away(state.voltage * config.voltage_decay)
    decayed_voltage = saturate24(state.voltage - voltage_removed)
    candidate = saturate24(decayed_voltage + current_work + config.bias)
    fired = candidate > config.threshold  # strict comparison; equality is silent
    next_voltage = config.reset_voltage if fired else candidate
    next_refractory = max(config.refractory_ticks - 1, 0) if fired else 0
    return LIFStep(
        state=LIFState(current_after, next_voltage, next_refractory),
        spiked=fired,
        current_work=current_work,
        voltage_pre_threshold=candidate,
    )
