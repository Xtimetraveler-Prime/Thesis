"""M03 matched workload/virtualization controls — source-level traffic model.

Four logical *PC MODELS*, not implemented equivalent FPGA configurations:
  timestep/onchip, event/onchip, timestep/DDR, event/DDR.
Neural functionality is independently checked via M02 dense, M02 queued,
and an M03 sparse-but-exact zero/bias-safe evaluator.

State traffic uses the M01 LRU accounting with SAME neuron-count/record size
and residency policy, but DIFFERENT valid state-access traces:
  timestep: every neuron every tick;
  event: only a neuron with nonzero previous state, nonzero bias, or arrived
         synaptic/external current (provably identical per accepted M02 rev1).
Synapse traffic uses an illustrative external CSR-like sequential edge storage,
NOT hardware AXI/DMA pointer timing, metadata or burst alignment.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .m01_residency import StudyConfig, simulate
from .m02_dense_reference import evaluate_dense
from .m02_event_reference import evaluate_events
from .m03_sparse_reference import evaluate_exact_sparse
from .m03_workloads import Workload, canonicalize_trace, sha256_json


@dataclass(frozen=True)
class ComparisonConfig:
    state_bytes: int = 16
    onchip_state_capacity_bytes: int = 2048
    ddr_state_cache_bytes: int = 512
    block_neurons: int = 8
    max_transfer_bytes: int = 256
    synapse_record_bytes: int = 8
    residency_policy: str = "block"
    hybrid_pinned_neurons: int = 0

    def validate(self, neuron_count: int) -> StudyConfig:
        for name in ("state_bytes", "onchip_state_capacity_bytes",
                     "ddr_state_cache_bytes", "block_neurons",
                     "max_transfer_bytes", "synapse_record_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.residency_policy not in ("block", "individual", "hybrid"):
            raise ValueError("unsupported residency policy")
        if type(self.hybrid_pinned_neurons) is not int or self.hybrid_pinned_neurons < 0:
            raise ValueError("hybrid_pinned_neurons must be nonnegative int")
        if self.residency_policy != "hybrid" and self.hybrid_pinned_neurons:
            raise ValueError("pins must be zero unless residency_policy == hybrid")
        if self.ddr_state_cache_bytes >= self.onchip_state_capacity_bytes:
            # The DDR control is deliberately capacity-limited so it actually
            # tests virtualization vs the full on-chip resident alternative.
            raise ValueError("DDR state cache must be smaller than full onchip budget")
        cfg = StudyConfig(
            neuron_count=neuron_count,
            state_bytes=self.state_bytes,
            resident_budget_bytes=self.ddr_state_cache_bytes,
            block_neurons=self.block_neurons,
            hybrid_pinned_neurons=self.hybrid_pinned_neurons,
            max_transfer_bytes=self.max_transfer_bytes,
        )
        cfg.validate()
        return cfg


def _transactions(total_bytes: int, max_bytes: int) -> int:
    return 0 if total_bytes == 0 else (total_bytes + max_bytes - 1) // max_bytes


def compare_workload(workload: Workload, config: ComparisonConfig) -> dict:
    """Require exact independent neural agreement before returning traffic."""
    config.validate(workload.spec.neuron_count)
    net = workload.network
    ticks, neuron_count = workload.spec.ticks, len(net.neurons)
    dense = evaluate_dense(net, workload.external_currents, ticks=ticks)
    event_queue = evaluate_events(net, workload.external_currents, ticks=ticks)
    sparse = evaluate_exact_sparse(net, workload.external_currents, ticks=ticks)
    if dense != event_queue or dense != sparse.trace:
        raise AssertionError("reference disagreement: refuse memory comparison")

    canonical = canonicalize_trace(workload, dense)
    dense_accesses = tuple(neuron for _t in range(ticks)
                           for neuron in range(neuron_count))
    sparse_accesses = tuple(neuron for row in sparse.evaluated_ids_by_tick
                            for neuron in row)
    # Safe idle skip requires the accepted first LIF contract. Do not label
    # this as the schedule actually implemented by the FPGA (none exists).
    if len(dense_accesses) != neuron_count * ticks:
        raise AssertionError("dense access conservation")
    if not set(sparse_accesses).issubset(set(range(neuron_count))):
        raise AssertionError("sparse trace out of network bounds")

    # Data bytes for a simplistic contiguous edge array, separate from state.
    # For dense timestep, scan every edge every tick (one sequential read/tick).
    # For event path, read contiguous outgoing fanout for each emitting pre.
    # No CSR offset-table/AXI setup/tags/PS overhead included.
    edge_size = config.synapse_record_bytes
    max_transfer = config.max_transfer_bytes
    per_tick_dense_edge_bytes = len(net.synapses) * edge_size
    timestep_synapse_reads = per_tick_dense_edge_bytes * ticks
    timestep_synapse_transactions = (
        _transactions(per_tick_dense_edge_bytes, max_transfer) * ticks
    )
    event_synapse_reads = 0
    event_synapse_transactions = 0
    active_synapse_traversals = 0
    firing_count = 0
    for row in sparse.fanout_per_firing_by_tick:
        for _pre, fanout in row:
            firing_count += 1
            active_synapse_traversals += fanout
            row_bytes = fanout * edge_size
            event_synapse_reads += row_bytes
            event_synapse_transactions += _transactions(row_bytes, max_transfer)

    potential_full_onchip_bytes = neuron_count * config.state_bytes
    resident_fits = (
        potential_full_onchip_bytes <= config.onchip_state_capacity_bytes
    )
    report: dict[str, dict] = {}
    study_cfg = config.validate(neuron_count)

    for execution, accesses, evaluated_count, synapse_work, synapse_bytes, syn_tx in (
        ("timestep", dense_accesses, len(dense_accesses),
         len(net.synapses) * ticks, timestep_synapse_reads,
         timestep_synapse_transactions),
        ("event", sparse_accesses, len(sparse_accesses),
         active_synapse_traversals, event_synapse_reads,
         event_synapse_transactions),
    ):
        for memory in ("onchip", "ddr"):
            name = f"{execution}/{memory}"
            if memory == "onchip" and not resident_fits:
                report[name] = {
                    "available": False,
                    "reason": "full neuron state exceeds declared onchip capacity; "
                              "do not extrapolate a resident control",
                    "required_onchip_state_bytes": potential_full_onchip_bytes,
                    "declared_onchip_state_capacity_bytes": config.onchip_state_capacity_bytes,
                    "functional_parity_verified": True,
                }
                continue

            state = None if memory == "onchip" else simulate(
                study_cfg, accesses, approach=config.residency_policy
            ).as_dict()
            sb_read = 0 if state is None else state["read_bytes"]
            sb_write = 0 if state is None else state["write_bytes"]
            state_tx = 0 if state is None else state["total_transactions"]
            report[name] = {
                "available": True,
                "functional_parity_verified": True,
                "evaluated_neuron_steps": evaluated_count,
                "synapse_edge_visits": synapse_work,
                "state_read_bytes": sb_read,
                "state_write_bytes": sb_write,
                "state_transactions": state_tx,
                "synapse_read_bytes": 0 if memory == "onchip" else synapse_bytes,
                "synapse_transactions": 0 if memory == "onchip" else syn_tx,
                "total_modeled_bytes": (
                    sb_read + sb_write
                    + (synapse_bytes if memory == "ddr" else 0)
                ),
                "total_modeled_transactions": (
                    state_tx + (syn_tx if memory == "ddr" else 0)
                ),
                "state_policy_detail": state,
            }

    # Synaptic *functional* event count is the same in all four configurations
    # and is deliberately not confused with the dense edge tests.
    return {
        "schema": "m03-matched-lif-ddr-traffic-v1",
        "status": "PC_ONLY_SYNTHETIC_TRAFFIC_NO_HW_SPEED_OR_ENERGY",
        "accepted_neural_contract": "M02 integer LIF reference revision 1",
        "workload_spec": asdict(workload.spec),
        "comparison_config": asdict(config),
        "canonical_role_workload_sha256": workload.canonical_role_sha256,
        "relabeled_network_input_sha256": workload.relabeled_input_sha256,
        "canonical_functional_trace_sha256": canonical["canonical_trace_sha256"],
        "functional_trace_by_roles": canonical,
        "neural_equivalence": {
            "dense_vs_M02_queued": True,
            "dense_vs_M03_sparse_exact": True,
            "total_spikes": firing_count,
            "dense_neuron_updates": len(dense_accesses),
            "exact_sparse_neuron_updates": len(sparse_accesses),
            "total_edge_traversals_when_spiking": active_synapse_traversals,
            "synapse_count": len(net.synapses),
            "spike_events_by_tick": [list(row) for row in sparse.trace.spike_rows],
            "sparse_state_ids_by_tick": [list(row) for row in sparse.evaluated_ids_by_tick],
            "event_destinations_by_tick": [list(row) for row in sparse.destinations_by_tick],
            "visited_synapses_by_tick": list(sparse.traversed_synapses_by_tick),
            "delivered_events_by_tick": list(sparse.deliveries_by_tick),
            "pending_future_deliveries_by_tick": list(sparse.pending_future_deliveries_by_tick),
            "peak_pending_deliveries_pc_model": sparse.peak_pending_deliveries,
            "touched_state_groups_by_tick": [
                len({neuron // config.block_neurons for neuron in group})
                for group in sparse.evaluated_ids_by_tick
            ],
            "unique_state_groups_touched_over_run": len({
                neuron // config.block_neurons
                for neuron in sparse_accesses
            }),
            "unique_state_neurons_touched_over_run": len(set(sparse_accesses)),
        },
        "control_design": {
            "neuron_step_comparison": "dense N*T vs exact M02 zero-state idle elimination",
            "onchip_test_possible": resident_fits,
            "onchip_state_bytes_required": potential_full_onchip_bytes,
            "onchip_capacity_bytes": config.onchip_state_capacity_bytes,
            "ddr_state_cache_capacity_bytes": config.ddr_state_cache_bytes,
            "external_adjacency": "idealized precontiguous fanout records; "
                                  "CSR index/table/AXI setup not counted",
            "caveat": "DDR controls have a smaller state cache than resident controls; "
                      "these are logical PC models, not resource-matched FPGA builds.",
            "excluded": [
                "DDR actual burst latency/bank conflicts/pointer lookup",
                "cache tag RAM, controller LUT/FF, DMA descriptor and PS work",
                "actual FPGA queue occupancy, FIFO backpressure and arbitration stalls",
                "compute/transfer overlap",
                "real KV260 throughput or timing", "energy and power",
                "SNN classification accuracy and unseen application generalization",
            ],
        },
        "four_way_models": report,
    }
