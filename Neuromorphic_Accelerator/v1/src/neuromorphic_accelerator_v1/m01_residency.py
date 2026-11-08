"""M01: deterministic, hardware-agnostic DDR-backed neuron-state residency study.

This is a *traffic accounting model*, not an SNN simulator, DDR cycle simulator,
cache-coherence implementation, or a measured KV260 performance model.

One request represents one write-modifying access to a logical neuron's state.
All approaches receive exactly the same ordered requests, with identical state
size and total on-chip data budget. Synaptic weights, router traffic, DMA
setup, burst alignment, tag RAM, pipeline overlap and timestep semantics are
deliberately OUT OF SCOPE. See docs/M01_ARCHITECTURE_OPTIONS.md.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import random
from typing import Iterable


APPROACHES = ("individual", "block", "hybrid")
LOCALITIES = ("clustered", "dispersed")
SCHEMA = "m01-residency-traffic-v1"


def _int(name: str, value: object, *, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, not {value!r}")
    return value


@dataclass(frozen=True)
class StudyConfig:
    neuron_count: int = 4096
    state_bytes: int = 16
    resident_budget_bytes: int = 2048
    block_neurons: int = 16
    hybrid_pinned_neurons: int = 32
    max_transfer_bytes: int = 256

    def validate(self) -> None:
        for field in ("neuron_count", "state_bytes", "resident_budget_bytes",
                      "block_neurons", "max_transfer_bytes"):
            _int(field, getattr(self, field), minimum=1)
        _int("hybrid_pinned_neurons", self.hybrid_pinned_neurons, minimum=0)
        if self.neuron_count % self.block_neurons:
            raise ValueError("neuron_count must be divisible by block_neurons in M01")
        if self.hybrid_pinned_neurons >= self.neuron_count:
            raise ValueError("hybrid_pinned_neurons must be less than neuron_count")
        if (self.neuron_count - self.hybrid_pinned_neurons) % self.block_neurons:
            raise ValueError("hybrid unpinned neuron count must divide into full blocks")
        if self.resident_budget_bytes < self.block_neurons * self.state_bytes:
            raise ValueError("resident budget cannot hold one full block")
        if (self.resident_budget_bytes
                - self.hybrid_pinned_neurons * self.state_bytes
                < self.block_neurons * self.state_bytes):
            raise ValueError("hybrid needs pin capacity plus at least one cold block")


@dataclass
class Traffic:
    approach: str
    request_count: int = 0
    resident_hits: int = 0
    misses: int = 0
    prefetch_records: int = 0
    evictions: int = 0
    dirty_evictions: int = 0
    final_dirty_flushes: int = 0
    read_bytes: int = 0
    write_bytes: int = 0
    read_transactions: int = 0
    write_transactions: int = 0
    requested_resident_bytes: int = 0
    allocated_resident_bytes: int = 0
    wasted_resident_budget_bytes: int = 0
    maximum_used_resident_bytes: int = 0
    dynamic_cache_slots: int = 0
    pinned_records: int = 0
    distinct_neurons_touched: int = 0
    distinct_residency_units_touched: int = 0

    def as_dict(self) -> dict:
        value = asdict(self)
        value["total_bytes"] = self.read_bytes + self.write_bytes
        value["total_transactions"] = self.read_transactions + self.write_transactions
        value["hit_rate"] = (
            self.resident_hits / self.request_count if self.request_count else 0.0
        )
        return value


def generate_trace(
    *,
    neuron_count: int,
    active_neurons: int,
    requests: int,
    locality: str,
    seed: int = 1,
) -> tuple[int, ...]:
    """Produce the same shuffled *role sequence* under two neuron-ID mappings.

    Both cases touch exactly active_neurons distinct logical neurons, each with
    the same multiplicity. Clustered IDs are the first active_neurons; dispersed
    IDs span the whole address space. Differences are LOCATION, not event work.
    """
    _int("neuron_count", neuron_count, minimum=1)
    _int("active_neurons", active_neurons, minimum=1)
    _int("requests", requests, minimum=1)
    _int("seed", seed, minimum=0)
    if active_neurons > neuron_count:
        raise ValueError("active_neurons cannot exceed neuron_count")
    if requests < active_neurons:
        raise ValueError("requests must cover every declared active neuron")
    if locality not in LOCALITIES:
        raise ValueError(f"locality must be one of {LOCALITIES}")
    if locality == "clustered":
        ids = tuple(range(active_neurons))
    else:
        ids = tuple(i * neuron_count // active_neurons
                    for i in range(active_neurons))
    roles = list(range(active_neurons))
    roles.extend(i % active_neurons for i in range(requests - active_neurons))
    random.Random(seed).shuffle(roles)
    return tuple(ids[i] for i in roles)


def simulate(
    config: StudyConfig,
    trace: Iterable[int],
    *,
    approach: str,
) -> Traffic:
    """Count idealized state reads/writes at cold start through final flush.

    A: neuron-granular LRU.
    B: fixed-size, whole-block LRU.
    C: first P logical IDs pinned in local memory + LRU blocks over rest.
       Pinned IDs are a disclosed, pre-registered prefix, NOT inferred from
       evaluation traffic. Pinned records are prefetched even if never used.
       Pinned and dynamic bytes share the SAME total on-chip capacity.
    """
    config.validate()
    if approach not in APPROACHES:
        raise ValueError(f"unknown approach {approach!r}")
    requests = tuple(trace)
    for neuron_id in requests:
        if type(neuron_id) is not int or not (0 <= neuron_id < config.neuron_count):
            raise ValueError(f"invalid neuron ID in trace: {neuron_id!r}")

    nbytes = config.state_bytes
    page_bytes = config.block_neurons * nbytes
    pins = config.hybrid_pinned_neurons if approach == "hybrid" else 0
    unit_bytes = nbytes if approach == "individual" else page_bytes
    dynamic_bytes = config.resident_budget_bytes - pins * nbytes
    slots = dynamic_bytes // unit_bytes
    if slots < 1:
        raise ValueError("resident budget cannot hold one dynamic cache unit")

    total_allocation = pins * nbytes + slots * unit_bytes
    result = Traffic(
        approach=approach,
        requested_resident_bytes=config.resident_budget_bytes,
        allocated_resident_bytes=total_allocation,
        wasted_resident_budget_bytes=config.resident_budget_bytes - total_allocation,
        dynamic_cache_slots=slots,
        pinned_records=pins,
        request_count=len(requests),
    )
    # LRU map: every dynamically resident unit becomes dirty on its first hit.
    # OrderedDict moves most recently touched entries to the right.
    cache: OrderedDict[int, None] = OrderedDict()
    dirty_pins: set[int] = set()
    touched_units: set[tuple[str, int]] = set()

    def transfer(size: int, *, write: bool) -> None:
        if size <= 0:
            raise AssertionError("zero-sized transfer")
        ntrans = (size + config.max_transfer_bytes - 1) // config.max_transfer_bytes
        if write:
            result.write_bytes += size
            result.write_transactions += ntrans
        else:
            result.read_bytes += size
            result.read_transactions += ntrans

    if pins:
        for neuron in range(pins):
            transfer(nbytes, write=False)  # explicit cold-start pin prefetch
        result.prefetch_records = pins

    for neuron in requests:
        if pins and neuron < pins:
            touched_units.add(("pinned", neuron))
            dirty_pins.add(neuron)
            result.resident_hits += 1
            continue

        if approach == "individual":
            key = neuron
        elif approach == "hybrid":
            key = (neuron - pins) // config.block_neurons
        else:
            key = neuron // config.block_neurons
        touched_units.add(("dynamic", key))

        if key in cache:
            cache.move_to_end(key)
            result.resident_hits += 1
        else:
            result.misses += 1
            if len(cache) == slots:
                cache.popitem(last=False)
                result.evictions += 1
                result.dirty_evictions += 1
                transfer(unit_bytes, write=True)
            transfer(unit_bytes, write=False)
            cache[key] = None
            used = pins * nbytes + len(cache) * unit_bytes
            result.maximum_used_resident_bytes = max(
                result.maximum_used_resident_bytes, used
            )

    # The experiment closes with complete dirty-state writeback, so otherwise
    # hidden write traffic is not omitted by comparing different cache sizes.
    for _key in cache:
        transfer(unit_bytes, write=True)
        result.final_dirty_flushes += 1
    for _neuron in sorted(dirty_pins):
        transfer(nbytes, write=True)
        result.final_dirty_flushes += 1

    result.distinct_neurons_touched = len(set(requests))
    result.distinct_residency_units_touched = len(touched_units)
    result.maximum_used_resident_bytes = max(
        result.maximum_used_resident_bytes, pins * nbytes
    )
    if result.resident_hits + result.misses != result.request_count:
        raise AssertionError("request accounting not conserved")
    if result.allocated_resident_bytes > config.resident_budget_bytes:
        raise AssertionError("on-chip budget exceeded")
    return result


def serial_transfer_estimate_ns(
    traffic: Traffic,
    *,
    illustrative_transaction_overhead_ns: float,
    illustrative_bandwidth_mbps: float,
) -> float:
    """Optional pure *assumption*; no overlap/compute/DDR contention modeled."""
    overhead = illustrative_transaction_overhead_ns
    bandwidth = illustrative_bandwidth_mbps
    if (not math.isfinite(overhead) or overhead < 0
            or not math.isfinite(bandwidth) or bandwidth <= 0):
        raise ValueError("illustrative overhead must be finite >=0, bandwidth finite >0")
    return (traffic.read_transactions + traffic.write_transactions) * overhead + (
        (traffic.read_bytes + traffic.write_bytes) * 1000.0 / bandwidth
    )


def run_study(
    config: StudyConfig,
    *,
    active_neurons: int = 64,
    requests: int = 512,
    seed: int = 1,
    locality: str = "clustered",
    illustrative_transaction_overhead_ns: float | None = None,
    illustrative_bandwidth_mbps: float | None = None,
) -> dict:
    config.validate()
    if (illustrative_transaction_overhead_ns is None) != (
        illustrative_bandwidth_mbps is None
    ):
        raise ValueError("both illustrative timing assumptions must be supplied together")
    trace = generate_trace(
        neuron_count=config.neuron_count,
        active_neurons=active_neurons,
        requests=requests,
        locality=locality,
        seed=seed,
    )
    trace_bytes = json.dumps(trace, separators=(",", ":")).encode("ascii")
    results: dict = {}
    for approach in APPROACHES:
        result = simulate(config, trace, approach=approach)
        row = result.as_dict()
        if illustrative_transaction_overhead_ns is not None:
            row["hypothetical_serial_memory_ns"] = serial_transfer_estimate_ns(
                result,
                illustrative_transaction_overhead_ns=illustrative_transaction_overhead_ns,
                illustrative_bandwidth_mbps=illustrative_bandwidth_mbps,
            )
        results[approach] = row
    return {
        "schema": SCHEMA,
        "measurement_status": "PC_ONLY_TRAFFIC_ACCOUNTING_NOT_HARDWARE_MEASURED",
        "work_unit": "one write-modifying neuron state access; NOT a timed LIF spike",
        "scope": {
            "included": ["cold-start loads", "dirty evictions",
                         "final writebacks", "fixed transfer splitting",
                         "same state-update trace across approaches"],
            "excluded": ["synapses and fanout", "LIF arithmetic",
                         "DMA/AXI setup and alignment", "PS/PL scheduling",
                         "hardware cache tag overhead", "overlap/queueing",
                         "KV260 measured DDR timing", "energy"],
        },
        "config": asdict(config),
        "trace": {
            "locality": locality,
            "active_neurons": active_neurons,
            "requests": requests,
            "seed": seed,
            "sha256": hashlib.sha256(trace_bytes).hexdigest(),
            "first_16_neuron_ids": list(trace[:16]),
        },
        "illustrative_timing_assumptions": (
            None if illustrative_transaction_overhead_ns is None
            else {
                "transaction_overhead_ns": illustrative_transaction_overhead_ns,
                "bandwidth_mbps_decimal": illustrative_bandwidth_mbps,
                "disclaimer": "hypothetical serial traffic only, NOT KV260 latency",
            }
        ),
        "results": results,
    }
