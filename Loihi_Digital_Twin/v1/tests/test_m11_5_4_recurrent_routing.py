from __future__ import annotations

import pytest

from neuromorphic_twin.fpga_core_capacity import FpgaCoreCapacity
from neuromorphic_twin.fpga_recurrent_routing import (
    DoubleBufferedRecurrentQueue,
    FrozenRouteStorage,
    freeze_spike_routes_v1,
    reset_recurrent_queue_v1,
    route_and_commit_recurrent_v1,
)
from neuromorphic_twin.model import SpikeRoute


def _routes() -> FrozenRouteStorage:
    # Deliberately declare sources out of source-ID order. Declaration order
    # within source 1 is 8 then 7 and must remain that way after CSR freezing.
    return freeze_spike_routes_v1(
        (
            SpikeRoute(source_neuron=2, target_axon=9),
            SpikeRoute(source_neuron=1, target_axon=8),
            SpikeRoute(source_neuron=0, target_axon=6),
            SpikeRoute(source_neuron=1, target_axon=7),
            SpikeRoute(source_neuron=2, target_axon=6),
        ),
        neuron_count=3,
    )


def test_route_freezer_groups_sources_and_preserves_declaration_order() -> None:
    storage = _routes()
    assert storage.row_pointers == (0, 1, 3, 5)
    assert storage.target_axons == (6, 8, 7, 9, 6)
    assert storage.targets_for_source(0) == (6,)
    assert storage.targets_for_source(1) == (8, 7)
    assert storage.targets_for_source(2) == (9, 6)


def test_simultaneous_spikes_route_in_ascending_source_then_declaration_order() -> None:
    result = route_and_commit_recurrent_v1(
        DoubleBufferedRecurrentQueue.empty(),
        _routes(),
        (True, True, True),
    )
    assert result.consumed_recurrent_axons == ()
    assert result.routed_output_axons == (6, 8, 7, 9, 6)
    assert result.queue_after_commit.current_bank == 1
    assert result.queue_after_commit.current_events == (6, 8, 7, 9, 6)


def test_same_target_from_different_sources_preserves_multiplicity() -> None:
    result = route_and_commit_recurrent_v1(
        DoubleBufferedRecurrentQueue.empty(),
        _routes(),
        (True, False, True),
    )
    assert result.routed_output_axons == (6, 9, 6)
    assert result.routed_output_axons.count(6) == 2


def test_new_recurrence_is_not_consumed_until_next_tick() -> None:
    queue = DoubleBufferedRecurrentQueue(
        current_bank=0,
        bank0=(3, 4),
        bank1=(99,),  # stale inactive-bank content must be overwritten
    )
    first = route_and_commit_recurrent_v1(queue, _routes(), (True, False, False))

    # Tick t consumes only the bank that existed before routing.
    assert first.consumed_recurrent_axons == (3, 4)
    assert first.routed_output_axons == (6,)
    assert first.queue_after_commit.current_bank == 1
    assert first.queue_after_commit.current_events == (6,)
    assert 6 not in first.consumed_recurrent_axons

    # Tick t+1 can now consume the event emitted by tick t.
    second = route_and_commit_recurrent_v1(
        first.queue_after_commit,
        _routes(),
        (False, False, False),
    )
    assert second.consumed_recurrent_axons == (6,)
    assert second.routed_output_axons == ()
    assert second.queue_after_commit.current_bank == 0
    assert second.queue_after_commit.current_events == ()


def test_no_spikes_replaces_inactive_bank_and_prevents_stale_replay() -> None:
    queue = DoubleBufferedRecurrentQueue(
        current_bank=0,
        bank0=(1,),
        bank1=(55, 56),
    )
    result = route_and_commit_recurrent_v1(queue, _routes(), (False, False, False))
    assert result.consumed_recurrent_axons == (1,)
    assert result.routed_output_axons == ()
    assert result.queue_after_commit.current_bank == 1
    assert result.queue_after_commit.current_events == ()


def test_reset_clears_both_banks_and_restores_bank_zero() -> None:
    reset = reset_recurrent_queue_v1()
    assert reset.current_bank == 0
    assert reset.bank0 == ()
    assert reset.bank1 == ()
    assert reset.current_events == ()


def test_exact_duplicate_route_is_rejected_but_cross_source_same_target_is_legal() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        freeze_spike_routes_v1(
            (
                SpikeRoute(0, 5),
                SpikeRoute(0, 5),
            ),
            neuron_count=2,
        )

    storage = freeze_spike_routes_v1(
        (
            SpikeRoute(0, 5),
            SpikeRoute(1, 5),
        ),
        neuron_count=2,
    )
    assert storage.target_axons == (5, 5)


def test_route_source_target_and_count_capacity_are_validated() -> None:
    with pytest.raises(ValueError, match="source"):
        freeze_spike_routes_v1((SpikeRoute(2, 0),), neuron_count=2)
    with pytest.raises(ValueError, match="target axon"):
        freeze_spike_routes_v1((SpikeRoute(0, 1024),), neuron_count=1)

    tiny = FpgaCoreCapacity(
        max_neurons=4,
        max_axons=8,
        max_synapses=8,
        max_weight_formats=4,
        max_routes=2,
        max_external_events_per_tick=4,
        max_recurrent_events_per_tick=4,
    )
    with pytest.raises(ValueError, match="route count"):
        freeze_spike_routes_v1(
            (SpikeRoute(0, 0), SpikeRoute(1, 1), SpikeRoute(2, 2)),
            neuron_count=3,
            capacity=tiny,
        )


def test_spike_vector_shape_and_types_are_strict() -> None:
    routes = _routes()
    with pytest.raises(ValueError, match="length"):
        route_and_commit_recurrent_v1(
            DoubleBufferedRecurrentQueue.empty(), routes, (True, False)
        )
    with pytest.raises(TypeError, match="bools"):
        route_and_commit_recurrent_v1(
            DoubleBufferedRecurrentQueue.empty(), routes, (True, 1, False)
        )


def test_queue_rejects_invalid_bank_events_and_selector() -> None:
    with pytest.raises(ValueError, match="current_bank"):
        DoubleBufferedRecurrentQueue(current_bank=2)
    with pytest.raises(ValueError, match="physical capacity"):
        DoubleBufferedRecurrentQueue(bank0=(1024,))
    with pytest.raises(TypeError, match="ints"):
        DoubleBufferedRecurrentQueue(bank1=(True,))


def test_next_queue_capacity_overflow_is_detected_during_routing() -> None:
    tiny = FpgaCoreCapacity(
        max_neurons=4,
        max_axons=8,
        max_synapses=8,
        max_weight_formats=4,
        max_routes=4,
        max_external_events_per_tick=4,
        max_recurrent_events_per_tick=2,
    )
    routes = freeze_spike_routes_v1(
        (SpikeRoute(0, 1), SpikeRoute(0, 2), SpikeRoute(1, 3)),
        neuron_count=2,
        capacity=tiny,
    )
    with pytest.raises(OverflowError, match="next recurrent queue"):
        route_and_commit_recurrent_v1(
            DoubleBufferedRecurrentQueue.empty(),
            routes,
            (True, True),
            capacity=tiny,
        )
