"""P06-B2.2 deterministic TRAIN-only scaled SNN fitting and candidate integrity.

Never opens/downloads official MNIST TEST, never mutates the accepted Track A
checkpoint. Real fitting *only* accepts the frozen Track A source TRAIN-only
loader's canonical 60k population, pinned 50k/10k split, and explicitly
approved B2.1 experiment settings.

B2.2 writes a TRAINED CANDIDATE with a strict weights-file SHA and effective
integer tensor SHA. It is NOT a B2.3 quantized/packed parity freeze, official
TEST score, or a scaled KV260 hardware result.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import struct
import sys
import tempfile

import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader, Subset, TensorDataset

from .p06_a3_data import SPLIT_SCHEMA, TRAIN_FILES, TrainingSplit
from .p06_a4_snapshot import (
    PINNED_TRAIN_INDICES_SHA256,
    PINNED_VALIDATION_INDICES_SHA256,
)
from .p06_a3_training import LOGIT_SCALE, WEIGHT_CLAMP, HIDDEN_LIF, OUTPUT_LIF
from .p06_b21_training_foundation import (
    B21IntegerSNN, B21Settings, foundation_manifest, require_train_only_split,
)
from .p06_input_contract import ENCODER_PROFILE, READOUT_PROFILE

B22_SCHEMA = "p06-b2.2-canonical-train-validation-candidate-v1"
B22_TRAIN_STATUS = "TRAINED_CANDIDATE_NOT_FROZEN"
B22_TEST_STATUS = "SEALED_NOT_ACCESSED"
B22_WEIGHT_FILE = "weights_state_dict.pt"
B22_MANIFEST_FILE = "candidate_manifest.json"
B22_LOSS = "cross_entropy(2.0 * 26_tick_exact_integer_output_spike_counts)"
B22_CLIP_NORM = 5.0


class B22TrainingError(ValueError):
    """Explicit source, training state, dataset or candidate-integrity rejection."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for piece in iter(lambda: stream.read(1 << 20), b""):
            h.update(piece)
    return h.hexdigest()


def _sha_indices(indices: tuple[int, ...]) -> str:
    h = hashlib.sha256()
    for index in indices:
        h.update(struct.pack("<I", index))
    return h.hexdigest()


def require_pinned_train_validation(split: TrainingSplit) -> dict:
    """Require original canonical TRAIN archive and the exact A3 split IDs.

    Must be invoked after load_train_validation(path, strict=True) has
    individually MD5-checked both compressed canonical TRAIN IDX files.
    """
    try:
        manifest = require_train_only_split(split)
    except (TypeError, ValueError) as exc:
        raise B22TrainingError(f"canonical TRAIN-only admission rejected: {exc}") from exc
    pinned = (
        (split.train_indices, "train_indices_le32_sha256", PINNED_TRAIN_INDICES_SHA256),
        (split.validation_indices, "validation_indices_le32_sha256",
         PINNED_VALIDATION_INDICES_SHA256),
    )
    for indices, name, expected in pinned:
        calculated = _sha_indices(indices)
        if calculated != expected or manifest.get(name) != expected:
            raise B22TrainingError(f"canonical TRAIN-only {name} does not match frozen A3 split")
    if any(not 0 <= int(label) <= 9 for label in split.labels):
        raise B22TrainingError("canonical TRAIN source label outside ten classes")
    return manifest


def _validate_source_manifest(manifest: dict) -> None:
    """Check internal source identities even on checkpoint reload.

    Compressed IDX bytes must still be read using original strict=True loader
    for a real fitting session; no manifest alone proves those bytes.
    """
    if (not isinstance(manifest, dict) or manifest.get("schema") != SPLIT_SCHEMA
            or manifest.get("train_count") != 50000
            or manifest.get("validation_count") != 10000
            or manifest.get("image_count") != 60000
            or manifest.get("split_seed") != 20261013
            or manifest.get("official_test_set") != "sealed: no t10k archives opened"
            or manifest.get("train_indices_le32_sha256") != PINNED_TRAIN_INDICES_SHA256
            or manifest.get("validation_indices_le32_sha256") != PINNED_VALIDATION_INDICES_SHA256):
        raise B22TrainingError("candidate canonical TRAIN source/split manifest mismatch")
    for kind, (filename, checksum) in TRAIN_FILES.items():
        archive = manifest.get("archives", {}).get(kind, {})
        if archive.get("filename") != filename or archive.get("source_md5") != checksum:
            raise B22TrainingError("candidate canonical TRAIN archive manifest mismatch")


