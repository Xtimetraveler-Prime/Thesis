"""M06 CPU-ONLY on-chip sparse LIF scheduling with paged neuron voltage.

This independent prototype runs M02 rev1 neural math using the exact M06
BlockCache rather than keeping working voltages in a resident Python array.
For records >=6 bytes, fields [0:2] hold signed16 voltage and [2:6]
hold the last completed logical tick + 1 (zero = never evaluated); a
future watermark is rejected. Records of 2..5 bytes retain voltage-only
compatibility with the initial M06 source baseline.

Only the small/nonzero membership bitmap, static neuron CONFIG, and a future
delivery queue remain on-chip *conceptually*. Synapse adjacency is currently
on-chip: paged synapses are a future M06 design decision. The full trace is
a TEST-ONLY observer copy excluded from cache transfer counters.
Every invocation begins at logical tick 0 from independently verified
canonical M02 initial state: continuing an already-committed prior epoch,
including carried recurrent events, is future M06 work.

No physical DDR/AXI/PS/FPGA behavior, throughput or true hardware memory
capacity is established by executing Python.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable

from .m02_types import InputCurrent, Network, ReferenceTrace, validate
from .m06_block_residency import (
    BlockCache, CanonicalImage, Geometry, ResidencyError,
)

MAX_M05_NEURONS = 1024
MAX_M05_SYNAPSES = 4096
MAX_M05_TICKS = 64
MAX_M05_DELAY = 8
MAX_M05_EXTERNAL = 32768
MAX_M05_DELIVERIES_PER_TICK = 4096


@dataclass(frozen=True)
class PagedRun:
    trace: ReferenceTrace
    evaluated_ids_by_tick: tuple[tuple[int, ...], ...]
    touched_ids_by_tick: tuple[tuple[int, ...], ...]
    deliveries_by_tick: tuple[int, ...]
    fanout_edges_by_tick: tuple[int, ...]
    cache_counters: dict
    emitted_spikes: int
    storage_model: str = "SOFTWARE_BLOCK_CACHE_NO_HARDWARE"

    @property
    def evaluations(self) -> int:
        return sum(len(r) for r in self.evaluated_ids_by_tick)


def check_bounded_network(net: Network, inputs: Iterable[InputCurrent], ticks: int
                          ) -> tuple[InputCurrent, ...]:
    if not isinstance(net, Network):
        raise ValueError("expected M02 Network")
    events = validate(net, inputs, ticks)
    if (net.state_bits != 16 or len(net.neurons) > MAX_M05_NEURONS
            or len(net.synapses) > MAX_M05_SYNAPSES
            or ticks > MAX_M05_TICKS or len(events) > MAX_M05_EXTERNAL):
        raise ValueError("outside accepted bounded M05 signed16 neural envelope")
    if any(s.delay > MAX_M05_DELAY for s in net.synapses):
        raise ValueError("recurrent delays greater than 8 not supported")
    if any(events[j].tick > events[j+1].tick for j in range(len(events)-1)):
        raise ValueError("rolling external events must be tick-sorted")
    return events


def new_canonical_neuron_image(net: Network, geometry: Geometry, *,
                               owner: str) -> CanonicalImage:
    """Initialize canonical state independently of future cache accesses."""
    check_bounded_network(net, (), 1)
    geometry.validate()
    if (geometry.logical_neurons != len(net.neurons)
            or geometry.bytes_per_neuron < 2):
        raise ValueError("canonical image must allocate one >=2-byte row per neuron")
    rows = (cell.initial_v.to_bytes(2, "little", signed=True)
            + bytes(geometry.bytes_per_neuron - 2)
            for cell in net.neurons)
    return CanonicalImage(geometry, emulated_owner=owner, initial=b"".join(rows))


def replay_with_paging(net: Network, inputs: Iterable[InputCurrent], *,
                       ticks: int, cache: BlockCache) -> PagedRun:
    """Execute independently checked sparse recurrence while paging LIF states.

    The *working* voltage is ALWAYS fetched via cache.read for every
    evaluated neuron; no shadow voltage is used to decide firing, future
    scheduling or eligibility. The trace-only shadow is excluded from
    measured cache traffic and must not be confused with hardware SRAM.
    An admitted-future-event overflow or any transfer fault poisons the
    current run. Page writeback is not transactionally rolled back, so a
    failed run MUST NOT be retried without explicit recovery.
    """
    events = check_bounded_network(net, inputs, ticks)
    if (cache.geometry.logical_neurons != len(net.neurons)
            or cache.geometry.bytes_per_neuron < 2):
        raise ValueError("cache must contain one >=2B state row per logical neuron")
    if cache.counters.accesses or cache.resident_pages or cache.poisoned:
        raise ValueError("run requires fresh dedicated cache and canonical initial state")
    expected_initial = b"".join(
        n.initial_v.to_bytes(2, "little", signed=True)
        + bytes(cache.geometry.bytes_per_neuron - 2) for n in net.neurons)
    # Test-only canonical snapshot checks that paging starts at precisely the
    # M02 initial state. This is NOT a physical DDR read or cache traffic.
    if cache.store.snapshot(owner=cache.owner) != expected_initial:
        raise ValueError("canonical state not initialized for requested M02 network")

    n = len(net.neurons)
    incoming_by_tick: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for e in events:
        incoming_by_tick[e.tick].append((e.neuron, e.current))
    out: list[list[tuple[int, int, int]]] = [[] for _ in range(n)]
    for edge in net.synapses:
        out[edge.pre].append((edge.post, edge.weight, edge.delay))
    nonzero = {i for i, cell in enumerate(net.neurons) if cell.initial_v != 0}
    biased = {i for i, cell in enumerate(net.neurons) if cell.bias != 0}
    # Shadow output trace exists ONLY for regression observation: no reads
    # from this array affect algorithmic work, recurrence or memory counters.
    observer_voltage = [c.initial_v for c in net.neurons]
    voltage_rows: list[tuple[int, ...]] = []
    spike_rows: list[tuple[int, ...]] = []
    eval_rows: list[tuple[int, ...]] = []
    touched_rows: list[tuple[int, ...]] = []
    delivery_rows: list[int] = []
    fanout_rows: list[int] = []
    try:
        for t in range(ticks):
            deliveries = incoming_by_tick.pop(t, ())
            if len(deliveries) > MAX_M05_DELIVERIES_PER_TICK:
                raise ResidencyError("M05 4096 individual deliveries per tick exceeded")
            incoming = defaultdict(int)
            targets: set[int] = set()
            for dst, weight in deliveries:
                incoming[dst] += weight
                targets.add(dst)  # zero/canceling events still wake neurons
            eligible = tuple(sorted(nonzero | biased | targets))
            next_nonzero: set[int] = set()
            spikes: list[int] = []
            for neuron in eligible:
                # The only *runtime* voltage source is page-loaded state.
                record = cache.read(neuron)
                prev = int.from_bytes(record[:2], "little", signed=True)
                if len(record) >= 6:
                    last_completed = int.from_bytes(record[2:6], "little")
                    # 0 means never evaluated in this logical epoch, and
                    # t+1 represents the last completed update at tick t.
                    # The cache must preserve this watermark over eviction.
                    if last_completed > t:
                        raise ResidencyError("future last-update tick in paged neuron state")
                cell = net.neurons[neuron]
                product = prev * net.decay_num
                decayed = ((abs(product) // net.decay_den)
                           * (-1 if product < 0 else 1))
                raw = decayed + cell.bias + incoming[neuron]
                value = max(-32768, min(32767, raw))
                if value >= cell.threshold:
                    spikes.append(neuron)
                    value = cell.reset_v
                new_record = value.to_bytes(2, "little", signed=True)
                if len(record) >= 6:
                    new_record += (t + 1).to_bytes(4, "little") + record[6:]
                else:
                    new_record += record[2:]
                cache.write(neuron, new_record)
                if value != 0:
                    next_nonzero.add(neuron)
                observer_voltage[neuron] = value
            nonzero = next_nonzero
            fanout = 0
            for pre in spikes:
                for post, weight, delay in out[pre]:
                    fanout += 1
                    future = t + delay
                    if future < ticks:
                        incoming_by_tick[future].append((post, weight))
                        if (len(incoming_by_tick[future])
                                > MAX_M05_DELIVERIES_PER_TICK):
                            raise ResidencyError("M05 recurrent arrival capacity exceeded")
            voltage_rows.append(tuple(observer_voltage))
            spike_rows.append(tuple(spikes))
            eval_rows.append(eligible)
            touched_rows.append(tuple(sorted(targets)))
            delivery_rows.append(len(deliveries))
            fanout_rows.append(fanout)
        cache.flush()  # All dirty state must reach canonical software image.
    except (ValueError, ResidencyError, PermissionError):
        cache._poisoned = True  # sticky quarantine; no implicit retry/rollback
        raise
    return PagedRun(
        trace=ReferenceTrace(tuple(voltage_rows), tuple(spike_rows)),
        evaluated_ids_by_tick=tuple(eval_rows),
        touched_ids_by_tick=tuple(touched_rows),
        deliveries_by_tick=tuple(delivery_rows),
        fanout_edges_by_tick=tuple(fanout_rows),
        cache_counters=asdict(cache.counters),
        emitted_spikes=sum(map(len, spike_rows)),
    )
