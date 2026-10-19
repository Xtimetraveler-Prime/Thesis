"""P06-B1.2 independent structural/numerical acceptance candidates.

All graphs are synthetic signed integer projections. No trained Track A files,
official MNIST TEST archives, physical FPGA or new hardware ABI are involved.
"""
from __future__ import annotations

import hashlib
import json
import os

import pytest

from loihi_twin_v2.compiler import (
    InputPopulationSpec, InputProjectionSpec, MappingError, MappingOptions,
    NetworkSpec, PopulationSpec, ProjectionConnection, ProjectionSpec, compile_network,
)
from loihi_twin_v2.compartment import CompartmentConfig
from loihi_twin_v2.p06_b12_partition import B12Options, B12Result, compile_synapse_aware

CFG_H = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
CFG_O = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)


def tiny_network(*, shuffled=False):
    incoming = (
        ProjectionConnection(0, 0, 5), ProjectionConnection(1, 0, -2),
        ProjectionConnection(0, 1, -4), ProjectionConnection(1, 1, 9),
    )
    outgoing = (
        ProjectionConnection(0, 0, 2), ProjectionConnection(1, 0, 4),
        ProjectionConnection(0, 1, -3), ProjectionConnection(1, 1, 6),
    )
    populations = (PopulationSpec("h", 2, CFG_H), PopulationSpec("z", 2, CFG_O))
    return NetworkSpec(
        populations=populations[::-1] if shuffled else populations,
        input_populations=(InputPopulationSpec("pixels", 2),),
        input_projections=(InputProjectionSpec(
            "in", "pixels", "h", incoming[::-1] if shuffled else incoming,
        ),),
        projections=(ProjectionSpec(
            "out", "h", "z", outgoing[::-1] if shuffled else outgoing,
        ),),
    )


def synthetic_dense(hidden, inputs=784, outputs=10):
    """No dataset/weights loaded. Distinct source patterns prevent fake sharing."""
    network = NetworkSpec(
        populations=(PopulationSpec("h", hidden, CFG_H),
                     PopulationSpec("z", outputs, CFG_O)),
        input_populations=(InputPopulationSpec("pixels", inputs),),
        input_projections=(InputProjectionSpec(
            "dense_input", "pixels", "h",
            tuple(ProjectionConnection(source, dest, 1 + ((41 * source + 13 * dest) % 997))
                  for source in range(inputs) for dest in range(hidden)),
        ),),
        projections=(ProjectionSpec(
            "dense_output", "h", "z",
            tuple(ProjectionConnection(source, dest, 1 + ((43 * source + 17 * dest) % 3001))
                  for source in range(hidden) for dest in range(outputs)),
        ),),
    )
    return network


def _reconstruct_edges(compiled):
    """Independently decode source and destination indices from binding tables.

    Does not call B1.2's builder or canonical private template-normalizer.
    """
    locations = {(p.core_id, p.compartment_id): (p.population, p.neuron_index)
                 for p in compiled.placement}
    inverse_ingress = {(r.destination_core, r.destination_axon):
                       ("input", r.input_population, r.input_index)
                       for r in compiled.ingress_routes}
    inverse_neural = {}
    for core in compiled.logical_deployment.core_configs:
        for entry in core.output_routes:
            source = locations[(core.core_id, entry.source_compartment)]
            for route in entry.routes:
                address = (route.destination_core, route.destination_axon)
                if address in inverse_neural:
                    raise AssertionError("duplicate source routed to same destination axon")
                inverse_neural[address] = ("neuron", *source)
    expected_bindings = set(inverse_ingress) | set(inverse_neural)
    if set(inverse_ingress) & set(inverse_neural):
        raise AssertionError("neural and input axons collided")
    actual = {}
    for core in compiled.logical_deployment.core_configs:
        templates = {t.template_id: t for t in core.synapse_templates}
        for binding in core.input_axons:
            addr = (core.core_id, binding.axon_id)
            assert addr in expected_bindings
            source = inverse_ingress.get(addr, inverse_neural.get(addr))
            for entry in templates[binding.template_id].entries:
                target = locations[(core.core_id, binding.target_offset + entry.target_compartment)]
                key = (source[0], source[1], source[2], target[0], target[1])
                assert key not in actual
                actual[key] = entry.weight
    return actual


