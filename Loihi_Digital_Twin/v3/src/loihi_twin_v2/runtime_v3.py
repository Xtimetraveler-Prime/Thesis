"""Executable FPGA-v3 P03.1 autonomous-runtime contract.

This is a control-plane contract model, not the production Cortex-A53 runtime.
It freezes legal phase transitions and board-local ownership invariants before
the standalone PS implementation is written.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, IntEnum


class RuntimeState(str, Enum):
    RESET = "reset"
    LOAD_DEPLOYMENT = "load_deployment"
    INITIALIZE_BACKING = "initialize_backing"
    INITIALIZE_RESIDENT_SET = "initialize_resident_set"
    LOAD_INPUT = "load_input"
    TIMESTEP_BEGIN = "timestep_begin"
    SELECT_LOGICAL_CORE = "select_logical_core"
    ENSURE_RESIDENT = "ensure_resident"
    SAVE_VICTIM = "save_victim"
    LOAD_REQUESTED = "load_requested"
    DISPATCH_CORE = "dispatch_core"
    DRAIN_AND_ROUTE_PACKETS = "drain_and_route_packets"
    MARK_LOGICAL_CORE_COMPLETE = "mark_logical_core_complete"
    BARRIER_CHECK = "barrier_check"
    SWAP_EVENT_BANKS = "swap_event_banks"
    ADVANCE_TIMESTEP = "advance_timestep"
    FINALIZE = "finalize"
    WRITE_RESULT = "write_result"
    DONE = "done"
    ERROR = "error"


class RuntimeFault(IntEnum):
    NONE = 0
    INVALID_RUN_CONFIG = 1
    DEPLOYMENT_INVALID = 2
    BACKING_ABI = 3
    BACKING_RANGE = 4
    CACHE_OWNERSHIP = 5
    PAGE_ERROR = 6
    DISPATCH_ERROR = 7
    PACKET_FORMAT = 8
    EVENT_OVERFLOW = 9
    RESOURCE_OVERFLOW = 10
    BARRIER_INCOMPLETE = 11
    CONTROL_PROTOCOL = 12
    TIMEOUT = 13


class RuntimeContractError(RuntimeError):
    """Raised when an action violates the P03.1 fail-closed contract."""


@dataclass(slots=True)
class RuntimeCounters:
    initial_page_ins: int = 0
    page_ins: int = 0
    page_outs: int = 0
    logical_dispatches: int = 0
    routed_packets: int = 0
    barriers: int = 0
    timesteps_completed: int = 0


@dataclass(slots=True)
class AutonomousRuntimeContract:
    logical_core_ids: tuple[int, ...]
    total_timesteps: int
    state: RuntimeState = RuntimeState.RESET
    current_timestep: int = 0
    current_event_bank: int = 0
    selected_core: int | None = None
    selected_slot: int | None = None
    completed_cores: set[int] = field(default_factory=set)
    pending_packets: int = 0
    first_fault: RuntimeFault = RuntimeFault.NONE
    fault_state: RuntimeState | None = None
    external_control_locked: bool = False
    control_timer_active: bool = False
    inference_timer_active: bool = False
    result_committed: bool = False
    counters: RuntimeCounters = field(default_factory=RuntimeCounters)

    def __post_init__(self) -> None:
        if not self.logical_core_ids:
            raise ValueError("logical_core_ids must not be empty")
        if len(set(self.logical_core_ids)) != len(self.logical_core_ids):
            raise ValueError("logical_core_ids must be unique")
        if any(core < 0 or core >= 128 for core in self.logical_core_ids):
            raise ValueError("logical_core_ids must be in [0, 127]")
        if self.total_timesteps <= 0:
            raise ValueError("total_timesteps must be positive")

    @property
    def barrier_ready(self) -> bool:
        return (
            self.completed_cores == set(self.logical_core_ids)
            and self.pending_packets == 0
        )

    @property
    def external_pc_may_drive_algorithmic_control(self) -> bool:
        return not self.external_control_locked

    def _fail(self, code: RuntimeFault, message: str) -> None:
        if self.first_fault == RuntimeFault.NONE:
            self.first_fault = code
            self.fault_state = self.state
        self.state = RuntimeState.ERROR
        self.control_timer_active = False
        self.inference_timer_active = False
        raise RuntimeContractError(message)

    def _require_state(self, *allowed: RuntimeState) -> None:
        if self.state not in allowed:
            names = ", ".join(state.value for state in allowed)
            self._fail(
                RuntimeFault.CONTROL_PROTOCOL,
                f"state {self.state.value} does not permit operation; expected {names}",
            )

    def reset(self) -> None:
        self.state = RuntimeState.RESET
        self.current_timestep = 0
        self.current_event_bank = 0
        self.selected_core = None
        self.selected_slot = None
        self.completed_cores.clear()
        self.pending_packets = 0
        self.first_fault = RuntimeFault.NONE
        self.fault_state = None
        self.external_control_locked = False
        self.control_timer_active = False
        self.inference_timer_active = False
        self.result_committed = False
        self.counters = RuntimeCounters()

    def begin_run(self) -> None:
        self._require_state(RuntimeState.RESET)
        self.external_control_locked = True
        self.control_timer_active = True
        self.state = RuntimeState.LOAD_DEPLOYMENT

    def deployment_loaded(self) -> None:
        self._require_state(RuntimeState.LOAD_DEPLOYMENT)
        self.state = RuntimeState.INITIALIZE_BACKING

    def backing_initialized(self) -> None:
        self._require_state(RuntimeState.INITIALIZE_BACKING)
        self.state = RuntimeState.INITIALIZE_RESIDENT_SET

    def residents_initialized(self, *, initial_page_ins: int = 0) -> None:
        self._require_state(RuntimeState.INITIALIZE_RESIDENT_SET)
        if initial_page_ins < 0:
            self._fail(
                RuntimeFault.CONTROL_PROTOCOL,
                "initial_page_ins must be non-negative",
            )
        self.counters.initial_page_ins += initial_page_ins
        self.inference_timer_active = True
        self.state = RuntimeState.LOAD_INPUT

    def input_loaded(self) -> None:
        self._require_state(RuntimeState.LOAD_INPUT)
        self.state = RuntimeState.TIMESTEP_BEGIN

    def begin_timestep(self) -> None:
        self._require_state(RuntimeState.TIMESTEP_BEGIN)
        self.completed_cores.clear()
        self.pending_packets = 0
        self.selected_core = None
        self.selected_slot = None
        self.state = RuntimeState.SELECT_LOGICAL_CORE

    def select_core(self, logical_core_id: int) -> None:
        self._require_state(RuntimeState.SELECT_LOGICAL_CORE)
        if logical_core_id not in self.logical_core_ids:
            self._fail(
                RuntimeFault.INVALID_RUN_CONFIG,
                "selected logical core is not configured",
            )
        if logical_core_id in self.completed_cores:
            self._fail(
                RuntimeFault.CONTROL_PROTOCOL,
                "logical core already completed this timestep",
            )
        self.selected_core = logical_core_id
        self.selected_slot = None
        self.state = RuntimeState.ENSURE_RESIDENT

    def resident_hit(self, resident_slot: int) -> None:
        self._require_state(RuntimeState.ENSURE_RESIDENT)
        if not 0 <= resident_slot < 3:
            self._fail(
                RuntimeFault.INVALID_RUN_CONFIG,
                "resident slot must be in [0, 2]",
            )
        self.selected_slot = resident_slot
        self.state = RuntimeState.DISPATCH_CORE

    def resident_miss(self, resident_slot: int, *, victim_dirty: bool) -> None:
        self._require_state(RuntimeState.ENSURE_RESIDENT)
        if not 0 <= resident_slot < 3:
            self._fail(
                RuntimeFault.INVALID_RUN_CONFIG,
                "resident slot must be in [0, 2]",
            )
        self.selected_slot = resident_slot
        self.state = (
            RuntimeState.SAVE_VICTIM
            if victim_dirty
            else RuntimeState.LOAD_REQUESTED
        )

    def victim_saved(self) -> None:
        self._require_state(RuntimeState.SAVE_VICTIM)
        self.counters.page_outs += 1
        self.state = RuntimeState.LOAD_REQUESTED

    def requested_loaded(self) -> None:
        self._require_state(RuntimeState.LOAD_REQUESTED)
        self.counters.page_ins += 1
        self.state = RuntimeState.DISPATCH_CORE

    def dispatch_done(self, *, packet_count: int) -> None:
        self._require_state(RuntimeState.DISPATCH_CORE)
        if packet_count < 0 or packet_count > 4096:
            self._fail(
                RuntimeFault.EVENT_OVERFLOW,
                "packet_count must be in [0, 4096]",
            )
        self.pending_packets = packet_count
        self.counters.logical_dispatches += 1
        self.state = RuntimeState.DRAIN_AND_ROUTE_PACKETS

    def route_packets(self, count: int = 1) -> None:
        self._require_state(RuntimeState.DRAIN_AND_ROUTE_PACKETS)
        if count < 0 or count > self.pending_packets:
            self._fail(
                RuntimeFault.PACKET_FORMAT,
                "cannot route more packets than remain pending",
            )
        self.pending_packets -= count
        self.counters.routed_packets += count

    def packets_drained(self) -> None:
        self._require_state(RuntimeState.DRAIN_AND_ROUTE_PACKETS)
        if self.pending_packets != 0:
            self._fail(
                RuntimeFault.BARRIER_INCOMPLETE,
                "packet traffic remains pending",
            )
        self.state = RuntimeState.MARK_LOGICAL_CORE_COMPLETE

    def mark_core_complete(self) -> None:
        self._require_state(RuntimeState.MARK_LOGICAL_CORE_COMPLETE)
        if self.selected_core is None:
            self._fail(
                RuntimeFault.CONTROL_PROTOCOL,
                "no logical core is selected",
            )
        self.completed_cores.add(self.selected_core)
        self.selected_core = None
        self.selected_slot = None
        self.state = (
            RuntimeState.BARRIER_CHECK
            if self.completed_cores == set(self.logical_core_ids)
            else RuntimeState.SELECT_LOGICAL_CORE
        )

    def complete_barrier(self) -> None:
        if self.state != RuntimeState.BARRIER_CHECK or not self.barrier_ready:
            self._fail(
                RuntimeFault.BARRIER_INCOMPLETE,
                "global barrier requires every logical core complete and no pending packets",
            )
        self.counters.barriers += 1
        self.state = RuntimeState.SWAP_EVENT_BANKS

    def swap_event_banks(self) -> None:
        self._require_state(RuntimeState.SWAP_EVENT_BANKS)
        self.current_event_bank = 1 - self.current_event_bank
        self.state = RuntimeState.ADVANCE_TIMESTEP

    def advance_timestep(self) -> None:
        self._require_state(RuntimeState.ADVANCE_TIMESTEP)
        self.counters.timesteps_completed += 1
        self.current_timestep += 1
        self.state = (
            RuntimeState.FINALIZE
            if self.counters.timesteps_completed >= self.total_timesteps
            else RuntimeState.TIMESTEP_BEGIN
        )

    def finalize(self) -> None:
        self._require_state(RuntimeState.FINALIZE)
        self.state = RuntimeState.WRITE_RESULT

    def write_result(self) -> None:
        self._require_state(RuntimeState.WRITE_RESULT)
        self.result_committed = True
        self.inference_timer_active = False
        self.control_timer_active = False
        self.state = RuntimeState.DONE

    def inject_fault(
        self,
        code: RuntimeFault,
        message: str = "runtime fault",
    ) -> None:
        if code == RuntimeFault.NONE:
            raise ValueError("fault code must not be NONE")
        if self.state == RuntimeState.ERROR:
            return
        self._fail(code, message)
