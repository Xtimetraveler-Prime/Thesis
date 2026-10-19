"""P06-B1.1 numerical/capacity gates; synthetic only, no MNIST files or JTAG.

Hard-coded limits and expected numerical traces are independent of the new
contract auditor. Original P06 compiler/P03/P02/LogicalChip are test subjects.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from loihi_twin_v2.compiler import (
    InputPopulationSpec, InputProjectionSpec, MappingOptions, NetworkSpec,
    PopulationSpec, ProjectionConnection, ProjectionSpec, compile_network,
)
from loihi_twin_v2.compartment import CompartmentConfig
from loihi_twin_v2.ddr_abi import (
    P02_DDR_BANK_LAYOUT, P02_DDR_CONTEXT_STRIDE_BYTES,
    build_initial_ddr_context_record, parse_ddr_context_header, ddr_bank_slice,
)
from loihi_twin_v2.hardware_p08 import export_paged_hardware_image
from loihi_twin_v2.p06_b1_contract import (
    B1CapacityError, B1_CONTRACT_SCHEMA, CorePressure, audit_compiled_candidate,
)


def candidate():
    hidden = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
    readout = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)
    source = NetworkSpec(
        populations=(PopulationSpec("h", 2, hidden), PopulationSpec("z", 2, readout)),
        input_populations=(InputPopulationSpec("pixels", 2),),
        input_projections=(InputProjectionSpec(
            "pixels-to-h", "pixels", "h", (
                ProjectionConnection(0, 0, 5), ProjectionConnection(1, 0, -2),
                ProjectionConnection(0, 1, -4), ProjectionConnection(1, 1, 9),
            ),
        ),),
        projections=(ProjectionSpec(
            "h-to-z", "h", "z", (
                ProjectionConnection(0, 0, 2), ProjectionConnection(1, 0, 4),
                ProjectionConnection(0, 1, -3), ProjectionConnection(1, 1, 6),
            ),
        ),),
    )
    # This is a MINIMUM VIABLE partition using the existing compiler's
    # compartment-limit option, not the future B1.2 synapse-aware algorithm.
    return compile_network(source, MappingOptions(compartments_per_core=1, max_logical_cores=4))


def test_p02_512k_bank_geometry_independent_frozen_offsets():
    expected = (
        ("config", 0x01000, 16, 1024),
        ("state", 0x05000, 8, 1024),
        ("axon", 0x07000, 8, 4096),
        ("synapse", 0x0F000, 8, 32768),
        ("route_descriptor", 0x4F000, 4, 1024),
        ("route", 0x50000, 4, 4096),
        ("event0", 0x54000, 4, 4096),
        ("event1", 0x58000, 4, 4096),
        ("trace", 0x5C000, 32, 1024),
        ("packet", 0x64000, 8, 4096),
    )
    assert P02_DDR_CONTEXT_STRIDE_BYTES == 0x80000
    assert tuple((b.name, b.offset, b.word_bytes, b.depth) for b in P02_DDR_BANK_LAYOUT) == expected
    assert P02_DDR_BANK_LAYOUT[-1].end == 0x6C000
    assert 0x80000 - P02_DDR_BANK_LAYOUT[-1].end == 0x14000
    for previous, following in zip(P02_DDR_BANK_LAYOUT, P02_DDR_BANK_LAYOUT[1:]):
        assert previous.end == following.offset


def test_real_compiler_exports_four_distinct_full_ddr_records_and_three_slots():
    compiled = candidate()
    manifest = audit_compiled_candidate(compiled)
    assert manifest["schema"] == B1_CONTRACT_SCHEMA
    assert manifest["logical_core_count"] == 4
    assert manifest["resident_context_slots"] == 3
    assert manifest["physical_hls_engines"] == 1
    assert manifest["backing_bytes"] == 4 * 524288
    assert manifest["new_b1_partition_algorithm"] == "NOT_IMPLEMENTED_B1_1"
    assert manifest["p05_diagnostic_abi_scaled_compatible"] is False
    assert manifest["physical_kv260_execution"] == "NOT_TESTED"
    assert manifest["official_mnist_test_access"] == "NONE"
    assert [(row["core_id"], row["synapse_words"], row["input_axons"],
             row["logical_synapse_bytes"], row["route_words"]) for row in manifest["cores"]] == [
                 (0, 2, 2, 24, 2), (1, 2, 2, 24, 2),
                 (2, 2, 2, 24, 0), (3, 2, 2, 24, 0),
             ]
    assert [row["worst_current_bank_events"] for row in manifest["cores"]] == [2, 2, 2, 2]
    assert audit_compiled_candidate(compiled) == manifest  # repeat/byte provenance
    from loihi_twin_v2.hardware_p08 import export_paged_hardware_image
    paged = export_paged_hardware_image(compiled.logical_deployment.core_configs)
    assert paged.requires_paging
    assert paged.initial_page().logical_core_ids == (0, 1, 2)
    assert paged.resident_page((3, 1, 0)).logical_core_ids == (3, 1, 0)
    with pytest.raises(ValueError, match="slot"):
        paged.resident_page((0, 1, 2, 3))
    for context, row in zip(paged.backing_contexts, manifest["cores"]):
        record = build_initial_ddr_context_record(context)
        assert len(record) == 524288
        assert hashlib.sha256(record).hexdigest() == row["initial_ddr_sha256"]
        assert parse_ddr_context_header(record).logical_core_id == row["core_id"]
        for bank in ("event0", "event1", "trace", "packet"):
            assert not any(record[ddr_bank_slice(bank)])
        assert not any(record[0x6C000:])


def test_packed_signed24_synapses_match_independent_known_weight_sets():
    compiled = candidate()
    paged = export_paged_hardware_image(compiled.logical_deployment.core_configs)
    # Manually decode P03 [33:10] two's-complement weights, without invoking
    # P03's unpack_synapse_word or the B1 capacity audit.
    def signed24(word):
        value = (word >> 10) & 0xFFFFFF
        return value - 0x1000000 if value & 0x800000 else value
    expected = ((5, -2), (-4, 9), (2, 4), (-3, 6))
    for context, pairs in zip(paged.backing_contexts, expected):
        assert sorted(signed24(w) for w in context.image.synapse_words) == sorted(pairs)
        assert all((word & 0x3FF) == 0 for word in context.image.synapse_words)


def test_independent_hand_calculated_two_epoch_integer_spikes_and_schedule():
    compiled = candidate()
    injected = compiled.external_packets("pixels", (0, 1), target_timestep=0)
    assert len(injected) == 4  # two external channels replicated to two hidden cores
    traces = []
    for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
        chip = compiled.build_chip()
        t0 = chip.step(injected, service_order=order)
        t1 = chip.step(service_order=order)
        # Independently calculated: hidden0=5-2=3, hidden1=-4+9=5
        # both exceed 2 at tick 0. The two readouts receive NEXT packets
        # only at tick 1: output0=2+4=6>5, output1=-3+6=3<=5.
        assert [c.spikes_out for c in t0.cores] == [(0,), (0,), (), ()]
        assert [c.spikes_out for c in t1.cores] == [(), (), (0,), ()]
        assert [len(c.packets_out) for c in t0.cores] == [2, 2, 0, 0]
        assert all(p.target_timestep == 1 for c in t0.cores for p in c.packets_out)
        assert [c.compartment_state_after[0].state.voltage for c in t0.cores] == [0, 0, 0, 0]
        assert [c.compartment_state_after[0].state.voltage for c in t1.cores] == [0, 0, 0, 3]
        traces.append((tuple(c.normalized() for c in t0.cores),
                       tuple(c.normalized() for c in t1.cores)))
    assert traces[0] == traces[1]


def test_theoretical_all_255_hidden_geometry_distinguishes_39_from_40():
    # Independent pressure calculation, NOT a completed 1000-hidden mapping.
    def dense_core(hidden):
        return CorePressure(
            compartments=hidden, input_axons=784, route_words=hidden,
            synapse_words=784 * hidden, template_headers=784,
            external_events_per_tick=784, routed_events_per_tick=0,
            emitted_packets_per_tick=hidden,
        )
    assert dense_core(39).validate().synapse_bytes == 128576
    assert dense_core(39).current_event_bank_events == 784
    with pytest.raises(B1CapacityError, match="synapse_bytes: used=131712, limit=131072"):
        dense_core(40).validate()
    # At most 39 destination neurons per hidden core in THIS worst-case
    # unique-source-template profile => at least ceil(1000/39)=26 hidden.
    assert (1000 + 39 - 1) // 39 == 26


@pytest.mark.parametrize("change,name", [
    ({"compartments": 1025}, "compartments"),
    ({"input_axons": 4097}, "input_axons"),
    ({"route_words": 4097}, "route_words"),
    ({"synapse_words": 32769}, "synapse_words"),
    ({"external_events_per_tick": 784, "routed_events_per_tick": 3313},
     "current_event_bank_events"),
    ({"emitted_packets_per_tick": 4097}, "emitted_packets_per_tick"),
    ({"input_axons": -1}, "nonnegative"),
])
def test_independent_capacity_violations_fail_closed(change, name):
    args = dict(compartments=1, input_axons=1, route_words=0,
                synapse_words=1, template_headers=1,
                external_events_per_tick=0, routed_events_per_tick=0,
                emitted_packets_per_tick=0)
    args.update(change)
    with pytest.raises(ValueError, match=name):
        CorePressure(**args).validate()


def test_synapse_budget_exact_edge_and_event_bank_exact_edge():
    ok = CorePressure(
        compartments=1, input_axons=1, route_words=1,
        synapse_words=32766, template_headers=1,
        external_events_per_tick=784, routed_events_per_tick=3312,
        emitted_packets_per_tick=4096,
    )
    assert ok.synapse_bytes == 131072
    assert ok.current_event_bank_events == 4096
    ok.validate()
    with pytest.raises(B1CapacityError, match="synapse_bytes"):
        replace(ok, synapse_words=32767).validate()


def test_initial_ddr_record_corruption_rejected_by_real_crc_parser():
    compiled = candidate()
    context = export_paged_hardware_image(
        compiled.logical_deployment.core_configs).backing_contexts[0]
    record = bytearray(build_initial_ddr_context_record(context))
    record[0x0F000] ^= 0x01
    with pytest.raises(ValueError, match="SHA-256"):
        parse_ddr_context_header(bytes(record))
    with pytest.raises(ValueError, match="exactly"):
        parse_ddr_context_header(bytes(record[:-1]))
