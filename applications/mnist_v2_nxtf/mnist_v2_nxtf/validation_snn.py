"""P08.3.5 validation-only execution of the accepted converted SNN.

The official MNIST test split is intentionally absent. This module consumes the
frozen 5,000-image validation partition from the official 60k training split and
the exact accepted P08.3.4 conversion artifact.

Execution uses a vectorized TensorFlow implementation of the accepted FPGA-v2
compatibility profile. For the frozen P08 neuron parameters
(current_decay=4096, voltage_decay=0, reset=0, refractory=0), each compartment
reduces exactly to integer integrate-and-fire with hard reset. Synaptic spikes
from one convolutional stage arrive at the next stage one algorithmic tick
later, matching the logical packet-routing contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .accepted_ann import ACCEPTED_ANN_BEST_VAL_ACCURACY
from .accepted_conversion import (
    ACCEPTED_COMPILED_FINGERPRINT,
    ACCEPTED_CONVERSION_FINGERPRINT,
    ACCEPTED_NETWORK_FINGERPRINT,
    validate_accepted_conversion,
)
from .policy import CONVERSION_POLICY, OFFICIAL_TEST_POLICY
from .training import prepare_full_training_arrays


VALIDATION_SCHEMA = "p08-snn-validation-v1"
VALIDATION_MANIFEST_FILENAME = "validation_manifest.json"
VALIDATION_PREDICTIONS_FILENAME = "validation_predictions.npz"
RATE_ENCODER = "zero_phase_bresenham_exact_count"


def _array_identity(array: np.ndarray) -> bytes:
    value = np.ascontiguousarray(array)
    header = json.dumps(
        {"shape": value.shape, "dtype": str(value.dtype)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return header + b"\0" + value.tobytes(order="C")


def _arrays_fingerprint(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        digest.update(_array_identity(array))
    return digest.hexdigest()


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def rate_spike_counts(images: np.ndarray, timesteps: int) -> np.ndarray:
    """Map normalized pixels in [0,1] to an exact deterministic spike count."""

    values = np.asarray(images, dtype=np.float64)
    if timesteps <= 0:
        raise ValueError("timesteps must be positive")
    if np.any(values < 0.0) or np.any(values > 1.0):
        raise ValueError("rate encoder expects normalized pixels in [0,1]")
    counts = np.floor(values * float(timesteps) + 0.5).astype(np.int32)
    return np.clip(counts, 0, timesteps)


def rate_spikes_at_tick(counts: np.ndarray, tick: int, timesteps: int) -> np.ndarray:
    """Zero-phase Bresenham schedule with exactly ``counts`` spikes per source."""

    if not 0 <= tick < timesteps:
        raise ValueError("tick is outside the encoded horizon")
    values = np.asarray(counts, dtype=np.int64)
    before = (tick * values) // timesteps
    after = ((tick + 1) * values) // timesteps
    return after > before


def compartment_update(
    voltage: np.ndarray,
    synaptic_input: np.ndarray,
    bias: np.ndarray | int,
    threshold: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorized form of the frozen P08 FPGA-v2 compartment step."""

    candidate = (
        np.asarray(voltage, dtype=np.int64)
        + np.asarray(synaptic_input, dtype=np.int64)
        + np.asarray(bias, dtype=np.int64)
    )
    spikes = candidate > int(threshold)
    next_voltage = np.where(spikes, 0, candidate).astype(np.int64)
    return next_voltage, spikes


