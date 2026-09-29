from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    CompartmentConfig,
    InputAxonBinding,
    LogicalChip,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    RouteScope,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
)


def lif(threshold: int = 5) -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=threshold,
    )


def input_core(core_id: int, axon_id: int, weight: int = 6, *, routes=()) -> LogicalCoreConfig:
    return LogicalCoreConfig(
        core_id=core_id,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(axon_id=axon_id, template_id=0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, weight),)),),
        output_routes=(OutputRouteEntry(0, tuple(routes)),) if routes else (),
    )


def trace_for_core(trace, core_id: int):
    return next(core for core in trace.cores if core.logical_core_id == core_id)


def test_t2_two_core_feed_forward_packet_is_applied_next_timestep():
    core0 = input_core(0, 0, routes=(OutputRoute(1, 3),))
    core1 = input_core(1, 3)
    chip = LogicalChip((core0, core1))

    t0 = chip.step((SpikePacket(0, 0, 0),))
    assert trace_for_core(t0, 0).spikes_out == (0,)
    assert trace_for_core(t0, 1).spikes_out == ()
    assert trace_for_core(t0, 0).packets_out[0].target_timestep == 1
    assert trace_for_core(t0, 0).packets_out[0].destination_core == 1
    assert trace_for_core(t0, 0).packets_out[0].destination_axon == 3

    t1 = chip.step()
    assert trace_for_core(t1, 1).spikes_out == (0,)
    assert len(trace_for_core(t1, 1).packet_in) == 1
    assert trace_for_core(t1, 1).synaptic_contributions[0].weight == 6


def test_t3_multicast_expands_to_explicit_per_destination_packets():
    source = input_core(
        0,
        0,
        routes=(OutputRoute(1, 1), OutputRoute(2, 2)),
    )
    core1 = input_core(1, 1)
    core2 = input_core(2, 2)
    chip = LogicalChip((source, core1, core2))

    t0 = chip.step((SpikePacket(0, 0, 0),))
    packets = trace_for_core(t0, 0).packets_out
    assert [(p.destination_core, p.destination_axon) for p in packets] == [(1, 1), (2, 2)]

    t1 = chip.step()
    assert trace_for_core(t1, 1).spikes_out == (0,)
    assert trace_for_core(t1, 2).spikes_out == (0,)


def test_t4_same_timestep_packet_order_does_not_change_normalized_state_or_trace():
    config = LogicalCoreConfig(
        core_id=0,
        compartments=(lif(threshold=100),),
        input_axons=(
            InputAxonBinding(0, 0),
            InputAxonBinding(1, 1),
        ),
        synapse_templates=(
            SynapseTemplate(0, (SynapseEntry(0, 2),)),
            SynapseTemplate(1, (SynapseEntry(0, 3),)),
        ),
    )
    packets = (SpikePacket(0, 0, 0), SpikePacket(0, 0, 1))

    first = LogicalChip((config,)).step(packets)
    second = LogicalChip((config,)).step(tuple(reversed(packets)))

    assert first.normalized() == second.normalized()
    assert trace_for_core(first, 0).compartment_state_after[0].state.voltage == 5


def test_t5_barrier_blocks_advance_until_routed_packet_is_drained():
    core0 = input_core(0, 0, routes=(OutputRoute(1, 3),))
    core1 = input_core(1, 3)
    chip = LogicalChip((core0, core1))

    chip.evaluate((SpikePacket(0, 0, 0),))
    assert chip.router.pending_count == 1
    assert not chip.can_advance
    with pytest.raises(RuntimeError, match="cannot advance"):
        chip.advance()

    delivered = chip.drain_packets(limit=1)
    assert len(delivered) == 1
    assert chip.can_advance
    trace = chip.advance()
    assert trace.barrier.can_advance
    assert trace.barrier.in_flight_packets == 0
    assert chip.current_timestep == 1


