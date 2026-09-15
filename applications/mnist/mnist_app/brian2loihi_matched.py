"""Matched native-sparse MNIST execution against pinned Brian2Loihi."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Sequence

from .matched_reference import (
    FrozenMatchedWorkload,
    build_comparison_scenario,
    decode_spike_counts,
    spike_counts_from_trace,
)


RESULT_SCHEMA = "neuromorphic-twin-mnist-11-brian2loihi-case-v1"
SUITE_SCHEMA = "neuromorphic-twin-mnist-11-brian2loihi-suite-v1"


@dataclass(frozen=True, slots=True)
class MatchedImageInput:
    mnist_test_index: int
    label: int
    schedule: tuple[tuple[int, ...], ...]
    golden_prediction: int
    golden_spike_counts: tuple[int, ...]


def _report_payload(report: object) -> dict[str, object]:
    return {
        "passed": bool(report.passed),
        "compared_ticks": int(report.compared_ticks),
        "mismatch_count": len(report.mismatches),
        "first_mismatch": (
            None
            if not report.mismatches
            else {
                "tick": report.mismatches[0].tick,
                "field": report.mismatches[0].field,
                "neuron_id": report.mismatches[0].neuron_id,
                "reference": report.mismatches[0].reference,
                "candidate": report.mismatches[0].candidate,
            }
        ),
    }


def run_brian2loihi_matched_case(
    workload: FrozenMatchedWorkload,
    image: MatchedImageInput,
) -> dict[str, object]:
    """Run one frozen image through project and Brian2Loihi without retuning.

    The project R=0 configuration is first compared against an otherwise
    identical project R=1 surrogate.  Brian2Loihi is invoked only after that
    equivalence is proven for the exact image schedule.  The Brian scenario uses
    unbounded arithmetic because the external emulator does not model the
    project's SAT24 policy; the frozen deployment's accepted conservative bound
    proves saturation is inactive for this workload profile.
    """

    from neuromorphic_twin.comparison.brian2loihi_backend import (
        run_brian2loihi_backend_with_weights,
    )
    from neuromorphic_twin.comparison.compare import compare_traces
    from neuromorphic_twin.comparison.python_backend import run_python_backend

    name = f"mnist11-native-sparse-index{image.mnist_test_index:05d}"
    project_scenario = build_comparison_scenario(
        workload,
        image.schedule,
        name=name,
        reference_refractory=False,
        unbounded_arithmetic=False,
    )
    surrogate_scenario = build_comparison_scenario(
        workload,
        image.schedule,
        name=name,
        reference_refractory=True,
        unbounded_arithmetic=False,
    )
    brian_scenario = build_comparison_scenario(
        workload,
        image.schedule,
        name=name,
        reference_refractory=True,
        unbounded_arithmetic=True,
    )

    project_trace = run_python_backend(project_scenario)
    surrogate_trace = run_python_backend(surrogate_scenario)
    refractory_report = compare_traces(
        project_trace,
        surrogate_trace,
        fields=("current_after", "voltage_after", "spikes"),
    )
    if not refractory_report.passed:
        raise RuntimeError(
            "project R=0 -> R=1 matched-reference equivalence failed for "
            f"MNIST index {image.mnist_test_index}"
        )

    project_counts = spike_counts_from_trace(project_trace)
    project_prediction = decode_spike_counts(project_counts)
    if project_counts != image.golden_spike_counts or project_prediction != image.golden_prediction:
        raise RuntimeError(
            "matched project scenario no longer reproduces the frozen golden result"
        )

    brian_run = run_brian2loihi_backend_with_weights(brian_scenario)
    brian_trace = brian_run.trace
    trace_report = compare_traces(
        surrogate_trace,
        brian_trace,
        fields=("current_after", "voltage_after", "spikes"),
    )
    brian_counts = spike_counts_from_trace(brian_trace)
    brian_prediction = decode_spike_counts(brian_counts)

    expected_weights = tuple(int(synapse.weight) for synapse in workload.synapses)
    observed_weights = tuple(int(value) for value in brian_run.effective_weights)
    weight_mismatches = [
        index
        for index, (expected, observed) in enumerate(
            zip(expected_weights, observed_weights, strict=True)
        )
        if expected != observed
    ]

    exact_spike_vector = brian_counts == project_counts
    exact_prediction = brian_prediction == project_prediction
    passed = (
        trace_report.passed
        and not weight_mismatches
        and exact_spike_vector
        and exact_prediction
    )
    return {
        "schema": RESULT_SCHEMA,
        "profile": workload.profile,
        "mnist_test_index": image.mnist_test_index,
        "label": image.label,
        "ticks": len(image.schedule),
        "total_input_events": sum(len(row) for row in image.schedule),
        "project_refractory_0_to_1_equivalence": _report_payload(refractory_report),
        "project_prediction": project_prediction,
        "brian2loihi_prediction": brian_prediction,
        "project_spike_counts": list(project_counts),
        "brian2loihi_spike_counts": list(brian_counts),
        "prediction_agreement": exact_prediction,
        "spike_count_vector_agreement": exact_spike_vector,
        "trace_comparison": _report_payload(trace_report),
        "weight_count": len(expected_weights),
        "effective_weight_mismatch_count": len(weight_mismatches),
        "first_effective_weight_mismatch_index": (
            weight_mismatches[0] if weight_mismatches else None
        ),
        "passed": passed,
        "evidence_label": "MATCHED GRAPH + MATCHED/EXPLICITLY-EQUIVALENT DYNAMICS",
    }


def write_case_result(result: dict[str, object], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def summarize_suite(results: Sequence[dict[str, object]]) -> dict[str, object]:
    if not results:
        raise ValueError("Brian2Loihi matched suite requires at least one case")
    predictions = sum(bool(result["prediction_agreement"]) for result in results)
    spike_vectors = sum(bool(result["spike_count_vector_agreement"]) for result in results)
    trace_exact = sum(bool(result["trace_comparison"]["passed"]) for result in results)
    passed = sum(bool(result["passed"]) for result in results)
    return {
        "schema": SUITE_SCHEMA,
        "profile": "native-sparse",
        "case_count": len(results),
        "passed_cases": passed,
        "prediction_agreement_cases": predictions,
        "spike_count_vector_agreement_cases": spike_vectors,
        "exact_trace_agreement_cases": trace_exact,
        "all_passed": passed == len(results),
        "cases": [
            {
                "mnist_test_index": int(result["mnist_test_index"]),
                "label": int(result["label"]),
                "project_prediction": int(result["project_prediction"]),
                "brian2loihi_prediction": int(result["brian2loihi_prediction"]),
                "trace_mismatches": int(result["trace_comparison"]["mismatch_count"]),
                "weight_mismatches": int(result["effective_weight_mismatch_count"]),
                "passed": bool(result["passed"]),
            }
            for result in results
        ],
    }


def write_suite_summary(results: Sequence[dict[str, object]], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(summarize_suite(results), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target
