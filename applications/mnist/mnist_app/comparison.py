"""Matched-corpus comparison between float SNN and quantized golden inference."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .config import get_profile
from .dataset import load_mnist
from .inference import evaluate_dataset, load_deployment
from .training import evaluate_float_weights


def summarize_prediction_comparison(
    float_predictions: np.ndarray,
    golden_predictions: np.ndarray,
    labels: np.ndarray,
) -> dict[str, float | int]:
    """Summarize two classifiers evaluated on the exact same labels."""

    float_pred = np.asarray(float_predictions, dtype=np.int64)
    golden_pred = np.asarray(golden_predictions, dtype=np.int64)
    target = np.asarray(labels, dtype=np.int64)
    if float_pred.shape != target.shape or golden_pred.shape != target.shape:
        raise ValueError("prediction and label arrays must have identical shapes")

    count = len(target)
    float_correct = float_pred == target
    golden_correct = golden_pred == target
    agreements = float_pred == golden_pred
    return {
        "images": count,
        "float_accuracy": float(np.mean(float_correct)) if count else 0.0,
        "golden_accuracy": float(np.mean(golden_correct)) if count else 0.0,
        "golden_minus_float_accuracy": (
            float(np.mean(golden_correct) - np.mean(float_correct))
            if count
            else 0.0
        ),
        "prediction_agreement": float(np.mean(agreements)) if count else 0.0,
        "prediction_disagreements": int(np.count_nonzero(~agreements)),
        "float_correct_golden_wrong": int(
            np.count_nonzero(float_correct & ~golden_correct)
        ),
        "float_wrong_golden_correct": int(
            np.count_nonzero(~float_correct & golden_correct)
        ),
    }


def compare_float_checkpoint_to_golden(
    checkpoint_path: str | Path,
    deployment_path: str | Path,
    *,
    limit: int | None = None,
    batch_size: int = 128,
) -> dict[str, object]:
    """Evaluate float and quantized models on the same MNIST test samples."""

    checkpoint = np.load(checkpoint_path)
    checkpoint_profile = str(np.asarray(checkpoint["profile"]).item())
    selected = get_profile(checkpoint_profile)
    weights = np.asarray(checkpoint["weights"], dtype=np.float32)

    runtime = load_deployment(deployment_path)
    if runtime.profile.name != selected.name:
        raise ValueError(
            "checkpoint and deployment profiles do not match: "
            f"{selected.name} != {runtime.profile.name}"
        )

    dataset = load_mnist()
    images, labels = dataset.x_test, dataset.y_test
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive when provided")
        images, labels = images[:limit], labels[:limit]

    (
        float_accuracy,
        float_mean_spikes,
        float_predictions,
        float_incorrect,
    ) = evaluate_float_weights(
        weights,
        images,
        labels,
        profile=selected,
        batch_size=batch_size,
    )
    golden = evaluate_dataset(
        runtime.core,
        images,
        labels,
        profile=selected,
        row_lengths=runtime.row_lengths,
    )
    golden_predictions = np.asarray(golden["predictions"], dtype=np.int64)
    summary = summarize_prediction_comparison(
        float_predictions,
        golden_predictions,
        labels,
    )
    summary.update(
        {
            "profile": selected.name,
            "float_accuracy": float_accuracy,
            "float_mean_output_spikes": float_mean_spikes,
            "float_incorrect_predictions": int(len(float_incorrect)),
            "golden_accuracy": float(golden["accuracy"]),
            "golden_mean_output_spikes": float(golden["mean_output_spikes"]),
            "golden_mean_input_events": float(golden["mean_input_events"]),
            "golden_mean_synaptic_visits": golden["mean_synaptic_visits"],
            "golden_no_spike_images": int(golden["no_spike_images"]),
            "golden_tied_winner_images": int(golden["tied_winner_images"]),
            "deployment_nonzero_synapses": int(
                runtime.manifest["quantization"]["nonzero_synapses"]
            ),
        }
    )
    return summary