def test_t6_cross_core_recurrence_progresses_one_architectural_boundary_at_a_time():
    core0 = LogicalCoreConfig(
        core_id=0,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(0, 0), InputAxonBinding(2, 0)),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(OutputRouteEntry(0, (OutputRoute(1, 1),)),),
    )
    core1 = input_core(1, 1, routes=(OutputRoute(0, 2),))
    chip = LogicalChip((core0, core1))

    t0 = chip.step((SpikePacket(0, 0, 0),))
    t1 = chip.step()
    t2 = chip.step()

    assert trace_for_core(t0, 0).spikes_out == (0,)
    assert trace_for_core(t0, 1).spikes_out == ()
    assert trace_for_core(t1, 1).spikes_out == (0,)
    assert trace_for_core(t1, 0).spikes_out == ()
    assert trace_for_core(t2, 0).spikes_out == (0,)


def test_t9_core_service_order_and_router_drain_order_do_not_change_normalized_trace():
    core0 = input_core(0, 0, routes=(OutputRoute(1, 1),))
    core1 = input_core(1, 1, routes=(OutputRoute(0, 0),))
    packets = (SpikePacket(0, 0, 0), SpikePacket(0, 1, 1))

    a = LogicalChip((core0, core1)).step(
        packets,
        service_order=(0, 1),
        reverse_packet_drain=False,
    )
    b = LogicalChip((core0, core1)).step(
        tuple(reversed(packets)),
        service_order=(1, 0),
        reverse_packet_drain=True,
    )

    assert a.normalized() == b.normalized()


def test_p04_local_and_remote_fanout_are_explicit_and_share_barrier_semantics():
    source = LogicalCoreConfig(
        core_id=0,
        compartments=(lif(),),
        input_axons=(
            InputAxonBinding(0, 0),
            InputAxonBinding(2, 0),
        ),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 6),)),),
        output_routes=(
            OutputRouteEntry(
                0,
                (
                    OutputRoute(0, 2),
                    OutputRoute(1, 1),
                ),
            ),
        ),
    )
    remote = input_core(1, 1)
    chip = LogicalChip((source, remote))

    t0 = chip.step((SpikePacket(0, 0, 0),))
    packets = trace_for_core(t0, 0).packets_out
    assert [packet.route_scope for packet in packets] == [RouteScope.LOCAL, RouteScope.REMOTE]
    assert (1, 0, 0, "local", 1) in t0.packet_traffic
    assert (1, 0, 1, "remote", 1) in t0.packet_traffic
    assert t0.barrier.can_advance

    t1 = chip.step()
    assert trace_for_core(t1, 0).spikes_out == (0,)
    assert trace_for_core(t1, 1).spikes_out == (0,)


def test_p04_simultaneous_remote_producers_fan_in_deterministically():
    core0 = input_core(0, 0, routes=(OutputRoute(2, 10),))
    core1 = input_core(1, 1, routes=(OutputRoute(2, 11),))
    core2 = LogicalCoreConfig(
        core_id=2,
        compartments=(lif(),),
        input_axons=(
            InputAxonBinding(10, 0),
            InputAxonBinding(11, 1),
        ),
        synapse_templates=(
            SynapseTemplate(0, (SynapseEntry(0, 3),)),
            SynapseTemplate(1, (SynapseEntry(0, 4),)),
        ),
    )
    packets = (SpikePacket(0, 0, 0), SpikePacket(0, 1, 1))

    first_chip = LogicalChip((core0, core1, core2))
    second_chip = LogicalChip((core0, core1, core2))
    first_t0 = first_chip.step(packets, service_order=(0, 1, 2))
    second_t0 = second_chip.step(tuple(reversed(packets)), service_order=(1, 0, 2))

    assert first_t0.normalized() == second_t0.normalized()
    assert (1, 0, 2, "remote", 1) in first_t0.packet_traffic
    assert (1, 1, 2, "remote", 1) in first_t0.packet_traffic

    first_t1 = first_chip.step()
    second_t1 = second_chip.step(service_order=(2, 1, 0), reverse_packet_drain=True)
    assert first_t1.normalized() == second_t1.normalized()
    destination = trace_for_core(first_t1, 2)
    assert [item.weight for item in destination.synaptic_contributions] == [3, 4]
    assert destination.compartment_state_after[0].state.voltage == 7
    assert destination.spikes_out == (0,)
