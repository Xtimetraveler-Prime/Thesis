"""Deterministic Python-to-HLS neuron conformance vectors for M11.2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import NeuronConfig, NeuronState
from .neuron import step_neuron
from .specification import (
    DECAY_MAX,
    FPGA_CORE_ARITHMETIC_V1,
    REFRACTORY_MAX,
    STATE_MAX,
    STATE_MIN,
    validate_neuron_config_v1,
    validate_neuron_state_v1,
)

M11_2_DEFAULT_SEED = 0x4D313132
M11_2_DEFAULT_RANDOM_CASES = 2048
M11_2_SYNAPTIC_MIN = -(1 << 31)
M11_2_SYNAPTIC_MAX = (1 << 31) - 1

_MASK64 = (1 << 64) - 1


@dataclass(frozen=True, slots=True)
class HlsNeuronVector:
    """One exact input/output comparison vector for ``neuron_step_v1``."""

    name: str
    current_before: int
    voltage_before: int
    refractory_before: int
    synaptic_input: int
    current_decay: int
    voltage_decay: int
    threshold: int
    bias: int
    reset_voltage: int
    refractory_ticks: int
    expected_current: int
    expected_voltage: int
    expected_refractory: int
    expected_spike: int


class _SplitMix64:
    """Small specified PRNG so M11.2 vectors do not depend on Python version."""

    def __init__(self, seed: int) -> None:
        self._state = seed & _MASK64

    def next_u64(self) -> int:
        self._state = (self._state + 0x9E3779B97F4A7C15) & _MASK64
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
        return (value ^ (value >> 31)) & _MASK64

    def randint(self, minimum: int, maximum: int) -> int:
        if maximum < minimum:
            raise ValueError("maximum must be >= minimum")
        span = maximum - minimum + 1
        return minimum + (self.next_u64() % span)


def _evaluate(
    name: str,
    *,
    current_before: int,
    voltage_before: int,
    refractory_before: int,
    synaptic_input: int,
    current_decay: int,
    voltage_decay: int,
    threshold: int,
    bias: int,
    reset_voltage: int,
    refractory_ticks: int,
) -> HlsNeuronVector:
    state = NeuronState(
        current=current_before,
        voltage=voltage_before,
        refractory_remaining=refractory_before,
    )
    config = NeuronConfig(
        current_decay=current_decay,
        voltage_decay=voltage_decay,
        threshold=threshold,
        bias=bias,
        reset_voltage=reset_voltage,
        refractory_ticks=refractory_ticks,
    )
    validate_neuron_state_v1(state)
    validate_neuron_config_v1(config)

    result = step_neuron(
        state,
        config,
        synaptic_input,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    return HlsNeuronVector(
        name=name,
        current_before=current_before,
        voltage_before=voltage_before,
        refractory_before=refractory_before,
        synaptic_input=synaptic_input,
        current_decay=current_decay,
        voltage_decay=voltage_decay,
        threshold=threshold,
        bias=bias,
        reset_voltage=reset_voltage,
        refractory_ticks=refractory_ticks,
        expected_current=result.state.current,
        expected_voltage=result.state.voltage,
        expected_refractory=result.state.refractory_remaining,
        expected_spike=int(result.spiked),
    )


def directed_hls_neuron_vectors() -> tuple[HlsNeuronVector, ...]:
    """Return Python-evaluated vectors targeting FPGA-v1 boundaries."""

    cases = (
        dict(name="zero_state", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=0, current_decay=0, voltage_decay=0, threshold=1, bias=0, reset_voltage=0, refractory_ticks=0),
        dict(name="threshold_equality", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=5, current_decay=0, voltage_decay=0, threshold=5, bias=0, reset_voltage=0, refractory_ticks=0),
        dict(name="threshold_just_over", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=6, current_decay=0, voltage_decay=0, threshold=5, bias=0, reset_voltage=0, refractory_ticks=0),
        dict(name="current_positive_saturation", current_before=STATE_MAX, voltage_before=0, refractory_before=0, synaptic_input=1, current_decay=0, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="current_negative_saturation", current_before=STATE_MIN, voltage_before=0, refractory_before=0, synaptic_input=-1, current_decay=0, voltage_decay=0, threshold=0, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="voltage_positive_saturation", current_before=1, voltage_before=STATE_MAX, refractory_before=0, synaptic_input=0, current_decay=0, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="voltage_negative_saturation", current_before=-1, voltage_before=STATE_MIN, refractory_before=0, synaptic_input=0, current_decay=0, voltage_decay=0, threshold=0, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="current_decay_one_positive", current_before=4096, voltage_before=0, refractory_before=0, synaptic_input=0, current_decay=1, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="current_decay_one_negative", current_before=-4096, voltage_before=0, refractory_before=0, synaptic_input=0, current_decay=1, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="current_half_decay_positive_odd", current_before=5, voltage_before=0, refractory_before=0, synaptic_input=0, current_decay=2048, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="current_half_decay_negative_odd", current_before=-5, voltage_before=0, refractory_before=0, synaptic_input=0, current_decay=2048, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="current_decay_4095", current_before=4096, voltage_before=0, refractory_before=0, synaptic_input=0, current_decay=4095, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="current_full_decay", current_before=-123456, voltage_before=0, refractory_before=0, synaptic_input=0, current_decay=DECAY_MAX, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="voltage_full_decay", current_before=11, voltage_before=-123456, refractory_before=0, synaptic_input=0, current_decay=0, voltage_decay=DECAY_MAX, threshold=STATE_MAX, bias=7, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="refractory_one", current_before=100, voltage_before=99, refractory_before=1, synaptic_input=28, current_decay=2048, voltage_decay=DECAY_MAX, threshold=1000, bias=50, reset_voltage=-7, refractory_ticks=3),
        dict(name="refractory_max", current_before=STATE_MAX, voltage_before=STATE_MIN, refractory_before=REFRACTORY_MAX, synaptic_input=-10, current_decay=1, voltage_decay=4095, threshold=100, bias=STATE_MAX, reset_voltage=-11, refractory_ticks=REFRACTORY_MAX),
        dict(name="spike_refractory_zero", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=6, current_decay=0, voltage_decay=0, threshold=5, bias=0, reset_voltage=-1, refractory_ticks=0),
        dict(name="spike_refractory_one", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=6, current_decay=0, voltage_decay=0, threshold=5, bias=0, reset_voltage=-1, refractory_ticks=1),
        dict(name="spike_refractory_max", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=6, current_decay=0, voltage_decay=0, threshold=5, bias=0, reset_voltage=-1, refractory_ticks=REFRACTORY_MAX),
        dict(name="positive_bias_saturation", current_before=0, voltage_before=STATE_MAX, refractory_before=0, synaptic_input=0, current_decay=0, voltage_decay=0, threshold=STATE_MAX, bias=STATE_MAX, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="negative_bias_saturation", current_before=0, voltage_before=STATE_MIN, refractory_before=0, synaptic_input=0, current_decay=0, voltage_decay=0, threshold=0, bias=STATE_MIN, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="large_positive_synaptic_input", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=M11_2_SYNAPTIC_MAX, current_decay=0, voltage_decay=0, threshold=STATE_MAX, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="large_negative_synaptic_input", current_before=0, voltage_before=0, refractory_before=0, synaptic_input=M11_2_SYNAPTIC_MIN, current_decay=0, voltage_decay=0, threshold=0, bias=0, reset_voltage=STATE_MIN, refractory_ticks=0),
        dict(name="minimum_reset_voltage_spike", current_before=0, voltage_before=STATE_MIN, refractory_before=0, synaptic_input=2, current_decay=0, voltage_decay=DECAY_MAX, threshold=STATE_MIN + 1, bias=0, reset_voltage=STATE_MIN, refractory_ticks=2),
    )
    return tuple(_evaluate(**case) for case in cases)


def _random_refractory(rng: _SplitMix64, index: int) -> int:
    mode = index % 4
    if mode in (0, 1):
        return 0
    if mode == 2:
        return 1
    return rng.randint(2, REFRACTORY_MAX)


def _random_refractory_ticks(rng: _SplitMix64, index: int) -> int:
    mode = index % 5
    if mode == 0:
        return 0
    if mode == 1:
        return 1
    if mode == 2:
        return REFRACTORY_MAX
    return rng.randint(0, REFRACTORY_MAX)


def _random_decay(rng: _SplitMix64, index: int, offset: int) -> int:
    boundaries = (0, 1, 2048, 4095, 4096)
    if index % 8 == offset:
        return boundaries[(index // 8) % len(boundaries)]
    return rng.randint(0, DECAY_MAX)


def randomized_hls_neuron_vectors(
    *,
    count: int = M11_2_DEFAULT_RANDOM_CASES,
    seed: int = M11_2_DEFAULT_SEED,
) -> tuple[HlsNeuronVector, ...]:
    """Return a reproducible pseudo-random FPGA-v1 differential corpus."""

    if count < 0:
        raise ValueError("count cannot be negative")

    rng = _SplitMix64(seed)
    vectors: list[HlsNeuronVector] = []
    state_edges = (STATE_MIN, STATE_MIN + 1, -1, 0, 1, STATE_MAX - 1, STATE_MAX)
    synaptic_edges = (
        M11_2_SYNAPTIC_MIN,
        -STATE_MAX - 1,
        -1,
        0,
        1,
        STATE_MAX + 1,
        M11_2_SYNAPTIC_MAX,
    )

    for index in range(count):
        current_before = (
            state_edges[(index // 16) % len(state_edges)]
            if index % 16 == 0
            else rng.randint(STATE_MIN, STATE_MAX)
        )
        voltage_before = (
            state_edges[(index // 16 + 3) % len(state_edges)]
            if index % 16 == 1
            else rng.randint(STATE_MIN, STATE_MAX)
        )
        synaptic_input = (
            synaptic_edges[(index // 16) % len(synaptic_edges)]
            if index % 16 == 2
            else rng.randint(M11_2_SYNAPTIC_MIN, M11_2_SYNAPTIC_MAX)
        )

        reset_voltage = rng.randint(STATE_MIN, STATE_MAX - 1)
        threshold = rng.randint(reset_voltage + 1, STATE_MAX)

        vectors.append(
            _evaluate(
                f"random_{index:04d}",
                current_before=current_before,
                voltage_before=voltage_before,
                refractory_before=_random_refractory(rng, index),
                synaptic_input=synaptic_input,
                current_decay=_random_decay(rng, index, 0),
                voltage_decay=_random_decay(rng, index, 1),
                threshold=threshold,
                bias=rng.randint(STATE_MIN, STATE_MAX),
                reset_voltage=reset_voltage,
                refractory_ticks=_random_refractory_ticks(rng, index),
            )
        )

    return tuple(vectors)


def build_m11_2_hls_vectors(
    *,
    random_cases: int = M11_2_DEFAULT_RANDOM_CASES,
    seed: int = M11_2_DEFAULT_SEED,
) -> tuple[HlsNeuronVector, ...]:
    """Return the complete directed + seeded-random M11.2 corpus."""

    return directed_hls_neuron_vectors() + randomized_hls_neuron_vectors(
        count=random_cases,
        seed=seed,
    )


def write_m11_2_cpp_initializer(
    output_path: str | Path,
    vectors: tuple[HlsNeuronVector, ...],
    *,
    directed_count: int,
    seed: int,
) -> Path:
    """Write vectors as a C++ initializer included by the HLS testbench."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "// Generated by neuromorphic_twin.hls_conformance. Do not edit.",
        f"static constexpr unsigned M11_2_GOLDEN_SEED = 0x{seed:X}u;",
        f"static constexpr unsigned M11_2_DIRECTED_COUNT = {directed_count}u;",
        f"static constexpr unsigned M11_2_RANDOM_COUNT = {len(vectors) - directed_count}u;",
        "static const TestVector M11_2_GOLDEN_VECTORS[] = {",
    ]
    for vector in vectors:
        lines.append(
            "    {"
            f'\"{vector.name}\", '
            f"{vector.current_before}LL, {vector.voltage_before}LL, {vector.refractory_before}u, "
            f"{vector.synaptic_input}LL, {vector.current_decay}u, {vector.voltage_decay}u, "
            f"{vector.threshold}LL, {vector.bias}LL, {vector.reset_voltage}LL, {vector.refractory_ticks}u, "
            f"{vector.expected_current}LL, {vector.expected_voltage}LL, {vector.expected_refractory}u, "
            f"{vector.expected_spike}u"
            "},"
        )
    lines.extend(
        [
            "};",
            "static constexpr unsigned M11_2_GOLDEN_COUNT =",
            "    sizeof(M11_2_GOLDEN_VECTORS) / sizeof(M11_2_GOLDEN_VECTORS[0]);",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
