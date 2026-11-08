"""Deterministic, FAKE transport for M05.10 controller testing, NOT FPGA RTL.

ScriptedTransport exercises the *same nonblocking adapter API* that a future
AXI-Lite/DMA backend must implement. It has finite input/output FIFO capacity
and can model terminal status before all output is drained, incomplete traces,
late errors, stalled inputs, missing completion, and a quiescence barrier.

This is an intentionally scripted test double, NOT a neural calculation,
DMA emulation of bus timings, RTL simulation or performance estimate.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from .m05_execution_controller import (
    ExecutionTransport, InputPort, RunPlan,
)
from .m05_trace_commit import RollingTraceRow


@dataclass(frozen=True)
class ScriptedRun:
    rows: tuple[RollingTraceRow, ...]
    status: int = 0
    output_stride: int = 1
    receive_stride: int = 3
    input_capacity: int = 1
    quiescent_delay: int = 0
    completion_before_output_drained: bool = True
    never_complete: bool = False

    def __post_init__(self) -> None:
        if type(self.rows) is not tuple:
            raise ValueError("fake RTL rows must be a tuple")
        if self.status not in range(7) or type(self.status) is not int:
            raise ValueError("script status must be 0..6")
        for name in ("output_stride", "receive_stride", "input_capacity"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")
        if type(self.quiescent_delay) is not int or self.quiescent_delay < 0:
            raise ValueError("quiescent_delay must be nonnegative")


class ScriptedTransport(ExecutionTransport):
    """A deterministic fake; no FPGA clocks and no actual AXI signals."""

    def __init__(self, scripts: tuple[ScriptedRun, ...]):
        self.scripts = deque(scripts)
        self.active: ScriptedRun | None = None
        self.run_plan: RunPlan | None = None
        self.queues: dict[InputPort, deque[object]] = {
            "neurons": deque(), "synapses": deque(),
            "external_events": deque()
        }
        self.sink: deque[RollingTraceRow] = deque()
        self.counters = {"neurons": 0, "synapses": 0, "external_events": 0}
        self.clock = 0
        self.generated = 0
        self.begin_calls = 0
        self.recovery_calls = 0
        self.input_stalls = 0
        self.output_stalls = 0
        self.quiescent_checks = 0
        self.completion_observed_with_queued_rows = 0

    def begin(self, plan: RunPlan) -> None:
        if self.active is not None:
            raise RuntimeError("fake transport still has active transaction")
        if not self.scripts:
            raise RuntimeError("fake transport has no scripted next response")
        self.active = self.scripts.popleft()
        self.run_plan = plan
        self.clock = 0
        self.generated = 0
        self.begin_calls += 1
        self.counters = {"neurons": 0, "synapses": 0, "external_events": 0}

    def try_send(self, port: InputPort, payload: object) -> bool:
        if self.active is None:
            raise RuntimeError("no fake transaction")
        q = self.queues[port]
        if len(q) >= self.active.input_capacity:
            self.input_stalls += 1
            return False
        q.append(payload)
        return True

    def try_receive(self) -> RollingTraceRow | None:
        if self.active is None:
            raise RuntimeError("no fake transaction")
        if self.sink and self.clock % self.active.receive_stride == 0:
            return self.sink.popleft()
        return None

    def _all_ingress_retired(self) -> bool:
        if self.run_plan is None:
            return False
        return (
            self.counters["neurons"] == len(self.run_plan.neurons)
            and self.counters["synapses"] == len(self.run_plan.synapses)
            and self.counters["external_events"] == len(
                self.run_plan.external_events)
            and not any(self.queues[p] for p in self.queues)
        )

    def _generated_done(self) -> bool:
        return (self.active is not None
                and self._all_ingress_retired()
                and self.generated == len(self.active.rows))

    def poll_completion(self) -> int | None:
        if self.active is None:
            raise RuntimeError("no fake transaction")
        if self.active.never_complete or not self._generated_done():
            return None
        if self.active.completion_before_output_drained or not self.sink:
            if self.sink:
                self.completion_observed_with_queued_rows += 1
            return self.active.status
        return None

    def is_quiescent(self) -> bool:
        self.quiescent_checks += 1
        if self.active is None:
            return False
        ready = (self._generated_done() and not self.sink
                 and self.clock >= self.active.quiescent_delay)
        if ready:
            self.active = None
            self.run_plan = None
        return ready

    def advance(self) -> None:
        if self.active is None:
            raise RuntimeError("no fake transaction")
        self.clock += 1
        # Consume one queued ingress transfer per port per service iteration.
        for port, q in self.queues.items():
            if q:
                q.popleft()
                self.counters[port] += 1
        if self._all_ingress_retired() and self.generated < len(self.active.rows):
            if self.clock % self.active.output_stride == 0:
                if len(self.sink) < 1:
                    self.sink.append(self.active.rows[self.generated])
                    self.generated += 1
                else:
                    self.output_stalls += 1

    def reset_and_verify_idle(self) -> None:
        # Fake synchronous reset, not a claim about physical PL reset/flush.
        self.recovery_calls += 1
        self.active = None
        self.run_plan = None
        self.sink.clear()
        for q in self.queues.values():
            q.clear()
        self.generated = 0
        self.counters = {"neurons": 0, "synapses": 0, "external_events": 0}
