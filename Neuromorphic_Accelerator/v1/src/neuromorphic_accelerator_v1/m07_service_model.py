"""M07.5 bounded SOURCE-ONLY queue/transfer service and batching acceptance model.

Not RTL, cycle-accurate AXI, physical DDR, calibrated board timing, or a
new execution engine. The M06 canonical image captures each *completed*
synchronous block transfer (not its bus-channel beats). Deliberately assumed
service-cycle costs are applied serially to this trace after the accepted
M06 replay passes independent M02/M03 exact neural and canonical checks.

No access to future event arrival influences neural work. Event batching
modifies only the separately modeled ingress queue, never neuron ordering,
synaptic arrival tick, signed arithmetic or M06 cache replacement.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace

from .m02_dense_reference import evaluate_dense
from .m02_event_reference import evaluate_events
from .m03_sparse_reference import evaluate_exact_sparse
from .m03_workloads import Workload, WorkloadSpec, build_workload, canonicalize_trace
from .m03_traffic import ComparisonConfig, compare_workload
from .m06_block_residency import BlockCache, CanonicalImage, Geometry
from .m06_paged_replay import new_canonical_neuron_image, replay_with_paging
from .m07_activity_cache import ActivityHistoryCache
from .m07_policy_baseline import DirectFetchCache
from .m07_matched_controls import FourWayPolicyConfig

POLICIES = ("direct", "lru", "activity_history")
SCOPE = "M07_5_SYNTHETIC_SERIAL_SERVICE_ONLY_NO_HARDWARE_TIMING"


@dataclass(frozen=True)
class ServiceAssumptions:
    """User-editable DIMENSIONLESS toy cycle costs; NOT device calibration."""
    fifo_depth_events: int = 4
    enqueue_batch_setup_cycles: int = 2
    consumer_event_interval_cycles: int = 2
    neuron_compute_cycles: int = 3
    read_transfer_chunk_cycles: int = 5
    write_transfer_chunk_cycles: int = 7
    write_b_ack_cycles: int = 2
    history_depth: int = 16

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if type(value) is not int or value < 1:
                raise ValueError(f"{name}: positive integer assumption required")
        if self.fifo_depth_events > 4096 or self.history_depth > 4096:
            raise ValueError("model FIFO/history bounds exceeded")


class TraceImage(CanonicalImage):
    """Passive log of successful M06 CanonicalImage block operations only."""

    def __init__(self, geometry: Geometry, *, owner: str, initial: bytes):
        super().__init__(geometry, emulated_owner=owner, initial=initial)
        self.completed: list[dict] = []

    def read_block(self, page: int, *, owner: str):
        data, version, chunks = super().read_block(page, owner=owner)
        self.completed.append({"op": "R", "page": page, "chunks": chunks,
                               "bytes": len(data), "version": version})
        return data, version, chunks

    def write_block(self, page: int, data: bytes, *,
                    expected_version: int, owner: str):
        new_version, chunks = super().write_block(
            page, data, expected_version=expected_version, owner=owner)
        self.completed.append({"op": "W", "page": page, "chunks": chunks,
                               "bytes": len(data), "version": new_version})
        return new_version, chunks


def _ingress_model(arrivals_by_tick: tuple[int, ...], *,
                   batch_width: int, config: ServiceAssumptions) -> dict:
    """Serialized per-tick enqueue and dequeue with declared consumer interval.

    All due recurrent+external events are offered at the START of their
    logical tick (M03 oracle counts). Each enqueue accepts <=batch_width
    events, then pays a declared setup delay before next enqueue. Consumer
    removes one event every declared service interval. No backlog crosses a
    logical tick. No AXI
    arbitration, compute overlap, or event-generation timestamps implied.
    """
    if type(batch_width) is not int or batch_width < 1 or batch_width > 4096:
        raise ValueError("batch_width must be an integer within 1..4096")
    config.validate()
    result = {"arrivals": 0, "consumed": 0, "batch_dispatches": 0,
              "producer_full_stall_cycles": 0, "queue_model_cycles": 0,
              "peak_occupancy_events": 0, "ticks_with_events": 0,
              "batch_width": batch_width}
    for arrivals in arrivals_by_tick:
        if type(arrivals) is not int or arrivals < 0 or arrivals > 4096:
            raise ValueError("M05 tick delivery count must be within 0..4096")
        if arrivals == 0:
            continue
        result["ticks_with_events"] += 1
        remain, occupancy, setup, consumed = arrivals, 0, 0, 0
        consumer_cooldown = 0
        cycles = 0
        while remain or occupancy:
            if remain:
                if setup:
                    setup -= 1
                elif occupancy >= config.fifo_depth_events:
                    result["producer_full_stall_cycles"] += 1
                else:
                    k = min(batch_width, config.fifo_depth_events-occupancy, remain)
                    occupancy += k
                    remain -= k
                    result["batch_dispatches"] += 1
                    setup = config.enqueue_batch_setup_cycles - 1
            result["peak_occupancy_events"] = max(
                result["peak_occupancy_events"], occupancy)
            if consumer_cooldown:
                consumer_cooldown -= 1
            elif occupancy:
                occupancy -= 1
                consumed += 1
                consumer_cooldown = config.consumer_event_interval_cycles - 1
            cycles += 1
        if consumed != arrivals:
            raise AssertionError("queue model consumed a different number of events")
        result["arrivals"] += arrivals
        result["consumed"] += consumed
        result["queue_model_cycles"] += cycles
    return result


def _service_model(ops: list[dict], geom: Geometry,
                   config: ServiceAssumptions) -> dict:
    """Conservative serialized model after synchronous M06 acknowledgments.

    This reproduces software operation ORDER, not actual R/RLAST/B/ARVALID
    handshakes. 'B-before-AR guards' count W followed by R in this source
    order, and mean only that M06's write_block returned first. Physical
    B/AR cycles and outstanding AXI requests remain UNKNOWN/None.
    """
    read_bytes = write_bytes = read_tx = write_tx = 0
    cost = 0
    guarded = 0
    prev = None
    for entry in ops:
        if entry["op"] not in ("R", "W"):
            raise AssertionError("unrecognized canonical block service")
        if entry["bytes"] != geom.page_bytes:
            raise AssertionError("partial page falsely treated as a completed transfer")
        if entry["chunks"] != (
            (geom.page_bytes + geom.max_model_transfer_bytes - 1)
            // geom.max_model_transfer_bytes):
            raise AssertionError("wrong model chunk count")
        if prev == "W" and entry["op"] == "R":
            guarded += 1
        if entry["op"] == "R":
            read_bytes += entry["bytes"]
            read_tx += entry["chunks"]
            cost += entry["chunks"] * config.read_transfer_chunk_cycles
        else:
            write_bytes += entry["bytes"]
            write_tx += entry["chunks"]
            cost += (entry["chunks"] * config.write_transfer_chunk_cycles
                     + config.write_b_ack_cycles)
        prev = entry["op"]
    return {
        "completed_software_block_reads": sum(x["op"] == "R" for x in ops),
        "completed_software_block_writes": sum(x["op"] == "W" for x in ops),
        "state_read_bytes": read_bytes, "state_write_bytes": write_bytes,
        "read_chunks": read_tx, "write_chunks": write_tx,
        "source_order_write_then_read_guards": guarded,
        "assumed_serial_transfer_cycles": cost,
        "assumed_max_concurrent_software_block_transfer": 1 if ops else 0,
        "actual_axi_b_before_ar_cycles": None,
        "actual_outstanding_axi_requests": None,
        "actual_physical_ddr_bytes": None,
    }


def evaluate_service_case(workload: Workload, geometry: Geometry,
                          *, policy: str, batch_width: int,
                          synapse_record_bytes: int,
                          assumptions: ServiceAssumptions) -> dict:
    """Cross-check independent M02/M03 and executed M06 before model timing."""
    if policy not in POLICIES:
        raise ValueError("unsupported M07 cache policy")
    assumptions.validate()
    if type(synapse_record_bytes) is not int or synapse_record_bytes < 1:
        raise ValueError("synapse_record_bytes must be a positive integer")
    _ingress_model((), batch_width=batch_width, config=assumptions)
    geometry.validate()
    net, inputs, ticks = (workload.network, workload.external_currents,
                          workload.spec.ticks)
    if geometry.logical_neurons != len(net.neurons) or geometry.bytes_per_neuron < 6:
        raise ValueError("state image geometry must match the M03 workload")
    dense = evaluate_dense(net, inputs, ticks=ticks)
    queued = evaluate_events(net, inputs, ticks=ticks)
    sparse = evaluate_exact_sparse(net, inputs, ticks=ticks)
    if dense != queued or dense != sparse.trace:
        raise AssertionError("M02 dense/queued/M03 exact neural oracle mismatch")
    owner = "M07_5_SOFTWARE_ONLY"
    pristine = new_canonical_neuron_image(net, geometry, owner=owner)
    store = TraceImage(geometry, owner=owner, initial=pristine.snapshot(owner=owner))
    if policy == "direct":
        cache = DirectFetchCache(store, owner=owner)
    elif policy == "lru":
        cache = BlockCache(store, owner=owner)
    else:
        cache = ActivityHistoryCache(
            store, owner=owner, history_depth=assumptions.history_depth)
    run = replay_with_paging(net, inputs, ticks=ticks, cache=cache)
    if (run.trace != dense or
            run.evaluated_ids_by_tick != sparse.evaluated_ids_by_tick or
            run.deliveries_by_tick != sparse.deliveries_by_tick or
            run.fanout_edges_by_tick != sparse.traversed_synapses_by_tick):
        raise AssertionError("M07 timing assumption changed neural recurrence")
    last = [0] * len(net.neurons)
    for t, row in enumerate(sparse.evaluated_ids_by_tick):
        for i in row:
            last[i] = t + 1
    expected = b"".join(
        v.to_bytes(2, "little", signed=True)
        + last[i].to_bytes(4, "little")
        + bytes(geometry.bytes_per_neuron-6)
        for i,v in enumerate(dense.voltage_rows[-1]))
    if (store.snapshot(owner=owner) != expected or cache.poisoned or
            cache.dirty_pages):
        raise AssertionError("M07 timing replay final canonical state not exact")
    transfers = _service_model(store.completed, geometry, assumptions)
    counters = asdict(cache.counters)
    if (transfers["state_read_bytes"] != counters["read_bytes"] or
            transfers["state_write_bytes"] != counters["write_bytes"] or
            transfers["read_chunks"] != counters["read_transactions"] or
            transfers["write_chunks"] != counters["write_transactions"] or
            counters["accesses"] != 2*run.evaluations):
        raise AssertionError("recorded transfers and accepted cache counters differ")
    queue = _ingress_model(run.deliveries_by_tick,
                           batch_width=batch_width, config=assumptions)
    if queue["arrivals"] != sum(sparse.deliveries_by_tick):
        raise AssertionError("ingress batcher changed recurrent/external work")
    # M03 synapse traffic remains a model of *external* precontiguous edges;
    # M06 does NOT issue it, so do NOT charge it as actual service cycles.
    m03config = ComparisonConfig(
        state_bytes=geometry.bytes_per_neuron,
        block_neurons=geometry.neurons_per_block,
        ddr_state_cache_bytes=geometry.resident_budget_bytes,
        onchip_state_capacity_bytes=max(geometry.resident_budget_bytes+1,
                                        geometry.image_bytes),
        max_transfer_bytes=geometry.page_bytes,
        synapse_record_bytes=synapse_record_bytes,
    )
    controls = compare_workload(workload,m03config)
    syn = controls["four_way_models"]["event/ddr"]
    if (syn["evaluated_neuron_steps"] != run.evaluations or
            syn["synapse_edge_visits"] != sum(run.fanout_edges_by_tick)):
        raise AssertionError("M03 synapse work not matched to paged recurrence")
    compute_cost = assumptions.neuron_compute_cycles * run.evaluations
    model_total = (compute_cost + queue["queue_model_cycles"]
                   + transfers["assumed_serial_transfer_cycles"])
    return {
        "policy": policy,
        "batch_width": batch_width,
        "synapse_record_bytes_hypothetical": synapse_record_bytes,
        "role_sha256": workload.canonical_role_sha256,
        "input_sha256": workload.relabeled_input_sha256,
        "canonical_trace_sha256": canonicalize_trace(workload,dense)[
            "canonical_trace_sha256"],
        "evaluations": run.evaluations,
        "spikes": sum(map(len,run.trace.spike_rows)),
        "delivered_events": sum(run.deliveries_by_tick),
        "fanout_edge_visits": sum(run.fanout_edges_by_tick),
        "cache_counters": counters,
        "transfers": transfers,
        "ingress_queue": queue,
        "synapse_ddr_analytical_bytes_not_issued": syn["synapse_read_bytes"],
        "synapse_ddr_analytical_transactions_not_issued": syn["synapse_transactions"],
        "modeled_compute_cycles_assumed": compute_cost,
        "modeled_serialized_complete_run_cycles_assumed": model_total,
        "actual_run_cycles": None, "actual_runtime_ns": None,
        "actual_queue_stalls": None, "actual_axi_fence_cycles": None,
        "real_ddr_bytes": None, "resource_utilization": None,
        "neural_and_final_canonical_parity": True,
    }


@dataclass(frozen=True)
class ServiceSweepPlan:
    neurons: int = 32
    active_roles: int = 8
    fanout: int = 3
    external_events_per_tick: int = 4
    ticks: int = 8
    seeds: tuple[int,...] = (17,23)
    batches: tuple[int,...] = (1,4)
    synapse_record_bytes: tuple[int,...] = (4,8)
    state_bytes: int = 16
    block_neurons: int = 4
    resident_slots: int = 2

    def validate(self) -> None:
        for k in ("neurons","active_roles","ticks","state_bytes",
                  "block_neurons","resident_slots"):
            v=getattr(self,k)
            if type(v) is not int or v < 1:
                raise ValueError(k + " must be a positive integer")
        for k in ("fanout","external_events_per_tick"):
            v=getattr(self,k)
            if type(v) is not int or v < 0:
                raise ValueError(k + " must be nonnegative")
        for k in ("seeds","batches","synapse_record_bytes"):
            v=getattr(self,k)
            if (type(v) is not tuple or not v or
                    tuple(sorted(set(v))) != v or
                    any(type(x) is not int or x < (0 if k=="seeds" else 1)
                        for x in v)):
                raise ValueError(k + " must be unique ascending positive tuple")
        WorkloadSpec(neuron_count=self.neurons, active_roles=self.active_roles,
            fanout_per_active=self.fanout,
            external_events_per_tick=self.external_events_per_tick,
            ticks=self.ticks, seed=0).validate()
        FourWayPolicyConfig(state_bytes=self.state_bytes,
            block_neurons=self.block_neurons,
            resident_slots=self.resident_slots,
            onchip_state_capacity_bytes=self.neurons*self.state_bytes+1,
        ).validate(self.neurons)


def run_service_sweep(plan: ServiceSweepPlan,
                      assumptions: ServiceAssumptions) -> dict:
    plan.validate()
    assumptions.validate()
    geom = FourWayPolicyConfig(
        state_bytes=plan.state_bytes, block_neurons=plan.block_neurons,
        resident_slots=plan.resident_slots,
        onchip_state_capacity_bytes=plan.neurons*plan.state_bytes+1,
    ).validate(plan.neurons)[0]
    rows = []
    for seed in plan.seeds:
        for locality in ("clustered","dispersed"):
            spec = WorkloadSpec(neuron_count=plan.neurons,
                active_roles=plan.active_roles, fanout_per_active=plan.fanout,
                external_events_per_tick=plan.external_events_per_tick,
                ticks=plan.ticks, seed=seed, locality=locality)
            w=build_workload(spec)
            combos = []
            for policy in POLICIES:
                for batch in plan.batches:
                    for record_bytes in plan.synapse_record_bytes:
                        combos.append(evaluate_service_case(
                            w,geom,policy=policy,batch_width=batch,
                            synapse_record_bytes=record_bytes,
                            assumptions=assumptions))
            witness = combos[0]
            for entry in combos:
                for key in ("role_sha256","input_sha256",
                            "canonical_trace_sha256","evaluations","spikes",
                            "delivered_events","fanout_edge_visits"):
                    if entry[key] != witness[key]:
                        raise AssertionError("source service ablation changed work: "+key)
            for policy in POLICIES:
                variants=[e for e in combos if e["policy"]==policy]
                base=variants[0]
                for e in variants:
                    if (e["transfers"] != base["transfers"] or
                            e["cache_counters"] != base["cache_counters"]):
                        raise AssertionError("batch/record width changed cache transfers")
            rows.append({"seed":seed, "locality":locality,
                         "role_sha256":w.canonical_role_sha256,
                         "trace_sha256":witness["canonical_trace_sha256"],
                         "cases":combos})
    for seed in plan.seeds:
        a,b=[r for r in rows if r["seed"]==seed]
        if (a["role_sha256"]!=b["role_sha256"] or
                a["trace_sha256"]!=b["trace_sha256"]):
            raise AssertionError("M03 role-equivalent locality trace changed")
    return {
        "schema":"m07-5-serialized-source-service-v1",
        "scope":SCOPE,
        "plan":asdict(plan), "assumptions":asdict(assumptions),
        "number_of_matched_cases":sum(len(r["cases"]) for r in rows),
        "rows":rows,
        "model_assumption": (
            "event arrivals offered at start of each logical tick; FIFO "
            "enqueues batch_width with setup delay and declared consumer interval; "
            "state blocks are synchronous completed M06 transfers; "
            "compute, queue and page-service costs ADDED serially, no overlap; "
            "write-B model completion before next read is IMPLIED by M06 "
            "function return; NO AXI waveform / calibration"),
        "synapse_format_study": (
            "4B/8B hypothetical edge record sizes change M03 analytical "
            "external synapse read bytes; M06 adjacency remains on-chip"),
        "actual_hardware_performance_measured":False,
        "physical_ddr_executed":False,
        "no_vendor_hls_rtl_executed":True,
    }
