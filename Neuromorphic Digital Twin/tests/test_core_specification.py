import re
from pathlib import Path

import pytest

from neuromorphic_twin import (
    CORE_SPEC_SCHEMA,
    DECAY_BITS,
    DECAY_MAX,
    DECAY_MIN,
    FPGA_CORE_ARITHMETIC_V1,
    ID_BITS,
    ID_MAX,
    REFRACTORY_BITS,
    REFRACTORY_MAX,
    STATE_BITS,
    STATE_MAX,
    STATE_MIN,
    TICK_BITS,
    NeuronConfig,
    NeuronState,
    NeuromorphicCore,
    OverflowMode,
    SpikeRoute,
    Synapse,
    WeightFormat,
    WeightSignMode,
    round_away_from_zero,
    step_neuron,
    validate_core_configuration_v1,
    validate_neuron_config_v1,
    validate_spike_route_v1,
    validate_synapse_v1,
)


SPEC_PATH = Path(__file__).parents[1] / "docs" / "CORE_SPECIFICATION.md"


def _cfg(
    *,
    current_decay: int = 0,
    voltage_decay: int = 0,
    threshold: int = 100,
    bias: int = 0,
    reset_voltage: int = 0,
    refractory_ticks: int = 0,
) -> NeuronConfig:
    return NeuronConfig(
        current_decay=current_decay,
        voltage_decay=voltage_decay,
        threshold=threshold,
        bias=bias,
        reset_voltage=reset_voltage,
        refractory_ticks=refractory_ticks,
    )


def test_profile_v1_freezes_architectural_widths_and_saturating_state() -> None:
    assert CORE_SPEC_SCHEMA == "neuromorphic-twin-core-spec-v1"
    assert STATE_BITS == 24
    assert STATE_MIN == -(1 << 23)
    assert STATE_MAX == (1 << 23) - 1
    assert TICK_BITS == 32
    assert ID_BITS == 16
    assert ID_MAX == 65535
    assert REFRACTORY_BITS == 16
    assert REFRACTORY_MAX == 65535
    assert DECAY_BITS == 13
    assert (DECAY_MIN, DECAY_MAX) == (0, 4096)

    arithmetic = FPGA_CORE_ARITHMETIC_V1
    assert arithmetic.state_bits == 24
    assert arithmetic.overflow is OverflowMode.SATURATE
    assert arithmetic.apply(STATE_MAX + 1) == STATE_MAX
    assert arithmetic.apply(STATE_MIN - 1) == STATE_MIN


