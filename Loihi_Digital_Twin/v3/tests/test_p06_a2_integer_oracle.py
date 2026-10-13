"""P06-A2.1: hand-derived arithmetic vectors and existing-model differential gates.

The new scalar oracle must never call the existing neuron step; comparisons
against it and P03 packed data are downstream checks, not oracle internals.
"""

from __future__ import annotations

import random

import pytest

from loihi_twin_v2.arithmetic import ArithmeticConfig, OverflowMode
from loihi_twin_v2.compartment import CompartmentConfig, CompartmentState, step_compartment
from loihi_twin_v2.hardware_p03 import (
    pack_compartment_config,
    pack_compartment_state,
    unpack_compartment_config,
    unpack_compartment_state,
)
from loihi_twin_v2.p06_integer_oracle import (
    ACC_MAX,
    DECAY_DENOMINATOR,
    STATE_MAX,
    STATE_MIN,
    LIFParameters,
    LIFState,
    accumulate_synapses,
    lif_step,
    round_div4096_away,
    saturate24,
    wrap64,
)


SAT24 = ArithmeticConfig(state_bits=24, overflow=OverflowMode.SATURATE)


def test_hand_calculated_equality_crossing_and_strict_reset():
    config = LIFParameters(4096, 0, threshold=5)
    equal = lif_step(LIFState(), config, 5)
    assert (equal.current_work, equal.state.current, equal.state.voltage) == (5, 0, 5)
    assert equal.voltage_pre_threshold == 5 and not equal.spiked
    crossed = lif_step(LIFState(), config, 6)
    assert crossed.voltage_pre_threshold == 6 and crossed.spiked
    assert crossed.state == LIFState(0, 0, 0)


def test_hand_calculated_negative_weight_and_decay_rounding():
    assert [round_div4096_away(v) for v in (-8193, -4096, -1, 0, 1, 4096, 4097)] == [
        -3, -1, -1, 0, 1, 1, 2
    ]
    assert accumulate_synapses((9, -15, 3)) == -3
    no_spike = lif_step(LIFState(voltage=7), LIFParameters(4096, 0, threshold=5), -3)
    assert (no_spike.current_work, no_spike.state.current, no_spike.state.voltage) == (-3, 0, 4)
    assert not no_spike.spiked
    pos = lif_step(LIFState(current=1, voltage=1), LIFParameters(1, 1, 10), 0)
    neg = lif_step(LIFState(current=-1, voltage=-1), LIFParameters(1, 1, 10), 0)
    assert pos.state == LIFState(0, 1, 0)
    assert neg.state == LIFState(0, -1, 0)


def test_saturation_before_threshold_and_before_current_decay():
    assert saturate24(STATE_MAX + 50) == STATE_MAX
    assert saturate24(STATE_MIN - 50) == STATE_MIN
    at_limit = lif_step(
        LIFState(current=STATE_MAX, voltage=STATE_MAX - 1),
        LIFParameters(4096, 0, threshold=STATE_MAX), 999,
    )
    assert at_limit.current_work == STATE_MAX
    assert at_limit.state == LIFState(0, STATE_MAX, 0)
    assert not at_limit.spiked  # saturated equality, not overflow-triggered spike
    lower = lif_step(
        LIFState(current=STATE_MIN, voltage=-5),
        LIFParameters(4096, 0, threshold=1), -1,
    )
    assert lower.current_work == STATE_MIN
    assert lower.state == LIFState(0, STATE_MIN, 0) and not lower.spiked


def test_refractory_steps_integrate_current_but_hold_voltage_reset():
    config = LIFParameters(current_decay=0, voltage_decay=0,
                           threshold=3, reset_voltage=-1, refractory_ticks=3)
    first = lif_step(LIFState(), config, 4)
    assert first.spiked and first.state == LIFState(4, -1, 2)
    # Even while refractory, the neuron accumulates input and retains current.
    second = lif_step(first.state, config, -7)
    assert not second.spiked and second.state == LIFState(-3, -1, 1)
    assert second.voltage_pre_threshold is None
    third = lif_step(second.state, config, 2)
    assert not third.spiked and third.state == LIFState(-1, -1, 0)
    fourth = lif_step(third.state, config, 6)
    assert fourth.spiked and fourth.state == LIFState(5, -1, 2)


def test_signed_64_accumulation_and_input_validation():
    assert accumulate_synapses([STATE_MAX, STATE_MIN, 1]) == 0
    assert wrap64(ACC_MAX + 1) == -(1 << 63)
    assert wrap64(-(1 << 63) - 1) == ACC_MAX
    with pytest.raises(ValueError, match="synaptic weight"):
        accumulate_synapses([STATE_MAX + 1])
    with pytest.raises(ValueError, match="synaptic_input"):
        lif_step(LIFState(), LIFParameters(0, 0, 1), ACC_MAX + 1)


