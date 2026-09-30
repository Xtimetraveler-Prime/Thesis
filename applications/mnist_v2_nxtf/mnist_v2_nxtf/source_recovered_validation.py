"""P08.3.5d validation-only execution of the accepted source-recovered SNN.

This gate is the first classification-accuracy measurement after P08.3.5b/c
recovered the public NxTF/SNN-Toolbox conversion semantics.  It consumes only
the frozen 5,000-example validation partition from the MNIST training split.
The official 10,000-example test split is intentionally unreachable here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .accepted_ann import ACCEPTED_ANN_VAL_ACCURACY
from .policy import CONVERSION_POLICY, OFFICIAL_TEST_POLICY
from .source_backend_reconstruction import SOURCE_INPUT_SCALE, _build_activity_simulator
from .source_recovered_conversion import (
    SOFTMAX_READOUT_MODE,
    SOURCE_RECOVERED_MANIFEST,
    SOURCE_RECOVERED_PARAMETERS,
    _arrays_fingerprint,
)
from .training import _array_identity, prepare_full_training_arrays

VALIDATION_SCHEMA = "p08-source-recovered-validation-v1"
VALIDATION_MANIFEST = "source_recovered_validation_manifest.json"
VALIDATION_RESULTS = "source_recovered_validation_results.npz"
VALIDATION_EXAMPLES = 5_000
VALIDATION_TIMESTEPS = 100
DEFAULT_BATCH_SIZE = 128

ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT = (
    "9169939821201e4764813dbb17e254b796cd952e4707315eb61ecd0e0082926e"
)
ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT = (
    "6e47dc0c37d2f05828f0a0231406c7df8e4bf83652300fde0df1a0b8f9d83f13"
)
ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT = (
    "5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b"
)
ACCEPTED_HIDDEN_THRESHOLDS = (556, 512, 672)
ACCEPTED_INPUT_THRESHOLD = 2040


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _results_fingerprint(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        digest.update(_array_identity(np.asarray(array)))
    return digest.hexdigest()


def _load_accepted_conversion(conversion_dir: str | Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    root = Path(conversion_dir)
    manifest_path = root / SOURCE_RECOVERED_MANIFEST
    parameters_path = root / SOURCE_RECOVERED_PARAMETERS
    if not manifest_path.is_file():
        raise FileNotFoundError(f"accepted P08.3.5c manifest is missing: {manifest_path}")
    if not parameters_path.is_file():
        raise FileNotFoundError(f"accepted P08.3.5c parameters are missing: {parameters_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
        "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
        "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
        "input_threshold": ACCEPTED_INPUT_THRESHOLD,
        "hidden_thresholds": list(ACCEPTED_HIDDEN_THRESHOLDS),
        "softmax_readout_mode": SOFTMAX_READOUT_MODE,
        "official_test_used": False,
        "test_examples_observed": 0,
    }
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise AssertionError(
                f"P08.3.5d requires accepted P08.3.5c {key}={expected!r}; "
                f"observed {manifest.get(key)!r}"
            )

    with np.load(parameters_path, allow_pickle=False) as payload:
        parameters = {name: np.asarray(payload[name]) for name in payload.files}
    observed = _arrays_fingerprint(parameters)
    if observed != ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT:
        raise AssertionError(
            "P08.3.5c parameter artifact does not reproduce its accepted fingerprint"
        )
    return parameters, manifest


def _input_bias_frames(images: np.ndarray) -> tuple[np.ndarray, float]:
    """Apply the recovered NxTF frame-input scaling once to the full corpus."""

    values = np.asarray(images, dtype=np.float32)
    if values.shape != (VALIDATION_EXAMPLES, 28, 28, 1):
        raise AssertionError(f"validation image shape drifted: {values.shape}")
    global_max = float(np.max(values))
    if not np.isfinite(global_max) or global_max <= 0.0:
        raise ValueError("validation corpus has no positive finite pixel maximum")
    # Mirrors public NxTF set_inputs(): normalize the supplied frame corpus by
    # its maximum, multiply by 255, then cast to integer (toward zero).
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
        raise AssertionError("validation split unexpectedly lacks an MNIST class")
    return np.diag(confusion).astype(np.float64) / totals.astype(np.float64)


def run_source_recovered_validation(
    conversion_dir: str | Path,
    output_dir: str | Path,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if CONVERSION_POLICY.primary_timesteps != VALIDATION_TIMESTEPS:
        raise AssertionError("P08.3.5d requires the frozen 100-timestep horizon")

    parameters, conversion_manifest = _load_accepted_conversion(conversion_dir)
    arrays = prepare_full_training_arrays()
    if len(arrays.x_validation) != VALIDATION_EXAMPLES:
        raise AssertionError("P08.3.5d requires exactly 5,000 validation examples")
    labels = np.argmax(arrays.y_validation, axis=1).astype(np.int64)
    pixel_bias, input_global_max = _input_bias_frames(arrays.x_validation)

    simulator = _build_activity_simulator(parameters, VALIDATION_TIMESTEPS)
    evidence_parts: list[np.ndarray] = []
    total_spikes = np.zeros(4, dtype=np.int64)
    active_examples = np.zeros(4, dtype=np.int64)
    first_spike_ticks = np.full(4, -1, dtype=np.int64)
    max_candidates = np.full(4, np.iinfo(np.int64).min, dtype=np.int64)

    for start in range(0, VALIDATION_EXAMPLES, batch_size):
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
    if evidence.shape != (VALIDATION_EXAMPLES, 10):
        raise AssertionError(f"final evidence shape drifted: {evidence.shape}")
    if not np.all(np.isfinite(evidence)):
        raise AssertionError("non-finite final membrane evidence observed")

    predictions = np.argmax(evidence, axis=1).astype(np.int64)
    maxima = np.max(evidence, axis=1, keepdims=True)
    tie_widths = np.sum(evidence == maxima, axis=1)
    ties = int(np.count_nonzero(tie_widths > 1))
    all_equal = int(np.count_nonzero(tie_widths == 10))
    zero_evidence = int(np.count_nonzero(np.all(evidence == 0, axis=1)))
    correct = int(np.count_nonzero(predictions == labels))
    accuracy = float(correct / VALIDATION_EXAMPLES)
    confusion = _confusion_matrix(labels, predictions)
    class_accuracy = _class_accuracy(confusion)

    # This is not an accuracy acceptance threshold. It only rejects the exact
    # degenerate failure mode that triggered P08.3.5/5a (no propagated output
    # evidence for the entire validation corpus).
    if np.all(total_spikes[1:4] <= 0):
        raise RuntimeError("source-recovered hidden network produced no spikes")
    if all_equal == VALIDATION_EXAMPLES:
        raise RuntimeError("source-recovered readout evidence is degenerate for every example")

    prediction_fingerprint = _results_fingerprint(labels, predictions)
    evidence_fingerprint = _results_fingerprint(evidence)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    results_path = output / VALIDATION_RESULTS
    np.savez_compressed(
        results_path,
        labels=labels,
        predictions=predictions,
        final_evidence=evidence.astype(np.int64),
        confusion_matrix=confusion,
        class_accuracy=class_accuracy,
        stage_total_spikes=total_spikes,
        stage_active_examples=active_examples,
        first_spike_ticks=first_spike_ticks,
        max_candidate_values=max_candidates,
    )

    manifest: dict[str, Any] = {
        "schema": VALIDATION_SCHEMA,
        "status": "P08_3_5D_SOURCE_RECOVERED_VALIDATION_REVIEW_PENDING",
        "official_test_policy": OFFICIAL_TEST_POLICY,
        "official_test_used": False,
        "test_examples_observed": 0,
        "validation_examples": VALIDATION_EXAMPLES,
        "timesteps": VALIDATION_TIMESTEPS,
        "batch_size_execution_only": int(batch_size),
        "validation_input_scaling_scope": "full_5000_validation_corpus_once_before_batching",
        "validation_input_global_max": input_global_max,
        "input_scale": SOURCE_INPUT_SCALE,
        "input_threshold": ACCEPTED_INPUT_THRESHOLD,
        "hidden_thresholds": list(ACCEPTED_HIDDEN_THRESHOLDS),
        "softmax_readout_mode": SOFTMAX_READOUT_MODE,
        "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
        "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
        "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
        "conversion_manifest_fingerprint": conversion_manifest["manifest_fingerprint"],
        "split_fingerprint": arrays.split_fingerprint,
        "dataset_fingerprint": arrays.dataset_fingerprint,
        "correct": correct,
        "accuracy": accuracy,
        "ann_validation_reference_accuracy": float(ACCEPTED_ANN_VAL_ACCURACY),
        "ann_minus_snn_validation_accuracy": float(ACCEPTED_ANN_VAL_ACCURACY - accuracy),
        "accuracy_acceptance_threshold": None,
        "post_conversion_accuracy_tuning": False,
        "ties": ties,
        "all_equal_evidence_examples": all_equal,
        "zero_evidence_examples": zero_evidence,
        "evidence_min": int(np.min(evidence)),
        "evidence_max": int(np.max(evidence)),
        "prediction_fingerprint": prediction_fingerprint,
        "evidence_fingerprint": evidence_fingerprint,
        "confusion_matrix": confusion.tolist(),
        "class_accuracy": [float(value) for value in class_accuracy],
        "stage_names": ["input", "conv1", "conv2", "conv3"],
        "stage_total_spikes": [int(value) for value in total_spikes],
        "stage_active_examples": [int(value) for value in active_examples],
        "first_spike_ticks": [int(value) for value in first_spike_ticks],
        "max_candidate_values": [int(value) for value in max_candidates],
        "classification_accuracy_evaluated": True,
        "classification_selection_source": "frozen_validation_partition_measurement_only",
    }
    manifest["manifest_fingerprint"] = _json_fingerprint(manifest)
    (output / VALIDATION_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run P08.3.5d source-recovered validation-only SNN measurement"
    )
    parser.add_argument("--conversion-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = run_source_recovered_validation(
        args.conversion_dir,
        args.output_dir,
        batch_size=args.batch_size,
    )
    print(
        "PASS: P08.3.5d source-recovered validation "
        f"examples={manifest['validation_examples']} timesteps={manifest['timesteps']} "
        f"accuracy={manifest['accuracy']:.6f} "
        f"ann_reference={manifest['ann_validation_reference_accuracy']:.6f} "
        f"delta={manifest['ann_minus_snn_validation_accuracy']:.6f}"
    )
    print(
        "PASS: P08.3.5d readout evidence "
        f"ties={manifest['ties']} all_equal={manifest['all_equal_evidence_examples']} "
        f"zero={manifest['zero_evidence_examples']} "
        f"range=[{manifest['evidence_min']},{manifest['evidence_max']}]"
    )
    totals = manifest["stage_total_spikes"]
    active = manifest["stage_active_examples"]
    print(
        "PASS: P08.3.5d hidden activity "
        f"input={totals[0]} conv1={totals[1]} conv2={totals[2]} conv3={totals[3]} "
        f"active_examples={active}"
    )
    print(
        "PASS: P08.3.5d artifact identities "
        f"parameters={manifest['parameter_fingerprint']} "
        f"network={manifest['network_fingerprint']} compiled={manifest['compiled_fingerprint']}"
    )
    print(
        "PASS: P08.3.5d deterministic results "
        f"predictions={manifest['prediction_fingerprint']} "
        f"evidence={manifest['evidence_fingerprint']}"
    )
    print(
        "PASS: P08.3.5d measurement policy accuracy_threshold=none "
        "post_conversion_tuning=false"
    )
    print(
        "PASS: P08.3.5d test lock official_test_used=false "
        "test_examples_observed=0 validation_examples=5000"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