def _expected_edges(network):
    oracle = {}
    for p in network.input_projections:
        for e in p.connections:
            oracle[("input", p.source_input, e.source_index,
                    p.destination_population, e.destination_index)] = e.weight
    for p in network.projections:
        for e in p.connections:
            oracle[("neuron", p.source_population, e.source_index,
                    p.destination_population, e.destination_index)] = e.weight
    return oracle


def test_b12_two_core_mapping_source_order_independent_and_exact_edges():
    a = compile_synapse_aware(tiny_network(), B12Options(readout_population="z"))
    b = compile_synapse_aware(tiny_network(shuffled=True), B12Options(readout_population="z"))
    assert a.fingerprint == b.fingerprint
    assert a.manifest() == b.manifest()
    assert a.capacity_audit == b.capacity_audit
    assert [(p.population, p.neuron_index, p.core_id, p.compartment_id)
            for p in a.compiled.placement] == [
                ("h", 0, 0, 0), ("h", 1, 0, 1),
                ("z", 0, 1, 0), ("z", 1, 1, 1)]
    assert _reconstruct_edges(a.compiled) == _expected_edges(tiny_network())
    assert a.capacity_audit["backing_bytes"] == 2 * 524288
    assert a.manifest()["per_core_roles"] == [
        {"core_id": 0, "population": "h", "role": "non_readout"},
        {"core_id": 1, "population": "z", "role": "readout"},
    ]


def test_b12_matches_hand_calculated_signed_lif_next_packets_and_legacy_core():
    source = tiny_network()
    fitted = compile_synapse_aware(source, B12Options(readout_population="z"))
    legacy = compile_network(source, MappingOptions(compartments_per_core=2, max_logical_cores=2))
    sample = fitted.compiled.external_packets("pixels", (0, 1), target_timestep=0)
    reference = legacy.external_packets("pixels", (0, 1), target_timestep=0)
    assert sample == reference
    assert len(sample) == 2
    for order in ((0, 1), (1, 0)):
        new = fitted.compiled.build_chip()
        original = legacy.build_chip()
        for tick in range(3):
            events = sample if tick == 0 else ()
            oevents = reference if tick == 0 else ()
            actual = new.step(events, service_order=order)
            expected = original.step(oevents, service_order=order)
            assert [trace.normalized() for trace in actual.cores] == [
                trace.normalized() for trace in expected.cores]
            if tick == 0:
                assert [trace.spikes_out for trace in actual.cores] == [(0, 1), ()]
                assert len(actual.cores[0].packets_out) == 2
                assert {packet.target_timestep for packet in actual.cores[0].packets_out} == {1}
            if tick == 1:
                assert [trace.spikes_out for trace in actual.cores] == [(), (0,)]
                assert [s.state.voltage for s in actual.cores[1].compartment_state_after] == [0, 3]


def test_b12_uses_stored_template_sharing_without_conflating_axons():
    cfg = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=3)
    network = NetworkSpec(
        populations=(PopulationSpec("z", 2, cfg),),
        input_populations=(InputPopulationSpec("x", 2),),
        input_projections=(InputProjectionSpec(
            "in", "x", "z", tuple(ProjectionConnection(s, d, 5)
                               for s in range(2) for d in range(2)),
        ),),
    )
    result = compile_synapse_aware(network, B12Options(readout_population="z"))
    core = result.compiled.logical_deployment.core_configs[0]
    assert len(core.input_axons) == 2
    assert len(core.synapse_templates) == 1
    assert len(core.synapse_templates[0].entries) == 2
    assert result.capacity_audit["cores"][0]["synapse_words"] == 2
    assert result.capacity_audit["cores"][0]["logical_synapse_bytes"] == 20
    assert _reconstruct_edges(result.compiled) == _expected_edges(network)


