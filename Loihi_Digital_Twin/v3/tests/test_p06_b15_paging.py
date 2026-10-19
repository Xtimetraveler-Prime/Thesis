"""B1.5 host-only deterministic residency, P05 transfer-traffic and parity gates.

Hard-coded physically measured P05.2i 80-dispatch arithmetic is an
INDEPENDENT historical sanity proof, NOT a new 27-core KV260 result.
No board, DDR writes, trained model, official TEST or timing measurement.
"""
from __future__ import annotations

from dataclasses import replace
import os

import pytest

from loihi_twin_v2.compiler import (
    InputPopulationSpec, InputProjectionSpec, NetworkSpec, PopulationSpec,
    ProjectionConnection, ProjectionSpec,
)
from loihi_twin_v2.compartment import CompartmentConfig
from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b14_differential import run_and_compare
from loihi_twin_v2.p06_b14_monolithic import pixel_schedule_independent
from loihi_twin_v2.p06_b15_paging import (
    B15ScheduleError, ResidentLRU, run_paged_model,
    project_schedule_only, hypothetical_transport_seconds,
)


def small_four_core():
    hidden = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
    readout = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)
    network = NetworkSpec(
        populations=(PopulationSpec("h", 2, hidden), PopulationSpec("z", 2, readout)),
        input_populations=(InputPopulationSpec("pixels", 2),),
        input_projections=(InputProjectionSpec(
            "input", "pixels", "h", (
                ProjectionConnection(0, 0, 5), ProjectionConnection(1, 0, -2),
                ProjectionConnection(0, 1, -4), ProjectionConnection(1, 1, 9),
            ),
        ),),
        projections=(ProjectionSpec(
            "hidden_to_readout", "h", "z", (
                ProjectionConnection(0, 0, 2), ProjectionConnection(1, 0, 4),
                ProjectionConnection(0, 1, -3), ProjectionConnection(1, 1, 6),
            ),
        ),),
    )
    mapping = compile_synapse_aware(network, B12Options(
        readout_population="z", compartments_per_core=1))
    assert mapping.capacity_audit["logical_core_count"] == 4
    schedule = {"pixels": ((0, 1),) + ((),) * 25}
    return network, mapping, schedule


def _alternate(ids):
    return tuple(ids if tick % 2 == 0 else ids[::-1] for tick in range(26))


def test_reference_p05_2i_exact_measured_page_bytes_from_80_dispatches():
    # Independent numerical values from the accepted original PHYSICAL P05.2i
    # MMIO read-only counters, for five cores × 16 ticks, not a new run.
    ids = (0, 1, 2, 3, 4)
    paging = ResidentLRU(ids)
    for tick in range(16):
        for i, core in enumerate(ids):
            paging.visit(tick, tick * 5 + i, core)
    paging.flush()
    report = paging.report()
    assert report["dispatches"] == 80
    assert report["global_barriers"] == 16
    assert report["resident_context_slots"] == 3
    assert report["full_page_ins"] == 80
    assert report["initial_empty_slot_page_ins"] == 3
    assert report["replacement_page_ins"] == 77
    assert report["dirty_evictions"] == 77
    assert report["runtime_mutable_page_outs"] == 77
    assert report["final_mutable_page_outs"] == 3
    assert report["all_mutable_page_outs"] == 80
    assert report["estimated_page_engine_read_bytes"] == 80 * 438272
    assert report["estimated_page_engine_write_bytes"] == 80 * 106496
    assert report["estimated_read_bursts_256B"] == 136960
    assert report["estimated_write_bursts_256B"] == 33280
    assert report["estimated_page_engine_total_bytes"] == 43581440
    assert report["physical_scaled_page_traffic_measured"] is False


