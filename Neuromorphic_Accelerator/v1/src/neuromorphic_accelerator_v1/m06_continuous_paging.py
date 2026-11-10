"""M06 SOURCE-ONLY paged LIF streaming across bounded execution windows.

Unlike m06_paged_replay (one fresh <=64 tick epoch), this model owns the
scheduling state across *successive windows*, preserving recurrent events
across a window boundary and retaining canonical neuron voltages, LRU tags
and (for >=6 byte rows) last-completed-tick metadata. Work is performed
through the same BlockCache interface, never a resident working-voltage
array. Full output trace is only a TEST observer copy and is NOT charged
to the traffic counters.

Accepted M05 per-window envelope is <=64 ticks; this software-only bridge
tests up to 256 total ticks. It is NOT synthesized HLS RTL, NOT an unbounded
continuous FPGA scheduler and NOT an atomic multi-window DDR transaction.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable

from .m02_types import InputCurrent, Network, ReferenceTrace, validate
from .m06_block_residency import BlockCache, ResidencyError
from .m06_paged_replay import (
    MAX_M05_NEURONS, MAX_M05_SYNAPSES, MAX_M05_DELAY,
    MAX_M05_EXTERNAL, MAX_M05_DELIVERIES_PER_TICK,
)

MAX_SOFTWARE_SESSION_TICKS = 256
MAX_WINDOW_TICKS = 64


@dataclass(frozen=True)
class WindowReceipt:
    first_tick: int
    end_tick_exclusive: int
    evaluated: int
    emitted_spikes: int
    individual_deliveries: int
    canonical_flushed: bool
    source_scope: str = "M06_SOURCE_ONLY_NOT_RTL"


class PagedContinuousSession:
    """Exact sparse scheduler over bounded windows and ONE logical epoch.

    The caller is responsible for separate shadow-image transactionality.
    flush() is performed at each successful window boundary on this cache's
    backing image, which is NOT physically atomic on AXI. On any failure,
    the session is sticky failed, the cache is poisoned, and prior output
    should be considered PROVISIONAL until the entire session is finalized.
    """

    def __init__(self, net: Network, events: Iterable[InputCurrent],
                 *, total_ticks: int, cache: BlockCache):
        frozen = validate(net, events, total_ticks)
        if (net.state_bits != 16 or len(net.neurons) > MAX_M05_NEURONS
                or len(net.synapses) > MAX_M05_SYNAPSES
                or len(frozen) > MAX_M05_EXTERNAL
                or any(s.delay > MAX_M05_DELAY for s in net.synapses)
                or total_ticks > MAX_SOFTWARE_SESSION_TICKS):
            raise ValueError("outside bounded M06 continuous source model envelope")
        if any(frozen[j].tick > frozen[j+1].tick for j in range(len(frozen)-1)):
            raise ValueError("external events must be sorted by tick")
        if (cache.geometry.logical_neurons != len(net.neurons) or
                cache.geometry.bytes_per_neuron < 2):
            raise ValueError("cache geometry must hold each admitted neuron")
        if cache.poisoned or cache.counters.accesses or cache.resident_pages:
            raise ValueError("fresh cache required for new logical session")
        first = b"".join(
            n.initial_v.to_bytes(2, "little", signed=True)
            + bytes(cache.geometry.bytes_per_neuron-2) for n in net.neurons)
        if cache.store.snapshot(owner=cache.owner) != first:
            raise ValueError("new session requires validated M02 initial canonical state")

        self.net = net
        self.cache = cache
        self.total_ticks = total_ticks
        self.cursor = 0
        self.status = "IN_PROGRESS"
        self._scheduled: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for e in frozen:
            self._scheduled[e.tick].append((e.neuron, e.current))
        for tick, arrivals in self._scheduled.items():
            if len(arrivals) > MAX_M05_DELIVERIES_PER_TICK:
                raise ValueError(f"initial tick {tick} delivery capacity exceeded")
        self._out: list[list[tuple[int, int, int]]] = [[] for _ in net.neurons]
        for edge in net.synapses:
            self._out[edge.pre].append((edge.post, edge.weight, edge.delay))
        self._active: set[int] = {
            i for i, n in enumerate(net.neurons) if n.initial_v != 0
        }
        self._biased: set[int] = {
            i for i, n in enumerate(net.neurons) if n.bias != 0
        }
        # Observer full trace, not consulted for eligibility/current/voltage.
        self._observer = [n.initial_v for n in net.neurons]
        self._vrows: list[tuple[int, ...]] = []
        self._spikes: list[tuple[int, ...]] = []
        self._evaluated: list[tuple[int, ...]] = []
        self._touched: list[tuple[int, ...]] = []
        self._delivery_counts: list[int] = []
        self._fanout: list[int] = []
        self.receipts: list[WindowReceipt] = []

    @property
    def trace(self) -> ReferenceTrace:
        return ReferenceTrace(tuple(self._vrows), tuple(self._spikes))

    @property
    def evaluated_ids_by_tick(self) -> tuple[tuple[int, ...], ...]:
        return tuple(self._evaluated)

    @property
    def touched_ids_by_tick(self) -> tuple[tuple[int, ...], ...]:
        return tuple(self._touched)

    @property
    def deliveries_by_tick(self) -> tuple[int, ...]:
        return tuple(self._delivery_counts)

    @property
    def fanout_edges_by_tick(self) -> tuple[int, ...]:
        return tuple(self._fanout)

    @property
    def counters(self) -> dict:
        return asdict(self.cache.counters)

    def run_window(self, stop_tick_exclusive: int) -> WindowReceipt:
        if self.status != "IN_PROGRESS":
            raise ResidencyError("cannot run a failed or finalized neural session")
        if (type(stop_tick_exclusive) is not int or
                not self.cursor < stop_tick_exclusive <= self.total_ticks or
                stop_tick_exclusive-self.cursor > MAX_WINDOW_TICKS):
            raise ValueError("window must advance 1..64 ticks without skipping time")
        first = self.cursor
        try:
            for tick in range(first, stop_tick_exclusive):
                deliveries = self._scheduled.pop(tick, ())
                if len(deliveries) > MAX_M05_DELIVERIES_PER_TICK:
                    raise ResidencyError("individual recurrent+external tick cap exceeded")
                sums = defaultdict(int)
                destinations: set[int] = set()
                for dst, weight in deliveries:
                    sums[dst] += weight
                    destinations.add(dst)  # even zero/canceled arrivals wake
                eligible = tuple(sorted(self._active | self._biased | destinations))
                next_active: set[int] = set()
                spikes: list[int] = []
                for neuron in eligible:
                    record = self.cache.read(neuron)
                    prior = int.from_bytes(record[:2], "little", signed=True)
                    if len(record) >= 6:
                        completed = int.from_bytes(record[2:6], "little")
                        if completed > tick:
                            raise ResidencyError("future last-completed tick in paged state")
                    product = prior * self.net.decay_num
                    leaked = (abs(product) // self.net.decay_den) * (
                        -1 if product < 0 else 1)
                    raw = leaked + self.net.neurons[neuron].bias + sums[neuron]
                    state = min(32767, max(-32768, raw))
                    cell = self.net.neurons[neuron]
                    if state >= cell.threshold:
                        spikes.append(neuron)
                        state = cell.reset_v
                    state_bytes = state.to_bytes(2, "little", signed=True)
                    if len(record) >= 6:
                        state_bytes += (tick+1).to_bytes(4, "little") + record[6:]
                    else:
                        state_bytes += record[2:]
                    self.cache.write(neuron, state_bytes)
                    if state != 0:
                        next_active.add(neuron)
                    self._observer[neuron] = state
                self._active = next_active
                fanout = 0
                for pre in spikes:
                    for post, weight, delay in self._out[pre]:
                        fanout += 1
                        future = tick+delay
                        if future < self.total_ticks:
                            self._scheduled[future].append((post, weight))
                            if (len(self._scheduled[future]) >
                                    MAX_M05_DELIVERIES_PER_TICK):
                                raise ResidencyError(
                                    "future recurrent per-tick delivery cap exceeded")
                self._vrows.append(tuple(self._observer))
                self._spikes.append(tuple(spikes))
                self._evaluated.append(eligible)
                self._touched.append(tuple(sorted(destinations)))
                self._delivery_counts.append(len(deliveries))
                self._fanout.append(fanout)
                self.cursor += 1

            # Explicit canonical boundary in the SOFTWARE memory. A failing
            # AXI write may partially mutate this backing image, so the only
            # safe future physical pattern is a separately owned shadow epoch.
            self.cache.flush()
        except (ResidencyError, ValueError, PermissionError):
            self.status = "FAILED_REQUIRES_ABORT"
            self.cache._poisoned = True
            raise
        rec = WindowReceipt(
            first_tick=first, end_tick_exclusive=self.cursor,
            evaluated=sum(len(x) for x in self._evaluated[first:self.cursor]),
            emitted_spikes=sum(len(x) for x in self._spikes[first:self.cursor]),
            individual_deliveries=sum(self._delivery_counts[first:self.cursor]),
            canonical_flushed=True,
        )
        self.receipts.append(rec)
        return rec

    def finalize(self) -> dict:
        if self.status != "IN_PROGRESS" or self.cursor != self.total_ticks:
            raise ResidencyError("cannot finalize incomplete/failed paged session")
        self.cache.flush()
        self.status = "COMPLETE_UNCOMMITTED"
        return {
            "status": self.status,
            "ticks": self.cursor,
            "windows": len(self.receipts),
            "evaluations": sum(len(x) for x in self._evaluated),
            "spikes": sum(len(x) for x in self._spikes),
            "deliveries": sum(self._delivery_counts),
            "cache_counters": self.counters,
            "canonical_atomic_commit": "NOT_PROVEN",
            "vendor_axi": "NOT_TESTED",
        }