def test_b12_chooses_capacity_driven_3_plus_3_not_compartment_driven_6():
    network = synthetic_dense(hidden=6, inputs=4, outputs=1)
    options = B12Options(readout_population="z", synapse_bytes_per_core=80)
    result = compile_synapse_aware(network, options)
    assert result.capacity_audit["logical_core_count"] == 3
    assert result.manifest()["per_core_roles"][-1]["role"] == "readout"
    assert [
        len([p for p in result.compiled.placement if p.core_id == i]) for i in range(3)
    ] == [3, 3, 1]
    assert [core["logical_synapse_bytes"] for core in result.capacity_audit["cores"]] == [80, 80, 72]
    assert _reconstruct_edges(result.compiled) == _expected_edges(network)
    assert max(row["worst_current_bank_events"] for row in result.capacity_audit["cores"]) == 6


def test_dense_784_to_40_requires_synapse_split_and_packs_exact_ddr():
    network = synthetic_dense(40)
    result = compile_synapse_aware(network, B12Options(readout_population="z"))
    assert result.capacity_audit["logical_core_count"] == 3
    counts = [row["compartments"] for row in result.capacity_audit["cores"]]
    assert counts == [39, 1, 10]
    assert result.capacity_audit["cores"][0]["synapse_words"] == 784 * 39
    assert result.capacity_audit["cores"][0]["logical_synapse_bytes"] == 128576
    assert result.capacity_audit["cores"][0]["worst_current_bank_events"] == 784
    assert result.capacity_audit["cores"][2]["worst_current_bank_events"] == 40
    assert _reconstruct_edges(result.compiled) == _expected_edges(network)



def test_all_255_synthetic_25_input_plus_1_drain_tick_order_invariance():
    """Actual 784-channel fanout into TWO packed hidden cores each event tick.

    Integer expectation is independent of the compiler: all effective weights
    are positive and >2 in total, thus every hidden compartment spikes on all
    25 input ticks. Each readout receives those spikes one tick LATER, thus
    all ten readouts spike exactly on ticks 1..25 and never on tick 0.
    This is software-only, not a B1.3 ingress protocol or KV260 execution.
    """
    result = compile_synapse_aware(
        synthetic_dense(hidden=40), B12Options(readout_population="z"))
    compiled = result.compiled
    assert [row["worst_external_events"] for row in result.capacity_audit["cores"]] == [784, 784, 0]
    assert [row["worst_routed_events"] for row in result.capacity_audit["cores"]] == [0, 0, 40]
    expected_per_tick = []
    for tick in range(26):
        sample = compiled.external_packets(
            "pixels", range(784) if tick < 25 else (), target_timestep=tick)
        assert len(sample) == (1568 if tick < 25 else 0)
        assert all(p.target_timestep == tick for p in sample)
        expected_per_tick.append(sample)
    snapshots = []
    for order, reverse in (((0, 1, 2), False), ((2, 1, 0), True)):
        chip = compiled.build_chip()
        one_run = []
        readout_counts = [0] * 10
        for tick, events in enumerate(expected_per_tick):
            traced = chip.step(
                events, service_order=order, reverse_packet_drain=reverse)
            hidden_spikes = sum(len(c.spikes_out) for c in traced.cores[:2])
            assert hidden_spikes == (40 if tick < 25 else 0)
            assert len(traced.cores[2].packet_in) == (0 if tick == 0 else 40)
            assert len(traced.cores[2].spikes_out) == (0 if tick == 0 else 10)
            for neuron in traced.cores[2].spikes_out:
                readout_counts[neuron] += 1
            one_run.append(tuple((
                c.logical_core_id,
                c.spikes_out,
                tuple((s.state.current, s.state.voltage, s.state.refractory_remaining)
                      for s in c.compartment_state_after),
                tuple(p.logical_key for p in c.packets_out),
            ) for c in traced.cores))
        assert readout_counts == [25] * 10
        snapshots.append(one_run)
    assert snapshots[0] == snapshots[1]