def earliest_best_epoch(history: list[dict]) -> int:
    """Maximum held-out TRAIN-derived validation accuracy, earliest tie."""
    if not history:
        raise B22TrainingError("empty validation history")
    score, winner = -1.0, 0
    for index, row in enumerate(history, start=1):
        accuracy = row.get("validation", {}).get("accuracy")
        if (type(accuracy) not in (int, float)
                or not math.isfinite(accuracy) or not 0 <= accuracy <= 1):
            raise B22TrainingError("missing or nonfinite validation accuracy")
        if accuracy > score:
            score, winner = accuracy, index
    return winner


def build_loaders(
    split: TrainingSplit, settings: B21Settings, epoch: int,
) -> tuple[DataLoader, DataLoader]:
    """Exact TRAIN/validation split; no truncation/validation shuffling."""
    if not isinstance(settings, B21Settings) or not 1 <= epoch <= settings.epochs:
        raise B22TrainingError("invalid B2.2 epoch/settings")
    require_pinned_train_validation(split)
    pixels = torch.frombuffer(bytearray(split.images), dtype=torch.uint8).view(split.count, 784)
    labels = torch.frombuffer(bytearray(split.labels), dtype=torch.uint8).to(torch.int64)
    ds = TensorDataset(pixels, labels)
    training = DataLoader(
        Subset(ds, split.train_indices), batch_size=settings.batch_size,
        shuffle=True,
        generator=torch.Generator(device="cpu").manual_seed(settings.seed + epoch),
        num_workers=0, drop_last=False,
    )
    validation = DataLoader(
        Subset(ds, split.validation_indices), batch_size=settings.batch_size,
        shuffle=False, num_workers=0, drop_last=False,
    )
    return training, validation


def train_epoch(
    model: B21IntegerSNN, loader: DataLoader, optimizer: torch.optim.Optimizer,
    *, device: torch.device,
) -> dict:
    """One full pass over supplied TRAIN-only batches, clipping and STE."""
    model.train()
    samples = correct = 0
    loss_sum = 0.0
    for pixels, labels in loader:
        pixels, labels = pixels.to(device), labels.to(device)
        optimizer.zero_grad(set_to_none=True)
        output = model(pixels)
        loss = F.cross_entropy(output * LOGIT_SCALE, labels)
        if not bool(torch.isfinite(loss).item()):
            raise B22TrainingError("nonfinite TRAIN loss")
        loss.backward()
        for name, param in model.named_parameters():
            if param.grad is None or not bool(torch.isfinite(param.grad).all().item()):
                raise B22TrainingError(f"nonfinite/missing TRAIN gradient: {name}")
        grad_norm = torch.nn.utils.clip_grad_norm_(
            model.parameters(), max_norm=B22_CLIP_NORM, error_if_nonfinite=True)
        if not bool(torch.isfinite(grad_norm).item()):
            raise B22TrainingError("nonfinite TRAIN gradient norm")
        optimizer.step()
        with torch.no_grad():
            for weight in (model.w_input_hidden, model.w_hidden_output):
                if not bool(torch.isfinite(weight).all().item()):
                    raise B22TrainingError("nonfinite model parameter after optimizer")
                weight.clamp_(-WEIGHT_CLAMP, WEIGHT_CLAMP)
        n = labels.numel()
        samples += n
        loss_sum += float(loss.detach()) * n
        correct += int((output.detach().argmax(dim=1) == labels).sum())
    if samples < 1:
        raise B22TrainingError("empty TRAIN loader")
    return {"count": samples, "accuracy": correct / samples,
            "mean_cross_entropy": loss_sum / samples}


