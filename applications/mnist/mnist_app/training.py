"""TensorFlow training utilities for the dual-profile direct MNIST SNNs.

The user's class notebooks provide the surrounding workflow: TensorFlow/Keras
MNIST loading, Adam, sparse categorical cross-entropy, elapsed training time,
argmax predictions, and incorrect-sample indexing. This module preserves those
pieces while replacing the ANN forward path with the application's explicit
integrate-and-fire dynamics.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import (
    DEFAULT_PROFILE,
    FLOAT_THRESHOLD,
    OUTPUT_NEURONS,
    PRESENTATION_TICKS,
    MnistProfile,
    get_profile,
)
from .dataset import load_mnist
from .encoding import encode_binary_spikes


@dataclass(frozen=True, slots=True)
class TrainingResult:
    checkpoint: Path
    metrics: Path
    evaluation: Path
    final_test_accuracy: float
    profile: str
    nonzero_weights: int


def _require_tensorflow():
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "TensorFlow is required for MNIST SNN training. Install the "
            "application with the 'train' extra."
        ) from exc
    return tf


def _surrogate_spike(tf, x):
    """Hard strict-threshold forward path with a fast-sigmoid surrogate gradient."""

    @tf.custom_gradient
    def op(value):
        spike = tf.cast(value > 0.0, tf.float32)

        def grad(dy):
            slope = 5.0
            surrogate = 1.0 / tf.square(1.0 + slope * tf.abs(value))
            return dy * surrogate

        return spike, grad

    return op(x)


def magnitude_pruning_mask(weights: np.ndarray, max_nonzero: int) -> np.ndarray:
    """Keep at most ``max_nonzero`` largest-magnitude weights deterministically."""

    matrix = np.asarray(weights)
    if matrix.ndim != 2:
        raise ValueError("weights must be a rank-2 matrix")
    if isinstance(max_nonzero, bool) or not isinstance(max_nonzero, int):
        raise TypeError("max_nonzero must be an int")
    if max_nonzero < 0:
        raise ValueError("max_nonzero cannot be negative")

    flat = np.abs(matrix).reshape(-1)
    keep = min(max_nonzero, flat.size)
    mask = np.zeros(flat.size, dtype=np.float32)
    if keep:
        indices = np.arange(flat.size)
        # Primary key: descending magnitude. Secondary key: ascending flat index.
        order = np.lexsort((indices, -flat))
        mask[order[:keep]] = 1.0
    return mask.reshape(matrix.shape)


def analyze_predictions(
    class_scores: np.ndarray,
    labels: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return notebook-style argmax predictions and incorrect sample indices."""

    scores = np.asarray(class_scores)
    target = np.asarray(labels, dtype=np.int64)
    if scores.ndim != 2 or scores.shape[1] != OUTPUT_NEURONS:
        raise ValueError(f"class_scores must have shape (N, {OUTPUT_NEURONS})")
    if scores.shape[0] != target.shape[0]:
        raise ValueError("class_scores and labels must contain the same samples")
    predictions = np.argmax(scores, axis=1).astype(np.int64)
    incorrect = np.where(predictions != target)[0].astype(np.int64)
    return predictions, incorrect


def forward_spike_counts(
    spikes,
    weights,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    threshold: float = FLOAT_THRESHOLD,
):
    """Run the float training model and return output spike counts."""

    tf = _require_tensorflow()
    selected = get_profile(profile)
    spikes = tf.convert_to_tensor(spikes, dtype=tf.float32)
    weights = tf.convert_to_tensor(weights, dtype=tf.float32)
    if spikes.shape.rank != 3:
        raise ValueError("spikes must have rank 3: (batch, ticks, axons)")
    expected = (selected.input_axons, OUTPUT_NEURONS)
    if weights.shape != expected:
        raise ValueError(f"weights must have shape {expected}; got {weights.shape}")

    batch = tf.shape(spikes)[0]
    voltage = tf.zeros((batch, OUTPUT_NEURONS), dtype=tf.float32)
    counts = tf.zeros_like(voltage)
    for tick in range(PRESENTATION_TICKS):
        synaptic_input = tf.linalg.matmul(spikes[:, tick, :], weights)
        voltage_work = voltage + synaptic_input
        spike = _surrogate_spike(tf, voltage_work - float(threshold))
        voltage = voltage_work * (1.0 - spike)
        counts = counts + spike
    return counts


