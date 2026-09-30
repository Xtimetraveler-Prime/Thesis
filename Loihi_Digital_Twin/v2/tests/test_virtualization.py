from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    ResourceCapacityError,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
    VirtualizedLogicalChip,
)


def lif(threshold: int = 5) -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=threshold,
    )


def ring_core(core_id: int, input_axon: int, next_core: int, next_axon: int) -> LogicalCoreConfig:
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(input_axon, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(
            OutputRouteEntry(0, (OutputRoute(next_core, next_axon),)),
        ),
    )


def make_three_core_ring() -> tuple[LogicalCoreConfig, ...]:
    return (
        ring_core(0, 10, 1, 11),
        ring_core(1, 11, 2, 12),
        ring_core(2, 12, 0, 10),
    )


def run_ring(
    physical_engine_count: int,
    service_orders: tuple[tuple[int, ...], ...],
    *,
    reverse_drain: bool = False,
) -> tuple[tuple, ...]:
    chip = VirtualizedLogicalChip(
        make_three_core_ring(),
        physical_engine_count=physical_engine_count,
    )
    traces = []
    for timestep, order in enumerate(service_orders):
        external = (SpikePacket(0, 0, 10),) if timestep == 0 else ()
        trace = chip.step(
            external,
            service_order=order,
            reverse_packet_drain=reverse_drain,
        )
        traces.append(trace.normalized())
    return tuple(traces)


def test_p05_one_engine_services_more_logical_cores_than_physically_instantiated():
    chip = VirtualizedLogicalChip(make_three_core_ring(), physical_engine_count=1)

    trace = chip.step(
        (SpikePacket(0, 0, 10),),
        service_order=(0, 1, 2),
    )

    assert trace.algorithmic_timestep == 0
    assert chip.report.logical_core_count == 3
    assert chip.report.physical_engine_count == 1
    assert chip.report.virtualization_ratio == 3.0
    assert chip.last_schedule is not None
    assert chip.last_schedule.wave_count == 3
    assert [dispatch.physical_engine_id for dispatch in chip.last_schedule.dispatches] == [0, 0, 0]
    assert [dispatch.logical_core_id for dispatch in chip.last_schedule.dispatches] == [0, 1, 2]


def test_p05_virtualization_invariance_across_one_two_and_three_physical_engines():
    orders = (
        (0, 1, 2),
        (2, 1, 0),
        (1, 0, 2),
        (0, 2, 1),
    )

    one_engine = run_ring(1, orders)
    two_engines = run_ring(2, orders)
    three_engines = run_ring(3, orders)

    assert one_engine == two_engines == three_engines


def test_p05_virtualization_invariance_across_logical_service_and_packet_drain_orders():
    forward_orders = (
        (0, 1, 2),
        (0, 1, 2),
        (0, 1, 2),
        (0, 1, 2),
    )
    permuted_orders = (
        (2, 0, 1),
        (1, 2, 0),
        (2, 1, 0),
        (1, 0, 2),
    )

    forward = run_ring(1, forward_orders, reverse_drain=False)
    permuted = run_ring(1, permuted_orders, reverse_drain=True)

    assert forward == permuted


def test_p05_physical_engine_assignment_never_changes_logical_packet_identity():
    chip = VirtualizedLogicalChip(make_three_core_ring(), physical_engine_count=2)

    t0 = chip.step(
        (SpikePacket(0, 0, 10),),
        service_order=(0, 1, 2),
        physical_engine_order=(1, 0),
    )
    source = next(core for core in t0.cores if core.logical_core_id == 0)

    assert source.spikes_out == (0,)
    assert len(source.packets_out) == 1
    packet = source.packets_out[0]
    assert packet.source_core == 0
    assert packet.destination_core == 1
    assert packet.destination_axon == 11
    assert chip.last_schedule is not None
    assert chip.last_schedule.dispatches[0].physical_engine_id == 1


def test_p05_logical_capacity_validation_precedes_and_cannot_be_bypassed_by_virtualization():
    too_many_compartments = tuple(lif() for _ in range(1025))

    with pytest.raises(ResourceCapacityError) as excinfo:
        LogicalCoreConfig(core_id=0, compartments=too_many_compartments)

    assert excinfo.value.resource == "compartments"
    assert excinfo.value.used == 1025
    assert excinfo.value.limit == 1024
