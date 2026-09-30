"""Vectorized evaluator for the frozen P08 integer SNN.

This evaluator mirrors the v2 architectural timing contract: external pixel
spikes may reach layer 0 in the current algorithmic timestep, while every neural
projection emits packets targeting the following timestep.  It is intended for
full-corpus accuracy characterization; representative cases are separately
checked against the exact `LogicalChip` golden model and physical K26 path.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from .config import CHARACTERIZATION_TIMESTEPS, PRIMARY_TIMESTEPS
from .data import quantize_input_spike_counts
from .topology import IntegerModel
from .training import require_tensorflow


def _spike_and_reset(tf, voltage, synaptic_input, threshold: int):
    voltage = voltage + synaptic_input
    spikes = voltage > float(threshold)
    voltage = tf.where(spikes, tf.zeros_like(voltage), voltage)
    return voltage, tf.cast(spikes, tf.float32)


def _simulate_batch(
    model: IntegerModel,
    images: np.ndarray,
    horizons: tuple[int, ...],
):
    tf = require_tensorflow()
    maximum = max(horizons)
    levels = quantize_input_spike_counts(images, timesteps=maximum).astype(np.int32)
    levels_tf = tf.convert_to_tensor(levels, dtype=tf.int32)
    batch = int(levels.shape[0])

    q1 = tf.convert_to_tensor(np.asarray(model.conv1), dtype=tf.float32)
    q2 = tf.convert_to_tensor(np.asarray(model.conv2), dtype=tf.float32)
    q3 = tf.convert_to_tensor(np.asarray(model.dense1), dtype=tf.float32)
    q4 = tf.convert_to_tensor(np.asarray(model.dense2), dtype=tf.float32)

    v1 = tf.zeros((batch, 24, 24, 3), dtype=tf.float32)
    v2 = tf.zeros((batch, 11, 11, 6), dtype=tf.float32)
    v3 = tf.zeros((batch, 8), dtype=tf.float32)
    v4 = tf.zeros((batch, 10), dtype=tf.float32)
    previous1 = tf.zeros_like(v1)
    previous2 = tf.zeros_like(v2)
    previous3 = tf.zeros_like(v3)
    output_counts = tf.zeros((batch, 10), dtype=tf.int32)
    snapshots: dict[int, np.ndarray] = {}

    for timestep in range(maximum):
        before = (timestep * levels_tf) // maximum
        after = ((timestep + 1) * levels_tf) // maximum
        input_spikes = tf.cast(after > before, tf.float32)
        input_spikes = tf.reshape(input_spikes, (batch, 28, 28, 1))

        syn1 = tf.nn.conv2d(input_spikes, q1, strides=1, padding="VALID")
        v1, spikes1 = _spike_and_reset(tf, v1, syn1, model.thresholds[0])

        syn2 = tf.nn.conv2d(previous1, q2, strides=[1, 2, 2, 1], padding="VALID")
        v2, spikes2 = _spike_and_reset(tf, v2, syn2, model.thresholds[1])

        syn3 = tf.matmul(tf.reshape(previous2, (batch, -1)), q3)
        v3, spikes3 = _spike_and_reset(tf, v3, syn3, model.thresholds[2])

        syn4 = tf.matmul(previous3, q4)
        v4, spikes4 = _spike_and_reset(tf, v4, syn4, model.thresholds[3])
        output_counts = output_counts + tf.cast(spikes4, tf.int32)

        previous1 = spikes1
        previous2 = spikes2
        previous3 = spikes3
        completed = timestep + 1
        if completed in horizons:
            snapshots[completed] = np.asarray(output_counts.numpy(), dtype=np.int32)

    return snapshots


def simulate_output_counts(
    model: IntegerModel,
    images: np.ndarray,
    *,
    horizons: Iterable[int] = CHARACTERIZATION_TIMESTEPS,
    batch_size: int = 64,
) -> dict[int, np.ndarray]:
    """Return cumulative output spike counts at each requested timestep horizon."""

    selected = tuple(sorted(set(int(value) for value in horizons)))
    if not selected or selected[0] <= 0:
        raise ValueError("horizons must contain positive integers")
    if selected[-1] > PRIMARY_TIMESTEPS:
        raise ValueError(f"horizons may not exceed the frozen {PRIMARY_TIMESTEPS}-tick horizon")
    array = np.asarray(images)
    if array.ndim == 2:
        array = array[np.newaxis, ...]
    results = {horizon: [] for horizon in selected}
    for start in range(0, len(array), batch_size):
        batch = array[start : start + batch_size]
        snapshots = _simulate_batch(model, batch, selected)
        for horizon in selected:
            results[horizon].append(snapshots[horizon])
    return {
        horizon: np.concatenate(parts, axis=0) if parts else np.empty((0, 10), dtype=np.int32)
        for horizon, parts in results.items()
    }


def accuracy_by_horizon(
    model: IntegerModel,
    images: np.ndarray,
    labels: np.ndarray,
    *,
    horizons: Iterable[int] = CHARACTERIZATION_TIMESTEPS,
    batch_size: int = 64,
) -> dict[int, dict[str, float | int]]:
    counts = simulate_output_counts(model, images, horizons=horizons, batch_size=batch_size)
    target = np.asarray(labels, dtype=np.int64)
    result: dict[int, dict[str, float | int]] = {}
    for horizon, scores in counts.items():
        predictions = np.argmax(scores, axis=1)
        correct = int(np.count_nonzero(predictions == target))
        result[horizon] = {
            "samples": int(len(target)),
            "correct": correct,
            "errors": int(len(target) - correct),
            "accuracy": float(correct / len(target)) if len(target) else 0.0,
        }
    return result