def test_direct_cache_exact_lru_slots_victim_hits_and_final_flush():
    paging = ResidentLRU((0, 1, 2, 3))
    ops = [paging.visit(0, ordinal, core) for ordinal, core in enumerate((0, 1, 2, 3))]
    assert [op.slot for op in ops] == [0, 1, 2, 0]
    assert [op.evicted_core for op in ops] == [None, None, None, 0]
    assert [op.hit for op in ops] == [False] * 4
    assert [op.page_in_bytes for op in ops] == [438272] * 4
    assert [op.mutable_page_out_bytes for op in ops] == [0, 0, 0, 106496]
    assert [op.backing_ddr_offset_bytes for op in ops] == [
        0, 524288, 1048576, 1572864]
    later = [paging.visit(1, 4 + i, core) for i, core in enumerate((3, 2, 1, 0))]
    assert [op.hit for op in later] == [True, True, True, False]
    assert later[-1].evicted_core == 3
    final = paging.flush()
    assert {(f.slot, f.core_id) for f in final} == {(0, 0), (1, 1), (2, 2)}
    report = paging.report()
    assert report["page_hits"] == 3
    assert report["full_page_ins"] == 5
    assert report["dirty_evictions"] == 2
    assert report["final_mutable_page_outs"] == 3
    assert report["all_mutable_page_outs"] == 5
    assert report["estimated_page_engine_total_bytes"] == 5 * (438272 + 106496)
    with pytest.raises(B15ScheduleError, match="final flush already"):
        paging.flush()
    with pytest.raises(B15ScheduleError, match="after final"):
        paging.visit(2, 8, 0)


def test_resident_1_to_3_core_regime_only_initial_load_and_final_flush():
    for count in (1, 2, 3):
        page = ResidentLRU(tuple(range(count)))
        for tick in range(26):
            for core in range(count):
                page.visit(tick, tick * count + core, core)
        page.flush()
        summary = page.report()
        assert summary["resident_context_slots"] == count
        assert summary["full_page_ins"] == count
        assert summary["page_hits"] == count * 25
        assert summary["dirty_evictions"] == 0
        assert summary["final_mutable_page_outs"] == count
        assert summary["estimated_page_engine_total_bytes"] == count * 544768


def test_b15_serial_4_core_round_robin_26_tick_matches_independent_monolithic():
    source, mapped, schedule = small_four_core()
    run = run_paged_model(source, mapped, schedule, readout_population="z")
    report = run.report()
    paging = report["paging"]
    assert report["schema"].startswith("p06-b1.5-")
    assert paging["dispatches"] == 26 * 4
    assert paging["global_barriers"] == 26
    assert paging["resident_context_slots"] == 3
    assert paging["one_engine_max_in_flight_dispatches"] == 1
    assert paging["full_page_ins"] == 104
    assert paging["page_hits"] == 0
    assert paging["dirty_evictions"] == 101
    assert paging["final_mutable_page_outs"] == 3
    assert paging["all_mutable_page_outs"] == 104
    assert paging["estimated_page_engine_total_bytes"] == 104 * 544768
    assert report["predicted_class"] == 0
    assert report["readout_spike_counts"] == [1, 0]
    assert report["algorithmic_neural_parity"] is True
    assert report["routed_packet_events"] == 4
    assert report["physical_kv260_execution"] == "NOT_TESTED"
    assert report["actual_ddr_mutable_bytes_materialized"] is False
    assert len(run.page_operations) == 104
    assert len(run.initial_ddr_backing) == 4
    assert [rec["ddr_offset_bytes"] for rec in run.initial_ddr_backing] == [
        0, 524288, 1048576, 1572864]
    assert all(rec["full_ddr_record_bytes"] == 524288 for rec in run.initial_ddr_backing)
    assert all(len(rec["initial_ddr_sha256"]) == 64 for rec in run.initial_ddr_backing)
    assert all(e.finished_barrier for e in run.epochs)
    assert [e.next_bank for e in run.epochs] == [(t + 1) % 2 for t in range(26)]
    assert [e.emitted_packets for e in run.epochs] == [4] + [0] * 25
    assert run.epochs[0].nonresident_at_emission_packets == 4


