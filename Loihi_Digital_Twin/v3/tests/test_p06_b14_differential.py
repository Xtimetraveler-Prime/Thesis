"""P06-B1.4 independent integer network/differential acceptance candidates.

No trained checkpoints or official MNIST TEST. Unlike B1.1-B1.3, an
independent MONOLITHIC oracle is responsible for expected states and outputs.
"""
from __future__ import annotations

from dataclasses import replace
import random

import pytest

from loihi_twin_v2.compiler import (
    InputPopulationSpec, InputProjectionSpec, NetworkSpec, PopulationSpec,
    ProjectionConnection, ProjectionSpec,
)
from loihi_twin_v2.compartment import CompartmentConfig, CompartmentState
from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b14_monolithic import (
    B14OracleError, pixel_schedule_independent, simulate_monolithic,
)
from loihi_twin_v2.p06_b14_differential import (
    B14Divergence, compare_monolithic_to_traces, run_and_compare,
)
from loihi_twin_v2.p06_input_contract import pixel_spikes


def empty_schedule(population="pixels"):
    return {population: ((),) * 26}


def two_layer_reference():
    hidden = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
    output = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)
    return NetworkSpec(
        populations=(PopulationSpec("h", 2, hidden),
                     PopulationSpec("z", 10, output)),
        input_populations=(InputPopulationSpec("pixels", 2),),
        input_projections=(InputProjectionSpec(
            "in", "pixels", "h", (
                ProjectionConnection(0, 0, 5),
                ProjectionConnection(1, 0, -2),
                ProjectionConnection(0, 1, -4),
                ProjectionConnection(1, 1, 9),
            ),
        ),),
        projections=(ProjectionSpec(
            "out", "h", "z", (
                ProjectionConnection(0, 0, 2),
                ProjectionConnection(1, 0, 4),
                ProjectionConnection(0, 1, -3),
                ProjectionConnection(1, 1, 6),
            ),
        ),),
    )


def trace_all(source, mapped, schedule, service=None, reverse=False):
    chip = mapped.compiled.build_chip()
    result = []
    for tick in range(26):
        incoming = []
        for population, rows in sorted(schedule.items()):
            active = rows[tick]
            if active:
                incoming.extend(mapped.compiled.external_packets(
                    population, active, target_timestep=tick))
        result.append(chip.step(tuple(incoming), service_order=service,
                                reverse_packet_drain=reverse))
    return tuple(result)


def test_hand_calculated_signed24_two_timestep_26_tick_oracle_and_first_class():
    source = two_layer_reference()
    schedule = {"pixels": ((0, 1),) + ((),) * 25}
    oracle = simulate_monolithic(source, schedule, readout_population="z")
    assert len(oracle.ticks) == 26
    assert oracle.ticks[0].spikes == (("h", 0), ("h", 1))
    assert dict(oracle.ticks[0].synaptic_inputs)[("h", 0)] == 3
    assert dict(oracle.ticks[0].synaptic_inputs)[("h", 1)] == 5
    assert dict(oracle.ticks[0].synaptic_inputs)[("z", 0)] == 0
    assert oracle.ticks[1].spikes == (("z", 0),)
    assert dict(oracle.ticks[1].synaptic_inputs)[("z", 0)] == 6
    assert dict(oracle.ticks[1].synaptic_inputs)[("z", 1)] == 3
    assert dict(oracle.ticks[1].after)[("z", 1)].voltage == 3
    assert oracle.ticks[2].spikes == ()
    assert oracle.readout_spike_counts == (1,) + (0,) * 9
    assert oracle.predicted_class == 0
    assert len(oracle.trace_sha256) == 64
    for limit in (1, 2, 10):
        mapped = compile_synapse_aware(
            source, B12Options(readout_population="z", compartments_per_core=limit))
        ids = tuple(core.core_id for core in mapped.compiled.logical_deployment.core_configs)
        a = run_and_compare(source, mapped, schedule, readout_population="z",
                            service_order=ids)
        b = run_and_compare(source, mapped, schedule, readout_population="z",
                            service_order=ids[::-1], reverse_packet_drain=True)
        assert a.report()["all_neuron_states_and_inputs_equal"] is True
        assert a.reference.trace_sha256 == oracle.trace_sha256
        assert a.report()["readout_spike_counts"] == [1] + [0] * 9
        assert a.output_trace_sha256 == b.output_trace_sha256
        assert a.observed_routed_packets == (4 if limit == 1 else 2)
        assert a.observed_external_packets == (4 if limit == 1 else 2)