@torch.no_grad()
def validate_epoch(
    model: B21IntegerSNN, loader: DataLoader, *, device: torch.device,
) -> dict:
    """Validation labels are used ONLY for epoch selection, not gradients."""
    model.eval()
    total = correct = all_silent = 0
    loss_sum = total_spikes = 0.0
    class_predictions = [0] * 10
    class_spikes = [0] * 10
    for pixels, labels in loader:
        pixels, labels = pixels.to(device), labels.to(device)
        counts = model(pixels)
        loss = F.cross_entropy(counts * LOGIT_SCALE, labels, reduction="sum")
        if not bool(torch.isfinite(loss).item()):
            raise B22TrainingError("nonfinite VALIDATION loss")
        guess = counts.argmax(dim=1)
        correct += int((guess == labels).sum())
        all_silent += int((counts.sum(dim=1) == 0).sum())
        total_spikes += float(counts.sum())
        loss_sum += float(loss)
        for c in range(10):
            class_predictions[c] += int((guess == c).sum())
            class_spikes[c] += int(counts[:, c].sum())
        total += labels.numel()
    if total < 1:
        raise B22TrainingError("empty VALIDATION loader")
    assert sum(class_predictions) == total
    return {
        "count": total, "accuracy": correct / total,
        "mean_cross_entropy": loss_sum / total,
        "all_silent_count": all_silent,
        "all_silent_fraction": all_silent / total,
        "mean_output_spikes_per_image": total_spikes / total,
        "predicted_class_histogram": class_predictions,
        "output_spike_counts_by_class": class_spikes,
    }


def _preflight_device(name: str) -> torch.device:
    if name not in ("cpu", "cuda"):
        raise B22TrainingError("B2.2 device must be cpu or cuda (explicit deterministic mode)")
    if name == "cuda":
        if not torch.cuda.is_available():
            raise B22TrainingError("CUDA requested but PyTorch CUDA unavailable")
        if os.environ.get("CUBLAS_WORKSPACE_CONFIG") not in (":4096:8", ":16:8"):
            raise B22TrainingError(
                "deterministic CUDA requires CUBLAS_WORKSPACE_CONFIG=:4096:8 "
                "exported before launching Python")
    return torch.device(name)


def resource_preflight(settings: B21Settings, device: str = "cpu") -> dict:
    """Reproducible *lower-bound shape* arithmetic, NOT observed peak RAM/time."""
    if not isinstance(settings, B21Settings):
        raise TypeError("B21Settings required")
    target = _preflight_device(device)
    h, b = settings.hidden_neurons, settings.batch_size
    return {
        "schema": B22_SCHEMA,
        "mode": "SHAPE_ONLY_NO_TRAIN_NO_DATASET_IO",
        "architecture": [784, h, 10],
        "dense_connections": 794 * h,
        "device": str(target),
        "train_images": 50000,
        "validation_images": 10000,
        "epochs": settings.epochs,
        "batch_size": b,
        "float32_trainable_parameter_bytes": 4 * 794 * h,
        "float64_effective_weights_bytes_per_forward": 8 * 794 * h,
        "float64_hidden_state_single_tensor_batch_bytes": 8 * b * h,
        "minimum_loaded_raw_uint8_train_archive_bytes": 60000 * 784,
        "optimizer": "Adam",
        "optimizer_moment_bytes_approx": 8 * 794 * h,
        "peak_autograd_RAM": "UNKNOWN_MUST_MEASURE; 26 unrolled STE timesteps",
        "runtime_seconds": None,
        "benchmark_or_accuracy_observed": False,
        "official_mnist_test_status": B22_TEST_STATUS,
        "checkpoint_frozen": False,
    }


def _state_snapshot(model: B21IntegerSNN) -> dict:
    return {name: tensor.detach().cpu().clone()
            for name, tensor in model.state_dict().items()}


