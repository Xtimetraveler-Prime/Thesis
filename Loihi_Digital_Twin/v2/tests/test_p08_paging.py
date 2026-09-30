from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalChip,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    P03_REQUIRED_ARITHMETIC,
    PagedVirtualizedLogicalChip,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
    export_paged_hardware_image,
    export_virtualized_hardware_image,
)
from loihi_twin_v2.hardware_p03 import unpack_route_word
from loihi_twin_v2.paging import DeterministicContextPager


def lif() -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=5,
    )


def ring_core(core_id: int, core_count: int = 5) -> LogicalCoreConfig:
    input_axon = 10 + core_id
    next_core = (core_id + 1) % core_count
    next_axon = 10 + next_core
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(input_axon, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(
            OutputRouteEntry(0, (OutputRoute(next_core, next_axon),)),
        ),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def make_five_core_ring() -> tuple[LogicalCoreConfig, ...]:
    return tuple(ring_core(core_id) for core_id in range(5))


def accumulating_core(core_id: int) -> LogicalCoreConfig:
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(
            CompartmentConfig(
                current_decay=4096,
                voltage_decay=0,
                threshold=5,
            ),
        ),
        input_axons=(InputAxonBinding(10 + core_id, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 3),)),),
        arithmetic=P03_REQUIRED_ARITHMETIC,
    )


def run_reference(steps: int = 7) -> tuple[tuple, ...]:
    chip = LogicalChip(make_five_core_ring())
    traces = []
    for timestep in range(steps):
        external = (SpikePacket(0, 0, 10),) if timestep == 0 else ()
        traces.append(chip.step(external).normalized())
    return tuple(traces)


def run_paged(
    orders: tuple[tuple[int, ...], ...],
    *,
    reverse_drain: bool,
) -> tuple[tuple[tuple, ...], tuple[dict[str, object], ...]]:
    chip = PagedVirtualizedLogicalChip(
        make_five_core_ring(),
        resident_context_count=3,
    )
    traces = []
    schedules = []
    for timestep, order in enumerate(orders):
        external = (SpikePacket(0, 0, 10),) if timestep == 0 else ()
        trace = chip.step(
            external,
            service_order=order,
            reverse_packet_drain=reverse_drain,
        )
        traces.append(trace.normalized())
        assert chip.last_page_schedule is not None
        schedules.append(chip.last_page_schedule.as_dict())
    return tuple(traces), tuple(schedules)


def test_p08_paged_image_accepts_five_logical_cores_without_expanding_resident_slots():
    configs = make_five_core_ring()

    with pytest.raises(ValueError, match="at most 3 contexts"):
        export_virtualized_hardware_image(configs)

    image = export_paged_hardware_image(configs)
    report = image.report()

    assert report["logical_core_count"] == 5
    assert report["backing_context_count"] == 5
    assert report["resident_context_count"] == 3
    assert report["physical_engine_count"] == 1
    assert report["requires_paging"] is True
    assert report["logical_capacity_changed"] is False
    assert image.initial_resident_core_ids == (0, 1, 2)


def test_p08_resident_page_changes_slot_identity_without_rewriting_routes():
    image = export_paged_hardware_image(make_five_core_ring())
    page = image.resident_page((3, 4, 0))

    assert page.logical_to_context_slot == {3: 0, 4: 1, 0: 2}

    core3 = image.backing_by_logical_core[3].image
    assert len(core3.route_words) == 1
    route = unpack_route_word(core3.route_words[0])
    assert route["destination_core"] == 4
    assert route["destination_axon"] == 14


def test_p08_round_robin_pager_records_hits_loads_and_evictions_deterministically():
    pager = DeterministicContextPager((0, 1, 2, 3, 4), resident_context_count=3)

    schedule = pager.plan(0, service_order=(0, 1, 2, 3, 4))

    assert schedule.residency_before == (0, 1, 2)
    assert schedule.page_hit_count == 3
    assert schedule.page_load_count == 2
    assert schedule.eviction_count == 2
    assert schedule.residency_after == (3, 4, 2)
    assert [dispatch.context_slot for dispatch in schedule.dispatches] == [0, 1, 2, 0, 1]
    assert [dispatch.evicted_logical_core_id for dispatch in schedule.dispatches] == [
        None,
        None,
        None,
        0,
        1,
    ]


def test_p08_architectural_state_survives_eviction_and_reload():
    chip = PagedVirtualizedLogicalChip(
        tuple(accumulating_core(core_id) for core_id in range(5)),
        resident_context_count=3,
    )

    t0 = chip.step(
        (SpikePacket(0, 0, 10),),
        service_order=(0, 1, 2, 3, 4),
    )
    assert chip.cores[0].states[0].voltage == 3
    assert next(core for core in t0.cores if core.logical_core_id == 0).spikes_out == ()
    assert chip.last_page_schedule is not None
    assert 0 not in chip.last_page_schedule.residency_after

    t1 = chip.step(
        (SpikePacket(1, 0, 10),),
        service_order=(3, 4, 2, 1, 0),
    )
    core0 = next(core for core in t1.cores if core.logical_core_id == 0)
    assert core0.spikes_out == (0,)
    assert chip.last_page_schedule is not None
    core0_dispatch = next(
        dispatch
        for dispatch in chip.last_page_schedule.dispatches
        if dispatch.logical_core_id == 0
    )
    assert core0_dispatch.page_hit is False


def test_p08_paged_execution_matches_unpaged_logical_reference_across_page_and_drain_orders():
    forward = tuple((0, 1, 2, 3, 4) for _ in range(7))
    permuted = (
        (4, 3, 2, 1, 0),
        (1, 3, 0, 4, 2),
        (2, 4, 1, 3, 0),
        (3, 0, 4, 1, 2),
        (0, 2, 4, 1, 3),
        (4, 1, 3, 0, 2),
        (2, 0, 3, 4, 1),
    )

    reference = run_reference()
    paged_forward, forward_schedules = run_paged(forward, reverse_drain=False)
    paged_permuted, permuted_schedules = run_paged(permuted, reverse_drain=True)

    assert reference == paged_forward == paged_permuted
    assert any(schedule["page_load_count"] > 0 for schedule in forward_schedules)
    assert any(schedule["page_load_count"] > 0 for schedule in permuted_schedules)


def test_p08_pager_rejects_non_permutation_service_order():
    pager = DeterministicContextPager((0, 1, 2, 3, 4), resident_context_count=3)

    with pytest.raises(ValueError, match="permutation"):
        pager.plan(0, service_order=(0, 1, 2, 3, 3))
