"""Dataset, split, and deterministic rate-encoding helpers for P08."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import (
    PRIMARY_TIMESTEPS,
    SOURCE_HEIGHT,
    SOURCE_WIDTH,
    VALIDATION_SEED,
    VALIDATION_SIZE,
)


@dataclass(frozen=True, slots=True)
class MnistDataset:
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray


def load_mnist() -> MnistDataset:
    """Load the standard Keras MNIST split as raw uint8 images."""

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "TensorFlow is required to download/load MNIST. Install the P08 "
            "application with its 'train' extra."
        ) from exc
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    return MnistDataset(
        np.asarray(x_train, dtype=np.uint8),
        np.asarray(y_train, dtype=np.int64),
        np.asarray(x_test, dtype=np.uint8),
        np.asarray(y_test, dtype=np.int64),
    )


def stratified_train_validation_indices(
    labels: np.ndarray,
    validation_size: int = VALIDATION_SIZE,
    *,
    seed: int = VALIDATION_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Match the accepted baseline application's deterministic split policy."""

    target = np.asarray(labels, dtype=np.int64)
    if target.ndim != 1:
        raise ValueError("labels must be a rank-1 array")
    if isinstance(validation_size, bool) or not isinstance(validation_size, int):
        raise TypeError("validation_size must be an int")
    if validation_size <= 0 or validation_size >= len(target):
        raise ValueError("validation_size must be positive and smaller than the training set")

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
                f"class {int(class_id)} has only {len(members)} samples, cannot allocate {needed}"
            )
        if needed:
            validation_parts.append(
                np.asarray(rng.choice(members, size=needed, replace=False), dtype=np.int64)
            )
    validation = np.sort(np.concatenate(validation_parts))
    keep = np.ones(len(target), dtype=bool)
    keep[validation] = False
    training = np.flatnonzero(keep).astype(np.int64)
    return training, validation


def normalize_images(images: np.ndarray) -> np.ndarray:
    array = np.asarray(images)
    if array.ndim == 2:
        array = array[np.newaxis, ...]
    if array.ndim != 3 or array.shape[1:] != (SOURCE_HEIGHT, SOURCE_WIDTH):
        raise ValueError(f"images must have shape (28, 28) or (N, 28, 28); got {array.shape}")
    if np.any(array < 0) or np.any(array > 255):
        raise ValueError("MNIST pixels must be in 0..255")
    return array.astype(np.float32) / np.float32(255.0)


def quantize_input_spike_counts(
    images: np.ndarray,
    *,
    timesteps: int = PRIMARY_TIMESTEPS,
) -> np.ndarray:
    """Map each pixel deterministically to an integer event count in [0, T]."""

    if isinstance(timesteps, bool) or not isinstance(timesteps, int) or timesteps <= 0:
        raise ValueError("timesteps must be a positive int")
    array = np.asarray(images)
    if array.ndim == 2:
        array = array[np.newaxis, ...]
    if array.ndim != 3 or array.shape[1:] != (SOURCE_HEIGHT, SOURCE_WIDTH):
        raise ValueError(f"images must have shape (28, 28) or (N, 28, 28); got {array.shape}")
    if np.any(array < 0) or np.any(array > 255):
        raise ValueError("MNIST pixels must be in 0..255")
    pixels = array.astype(np.int64, copy=False)
    levels = (pixels * timesteps + 127) // 255
    return levels.reshape(len(pixels), SOURCE_HEIGHT * SOURCE_WIDTH).astype(np.int16)


def encode_binary_spikes(
    images: np.ndarray,
    *,
    timesteps: int = PRIMARY_TIMESTEPS,
) -> np.ndarray:
    """Return deterministic evenly distributed rate spikes with shape (N,T,784)."""

    levels = quantize_input_spike_counts(images, timesteps=timesteps)
    ticks = np.arange(timesteps, dtype=np.int64)
    before = (ticks[None, :, None] * levels[:, None, :]) // timesteps
    after = ((ticks[None, :, None] + 1) * levels[:, None, :]) // timesteps
    return after > before
