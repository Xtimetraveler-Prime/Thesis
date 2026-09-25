"""Matched native-sparse MNIST experiments for the pinned Catalyst N1 reference.

Two Catalyst CPU views are retained deliberately:

* ``graph-preserving`` materializes 784 source neurons, ten classifier neurons,
  and the exact 4,086 effective-weight edges in Catalyst's generic SDK;
* ``delivered-drive`` collapses each frozen axon row to the exact ten fan-in
  current sums and injects those sums directly into ten output neurons.

The graph-preserving experiment is the primary matched-graph result.  The
``delivered-drive`` experiment is a CPU-reference control that isolates output
neuron dynamics.  It deliberately permits signed-32-bit fan-in sums because the
pinned Catalyst CPU simulator stores external current and soma accumulation in
``numpy.int32``.  This is broader than the signed-int16 direct-stimulus subset
frozen for M13.3 and must not be presented as a physical host-transport claim.

Source spikes in graph-preserving mode are delivered one Catalyst native tick
later.  After that declared pipeline normalization, the two Catalyst views must
match exactly in per-tick output voltage and spikes; otherwise the adapter fails
closed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from .brian2loihi_matched import MatchedImageInput
from .matched_reference import (
    FrozenMatchedWorkload,
    build_comparison_scenario,
    decode_spike_counts,
    spike_counts_from_trace,
)


RESULT_SCHEMA = "neuromorphic-twin-mnist-12-catalyst-case-v1"
SUITE_SCHEMA = "neuromorphic-twin-mnist-12-catalyst-suite-v1"
CATALYST_PIN = "1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
GENERIC_CPU_NEURONS_PER_CORE = 1024
K26_CONFIGURED_NEURONS = 512
K26_POOL_DEPTH_PER_CORE = 4096
INT16_MIN = -(1 << 15)
INT16_MAX = (1 << 15) - 1
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1


def catalyst_feasibility_audit(workload: FrozenMatchedWorkload) -> dict[str, object]:
    graph_neurons = workload.input_axons + workload.output_neurons
    graph_pairs = {(int(s.axon_id), int(s.target_neuron)) for s in workload.synapses}
    if len(graph_pairs) != len(workload.synapses):
        raise ValueError("Catalyst weight-matrix adapter requires unique axon/target pairs")
    max_abs_weight = max(abs(int(s.weight)) for s in workload.synapses)
    weights_fit_int16 = max_abs_weight <= INT16_MAX
    return {
        "schema": "neuromorphic-twin-mnist-12-catalyst-feasibility-v1",
        "catalyst_commit": CATALYST_PIN,
        "frozen_profile": workload.profile,
        "graph": {
            "source_neurons_if_materialized": workload.input_axons,
            "output_neurons": workload.output_neurons,
            "total_neurons_if_materialized": graph_neurons,
            "effective_edges": len(workload.synapses),
            "unique_source_target_pairs": len(graph_pairs),
            "max_abs_effective_weight": max_abs_weight,
            "all_effective_weights_fit_signed_int16": weights_fit_int16,
        },
        "generic_cpu_reference": {
            "neurons_per_core": GENERIC_CPU_NEURONS_PER_CORE,
            "graph_preserving_single_core_fit": graph_neurons <= GENERIC_CPU_NEURONS_PER_CORE,
            "delivered_drive_accumulator_bits": 32,
            "delivered_drive_allows_fanin_sum_beyond_signed_int16": True,
            "note": (
                "Pinned Simulator uses a software-expanded connection pool and numpy.int32 "
                "external-current/soma-accumulator paths. Wide delivered-drive is a CPU-only "
                "semantic control, not a K26 host-stimulus or hardware-fit claim."
            ),
        },
        "pinned_k26_wrapper": {
            "configured_neurons": K26_CONFIGURED_NEURONS,
            "pool_depth_per_core": K26_POOL_DEPTH_PER_CORE,
            "graph_preserving_fit": graph_neurons <= K26_CONFIGURED_NEURONS,
            "graph_preserving_blocker": (
                None
                if graph_neurons <= K26_CONFIGURED_NEURONS
                else f"materialized graph needs {graph_neurons} neurons but pinned K26 wrapper configures {K26_CONFIGURED_NEURONS}"
            ),
            "delivered_drive_output_only_neuron_fit": workload.output_neurons <= K26_CONFIGURED_NEURONS,
            "physical_programming_source_supported": False,
            "physical_programming_blocker": (
                "Pinned M13.5 K26 source has no board XDC/PS integration/write_bitstream "
                "path; routed implementation is the strongest source-supported boundary."
            ),
        },
        "decision": {
            "software_graph_preserving_experiment": "SUPPORTED",
            "software_delivered_drive_experiment": "SUPPORTED_CPU_INT32_CONTROL",
            "physical_graph_preserving_k26_experiment": "BLOCKED_BY_PINNED_WRAPPER_CAPACITY_AND_BOARD_INTEGRATION",
            "physical_delivered_drive_k26_experiment": "BLOCKED_BY_BOARD_INTEGRATION_AND_NOT_GRAPH_MATCHED",
        },
    }


def _normalized_project_trace(trace: object) -> dict[str, object]:
    return {
        "ticks": [
            {
                "canonical_tick": int(tick.tick),
                "voltage_after": [int(v) for v in tick.voltage_after],
                "spikes": [int(v) for v in tick.spikes],
            }
            for tick in trace.ticks
        ]
    }


def _compare_voltage_spikes(
    reference: Mapping[str, object], candidate: Mapping[str, object]
) -> dict[str, object]:
    ref_ticks = list(reference["ticks"])
    cand_ticks = list(candidate["ticks"])
    if len(ref_ticks) != len(cand_ticks):
        return {
            "passed": False,
            "mismatch_count": 1,
            "first_mismatch": {
                "field": "tick_count",
                "reference": len(ref_ticks),
                "candidate": len(cand_ticks),
            },
        }

    mismatches: list[dict[str, object]] = []
    for expected_tick, (ref, cand) in enumerate(zip(ref_ticks, cand_ticks, strict=True)):
        if int(ref["canonical_tick"]) != expected_tick or int(cand["canonical_tick"]) != expected_tick:
            mismatches.append(
                {
                    "canonical_tick": expected_tick,
                    "field": "tick_id",
                    "reference": ref["canonical_tick"],
                    "candidate": cand["canonical_tick"],
                }
            )
            continue
        for field in ("voltage_after", "spikes"):
            if list(ref[field]) != list(cand[field]):
                mismatches.append(
                    {
                        "canonical_tick": expected_tick,
                        "field": field,
                        "reference": list(ref[field]),
                        "candidate": list(cand[field]),
                    }
                )
    return {
        "passed": not mismatches,
        "mismatch_count": len(mismatches),
        "first_mismatch": mismatches[0] if mismatches else None,
    }


def _collapse_delivered_drive(
    workload: FrozenMatchedWorkload,
    schedule: Sequence[Sequence[int]],
) -> tuple[tuple[int, ...], ...]:
    """Return exact per-output fan-in sums without narrowing to signed int16.

    Individual frozen weights remain signed-int16-compatible.  Multiple active
    axons may converge on one output during the same algorithmic tick, so the
    *sum* can legitimately exceed signed int16 (for example -55,680 in the
    accepted anchor bundle).  The pinned Catalyst CPU simulator's external
    current and synchronous soma accumulator are signed 32-bit NumPy arrays.
    """

    rows: dict[int, list[tuple[int, int]]] = {}
    for synapse in workload.synapses:
        rows.setdefault(int(synapse.axon_id), []).append(
            (int(synapse.target_neuron), int(synapse.weight))
        )

    collapsed: list[tuple[int, ...]] = []
    for tick, events in enumerate(schedule):
        values = [0] * workload.output_neurons
        for axon_id in events:
            for target, weight in rows.get(int(axon_id), ()):
                values[target] += weight
        for neuron_id, value in enumerate(values):
            if not INT32_MIN <= value <= INT32_MAX:
                raise OverflowError(
                    f"Catalyst CPU delivered-drive tick {tick} neuron {neuron_id} "
                    f"sum {value} exceeds signed int32"
                )
        collapsed.append(tuple(values))
    return tuple(collapsed)


def _run_delivered_drive(
    workload: FrozenMatchedWorkload,
    image: MatchedImageInput,
    project_trace: object,
) -> tuple[
    dict[str, object],
    tuple[int, ...],
    int,
    dict[str, object],
    dict[str, object],
]:
    """Run the CPU-only exact fan-in-sum control directly on output neurons."""

    try:
        import neurocore as nc
        from neurocore.constants import NEURONS_PER_CORE
    except Exception as exc:  # pragma: no cover - external pinned environment
        raise RuntimeError(
            "Catalyst neurocore SDK is not importable; put the pinned catalyst-n1/sdk on PYTHONPATH"
        ) from exc

    currents = _collapse_delivered_drive(workload, image.schedule)
    network = nc.Network()
    output = network.population(
        workload.output_neurons,
        params={"threshold": 8385, "leak": 0, "resting": 0, "refrac": 0},
        label="mnist_outputs_direct_drive",
    )
    simulator = nc.Simulator(num_cores=1)
    simulator.deploy(network)

    ext_dtype = str(simulator._ext_current.dtype)
    if ext_dtype != "int32":
        raise RuntimeError(
            f"pinned Catalyst CPU external-current dtype changed: expected int32, got {ext_dtype}"
        )

    placement = simulator._compiled.placement.neuron_map
    output_gids = [
        int(placement[(output.id, index)][0]) * int(NEURONS_PER_CORE)
        + int(placement[(output.id, index)][1])
        for index in range(workload.output_neurons)
    ]
    output_gid_to_logical = {gid: logical for logical, gid in enumerate(output_gids)}

    normalized_ticks: list[dict[str, object]] = []
    max_abs_current = 0
    outside_int16_values = 0
    for canonical_tick, row in enumerate(currents):
        for neuron_id, current in enumerate(row):
            max_abs_current = max(max_abs_current, abs(int(current)))
            if int(current) < INT16_MIN or int(current) > INT16_MAX:
                outside_int16_values += 1
            if int(current) != 0:
                simulator.inject(output[neuron_id], int(current))
        result = simulator.run(1)
        spike_gids = {int(gid) for gid in result.spike_trains}
        normalized_ticks.append(
            {
                "canonical_tick": canonical_tick,
                "native_tick": canonical_tick,
                "voltage_after": [int(simulator._potential[gid]) for gid in output_gids],
                "spikes": sorted(
                    output_gid_to_logical[gid]
                    for gid in spike_gids
                    if gid in output_gid_to_logical
                ),
            }
        )

    normalized = {"ticks": normalized_ticks}
    comparison = _compare_voltage_spikes(_normalized_project_trace(project_trace), normalized)
    counts = [0] * workload.output_neurons
    for tick in normalized_ticks:
        for neuron_id in tick["spikes"]:
            counts[int(neuron_id)] += 1
    result_counts = tuple(counts)
    metadata = {
        "catalyst_commit": CATALYST_PIN,
        "transport": "cpu_reference_direct_current",
        "external_current_dtype": ext_dtype,
        "fan_in_sum_width": "signed-int32",
        "max_abs_delivered_current": max_abs_current,
        "delivered_values_outside_signed_int16": outside_int16_values,
        "hardware_transport_claim": False,
        "m13_signed_int16_direct_stimulus_guard_reused": False,
    }
    return (
        comparison,
        result_counts,
        decode_spike_counts(result_counts),
        normalized,
        metadata,
    )


def _build_weight_matrix(workload: FrozenMatchedWorkload):
    import numpy as np

    matrix = np.zeros((workload.input_axons, workload.output_neurons), dtype=np.int32)
    seen: set[tuple[int, int]] = set()
    for synapse in workload.synapses:
        key = (int(synapse.axon_id), int(synapse.target_neuron))
        if key in seen:
            raise ValueError(f"duplicate frozen axon/target pair cannot map to Catalyst matrix: {key}")
        seen.add(key)
        value = int(synapse.weight)
        if not INT16_MIN <= value <= INT16_MAX:
            raise ValueError("frozen effective weight exceeds Catalyst signed-int16 boundary")
        matrix[key] = value
    if int(np.count_nonzero(matrix)) != len(workload.synapses):
        raise AssertionError("Catalyst weight matrix lost a stored nonzero synapse")
    return matrix


def _run_graph_preserving(
    workload: FrozenMatchedWorkload,
    image: MatchedImageInput,
) -> tuple[dict[str, object], tuple[int, ...], int, dict[str, object]]:
    """Run 784 explicit source neurons -> 10 output neurons in Catalyst SDK."""

    try:
        import neurocore as nc
        from neurocore.constants import NEURONS_PER_CORE
    except Exception as exc:  # pragma: no cover - external pinned environment
        raise RuntimeError(
            "Catalyst neurocore SDK is not importable; put the pinned catalyst-n1/sdk on PYTHONPATH"
        ) from exc

    if int(NEURONS_PER_CORE) < workload.input_axons + workload.output_neurons:
        raise RuntimeError("pinned Catalyst SDK cannot fit the graph-preserving MNIST reference on one core")

    network = nc.Network()
    source = network.population(
        workload.input_axons,
        params={"threshold": 1, "leak": 0, "resting": 0, "refrac": 0},
        label="mnist_pixels",
    )
    output = network.population(
        workload.output_neurons,
        params={"threshold": 8385, "leak": 0, "resting": 0, "refrac": 0},
        label="mnist_outputs",
    )
    matrix = _build_weight_matrix(workload)
    network.connect(source, output, weight_matrix=matrix, delay=0, format="sparse")

    simulator = nc.Simulator(num_cores=1)
    simulator.deploy(network)
    placement = simulator._compiled.placement.neuron_map
    source_gids = [
        int(placement[(source.id, index)][0]) * int(NEURONS_PER_CORE)
        + int(placement[(source.id, index)][1])
        for index in range(workload.input_axons)
    ]
    output_gids = [
        int(placement[(output.id, index)][0]) * int(NEURONS_PER_CORE)
        + int(placement[(output.id, index)][1])
        for index in range(workload.output_neurons)
    ]
    output_gid_to_logical = {gid: logical for logical, gid in enumerate(output_gids)}
    source_gid_to_logical = {gid: logical for logical, gid in enumerate(source_gids)}

    compiled_edges = sum(len(entries) for entries in simulator._adjacency.values())
    if compiled_edges != len(workload.synapses):
        raise RuntimeError(
            f"Catalyst compiler produced {compiled_edges} edges; expected {len(workload.synapses)}"
        )

    native_ticks: list[dict[str, object]] = []
    for native_tick in range(workload.presentation_ticks + 1):
        events = image.schedule[native_tick] if native_tick < workload.presentation_ticks else ()
        for axon_id in events:
            simulator.inject(source[int(axon_id)], 1)
        result = simulator.run(1)
        spike_gids = {int(gid) for gid in result.spike_trains}
        observed_source_spikes = sorted(
            source_gid_to_logical[gid] for gid in spike_gids if gid in source_gid_to_logical
        )
        if native_tick < workload.presentation_ticks and observed_source_spikes != sorted(events):
            raise RuntimeError(
                f"Catalyst source-neuron encoder mismatch at native tick {native_tick}: "
                f"expected={sorted(events)} observed={observed_source_spikes}"
            )
        native_ticks.append(
            {
                "native_tick": native_tick,
                "source_events": [int(v) for v in events],
                "output_voltage_after": [int(simulator._potential[gid]) for gid in output_gids],
                "output_spikes": sorted(
                    output_gid_to_logical[gid]
                    for gid in spike_gids
                    if gid in output_gid_to_logical
                ),
            }
        )

    normalized = {
        "ticks": [
            {
                "canonical_tick": canonical_tick,
                "native_tick": canonical_tick + 1,
                "voltage_after": list(native_ticks[canonical_tick + 1]["output_voltage_after"]),
                "spikes": list(native_ticks[canonical_tick + 1]["output_spikes"]),
            }
            for canonical_tick in range(workload.presentation_ticks)
        ]
    }
    counts = [0] * workload.output_neurons
    for tick in normalized["ticks"]:
        for neuron_id in tick["spikes"]:
            counts[int(neuron_id)] += 1
    count_tuple = tuple(counts)
    metadata = {
        "catalyst_commit": CATALYST_PIN,
        "source_neurons": workload.input_axons,
        "output_neurons": workload.output_neurons,
        "deployed_neurons": workload.input_axons + workload.output_neurons,
        "compiled_edges": compiled_edges,
        "native_ticks": workload.presentation_ticks + 1,
        "warmup_pipeline_ticks": 1,
    }
    return normalized, count_tuple, decode_spike_counts(count_tuple), metadata


def run_catalyst_matched_case(
    workload: FrozenMatchedWorkload,
    image: MatchedImageInput,
) -> dict[str, object]:
    from neuromorphic_twin.comparison.compare import compare_traces
    from neuromorphic_twin.comparison.python_backend import run_python_backend

    name = f"mnist12-native-sparse-index{image.mnist_test_index:05d}"
    project_original = build_comparison_scenario(
        workload,
        image.schedule,
        name=name,
        reference_refractory=False,
        unbounded_arithmetic=False,
    )
    project_reference = build_comparison_scenario(
        workload,
        image.schedule,
        name=name,
        reference_refractory=True,
        unbounded_arithmetic=False,
    )
    original_trace = run_python_backend(project_original)
    reference_trace = run_python_backend(project_reference)
    refractory_report = compare_traces(
        original_trace,
        reference_trace,
        fields=("current_after", "voltage_after", "spikes"),
    )
    if not refractory_report.passed:
        raise RuntimeError("project R=0 -> R=1 equivalence failed before Catalyst execution")
    project_counts = spike_counts_from_trace(original_trace)
    project_prediction = decode_spike_counts(project_counts)
    if project_counts != image.golden_spike_counts or project_prediction != image.golden_prediction:
        raise RuntimeError("matched project scenario no longer reproduces frozen golden result")

    (
        direct_cmp,
        direct_counts,
        direct_prediction,
        direct_normalized,
        direct_metadata,
    ) = _run_delivered_drive(workload, image, reference_trace)
    graph_normalized, graph_counts, graph_prediction, graph_metadata = _run_graph_preserving(
        workload, image
    )
    graph_cmp = _compare_voltage_spikes(
        _normalized_project_trace(reference_trace), graph_normalized
    )

    internal_trace_cmp = _compare_voltage_spikes(direct_normalized, graph_normalized)
    catalyst_internal_prediction_agreement = graph_prediction == direct_prediction
    catalyst_internal_spike_vector_agreement = graph_counts == direct_counts
    transport_consistent = (
        internal_trace_cmp["passed"]
        and catalyst_internal_prediction_agreement
        and catalyst_internal_spike_vector_agreement
    )

    return {
        "schema": RESULT_SCHEMA,
        "profile": workload.profile,
        "mnist_test_index": image.mnist_test_index,
        "label": image.label,
        "project_prediction": project_prediction,
        "project_spike_counts": list(project_counts),
        "refractory_0_to_1_equivalent": True,
        "delivered_drive": {
            "prediction": direct_prediction,
            "spike_counts": list(direct_counts),
            "prediction_agreement_with_project": direct_prediction == project_prediction,
            "spike_vector_agreement_with_project": direct_counts == project_counts,
            "voltage_spike_trace": direct_cmp,
            "metadata": direct_metadata,
            "evidence_label": "MATCHED DELIVERED DRIVE + TRANSLATED DYNAMICS (CPU INT32 CONTROL)",
        },
        "graph_preserving": {
            "prediction": graph_prediction,
            "spike_counts": list(graph_counts),
            "prediction_agreement_with_project": graph_prediction == project_prediction,
            "spike_vector_agreement_with_project": graph_counts == project_counts,
            "voltage_spike_trace": graph_cmp,
            "metadata": graph_metadata,
            "evidence_label": "MATCHED EFFECTIVE GRAPH + TRANSLATED DYNAMICS",
        },
        "catalyst_internal_control": {
            "prediction_agreement": catalyst_internal_prediction_agreement,
            "spike_vector_agreement": catalyst_internal_spike_vector_agreement,
            "voltage_spike_trace": internal_trace_cmp,
        },
        "passed_transport_consistency": transport_consistent,
        "note": (
            "A Catalyst-vs-project mismatch is an experimental result, not an automatic "
            "failure. Only disagreement between the independently constructed Catalyst "
            "graph-preserving and exact-fan-in CPU control paths fails closed."
        ),
    }


def summarize_suite(results: Sequence[dict[str, object]]) -> dict[str, object]:
    if not results:
        raise ValueError("Catalyst matched suite requires at least one case")
    return {
        "schema": SUITE_SCHEMA,
        "profile": "native-sparse",
        "case_count": len(results),
        "transport_consistent_cases": sum(bool(r["passed_transport_consistency"]) for r in results),
        "graph_prediction_agreement_cases": sum(
            bool(r["graph_preserving"]["prediction_agreement_with_project"]) for r in results
        ),
        "graph_spike_vector_agreement_cases": sum(
            bool(r["graph_preserving"]["spike_vector_agreement_with_project"]) for r in results
        ),
        "delivered_drive_prediction_agreement_cases": sum(
            bool(r["delivered_drive"]["prediction_agreement_with_project"]) for r in results
        ),
        "delivered_drive_spike_vector_agreement_cases": sum(
            bool(r["delivered_drive"]["spike_vector_agreement_with_project"]) for r in results
        ),
        "cases": [
            {
                "mnist_test_index": int(r["mnist_test_index"]),
                "label": int(r["label"]),
                "project_prediction": int(r["project_prediction"]),
                "graph_prediction": int(r["graph_preserving"]["prediction"]),
                "delivered_drive_prediction": int(r["delivered_drive"]["prediction"]),
                "transport_consistent": bool(r["passed_transport_consistency"]),
            }
            for r in results
        ],
    }


def write_json(payload: Mapping[str, object], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
