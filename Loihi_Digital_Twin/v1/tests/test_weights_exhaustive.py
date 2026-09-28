from fractions import Fraction
from math import floor

import pytest

from neuromorphic_twin.weights import (
    WEIGHT_ALIGNMENT,
    WEIGHT_LIMIT,
    WeightFormat,
    WeightSignMode,
    encode_static_weight,
)


@pytest.mark.parametrize(
    ("exponent", "num_weight_bits", "sign_mode"),
    [
        (-8, 0, WeightSignMode.EXCITATORY),
        (-8, 8, WeightSignMode.INHIBITORY),
        (7, 0, WeightSignMode.MIXED),
        (7, 8, WeightSignMode.EXCITATORY),
    ],
)
def test_documented_configuration_boundaries_are_accepted(
    exponent: int,
    num_weight_bits: int,
    sign_mode: WeightSignMode,
) -> None:
    fmt = WeightFormat(
        exponent=exponent,
        num_weight_bits=num_weight_bits,
        sign_mode=sign_mode,
    )

    assert fmt.exponent == exponent
    assert fmt.num_weight_bits == num_weight_bits
    assert fmt.sign_mode is sign_mode


def test_full_valid_static_weight_space_matches_literal_reference() -> None:
    checked = 0

    for sign_mode in WeightSignMode:
        low, high = _mantissa_bounds(sign_mode)
        for exponent in range(-8, 8):
            for num_weight_bits in range(0, 9):
                fmt = WeightFormat(
                    exponent=exponent,
                    num_weight_bits=num_weight_bits,
                    sign_mode=sign_mode,
                )
                for mantissa in range(low, high + 1):
                    result = encode_static_weight(mantissa, fmt)
                    expected_quantized, expected_before_clip, expected = (
                        _literal_static_weight_reference(
                            mantissa,
                            exponent=exponent,
                            num_weight_bits=num_weight_bits,
                            sign_mode=sign_mode,
                        )
                    )

                    assert result.requested_mantissa == mantissa
                    assert result.quantized_mantissa == expected_quantized
                    assert result.effective_weight_before_clip == expected_before_clip
                    assert result.effective_weight == expected
                    assert result.clipped is (expected != expected_before_clip)
                    assert result.effective_weight % WEIGHT_ALIGNMENT == 0
                    assert -WEIGHT_LIMIT <= result.effective_weight <= WEIGHT_LIMIT
                    checked += 1

    assert checked == 147_456


def _literal_static_weight_reference(
    mantissa: int,
    *,
    exponent: int,
    num_weight_bits: int,
    sign_mode: WeightSignMode,
) -> tuple[int, int, int]:
    """Literal equation-oriented oracle kept independent of encoder helpers."""

    mixed_sign_bit = 1 if sign_mode is WeightSignMode.MIXED else 0
    precision_shift = 8 - (num_weight_bits - mixed_sign_bit)
    quantum = 1 << precision_shift

    quantized_magnitude = (abs(mantissa) // quantum) * quantum
    quantized = quantized_magnitude if mantissa >= 0 else -quantized_magnitude

    scaled = Fraction(quantized * WEIGHT_ALIGNMENT) * (Fraction(2) ** exponent)
    aligned_before_clip = floor(scaled / WEIGHT_ALIGNMENT) * WEIGHT_ALIGNMENT
    clipped = min(max(aligned_before_clip, -WEIGHT_LIMIT), WEIGHT_LIMIT)
    return quantized, aligned_before_clip, clipped


def _mantissa_bounds(sign_mode: WeightSignMode) -> tuple[int, int]:
    if sign_mode is WeightSignMode.EXCITATORY:
        return 0, 255
    if sign_mode is WeightSignMode.INHIBITORY:
        return -256, 0
    return -256, 254
