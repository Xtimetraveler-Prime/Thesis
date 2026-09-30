"""Deterministic Keras training for the P08 candidate CNN."""

from __future__ import annotations

import json
from pathlib import Path
import time

import numpy as np

from .config import BATCH_SIZE, LEARNING_RATE, MAX_EPOCHS, VALIDATION_SEED
from .data import load_mnist, normalize_images, stratified_train_validation_indices


def require_tensorflow():
    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "TensorFlow is required for P08 training. Install applications/mnist_v2_nxtf[train]."
        ) from exc
    return tf


def build_ann():
    """Build the four weight-bearing layer P08 ANN candidate."""

    tf = require_tensorflow()
    inputs = tf.keras.Input(shape=(28, 28, 1), name="pixels")
    x = tf.keras.layers.Conv2D(
        3,
        5,
        strides=1,
        padding="valid",
        use_bias=False,
        activation="relu",
        name="stage0_conv1",
    )(inputs)
    x = tf.keras.layers.Conv2D(
        6,
        3,
        strides=2,
        padding="valid",
        use_bias=False,
        activation="relu",
        name="stage1_conv2",
    )(x)
    x = tf.keras.layers.Flatten(name="flatten")(x)
    x = tf.keras.layers.Dense(8, use_bias=False, activation="relu", name="stage2_dense8")(x)
    scores = tf.keras.layers.Dense(
        10,
        use_bias=False,
        activation="relu",
        name="stage3_output10",
    )(x)
    probabilities = tf.keras.layers.Softmax(name="class_probabilities")(scores)
    model = tf.keras.Model(inputs=inputs, outputs=probabilities, name="p08_mnist_cnn")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )
    return model


def _configure_determinism(tf) -> None:
    tf.keras.utils.set_random_seed(VALIDATION_SEED)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        # Older/alternate TensorFlow builds may not expose this; the seed is
        # still recorded and the limitation is visible in training metadata.
        pass


def train_ann(output_dir: str | Path, *, max_epochs: int = MAX_EPOCHS) -> dict:
    """Train with validation-only model selection and freeze the best checkpoint."""

    tf = require_tensorflow()
    _configure_determinism(tf)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    dataset = load_mnist()
    train_idx, validation_idx = stratified_train_validation_indices(dataset.y_train)
    x = normalize_images(dataset.x_train)[..., np.newaxis]
    x_train, y_train = x[train_idx], dataset.y_train[train_idx]
    x_val, y_val = x[validation_idx], dataset.y_train[validation_idx]

    model = build_ann()
    expected_parameters = 6125
    if model.count_params() != expected_parameters:
        raise RuntimeError(
            f"P08 ANN parameter contract changed: {model.count_params()} != {expected_parameters}"
        )

    best_weights = output / "p08_best.weights.h5"
    history_rows: list[dict] = []
    best_accuracy = -1.0
    best_epoch = -1
    started = time.perf_counter()

    for epoch in range(1, int(max_epochs) + 1):
        history = model.fit(
            x_train,
            y_train,
            validation_data=(x_val, y_val),
            batch_size=BATCH_SIZE,
            epochs=1,
            shuffle=True,
            verbose=2,
        )
        train_accuracy = float(history.history["accuracy"][-1])
        val_accuracy = float(history.history["val_accuracy"][-1])
        train_loss = float(history.history["loss"][-1])
        val_loss = float(history.history["val_loss"][-1])
        history_rows.append(
            {
                "epoch": epoch,
                "train_accuracy": train_accuracy,
                "validation_accuracy": val_accuracy,
                "train_loss": train_loss,
                "validation_loss": val_loss,
            }
        )
        # Strict greater-than preserves the earliest epoch on a tie.
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            best_epoch = epoch
            model.save_weights(best_weights)

    elapsed = time.perf_counter() - started
    if best_epoch < 0 or not best_weights.exists():
        raise RuntimeError("P08 training did not produce a selected checkpoint")
    model.load_weights(best_weights)

    frozen_model = output / "p08_ann.keras"
    model.save(frozen_model)
    split_file = output / "validation_indices.npy"
    np.save(split_file, validation_idx)

    metadata = {
        "schema": "p08-ann-training-v1",
        "seed": VALIDATION_SEED,
        "training_images": int(len(train_idx)),
        "validation_images": int(len(validation_idx)),
        "official_test_images_evaluated": 0,
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "maximum_epochs": int(max_epochs),
        "best_epoch": best_epoch,
        "best_validation_accuracy": best_accuracy,
        "parameter_count": model.count_params(),
        "use_bias": False,
        "elapsed_training_seconds": elapsed,
        "history": history_rows,
        "checkpoint": best_weights.name,
        "frozen_model": frozen_model.name,
        "validation_indices": split_file.name,
    }
    metadata_file = output / "p08_training.json"
    metadata_file.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
    return metadata


def evaluate_frozen_ann(model_path: str | Path) -> dict:
    """Evaluate one already-frozen model on the untouched official test split."""

    tf = require_tensorflow()
    dataset = load_mnist()
    model = tf.keras.models.load_model(model_path)
    x_test = normalize_images(dataset.x_test)[..., np.newaxis]
    loss, accuracy = model.evaluate(x_test, dataset.y_test, batch_size=BATCH_SIZE, verbose=2)
    predictions = np.argmax(model.predict(x_test, batch_size=BATCH_SIZE, verbose=0), axis=1)
    return {
        "schema": "p08-ann-test-evaluation-v1",
        "samples": int(len(dataset.y_test)),
        "loss": float(loss),
        "accuracy": float(accuracy),
        "errors": int(np.count_nonzero(predictions != dataset.y_test)),
    }
