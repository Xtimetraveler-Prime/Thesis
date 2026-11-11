"""M07.4 controlled activity-history eviction pilot, not a neural reorderer.

The accepted M06 event scheduler already sorts each tick's eligible neuron
IDs, which also groups ascending block IDs. Re-sorting by page cannot
improve its within-tick block locality. Instead compare ONE bounded,
causal past-activity eviction candidate against direct/LRU on identical M03
neural fixtures and separately a non-neural adversarial hot-page trace.

The additional page-ID history and victim scans are explicitly uncosted
against the on-chip STATE budget. No speedup, area, queue/timing or physical
DDR claim is made. The candidate is experimental: negative wins are kept.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .m03_workloads import WorkloadSpec, build_workload
from .m06_block_residency import BlockCache, CanonicalImage, Geometry
from .m07_activity_cache import ActivityHistoryCache
from .m07_policy_baseline import run_policy

SCOPE = "M07_4_CAUSAL_ACTIVITY_HISTORY_SOURCE_ONLY_PILOT"
POLICIES = ("direct", "lru", "activity_history")


@dataclass(frozen=True)
class ActivityStudyPlan:
    neuron_count: int = 128
    active_roles: int = 16
    fanout_per_active: int = 3
    events_per_tick: int = 4
    ticks: int = 8
    seeds: tuple[int, ...] = (17, 23)
    geometries: tuple[tuple[int, int], ...] = (
        (4, 128), (4, 256), (8, 256), (8, 512),
    )  # (neurons per block, STATE bytes, not cache slots)
    history_depths: tuple[int, ...] = (4, 16, 32)
    state_bytes: int = 16
    declared_full_onchip_bytes: int = 2048
    max_model_transfer_bytes: int = 256

    def validate(self) -> None:
        for name in ("neuron_count", "active_roles", "ticks",
                     "state_bytes", "declared_full_onchip_bytes",
                     "max_model_transfer_bytes"):
            v = getattr(self, name)
            if type(v) is not int or v < 1:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("fanout_per_active", "events_per_tick"):
            v = getattr(self, name)
            if type(v) is not int or v < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.state_bytes < 6:
            raise ValueError("watermarked M06 record must have at least 6 bytes")
        WorkloadSpec(
            neuron_count=self.neuron_count, active_roles=self.active_roles,
            fanout_per_active=self.fanout_per_active,
            external_events_per_tick=self.events_per_tick, ticks=self.ticks,
            seed=0, state_bits=16,
        ).validate()
        for label, values, positive in (
            ("seeds", self.seeds, False),
            ("history_depths", self.history_depths, True),
        ):
            if (type(values) is not tuple or not values or
                tuple(sorted(set(values))) != values or
                any(type(v) is not int or v < (1 if positive else 0)
                    for v in values)):
                raise ValueError(label + " must be a unique ascending integer tuple")
        if any(depth > 4096 for depth in self.history_depths):
            raise ValueError("history depth exceeds bounded source policy limit")
        if (type(self.geometries) is not tuple or not self.geometries
                or tuple(sorted(set(self.geometries))) != self.geometries):
            raise ValueError("geometries must be unique ascending pairs")
        for item in self.geometries:
            if (type(item) is not tuple or len(item) != 2 or
                    any(type(v) is not int or v < 1 for v in item)):
                raise ValueError("invalid block/budget geometry pair")
            block, budget = item
            page_bytes = block * self.state_bytes
            if (self.neuron_count % block or budget % page_bytes
                    or budget < page_bytes or
                    budget >= self.declared_full_onchip_bytes or
                    budget >= self.neuron_count * self.state_bytes):
                raise ValueError("invalid/unequal resident byte capacity or block geometry")
            self.geometry(block, budget).validate()

    def geometry(self, block: int, budget: int) -> Geometry:
        page = block * self.state_bytes
        return Geometry(
            logical_neurons=self.neuron_count,
            bytes_per_neuron=self.state_bytes,
            neurons_per_block=block,
            resident_budget_bytes=budget,
            max_model_transfer_bytes=min(self.max_model_transfer_bytes, page),
        )


def _source_microtrace() -> dict:
    """Deterministic NON-NEURAL repeated-hot-page workload for policy sanity.

    This pattern is deliberately separate from M03 recurrent LIF experiments,
    not counted as an independent neural performance or accelerator result.
    """
    geom = Geometry(logical_neurons=12, bytes_per_neuron=16,
                    neurons_per_block=2, resident_budget_bytes=64,
                    max_model_transfer_bytes=32)
    sequence = (0, 0, 2, 4, 0, 6, 0, 8, 0, 10, 0)
    expected = bytearray(geom.image_bytes)
    results = {}
    for name in ("lru", "activity_history"):
        image = CanonicalImage(geom, emulated_owner="M07_MICROTRACE", initial=bytes(expected))
        cache = (BlockCache(image, owner="M07_MICROTRACE") if name == "lru" else
                 ActivityHistoryCache(image, owner="M07_MICROTRACE", history_depth=16))
        for i, neuron in enumerate(sequence):
            record = cache.read(neuron)
            value = (i+1).to_bytes(2, "little") + record[2:]
            cache.write(neuron, value)
        cache.flush()
        if cache.poisoned or cache.dirty_pages:
            raise AssertionError("microtrace cache failed to persist and close")
        if name == "lru":
            lru_snapshot = image.snapshot(owner="M07_MICROTRACE")
        elif image.snapshot(owner="M07_MICROTRACE") != lru_snapshot:
            raise AssertionError("history policy changes non-neural state bytes")
        results[name] = {
            "misses": cache.counters.misses,
            "model_state_bytes": cache.counters.read_bytes + cache.counters.write_bytes,
            "model_state_transactions": (
                cache.counters.read_transactions + cache.counters.write_transactions),
            "policy_observer": cache.policy_observer()
            if name == "activity_history" else None,
        }
    return {
        "type": "NON_NEURAL_DIRECTED_ACCESS_PATTERN",
        "neuron_ids": list(sequence),
        "pages": [geom.page_for_neuron(n) for n in sequence],
        "cache_slots": geom.slots,
        "history_depth": 16,
        "models": results,
        "identical_final_canonical_bytes": True,
        "real_neural_equivalence_claim": False,
    }


def run_activity_study(plan: ActivityStudyPlan) -> dict:
    """Same M02/M03 reference checked by unchanged M07.1 run_policy.

    Each geometry/policy pair starts fresh from identical canonical state.
    Any policy or locality mismatch in spikes, deliveries, fanout, neural
    evaluations, canonical role trace, or initial input identity aborts.
    No best-case selection is reported as a general policy victory.
    """
    plan.validate()
    pilot = _source_microtrace()
    if not (pilot["models"]["activity_history"]["misses"]
            < pilot["models"]["lru"]["misses"]):
        raise AssertionError("directed hot-page positive control did not distinguish policy")

    rows = []
    seed_hashes = {}
    for seed in plan.seeds:
        for block, budget in plan.geometries:
            geom = plan.geometry(block, budget)
            layouts = {}
            for locality in ("clustered", "dispersed"):
                spec = WorkloadSpec(
                    neuron_count=plan.neuron_count,
                    active_roles=plan.active_roles,
                    fanout_per_active=plan.fanout_per_active,
                    external_events_per_tick=plan.events_per_tick,
                    ticks=plan.ticks, seed=seed, locality=locality,
                    state_bits=16)
                work = build_workload(spec)
                base = {
                    policy: run_policy(work, geom, policy=policy)
                    for policy in ("direct", "lru")
                }
                histories = {
                    depth: run_policy(
                        work, geom, policy="activity_history",
                        history_depth=depth)
                    for depth in plan.history_depths
                }
                witness = base["lru"]
                for result in (*base.values(), *histories.values()):
                    for field in (
                        "role_workload_sha256", "relabeled_input_sha256",
                        "canonical_trace_sha256", "evaluations", "spikes",
                        "delivered_events", "fanout_edge_visits",
                    ):
                        if result[field] != witness[field]:
                            raise AssertionError("policy changed matched neural work: "+field)
                    if (not result["canonical_image_and_last_tick_parity"]
                            or not result["m02_dense_queued_m03_sparse_m06_paged_parity"]):
                        raise AssertionError("failed independent neural/canonical parity")
                    counts = result["state_cache_counters"]
                    if counts["accesses"] != 2 * result["evaluations"]:
                        raise AssertionError("per-evaluation cache accounting not conserved")
                ids = (witness["role_workload_sha256"],
                       witness["canonical_trace_sha256"])
                if seed in seed_hashes:
                    if seed_hashes[seed]["role_and_trace"] != ids:
                        raise AssertionError("geometry/locality changed canonical neural work")
                    if seed_hashes[seed][locality] != witness["relabeled_input_sha256"]:
                        raise AssertionError("cache experiment changed original inputs")
                else:
                    seed_hashes[seed] = {"role_and_trace": ids}
                seed_hashes[seed][locality] = witness["relabeled_input_sha256"]
                lru_bytes = witness["state_transfer_bytes"]
                layouts[locality] = {
                    "role_workload_sha256": ids[0],
                    "canonical_trace_sha256": ids[1],
                    "relabeled_input_sha256": witness["relabeled_input_sha256"],
                    "neural_work": {
                        key: witness[key] for key in (
                            "evaluations", "spikes", "delivered_events",
                            "fanout_edge_visits")
                    },
                    "direct": {
                        "misses": base["direct"]["state_cache_counters"]["misses"],
                        "state_bytes": base["direct"]["state_transfer_bytes"],
                        "state_transactions": base["direct"]["state_transfer_transactions"],
                    },
                    "lru": {
                        "misses": witness["state_cache_counters"]["misses"],
                        "state_bytes": lru_bytes,
                        "state_transactions": witness["state_transfer_transactions"],
                    },
                    "history": {
                        str(depth): {
                            "misses": result["state_cache_counters"]["misses"],
                            "state_bytes": result["state_transfer_bytes"],
                            "state_transactions": result["state_transfer_transactions"],
                            "state_bytes_saved_vs_lru": lru_bytes - result["state_transfer_bytes"],
                            "state_transactions_saved_vs_lru": (
                                witness["state_transfer_transactions"]
                                - result["state_transfer_transactions"]),
                            "policy_observer": result["activity_history_observer"],
                        } for depth, result in histories.items()
                    },
                }
            if (layouts["clustered"]["neural_work"] !=
                    layouts["dispersed"]["neural_work"]):
                raise AssertionError("locality changed role-normalized computation")
            rows.append({
                "seed": seed,
                "block_neurons": block,
                "resident_budget_bytes": budget,
                "page_bytes": geom.page_bytes,
                "resident_slots": geom.slots,
                "localities": layouts,
            })
    deltas = [
        item["state_bytes_saved_vs_lru"]
        for row in rows for loc in row["localities"].values()
        for item in loc["history"].values()
    ]
    return {
        "schema": "m07-activity-history-pilot-v1",
        "scope": SCOPE,
        "plan": asdict(plan),
        "geometry_seed_cases": len(rows),
        "policy_history_comparisons": len(deltas),
        "witnessed_outcomes": {
            "history_lower_model_bytes": sum(delta > 0 for delta in deltas),
            "history_equal_model_bytes": sum(delta == 0 for delta in deltas),
            "history_higher_model_bytes": sum(delta < 0 for delta in deltas),
            "net_model_bytes_saved_vs_lru_across_cases": sum(deltas),
            "warning": (
                "aggregate uses synthetic, nonindependent configurations and "
                "IS NOT hardware speedup, energy, area or a confidence interval"),
        },
        "microtrace": pilot,
        "rows": rows,
        "neuron_execution_order": "unchanged M06 ascending neuron ID per logical tick",
        "activity_observation": "bounded history of completed read/write evaluations only",
        "synapse_traffic": "M03 separate analytical estimate NOT in this state-only pilot",
        "extra_history_and_scan_metadata_fits_declared_state_budget": False,
        "equal_total_fpga_resource_comparison": False,
        "lookahead": False,
        "reordered_deliveries": False,
        "service_cycles": None,
        "b_before_ar_cycles": None,
        "queue_stalls": None,
        "physical_ddr_bytes": None,
        "hardware_latency_ns": None,
        "actual_yana_implementation": False,
        "measurement_status": "PC_ONLY_MODEL_NO_VITIS_RTL_OR_BOARD",
    }
