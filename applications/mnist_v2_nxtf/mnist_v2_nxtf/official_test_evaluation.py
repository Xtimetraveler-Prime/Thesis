"""P08.4.1 frozen ANN/SNN evaluation on the untouched official MNIST test split.

This module is intentionally downstream of the accepted P08.3 freeze.  It may
observe the official 10,000-image MNIST test split, but it may not change the
accepted checkpoint, conversion parameters, thresholds, readout, or timestep
horizon in response to the result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .accepted_ann import (
    ACCEPTED_ANN_CHECKPOINT_SHA256,
    ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
    validate_accepted_checkpoint,
)
from .data import load_mnist, normalize_images
from .policy import CONVERSION_POLICY, OFFICIAL_TEST_POLICY
from .source_backend_reconstruction import SOURCE_INPUT_SCALE, _build_activity_simulator
from .source_recovered_conversion import SOFTMAX_READOUT_MODE
from .source_recovered_validation import (
    ACCEPTED_HIDDEN_THRESHOLDS,
    ACCEPTED_INPUT_THRESHOLD,
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    _load_accepted_conversion,
    _results_fingerprint,
)
from .training import _array_identity

OFFICIAL_TEST_SCHEMA = "p08-official-test-evaluation-v1"
OFFICIAL_TEST_MANIFEST = "official_test_evaluation_manifest.json"
OFFICIAL_TEST_RESULTS = "official_test_evaluation_results.npz"
OFFICIAL_TEST_EXAMPLES = 10_000
OFFICIAL_TEST_TIMESTEPS = 100
DEFAULT_BATCH_SIZE = 128
P08_3_ACCEPTANCE_STATUS = "P08_3_ACCEPTED_OFFICIAL_TEST_UNLOCKED"


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dataset_fingerprint(images: np.ndarray, labels: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(_array_identity(np.asarray(images)))
    digest.update(_array_identity(np.asarray(labels)))
    return digest.hexdigest()


def _input_bias_frames(
    images: np.ndarray,
    *,
    expected_examples: int = OFFICIAL_TEST_EXAMPLES,
) -> tuple[np.ndarray, float]:
    """Apply recovered NxTF frame scaling once to the complete evaluation corpus."""

    values = np.asarray(images, dtype=np.float32)
    expected_shape = (expected_examples, 28, 28, 1)
    if values.shape != expected_shape:
        raise AssertionError(f"official-test image shape drifted: {values.shape} != {expected_shape}")
    global_max = float(np.max(values))
    if not np.isfinite(global_max) or global_max <= 0.0:
        raise ValueError("official-test corpus has no positive finite pixel maximum")
    encoded = (values / global_max * SOURCE_INPUT_SCALE).astype(np.int32)
    if encoded.min() < 0 or encoded.max() > SOURCE_INPUT_SCALE:
        raise AssertionError("8-bit BIAS input encoding escaped [0,255]")
    return encoded, global_max


def _confusion_matrix(labels: np.ndarray, predictions: np.ndarray) -> np.ndarray:
    matrix = np.zeros((10, 10), dtype=np.int64)
    np.add.at(matrix, (labels.astype(np.int64), predictions.astype(np.int64)), 1)
    return matrix


def _class_accuracy(confusion: np.ndarray) -> np.ndarray:
    totals = confusion.sum(axis=1)
    if np.any(totals <= 0):
        raise AssertionError("official test split unexpectedly lacks an MNIST class")
    return np.diag(confusion).astype(np.float64) / totals.astype(np.float64)


def _ann_predictions(model, images: np.ndarray, *, batch_size: int) -> np.ndarray:
    outputs = model.predict(images, batch_size=batch_size, verbose=0)
    values = np.asarray(outputs)
    if values.shape != (OFFICIAL_TEST_EXAMPLES, 10):
        raise AssertionError(f"ANN output shape drifted: {values.shape}")
    if not np.all(np.isfinite(values)):
        raise AssertionError("ANN produced non-finite official-test outputs")
    return np.argmax(values, axis=1).astype(np.int64)


def _run_snn(
    parameters: dict[str, np.ndarray],
    pixel_bias: np.ndarray,
    *,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    simulator = _build_activity_simulator(parameters, OFFICIAL_TEST_TIMESTEPS)
    evidence_parts: list[np.ndarray] = []
    total_spikes = np.zeros(4, dtype=np.int64)
    active_examples = np.zeros(4, dtype=np.int64)
    first_spike_ticks = np.full(4, -1, dtype=np.int64)
    max_candidates = np.full(4, np.iinfo(np.int64).min, dtype=np.int64)

    for start in range(0, OFFICIAL_TEST_EXAMPLES, batch_size):
        batch = pixel_bias[start : start + batch_size]
        totals_t, active_t, first_t, maxima_t, evidence_t = simulator(batch)
        totals = np.asarray(totals_t.numpy(), dtype=np.int64)
        active = np.asarray(active_t.numpy(), dtype=np.int64)
        first = np.asarray(first_t.numpy(), dtype=np.int64)
        maxima = np.asarray(maxima_t.numpy(), dtype=np.int64)
        evidence = np.asarray(evidence_t.numpy(), dtype=np.int64)

        total_spikes += totals
        active_examples += active
        max_candidates = np.maximum(max_candidates, maxima)
        for index, tick in enumerate(first):
            if tick >= 0 and (first_spike_ticks[index] < 0 or tick < first_spike_ticks[index]):
                first_spike_ticks[index] = tick
        evidence_parts.append(evidence)

    evidence = np.concatenate(evidence_parts, axis=0)
    if evidence.shape != (OFFICIAL_TEST_EXAMPLES, 10):
        raise AssertionError(f"SNN final evidence shape drifted: {evidence.shape}")
    predictions = np.argmax(evidence, axis=1).astype(np.int64)
    return predictions, evidence, total_spikes, active_examples, first_spike_ticks


def run_official_test_evaluation(
    checkpoint_path: str | Path,
    training_manifest_path: str | Path,
    conversion_dir: str | Path,
    output_dir: str | Path,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if CONVERSION_POLICY.primary_timesteps != OFFICIAL_TEST_TIMESTEPS:
        raise AssertionError("P08.4.1 requires the frozen 100-timestep horizon")

    # Artifact identity checks happen before the official test split is loaded.
    model, training_manifest = validate_accepted_checkpoint(
        checkpoint_path, training_manifest_path
    )
    parameters, conversion_manifest = _load_accepted_conversion(conversion_dir)

    dataset = load_mnist()
    if dataset.x_test.shape != (OFFICIAL_TEST_EXAMPLES, 28, 28):
        raise AssertionError(f"official MNIST test image shape drifted: {dataset.x_test.shape}")
    if dataset.y_test.shape != (OFFICIAL_TEST_EXAMPLES,):
        raise AssertionError(f"official MNIST test label shape drifted: {dataset.y_test.shape}")
    if np.any(dataset.y_test < 0) or np.any(dataset.y_test > 9):
        raise AssertionError("official MNIST test labels escaped 0..9")

    labels = np.asarray(dataset.y_test, dtype=np.int64)
    normalized = normalize_images(dataset.x_test)[..., np.newaxis]
    pixel_bias, input_global_max = _input_bias_frames(normalized)
    test_dataset_fingerprint = _dataset_fingerprint(dataset.x_test, labels)

    ann_predictions = _ann_predictions(model, normalized, batch_size=batch_size)
    snn_predictions, evidence, total_spikes, active_examples, first_spike_ticks = _run_snn(
        parameters, pixel_bias, batch_size=batch_size
    )

    ann_correct = int(np.count_nonzero(ann_predictions == labels))
    snn_correct = int(np.count_nonzero(snn_predictions == labels))
    ann_accuracy = float(ann_correct / OFFICIAL_TEST_EXAMPLES)
    snn_accuracy = float(snn_correct / OFFICIAL_TEST_EXAMPLES)

    maxima = np.max(evidence, axis=1, keepdims=True)
    tie_widths = np.sum(evidence == maxima, axis=1)
    ties = int(np.count_nonzero(tie_widths > 1))
    all_equal = int(np.count_nonzero(tie_widths == 10))
    zero_evidence = int(np.count_nonzero(np.all(evidence == 0, axis=1)))
    if np.all(total_spikes[1:4] <= 0):
        raise RuntimeError("accepted source-recovered SNN produced no hidden spikes on test")
    if all_equal == OFFICIAL_TEST_EXAMPLES:
        raise RuntimeError("accepted source-recovered SNN readout is degenerate on all test examples")

    ann_confusion = _confusion_matrix(labels, ann_predictions)
    snn_confusion = _confusion_matrix(labels, snn_predictions)
    ann_class_accuracy = _class_accuracy(ann_confusion)
    snn_class_accuracy = _class_accuracy(snn_confusion)

    both_correct = int(np.count_nonzero((ann_predictions == labels) & (snn_predictions == labels)))
    ann_only_correct = int(np.count_nonzero((ann_predictions == labels) & (snn_predictions != labels)))
    snn_only_correct = int(np.count_nonzero((ann_predictions != labels) & (snn_predictions == labels)))
    both_wrong = OFFICIAL_TEST_EXAMPLES - both_correct - ann_only_correct - snn_only_correct

    labels_fingerprint = _results_fingerprint(labels)
    ann_prediction_fingerprint = _results_fingerprint(labels, ann_predictions)
    snn_prediction_fingerprint = _results_fingerprint(labels, snn_predictions)
    evidence_fingerprint = _results_fingerprint(evidence)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output / OFFICIAL_TEST_RESULTS,
        labels=labels,
        ann_predictions=ann_predictions,
        snn_predictions=snn_predictions,
        snn_final_evidence=evidence.astype(np.int64),
        ann_confusion_matrix=ann_confusion,
        snn_confusion_matrix=snn_confusion,
        ann_class_accuracy=ann_class_accuracy,
        snn_class_accuracy=snn_class_accuracy,
        stage_total_spikes=total_spikes,
        stage_active_examples=active_examples,
        first_spike_ticks=first_spike_ticks,
    )

    manifest: dict[str, Any] = {
        "schema": OFFICIAL_TEST_SCHEMA,
        "status": "P08_4_1_OFFICIAL_TEST_REVIEW_PENDING",
        "p08_3_acceptance_status": P08_3_ACCEPTANCE_STATUS,
        "official_test_policy": OFFICIAL_TEST_POLICY,
        "official_test_used": True,
        "test_examples_observed": OFFICIAL_TEST_EXAMPLES,
        "evaluation_only_no_selection": True,
        "selection_decisions_after_test": 0,
        "post_test_training": False,
        "post_test_conversion_tuning": False,
        "post_test_threshold_tuning": False,
        "post_test_decoder_tuning": False,
        "post_test_timestep_tuning": False,
        "test_dataset_fingerprint": test_dataset_fingerprint,
        "labels_fingerprint": labels_fingerprint,
        "accepted_ann_checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
        "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
        "accepted_training_manifest_fingerprint": training_manifest["manifest_fingerprint"],
        "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
        "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
        "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
        "conversion_manifest_fingerprint": conversion_manifest["manifest_fingerprint"],
        "timesteps": OFFICIAL_TEST_TIMESTEPS,
        "batch_size_execution_only": int(batch_size),
        "test_input_scaling_scope": "full_10000_official_test_corpus_once_before_batching",
        "test_input_global_max": input_global_max,
        "input_scale": SOURCE_INPUT_SCALE,
        "input_threshold": ACCEPTED_INPUT_THRESHOLD,
        "hidden_thresholds": list(ACCEPTED_HIDDEN_THRESHOLDS),
        "softmax_readout_mode": SOFTMAX_READOUT_MODE,
        "ann_correct": ann_correct,
        "ann_accuracy": ann_accuracy,
        "snn_correct": snn_correct,
        "snn_accuracy": snn_accuracy,
        "ann_minus_snn_accuracy": float(ann_accuracy - snn_accuracy),
        "accuracy_acceptance_threshold": None,
        "snn_ties": ties,
        "snn_all_equal_evidence_examples": all_equal,
        "snn_zero_evidence_examples": zero_evidence,
        "snn_evidence_min": int(np.min(evidence)),
        "snn_evidence_max": int(np.max(evidence)),
        "both_correct": both_correct,
        "ann_only_correct": ann_only_correct,
        "snn_only_correct": snn_only_correct,
        "both_wrong": both_wrong,
        "ann_prediction_fingerprint": ann_prediction_fingerprint,
        "snn_prediction_fingerprint": snn_prediction_fingerprint,
        "snn_evidence_fingerprint": evidence_fingerprint,
        "ann_confusion_matrix": ann_confusion.tolist(),
        "snn_confusion_matrix": snn_confusion.tolist(),
        "ann_class_accuracy": [float(value) for value in ann_class_accuracy],
        "snn_class_accuracy": [float(value) for value in snn_class_accuracy],
        "stage_names": ["input", "conv1", "conv2", "conv3"],
        "stage_total_spikes": [int(value) for value in total_spikes],
        "stage_active_examples": [int(value) for value in active_examples],
        "first_spike_ticks": [int(value) for value in first_spike_ticks],
    }
    manifest["manifest_fingerprint"] = _json_fingerprint(manifest)
    (output / OFFICIAL_TEST_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run P08.4.1 frozen ANN/SNN official MNIST test evaluation"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--training-manifest", required=True)
    parser.add_argument("--conversion-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = run_official_test_evaluation(
        args.checkpoint,
        args.training_manifest,
        args.conversion_dir,
        args.output_dir,
        batch_size=args.batch_size,
    )
    print(
        "PASS: P08.4.1 official test accuracy "
        f"examples={manifest['test_examples_observed']} "
        f"ann={manifest['ann_accuracy']:.6f} snn={manifest['snn_accuracy']:.6f} "
        f"delta={manifest['ann_minus_snn_accuracy']:.6f} timesteps={manifest['timesteps']}"
    )
    print(
        "PASS: P08.4.1 SNN readout "
        f"ties={manifest['snn_ties']} all_equal={manifest['snn_all_equal_evidence_examples']} "
        f"zero={manifest['snn_zero_evidence_examples']} "
        f"range=[{manifest['snn_evidence_min']},{manifest['snn_evidence_max']}]"
    )
    totals = manifest["stage_total_spikes"]
    active = manifest["stage_active_examples"]
    print(
        "PASS: P08.4.1 SNN activity "
        f"input={totals[0]} conv1={totals[1]} conv2={totals[2]} conv3={totals[3]} "
        f"active_examples={active}"
    )
    print(
        "PASS: P08.4.1 agreement "
        f"both_correct={manifest['both_correct']} ann_only={manifest['ann_only_correct']} "
        f"snn_only={manifest['snn_only_correct']} both_wrong={manifest['both_wrong']}"
    )
    print(
        "PASS: P08.4.1 artifact identities "
        f"ann={manifest['accepted_ann_weights_fingerprint']} "
        f"parameters={manifest['parameter_fingerprint']} "
        f"network={manifest['network_fingerprint']} compiled={manifest['compiled_fingerprint']}"
    )
    print(
        "PASS: P08.4.1 deterministic results "
        f"ann_predictions={manifest['ann_prediction_fingerprint']} "
        f"snn_predictions={manifest['snn_prediction_fingerprint']} "
        f"evidence={manifest['snn_evidence_fingerprint']}"
    )
    print(
        "PASS: P08.4.1 test-use boundary official_test_used=true "
        "test_examples_observed=10000 selection_decisions_after_test=0 "
        "post_test_tuning=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