def test_alternating_service_order_reduces_page_faults_but_not_numerics():
    source, mapped, schedule = small_four_core()
    forward = run_paged_model(source, mapped, schedule, readout_population="z")
    reversed_epochs = run_paged_model(
        source, mapped, schedule, readout_population="z",
        service_orders=_alternate((0, 1, 2, 3)))
    check = run_and_compare(source, mapped, schedule, readout_population="z")
    assert forward.comparison.output_trace_sha256 == reversed_epochs.comparison.output_trace_sha256
    assert forward.comparison.output_trace_sha256 == check.output_trace_sha256
    assert forward.comparison.reference.trace_sha256 == reversed_epochs.comparison.reference.trace_sha256
    assert forward.operations_sha256 != reversed_epochs.operations_sha256
    assert reversed_epochs.traffic["page_hits"] == 75
    assert reversed_epochs.traffic["full_page_ins"] == 29
    assert reversed_epochs.traffic["dirty_evictions"] == 26
    assert reversed_epochs.traffic["final_mutable_page_outs"] == 3
    assert reversed_epochs.traffic["estimated_page_engine_total_bytes"] == 29 * 544768
    assert reversed_epochs.report()["routed_packet_events"] == forward.report()["routed_packet_events"]
    assert reversed_epochs.report()["predicted_class"] == forward.report()["predicted_class"]
    # Compare *raw* normalized per-core traces against the accepted unpaged
    # LogicalChip, not just the independent semantic hash.
    chip = mapped.compiled.build_chip()
    for tick, page_trace in enumerate(reversed_epochs.logical_traces):
        injected = mapped.compiled.external_packets(
            "pixels", schedule["pixels"][tick], target_timestep=tick) if schedule["pixels"][tick] else ()
        old = chip.step(injected, service_order=_alternate((0, 1, 2, 3))[tick],
                        reverse_packet_drain=True)
        assert tuple(c.normalized() for c in page_trace.cores) == tuple(
            c.normalized() for c in old.cores)


def test_static_page_planner_preserves_ddr_provenance_and_matches_dynamic_traffic():
    source, mapped, schedule = small_four_core()
    dynamic = run_paged_model(source, mapped, schedule, readout_population="z")
    structural = project_schedule_only(mapped)
    assert structural["mode"] == "STRUCTURAL_SCHEDULE_ONLY_NO_NEURAL_EXECUTION"
    assert structural["neural_equivalence_evaluated"] is False
    assert structural["schedule_sha256"] == dynamic.operations_sha256
    assert structural["paging"] == dynamic.traffic
    assert structural["full_ddr_backing_bytes_total"] == 4 * 524288
    assert len(structural["initial_backing_manifest"]) == 4
    assert [c["initial_ddr_sha256"] for c in structural["initial_backing_manifest"]] == [
        c["initial_ddr_sha256"] for c in dynamic.initial_ddr_backing]
    assert structural["worst_current_events_any_core"] <= 4096
    assert structural["physical_scaled_page_traffic_measured"] is False
    assert structural["actual_mutable_ddr_images_materialized"] is False
    assert structural["latency_seconds"] is None


def test_scenario_only_bandwidth_arithmetic_requires_explicit_valid_assumption():
    assert hypothetical_transport_seconds(1 << 30, 1.0) == 1.0
    assert hypothetical_transport_seconds(0, 1) == 0.0
    with pytest.raises(B15ScheduleError, match="GiB/s"):
        hypothetical_transport_seconds(544768, 0)
    with pytest.raises(B15ScheduleError, match="GiB/s"):
        hypothetical_transport_seconds(544768, float("nan"))
    with pytest.raises(B15ScheduleError, match="nonnegative"):
        hypothetical_transport_seconds(-1, 1.0)


def test_rejects_invalid_order_unknown_source_or_missing_final_flush():
    source, mapped, schedule = small_four_core()
    orders = tuple((0, 1, 2, 3) for _ in range(26))
    for invalid in (
        (orders[:-1], "26"),
        (orders[:1] + ((0, 0, 2, 3),) + orders[2:], "permutation"),
        (orders[:1] + ((0, 1, 2, 4),) + orders[2:], "permutation"),
    ):
        with pytest.raises(B15ScheduleError, match=invalid[1]):
            run_paged_model(source, mapped, schedule, readout_population="z",
                            service_orders=invalid[0])
    with pytest.raises(B15ScheduleError, match="final mutable"):
        run_paged_model(source, mapped, schedule, readout_population="z",
                        flush_at_end=False)
    with pytest.raises(B15ScheduleError, match="audit mismatch"):
        bad = replace(mapped, capacity_audit={
            **mapped.capacity_audit, "original_compiled_sha256": "bad"})
        run_paged_model(source, bad, schedule, readout_population="z")
    with pytest.raises(B15ScheduleError, match="unknown logical core"):
        ResidentLRU((0, 1, 2)).visit(0, 0, 3)
    with pytest.raises(B15ScheduleError, match="sorted"):
        ResidentLRU((2, 1, 0))
    with pytest.raises(B15ScheduleError, match="unique"):
        ResidentLRU((0, 1, 1))


