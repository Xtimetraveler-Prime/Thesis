"""M07.2 four-way matched PC MODEL with M06 cache policies.

Four logical controls for each immutable M03 workload:
  timestep/onchip, event/onchip, timestep/ddr, event/ddr.

The timestep DDR state stream is an *oracle-guided memory replay*: each
neuron's previous voltage and tick watermark is checked before writing the
independently M02-verified next voltage. It estimates exact M06 bytearray
block residency, but it does NOT run an independent timestep LIF kernel.
The event DDR path DOES execute the accepted M06 paged neural recurrence
through the selected policy and checks M02/M03 neural and canonical parity.

DDR-style synapse traffic is the accepted M03 *analytical* sequential edge
estimate, not real traffic issued by the M06 replay (which uses on-chip
adjacency). These separate models are composed only for transparent
four-way accounting, NEVER presented as integrated hardware or timing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .m02_dense_reference import evaluate_dense
from .m03_traffic import ComparisonConfig, compare_workload
from .m03_workloads import Workload, WorkloadSpec, build_workload, canonicalize_trace
from .m06_block_residency import BlockCache, Geometry, ResidencyError
from .m06_paged_replay import check_bounded_network, new_canonical_neuron_image
from .m07_policy_baseline import DirectFetchCache, run_policy

SCOPE = "M07_2_PC_ONLY_MATCHED_LOGICAL_CONTROLS_NOT_HARDWARE"
POLICIES = ("direct", "lru")
MODES = ("timestep/onchip", "event/onchip", "timestep/ddr", "event/ddr")


@dataclass(frozen=True)
class FourWayPolicyConfig:
    state_bytes: int = 16
    block_neurons: int = 8
    resident_slots: int = 4
    onchip_state_capacity_bytes: int = 2048
    max_model_transfer_bytes: int = 256
    synapse_record_bytes: int = 8

    def validate(self, neuron_count: int) -> tuple[Geometry, ComparisonConfig]:
        for name in ("state_bytes", "block_neurons", "resident_slots",
                     "onchip_state_capacity_bytes", "max_model_transfer_bytes",
                     "synapse_record_bytes"):
            v = getattr(self, name)
            if type(v) is not int or v < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.state_bytes < 6:
            raise ValueError("M07.2 requires >=6B state row for exact watermark checks")
        # No hidden budget increase: slots * page bytes must fit the declared
        # logical on-chip allowance for virtualized cache, which is *smaller*
        # than the full-resident comparator allowance (M03 assumption).
        page_bytes = self.block_neurons * self.state_bytes
        budget = self.resident_slots * page_bytes
        if budget >= self.onchip_state_capacity_bytes:
            raise ValueError("virtualized cache must be smaller than full-state capacity")
        g = Geometry(
            logical_neurons=neuron_count,
            bytes_per_neuron=self.state_bytes,
            neurons_per_block=self.block_neurons,
            resident_budget_bytes=budget,
            # A canonical page transfer cannot exceed the page width;
            # M03's upper bound still applies separately to synapse edges.
            max_model_transfer_bytes=min(self.max_model_transfer_bytes, page_bytes),
        )
        g.validate()
        m03 = ComparisonConfig(
            state_bytes=self.state_bytes,
            onchip_state_capacity_bytes=self.onchip_state_capacity_bytes,
            ddr_state_cache_bytes=budget,
            block_neurons=self.block_neurons,
            max_transfer_bytes=self.max_model_transfer_bytes,
            synapse_record_bytes=self.synapse_record_bytes,
        )
        m03.validate(neuron_count)
        return g, m03


def _check_accounting(counts: dict, geom: Geometry, evaluations: int) -> None:
    if counts["accesses"] != 2 * evaluations:
        raise AssertionError("two cache calls required per neuron evaluation")
    if counts["hits"] + counts["misses"] != counts["accesses"]:
        raise AssertionError("cache hits/misses do not conserve accesses")
    if counts["read_bytes"] != counts["misses"] * geom.page_bytes:
        raise AssertionError("state page read bytes do not conserve fills")
    chunk_count = ((geom.page_bytes + geom.max_model_transfer_bytes - 1)
                   // geom.max_model_transfer_bytes)
    if counts["read_transactions"] != counts["misses"] * chunk_count:
        raise AssertionError("model read transactions do not conserve fills")
    if (counts["write_bytes"] % geom.page_bytes != 0 or
            counts["write_transactions"] != (
                counts["write_bytes"] // geom.page_bytes) * chunk_count):
        raise AssertionError("model write transactions do not conserve dirty flushes")


def replay_timestep_oracle_state(workload: Workload, geom: Geometry, *,
                                 policy: str) -> dict:
    """Trace-accurate page/dirty memory traffic for every neuron every tick.

    M02 dense voltage is the independent *expected next state*. Prior bytes
    are checked against the previous oracle tick before every read/write pair
    and persisted against the final expected canonical image. No neural
    arithmetic is claimed to be independently performed by this replay.
    """
    if policy not in POLICIES:
        raise ValueError("unknown M07 policy")
    if geom.logical_neurons != len(workload.network.neurons) or geom.bytes_per_neuron < 6:
        raise ValueError("incompatible full M07 timestep state geometry")
    geom.validate()
    net = workload.network
    ticks = workload.spec.ticks
    check_bounded_network(net, workload.external_currents, ticks)
    dense = evaluate_dense(net, workload.external_currents, ticks=ticks)
    image = new_canonical_neuron_image(net, geom, owner="M07_2_SOFTWARE_ONLY")
    cache = (DirectFetchCache(image, owner="M07_2_SOFTWARE_ONLY")
             if policy == "direct"
             else BlockCache(image, owner="M07_2_SOFTWARE_ONLY"))
    try:
        for t in range(ticks):
            for i, neuron in enumerate(net.neurons):
                data = cache.read(i)
                before = (neuron.initial_v if t == 0
                          else dense.voltage_rows[t-1][i])
                prev = int.from_bytes(data[:2], "little", signed=True)
                stamp = int.from_bytes(data[2:6], "little")
                if prev != before or stamp != t:
                    raise ResidencyError("timestep previous voltage/tick witness mismatch")
                next_v = dense.voltage_rows[t][i]
                cache.write(i, next_v.to_bytes(2, "little", signed=True)
                            + (t+1).to_bytes(4, "little") + data[6:])
        cache.flush()
        expected = b"".join(
            dense.voltage_rows[-1][i].to_bytes(2, "little", signed=True)
            + ticks.to_bytes(4, "little")
            + bytes(geom.bytes_per_neuron - 6) for i in range(len(net.neurons))
        )
        if image.snapshot(owner="M07_2_SOFTWARE_ONLY") != expected:
            raise ResidencyError("timestep canonical image differs from neural oracle")
        if cache.dirty_pages or cache.poisoned:
            raise ResidencyError("timestep successful run must have clean state")
    except (ValueError, ResidencyError, PermissionError, AssertionError):
        cache._poisoned = True  # fail closed: never interpret partial traffic as success
        raise
    counts = asdict(cache.counters)
    evaluations = len(net.neurons) * ticks
    _check_accounting(counts, geom, evaluations)
    if policy == "direct" and (counts["misses"] != evaluations or
                               cache.direct_invalidations != evaluations):
        raise AssertionError("direct policy unexpectedly retained timestep state")
    return {
        "evaluation_mode": "oracle_guided_timestep_state_memory_replay",
        "state_evaluations": evaluations,
        "cache_counters": counts,
        "direct_invalidations_not_capacity_evictions": (
            cache.direct_invalidations if policy == "direct" else 0),
        "state_read_bytes": counts["read_bytes"],
        "state_write_bytes": counts["write_bytes"],
        "state_transactions": counts["read_transactions"] + counts["write_transactions"],
        "canonical_final_oracle_parity": True,
        "actual_lif_computed_by_cache": False,
    }


def compare_four_way(workload: Workload, cfg: FourWayPolicyConfig) -> dict:
    """Compare same M03 role-network and temporal input under both policies.

    The independent M03 four-way report establishes neural parity BEFORE
    policy traffic is modeled. M07 overwrites no M03 results or M02 golden
    data. No on-chip result is fabricated when its full state cannot fit.
    """
    geom, m03cfg = cfg.validate(len(workload.network.neurons))
    check_bounded_network(workload.network, workload.external_currents,
                          workload.spec.ticks)
    m03 = compare_workload(workload, m03cfg)
    oracle = evaluate_dense(workload.network, workload.external_currents,
                            ticks=workload.spec.ticks)
    canonical = canonicalize_trace(workload, oracle)["canonical_trace_sha256"]
    if canonical != m03["canonical_functional_trace_sha256"]:
        raise AssertionError("M03 independent canonical trace witness changed")

    rows: dict[str, dict] = {}
    for policy in POLICIES:
        controls: dict[str, dict] = {}
        event_model = run_policy(workload, geom, policy=policy)
        if (event_model["canonical_trace_sha256"] != canonical
                or event_model["role_workload_sha256"] != workload.canonical_role_sha256):
            raise AssertionError("M07 paged event execution changed M02/M03 semantics")
        for mode in MODES:
            base = m03["four_way_models"][mode]
            if not base["available"]:
                controls[mode] = {
                    "available": False,
                    "reason": base["reason"],
                    "required_onchip_state_bytes": base["required_onchip_state_bytes"],
                    "declared_onchip_state_capacity_bytes": (
                        base["declared_onchip_state_capacity_bytes"]),
                    "functional_parity_verified": True,
                    "model_timing_cycles": None,
                    "physical_ddr_bytes": None,
                }
                continue
            is_ddr = mode.endswith("/ddr")
            is_event = mode.startswith("event/")
            # M06 paged execution actually evaluates event-driven neurons.
            # Dense timestep is solely a separately checked memory-state
            # trace replay driven by M02 independent dense voltages.
            state = None
            if is_ddr:
                state = (event_model if is_event else
                         replay_timestep_oracle_state(workload, geom, policy=policy))
                if is_event:
                    evaluations = state["evaluations"]
                    state_read = state["state_cache_counters"]["read_bytes"]
                    state_write = state["state_cache_counters"]["write_bytes"]
                    state_tx = state["state_transfer_transactions"]
                    counts = state["state_cache_counters"]
                    invalidations = state["direct_invalidations_not_evictions"]
                else:
                    evaluations = state["state_evaluations"]
                    state_read = state["state_read_bytes"]
                    state_write = state["state_write_bytes"]
                    state_tx = state["state_transactions"]
                    counts = state["cache_counters"]
                    invalidations = state["direct_invalidations_not_capacity_evictions"]
                _check_accounting(counts, geom, evaluations)
                if evaluations != base["evaluated_neuron_steps"]:
                    raise AssertionError("M03 matched neuron work changed")
            else:
                evaluations = base["evaluated_neuron_steps"]
                state_read = state_write = state_tx = 0
                counts = None
                invalidations = 0
            # M03 analytical sequential edge array, never a real transfer
            # invoked by the M06 pager; 0 when adjacency wholly on chip.
            syn_read = base["synapse_read_bytes"]
            syn_tx = base["synapse_transactions"]
            controls[mode] = {
                "available": True,
                "functional_parity_verified": True,
                "canonical_functional_trace_sha256": canonical,
                "evaluated_neuron_steps": evaluations,
                "synapse_edge_visits": base["synapse_edge_visits"],
                "state_read_bytes": state_read,
                "state_write_bytes": state_write,
                "state_transactions": state_tx,
                "synapse_read_bytes_m03_estimate": syn_read,
                "synapse_transactions_m03_estimate": syn_tx,
                "combined_idealized_bytes": state_read + state_write + syn_read,
                "combined_idealized_transactions": state_tx + syn_tx,
                "state_cache_counters_m06_method_level": counts,
                "direct_invalidations_not_capacity_evictions": invalidations,
                "state_execution_source": (
                    "M06_PAGED_EXACT_LIF" if is_ddr and is_event else
                    "M02_ORACLE_GUIDED_STATE_MOVEMENT" if is_ddr else
                    "M03_LOGICAL_ONCHIP_CONTROL"),
                "synapse_model_source": (
                    "M03_SEQUENTIAL_DDR_ESTIMATE_NOT_ISSUED_BY_PAGER"
                    if is_ddr else "IDEAL_ONCHIP_NO_DDR"),
                "physical_ddr_bytes": None,
                "outstanding_axi_requests": None,
                "b_before_ar_fence_cycles": None,
                "queue_stall_cycles": None,
                "model_timing_cycles": None,
                "measured_latency_ns": None,
                "hardware_resource_utilization": None,
            }
        rows[policy] = controls

    for mode in MODES:
        d, l = rows["direct"][mode], rows["lru"][mode]
        if d["available"] != l["available"]:
            raise AssertionError("cache policy changed on-chip comparator availability")
        if d["available"]:
            for field in ("canonical_functional_trace_sha256", "evaluated_neuron_steps",
                          "synapse_edge_visits", "synapse_read_bytes_m03_estimate",
                          "synapse_transactions_m03_estimate"):
                if d[field] != l[field]:
                    raise AssertionError("policy alters matched work or synapse estimate")
    return {
        "schema": "m07-four-way-policy-matched-v1",
        "scope": SCOPE,
        "workload_spec": asdict(workload.spec),
        "canonical_role_workload_sha256": workload.canonical_role_sha256,
        "relabeled_network_input_sha256": workload.relabeled_input_sha256,
        "canonical_functional_trace_sha256": canonical,
        "geometry": asdict(geom),
        "full_comparator_state_bytes": len(workload.network.neurons) * cfg.state_bytes,
        "declared_full_onchip_state_capacity_bytes": cfg.onchip_state_capacity_bytes,
        "ddr_state_resident_budget_bytes": geom.resident_budget_bytes,
        "fairness_boundary": (
            "same network/numerics/inputs per policy; role-isomorphic neuron IDs "
            "across locality; virtualized state budget SMALLER than full onchip; "
            "NOT equal FPGA resource or clock control"),
        "neural_equivalence": m03["neural_equivalence"],
        "m03_original_analytical_state_policy": (
            "M01 block LRU first-touch-write approximation; intentionally not "
            "substituted for M06 read/write-level cache counters"),
        "controls_by_policy": rows,
        "measurement_status": "PC_MODELS_ONLY_NOT_VITIS_XSIM_OR_PHYSICAL_DDR",
        "vendor_hls_amd_executed": False,
        "physical_board_accessed": False,
    }


def build_matched_locality_report(spec: WorkloadSpec,
                                  cfg: FourWayPolicyConfig) -> dict:
    """Create one reproducible pair; require same ROLE work, not neuron IDs."""
    results = {
        locality: compare_four_way(build_workload(
            replace(spec, locality=locality)), cfg)
        for locality in ("clustered", "dispersed")
    }
    a, b = results["clustered"], results["dispersed"]
    for key in ("canonical_role_workload_sha256", "canonical_functional_trace_sha256"):
        if a[key] != b[key]:
            raise AssertionError("M03 locality permutations changed logical LIF work")
    for mode in MODES:
        for policy in POLICIES:
            c = a["controls_by_policy"][policy][mode]
            d = b["controls_by_policy"][policy][mode]
            if c["available"] != d["available"]:
                raise AssertionError("locality changed resource capacity gate")
            if c["available"]:
                for field in ("evaluated_neuron_steps", "synapse_edge_visits",
                              "synapse_read_bytes_m03_estimate",
                              "synapse_transactions_m03_estimate"):
                    if c[field] != d[field]:
                        raise AssertionError("locality changes neural or synaptic work")
    return {
        "schema": "m07-four-way-locality-pair-v1",
        "scope": SCOPE,
        "comparison_config": asdict(cfg),
        "canonical_role_workload_sha256": a["canonical_role_workload_sha256"],
        "canonical_functional_trace_sha256": a["canonical_functional_trace_sha256"],
        "matched_neural_work_confirmed": True,
        "model_only": True,
        "results_by_locality": results,
        "physical_hardware_measured": False,
    }
