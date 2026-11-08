"""M05.2 host-only sparse-tick/event scheduler exercising the actual M05 C++ batch.

This is NOT synthesized event hardware, real FIFO backpressure, AXI/DDR traffic,
physical timing, or measured acceleration. All accepted M02 rev1 semantics
remain unchanged; the explicit M04.5 first-K26 admission envelope applies.
The kernel is called as a separate host subprocess per active tick solely for
correctness; subprocess startup cost is *not* a benchmark of PL service.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import subprocess

from .m02_types import InputCurrent, Network, ReferenceTrace, validate
from .m04_profile import (
    FIRST_STATE_BITS, MAX_ARRIVALS_PER_TICK, MAX_U32, MAX_U64, M04AdmissionError,
)

MAX_RESIDENT_NEURONS = 1024  # first on-chip baseline; no HDL memory implemented


@dataclass(frozen=True)
class M05HostTrace:
    trace: ReferenceTrace
    evaluated_ids_by_tick: tuple[tuple[int, ...], ...]
    deliveries_by_tick: tuple[int, ...]
    kernel_batches: int

    @property
    def evaluated_neuron_steps(self) -> int:
        return sum(len(ids) for ids in self.evaluated_ids_by_tick)


def _evaluate_batch(binary: str, requests: list[tuple[int, ...]]
                    ) -> tuple[tuple[int, int, int, int, int], ...]:
    if not requests:
        return ()
    if len(requests) > MAX_RESIDENT_NEURONS:
        raise M04AdmissionError("M05 kernel request batch exceeds 1024")
    payload = str(len(requests)) + "\n" + "".join(
        " ".join(map(str, request)) + "\n" for request in requests
    )
    completed = subprocess.run(
        [binary], input=payload, text=True, capture_output=True, check=False
    )
    if completed.returncode:
        raise RuntimeError(f"M05 host kernel failed ({completed.returncode}): "
                           f"{completed.stderr.strip()}")
    try:
        rows = [tuple(int(v) for v in line.split())
                for line in completed.stdout.splitlines()]
    except ValueError as exc:
        raise RuntimeError("M05 non-integer kernel response") from exc
    if not rows or rows[0] != (0, len(requests)) or len(rows) != len(requests) + 1:
        raise RuntimeError("M05 response framing/count mismatch")
    reply_rows = rows[1:]
    if any(len(row) != 5 for row in reply_rows):
        raise RuntimeError("M05 response row has wrong width")
    for request, reply in zip(requests, reply_rows):
        if reply[:2] != (request[0], request[2]) or reply[2] != 0 or reply[4] not in (0, 1):
            raise RuntimeError("M05 response ID/tick/status mismatch")
    return tuple(reply_rows)


def replay_exact_sparse_host(
    network: Network,
    external_inputs: Iterable[InputCurrent],
    *,
    ticks: int,
    kernel_binary: str | Path,
    resident_neurons: int = MAX_RESIDENT_NEURONS,
) -> M05HostTrace:
    """Known finite host workload, live synaptic scheduling, full per-tick parity.

    Independent of the M02 evaluator's update/routing implementations: the
    routine does NOT call either M02 evaluator to produce its own results.
    No user-visible partial trace is returned if any tick overflows/fails.
    """
    inputs = validate(network, external_inputs, ticks)
    if type(resident_neurons) is not int or not 1 <= resident_neurons <= MAX_RESIDENT_NEURONS:
        raise M04AdmissionError("resident_neurons must be in [1,1024]")
    if len(network.neurons) > resident_neurons:
        raise M04AdmissionError("logical network exceeds first resident working set")
    if network.state_bits != FIRST_STATE_BITS:
        raise M04AdmissionError("first M05 kernel profile requires W16")
    if network.decay_num > MAX_U32 or network.decay_den > MAX_U32:
        raise M04AdmissionError("decay rational exceeds unsigned 32-bit")
    if ticks - 1 > MAX_U64:
        raise M04AdmissionError("tick metadata exceeds unsigned 64-bit")
    binary = str(kernel_binary)
    if not Path(binary).is_file():
        raise FileNotFoundError("M05 host kernel binary missing")

    outgoing: list[list[tuple[int, int, int]]] = [
        [] for _ in network.neurons
    ]
    for edge in network.synapses:
        outgoing[edge.pre].append((edge.post, edge.weight, edge.delay))

    arrivals: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for event in inputs:
        arrivals[event.tick].append((event.neuron, event.current))
        if len(arrivals[event.tick]) > MAX_ARRIVALS_PER_TICK:
            raise M04AdmissionError("external tick exceeds 4096 deliveries")

    states = [cell.initial_v for cell in network.neurons]
    voltage_rows: list[tuple[int, ...]] = []
    spike_rows: list[tuple[int, ...]] = []
    worklists: list[tuple[int, ...]] = []
    count_rows: list[int] = []
    batches = 0
    for tick in range(ticks):
        incoming = [0] * len(states)
        targets: set[int] = set()
        items = arrivals.pop(tick, [])
        if len(items) > MAX_ARRIVALS_PER_TICK:
            raise M04AdmissionError(f"tick {tick}: too many delivered events")
        for destination, current in items:
            incoming[destination] += current
            targets.add(destination)

        # The only currently accepted exact skip: v==0, bias==0, no delivery.
        eligible = tuple(sorted(targets |
                                {i for i, v in enumerate(states) if v != 0} |
                                {i for i, p in enumerate(network.neurons) if p.bias != 0}))
        requests = [
            (i, len(states), tick, states[i], incoming[i],
             network.neurons[i].bias, network.neurons[i].threshold,
             network.neurons[i].reset_v, network.state_bits,
             network.decay_num, network.decay_den)
            for i in eligible
        ]
        replies = _evaluate_batch(binary, requests)
        if requests:
            batches += 1
        proposed = list(states)
        fired: list[int] = []
        for i, reply in zip(eligible, replies):
            proposed[i] = reply[3]
            if reply[4] == 1:
                fired.append(i)

        # All future synapses are queued after this tick's state evaluations.
        # Validate future delivery capacities before returning any trace.
        for pre in fired:
            for post, weight, delay in outgoing[pre]:
                future = tick + delay
                if future < ticks:
                    arrivals[future].append((post, weight))
                    if len(arrivals[future]) > MAX_ARRIVALS_PER_TICK:
                        raise M04AdmissionError(
                            f"tick {future}: more than 4096 delivered events"
                        )
        states = proposed
        voltage_rows.append(tuple(states))
        spike_rows.append(tuple(fired))
        worklists.append(eligible)
        count_rows.append(len(items))

    return M05HostTrace(
        trace=ReferenceTrace(tuple(voltage_rows), tuple(spike_rows)),
        evaluated_ids_by_tick=tuple(worklists),
        deliveries_by_tick=tuple(count_rows),
        kernel_batches=batches,
    )
