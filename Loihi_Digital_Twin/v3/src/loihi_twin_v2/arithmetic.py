"""Integer arithmetic retained from the validated FPGA-v1 neuron contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OverflowMode(str, Enum):
    NONE = "none"
    SATURATE = "saturate"
    WRAP = "wrap"


def round_away_from_zero(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    if numerator == 0:
        return 0
    magnitude = (abs(numerator) + denominator - 1) // denominator
    return magnitude if numerator > 0 else -magnitude


@dataclass(frozen=True, slots=True)
class ArithmeticConfig:
    state_bits: int | None = None
    overflow: OverflowMode = OverflowMode.NONE

    def __post_init__(self) -> None:
        if self.state_bits is not None and self.state_bits < 2:
            raise ValueError("state_bits must be at least 2")
        if self.overflow is not OverflowMode.NONE and self.state_bits is None:
            raise ValueError("state_bits is required for saturate or wrap mode")

    @property
    def minimum(self) -> int | None:
        if self.state_bits is None:
            return None
        return -(1 << (self.state_bits - 1))

    @property
    def maximum(self) -> int | None:
        if self.state_bits is None:
            return None
        return (1 << (self.state_bits - 1)) - 1

    def apply(self, value: int) -> int:
        if self.overflow is OverflowMode.NONE:
            return int(value)
        assert self.state_bits is not None
        assert self.minimum is not None
        assert self.maximum is not None
        if self.overflow is OverflowMode.SATURATE:
            return min(max(int(value), self.minimum), self.maximum)
        modulus = 1 << self.state_bits
        return ((int(value) - self.minimum) % modulus) + self.minimum
