from __future__ import annotations

import pytest

from loihi_twin_v2.runtime_v3 import (
    AutonomousRuntimeContract,
    RuntimeContractError,
    RuntimeFault,
    RuntimeState,
)


def _boot(model: AutonomousRuntimeContract) -> None:
    model.begin_run()
    assert not model.external_pc_may_drive_algorithmic_control
    model.deployment_loaded()
    model.backing_initialized()
    model.residents_initialized(initial_page_ins=3)
    assert model.control_timer_active
    assert model.inference_timer_active
    model.input_loaded()


def _service_core(
    model: AutonomousRuntimeContract,
    core: int,
    *,
    slot: int,
    packets: int,
    miss: bool = False,
    dirty_victim: bool = False,
) -> None:
    model.select_core(core)
    if miss:
        model.resident_miss(slot, victim_dirty=dirty_victim)
        if dirty_victim:
            model.victim_saved()
        model.requested_loaded()
    else:
        model.resident_hit(slot)
    model.dispatch_done(packet_count=packets)
    if packets:
        model.route_packets(packets)
    model.packets_drained()
    model.mark_core_complete()


def test_p03_1_happy_path_preserves_barrier_and_event_bank_order():
    model = AutonomousRuntimeContract((0, 1), total_timesteps=2)
    _boot(model)

    model.begin_timestep()
    _service_core(model, 0, slot=0, packets=1)
    _service_core(model, 1, slot=1, packets=0)
    assert model.state is RuntimeState.BARRIER_CHECK
    assert model.current_event_bank == 0
    model.complete_barrier()
    model.swap_event_banks()
    assert model.current_event_bank == 1
    model.advance_timestep()

    model.begin_timestep()
    _service_core(
        model,
        0,
        slot=2,
        packets=0,
        miss=True,
        dirty_victim=True,
    )
    _service_core(model, 1, slot=1, packets=1)
    model.complete_barrier()
    model.swap_event_banks()
    assert model.current_event_bank == 0
    model.advance_timestep()

    assert model.state is RuntimeState.FINALIZE
    model.finalize()
    model.write_result()

    assert model.state is RuntimeState.DONE
    assert model.result_committed
    assert not model.control_timer_active
    assert not model.inference_timer_active
    assert model.counters.initial_page_ins == 3
    assert model.counters.page_ins == 1
    assert model.counters.page_outs == 1
    assert model.counters.logical_dispatches == 4
    assert model.counters.routed_packets == 2
    assert model.counters.barriers == 2
    assert model.counters.timesteps_completed == 2


def test_p03_1_barrier_fails_closed_while_work_is_incomplete():
    model = AutonomousRuntimeContract((0, 1), total_timesteps=1)
    _boot(model)
    model.begin_timestep()
    _service_core(model, 0, slot=0, packets=0)

    with pytest.raises(RuntimeContractError):
        model.complete_barrier()

    assert model.state is RuntimeState.ERROR
    assert model.first_fault is RuntimeFault.BARRIER_INCOMPLETE
    assert not model.control_timer_active
    assert not model.inference_timer_active


def test_p03_1_packet_drain_is_required_before_core_completion():
    model = AutonomousRuntimeContract((0,), total_timesteps=1)
    _boot(model)
    model.begin_timestep()
    model.select_core(0)
    model.resident_hit(0)
    model.dispatch_done(packet_count=2)
    model.route_packets(1)

    with pytest.raises(RuntimeContractError):
        model.packets_drained()

    assert model.first_fault is RuntimeFault.BARRIER_INCOMPLETE
    assert model.state is RuntimeState.ERROR


def test_p03_1_page_miss_orders_dirty_save_before_load():
    model = AutonomousRuntimeContract((0,), total_timesteps=1)
    _boot(model)
    model.begin_timestep()
    model.select_core(0)
    model.resident_miss(2, victim_dirty=True)

    assert model.state is RuntimeState.SAVE_VICTIM
    model.victim_saved()
    assert model.state is RuntimeState.LOAD_REQUESTED
    model.requested_loaded()
    assert model.state is RuntimeState.DISPATCH_CORE
    assert model.counters.page_outs == 1
    assert model.counters.page_ins == 1


def test_p03_1_event_bank_can_flip_only_after_complete_barrier():
    model = AutonomousRuntimeContract((0,), total_timesteps=1)
    _boot(model)
    model.begin_timestep()

    with pytest.raises(RuntimeContractError):
        model.swap_event_banks()

    assert model.state is RuntimeState.ERROR
    assert model.first_fault is RuntimeFault.CONTROL_PROTOCOL
    assert model.current_event_bank == 0


def test_p03_1_first_fault_is_sticky_until_reset():
    model = AutonomousRuntimeContract((0,), total_timesteps=1)
    _boot(model)

    with pytest.raises(RuntimeContractError):
        model.inject_fault(RuntimeFault.PAGE_ERROR, "page failed")

    model.inject_fault(RuntimeFault.DISPATCH_ERROR, "later fault")
    assert model.first_fault is RuntimeFault.PAGE_ERROR
    assert model.state is RuntimeState.ERROR

    model.reset()
    assert model.first_fault is RuntimeFault.NONE
    assert model.state is RuntimeState.RESET
    assert model.external_pc_may_drive_algorithmic_control


def test_p03_1_rejects_duplicate_or_out_of_range_core_ids():
    with pytest.raises(ValueError):
        AutonomousRuntimeContract((0, 0), total_timesteps=1)
    with pytest.raises(ValueError):
        AutonomousRuntimeContract((128,), total_timesteps=1)
