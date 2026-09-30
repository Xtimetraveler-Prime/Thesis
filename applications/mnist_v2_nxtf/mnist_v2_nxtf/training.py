"""Deterministic P08.3 ANN training/checkpoint pipeline.

The official MNIST test split is intentionally absent from this module's public
training boundary. Full P08.3 training consumes only the official 60k training
split, partitions it into the frozen 55k/5k train/validation sets, and selects a
checkpoint from validation metrics only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .ann import EXPECTED_ANN_PARAMETERS, build_ann, compile_ann, configure_determinism
from .config import NUM_CLASSES, TOPOLOGY_STATUS
from .data import (
    load_mnist_training_split,
    normalize_images,
    stratified_train_validation_indices,
)
from .policy import ANN_POLICY, OFFICIAL_TEST_POLICY, POLICY_STATUS, validate_frozen_policy


TRAINING_SCHEMA = "p08-ann-training-v1"
FULL_TRAINING_MODE = "full-55k-5k"
SMOKE_TRAINING_MODE = "deterministic-smoke"
CHECKPOINT_FILENAME = "selected_ann.keras"
MANIFEST_FILENAME = "training_manifest.json"


@dataclass(frozen=True, slots=True)
class TrainingArrays:
    x_train: np.ndarray
    y_train: np.ndarray
    x_validation: np.ndarray
    y_validation: np.ndarray
    split_fingerprint: str
    dataset_fingerprint: str
    mode: str


@dataclass(frozen=True, slots=True)
class EpochRecord:
    epoch: int
    loss: float
    accuracy: float
    val_loss: float
    val_accuracy: float

    @property
    def selection_key(self) -> tuple[float, float, int]:
        # Smaller tuple wins: highest val accuracy, then lowest val loss, then
        # earliest epoch. This encodes the frozen P08.3.1 checkpoint rule.
        return (-self.val_accuracy, self.val_loss, self.epoch)


@dataclass(frozen=True, slots=True)
class TrainingResult:
    output_dir: Path
    checkpoint_path: Path
    manifest_path: Path
    best_epoch: int
    best_val_accuracy: float
    best_val_loss: float
    epochs_ran: int
    checkpoint_sha256: str
    manifest_fingerprint: str


def _sha256_bytes(*parts: bytes) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest()


def _array_identity(array: np.ndarray) -> bytes:
    value = np.ascontiguousarray(array)
    header = json.dumps(
        {"shape": value.shape, "dtype": str(value.dtype)},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return header + b"\0" + value.tobytes(order="C")


def _one_hot(labels: np.ndarray) -> np.ndarray:
    labels = np.asarray(labels, dtype=np.int64)
    if labels.ndim != 1:
        raise ValueError("labels must be rank-1")
    if np.any(labels < 0) or np.any(labels >= NUM_CLASSES):
        raise ValueError("MNIST labels must be in 0..9")
    return np.eye(NUM_CLASSES, dtype=np.float32)[labels]


def prepare_full_training_arrays() -> TrainingArrays:
    """Prepare the frozen 55k/5k split without exposing official test arrays."""

    validate_frozen_policy()
    source = load_mnist_training_split()
    if source.x_train.shape != (60_000, 28, 28) or source.y_train.shape != (60_000,):
        raise AssertionError(
            "official MNIST training split shape drifted: "
            f"images={source.x_train.shape} labels={source.y_train.shape}"
        )

    train_indices, validation_indices = stratified_train_validation_indices(
        source.y_train,
        validation_size=ANN_POLICY.validation_size,
        seed=ANN_POLICY.random_seed,
    )
    if len(train_indices) != 55_000 or len(validation_indices) != 5_000:
        raise AssertionError("frozen P08.3 train/validation sizes drifted")

    x_train = normalize_images(source.x_train[train_indices])[..., np.newaxis]
    x_validation = normalize_images(source.x_train[validation_indices])[..., np.newaxis]
    y_train = _one_hot(source.y_train[train_indices])
    y_validation = _one_hot(source.y_train[validation_indices])

    split_fingerprint = _sha256_bytes(
        _array_identity(train_indices),
        _array_identity(validation_indices),
    )
    dataset_fingerprint = _sha256_bytes(
        _array_identity(source.x_train),
        _array_identity(source.y_train),
    )
    return TrainingArrays(
        x_train=x_train,
        y_train=y_train,
        x_validation=x_validation,
        y_validation=y_validation,
        split_fingerprint=split_fingerprint,
        dataset_fingerprint=dataset_fingerprint,
        mode=FULL_TRAINING_MODE,
    )


def make_smoke_training_arrays() -> TrainingArrays:
    """Create a tiny deterministic corpus that exercises the real training path."""

    rng = np.random.default_rng(ANN_POLICY.random_seed ^ 0x50383332)
    train_labels = np.tile(np.arange(NUM_CLASSES, dtype=np.int64), 8)
    validation_labels = np.tile(np.arange(NUM_CLASSES, dtype=np.int64), 2)

    # Give each class a weak deterministic spatial signature plus noise. Accuracy
    # is deliberately not an acceptance criterion; this corpus only validates
    # training/checkpoint plumbing without using MNIST or tuning policy.
    train_images = rng.integers(0, 32, size=(80, 28, 28), dtype=np.uint8)
    validation_images = rng.integers(0, 32, size=(20, 28, 28), dtype=np.uint8)
    for index, label in enumerate(train_labels):
        train_images[index, label * 2 : label * 2 + 3, :] = np.uint8(224)
    for index, label in enumerate(validation_labels):
        validation_images[index, label * 2 : label * 2 + 3, :] = np.uint8(224)

    x_train = normalize_images(train_images)[..., np.newaxis]
    x_validation = normalize_images(validation_images)[..., np.newaxis]
    y_train = _one_hot(train_labels)
    y_validation = _one_hot(validation_labels)

    split_fingerprint = _sha256_bytes(
        _array_identity(train_labels),
        _array_identity(validation_labels),
    )
    dataset_fingerprint = _sha256_bytes(
        _array_identity(train_images),
        _array_identity(train_labels),
        _array_identity(validation_images),
        _array_identity(validation_labels),
    )
    return TrainingArrays(
        x_train=x_train,
        y_train=y_train,
        x_validation=x_validation,
        y_validation=y_validation,
        split_fingerprint=split_fingerprint,
        dataset_fingerprint=dataset_fingerprint,
        mode=SMOKE_TRAINING_MODE,
    )


def checkpoint_is_better(candidate: EpochRecord, current: EpochRecord | None) -> bool:
    return current is None or candidate.selection_key < current.selection_key


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _epoch_record(epoch: int, logs: dict[str, Any]) -> EpochRecord:
    required = ("loss", "accuracy", "val_loss", "val_accuracy")
    missing = [name for name in required if name not in logs]
    if missing:
        raise RuntimeError(f"training logs missing required metrics: {missing}")
    record = EpochRecord(
        epoch=epoch,
        loss=float(logs["loss"]),
        accuracy=float(logs["accuracy"]),
        val_loss=float(logs["val_loss"]),
        val_accuracy=float(logs["val_accuracy"]),
    )
    if not all(np.isfinite(value) for value in asdict(record).values() if isinstance(value, float)):
        raise RuntimeError(f"non-finite training metric at epoch {epoch}: {record}")
    return record


def train_arrays(
    arrays: TrainingArrays,
    output_dir: str | Path,
    *,
    max_epochs: int,
) -> TrainingResult:
    """Train/select one ANN using only the supplied train/validation arrays."""

    validate_frozen_policy()
    if max_epochs <= 0 or max_epochs > ANN_POLICY.max_epochs:
        raise ValueError(f"max_epochs must be in 1..{ANN_POLICY.max_epochs}")
    if arrays.mode == FULL_TRAINING_MODE and max_epochs != ANN_POLICY.max_epochs:
        raise ValueError("full P08.3 training must use the frozen maximum epoch policy")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / CHECKPOINT_FILENAME
    manifest_path = output_dir / MANIFEST_FILENAME
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    if manifest_path.exists():
        manifest_path.unlink()

    configure_determinism()
    model = compile_ann(build_ann(configure_seed=False))
    if model.count_params() != EXPECTED_ANN_PARAMETERS:
        raise AssertionError("training model parameter count drifted")

    try:
        import tensorflow as tf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("TensorFlow is required for P08.3 training") from exc

    history: list[EpochRecord] = []
    best: EpochRecord | None = None
    wait = 0
    patience = ANN_POLICY.early_stopping_patience

    class ValidationCheckpoint(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):  # type: ignore[override]
            nonlocal best, wait
            record = _epoch_record(int(epoch) + 1, dict(logs or {}))
            history.append(record)
            if checkpoint_is_better(record, best):
                best = record
                wait = 0
                self.model.save(checkpoint_path, overwrite=True)
            else:
                wait += 1
                if wait >= patience:
                    self.model.stop_training = True

    model.fit(
        arrays.x_train,
        arrays.y_train,
        validation_data=(arrays.x_validation, arrays.y_validation),
        batch_size=ANN_POLICY.batch_size,
        epochs=max_epochs,
        shuffle=ANN_POLICY.shuffle_training,
        callbacks=[ValidationCheckpoint()],
        verbose=2,
    )

    if best is None or not checkpoint_path.is_file():
        raise RuntimeError("validation checkpoint selection produced no model artifact")

    # Load the selected artifact before writing the manifest so serialization is
    # part of the gate, not merely assumed from model.save returning.
    selected = tf.keras.models.load_model(checkpoint_path)
    if selected.count_params() != EXPECTED_ANN_PARAMETERS:
        raise AssertionError("serialized selected checkpoint changed parameter count")

    checkpoint_sha256 = _file_sha256(checkpoint_path)
    manifest: dict[str, Any] = {
        "schema": TRAINING_SCHEMA,
        "mode": arrays.mode,
        "topology_status": TOPOLOGY_STATUS,
        "policy_status": POLICY_STATUS,
        "official_test_policy": OFFICIAL_TEST_POLICY,
        "official_test_used": False,
        "selection_source": "fixed_validation_split_only",
        "train_examples": int(len(arrays.x_train)),
        "validation_examples": int(len(arrays.x_validation)),
        "test_examples_observed": 0,
        "split_fingerprint": arrays.split_fingerprint,
        "dataset_fingerprint": arrays.dataset_fingerprint,
        "model_parameters": int(selected.count_params()),
        "max_epochs": int(max_epochs),
        "epochs_ran": len(history),
        "early_stopping_patience": patience,
        "checkpoint_metric": ANN_POLICY.checkpoint_metric,
        "checkpoint_mode": ANN_POLICY.checkpoint_mode,
        "checkpoint_tiebreakers": list(ANN_POLICY.checkpoint_tiebreakers),
        "best_epoch": best.epoch,
        "best_val_accuracy": best.val_accuracy,
        "best_val_loss": best.val_loss,
        "checkpoint_filename": checkpoint_path.name,
        "checkpoint_sha256": checkpoint_sha256,
        "history": [asdict(record) for record in history],
        "random_seed": ANN_POLICY.random_seed,
        "deterministic_ops": ANN_POLICY.deterministic_ops,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "tensorflow_version": tf.__version__,
    }
    manifest_fingerprint = _json_fingerprint(manifest)
    manifest["manifest_fingerprint"] = manifest_fingerprint
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return TrainingResult(
        output_dir=output_dir,
        checkpoint_path=checkpoint_path,
        manifest_path=manifest_path,
        best_epoch=best.epoch,
        best_val_accuracy=best.val_accuracy,
        best_val_loss=best.val_loss,
        epochs_ran=len(history),
        checkpoint_sha256=checkpoint_sha256,
        manifest_fingerprint=manifest_fingerprint,
    )


def run_training(output_dir: str | Path, *, smoke: bool = False) -> TrainingResult:
    arrays = make_smoke_training_arrays() if smoke else prepare_full_training_arrays()
    epochs = 1 if smoke else ANN_POLICY.max_epochs
    return train_arrays(arrays, output_dir, max_epochs=epochs)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen P08.3 ANN training pipeline")
    parser.add_argument("--output-dir", required=True, help="directory for selected checkpoint/manifest")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run one epoch on deterministic synthetic data; does not load MNIST",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_training(args.output_dir, smoke=bool(args.smoke))
    mode = SMOKE_TRAINING_MODE if args.smoke else FULL_TRAINING_MODE
    print(
        f"PASS: P08.3.2 {mode} checkpoint "
        f"epochs={result.epochs_ran} best_epoch={result.best_epoch} "
        f"val_accuracy={result.best_val_accuracy:.6f} val_loss={result.best_val_loss:.6f}"
    )
    print(
        "PASS: P08.3.2 artifact manifest official_test_used=false "
        f"checkpoint_sha256={result.checkpoint_sha256} "
        f"manifest_fingerprint={result.manifest_fingerprint}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
