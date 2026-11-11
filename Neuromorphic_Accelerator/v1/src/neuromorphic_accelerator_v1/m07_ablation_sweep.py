"""M07.3 reproducible, fair HOST-ONLY residency/locality ablations.

Vary exactly one declared capacity axis or block-geometry axis at a time.
Within each seeded M03 role-isomorphic pair, activity count, signed events,
edges, neural computation and M02 traces remain invariant. This program
never schedules hardware or reads physical DDR: state bytes are M06 Python
page transfers; synapse bytes are the separate M03 analytical estimate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .m03_workloads import WorkloadSpec
from .m07_matched_controls import (
    FourWayPolicyConfig, MODES, POLICIES, build_matched_locality_report,
)

SCHEMA = "m07-residency-locality-ablation-v1"
STATUS = "HOST_ONLY_MODEL_NO_VENDOR_HLS_RTL_OR_PHYSICAL_DDR"
LOCALITIES = ("clustered", "dispersed")


@dataclass(frozen=True)
class AblationPlan:
    neuron_count: int = 128
    active_roles: int = 16
    fanout_per_active: int = 3
    external_events_per_tick: int = 4
    ticks: int = 8
    seeds: tuple[int, ...] = (17, 23)
    block_sizes_neurons: tuple[int, ...] = (2, 4, 8)
    resident_budgets_bytes: tuple[int, ...] = (128, 256, 512)
    state_bytes: int = 16
    onchip_state_capacity_bytes: int = 2048
    max_model_transfer_bytes: int = 256
    synapse_record_bytes: int = 8

    def validate(self) -> None:
        positive = (
            "neuron_count", "active_roles", "ticks", "state_bytes",
            "onchip_state_capacity_bytes", "max_model_transfer_bytes",
            "synapse_record_bytes",
        )
        nonnegative = ("fanout_per_active", "external_events_per_tick")
        for key in positive + nonnegative:
            value = getattr(self, key)
            if type(value) is not int or value < (0 if key in nonnegative else 1):
                raise ValueError(f"{key} requires an appropriate integer")
        if self.state_bytes < 6:
            raise ValueError("state record needs signed voltage + four-byte watermark")
        spec = self.workload_spec(0)
        spec.validate()
        if spec.state_bits != 16:
            raise ValueError("M06 paged replay currently admits signed16 only")
        for key in ("seeds", "block_sizes_neurons", "resident_budgets_bytes"):
            values = getattr(self, key)
            if (type(values) is not tuple or not values or
                    any(type(v) is not int or v < (0 if key == "seeds" else 1)
                        for v in values)):
                raise ValueError(f"{key} requires nonempty tuple of valid integers")
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"{key} must be unique and ascending")
        for block in self.block_sizes_neurons:
            if self.neuron_count % block:
                raise ValueError("every block size must evenly partition neurons")
            for budget in self.resident_budgets_bytes:
                page_bytes = block * self.state_bytes
                if budget % page_bytes:
                    raise ValueError("budget must be whole number of full blocks")
                if budget >= self.onchip_state_capacity_bytes:
                    raise ValueError("virtualized budget must be below on-chip limit")
                if budget >= self.neuron_count * self.state_bytes:
                    raise ValueError("ablation must retain a virtualized state image")
                if budget < page_bytes:
                    raise ValueError("budget cannot hold at least one block")
                cfg = self.policy_config(block, budget)
                cfg.validate(self.neuron_count)

    def workload_spec(self, seed: int) -> WorkloadSpec:
        return WorkloadSpec(
            neuron_count=self.neuron_count, active_roles=self.active_roles,
            fanout_per_active=self.fanout_per_active,
            external_events_per_tick=self.external_events_per_tick,
            ticks=self.ticks, seed=seed, state_bits=16,
        )

    def policy_config(self, block: int, budget: int) -> FourWayPolicyConfig:
        return FourWayPolicyConfig(
            state_bytes=self.state_bytes, block_neurons=block,
            resident_slots=budget // (block * self.state_bytes),
            onchip_state_capacity_bytes=self.onchip_state_capacity_bytes,
            max_model_transfer_bytes=self.max_model_transfer_bytes,
            synapse_record_bytes=self.synapse_record_bytes,
        )


def _metric(row: dict) -> dict:
    """Keep explicit provenance/units, including unavailable comparator rows."""
    if not row["available"]:
        return {
            "available": False,
            "reason": row["reason"],
            "functional_parity_verified": row["functional_parity_verified"],
            "state_transfer_bytes": None,
            "state_transfer_transactions": None,
            "synapse_analytical_bytes": None,
            "neuron_evaluations": None,
            "physical_ddr_bytes": None,
            "service_cycles": None,
        }
    reads, writes = row["state_read_bytes"], row["state_write_bytes"]
    counters = row["state_cache_counters_m06_method_level"]
    if counters is not None:
        if counters["read_bytes"] != reads or counters["write_bytes"] != writes:
            raise AssertionError("cache counter mismatch")
    return {
        "available": True,
        "functional_parity_verified": row["functional_parity_verified"],
        "neuron_evaluations": row["evaluated_neuron_steps"],
        "synapse_edge_visits": row["synapse_edge_visits"],
        "state_read_bytes": reads,
        "state_write_bytes": writes,
        "state_transfer_bytes": reads + writes,
        "state_transfer_transactions": row["state_transactions"],
        "state_cache_method_counters": counters,
        "synapse_analytical_bytes": row["synapse_read_bytes_m03_estimate"],
        "synapse_analytical_transactions": row["synapse_transactions_m03_estimate"],
        "combined_idealized_bytes": row["combined_idealized_bytes"],
        "physical_ddr_bytes": None,
        "service_cycles": None,
        "hardware_resources": None,
        "state_execution_source": row["state_execution_source"],
        "synapse_model_source": row["synapse_model_source"],
    }


def run_ablation(plan: AblationPlan) -> dict:
    """Require independent neural/mapping invariance BEFORE reporting ablations.

    Each budget is fixed in BYTES when block size varies, avoiding a false
    'same capacity' comparison based only on the number of resident slots.
    Cold caches, final dirty flushes and fixed full-block transfer units apply
    to every row; there is no measured time or physical transfer.
    """
    plan.validate()
    rows: list[dict] = []
    per_seed_roles: dict[int, tuple[str, str]] = {}
    per_seed_input_hashes: dict[int, dict[str, str]] = {}
    # Use a fixed seed/block/budget iteration order for stable JSON evidence.
    for seed in plan.seeds:
        for budget in plan.resident_budgets_bytes:
            for block in plan.block_sizes_neurons:
                cfg = plan.policy_config(block, budget)
                pair = build_matched_locality_report(plan.workload_spec(seed), cfg)
                layout_rows: dict[str, dict] = {}
                canonical_hash = pair["canonical_functional_trace_sha256"]
                role_hash = pair["canonical_role_workload_sha256"]
                if seed in per_seed_roles and per_seed_roles[seed] != (
                        role_hash, canonical_hash):
                    raise AssertionError("cache geometry changed neural role workload/trace")
                per_seed_roles[seed] = (role_hash, canonical_hash)
                config_ids: dict[str, str] = {}
                for locality in LOCALITIES:
                    result = pair["results_by_locality"][locality]
                    config_ids[locality] = result["relabeled_network_input_sha256"]
                    if (result["canonical_functional_trace_sha256"] != canonical_hash
                            or result["canonical_role_workload_sha256"] != role_hash):
                        raise AssertionError("relabeling changed neural result or input roles")
                    neural = result["neural_equivalence"]
                    # Independent work counters: exact sparse evaluations,
                    # spike count and synaptic fanout must match across locality.
                    work = {
                        "total_spikes": neural["total_spikes"],
                        "spiking_synapse_edge_visits": neural[
                            "total_edge_traversals_when_spiking"],
                        "event_neuron_evaluations": neural[
                            "exact_sparse_neuron_updates"],
                        "dense_neuron_evaluations": neural[
                            "dense_neuron_updates"],
                        "external_input_events": (
                            plan.external_events_per_tick * plan.ticks),
                    }
                    layout = {
                        "relabeled_network_input_sha256": config_ids[locality],
                        "work": work,
                        "unique_event_state_groups": neural[
                            "unique_state_groups_touched_over_run"],
                        "event_groups_by_tick": neural["touched_state_groups_by_tick"],
                        "controls": {
                            policy: {
                                mode: _metric(result["controls_by_policy"][policy][mode])
                                for mode in MODES
                            }
                            for policy in POLICIES
                        },
                    }
                    for mode in MODES:
                        d = layout["controls"]["direct"][mode]
                        l = layout["controls"]["lru"][mode]
                        if d["available"] != l["available"]:
                            raise AssertionError("policy changed resource comparator gate")
                        if d["available"]:
                            if (d["neuron_evaluations"] != l["neuron_evaluations"]
                                    or d["synapse_edge_visits"] != l["synapse_edge_visits"]
                                    or d["synapse_analytical_bytes"] != l[
                                        "synapse_analytical_bytes"]):
                                raise AssertionError("policy changed neural/synaptic work")
                    layout_rows[locality] = layout
                if (layout_rows["clustered"]["work"] !=
                        layout_rows["dispersed"]["work"]):
                    raise AssertionError("locality changed role-level neural work")
                if seed in per_seed_input_hashes:
                    if per_seed_input_hashes[seed] != config_ids:
                        raise AssertionError("block geometry unexpectedly changed input mapping")
                else:
                    per_seed_input_hashes[seed] = config_ids
                event_state = {}
                for locality in LOCALITIES:
                    controls = layout_rows[locality]["controls"]
                    event_state[locality] = {
                        policy: controls[policy]["event/ddr"]["state_transfer_bytes"]
                        for policy in POLICIES
                    }
                rows.append({
                    "seed": seed,
                    "resident_budget_bytes": budget,
                    "block_neurons": block,
                    "page_bytes": block * plan.state_bytes,
                    "resident_slots": budget // (block * plan.state_bytes),
                    "canonical_role_workload_sha256": role_hash,
                    "canonical_functional_trace_sha256": canonical_hash,
                    "localities": layout_rows,
                    "event_state_bytes_saved_by_lru": {
                        locality: event_state[locality]["direct"]
                        - event_state[locality]["lru"] for locality in LOCALITIES
                    },
                    "lru_event_state_locality_penalty_bytes": (
                        event_state["dispersed"]["lru"]
                        - event_state["clustered"]["lru"]),
                })

    return {
        "schema": SCHEMA,
        "scope": STATUS,
        "plan": asdict(plan),
        "num_parameter_combinations": len(rows),
        "num_policy_locality_four_way_rows": len(rows) * 2 * 2 * 4,
        "unique_workload_seeds": len(plan.seeds),
        "controlled_comparison": {
            "fixed_per_seed": ["role graph and signed weights/delays",
                               "all external events and their tick positions",
                               "M02 exact LIF and M03 sparse eligibility",
                               "state-record bytes and synapse record bytes",
                               "full-onchip comparator budget",
                               "transfer bound and cold-cache/final flush policy"],
            "swept": ["resident budget in BYTES", "neurons per block",
                      "resident slots derived from fixed byte budget",
                      "clustered/dispersed IDs", "direct/LRU policy"],
            "not_swept_yet": ["event batching", "additional placement heuristics",
                              "scheduler reordering", "queue depth"],
            "not_measured": ["DDR controller/PS cycles", "FPGA AXI transactions",
                             "pipeline/stall service time", "placed/routed FPGA area",
                             "power or energy"],
        },
        "performance_or_yana_equivalence_claim": False,
        "physical_hardware_measured": False,
        "rows": rows,
    }
