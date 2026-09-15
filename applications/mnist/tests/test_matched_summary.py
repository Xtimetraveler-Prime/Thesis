from __future__ import annotations

import json
from pathlib import Path

import pytest

from mnist_app.matched_summary import build_matched_summary


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _accepted() -> dict[str, object]:
    return {
        "corpus": "official-mnist-test-full",
        "profiles": {
            "native-sparse": {
                "summary": {
                    "images": 10000,
                    "golden_accuracy": 0.9171,
                    "deployment_stored_synapses": 4086,
                }
            }
        },
    }


def _brian(indices: list[int]) -> dict[str, object]:
    n = len(indices)
    return {
        "schema": "neuromorphic-twin-mnist-11-brian2loihi-suite-v1",
        "prediction_agreement_cases": n,
        "spike_count_vector_agreement_cases": n,
        "exact_trace_agreement_cases": n,
        "project_accuracy_on_scope": 1.0,
        "brian2loihi_accuracy_on_scope": 1.0,
        "cases": [{"mnist_test_index": index} for index in indices],
    }


def _catalyst(indices: list[int]) -> dict[str, object]:
    n = len(indices)
    return {
        "schema": "neuromorphic-twin-mnist-12-catalyst-suite-v1",
        "transport_consistent_cases": n,
        "graph_prediction_agreement_cases": n,
        "graph_spike_vector_agreement_cases": n,
        "delivered_drive_prediction_agreement_cases": n,
        "delivered_drive_spike_vector_agreement_cases": n,
        "cases": [{"mnist_test_index": index} for index in indices],
    }


def test_matched_summary_requires_identical_scope_order(tmp_path: Path) -> None:
    accepted = _write(tmp_path / "accepted.json", _accepted())
    brian = _write(tmp_path / "brian.json", _brian([3, 1]))
    catalyst = _write(tmp_path / "catalyst.json", _catalyst([3, 1]))
    result = build_matched_summary(accepted, brian, catalyst)
    assert result["matched_scope"]["mnist_test_indices"] == [3, 1]
    assert result["project_full_test_context"]["golden_accuracy"] == pytest.approx(0.9171)

    wrong = _write(tmp_path / "catalyst-wrong.json", _catalyst([1, 3]))
    with pytest.raises(ValueError, match="different MNIST index/order scopes"):
        build_matched_summary(accepted, brian, wrong)