@pytest.mark.parametrize("kwargs", [
    {"current_decay": -1, "voltage_decay": 0, "threshold": 1},
    {"current_decay": 0, "voltage_decay": DECAY_DENOMINATOR + 1, "threshold": 1},
    {"current_decay": 0, "voltage_decay": 0, "threshold": 0},
    {"current_decay": 0, "voltage_decay": 0, "threshold": 1, "reset_voltage": 1},
    {"current_decay": 0, "voltage_decay": 0, "threshold": 1, "bias": STATE_MAX + 1},
    {"current_decay": 0, "voltage_decay": 0, "threshold": 1, "refractory_ticks": 65536},
])
def test_invalid_hardware_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        LIFParameters(**kwargs)


@pytest.mark.parametrize("kwargs", [
    {"current": STATE_MIN - 1}, {"voltage": STATE_MAX + 1},
    {"refractory_remaining": -1}, {"refractory_remaining": 65536},
])
def test_invalid_hardware_state_is_rejected(kwargs):
    with pytest.raises(ValueError):
        LIFState(**kwargs)


def test_bool_and_fractional_values_are_not_coerced():
    with pytest.raises(TypeError):
        LIFState(current=True)
    with pytest.raises(TypeError):
        LIFParameters(current_decay=0.5, voltage_decay=0, threshold=1)
    with pytest.raises(TypeError):
        accumulate_synapses((True,))


def _compare_existing(state: LIFState, params: LIFParameters, delivered: int):
    """Only the TEST adapter invokes the preexisting accepted implementation."""
    reference = lif_step(state, params, delivered)
    current = step_compartment(
        CompartmentState(state.current, state.voltage, state.refractory_remaining),
        CompartmentConfig(
            current_decay=params.current_decay,
            voltage_decay=params.voltage_decay,
            threshold=params.threshold,
            bias=params.bias,
            reset_voltage=params.reset_voltage,
            refractory_ticks=params.refractory_ticks,
        ),
        delivered,
        SAT24,
    )
    assert reference.spiked == current.spiked
    assert (
        reference.state.current, reference.state.voltage,
        reference.state.refractory_remaining,
    ) == (
        current.state.current, current.state.voltage,
        current.state.refractory_remaining,
    )
    return reference


def test_directed_vectors_match_preexisting_golden():
    cases = [
        (LIFState(), LIFParameters(4096, 0, 5), 5),
        (LIFState(), LIFParameters(4096, 0, 5), 6),
        (LIFState(current=-1, voltage=-1), LIFParameters(1, 1, 10), 0),
        (LIFState(current=STATE_MIN, voltage=-5), LIFParameters(4096, 0, 1), -1),
        (LIFState(current=STATE_MAX, voltage=STATE_MAX - 1),
         LIFParameters(4096, 0, STATE_MAX), 999),
        (LIFState(current=7, voltage=25, refractory_remaining=2),
         LIFParameters(1024, 2048, 40, bias=-4, reset_voltage=-5, refractory_ticks=3), -9),
        (LIFState(current=-75, voltage=39),
         LIFParameters(205, 4095, 10, bias=-20, reset_voltage=-2), -80),
    ]
    for state, params, delivered in cases:
        _compare_existing(state, params, delivered)


def test_seeded_boundary_biased_differential_vs_existing_golden():
    rng = random.Random(0xA206A21)
    states = (STATE_MIN, STATE_MIN + 1, -4097, -1, 0, 1, 4097, STATE_MAX - 1, STATE_MAX)
    decays = (0, 1, 205, 2048, 4095, 4096)
    for _ in range(1000):
        threshold = rng.choice((1, 2048, STATE_MAX))
        reset = rng.choice((STATE_MIN, -1, 0))
        params = LIFParameters(
            current_decay=rng.choice(decays),
            voltage_decay=rng.choice(decays),
            threshold=threshold,
            bias=rng.choice(states),
            reset_voltage=reset,
            refractory_ticks=rng.choice((0, 1, 2, 5, 65535)),
        )
        state = LIFState(
            current=rng.choice(states),
            voltage=rng.choice(states),
            refractory_remaining=rng.choice((0, 0, 0, 1, 2, 65535)),
        )
        delivered = rng.choice(states + (-(1 << 40), (1 << 40)))
        _compare_existing(state, params, delivered)


def test_p03_packed_config_and_state_preserve_oracle_semantics():
    params = LIFParameters(4096, 205, 2048, bias=-11, reset_voltage=-3, refractory_ticks=5)
    state = LIFState(-17, 2048, 0)
    binary_cfg = pack_compartment_config(CompartmentConfig(**{
        "current_decay": params.current_decay,
        "voltage_decay": params.voltage_decay,
        "threshold": params.threshold,
        "bias": params.bias,
        "reset_voltage": params.reset_voltage,
        "refractory_ticks": params.refractory_ticks,
    }))
    binary_state = pack_compartment_state(CompartmentState(
        state.current, state.voltage, state.refractory_remaining
    ))
    decoded_cfg = LIFParameters(**unpack_compartment_config(binary_cfg))
    unpacked_state = unpack_compartment_state(binary_state)
    decoded_state = LIFState(unpacked_state.current, unpacked_state.voltage,
                             unpacked_state.refractory_remaining)
    assert decoded_cfg == params and decoded_state == state
    assert lif_step(decoded_state, decoded_cfg, -1024) == lif_step(state, params, -1024)
    _compare_existing(decoded_state, decoded_cfg, -1024)
