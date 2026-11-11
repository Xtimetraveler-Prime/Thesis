"""M07.1 SOURCE-ONLY direct-fetch control versus accepted M06 LRU residency.

Both policies use the unmodified M06 CanonicalImage, BlockCache transfer/lease/
version checking, dirty writeback and M06 exact paged neural execution. The
direct policy admits one paired (read, write) LIF evaluation at a time and
invalidates the just-written page *after its acknowledged writeback*. This
avoids incorrectly charging a second fill for the write half of one neuron
evaluation but provides NO reuse between evaluations. It is NOT an AXI/DDR
controller or an RTL scheduler. Only canonical full-page traffic is counted.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from .m02_dense_reference import evaluate_dense
from .m02_event_reference import evaluate_events
from .m03_sparse_reference import evaluate_exact_sparse
from .m03_workloads import Workload, canonicalize_trace
from .m06_block_residency import BlockCache, Geometry, ResidencyError
from .m06_paged_replay import new_canonical_neuron_image, replay_with_paging

Policy = Literal["direct", "lru", "activity_history"]
SOURCE_SCOPE = "M07_1_PC_ONLY_CANONICAL_BLOCK_POLICY_NO_VENDOR_NO_BOARD"


class DirectFetchCache(BlockCache):
    """One block fetch + one acknowledged writeback per evaluated neuron.

    Strict paired read/write API: no speculative second read, read-only
    prefetch, retained clean hit or implicit partial evaluation completion.
    This is a SOURCE MODEL of the atomic evaluation service boundary, not
    a general replacement for M06's public read/write cache interface.
    On an invalid pair the cache is quarantined rather than discarded.
    """

    def __init__(self, store, *, owner: str):
        super().__init__(store, owner=owner)
        self._pending_neuron: int | None = None
        self.direct_invalidations = 0

    @property
    def pending_neuron(self) -> int | None:
        return self._pending_neuron

    def _protocol_failure(self, message: str) -> None:
        self._poisoned = True
        raise ResidencyError(message)

    def read(self, neuron: int) -> bytes:
        if self._pending_neuron is not None:
            self._protocol_failure("direct policy requires write before next read")
        data = super().read(neuron)
        self._pending_neuron = neuron
        return data

    def write(self, neuron: int, data: bytes) -> None:
        if self._pending_neuron is None or neuron != self._pending_neuron:
            self._protocol_failure("direct policy write must match pending read")
        super().write(neuron, data)
        # Base M06 flush retains fail-closed version checks, owner lease,
        # whole-page atomic commit and transfer-ack validation.
        super().flush()
        if len(self._resident) != 1 or self.dirty_pages:
            self._protocol_failure("direct policy failed to commit one clean block")
        # This is a voluntary invalidation, NOT a capacity eviction.
        # Track it separately from accepted M06 CacheCounters.evictions.
        self._resident.clear()
        self.direct_invalidations += 1
        self._pending_neuron = None

    def flush(self) -> None:
        if self._pending_neuron is not None:
            self._protocol_failure("direct policy cannot flush incomplete evaluation")
        super().flush()


def run_policy(workload: Workload, geometry: Geometry, *, policy: Policy,
               history_depth: int = 16) -> dict:
    """Refuse traffic results unless independent M02/M03 neural checks pass.

    Each result starts with a fresh M02 canonical image and executes the
    SAME M06 paged recurrence with a different storage policy. The final
    canonical *bytes*, including [2:6] last-completed-tick stamps, are
    independently constructed from the M03 exact sparse eligibility trace.
    Model bytes/transactions are NOT observed DDR bus operations.
    """
    if policy not in ("direct", "lru", "activity_history"):
        raise ValueError("policy must be direct, lru or activity_history")
    if policy != "activity_history" and history_depth != 16:
        raise ValueError("history_depth only applies to activity_history policy")
    geometry.validate()
    if geometry.logical_neurons != len(workload.network.neurons):
        raise ValueError("policy geometry must match entire logical network")
    if geometry.bytes_per_neuron < 6:
        raise ValueError("M07 baseline requires >=6B rows for tick-watermark verification")

    net = workload.network
    inputs = workload.external_currents
    ticks = workload.spec.ticks
    dense = evaluate_dense(net, inputs, ticks=ticks)
    queued = evaluate_events(net, inputs, ticks=ticks)
    sparse = evaluate_exact_sparse(net, inputs, ticks=ticks)
    if dense != queued or dense != sparse.trace:
        raise AssertionError("M02/M03 neural oracle disagreement: refuse M07 traffic")

    image = new_canonical_neuron_image(net, geometry, owner="M07_EMULATED_ONLY")
    if policy == "activity_history":
        from .m07_activity_cache import ActivityHistoryCache
        cache = ActivityHistoryCache(
            image, owner="M07_EMULATED_ONLY", history_depth=history_depth)
    else:
        cache = (DirectFetchCache(image, owner="M07_EMULATED_ONLY") if policy == "direct"
                 else BlockCache(image, owner="M07_EMULATED_ONLY"))
    run = replay_with_paging(net, inputs, ticks=ticks, cache=cache)
    if (run.trace != dense or
            run.evaluated_ids_by_tick != sparse.evaluated_ids_by_tick or
            run.touched_ids_by_tick != sparse.destinations_by_tick or
            run.deliveries_by_tick != sparse.deliveries_by_tick or
            run.fanout_edges_by_tick != sparse.traversed_synapses_by_tick):
        raise AssertionError("M07 policy changes exact M02/M03 neural work")

    last_completed = [0] * len(net.neurons)
    for t, ids in enumerate(sparse.evaluated_ids_by_tick):
        for neuron in ids:
            last_completed[neuron] = t + 1
    expected = b"".join(
        v.to_bytes(2, "little", signed=True) +
        last_completed[i].to_bytes(4, "little") +
        bytes(geometry.bytes_per_neuron - 6)
        for i, v in enumerate(dense.voltage_rows[-1])
    )
    if image.snapshot(owner="M07_EMULATED_ONLY") != expected:
        raise AssertionError("M07 final canonical image/watermarks differ from M02/M03")
    if cache.poisoned or cache.dirty_pages:
        raise AssertionError("M07 successful session must be clean and unpoisoned")

    counts = asdict(cache.counters)
    evaluations = sum(len(row) for row in sparse.evaluated_ids_by_tick)
    if counts["accesses"] != 2 * evaluations:
        raise AssertionError("paged read/write pair not conserved")
    if counts["accesses"] != counts["hits"] + counts["misses"]:
        raise AssertionError("cache access hit/miss accounting mismatch")
    if counts["read_bytes"] != counts["misses"] * geometry.page_bytes:
        raise AssertionError("cold fill byte accounting mismatch")
    if (counts["read_transactions"] !=
            counts["misses"] * (
                (geometry.page_bytes + geometry.max_model_transfer_bytes - 1)
                // geometry.max_model_transfer_bytes)):
        raise AssertionError("cold fill transfer count mismatch")
    invalidations = cache.direct_invalidations if policy == "direct" else 0
    if policy == "direct" and (invalidations != evaluations
                               or cache.resident_pages
                               or counts["misses"] != evaluations):
        raise AssertionError("direct policy retained state between evaluations")

    return {
        "schema": "m07-cache-policy-baseline-v1",
        "scope": (SOURCE_SCOPE if policy != "activity_history"
                  else "M07_4_CAUSAL_ACTIVITY_CACHE_SOURCE_ONLY_NOT_HARDWARE"),
        "policy": policy,
        "geometry": asdict(geometry),
        "workload_spec": asdict(workload.spec),
        "role_workload_sha256": workload.canonical_role_sha256,
        "relabeled_input_sha256": workload.relabeled_input_sha256,
        "canonical_trace_sha256": canonicalize_trace(
            workload, run.trace)["canonical_trace_sha256"],
        "m02_dense_queued_m03_sparse_m06_paged_parity": True,
        "canonical_image_and_last_tick_parity": True,
        "evaluations": evaluations,
        "spikes": sum(map(len, run.trace.spike_rows)),
        "delivered_events": sum(run.deliveries_by_tick),
        "fanout_edge_visits": sum(run.fanout_edges_by_tick),
        "state_cache_counters": counts,
        "direct_invalidations_not_evictions": invalidations,
        "state_transfer_bytes": counts["read_bytes"] + counts["write_bytes"],
        "state_transfer_transactions": (
            counts["read_transactions"] + counts["write_transactions"]),
        "synapse_transfer_bytes": None,  # M06 paged replay keeps adjacency on-chip
        "outstanding_axi_requests": None,
        "b_before_ar_fence_cycles": None,
        "queue_stall_cycles": None,
        "simulated_service_cycles": None,
        "physical_ddr_bytes": None,
        "measurement_status": "PC_ONLY_MODEL_NOT_RTL_OR_PHYSICAL_MEASUREMENT",
        **({"activity_history_observer": cache.policy_observer()}
           if policy == "activity_history" else {}),
    }