def test_independent_pixel_encoder_agrees_with_track_a_frozen_phase_equation():
    cases = (
        bytes(784), bytes([255] * 784),
        bytes([127] * 784), bytes(range(256)) * 3 + bytes(range(16)),
        bytes((i * 37 + 19) % 256 for i in range(784)),
    )
    for pixels in cases:
        assert len(pixels) == 784
        independent = pixel_schedule_independent(pixels)
        assert len(independent) == 26 and independent[-1] == ()
        for tick in range(26):
            assert independent[tick] == pixel_spikes(pixels, tick)
    assert len(pixel_schedule_independent(bytes([255] * 784))[0]) == 784
    assert all(not row for row in pixel_schedule_independent(bytes(784)))


def test_zero_input_silence_tie_and_no_spurious_packets():
    source = two_layer_reference()
    oracle = simulate_monolithic(source, empty_schedule(), readout_population="z")
    assert oracle.spike_count == 0
    assert oracle.readout_spike_counts == (0,) * 10
    assert oracle.predicted_class == 0
    mapped = compile_synapse_aware(source, B12Options(readout_population="z",
                                                       compartments_per_core=1))
    actual = run_and_compare(source, mapped, empty_schedule(), readout_population="z")
    assert actual.observed_core_spikes == 0
    assert actual.observed_routed_packets == 0
    assert actual.observed_external_packets == 0
    assert actual.predicted_class == 0


def test_independent_encoder_and_multi_core_all_255_dense_784_to_6_to_10():
    from test_p06_b12_partition import synthetic_dense
    source = synthetic_dense(hidden=6, inputs=784, outputs=10)
    mapped = compile_synapse_aware(source, B12Options(
        readout_population="z", compartments_per_core=3))
    assert mapped.capacity_audit["logical_core_count"] == 3
    schedule = {"pixels": pixel_schedule_independent(bytes([255] * 784))}
    a = run_and_compare(source, mapped, schedule, readout_population="z")
    b = run_and_compare(source, mapped, schedule, readout_population="z",
                        service_order=(2, 1, 0), reverse_packet_drain=True)
    assert a.output_trace_sha256 == b.output_trace_sha256
    assert a.reference.trace_sha256 == b.reference.trace_sha256
    assert a.observed_external_packets == 784 * 2 * 25
    assert a.observed_routed_packets == 6 * 25
    assert a.reference.readout_spike_counts == (25,) * 10


@pytest.mark.parametrize("seed", (1, 17, 2026))
def test_randomized_signed_saturated_decays_refractory_and_cross_core(seed):
    rng = random.Random(seed)
    h = CompartmentConfig(current_decay=3072, voltage_decay=2048,
                          threshold=9, reset_voltage=-2, bias=0,
                          refractory_ticks=3)
    z = CompartmentConfig(current_decay=4096, voltage_decay=3072,
                          threshold=6, reset_voltage=-1, refractory_ticks=2)
    source = NetworkSpec(
        populations=(PopulationSpec("h", 5, h), PopulationSpec("z", 10, z)),
        input_populations=(InputPopulationSpec("pixels", 8),),
        input_projections=(InputProjectionSpec(
            "in", "pixels", "h",
            tuple(ProjectionConnection(i, j, rng.choice((-12, -4, 1, 5, 11, 17)))
                  for i in range(8) for j in range(5)),
        ),),
        projections=(ProjectionSpec(
            "out", "h", "z",
            tuple(ProjectionConnection(i, j, rng.choice((-10, -6, 1, 3, 7, 12)))
                  for i in range(5) for j in range(10)),
        ),),
    )
    # All events early; decays and refractory can extend dynamics but do not
    # create a hidden-origin packet on the final drain tick.
    rows = tuple(tuple(i for i in range(8) if rng.randrange(4) != 0)
                 if tick < 7 else () for tick in range(26))
    schedule = {"pixels": rows}
    mapped = compile_synapse_aware(
        source, B12Options(readout_population="z", compartments_per_core=2))
    ids = tuple(c.core_id for c in mapped.compiled.logical_deployment.core_configs)
    forward = run_and_compare(source, mapped, schedule, readout_population="z",
                              service_order=ids)
    backward = run_and_compare(source, mapped, schedule, readout_population="z",
                               service_order=ids[::-1], reverse_packet_drain=True)
    assert forward.output_trace_sha256 == backward.output_trace_sha256
    assert forward.reference.trace_sha256 == backward.reference.trace_sha256
    assert forward.semantic_ticks_compared == 26


