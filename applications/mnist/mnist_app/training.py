"""TensorFlow training utilities for the first direct MNIST SNN.

The user's original lab used TensorFlow/Keras for MNIST loading, training, and
accuracy evaluation. This module keeps that workflow but replaces ReLU dense
neurons with an explicit integrate-and-fire output layer whose forward behavior
matches the frozen application profile: full current decay, persistent voltage,
hard reset to zero, no refractory period, and spike-count decoding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import FLOAT_THRESHOLD, INPUT_AXONS, OUTPUT_NEURONS, PRESENTATION_TICKS
from .dataset import load_mnist
from .encoding import encode_binary_spikes


@dataclass(frozen=True, slots=True)
class TrainingResult:
    checkpoint: Path
    metrics: Path
    final_test_accuracy: float


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
    """Hard forward threshold with a smooth fast-sigmoid surrogate gradient."""

    @tf.custom_gradient
    def op(value):
        spike = tf.cast(value > 0.0, tf.float32)

        def grad(dy):
            slope = 5.0
            surrogate = 1.0 / tf.square(1.0 + slope * tf.abs(value))
            return dy * surrogate

        return spike, grad

    return op(x)


def forward_spike_counts(spikes, weights, *, threshold: float = FLOAT_THRESHOLD):
    """Run the float training model and return output spike counts."""

    tf = _require_tensorflow()
    spikes = tf.convert_to_tensor(spikes, dtype=tf.float32)
    weights = tf.convert_to_tensor(weights, dtype=tf.float32)
    if spikes.shape.rank != 3:
        raise ValueError("spikes must have rank 3: (batch, ticks, axons)")
    if weights.shape != (INPUT_AXONS, OUTPUT_NEURONS):
        raise ValueError(
            f"weights must have shape {(INPUT_AXONS, OUTPUT_NEURONS)}; got {weights.shape}"
        )

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


def _evaluate(weights, images, labels, *, batch_size: int) -> tuple[float, float]:
    correct = 0
    total = 0
    total_spikes = 0.0
    for start in range(0, len(images), batch_size):
        stop = min(start + batch_size, len(images))
        spike_batch = encode_binary_spikes(images[start:stop]).astype(np.float32)
        counts = forward_spike_counts(spike_batch, weights).numpy()
        predictions = np.argmax(counts, axis=1)
        correct += int(np.sum(predictions == labels[start:stop]))
        total += stop - start
        total_spikes += float(np.sum(counts))
    return correct / total, total_spikes / total


def train_snn(
    output_dir: str | Path,
    *,
    epochs: int = 10,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    seed: int = 0x4D4E4953,
    train_limit: int | None = None,
    test_limit: int | None = None,
) -> TrainingResult:
    """Train and persist the frozen 400->10 direct spiking classifier."""

    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch_size must be positive")
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
        initializer((INPUT_AXONS, OUTPUT_NEURONS)),
        trainable=True,
        name="input_to_output_weights",
    )
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)

    @tf.function
    def train_step(spike_batch, label_batch):
        with tf.GradientTape() as tape:
            counts = forward_spike_counts(spike_batch, weights)
            loss = loss_fn(label_batch, counts)
        gradient = tape.gradient(loss, [weights])
        optimizer.apply_gradients(zip(gradient, [weights]))
        predictions = tf.argmax(counts, axis=1, output_type=tf.int64)
        accuracy = tf.reduce_mean(tf.cast(predictions == label_batch, tf.float32))
        return loss, accuracy

    history: list[dict[str, float | int]] = []
    order = np.arange(len(x_train))
    for epoch in range(1, epochs + 1):
        rng.shuffle(order)
        loss_sum = 0.0
        acc_sum = 0.0
        batches = 0
        for start in range(0, len(order), batch_size):
            ids = order[start : start + batch_size]
            spike_batch = encode_binary_spikes(x_train[ids]).astype(np.float32)
            labels = tf.convert_to_tensor(y_train[ids], dtype=tf.int64)
            loss, accuracy = train_step(spike_batch, labels)
            loss_sum += float(loss.numpy())
            acc_sum += float(accuracy.numpy())
            batches += 1

        test_accuracy, mean_output_spikes = _evaluate(
            weights, x_test, y_test, batch_size=batch_size
        )
        row = {
            "epoch": epoch,
            "mean_batch_loss": loss_sum / batches,
            "mean_batch_accuracy": acc_sum / batches,
            "test_accuracy": test_accuracy,
            "mean_output_spikes_per_image": mean_output_spikes,
        }
        history.append(row)
        print(
            f"epoch={epoch:02d} loss={row['mean_batch_loss']:.4f} "
            f"train_acc={row['mean_batch_accuracy']:.4f} "
            f"test_acc={test_accuracy:.4f} spikes/image={mean_output_spikes:.2f}"
        )

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "mnist_snn_float.npz"
    np.savez_compressed(
        checkpoint,
        weights=np.asarray(weights.numpy(), dtype=np.float32),
        threshold=np.float32(FLOAT_THRESHOLD),
        presentation_ticks=np.int32(PRESENTATION_TICKS),
        seed=np.int64(seed),
    )
    metrics_path = output / "training_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "schema": "neuromorphic-twin-mnist-training-v1",
                "architecture": "20x20-input-axons-to-10-lif-output-neurons",
                "input_axons": INPUT_AXONS,
                "output_neurons": OUTPUT_NEURONS,
                "presentation_ticks": PRESENTATION_TICKS,
                "threshold": FLOAT_THRESHOLD,
                "seed": seed,
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "train_samples": len(x_train),
                "test_samples": len(x_test),
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
        final_test_accuracy=float(history[-1]["test_accuracy"]),
    )