def _build_tf_simulator(parameters: dict[str, np.ndarray], timesteps: int):
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("TensorFlow is required for P08.3.5 SNN validation") from exc

    threshold = int(CONVERSION_POLICY.threshold_mantissa)
    weights = [
        tf.constant(parameters[f"conv{i}_kernel_integer"].astype(np.float32))
        for i in range(1, 5)
    ]
    biases = [
        tf.constant(parameters[f"conv{i}_bias_integer"].astype(np.int32))
        for i in range(1, 5)
    ]
    strides = (2, 1, 2, 1)

    @tf.function(
        input_signature=[tf.TensorSpec(shape=[None, 28, 28, 1], dtype=tf.int32)],
        reduce_retracing=True,
    )
    def simulate(encoded_counts):
        batch = tf.shape(encoded_counts)[0]
        v1 = tf.zeros([batch, 12, 12, 14], dtype=tf.int32)
        v2 = tf.zeros([batch, 10, 10, 20], dtype=tf.int32)
        v3 = tf.zeros([batch, 4, 4, 12], dtype=tf.int32)
        v4 = tf.zeros([batch, 1, 1, 10], dtype=tf.int32)
        p1 = tf.zeros_like(v1, dtype=tf.bool)
        p2 = tf.zeros_like(v2, dtype=tf.bool)
        p3 = tf.zeros_like(v3, dtype=tf.bool)
        output_counts = tf.zeros([batch, 10], dtype=tf.int32)

        for tick in tf.range(timesteps):
            before = tf.math.floordiv(tick * encoded_counts, timesteps)
            after = tf.math.floordiv((tick + 1) * encoded_counts, timesteps)
            input_spikes = tf.cast(after > before, tf.float32)

            syn1 = tf.cast(
                tf.nn.conv2d(
                    input_spikes,
                    weights[0],
                    strides=[1, strides[0], strides[0], 1],
                    padding="VALID",
                ),
                tf.int32,
            )
            syn2 = tf.cast(
                tf.nn.conv2d(
                    tf.cast(p1, tf.float32),
                    weights[1],
                    strides=[1, strides[1], strides[1], 1],
                    padding="VALID",
                ),
                tf.int32,
            )
            syn3 = tf.cast(
                tf.nn.conv2d(
                    tf.cast(p2, tf.float32),
                    weights[2],
                    strides=[1, strides[2], strides[2], 1],
                    padding="VALID",
                ),
                tf.int32,
            )
            syn4 = tf.cast(
                tf.nn.conv2d(
                    tf.cast(p3, tf.float32),
                    weights[3],
                    strides=[1, strides[3], strides[3], 1],
                    padding="VALID",
                ),
                tf.int32,
            )

            c1 = v1 + syn1 + biases[0]
            c2 = v2 + syn2 + biases[1]
            c3 = v3 + syn3 + biases[2]
            c4 = v4 + syn4 + biases[3]
            s1 = c1 > threshold
            s2 = c2 > threshold
            s3 = c3 > threshold
            s4 = c4 > threshold
            v1 = tf.where(s1, tf.zeros_like(c1), c1)
            v2 = tf.where(s2, tf.zeros_like(c2), c2)
            v3 = tf.where(s3, tf.zeros_like(c3), c3)
            v4 = tf.where(s4, tf.zeros_like(c4), c4)
            p1, p2, p3 = s1, s2, s3
            output_counts += tf.cast(tf.reshape(s4, [batch, 10]), tf.int32)

        return output_counts

    return simulate


