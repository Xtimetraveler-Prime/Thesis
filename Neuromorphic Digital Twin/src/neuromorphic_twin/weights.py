"""Loihi-style static synaptic weight encoding.

The encoder is intentionally independent of Brian2Loihi. It implements the
published static-weight contract with integer-only operations so the same logic
can later be translated into an FPGA datapath.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

WEIGHT_EXPONENT_MIN = -8
WEIGHT_EXPONENT_MAX = 7
WEIGHT_BITS_MIN = 0
WEIGHT_BITS_MAX = 8
WEIGHT_ALIGNMENT_BITS = 6
WEIGHT_ALIGNMENT = 1 << WEIGHT_ALIGNMENT_BITS
WEIGHT_LIMIT = (1 << 21) - WEIGHT_ALIGNMENT


class WeightSignMode(str, Enum):
    """Allowed signs for all mantissas sharing one weight format."""

    MIXED = "mixed"
    EXCITATORY = "excitatory"
    INHIBITORY = "inhibitory"


@dataclass(frozen=True, slots=True)
class WeightFormat:
    """Configuration shared by a group of Loihi-style synaptic mantissas."""

    exponent: int = 0
    num_weight_bits: int = 8
    sign_mode: WeightSignMode = WeightSignMode.EXCITATORY

    def __post_init__(self) -> None:
        _require_int("exponent", self.exponent)
        _require_int("num_weight_bits", self.num_weight_bits)
        if not WEIGHT_EXPONENT_MIN <= self.exponent <= WEIGHT_EXPONENT_MAX:
            raise ValueError(
                f"exponent must be in {WEIGHT_EXPONENT_MIN}..{WEIGHT_EXPONENT_MAX}"
            )
        if not WEIGHT_BITS_MIN <= self.num_weight_bits <= WEIGHT_BITS_MAX:
            raise ValueError(
                f"num_weight_bits must be in {WEIGHT_BITS_MIN}..{WEIGHT_BITS_MAX}"
            )
        if not isinstance(self.sign_mode, WeightSignMode):
            raise TypeError("sign_mode must be a WeightSignMode")

    @property
    def precision_shift(self) -> int:
        """Number of low mantissa bits discarded during initialization."""

        mixed_sign_bit = 1 if self.sign_mode is WeightSignMode.MIXED else 0
        return 8 - (self.num_weight_bits - mixed_sign_bit)

    @property
    def precision(self) -> int:
        """Spacing between representable initialized mantissas."""

        return 1 << self.precision_shift

    @property
    def mantissa_bounds(self) -> tuple[int, int]:
        """Inclusive requested-mantissa bounds for this sign mode."""

        if self.sign_mode is WeightSignMode.EXCITATORY:
            return (0, 255)
        if self.sign_mode is WeightSignMode.INHIBITORY:
            return (-256, 0)
        return (-256, 254)


@dataclass(frozen=True, slots=True)
class StaticWeightEncoding:
    """Traceable result of encoding one requested static mantissa."""

    requested_mantissa: int
    quantized_mantissa: int
    weight_format: WeightFormat
    effective_weight_before_clip: int
    effective_weight: int
    clipped: bool

    @property
    def precision(self) -> int:
        return self.weight_format.precision


def encode_static_weight(
    mantissa: int,
    weight_format: WeightFormat | None = None,
) -> StaticWeightEncoding:
    """Encode one static Loihi-style mantissa into its effective weight.

    Initialization follows four deterministic stages:

    1. Validate the requested mantissa against the selected sign mode.
    2. Quantize the mantissa toward zero at the configured precision.
    3. Apply the exponent and align the effective value to 64.
    4. Clip to the signed 21-bit range whose low six bits are zero.

    The result retains both requested and quantized values for later trace and
    FPGA-memory comparisons.
    """

    _require_int("mantissa", mantissa)
    fmt = weight_format or WeightFormat()
    if not isinstance(fmt, WeightFormat):
        raise TypeError("weight_format must be a WeightFormat")

    low, high = fmt.mantissa_bounds
    if not low <= mantissa <= high:
        raise ValueError(
            f"mantissa must be in {low}..{high} for {fmt.sign_mode.value} mode"
        )

    quantized_mantissa = _truncate_to_multiple_toward_zero(
        mantissa,
        fmt.precision,
    )
    aligned_weight = _apply_exponent_and_alignment(
        quantized_mantissa,
        fmt.exponent,
    )
    effective_weight = min(max(aligned_weight, -WEIGHT_LIMIT), WEIGHT_LIMIT)

    return StaticWeightEncoding(
        requested_mantissa=mantissa,
        quantized_mantissa=quantized_mantissa,
        weight_format=fmt,
        effective_weight_before_clip=aligned_weight,
        effective_weight=effective_weight,
        clipped=effective_weight != aligned_weight,
    )


def _truncate_to_multiple_toward_zero(value: int, quantum: int) -> int:
    magnitude = (abs(value) // quantum) * quantum
    return magnitude if value >= 0 else -magnitude


def _apply_exponent_and_alignment(mantissa: int, exponent: int) -> int:
    # J = floor(mantissa * 2**exponent) * 2**6. For negative exponents,
    # Python's integer floor division exactly matches the published final
    # right/left alignment stage, including negative values.
    if exponent >= 0:
        aligned_units = mantissa << exponent
    else:
        aligned_units = mantissa // (1 << -exponent)
    return aligned_units << WEIGHT_ALIGNMENT_BITS


def _require_int(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
