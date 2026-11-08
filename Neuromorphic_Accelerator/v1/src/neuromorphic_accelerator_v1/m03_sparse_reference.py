"""M03 exact-idle-elision *software* evaluator for accepted M02 LIF revision 1.

Lemma: with threshold > 0 (validated by M02), previous voltage == 0,
bias == 0 and summed input == 0, the neuron's new voltage remains 0
and cannot spike. Such a neuron may be omitted from a timestep state
evaluation without changing the functional result. Every nonzero-voltage
neuron, biased neuron, or event recipient MUST still be evaluated.

This is proof-scoped to M02 rev1, not a general YANA-style lazy-leak
implementation, nor actual hardware event queue throughput/DDR timing.
Full voltage snapshots below are for verification and their costs are
not included in the accounting model.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from .m02_types import InputCurrent, Network, ReferenceTrace, validate


@dataclass(frozen=True)
class SparseResult:
    trace: ReferenceTrace
    evaluated_ids_by_tick: tuple[tuple[int, ...], ...]
    destinations_by_tick: tuple[tuple[int, ...], ...]
    fired_ids_by_tick: tuple[tuple[int, ...], ...]
    traversed_synapses_by_tick: tuple[int, ...]
    fanout_per_firing_by_tick: tuple[tuple[tuple[int, int], ...], ...]
    deliveries_by_tick: tuple[int, ...]
    pending_future_deliveries_by_tick: tuple[int, ...]
    peak_pending_deliveries: int

    @property
    def evaluation_count(self) -> int:
        return sum(map(len, self.evaluated_ids_by_tick))


def evaluate_exact_sparse(
    network: Network, inputs: Iterable[InputCurrent], *, ticks: int
) -> SparseResult:
    """Evaluates strictly necessary LIF states, with full-trace exact output."""
    events = validate(network, inputs, ticks)
    n = len(network.neurons)
    net_outgoing: list[list[tuple[int, int, int]]] = [[] for _ in range(n)]
    for syn in network.synapses:
        net_outgoing[syn.pre].append((syn.post, syn.weight, syn.delay))

    scheduled: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for inp in events:
        scheduled[inp.tick].append((inp.neuron, inp.current))
    values = [cell.initial_v for cell in network.neurons]
    nonzero = {i for i, v in enumerate(values) if v != 0}
    biased = {i for i, cell in enumerate(network.neurons) if cell.bias != 0}
    lo = -(1 << (network.state_bits - 1))
    hi = (1 << (network.state_bits - 1)) - 1

    rows = []
    spikes = []
    eval_rows = []
    target_rows = []
    edge_rows = []
    fanout_rows = []
    delivery_rows = []
    pending_rows = []
    pending_count = sum(len(v) for v in scheduled.values())
    peak_pending = pending_count

    for t in range(ticks):
        incoming = [0] * n
        targets: set[int] = set()
        arrivals = scheduled.pop(t, ())
        pending_count -= len(arrivals)
        delivery_rows.append(len(arrivals))
        for destination, current in arrivals:
            incoming[destination] += current
            # Conservative even if currents sum to zero or weight == 0.
            targets.add(destination)

        evaluated = tuple(sorted(nonzero | biased | targets))
        next_nonzero: set[int] = set()
        fired: list[int] = []
        for neuron_id in evaluated:
            cell = network.neurons[neuron_id]
            prior = values[neuron_id]
            product = prior * network.decay_num
            # Independent arithmetic path: sign/magnitude absolute quotient.
            decay = (abs(product) // network.decay_den) * (
                -1 if product < 0 else 1
            )
            raw = decay + incoming[neuron_id] + cell.bias
            bounded = lo if raw < lo else hi if raw > hi else raw
            if bounded >= cell.threshold:
                fired.append(neuron_id)
                values[neuron_id] = cell.reset_v
            else:
                values[neuron_id] = bounded
            if values[neuron_id] != 0:
                next_nonzero.add(neuron_id)

        # Everything not evaluated had prior voltage, current and bias
        # identically zero; its new state is therefore provably still zero.
        nonzero = next_nonzero
        fired_row = tuple(fired)
        visited = 0
        grouped: list[tuple[int, int]] = []
        for presynaptic in fired_row:
            edges = net_outgoing[presynaptic]
            grouped.append((presynaptic, len(edges)))
            visited += len(edges)
            for destination, weight, delay in edges:
                delivery_tick = t + delay
                if delivery_tick < ticks:
                    scheduled[delivery_tick].append((destination, weight))
                    pending_count += 1

        rows.append(tuple(values))  # verification copy, NOT measured hardware
        spikes.append(fired_row)
        eval_rows.append(evaluated)
        target_rows.append(tuple(sorted(targets)))
        edge_rows.append(visited)
        fanout_rows.append(tuple(grouped))
        if pending_count < 0:
            raise AssertionError("negative scheduled delivery count")
        pending_rows.append(pending_count)
        peak_pending = max(peak_pending, pending_count)

    return SparseResult(
        trace=ReferenceTrace(tuple(rows), tuple(spikes)),
        evaluated_ids_by_tick=tuple(eval_rows),
        destinations_by_tick=tuple(target_rows),
        fired_ids_by_tick=tuple(spikes),
        traversed_synapses_by_tick=tuple(edge_rows),
        fanout_per_firing_by_tick=tuple(fanout_rows),
        deliveries_by_tick=tuple(delivery_rows),
        pending_future_deliveries_by_tick=tuple(pending_rows),
        peak_pending_deliveries=peak_pending,
    )