def evaluate_validation(
    conversion_dir: str | Path,
    output_dir: str | Path,
    *,
    batch_size: int = 500,
) -> dict[str, Any]:
    """Evaluate the full frozen 5,000-image validation split at 100 timesteps."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if CONVERSION_POLICY.primary_timesteps != 100:
        raise AssertionError("P08.3.5 primary horizon must remain exactly 100 timesteps")
    if CONVERSION_POLICY.current_decay != 4096:
        raise AssertionError("vectorized P08.3.5 path requires current_decay=4096")
    if CONVERSION_POLICY.voltage_decay != 0:
        raise AssertionError("vectorized P08.3.5 path requires voltage_decay=0")
    if CONVERSION_POLICY.reset_voltage != 0 or CONVERSION_POLICY.refractory_ticks != 0:
        raise AssertionError("vectorized P08.3.5 path requires zero reset/refractory profile")

    parameters, conversion_manifest = validate_accepted_conversion(conversion_dir)
    arrays = prepare_full_training_arrays()
    x_validation = arrays.x_validation
    labels = np.argmax(arrays.y_validation, axis=1).astype(np.int16)
    if x_validation.shape != (5000, 28, 28, 1) or labels.shape != (5000,):
        raise AssertionError("frozen validation split shape drifted")

    timesteps = CONVERSION_POLICY.primary_timesteps
    encoded = rate_spike_counts(x_validation, timesteps)
    simulator = _build_tf_simulator(parameters, timesteps)
    all_counts: list[np.ndarray] = []
    for start in range(0, len(encoded), batch_size):
        batch = encoded[start : start + batch_size]
        counts = np.asarray(simulator(batch).numpy(), dtype=np.int16)
        all_counts.append(counts)
    spike_counts = np.concatenate(all_counts, axis=0)
    if spike_counts.shape != (5000, 10):
        raise AssertionError(f"unexpected SNN output shape: {spike_counts.shape}")

    predictions = np.argmax(spike_counts, axis=1).astype(np.int16)
    correct = predictions == labels
    accuracy = float(np.mean(correct))
    maxima = np.max(spike_counts, axis=1, keepdims=True)
    ties = np.sum(np.sum(spike_counts == maxima, axis=1) > 1)
    silent = np.sum(np.sum(spike_counts, axis=1) == 0)
    total_output_spikes = int(np.sum(spike_counts, dtype=np.int64))

    confusion = np.zeros((10, 10), dtype=np.int32)
    np.add.at(confusion, (labels, predictions), 1)
    class_totals = confusion.sum(axis=1)
    class_correct = np.diag(confusion)
    class_accuracy = np.divide(
        class_correct,
        class_totals,
        out=np.zeros(10, dtype=np.float64),
        where=class_totals != 0,
    )

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    predictions_path = output / VALIDATION_PREDICTIONS_FILENAME
    np.savez_compressed(
        predictions_path,
        labels=labels,
        predictions=predictions,
        output_spike_counts=spike_counts,
        confusion_matrix=confusion,
    )
    predictions_fingerprint = _arrays_fingerprint(
        labels, predictions, spike_counts, confusion
    )

    manifest: dict[str, Any] = {
        "schema": VALIDATION_SCHEMA,
        "status": "P08_3_5_VALIDATION_MEASURED_REVIEW_PENDING",
        "official_test_policy": OFFICIAL_TEST_POLICY,
        "official_test_used": False,
        "test_examples_observed": 0,
        "validation_examples": 5000,
        "validation_split_fingerprint": arrays.split_fingerprint,
        "validation_dataset_fingerprint": arrays.dataset_fingerprint,
        "accepted_conversion_fingerprint": ACCEPTED_CONVERSION_FINGERPRINT,
        "accepted_network_fingerprint": ACCEPTED_NETWORK_FINGERPRINT,
        "accepted_compiled_fingerprint": ACCEPTED_COMPILED_FINGERPRINT,
        "conversion_manifest_fingerprint": conversion_manifest.get("manifest_fingerprint"),
        "timesteps": timesteps,
        "pipeline_flush_timesteps": 0,
        "input_encoder": RATE_ENCODER,
        "input_spike_count_rule": "floor(normalized_pixel * timesteps + 0.5)",
        "input_schedule_rule": "floor((t+1)*count/T) > floor(t*count/T)",
        "decoder": CONVERSION_POLICY.decoder,
        "decoder_tie_break": CONVERSION_POLICY.decoder_tie_break,
        "ann_validation_accuracy_reference": ACCEPTED_ANN_BEST_VAL_ACCURACY,
        "snn_validation_accuracy": accuracy,
        "ann_minus_snn_accuracy": ACCEPTED_ANN_BEST_VAL_ACCURACY - accuracy,
        "tie_examples": int(ties),
        "silent_examples": int(silent),
        "total_output_spikes": total_output_spikes,
        "class_accuracy": [float(value) for value in class_accuracy],
        "confusion_matrix": confusion.tolist(),
        "predictions_fingerprint": predictions_fingerprint,
        "accuracy_acceptance_threshold": None,
        "accuracy_policy": "measurement_only_no_post_conversion_tuning_threshold",
    }
    manifest_fingerprint = _json_fingerprint(manifest)
    manifest["manifest_fingerprint"] = manifest_fingerprint
    manifest_path = output / VALIDATION_MANIFEST_FILENAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run P08.3.5 validation-only 100-timestep SNN evaluation"
    )
    parser.add_argument("--conversion-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=500)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = evaluate_validation(
        args.conversion_dir,
        args.output_dir,
        batch_size=args.batch_size,
    )
    print(
        "PASS: P08.3.5 validation-only SNN execution "
        f"examples={manifest['validation_examples']} timesteps={manifest['timesteps']} "
        f"accuracy={manifest['snn_validation_accuracy']:.6f} "
        f"ann_reference={manifest['ann_validation_accuracy_reference']:.6f} "
        f"delta={manifest['ann_minus_snn_accuracy']:.6f}"
    )
    print(
        "PASS: P08.3.5 output activity "
        f"total_spikes={manifest['total_output_spikes']} "
        f"silent={manifest['silent_examples']} ties={manifest['tie_examples']}"
    )
    print(
        "PASS: P08.3.5 conversion identity "
        f"conversion={manifest['accepted_conversion_fingerprint']} "
        f"network={manifest['accepted_network_fingerprint']} "
        f"compiled={manifest['accepted_compiled_fingerprint']}"
    )
    print(
        "PASS: P08.3.5 test lock official_test_used=false test_examples_observed=0 "
        f"predictions_fingerprint={manifest['predictions_fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
