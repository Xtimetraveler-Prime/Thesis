"""MNIST dataset helpers derived from the user's TensorFlow lab workflow."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class MnistDataset:
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray


def load_mnist() -> MnistDataset:
    """Load standard MNIST as raw uint8 images using TensorFlow/Keras."""

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "TensorFlow is required to download/load MNIST. Install the MNIST "
            "application training extra first."
        ) from exc

    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()
    return MnistDataset(
        x_train=np.asarray(x_train, dtype=np.uint8),
        y_train=np.asarray(y_train, dtype=np.int64),
        x_test=np.asarray(x_test, dtype=np.uint8),
        y_test=np.asarray(y_test, dtype=np.int64),
    )