def test_large_positive_and_negative_signed24_synaptic_saturation():
    high, low = (1 << 23) - 1, -(1 << 23)
    h = CompartmentConfig(current_decay=4096, voltage_decay=4096,
                          threshold=100, bias=-1)
    z = CompartmentConfig(current_decay=4096, voltage_decay=4096,
                          threshold=100)
    source = NetworkSpec(
        populations=(PopulationSpec("h", 2, h), PopulationSpec("z", 10, z)),
        input_populations=(InputPopulationSpec("pixels", 4),),
        input_projections=(InputProjectionSpec(
            "in", "pixels", "h",
            tuple(ProjectionConnection(i, 0, high) for i in range(4))
            + tuple(ProjectionConnection(i, 1, low) for i in range(4)),
        ),),
        projections=(ProjectionSpec("out", "h", "z", (
            ProjectionConnection(0, 0, high),
            ProjectionConnection(1, 1, low),
        )),),
    )
    schedule = {"pixels": ((0, 1, 2, 3),) + ((),) * 25}
    reference = simulate_monolithic(source, schedule, readout_population="z")
    after = dict(reference.ticks[0].after)
    assert after[("h", 0)].voltage == 0  # positive saturation spikes and resets
    assert after[("h", 1)].voltage == low
    assert reference.ticks[0].spikes == (("h", 0),)
    mapped = compile_synapse_aware(source, B12Options(readout_population="z"))
    comparison = run_and_compare(source, mapped, schedule, readout_population="z")
    assert comparison.observed_routed_packets == 1


def test_independent_reference_detects_mutated_state_at_first_wrong_tick_and_neuron():
    source = two_layer_reference()
    schedule = {"pixels": ((0, 1),) + ((),) * 25}
    mapped = compile_synapse_aware(source, B12Options(readout_population="z"))
    original = trace_all(source, mapped, schedule)
    modified_tick = original[1]
    readout_trace = modified_tick.cores[1]
    first = readout_trace.compartment_state_after[0]
    altered = replace(first, state=CompartmentState(
        current=first.state.current + 1,
        voltage=first.state.voltage,
        refractory_remaining=first.state.refractory_remaining))
    changed = replace(readout_trace,
                      compartment_state_after=(altered,) +
                      readout_trace.compartment_state_after[1:])
    changed_tick = replace(modified_tick,
                           cores=(modified_tick.cores[0], changed))
    tampered = original[:1] + (changed_tick,) + original[2:]
    with pytest.raises(B14Divergence) as caught:
        compare_monolithic_to_traces(
            source, mapped, schedule, tampered, readout_population="z")
    err = caught.value
    assert (err.tick, err.neuron, err.field) == (1, ("z", 0), "state_after.current")


def test_independent_reference_detects_wrong_input_weight_spike_and_next_packet():
    source = two_layer_reference()
    schedule = {"pixels": ((0, 1),) + ((),) * 25}
    mapped = compile_synapse_aware(source, B12Options(readout_population="z"))
    original = trace_all(source, mapped, schedule)
    hidden_trace = original[0].cores[0]
    assert len(hidden_trace.synaptic_contributions) > 0
    corrupt_weight = replace(hidden_trace.synaptic_contributions[0],
                             weight=hidden_trace.synaptic_contributions[0].weight + 1)
    corrupted = replace(hidden_trace, synaptic_contributions=(
        corrupt_weight,) + hidden_trace.synaptic_contributions[1:])
    altered_trace = (replace(original[0],
                             cores=(corrupted, original[0].cores[1])),) + original[1:]
    with pytest.raises(B14Divergence) as caught:
        compare_monolithic_to_traces(
            source, mapped, schedule, altered_trace, readout_population="z")
    assert caught.value.tick == 0
    assert caught.value.field == "synaptic_input"
    bad_packet = replace(hidden_trace.packets_out[0], target_timestep=7)
    corrupted_packet = replace(hidden_trace, packets_out=(
        bad_packet,) + hidden_trace.packets_out[1:])
    packet_trace = (replace(original[0],
                            cores=(corrupted_packet, original[0].cores[1])),) + original[1:]
    with pytest.raises(B14Divergence) as caught:
        compare_monolithic_to_traces(
            source, mapped, schedule, packet_trace, readout_population="z")
    assert caught.value.tick == 0
    assert caught.value.field == "NEXT_packet_target"