@pytest.mark.parametrize("overrides,error_code", [
    ({"synapse_bytes_per_core": 79}, "b12_core_count"),
    ({"input_axons_per_core": 3}, "b12_unplaceable_neuron"),
    ({"synapse_words_per_core": 3}, "b12_unplaceable_neuron"),
    ({"event_bank_per_core": 3}, "b12_unplaceable_neuron"),
    ({"synapse_bytes_per_core": 4}, "b12_unplaceable_neuron"),
])
def test_fail_closed_impossible_budget_or_extra_core(overrides, error_code):
    network = synthetic_dense(hidden=6, inputs=4, outputs=1)
    settings = {"readout_population": "z", "max_logical_cores": 2,
                "synapse_bytes_per_core": 80}
    settings.update(overrides)
    with pytest.raises(MappingError) as captured:
        compile_synapse_aware(network, B12Options(**settings))
    assert captured.value.code == error_code


def test_route_fanout_limit_refuses_physically_unencodable_source():
    network = synthetic_dense(hidden=6, inputs=4, outputs=1)
    with pytest.raises(MappingError) as captured:
        compile_synapse_aware(network, B12Options(
            readout_population="z", route_words_per_core=2,
            synapse_bytes_per_core=80,
        ))
    assert captured.value.code == "b12_outgoing_route_capacity"


def test_p05_logical_address_budget_and_output_separation_fail_closed():
    source = synthetic_dense(hidden=126, inputs=1, outputs=1)
    with pytest.raises(MappingError) as caught:
        compile_synapse_aware(source, B12Options(
            readout_population="z", compartments_per_core=1))
    assert caught.value.code == "b12_core_count"
    for args in (
        {"readout_population": "absent"},
        {"readout_population": "z", "max_logical_cores": 127},
        {"readout_population": "z", "event_bank_per_core": 4097},
        {"readout_population": "z", "route_words_per_core": 0},
    ):
        if args["readout_population"] == "absent":
            with pytest.raises(MappingError, match="b12_readout_population"):
                compile_synapse_aware(tiny_network(), B12Options(**args))
        else:
            with pytest.raises(ValueError):
                B12Options(**args)


def test_b12_versioned_manifest_roundtrip_tamper_detected_and_sha_bound():
    result = compile_synapse_aware(tiny_network(), B12Options(readout_population="z"))
    text = result.to_json()
    loaded = B12Result.from_json(text)
    assert loaded.fingerprint == result.fingerprint
    assert loaded.capacity_audit == result.capacity_audit
    assert loaded.to_dict() == result.to_dict()
    tampered = json.loads(text)
    tampered["compiled"]["ingress_routes"][0]["destination_axon"] = 101
    with pytest.raises(ValueError, match="SHA256"):
        B12Result.from_dict(tampered)
    # Recompute the outer digest: independent source-derived manifest and
    # P03 export must still catch the changed, now invalid axon routing.
    tampered["sha256"] = hashlib.sha256(json.dumps({
        k: v for k, v in tampered.items() if k != "sha256"
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with pytest.raises((ValueError, KeyError)):
        B12Result.from_dict(tampered)


@pytest.mark.skipif(os.environ.get("P06_B12_FULL_SYNTHETIC") != "1",
                    reason="opt-in 794k-edge synthetic structure; run only on PC with sufficient RAM")
def test_full_784_1000_10_synthetic_structural_feasibility_only():
    network = synthetic_dense(1000)
    result = compile_synapse_aware(network, B12Options(readout_population="z"))
    manifest = result.capacity_audit
    assert manifest["logical_core_count"] == 27
    assert [row["compartments"] for row in manifest["cores"]] == [39] * 25 + [25, 10]
    assert sum(row["compartments"] for row in manifest["cores"]) == 1010
    assert sum(row["synapse_words"] for row in manifest["cores"]) == 794000
    assert sum(row["worst_external_events"] for row in manifest["cores"]) == 784 * 26
    assert max(row["worst_current_bank_events"] for row in manifest["cores"]) <= 4096
    assert manifest["backing_bytes"] == 27 * 524288
    assert result.compiled.report()["connection_sharing"]["expanded_connections"] == 794000
    assert manifest["physical_kv260_execution"] == "NOT_TESTED"
