"""M05.10 — transport-independent PS/PL execution-controller *model*.

No physical device is accessed by this module. An eventual hardware adapter
must implement the nonblocking ExecutionTransport contract with real AXI-Lite
registers, DMA/AXI-stream FIFOs, terminal status and reset/quiescence fences.

Correctness principles:
  * configure and ap_start ONCE per run, not per neuron/tick;
  * service all three input streams, concurrently drain output and observe
    completion on EACH service iteration (never wait for ap_done to drain);
  * output rows are provisional until status 0, full exact frame and a
    transport-certified quiescent boundary;
  * any fault, timeout, nonzero status, malformed row or I/O exception marks
    the controller FAULTED; no reuse until explicit verified recovery;
  * service steps are NOT FPGA clock cycles, DMA latency, or throughput.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Protocol, Literal

from .m05_trace_commit import (
    RollingTraceCommitGate, RollingTraceRow, TraceRunResult,
)

InputPort = Literal["neurons", "synapses", "external_events"]
MAX_U32 = (1 << 32) - 1


def _integer(value: object, lo: int, hi: int, field: str) -> None:
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"{field} outside [{lo},{hi}] or not an integer")


@dataclass(frozen=True)
class NeuronConfig:
    initial_voltage: int
    bias: int
    threshold: int
    reset_voltage: int

    def __post_init__(self) -> None:
        _integer(self.initial_voltage, -32768, 32767, "initial_voltage")
        _integer(self.bias, -32768, 32767, "bias")
        _integer(self.threshold, 1, 32767, "threshold")
        _integer(self.reset_voltage, -32768, 32767, "reset_voltage")
        if self.reset_voltage >= self.threshold:
            raise ValueError("reset_voltage must be below threshold")


@dataclass(frozen=True)
class SynapseConfig:
    pre: int
    post: int
    weight: int
    delay: int

    def __post_init__(self) -> None:
        _integer(self.pre, 0, 1023, "synapse.pre")
        _integer(self.post, 0, 1023, "synapse.post")
        _integer(self.weight, -32768, 32767, "synapse.weight")
        _integer(self.delay, 1, 8, "synapse.delay")


@dataclass(frozen=True)
class ExternalEvent:
    tick: int
    neuron_id: int
    current: int

    def __post_init__(self) -> None:
        _integer(self.tick, 0, 63, "external.tick")
        _integer(self.neuron_id, 0, 1023, "external.neuron_id")
        _integer(self.current, -32768, 32767, "external.current")


@dataclass(frozen=True)
class RunPlan:
    neurons: tuple[NeuronConfig, ...]
    synapses: tuple[SynapseConfig, ...]
    external_events: tuple[ExternalEvent, ...]
    ticks: int
    decay_num: int = 1
    decay_den: int = 1

    def __post_init__(self) -> None:
        if any(type(x) is not tuple for x in (
            self.neurons, self.synapses, self.external_events
        )):
            raise ValueError("network packets must be immutable tuples")
        n = len(self.neurons)
        _integer(n, 1, 1024, "neuron_count")
        _integer(len(self.synapses), 0, 4096, "synapse_count")
        _integer(self.ticks, 1, 64, "ticks")
        _integer(self.decay_den, 1, MAX_U32, "decay_den")
        _integer(self.decay_num, 0, self.decay_den, "decay_num")
        _integer(len(self.external_events), 0, self.ticks * 4096, "external_count")
        if not all(type(v) is NeuronConfig for v in self.neurons):
            raise ValueError("invalid neuron packet type")
        if not all(type(v) is SynapseConfig for v in self.synapses):
            raise ValueError("invalid synapse packet type")
        if not all(type(v) is ExternalEvent for v in self.external_events):
            raise ValueError("invalid external event packet type")
        if any(s.pre >= n or s.post >= n for s in self.synapses):
            raise ValueError("synapse endpoint outside admitted network")
        last_tick = -1
        per_tick = 0
        for e in self.external_events:
            if e.neuron_id >= n or e.tick >= self.ticks:
                raise ValueError("external event outside admitted run")
            if e.tick < last_tick:
                raise ValueError("external input must be sorted by tick")
            if e.tick != last_tick:
                last_tick, per_tick = e.tick, 0
            per_tick += 1
            if per_tick > 4096:
                raise ValueError("external input exceeds 4096 deliveries/tick")


class ExecutionTransport(Protocol):
    """Nonblocking adapter boundary; future DMA implementation NOT supplied.

    begin(): program exact generated AXI-Lite config and launch once. The
      adapter must not treat begin as permission to retry a failed launch.
    try_send(): accept exactly one immutable packet on one named ingress
      channel only when READY/space is available. False means *no transfer*.
    try_receive(): return one completely transferred AXIS trace row or None.
      Must never return a row twice.
    poll_completion(): return None until ap_done AND AXI-Lite final status
      has been reliably read; a terminal int (including error) after that.
      The status is consumed/latched once per run, not read-to-clear twice.
    is_quiescent(): after a successful completion, certifies all ingress
      packets are retired and no output remains buffered/in flight. It MUST
      be a real transport/hardware fence, not merely a FIFO empty snapshot.
    advance(): progress one nonblocking service opportunity. In a real PS
      adapter this might service DMA completions/interrupts and yield; it is
      NOT required to mean one FPGA fabric clock.
    reset_and_verify_idle(): explicit full PS/PL stream isolation/recovery.
      MUST only return after old input/output queues and HLS control state
      are known clean. No implementation is provided here.
    """

    def begin(self, plan: RunPlan) -> None: ...
    def try_send(self, port: InputPort, payload: object) -> bool: ...
    def try_receive(self) -> RollingTraceRow | None: ...
    def poll_completion(self) -> int | None: ...
    def is_quiescent(self) -> bool: ...
    def advance(self) -> None: ...
    def reset_and_verify_idle(self) -> None: ...


class ControllerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAULTED = "faulted"


@dataclass(frozen=True)
class ExecutionReport:
    result: TraceRunResult
    service_steps: int
    sent_neurons: int
    sent_synapses: int
    sent_external: int
    observed_status: int | None
    needs_recovery: bool


class ExecutionController:
    """One outstanding run; fail-closed synchronous cooperative service loop.

    Execution is synchronous, but feeding/draining/completion checks are
    interleaved in every iteration. It requires a *nonblocking* transport.
    An adapter blocking on individual DMA reads or writes violates this API.
    """

    def __init__(self, transport: ExecutionTransport):
        self.transport = transport
        self.state = ControllerState.IDLE

    def recover(self) -> None:
        """Explicit recovery/flush fence. Never assume hardware reset worked."""
        if self.state is ControllerState.RUNNING:
            raise RuntimeError("cannot recover during active execution")
        if self.state is not ControllerState.FAULTED:
            raise RuntimeError("recovery requires a prior fault")
        try:
            self.transport.reset_and_verify_idle()
        except Exception:
            self.state = ControllerState.FAULTED
            raise
        self.state = ControllerState.IDLE

    def execute(
        self, plan: RunPlan, *, max_service_steps: int = 100000,
        wall_timeout_s: float = 30.0
    ) -> ExecutionReport:
        if self.state is not ControllerState.IDLE:
            raise RuntimeError("execution controller not idle; recovery required")
        if type(plan) is not RunPlan:
            raise TypeError("expected validated RunPlan")
        _integer(max_service_steps, 1, 10_000_000, "max_service_steps")
        if type(wall_timeout_s) not in (int, float) or not 0 < wall_timeout_s <= 3600:
            raise ValueError("wall_timeout_s must be positive and at most 3600")
        gate = RollingTraceCommitGate(len(plan.neurons), plan.ticks)
        packets = (
            plan.neurons, plan.synapses, plan.external_events
        )
        names: tuple[InputPort, ...] = (
            "neurons", "synapses", "external_events"
        )
        sent = [0, 0, 0]
        status: int | None = None
        self.state = ControllerState.RUNNING
        steps = 0
        deadline = time.monotonic() + wall_timeout_s

        def outcome(result: TraceRunResult) -> ExecutionReport:
            if result.accepted:
                self.state = ControllerState.IDLE
            else:
                # Never reuse this PS/PL stream context until an explicitly
                # verified transport reset/flush. In particular, a nonzero
                # status can leave prefetched ingress and provisional output.
                self.state = ControllerState.FAULTED
            return ExecutionReport(
                result, steps, sent[0], sent[1], sent[2], status,
                self.state is ControllerState.FAULTED
            )

        try:
            self.transport.begin(plan)  # exactly once
            for steps in range(1, max_service_steps + 1):
                if time.monotonic() >= deadline:
                    return outcome(gate.abort("wall-clock execution timeout"))
                # Keep the three ingress streams moving while draining output.
                # Completion may arrive *before* all its output is drained.
                if status is None:
                    for i, name in enumerate(names):
                        if sent[i] < len(packets[i]) and self.transport.try_send(
                            name, packets[i][sent[i]]
                        ):
                            sent[i] += 1
                row = self.transport.try_receive()
                if row is not None:
                    gate.offer_row(row)  # poison-but-keep-draining on bad shape
                fresh_status = self.transport.poll_completion()
                if fresh_status is not None:
                    if type(fresh_status) is not int or not 0 <= fresh_status <= 6:
                        return outcome(gate.abort(
                            "transport completion status invalid/unknown"
                        ))
                    if status is not None and fresh_status != status:
                        return outcome(gate.abort(
                            "inconsistent completion status across polls"
                        ))
                    status = fresh_status
                    if status != 0:
                        return outcome(gate.complete(status))
                if status == 0:
                    if (all(sent[i] == len(packets[i]) for i in range(3))
                            and gate.received_count == gate.expected_rows
                            and self.transport.is_quiescent()):
                        return outcome(gate.complete(0))
                self.transport.advance()
            return outcome(gate.abort("service-step budget exhausted"))
        except Exception as exc:
            # Never publish partial rows if a backend/DMA/AXI-Lite call raises,
            # even if earlier output passed CRC/numeric checks.
            return outcome(gate.abort(
                f"transport exception: {type(exc).__name__}: {exc}"
            ))