def _serialize_candidate(
    model: B21IntegerSNN, output_directory: str | Path,
    settings: B21Settings, dataset_manifest: dict,
    history: list[dict], best_epoch: int,
) -> dict:
    """Best-epoch byte+integer-hash bound candidate, no overwrite or freeze.

    Internal; only fit_canonical_mnist calls this after canonical admission
    and a complete full-population validation history.
    """
    if (not history or len(history) != settings.epochs
            or not 1 <= best_epoch <= len(history)):
        raise B22TrainingError("candidate requires complete declared validation history")
    _validate_source_manifest(dataset_manifest)
    if best_epoch != earliest_best_epoch(history):
        raise B22TrainingError("candidate epoch is not earliest best validation epoch")
    out = Path(output_directory)
    if out.exists():
        raise FileExistsError(f"refusing to overwrite existing B2 candidate directory: {out}")
    if not out.parent.is_dir():
        raise FileNotFoundError(f"candidate parent folder must exist: {out.parent}")
    staged = Path(tempfile.mkdtemp(prefix=".p06_b22_candidate_", dir=out.parent))
    try:
        checkpoint = staged / B22_WEIGHT_FILE
        torch.save(_state_snapshot(model), checkpoint)
        best = history[best_epoch - 1]["validation"]
        if (any(row["train"]["count"] != 50000 or row["validation"]["count"] != 10000
                for row in history)):
            raise B22TrainingError("candidate cannot truncate canonical 50k/10k epoch populations")
        manifest = {
            "schema": B22_SCHEMA,
            "model_state": B22_TRAIN_STATUS,
            "architecture": [784, settings.hidden_neurons, 10],
            "dense_connections": 794 * settings.hidden_neurons,
            "settings": asdict(settings),
            "source_dataset": dataset_manifest,
            "input_encoder": ENCODER_PROFILE,
            "readout": READOUT_PROFILE,
            "neuron_config": {"hidden": asdict(HIDDEN_LIF),
                              "readout": asdict(OUTPUT_LIF)},
            "training_algorithm": "Adam; 26-tick strict integer forward and STE surrogate backward",
            "training_loss": B22_LOSS,
            "gradient_clip_norm": B22_CLIP_NORM,
            "parameter_clamp_abs": WEIGHT_CLAMP,
            "selection": "best validation accuracy; earliest epoch wins exact tie",
            "best_epoch": best_epoch,
            "best_validation": best,
            "history": history,
            "candidate_go": bool(best["accuracy"] >= settings.validation_go_floor),
            "validation_go_floor_predeclared": settings.validation_go_floor,
            "weights_file": B22_WEIGHT_FILE,
            "weights_file_sha256": _sha256_file(checkpoint),
            "effective_integer_weights_sha256": model.integer_weight_sha256(),
            "versions": {"python": sys.version.split()[0],
                         "torch": torch.__version__},
            "official_mnist_test_status": B22_TEST_STATUS,
            "official_mnist_test_images_evaluated": 0,
            "checkpoint_frozen": False,
            "B2_3_quantized_parity_accepted": False,
            "B2_4_freeze_accepted": False,
            "physical_kv260_execution": "NOT_TESTED",
        }
        (staged / B22_MANIFEST_FILE).write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if out.exists():
            raise FileExistsError(f"B2 candidate output directory appeared: {out}")
        staged.rename(out)
        return manifest
    finally:
        if staged.exists():
            shutil.rmtree(staged)


def load_candidate(directory: str | Path) -> tuple[B21IntegerSNN, dict]:
    """Verify SHA of trained state_dict AND distinct effective integer tensor."""
    folder = Path(directory)
    manifest = json.loads((folder / B22_MANIFEST_FILE).read_text(encoding="utf-8"))
    if manifest.get("schema") != B22_SCHEMA or manifest.get("model_state") != B22_TRAIN_STATUS:
        raise B22TrainingError("not a B2.2 trained checkpoint candidate")
    if manifest.get("official_mnist_test_status") != B22_TEST_STATUS:
        raise B22TrainingError("candidate TEST seal violated")
    if manifest.get("official_mnist_test_images_evaluated") != 0:
        raise B22TrainingError("candidate official TEST access/score forbidden")
    _validate_source_manifest(manifest.get("source_dataset"))
    history = manifest.get("history")
    settings_payload = manifest.get("settings")
    if not isinstance(settings_payload, dict):
        raise B22TrainingError("missing complete B2.2 settings")
    if (not isinstance(history, list) or not history
            or manifest.get("best_epoch") != earliest_best_epoch(history)):
        raise B22TrainingError("B2.2 best-validation selection provenance mismatch")
    if (manifest.get("checkpoint_frozen") is not False
            or manifest.get("B2_3_quantized_parity_accepted") is not False):
        raise B22TrainingError("B2.2 cannot impersonate later checkpoint freeze/parity")
    settings = B21Settings(**settings_payload)
    if (len(history) != settings.epochs
            or manifest.get("best_validation") != history[manifest["best_epoch"] - 1]["validation"]
            or manifest.get("candidate_go") is not (
                manifest["best_validation"]["accuracy"] >= settings.validation_go_floor)
            or any(row.get("train", {}).get("count") != 50000
                   or row.get("validation", {}).get("count") != 10000
                   for row in history)):
        raise B22TrainingError("B2.2 validation population/GO-floor/history mismatch")
    if (manifest.get("architecture") != [784, settings.hidden_neurons, 10]
            or manifest.get("dense_connections") != 794 * settings.hidden_neurons
            or manifest.get("input_encoder") != ENCODER_PROFILE
            or manifest.get("readout") != READOUT_PROFILE):
        raise B22TrainingError("B2.2 manifest architecture/encoder/readout mismatch")
    checkpoint = folder / manifest.get("weights_file", "")
    if (checkpoint.name != B22_WEIGHT_FILE
            or not checkpoint.is_file()
            or _sha256_file(checkpoint) != manifest.get("weights_file_sha256")):
        raise B22TrainingError("B2.2 checkpoint filename/file SHA256 mismatch")
    model = B21IntegerSNN.initialized(settings)
    # PyTorch weights_only rejects arbitrary Python pickle objects by default;
    # checkpoint file bytes must already match the recorded digest above.
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    if model.integer_weight_sha256() != manifest.get("effective_integer_weights_sha256"):
        raise B22TrainingError("B2.2 effective signed24 integer weight SHA256 mismatch")
    return model, manifest


