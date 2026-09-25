"""Classify Catalyst MNIST divergences using predeclared semantic differences."""

from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence


EXACT = "EXACT"
SUB_REST_CLAMP = "CATALYST_SUB_REST_CLAMP"
TRANSPORT_INCONSISTENT = "CATALYST_TRANSPORT_INCONSISTENT"
OTHER = "OTHER_TRANSLATED_DYNAMICS"


def _first_mismatch(result: Mapping[str, object], view: str) -> Mapping[str, object] | None:
    payload = result[view]
    comparison = payload["voltage_spike_trace"]
    mismatch = comparison.get("first_mismatch")
    return mismatch if isinstance(mismatch, Mapping) else None


def _is_sub_rest_clamp(mismatch: Mapping[str, object] | None) -> bool:
    if mismatch is None or mismatch.get("field") != "voltage_after":
        return False
    reference = mismatch.get("reference")
    candidate = mismatch.get("candidate")
    if not isinstance(reference, Sequence) or isinstance(reference, (str, bytes)):
        return False
    if not isinstance(candidate, Sequence) or isinstance(candidate, (str, bytes)):
        return False
    ref = [int(value) for value in reference]
    cand = [int(value) for value in candidate]
    if len(ref) != len(cand) or not any(value < 0 for value in ref):
        return False
    return cand == [max(value, 0) for value in ref]


def classify_case(result: Mapping[str, object]) -> dict[str, object]:
    """Classify the first FPGA-v1/Catalyst divergence for one matched case.

    Classification is intentionally causal and conservative. We only assign
    ``CATALYST_SUB_REST_CLAMP`` when the two independent Catalyst views are
    internally trace-identical and their first mismatch against FPGA-v1 is the
    same voltage vector obtained by replacing each negative project voltage with
    Catalyst's resting value zero. Later differences may be downstream effects
    of that first state divergence and are not independently relabeled.
    """

    internal = result["catalyst_internal_control"]["voltage_spike_trace"]
    if not bool(result.get("passed_transport_consistency")) or not bool(internal.get("passed")):
        classification = TRANSPORT_INCONSISTENT
    else:
        graph = _first_mismatch(result, "graph_preserving")
        direct = _first_mismatch(result, "delivered_drive")
        graph_count = int(result["graph_preserving"]["voltage_spike_trace"]["mismatch_count"])
        direct_count = int(result["delivered_drive"]["voltage_spike_trace"]["mismatch_count"])
        if graph_count == 0 and direct_count == 0:
            classification = EXACT
        elif graph == direct and _is_sub_rest_clamp(graph):
            classification = SUB_REST_CLAMP
        else:
            classification = OTHER

    return {
        "mnist_test_index": int(result["mnist_test_index"]),
        "label": int(result["label"]),
        "project_prediction": int(result["project_prediction"]),
        "graph_prediction": int(result["graph_preserving"]["prediction"]),
        "direct_prediction": int(result["delivered_drive"]["prediction"]),
        "prediction_agreement": bool(
            result["graph_preserving"]["prediction_agreement_with_project"]
        ),
        "graph_spike_vector_agreement": bool(
            result["graph_preserving"]["spike_vector_agreement_with_project"]
        ),
        "direct_spike_vector_agreement": bool(
            result["delivered_drive"]["spike_vector_agreement_with_project"]
        ),
        "transport_consistent": bool(result["passed_transport_consistency"]),
        "classification": classification,
        "graph_first_mismatch": _first_mismatch(result, "graph_preserving"),
        "direct_first_mismatch": _first_mismatch(result, "delivered_drive"),
    }


def _aggregate(cases: Sequence[Mapping[str, object]]) -> dict[str, object]:
    counts = Counter(str(case["classification"]) for case in cases)
    return {
        "case_count": len(cases),
        "classification_counts": dict(sorted(counts.items())),
        "transport_consistent_cases": sum(bool(case["transport_consistent"]) for case in cases),
        "prediction_agreement_cases": sum(bool(case["prediction_agreement"]) for case in cases),
        "graph_spike_vector_agreement_cases": sum(
            bool(case["graph_spike_vector_agreement"]) for case in cases
        ),
        "direct_spike_vector_agreement_cases": sum(
            bool(case["direct_spike_vector_agreement"]) for case in cases
        ),
        "sub_rest_clamp_cases": counts.get(SUB_REST_CLAMP, 0),
        "exact_cases": counts.get(EXACT, 0),
        "other_translated_dynamics_cases": counts.get(OTHER, 0),
        "transport_inconsistent_cases": counts.get(TRANSPORT_INCONSISTENT, 0),
    }


def summarize_cases(results: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not results:
        raise ValueError("Catalyst divergence summary requires at least one case")
    cases = [classify_case(result) for result in results]
    return {
        "schema": "neuromorphic-twin-mnist-12-catalyst-divergence-summary-v1",
        **_aggregate(cases),
        "cases": cases,
    }


def summarize_cases_compact(results: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Return full-scope evidence without embedding first-mismatch vectors per case."""

    if not results:
        raise ValueError("Catalyst divergence summary requires at least one case")
    cases = [classify_case(result) for result in results]
    classifications: dict[str, list[int]] = {}
    for case in cases:
        classifications.setdefault(str(case["classification"]), []).append(
            int(case["mnist_test_index"])
        )
    return {
        "schema": "neuromorphic-twin-mnist-12-catalyst-divergence-compact-v1",
        **_aggregate(cases),
        "classification_indices": dict(sorted(classifications.items())),
        "prediction_disagreement_indices": [
            int(case["mnist_test_index"])
            for case in cases
            if not bool(case["prediction_agreement"])
        ],
        "graph_spike_vector_disagreement_indices": [
            int(case["mnist_test_index"])
            for case in cases
            if not bool(case["graph_spike_vector_agreement"])
        ],
        "transport_inconsistent_indices": [
            int(case["mnist_test_index"])
            for case in cases
            if not bool(case["transport_consistent"])
        ],
    }
