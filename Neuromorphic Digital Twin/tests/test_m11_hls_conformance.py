from __future__ import annotations

from neuromorphic_twin.hls_conformance import (
    M11_2_DEFAULT_RANDOM_CASES,
    M11_2_DEFAULT_SEED,
    build_m11_2_hls_vectors,
    directed_hls_neuron_vectors,
    randomized_hls_neuron_vectors,
    write_m11_2_cpp_initializer,
)
from neuromorphic_twin.model import NeuronConfig, NeuronState
from neuromorphic_twin.neuron import step_neuron
from neuromorphic_twin.specification import (
    FPGA_CORE_ARITHMETIC_V1,
    REFRACTORY_MAX,
    STATE_MAX,
    STATE_MIN,
    validate_neuron_config_v1,
    validate_neuron_state_v1,
)


def test_m11_2_vector_corpus_is_deterministic() -> None:
    first = build_m11_2_hls_vectors(random_cases=64, seed=M11_2_DEFAULT_SEED)
    second = build_m11_2_hls_vectors(random_cases=64, seed=M11_2_DEFAULT_SEED)
    assert first == second
    assert randomized_hls_neuron_vectors(count=8, seed=1) != randomized_hls_neuron_vectors(
        count=8,
        seed=2,
    )

    # Lock the specified SplitMix64 stream so the standard corpus cannot drift
    # silently if generator internals are edited later.
    first_random = randomized_hls_neuron_vectors(count=1)[0]
    assert (
        first_random.current_before,
        first_random.voltage_before,
        first_random.refractory_before,
        first_random.synaptic_input,
        first_random.current_decay,
        first_random.voltage_decay,
        first_random.threshold,
        first_random.bias,
        first_random.reset_voltage,
        first_random.refractory_ticks,
        first_random.expected_current,
        first_random.expected_voltage,
        first_random.expected_refractory,
        first_random.expected_spike,
    ) == (
        -8388608,
        -2260350,
        0,
        1794213486,
        0,
        2575,
        2923231,
        -7382325,
        -4874965,
        0,
        8388607,
        166929,
        0,
        0,
    )


def test_m11_2_default_corpus_size_and_boundaries() -> None:
    directed = directed_hls_neuron_vectors()
    vectors = build_m11_2_hls_vectors()

    assert len(directed) == 24
    assert len(vectors) == 24 + M11_2_DEFAULT_RANDOM_CASES

    names = {vector.name for vector in directed}
    assert {
        "threshold_equality",
        "threshold_just_over",
        "current_positive_saturation",
        "current_negative_saturation",
        "current_decay_one_positive",
        "current_decay_one_negative",
        "current_half_decay_positive_odd",
        "current_half_decay_negative_odd",
        "refractory_one",
        "refractory_max",
        "spike_refractory_zero",
        "spike_refractory_one",
        "spike_refractory_max",
        "large_positive_synaptic_input",
        "large_negative_synaptic_input",
    } <= names

    assert any(vector.current_before == STATE_MIN for vector in vectors)
    assert any(vector.current_before == STATE_MAX for vector in vectors)
    assert any(vector.refractory_before == REFRACTORY_MAX for vector in vectors)
    assert any(vector.current_decay == 0 for vector in vectors)
    assert any(vector.current_decay == 4096 for vector in vectors)
    assert any(vector.voltage_decay == 0 for vector in vectors)
    assert any(vector.voltage_decay == 4096 for vector in vectors)
    assert {vector.expected_spike for vector in vectors} == {0, 1}


def test_every_m11_2_vector_replays_exactly_through_python_golden() -> None:
    for vector in build_m11_2_hls_vectors(random_cases=256):
        state = NeuronState(
            current=vector.current_before,
            voltage=vector.voltage_before,
            refractory_remaining=vector.refractory_before,
        )
        config = NeuronConfig(
            current_decay=vector.current_decay,
            voltage_decay=vector.voltage_decay,
            threshold=vector.threshold,
            bias=vector.bias,
            reset_voltage=vector.reset_voltage,
            refractory_ticks=vector.refractory_ticks,
        )
        validate_neuron_state_v1(state)
        validate_neuron_config_v1(config)

        result = step_neuron(
            state,
            config,
            vector.synaptic_input,
            arithmetic=FPGA_CORE_ARITHMETIC_V1,
        )
        assert result.state.current == vector.expected_current, vector.name
        assert result.state.voltage == vector.expected_voltage, vector.name
        assert result.state.refractory_remaining == vector.expected_refractory, vector.name
        assert int(result.spiked) == vector.expected_spike, vector.name


def test_m11_2_cpp_initializer_is_reproducible(tmp_path) -> None:
    vectors = build_m11_2_hls_vectors(random_cases=32, seed=0x1234)
    directed_count = len(directed_hls_neuron_vectors())
    first = tmp_path / "first.inc"
    second = tmp_path / "second.inc"

    write_m11_2_cpp_initializer(
        first,
        vectors,
        directed_count=directed_count,
        seed=0x1234,
    )
    write_m11_2_cpp_initializer(
        second,
        vectors,
        directed_count=directed_count,
        seed=0x1234,
    )

    assert first.read_bytes() == second.read_bytes()
    text = first.read_text(encoding="utf-8")
    assert "M11_2_GOLDEN_SEED = 0x1234u" in text
    assert f"M11_2_DIRECTED_COUNT = {directed_count}u" in text
    assert "M11_2_RANDOM_COUNT = 32u" in text
    assert "M11_2_GOLDEN_VECTORS" in text