def _evaluate(
    weights,
    images,
    labels,
    *,
    profile: MnistProfile,
    batch_size: int,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    score_rows: list[np.ndarray] = []
    total_spikes = 0.0
    for start in range(0, len(images), batch_size):
        stop = min(start + batch_size, len(images))
        spike_batch = encode_binary_spikes(
            images[start:stop],
            profile=profile,
        ).astype(np.float32)
        counts = forward_spike_counts(
            spike_batch,
            weights,
            profile=profile,
        ).numpy()
        score_rows.append(counts)
        total_spikes += float(np.sum(counts))

    scores = (
        np.concatenate(score_rows, axis=0)
        if score_rows
        else np.empty((0, OUTPUT_NEURONS), dtype=np.float32)
    )
    predictions, incorrect = analyze_predictions(scores, labels)
    accuracy = float(np.mean(predictions == labels)) if len(labels) else 0.0
    mean_spikes = total_spikes / len(labels) if len(labels) else 0.0
    return accuracy, mean_spikes, predictions, incorrect


def train_snn(
    output_dir: str | Path,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    epochs: int = 10,
    fine_tune_epochs: int = 5,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    seed: int = 0x4D4E4953,
    train_limit: int | None = None,
    test_limit: int | None = None,
) -> TrainingResult:
    """Train one direct SNN and, for native-sparse, prune/fine-tune to hardware fit."""

    selected = get_profile(profile)
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch_size must be positive")
    if fine_tune_epochs < 0:
        raise ValueError("fine_tune_epochs cannot be negative")

    tf = _require_tensorflow()
    tf.random.set_seed(seed)
    rng = np.random.default_rng(seed)

    dataset = load_mnist()
    x_train, y_train = dataset.x_train, dataset.y_train
    x_test, y_test = dataset.x_test, dataset.y_test
    if train_limit is not None:
        x_train, y_train = x_train[:train_limit], y_train[:train_limit]
    if test_limit is not None:
        x_test, y_test = x_test[:test_limit], y_test[:test_limit]

    initializer = tf.keras.initializers.GlorotUniform(seed=seed)
    weights = tf.Variable(
        initializer((selected.input_axons, OUTPUT_NEURONS)),
        trainable=True,
        name=f"{selected.name}_input_to_output_weights",
    )
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)

    @tf.function
    def train_step(spike_batch, label_batch, mask_tensor):
        with tf.GradientTape() as tape:
            effective_weights = weights * mask_tensor
            counts = forward_spike_counts(
                spike_batch,
                effective_weights,
                profile=selected,
            )
            loss = loss_fn(label_batch, counts)
        gradient = tape.gradient(loss, weights)
        gradient = gradient * mask_tensor
        optimizer.apply_gradients([(gradient, weights)])
        weights.assign(weights * mask_tensor)
        predictions = tf.argmax(counts, axis=1, output_type=tf.int64)
        accuracy = tf.reduce_mean(
            tf.cast(predictions == label_batch, tf.float32)
        )
        return loss, accuracy

    history: list[dict[str, float | int | str]] = []
    order = np.arange(len(x_train))
    mask = np.ones((selected.input_axons, OUTPUT_NEURONS), dtype=np.float32)

    def run_epochs(count: int, phase: str) -> None:
        nonlocal mask
        mask_tensor = tf.convert_to_tensor(mask, dtype=tf.float32)
        for phase_epoch in range(1, count + 1):
            rng.shuffle(order)
            loss_sum = 0.0
            acc_sum = 0.0
            batches = 0
            for start in range(0, len(order), batch_size):
                ids = order[start : start + batch_size]
                spike_batch = encode_binary_spikes(
                    x_train[ids],
                    profile=selected,
                ).astype(np.float32)
                labels = tf.convert_to_tensor(y_train[ids], dtype=tf.int64)
                loss, accuracy = train_step(spike_batch, labels, mask_tensor)
                loss_sum += float(loss.numpy())
                acc_sum += float(accuracy.numpy())
                batches += 1

            test_accuracy, mean_output_spikes, _, _ = _evaluate(
                weights * mask_tensor,
                x_test,
                y_test,
                profile=selected,
                batch_size=batch_size,
            )
            row = {
                "phase": phase,
                "epoch": phase_epoch,
                "mean_batch_loss": loss_sum / batches,
                "mean_batch_accuracy": acc_sum / batches,
                "test_accuracy": test_accuracy,
                "mean_output_spikes_per_image": mean_output_spikes,
                "active_connections": int(np.count_nonzero(mask)),
            }
            history.append(row)
            print(
                f"profile={selected.name} phase={phase} epoch={phase_epoch:02d} "
                f"loss={row['mean_batch_loss']:.4f} "
                f"train_acc={row['mean_batch_accuracy']:.4f} "
                f"test_acc={test_accuracy:.4f} "
                f"spikes/image={mean_output_spikes:.2f} "
                f"connections={row['active_connections']}"
            )

    start_time = time.perf_counter()
    run_epochs(epochs, "initial")

    pre_prune_accuracy, _, _, _ = _evaluate(
        weights,
        x_test,
        y_test,
        profile=selected,
        batch_size=batch_size,
    )

    if selected.is_sparse:
        mask = magnitude_pruning_mask(weights.numpy(), selected.max_synapses)
        weights.assign(weights * tf.convert_to_tensor(mask, dtype=tf.float32))
        post_prune_accuracy, _, _, _ = _evaluate(
            weights,
            x_test,
            y_test,
            profile=selected,
            batch_size=batch_size,
        )
        if fine_tune_epochs:
            run_epochs(fine_tune_epochs, "masked-finetune")
    else:
        post_prune_accuracy = pre_prune_accuracy

    elapsed_seconds = time.perf_counter() - start_time
    final_mask = tf.convert_to_tensor(mask, dtype=tf.float32)
    final_weights = np.asarray((weights * final_mask).numpy(), dtype=np.float32)
    (
        final_accuracy,
        mean_output_spikes,
        predictions,
        incorrect_indices,
    ) = _evaluate(
        final_weights,
        x_test,
        y_test,
        profile=selected,
        batch_size=batch_size,
    )
    nonzero_weights = int(np.count_nonzero(final_weights))
    if nonzero_weights > selected.max_synapses:
        raise AssertionError("trained network exceeds the selected synapse budget")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / f"{selected.name}_snn_float.npz"
    np.savez_compressed(
        checkpoint,
        weights=final_weights,
        mask=mask.astype(np.uint8),
        threshold=np.float32(FLOAT_THRESHOLD),
        presentation_ticks=np.int32(PRESENTATION_TICKS),
        seed=np.int64(seed),
        profile=np.asarray(selected.name),
    )

    evaluation_path = output / f"{selected.name}_evaluation.npz"
    np.savez_compressed(
        evaluation_path,
        predictions=predictions,
        labels=np.asarray(y_test, dtype=np.int64),
        incorrect_indices=incorrect_indices,
    )

    metrics_path = output / f"{selected.name}_training_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "schema": "neuromorphic-twin-mnist-training-v2",
                "profile": selected.name,
                "architecture": (
                    f"{selected.input_axons}-input-axons-to-10-lif-output-neurons"
                ),
                "input_axons": selected.input_axons,
                "output_neurons": OUTPUT_NEURONS,
                "presentation_ticks": PRESENTATION_TICKS,
                "threshold": FLOAT_THRESHOLD,
                "seed": seed,
                "epochs": epochs,
                "fine_tune_epochs": (
                    fine_tune_epochs if selected.is_sparse else 0
                ),
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "train_samples": len(x_train),
                "test_samples": len(x_test),
                "training_seconds": elapsed_seconds,
                "pre_prune_test_accuracy": pre_prune_accuracy,
                "post_prune_test_accuracy": post_prune_accuracy,
                "final_test_accuracy": final_accuracy,
                "mean_output_spikes_per_image": mean_output_spikes,
                "nonzero_weights": nonzero_weights,
                "incorrect_predictions": int(len(incorrect_indices)),
                "history": history,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return TrainingResult(
        checkpoint=checkpoint,
        metrics=metrics_path,
        evaluation=evaluation_path,
        final_test_accuracy=final_accuracy,
        profile=selected.name,
        nonzero_weights=nonzero_weights,
    )
