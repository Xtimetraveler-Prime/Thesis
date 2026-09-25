"""TensorFlow training utilities for the dual-profile direct MNIST SNNs.

The user's class notebooks provide the surrounding workflow: TensorFlow/Keras
MNIST loading, Adam, sparse categorical cross-entropy, elapsed training time,
argmax predictions, and incorrect-sample indexing. This module preserves those
pieces while replacing the ANN forward path with the application's explicit
integrate-and-fire dynamics.

Model selection uses a deterministic validation split drawn only from the
official MNIST training set. The official MNIST test set is evaluated only after
the selected checkpoint is frozen.
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


DEFAULT_VALIDATION_SIZE = 5000


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


def stratified_train_validation_indices(
    labels: np.ndarray,
    validation_size: int = DEFAULT_VALIDATION_SIZE,
    *,
    seed: int = 0x4D4E4953,
) -> tuple[np.ndarray, np.ndarray]:
    """Return deterministic stratified train/validation indices."""

    target = np.asarray(labels, dtype=np.int64)
    if target.ndim != 1:
        raise ValueError("labels must be a rank-1 array")
    if isinstance(validation_size, bool) or not isinstance(validation_size, int):
        raise TypeError("validation_size must be an int")
    if validation_size <= 0 or validation_size >= len(target):
        raise ValueError(
            "validation_size must be positive and smaller than the training set"
        )

    classes = np.unique(target)
    if len(classes) == 0:
        raise ValueError("labels cannot be empty")

    base, remainder = divmod(validation_size, len(classes))
    quotas = {
        int(class_id): base + (position < remainder)
        for position, class_id in enumerate(classes)
    }
    rng = np.random.default_rng(seed)
    validation_parts: list[np.ndarray] = []
    for class_id in classes:
        members = np.flatnonzero(target == class_id)
        needed = quotas[int(class_id)]
        if needed > len(members):
            raise ValueError(
                f"class {int(class_id)} has only {len(members)} samples, "
                f"cannot allocate {needed} validation samples"
            )
        if needed:
            selected = rng.choice(members, size=needed, replace=False)
            validation_parts.append(np.asarray(selected, dtype=np.int64))

    validation_indices = np.sort(np.concatenate(validation_parts))
    is_training = np.ones(len(target), dtype=bool)
    is_training[validation_indices] = False
    training_indices = np.flatnonzero(is_training).astype(np.int64)
    return training_indices, validation_indices


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


def evaluate_float_weights(
    weights,
    images,
    labels,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    batch_size: int = 128,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Evaluate float SNN weights without changing them."""

    selected = get_profile(profile)
    score_rows: list[np.ndarray] = []
    total_spikes = 0.0
    for start in range(0, len(images), batch_size):
        stop = min(start + batch_size, len(images))
        spike_batch = encode_binary_spikes(
            images[start:stop],
            profile=selected,
        ).astype(np.float32)
        counts = forward_spike_counts(
            spike_batch,
            weights,
            profile=selected,
        ).numpy()
        score_rows.append(counts)
        total_spikes += float(np.sum(counts))

    scores = (
        np.concatenate(score_rows, axis=0)
        if score_rows
        else np.empty((0, OUTPUT_NEURONS), dtype=np.float32)
    )
    target = np.asarray(labels, dtype=np.int64)
    predictions, incorrect = analyze_predictions(scores, target)
    accuracy = float(np.mean(predictions == target)) if len(target) else 0.0
    mean_spikes = total_spikes / len(target) if len(target) else 0.0
    return accuracy, mean_spikes, predictions, incorrect


