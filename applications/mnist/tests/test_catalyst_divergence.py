from __future__ import annotations

from mnist_app.catalyst_divergence import (
    EXACT,
    OTHER,
    SUB_REST_CLAMP,
    TRANSPORT_INCONSISTENT,
    classify_case,
    summarize_cases,
)


def _case(*, ref, cand, internal_passed=True, prediction=0):
    mismatch = None if ref == cand else {
        "canonical_tick": 0,
        "field": "voltage_after",
        "reference": ref,
        "candidate": cand,
    }
    comparison = {
        "passed": mismatch is None,
        "mismatch_count": 0 if mismatch is None else 1,
        "first_mismatch": mismatch,
    }
    return {
        "mnist_test_index": 3,
        "label": 0,
        "project_prediction": 0,
        "graph_preserving": {
            "prediction": prediction,
            "prediction_agreement_with_project": prediction == 0,
            "voltage_spike_trace": comparison,
        },
        "delivered_drive": {
            "prediction": prediction,
            "prediction_agreement_with_project": prediction == 0,
            "voltage_spike_trace": comparison,
        },
        "catalyst_internal_control": {
            "voltage_spike_trace": {
                "passed": internal_passed,
                "mismatch_count": 0 if internal_passed else 1,
                "first_mismatch": None if internal_passed else {"field": "voltage_after"},
            }
        },
        "passed_transport_consistency": internal_passed,
    }


def test_classifies_exact_sub_rest_and_other() -> None:
    exact = classify_case(_case(ref=[1, 2], cand=[1, 2]))
    assert exact["classification"] == EXACT

    clamp = classify_case(_case(ref=[0, -10, 4, -3], cand=[0, 0, 4, 0]))
    assert clamp["classification"] == SUB_REST_CLAMP

    other = classify_case(_case(ref=[0, -10, 4], cand=[0, 0, 5]))
    assert other["classification"] == OTHER


def test_transport_inconsistency_takes_precedence() -> None:
    result = classify_case(
        _case(ref=[0, -10], cand=[0, 0], internal_passed=False)
    )
    assert result["classification"] == TRANSPORT_INCONSISTENT


def test_summary_counts_anchor_style_results() -> None:
    first = _case(ref=[0, -13888, 2176, -2368], cand=[0, 0, 2176, 0])
    second = _case(ref=[3136, -3072, 8128, -22016], cand=[3136, 0, 8128, 0], prediction=2)
    second["mnist_test_index"] = 1
    second["label"] = 2
    second["project_prediction"] = 2
    second["graph_preserving"]["prediction_agreement_with_project"] = True
    second["delivered_drive"]["prediction_agreement_with_project"] = True

    summary = summarize_cases([first, second])
    assert summary["case_count"] == 2
    assert summary["transport_consistent_cases"] == 2
    assert summary["prediction_agreement_cases"] == 2
    assert summary["sub_rest_clamp_cases"] == 2
    assert summary["other_translated_dynamics_cases"] == 0
