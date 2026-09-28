import pytest

from neuromorphic_twin import ArithmeticConfig, OverflowMode, round_away_from_zero


def test_round_away_from_zero() -> None:
    assert round_away_from_zero(0, 4096) == 0
    assert round_away_from_zero(1, 4096) == 1
    assert round_away_from_zero(4096, 4096) == 1
    assert round_away_from_zero(4097, 4096) == 2
    assert round_away_from_zero(-1, 4096) == -1
    assert round_away_from_zero(-4097, 4096) == -2


def test_saturating_arithmetic() -> None:
    arithmetic = ArithmeticConfig(state_bits=4, overflow=OverflowMode.SATURATE)
    assert arithmetic.apply(9) == 7
    assert arithmetic.apply(-9) == -8


def test_wrapping_arithmetic() -> None:
    arithmetic = ArithmeticConfig(state_bits=4, overflow=OverflowMode.WRAP)
    assert arithmetic.apply(8) == -8
    assert arithmetic.apply(-9) == 7


def test_width_required_for_bounded_modes() -> None:
    with pytest.raises(ValueError):
        ArithmeticConfig(overflow=OverflowMode.SATURATE)