def train_snn(
    output_dir: str | Path,
    *,
    profile: str | MnistProfile = DEFAULT_PROFILE,
    epochs: int = 10,
    fine_tune_epochs: int = 5,
    validation_size: int = DEFAULT_VALIDATION_SIZE,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    seed: int = 0x4D4E4953,
    train_limit: int | None = None,
    test_limit: int | None = None,
) -> TrainingResult:
    """Train one direct SNN using validation-only checkpoint selection."""

    selected = get_profile(profile)
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch_size must be positive")
    if fine_tune_epochs < 0:
        raise ValueError("fine_tune_epochs cannot be negative")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be positive")

    tf = _require_tensorflow()
    tf.random.set_seed(seed)
    rng = np.random.default_rng(seed)

    dataset = load_mnist()
    train_indices, validation_indices = stratified_train_validation_indices(
        dataset.y_train,
        validation_size,
        seed=seed,
    )
    if train_limit is not None:
        if train_limit <= 0:
            raise ValueError("train_limit must be positive when provided")
        train_indices = train_indices[:train_limit]

    x_train = dataset.x_train[train_indices]
    y_train = dataset.y_train[train_indices]
    x_validation = dataset.x_train[validation_indices]
    y_validation = dataset.y_train[validation_indices]
    x_test, y_test = dataset.x_test, dataset.y_test
    if test_limit is not None:
        if test_limit <= 0:
            raise ValueError("test_limit must be positive when provided")
        x_test, y_test = x_test[:test_limit], y_test[:test_limit]

    initializer = tf.keras.initializers.GlorotUniform(seed=seed)
    weights = tf.Variable(
        initializer((selected.input_axons, OUTPUT_NEURONS)),
        trainable=True,
        name=f"{selected.name}_input_to_output_weights",
    )
    loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)

    def make_train_step():
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

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

        return train_step

    history: list[dict[str, float | int | str | bool]] = []
    order = np.arange(len(x_train))

    def run_phase(
        count: int,
        phase: str,
        mask: np.ndarray,
    ) -> tuple[np.ndarray, float, float, int]:
        if count <= 0:
            raise ValueError("run_phase requires at least one epoch")

        mask_tensor = tf.convert_to_tensor(mask, dtype=tf.float32)
        train_step = make_train_step()
        best_weights: np.ndarray | None = None
        best_validation_accuracy = -1.0
        best_validation_spikes = 0.0
        best_epoch = 0

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

            (
                validation_accuracy,
                validation_spikes,
                _,
                _,
            ) = evaluate_float_weights(
                weights * mask_tensor,
                x_validation,
                y_validation,
                profile=selected,
                batch_size=batch_size,
            )
            selected_as_best = validation_accuracy > best_validation_accuracy
            if selected_as_best:
                best_validation_accuracy = validation_accuracy
                best_validation_spikes = validation_spikes
                best_epoch = phase_epoch
                best_weights = np.asarray(
                    (weights * mask_tensor).numpy(),
                    dtype=np.float32,
                ).copy()

            row = {
                "phase": phase,
                "epoch": phase_epoch,
                "mean_batch_loss": loss_sum / batches,
                "mean_batch_accuracy": acc_sum / batches,
                "validation_accuracy": validation_accuracy,
                "mean_validation_output_spikes_per_image": validation_spikes,
                "active_connections": int(np.count_nonzero(mask)),
                "selected_as_best": selected_as_best,
            }
            history.append(row)
            print(
                f"profile={selected.name} phase={phase} epoch={phase_epoch:02d} "
                f"loss={row['mean_batch_loss']:.4f} "
                f"train_acc={row['mean_batch_accuracy']:.4f} "
                f"val_acc={validation_accuracy:.4f} "
                f"spikes/image={validation_spikes:.2f} "
                f"connections={row['active_connections']}"
            )

        if best_weights is None:
            raise AssertionError("training phase did not produce a checkpoint")
        weights.assign(best_weights)
        return (
            best_weights,
            best_validation_accuracy,
            best_validation_spikes,
            best_epoch,
        )

    start_time = time.perf_counter()
    dense_mask = np.ones(
        (selected.input_axons, OUTPUT_NEURONS),
        dtype=np.float32,
    )
    (
        _,
        best_initial_validation_accuracy,
        best_initial_validation_spikes,
        best_initial_epoch,
    ) = run_phase(epochs, "initial", dense_mask)

    post_prune_validation_accuracy = best_initial_validation_accuracy
    post_prune_validation_spikes = best_initial_validation_spikes
    best_finetune_epoch: int | None = None
    best_finetune_validation_accuracy: float | None = None
    best_finetune_validation_spikes: float | None = None
    selected_sparse_stage: str | None = None
    final_mask = dense_mask

    if selected.is_sparse:
        final_mask = magnitude_pruning_mask(
            weights.numpy(),
            selected.max_synapses,
        )
        weights.assign(
            weights * tf.convert_to_tensor(final_mask, dtype=tf.float32)
        )
        post_prune_weights = np.asarray(weights.numpy(), dtype=np.float32).copy()
        (
            post_prune_validation_accuracy,
            post_prune_validation_spikes,
            _,
            _,
        ) = evaluate_float_weights(
            weights,
            x_validation,
            y_validation,
            profile=selected,
            batch_size=batch_size,
        )
        print(
            f"profile={selected.name} phase=post-prune "
            f"val_acc={post_prune_validation_accuracy:.4f} "
            f"spikes/image={post_prune_validation_spikes:.2f} "
            f"connections={int(np.count_nonzero(final_mask))}"
        )
        selected_sparse_stage = "post-prune"

        if fine_tune_epochs:
            (
                finetune_weights,
                best_finetune_validation_accuracy,
                best_finetune_validation_spikes,
                best_finetune_epoch,
            ) = run_phase(
                fine_tune_epochs,
                "masked-finetune",
                final_mask,
            )
            if (
                best_finetune_validation_accuracy
                > post_prune_validation_accuracy
            ):
                weights.assign(finetune_weights)
                selected_sparse_stage = "masked-finetune"
            else:
                weights.assign(post_prune_weights)

    elapsed_seconds = time.perf_counter() - start_time
    final_mask_tensor = tf.convert_to_tensor(final_mask, dtype=tf.float32)
    final_weights = np.asarray(
        (weights * final_mask_tensor).numpy(),
        dtype=np.float32,
    )
    nonzero_weights = int(np.count_nonzero(final_weights))
    if nonzero_weights > selected.max_synapses:
        raise AssertionError("trained network exceeds the selected synapse budget")

    (
        final_accuracy,
        mean_output_spikes,
        predictions,
        incorrect_indices,
    ) = evaluate_float_weights(
        final_weights,
        x_test,
        y_test,
        profile=selected,
        batch_size=batch_size,
    )

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / f"{selected.name}_snn_float.npz"
    np.savez_compressed(
        checkpoint,
        weights=final_weights,
        mask=final_mask.astype(np.uint8),
        threshold=np.float32(FLOAT_THRESHOLD),
        presentation_ticks=np.int32(PRESENTATION_TICKS),
        seed=np.int64(seed),
        profile=np.asarray(selected.name),
        validation_size=np.int32(validation_size),
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
                "schema": "neuromorphic-twin-mnist-training-v3",
                "profile": selected.name,
                "architecture": (
                    f"{selected.input_axons}-input-axons-to-10-lif-output-neurons"
                ),
                "selection_policy": (
                    "best-validation-accuracy; earliest epoch wins exact ties"
                ),
                "test_policy": (
                    "official MNIST test set evaluated only after final "
                    "checkpoint selection"
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
                "training_samples": len(x_train),
                "validation_samples": len(x_validation),
                "test_samples": len(x_test),
                "training_seconds": elapsed_seconds,
                "best_initial_epoch": best_initial_epoch,
                "best_initial_validation_accuracy": (
                    best_initial_validation_accuracy
                ),
                "best_initial_validation_spikes_per_image": (
                    best_initial_validation_spikes
                ),
                "post_prune_validation_accuracy": (
                    post_prune_validation_accuracy
                ),
                "post_prune_validation_spikes_per_image": (
                    post_prune_validation_spikes
                ),
                "best_finetune_epoch": best_finetune_epoch,
                "best_finetune_validation_accuracy": (
                    best_finetune_validation_accuracy
                ),
                "best_finetune_validation_spikes_per_image": (
                    best_finetune_validation_spikes
                ),
                "selected_sparse_stage": selected_sparse_stage,
                "final_test_accuracy": final_accuracy,
                "mean_test_output_spikes_per_image": mean_output_spikes,
                "nonzero_weights": nonzero_weights,
                "incorrect_test_predictions": int(len(incorrect_indices)),
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
