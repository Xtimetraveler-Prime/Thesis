"""Identity contract for the accepted P08.3.3 ANN checkpoint."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ACCEPTED_ANN_CHECKPOINT_SHA256 = (
    "61f60eaa789dcf04131f658edb86db880999a5f0ad2c8f1bd06426d464dba7d2"
)
ACCEPTED_ANN_WEIGHTS_FINGERPRINT = (
    "e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce"
)
ACCEPTED_ANN_EPOCHS_RAN = 18
ACCEPTED_ANN_BEST_EPOCH = 13
ACCEPTED_ANN_BEST_VAL_ACCURACY = 0.992600
ACCEPTED_ANN_BEST_VAL_LOSS = 0.030356
ACCEPTED_ANN_PARAMETERS = 7_006


def _array_identity(array: np.ndarray) -> bytes:
    value = np.ascontiguousarray(array)
    header = json.dumps(
        {"shape": value.shape, "dtype": str(value.dtype)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return header + b"\0" + value.tobytes(order="C")


def weights_fingerprint(weights: list[np.ndarray]) -> str:
    digest = hashlib.sha256()
    for weight in weights:
        digest.update(_array_identity(weight))
    return digest.hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_accepted_manifest(manifest: dict[str, object]) -> None:
    expected = {
        "schema": "p08-ann-training-v1",
        "mode": "full-55k-5k",
        "official_test_used": False,
        "selection_source": "fixed_validation_split_only",
        "test_examples_observed": 0,
        "model_parameters": ACCEPTED_ANN_PARAMETERS,
        "epochs_ran": ACCEPTED_ANN_EPOCHS_RAN,
        "best_epoch": ACCEPTED_ANN_BEST_EPOCH,
        "checkpoint_sha256": ACCEPTED_ANN_CHECKPOINT_SHA256,
        "selected_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(
                f"accepted ANN manifest mismatch for {key}: "
                f"{manifest.get(key)!r} != {value!r}"
            )

    if abs(float(manifest["best_val_accuracy"]) - ACCEPTED_ANN_BEST_VAL_ACCURACY) > 5e-7:
        raise ValueError("accepted ANN validation accuracy mismatch")
    if abs(float(manifest["best_val_loss"]) - ACCEPTED_ANN_BEST_VAL_LOSS) > 5e-7:
        raise ValueError("accepted ANN validation loss mismatch")


def validate_accepted_checkpoint(checkpoint_path: str | Path, manifest_path: str | Path):
    """Load and verify the exact locally accepted P08.3.3 Keras artifact."""

    checkpoint = Path(checkpoint_path)
    manifest_file = Path(manifest_path)
    if not checkpoint.is_file():
        raise FileNotFoundError(f"accepted ANN checkpoint is missing: {checkpoint}")
    if not manifest_file.is_file():
        raise FileNotFoundError(f"accepted ANN manifest is missing: {manifest_file}")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    validate_accepted_manifest(manifest)
    observed_sha = file_sha256(checkpoint)
    if observed_sha != ACCEPTED_ANN_CHECKPOINT_SHA256:
        raise ValueError(
            "accepted ANN checkpoint SHA-256 mismatch: "
            f"{observed_sha} != {ACCEPTED_ANN_CHECKPOINT_SHA256}"
        )

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("TensorFlow is required to load the accepted ANN") from exc

    model = tf.keras.models.load_model(checkpoint)
    if int(model.count_params()) != ACCEPTED_ANN_PARAMETERS:
        raise ValueError("accepted ANN parameter count mismatch")
    observed_weights = weights_fingerprint(model.get_weights())
    if observed_weights != ACCEPTED_ANN_WEIGHTS_FINGERPRINT:
        raise ValueError(
            "accepted ANN tensor fingerprint mismatch: "
            f"{observed_weights} != {ACCEPTED_ANN_WEIGHTS_FINGERPRINT}"
        )
    return model, manifest
