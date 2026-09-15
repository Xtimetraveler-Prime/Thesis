from __future__ import annotations

from pathlib import Path

import pytest

from mnist_app.catalyst_matched import _build_weight_matrix, catalyst_feasibility_audit
from mnist_app.matched_bundle import scope_indices
from mnist_app.matched_reference import (
    SAT24_MAX,
    build_comparison_scenario,
    load_frozen_matched_workload,
    semantic_audit,
    validate_schedule,
)


FROZEN = Path(__file__).parents[1] / "frozen" / "mnist-v1"


def test_frozen_native_sparse_matched_contract() -> None:
    workload = load_frozen_matched_workload(FROZEN)
    assert workload.profile == "native-sparse"
    assert workload.input_axons == 784
    assert workload.output_neurons == 10
    assert workload.presentation_ticks == 16
    assert len(workload.synapses) == 4086
    assert workload.configs[0].threshold == 8384
    assert workload.configs[0].current_decay == 4096
    assert workload.configs[0].voltage_decay == 0
    assert workload.configs[0].refractory_ticks == 0
    assert workload.conservative_abs_voltage_bound < SAT24_MAX
    assert all(s.encoding is not None for s in workload.synapses)
    assert all(s.weight % 64 == 0 for s in workload.synapses)
    assert max(abs(s.weight) for s in workload.synapses) <= 32767


def test_semantic_audit_has_explicit_reference_classes() -> None:
    workload = load_frozen_matched_workload(FROZEN)
    rows = {row.field: row for row in semantic_audit(workload)}
    assert rows["refractory"].brian2loihi == "EQUIVALENT"
    assert rows["refractory"].catalyst == "EQUIVALENT"
    assert rows["synaptic_graph"].brian2loihi == "EXACT"
    assert rows["synaptic_graph"].catalyst == "TRANSLATED"
    assert rows["finite_width_saturation"].catalyst == "UNREPRESENTABLE"
    assert rows["online_learning_recurrence"].brian2loihi == "NOT_USED"


def test_project_refractory_zero_and_reference_one_are_exactly_equivalent() -> None:
    from neuromorphic_twin.comparison.compare import compare_traces
    from neuromorphic_twin.comparison.python_backend import run_python_backend

    workload = load_frozen_matched_workload(FROZEN)
    # Use a deterministic high-activity schedule so the equivalence is exercised
    # across repeated opportunities to spike, not just a quiescent trace.
    rows = [tuple(range(0, 784, 7)) for _ in range(16)]
    original = build_comparison_scenario(
        workload, rows, name="r0-r1-regression", reference_refractory=False
    )
    reference = build_comparison_scenario(
        workload, rows, name="r0-r1-regression", reference_refractory=True
    )
    report = compare_traces(
        run_python_backend(original),
        run_python_backend(reference),
        fields=("current_after", "voltage_after", "spikes"),
    )
    assert report.passed


def test_schedule_rejects_same_source_same_tick_multiplicity() -> None:
    rows = [()] * 16
    rows[0] = (4, 4)
    with pytest.raises(ValueError, match="repeats a source axon"):
        validate_schedule(rows)


def test_scope_indices_reuse_accepted_anchor_and_30_image_corpus() -> None:
    assert scope_indices("anchor", FROZEN) == (3, 1)
    corpus = scope_indices("corpus", FROZEN)
    assert len(corpus) == 30
    assert len(set(corpus)) == 30
    assert 3 in corpus and 1 in corpus


def test_catalyst_feasibility_distinguishes_cpu_from_pinned_k26_wrapper() -> None:
    workload = load_frozen_matched_workload(FROZEN)
    audit = catalyst_feasibility_audit(workload)
    assert audit["generic_cpu_reference"]["graph_preserving_single_core_fit"] is True
    assert audit["pinned_k26_wrapper"]["graph_preserving_fit"] is False
    assert audit["pinned_k26_wrapper"]["physical_programming_source_supported"] is False
    assert audit["graph"]["total_neurons_if_materialized"] == 794
    assert audit["graph"]["effective_edges"] == 4086


def test_catalyst_weight_matrix_preserves_all_stored_edges() -> None:
    import numpy as np

    workload = load_frozen_matched_workload(FROZEN)
    matrix = _build_weight_matrix(workload)
    assert matrix.shape == (784, 10)
    assert int(np.count_nonzero(matrix)) == 4086
    for synapse in workload.synapses[:100]:
        assert int(matrix[synapse.axon_id, synapse.target_neuron]) == synapse.weight