def fit_canonical_mnist(
    split: TrainingSplit, output_directory: str | Path,
    settings: B21Settings, *, device: str = "cpu",
) -> dict:
    """Explicit whole-population TRAIN-only experiment; no official TEST.

    This function deliberately does not offer a fast subset/short-epoch flag.
    The internal train_epoch/validate_epoch may run on tiny synthetic tensors
    in tests; those cannot enter this fitted-candidate public entry point.
    """
    if not isinstance(settings, B21Settings):
        raise TypeError("B21Settings required")
    out = Path(output_directory)
    if out.exists():
        raise FileExistsError(f"refusing to overwrite B2 candidate: {out}")
    source = require_pinned_train_validation(split)
    runtime_device = _preflight_device(device)
    previous_deterministic = torch.are_deterministic_algorithms_enabled()
    previous_benchmark = torch.backends.cudnn.benchmark
    cpu_rng = torch.random.get_rng_state()
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    try:
        random.seed(settings.seed)
        torch.manual_seed(settings.seed)
        model = B21IntegerSNN.initialized(settings).to(runtime_device)
        optimizer = torch.optim.Adam(model.parameters(), lr=settings.learning_rate)
        images = torch.frombuffer(bytearray(split.images), dtype=torch.uint8).view(
            split.count, 784)
        labels = torch.frombuffer(bytearray(split.labels), dtype=torch.uint8).long()
        dataset = TensorDataset(images, labels)
        validation = DataLoader(
            Subset(dataset, split.validation_indices), batch_size=settings.batch_size,
            shuffle=False, num_workers=0,
        )
        history = []
        best_epoch, best_accuracy, best_state = 0, -1.0, None
        for epoch in range(1, settings.epochs + 1):
            training = DataLoader(
                Subset(dataset, split.train_indices), batch_size=settings.batch_size,
                shuffle=True,
                generator=torch.Generator(device="cpu").manual_seed(settings.seed + epoch),
                drop_last=False, num_workers=0,
            )
            tr = train_epoch(model, training, optimizer, device=runtime_device)
            va = validate_epoch(model, validation, device=runtime_device)
            if tr["count"] != 50000 or va["count"] != 10000:
                raise B22TrainingError("refusing incomplete canonical train/validation population")
            print(f"B2.2 epoch {epoch}/{settings.epochs} "
                  f"train={tr['accuracy']:.5f} validation={va['accuracy']:.5f} "
                  f"silent={va['all_silent_fraction']:.5f}", flush=True)
            history.append({"epoch": epoch, "train": tr, "validation": va})
            if va["accuracy"] > best_accuracy:
                best_accuracy, best_epoch = va["accuracy"], epoch
                best_state = _state_snapshot(model)
        if best_state is None:
            raise B22TrainingError("no complete best-validation epoch to save")
        model.load_state_dict(best_state, strict=True)
        model.to("cpu")
        return _serialize_candidate(model, output_directory, settings,
                                    source, history, best_epoch)
    finally:
        torch.use_deterministic_algorithms(previous_deterministic)
        torch.backends.cudnn.benchmark = previous_benchmark
        torch.random.set_rng_state(cpu_rng)