def test_input_contract_unknown_malformed_and_final_epoch_loss_fail_closed():
    source = two_layer_reference()
    for broken in (
        {"pixels": ((0, 0),) + ((),) * 25},
        {"pixels": ((1, 0),) + ((),) * 25},
        {"pixels": ((2,),) + ((),) * 25},
        {"pixels": ((0,),) + ((),) * 24},
        {"other": ((),) * 26},
    ):
        with pytest.raises(B14OracleError, match="schedule"):
            simulate_monolithic(source, broken, readout_population="z")
    with pytest.raises(B14OracleError, match="784"):
        pixel_schedule_independent(bytes(783))
    # Recurrent self-spike on tick25 must be rejected: there is no serviced tick26.
    cfg = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=1)
    recurrent = NetworkSpec(
        populations=(PopulationSpec("h", 1, cfg), PopulationSpec("z", 1, cfg)),
        input_populations=(InputPopulationSpec("pixels", 1),),
        input_projections=(InputProjectionSpec(
            "in", "pixels", "h", (ProjectionConnection(0, 0, 3),)),),
        projections=(ProjectionSpec(
            "recur", "h", "h", (ProjectionConnection(0, 0, 3),)),),
    )
    with pytest.raises(B14OracleError, match="final drain"):
        simulate_monolithic(recurrent,
                            {"pixels": ((0,),) + ((),) * 25},
                            readout_population="z")


@pytest.mark.skipif(
    __import__("os").environ.get("P06_B14_DENSE40") != "1",
    reason="opt-in 784×40 dense 26-tick independently checked packed trace",
)
def test_dense_784_to_40_to_10_full_numerical_26_ticks():
    from test_p06_b12_partition import synthetic_dense
    network = synthetic_dense(40)
    mapped = compile_synapse_aware(network, B12Options(readout_population="z"))
    assert mapped.capacity_audit["logical_core_count"] == 3
    schedule = {"pixels": pixel_schedule_independent(bytes([255] * 784))}
    result = run_and_compare(network, mapped, schedule, readout_population="z")
    assert result.observed_external_packets == 784 * 2 * 25
    assert result.observed_routed_packets == 40 * 25
    assert result.readout_spike_counts == (25,) * 10


@pytest.mark.skipif(
    __import__("os").environ.get("P06_B14_SPARSE27") != "1",
    reason="optional 27-core 784-channel fully numerical sparse-weight differential",
)
def test_27_core_sparse_1000_hidden_26_tick_numerical_reference():
    from loihi_twin_v2.p06_b14_synthetic_fixtures import sparse_27_core_network
    source = sparse_27_core_network()
    result = compile_synapse_aware(
        source, B12Options(readout_population="z", compartments_per_core=39))
    assert result.capacity_audit["logical_core_count"] == 27
    schedule = {"pixels": pixel_schedule_independent(bytes([255] * 784))}
    normal = run_and_compare(source, result, schedule, readout_population="z")
    backward = run_and_compare(
        source, result, schedule, readout_population="z",
        service_order=tuple(range(26, -1, -1)), reverse_packet_drain=True)
    assert normal.output_trace_sha256 == backward.output_trace_sha256
    assert normal.observed_external_packets == 20384 * 25
    assert normal.observed_routed_packets == 1000 * 25
    assert normal.readout_spike_counts == (25,) * 10
    assert normal.reference.spike_count == (1000 + 10) * 25
