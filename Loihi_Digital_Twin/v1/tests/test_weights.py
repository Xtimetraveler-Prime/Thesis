import pytest

from neuromorphic_twin.weights import (
    WEIGHT_ALIGNMENT,
    WEIGHT_LIMIT,
    WeightFormat,
    WeightSignMode,
    encode_static_weight,
)


def test_default_excitatory_weight_expands_by_sixty_four() -> None:
    result = encode_static_weight(124)

    assert result.requested_mantissa == 124
    assert result.quantized_mantissa == 124
    assert result.precision == 1
    assert result.effective_weight == 124 * 64
    assert result.clipped is False


def test_reduced_precision_quantizes_positive_mantissa_toward_zero() -> None:
    result = encode_static_weight(
        127,
        WeightFormat(num_weight_bits=6),
    )

    assert result.precision == 4
    assert result.quantized_mantissa == 124
    assert result.effective_weight == 124 * 64


def test_reduced_precision_quantizes_negative_mantissa_toward_zero() -> None:
    result = encode_static_weight(
        -127,
        WeightFormat(
            num_weight_bits=6,
            sign_mode=WeightSignMode.INHIBITORY,
        ),
    )

    assert result.precision == 4
    assert result.quantized_mantissa == -124
    assert result.effective_weight == -124 * 64


@pytest.mark.parametrize(
    ("mantissa", "quantized"),
    [
        (253, 252),
        (-255, -254),
    ],
)
def test_mixed_mode_uses_one_bit_for_sign(
    mantissa: int,
    quantized: int,
) -> None:
    result = encode_static_weight(
        mantissa,
        WeightFormat(sign_mode=WeightSignMode.MIXED),
    )

    assert result.precision == 2
    assert result.quantized_mantissa == quantized


def test_positive_and_negative_exponents_scale_effective_weight() -> None:
    positive = encode_static_weight(3, WeightFormat(exponent=2))
    negative = encode_static_weight(128, WeightFormat(exponent=-2))

    assert positive.effective_weight == 3 * 256
    assert negative.effective_weight == 32 * 64


def test_negative_fractional_scaling_floors_at_final_alignment() -> None:
    result = encode_static_weight(
        -1,
        WeightFormat(
            exponent=-1,
            sign_mode=WeightSignMode.INHIBITORY,
        ),
    )

    assert result.quantized_mantissa == -1
    assert result.effective_weight_before_clip == -64
    assert result.effective_weight == -64


def test_extreme_negative_weight_clips_to_aligned_21_bit_limit() -> None:
    result = encode_static_weight(
        -256,
        WeightFormat(
            exponent=7,
            sign_mode=WeightSignMode.MIXED,
        ),
    )

    assert result.effective_weight_before_clip == -(1 << 21)
    assert result.effective_weight == -WEIGHT_LIMIT
    assert result.effective_weight % WEIGHT_ALIGNMENT == 0
    assert result.clipped is True


def test_largest_positive_weight_does_not_clip() -> None:
    result = encode_static_weight(255, WeightFormat(exponent=7))

    assert result.effective_weight == 255 * (1 << 13)
    assert result.effective_weight < WEIGHT_LIMIT
    assert result.clipped is False


@pytest.mark.parametrize(
    ("sign_mode", "valid_low", "valid_high", "invalid"),
    [
        (WeightSignMode.EXCITATORY, 0, 255, -1),
        (WeightSignMode.INHIBITORY, -256, 0, 1),
        (WeightSignMode.MIXED, -256, 254, 255),
    ],
)
def test_sign_modes_enforce_mantissa_ranges(
    sign_mode: WeightSignMode,
    valid_low: int,
    valid_high: int,
    invalid: int,
) -> None:
    fmt = WeightFormat(sign_mode=sign_mode)

    assert encode_static_weight(valid_low, fmt).requested_mantissa == valid_low
    assert encode_static_weight(valid_high, fmt).requested_mantissa == valid_high
    with pytest.raises(ValueError, match="mantissa must be"):
        encode_static_weight(invalid, fmt)


@pytest.mark.parametrize("exponent", [-9, 8])
def test_weight_format_rejects_invalid_exponent(exponent: int) -> None:
    with pytest.raises(ValueError, match="exponent must be"):
        WeightFormat(exponent=exponent)


@pytest.mark.parametrize("num_weight_bits", [-1, 9])
def test_weight_format_rejects_invalid_precision_bits(
    num_weight_bits: int,
) -> None:
    with pytest.raises(ValueError, match="num_weight_bits must be"):
        WeightFormat(num_weight_bits=num_weight_bits)


def test_weight_format_rejects_untyped_sign_mode() -> None:
    with pytest.raises(TypeError, match="WeightSignMode"):
        WeightFormat(sign_mode="mixed")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, 1.5, "1"])
def test_encoder_requires_integer_mantissa(value: object) -> None:
    with pytest.raises(TypeError, match="mantissa must be an int"):
        encode_static_weight(value)  # type: ignore[arg-type]


def test_zero_weight_bits_have_documented_quantization_behavior() -> None:
    excitatory = encode_static_weight(255, WeightFormat(num_weight_bits=0))
    inhibitory = encode_static_weight(
        -256,
        WeightFormat(
            num_weight_bits=0,
            sign_mode=WeightSignMode.INHIBITORY,
        ),
    )
    mixed = encode_static_weight(
        -256,
        WeightFormat(
            num_weight_bits=0,
            sign_mode=WeightSignMode.MIXED,
        ),
    )

    assert excitatory.quantized_mantissa == 0
    assert inhibitory.quantized_mantissa == -256
    assert mixed.quantized_mantissa == 0


def test_representative_configuration_space_preserves_invariants() -> None:
    requested_by_mode = {
        WeightSignMode.EXCITATORY: (0, 1, 127, 255),
        WeightSignMode.INHIBITORY: (-256, -127, -1, 0),
        WeightSignMode.MIXED: (-256, -127, -1, 0, 1, 127, 254),
    }

    for sign_mode, mantissas in requested_by_mode.items():
        for exponent in range(-8, 8):
            for num_weight_bits in range(0, 9):
                fmt = WeightFormat(
                    exponent=exponent,
                    num_weight_bits=num_weight_bits,
                    sign_mode=sign_mode,
                )
                for mantissa in mantissas:
                    result = encode_static_weight(mantissa, fmt)
                    assert result.quantized_mantissa % fmt.precision == 0
                    assert abs(result.quantized_mantissa) <= abs(mantissa)
                    assert result.effective_weight % WEIGHT_ALIGNMENT == 0
                    assert -WEIGHT_LIMIT <= result.effective_weight <= WEIGHT_LIMIT