def test_tick_schedule_is_atomic_and_recurrence_is_next_tick_only() -> None:
    core = NeuromorphicCore(
        [_cfg(threshold=5), _cfg(threshold=100)],
        [Synapse(0, 0, 6), Synapse(7, 1, 3)],
        spike_routes=[SpikeRoute(0, 7)],
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    tick_0 = core.step([0])
    tick_1 = core.step()

    assert tick_0.tick == 0
    assert tick_0.current_before == (0, 0)
    assert tick_0.routed_output_axons == (7,)
    assert tick_0.recurrent_input_axons == ()
    assert tick_0.synaptic_input == (6, 0)

    assert tick_1.tick == 1
    assert tick_1.recurrent_input_axons == (7,)
    assert tick_1.input_axons == (7,)
    assert tick_1.synaptic_input == (0, 3)


def test_external_events_precede_recurrent_events_and_preserve_multiplicity() -> None:
    core = NeuromorphicCore(
        [_cfg(threshold=5)],
        [Synapse(0, 0, 6)],
        spike_routes=[SpikeRoute(0, 0)],
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    core.step([0])
    trace = core.step([4, 0])

    assert trace.external_input_axons == (4, 0)
    assert trace.recurrent_input_axons == (0,)
    assert trace.input_axons == (4, 0, 0)
    assert trace.synaptic_input == (12,)


def test_synaptic_sum_is_exact_before_single_state_width_application() -> None:
    # M08's maximum aligned effective static-weight magnitude is 2^21 - 64.
    weight_limit = (1 << 21) - 64
    core = NeuromorphicCore(
        [_cfg(threshold=STATE_MAX)],
        [
            Synapse(0, 0, weight_limit),
            Synapse(1, 0, -weight_limit),
        ],
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    # Exact sum = 4 * weight_limit = 8,388,352, still below STATE_MAX.
    # Saturating after each individual positive contribution would produce a
    # different result, so this sequence catches an illegal per-synapse clamp.
    trace = core.step([0, 0, 0, 0, 0, 1])
    expected = 4 * weight_limit

    assert trace.synaptic_input == (expected,)
    assert trace.current_after == (expected,)
    assert trace.voltage_after == (expected,)


def test_encoded_synapse_delivers_m08_effective_weight_without_requantization() -> None:
    synapse = Synapse.encoded(
        axon_id=0,
        target_neuron=0,
        mantissa=124,
        weight_format=WeightFormat(
            exponent=0,
            num_weight_bits=8,
            sign_mode=WeightSignMode.EXCITATORY,
        ),
    )
    core = NeuromorphicCore(
        [_cfg(threshold=STATE_MAX)],
        [synapse],
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    trace = core.step([0])
    assert synapse.encoding is not None
    assert synapse.encoding.effective_weight == 7936
    assert trace.synaptic_input == (7936,)


def test_decay_rounding_endpoints_and_input_before_decay_contract() -> None:
    assert round_away_from_zero(1, 4096) == 1
    assert round_away_from_zero(-1, 4096) == -1
    assert round_away_from_zero(4097, 4096) == 2
    assert round_away_from_zero(-4097, 4096) == -2

    no_decay = step_neuron(
        NeuronState(current=-7),
        _cfg(current_decay=0, threshold=1000),
        synaptic_input=0,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    full_decay = step_neuron(
        NeuronState(current=-7),
        _cfg(current_decay=4096, threshold=1000),
        synaptic_input=0,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    half_decay = step_neuron(
        NeuronState(),
        _cfg(current_decay=2048, threshold=1000),
        synaptic_input=128,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    assert no_decay.state.current == -7
    assert full_decay.state.current == 0
    assert half_decay.state.current == 64
    assert half_decay.state.voltage == 128


def test_state_saturation_occurs_at_working_current_and_voltage_boundaries() -> None:
    result = step_neuron(
        NeuronState(current=STATE_MAX - 2, voltage=STATE_MAX - 2),
        _cfg(current_decay=0, voltage_decay=0, threshold=STATE_MAX, bias=10),
        synaptic_input=10,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    assert result.state.current == STATE_MAX
    assert result.state.voltage == STATE_MAX
    # Strict-greater-than threshold means equality after saturation does not fire.
    assert result.spiked is False


def test_threshold_reset_and_refractory_timing_contract() -> None:
    config = _cfg(
        current_decay=4096,
        voltage_decay=0,
        threshold=10,
        reset_voltage=-2,
        refractory_ticks=3,
    )

    equal = step_neuron(
        NeuronState(voltage=-2),
        config,
        synaptic_input=12,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    assert equal.state.voltage == 10
    assert equal.spiked is False

    tick_0 = step_neuron(
        NeuronState(voltage=-2),
        config,
        synaptic_input=13,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    assert tick_0.spiked is True
    assert tick_0.state.voltage == -2
    assert tick_0.state.refractory_remaining == 2

    tick_1 = step_neuron(
        tick_0.state,
        config,
        synaptic_input=5,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    tick_2 = step_neuron(
        tick_1.state,
        config,
        synaptic_input=5,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    tick_3 = step_neuron(
        tick_2.state,
        config,
        synaptic_input=13,
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    assert tick_1.spiked is False
    assert tick_1.state.voltage == -2
    assert tick_1.state.refractory_remaining == 1
    assert tick_2.spiked is False
    assert tick_2.state.voltage == -2
    assert tick_2.state.refractory_remaining == 0
    assert tick_3.spiked is True


def test_simultaneous_routes_are_stable_and_cross_source_multiplicity_is_kept() -> None:
    core = NeuromorphicCore(
        [_cfg(threshold=5), _cfg(threshold=5), _cfg(threshold=STATE_MAX)],
        [
            Synapse(0, 0, 6),
            Synapse(0, 1, 6),
            Synapse(8, 2, 1),
            Synapse(6, 2, 10),
        ],
        spike_routes=[
            SpikeRoute(1, 6),
            SpikeRoute(0, 8),
            SpikeRoute(0, 6),
        ],
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    emitted = core.step([0])
    delivered = core.step([99])

    assert tuple(spike.neuron_id for spike in emitted.spikes) == (0, 1)
    assert emitted.routed_output_axons == (8, 6, 6)
    assert delivered.external_input_axons == (99,)
    assert delivered.recurrent_input_axons == (8, 6, 6)
    assert delivered.input_axons == (99, 8, 6, 6)
    assert delivered.synaptic_input == (0, 0, 21)


def test_reset_discards_routes_and_replays_deterministically() -> None:
    core = NeuromorphicCore(
        [_cfg(threshold=5, reset_voltage=-1)],
        [Synapse(0, 0, 7)],
        spike_routes=[SpikeRoute(0, 0)],
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )

    first = core.step([0])
    assert first.routed_output_axons == (0,)

    core.reset()
    after_reset = core.step()
    assert after_reset.tick == 0
    assert after_reset.input_axons == ()
    assert after_reset.recurrent_input_axons == ()
    assert after_reset.spikes == ()

    core.reset()
    replay = core.step([0])
    assert replay == first
    assert replay.current_before == (0,)
    assert replay.voltage_before == (-1,)


def test_profile_validation_rejects_unrepresentable_configuration() -> None:
    valid = _cfg(
        current_decay=DECAY_MAX,
        voltage_decay=DECAY_MAX,
        threshold=STATE_MAX,
        bias=STATE_MIN,
        reset_voltage=STATE_MIN,
        refractory_ticks=REFRACTORY_MAX,
    )
    validate_neuron_config_v1(valid)
    validate_core_configuration_v1([valid])

    with pytest.raises(ValueError, match="threshold"):
        validate_neuron_config_v1(
            _cfg(threshold=STATE_MAX + 1, reset_voltage=0)
        )
    with pytest.raises(ValueError, match="bias"):
        validate_neuron_config_v1(
            _cfg(threshold=1, bias=STATE_MAX + 1, reset_voltage=0)
        )
    with pytest.raises(ValueError, match="refractory_ticks"):
        validate_neuron_config_v1(
            _cfg(threshold=1, refractory_ticks=REFRACTORY_MAX + 1)
        )

    with pytest.raises(ValueError, match="axon_id"):
        validate_synapse_v1(Synapse(ID_MAX + 1, 0, 1), neuron_count=1)
    with pytest.raises(ValueError, match="target_axon"):
        validate_spike_route_v1(SpikeRoute(0, ID_MAX + 1), neuron_count=1)
    with pytest.raises(ValueError, match="duplicate"):
        validate_core_configuration_v1(
            [_cfg()],
            spike_routes=[SpikeRoute(0, 2), SpikeRoute(0, 2)],
        )


def test_tick_trace_exposes_state_and_routing_boundaries() -> None:
    core = NeuromorphicCore(
        [_cfg(threshold=5)],
        [Synapse(0, 0, 6)],
        spike_routes=[SpikeRoute(0, 0)],
        arithmetic=FPGA_CORE_ARITHMETIC_V1,
    )
    trace = core.step([0, 0])

    assert trace.tick == 0
    assert trace.external_input_axons == (0, 0)
    assert trace.recurrent_input_axons == ()
    assert trace.input_axons == (0, 0)
    assert trace.synaptic_input == (12,)
    assert trace.current_before == (0,)
    assert trace.voltage_before == (0,)
    assert trace.current_after == (12,)
    assert trace.voltage_after == (0,)
    assert tuple(spike.neuron_id for spike in trace.spikes) == (0,)
    assert trace.routed_output_axons == (0,)


REQUIREMENT_TESTS = {
    # Tick schedule
    "CORE-TICK-001": "test_tick_schedule_is_atomic_and_recurrence_is_next_tick_only",
    "CORE-TICK-002": "test_tick_schedule_is_atomic_and_recurrence_is_next_tick_only",
    "CORE-TICK-003": "test_external_events_precede_recurrent_events_and_preserve_multiplicity",
    "CORE-TICK-004": "test_synaptic_sum_is_exact_before_single_state_width_application",
    "CORE-TICK-005": "test_simultaneous_routes_are_stable_and_cross_source_multiplicity_is_kept",
    "CORE-TICK-006": "test_tick_schedule_is_atomic_and_recurrence_is_next_tick_only",
    # State and configuration widths
    "CORE-STATE-001": "test_profile_v1_freezes_architectural_widths_and_saturating_state",
    "CORE-STATE-002": "test_profile_v1_freezes_architectural_widths_and_saturating_state",
    "CORE-STATE-003": "test_profile_v1_freezes_architectural_widths_and_saturating_state",
    "CORE-STATE-004": "test_profile_v1_freezes_architectural_widths_and_saturating_state",
    "CORE-STATE-005": "test_profile_validation_rejects_unrepresentable_configuration",
    "CORE-STATE-006": "test_profile_v1_freezes_architectural_widths_and_saturating_state",
    "CORE-STATE-007": "test_profile_validation_rejects_unrepresentable_configuration",
    "CORE-STATE-008": "test_profile_validation_rejects_unrepresentable_configuration",
    "CORE-STATE-009": "test_reset_discards_routes_and_replays_deterministically",
    # Arithmetic
    "CORE-ARITH-001": "test_state_saturation_occurs_at_working_current_and_voltage_boundaries",
    "CORE-ARITH-002": "test_decay_rounding_endpoints_and_input_before_decay_contract",
    "CORE-ARITH-003": "test_decay_rounding_endpoints_and_input_before_decay_contract",
    # Synapses
    "CORE-SYN-001": "test_encoded_synapse_delivers_m08_effective_weight_without_requantization",
    "CORE-SYN-002": "test_synaptic_sum_is_exact_before_single_state_width_application",
    "CORE-SYN-003": "test_external_events_precede_recurrent_events_and_preserve_multiplicity",
    "CORE-SYN-004": "test_synaptic_sum_is_exact_before_single_state_width_application",
    # Neuron transition
    "CORE-NEURON-001": "test_decay_rounding_endpoints_and_input_before_decay_contract",
    "CORE-NEURON-002": "test_decay_rounding_endpoints_and_input_before_decay_contract",
    "CORE-NEURON-003": "test_threshold_reset_and_refractory_timing_contract",
    "CORE-NEURON-004": "test_threshold_reset_and_refractory_timing_contract",
    "CORE-NEURON-005": "test_threshold_reset_and_refractory_timing_contract",
    "CORE-NEURON-006": "test_state_saturation_occurs_at_working_current_and_voltage_boundaries",
    "CORE-NEURON-007": "test_threshold_reset_and_refractory_timing_contract",
    "CORE-NEURON-008": "test_threshold_reset_and_refractory_timing_contract",
    "CORE-NEURON-009": "test_threshold_reset_and_refractory_timing_contract",
    # Routing
    "CORE-ROUTE-001": "test_simultaneous_routes_are_stable_and_cross_source_multiplicity_is_kept",
    "CORE-ROUTE-002": "test_profile_validation_rejects_unrepresentable_configuration",
    "CORE-ROUTE-003": "test_simultaneous_routes_are_stable_and_cross_source_multiplicity_is_kept",
    "CORE-ROUTE-004": "test_simultaneous_routes_are_stable_and_cross_source_multiplicity_is_kept",
    "CORE-ROUTE-005": "test_simultaneous_routes_are_stable_and_cross_source_multiplicity_is_kept",
    "CORE-ROUTE-006": "test_reset_discards_routes_and_replays_deterministically",
    # Static configuration
    "CORE-CFG-001": "test_profile_validation_rejects_unrepresentable_configuration",
    "CORE-CFG-002": "test_profile_validation_rejects_unrepresentable_configuration",
    "CORE-CFG-003": "test_profile_validation_rejects_unrepresentable_configuration",
    # Trace
    "CORE-TRACE-001": "test_tick_trace_exposes_state_and_routing_boundaries",
    "CORE-TRACE-002": "test_tick_trace_exposes_state_and_routing_boundaries",
}


def test_every_normative_requirement_is_linked_to_an_executable_test() -> None:
    requirement_ids = set(
        re.findall(r"\bCORE-[A-Z]+-\d{3}\b", SPEC_PATH.read_text(encoding="utf-8"))
    )

    assert requirement_ids == set(REQUIREMENT_TESTS)
    for test_name in REQUIREMENT_TESTS.values():
        assert test_name in globals()
        assert callable(globals()[test_name])