@pytest.mark.skipif(
    os.environ.get("P06_B15_SPARSE27") != "1",
    reason="opt-in 27-core full 26-tick neural/P05 paging oracle, host memory-intensive",
)
def test_full_27_core_26_tick_sparse_numerical_traffic_estimate():
    from loihi_twin_v2.p06_b14_synthetic_fixtures import sparse_27_core_network
    source = sparse_27_core_network()
    mapped = compile_synapse_aware(
        source, B12Options(readout_population="z", compartments_per_core=39))
    events = {"pixels": pixel_schedule_independent(bytes([255] * 784))}
    results = []
    for alternating in (False, True):
        report = run_paged_model(
            source, mapped, events, readout_population="z",
            service_orders=_alternate(tuple(range(27))) if alternating else None)
        results.append(report)
        assert report.traffic["dispatches"] == 702
        assert report.traffic["global_barriers"] == 26
        assert report.report()["routed_packet_events"] == 25000
        assert report.comparison.observed_external_packets == 509600
        assert report.comparison.readout_spike_counts == (25,) * 10
        assert report.report()["physical_kv260_execution"] == "NOT_TESTED"
        assert report.report()["latency_seconds"] is None
    forward, alternating = results
    assert forward.comparison.output_trace_sha256 == alternating.comparison.output_trace_sha256
    assert forward.traffic["full_page_ins"] == 702
    assert forward.traffic["dirty_evictions"] == 699
    assert forward.traffic["final_mutable_page_outs"] == 3
    assert forward.traffic["estimated_page_engine_total_bytes"] == 702 * 544768
    assert alternating.traffic["full_page_ins"] == 627
    assert alternating.traffic["page_hits"] == 75
    assert alternating.traffic["dirty_evictions"] == 624
    assert alternating.traffic["final_mutable_page_outs"] == 3
    assert alternating.traffic["estimated_page_engine_total_bytes"] == 627 * 544768


@pytest.mark.skipif(
    os.environ.get("P06_B15_DENSE27") != "1",
    reason="opt-in 794k-edge DENSE 27-core structural paging estimate only",
)
def test_full_27_core_dense_structural_schedule_only_vs_alternating_lru():
    from test_p06_b12_partition import synthetic_dense
    network = synthetic_dense(1000)
    mapped = compile_synapse_aware(network, B12Options(readout_population="z"))
    assert mapped.capacity_audit["logical_core_count"] == 27
    forward = project_schedule_only(mapped)
    alternating = project_schedule_only(mapped, service_orders=_alternate(tuple(range(27))))
    assert forward["mode"] == "STRUCTURAL_SCHEDULE_ONLY_NO_NEURAL_EXECUTION"
    assert forward["full_ddr_backing_bytes_total"] == 14155776
    assert forward["worst_current_events_any_core"] == 1000
    assert forward["worst_emitted_packets_any_core"] == 39
    assert forward["paging"]["dispatches"] == 702
    assert forward["paging"]["full_page_ins"] == 702
    assert forward["paging"]["dirty_evictions"] == 699
    assert forward["paging"]["final_mutable_page_outs"] == 3
    assert forward["paging"]["estimated_page_engine_read_bytes"] == 307666944
    assert forward["paging"]["estimated_page_engine_write_bytes"] == 74760192
    assert forward["paging"]["estimated_page_engine_total_bytes"] == 382427136
    assert alternating["paging"]["full_page_ins"] == 627
    assert alternating["paging"]["page_hits"] == 75
    assert alternating["paging"]["dirty_evictions"] == 624
    assert alternating["paging"]["estimated_page_engine_total_bytes"] == 627 * 544768
    assert forward["schedule_sha256"] != alternating["schedule_sha256"]
    assert forward["neural_equivalence_evaluated"] is False
    assert alternating["physical_scaled_page_traffic_measured"] is False
