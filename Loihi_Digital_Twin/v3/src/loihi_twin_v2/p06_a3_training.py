"""P06-A3.2/3 reproducible, train/validation-only compact SNN optimization.

All training passes through the integer-exact P06-A2.5 forward with surrogate
gradients. The official 10k MNIST test set is never loaded or evaluated.
This code creates *candidate* checkpoints, not frozen P06-A4 benchmarks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import sys

import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader, Subset, TensorDataset

from .p06_a3_data import SPLIT_SCHEMA, TrainingSplit
from .p06_input_contract import ENCODER_PROFILE, READOUT_PROFILE
from .p06_integer_oracle import LIFParameters
from .p06_train_forward import IntegerForwardSNN

TRAINING_SCHEMA = "p06-a3-compact-training-candidate-v1"
TRAINING_PROFILE = "p06-a3-compact-784x32x10-fixed-LIF-v1"
MIN_VALIDATION_ACCURACY = 0.60  # PREDECLARED GO/NO-GO, not observed accuracy
LOGIT_SCALE = 2.0
WEIGHT_CLAMP = 512.0  # narrower than signed24; always represented without loss

HIDDEN_LIF = LIFParameters(
    current_decay=4096, voltage_decay=4096, threshold=32,
    bias=0, reset_voltage=0, refractory_ticks=0,
)
OUTPUT_LIF = LIFParameters(
    current_decay=4096, voltage_decay=4096, threshold=8,
    bias=0, reset_voltage=0, refractory_ticks=0,
)


@dataclass(frozen=True)
class TrainSettings:
    seed: int = 20261013
    epochs: int = 8
    batch_size: int = 64
    learning_rate: float = 0.05
    surrogate_width: float = 16.0

    def __post_init__(self):
        if type(self.seed) is not int or type(self.epochs) is not int or self.epochs < 1:
            raise ValueError("training seed must be integer and epochs positive")
        if type(self.batch_size) is not int or self.batch_size < 1:
            raise ValueError("batch size must be positive")
        for name in ("learning_rate", "surrogate_width"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")


def initialize_model(settings: TrainSettings) -> IntegerForwardSNN:
    """Seeded nonzero initialization without altering process-global RNG."""
    model = IntegerForwardSNN(HIDDEN_LIF, OUTPUT_LIF, surrogate_width=settings.surrogate_width)
    rng = torch.Generator(device="cpu").manual_seed(settings.seed)
    with torch.no_grad():
        model.w_input_hidden.uniform_(-6.0, 6.0, generator=rng)
        model.w_hidden_output.uniform_(-4.0, 4.0, generator=rng)
    return model


def _data_loaders(split: TrainingSplit, settings: TrainSettings, epoch: int):
    if split.manifest.get("schema") != SPLIT_SCHEMA:
        raise ValueError("cannot train official candidate on synthetic/unverified MNIST IDX")
    pixels = torch.frombuffer(bytearray(split.images), dtype=torch.uint8).view(split.count, 784)
    labels = torch.frombuffer(bytearray(split.labels), dtype=torch.uint8).to(torch.int64)
    both = TensorDataset(pixels, labels)
    training = DataLoader(
        Subset(both, split.train_indices), batch_size=settings.batch_size,
        shuffle=True, generator=torch.Generator().manual_seed(settings.seed + epoch),
        num_workers=0, drop_last=False,
    )
    validating = DataLoader(
        Subset(both, split.validation_indices), batch_size=settings.batch_size,
        shuffle=False, num_workers=0,
    )
    return training, validating


def evaluate(model: IntegerForwardSNN, loader) -> dict:
    """Use validation pixels/labels only; never refer to test IDX files."""
    model.eval()
    correct = samples = silent = 0
    loss_total = 0.0
    with torch.no_grad():
        for pixels, labels in loader:
            counts = model(pixels)
            loss_total += float(F.cross_entropy(counts * LOGIT_SCALE, labels, reduction="sum"))
            correct += int((counts.argmax(dim=1) == labels).sum())
            silent += int((counts.sum(dim=1) == 0).sum())
            samples += len(labels)
    if not samples:
        raise ValueError("empty validation loader")
    return {
        "count": samples, "accuracy": correct / samples,
        "mean_cross_entropy": loss_total / samples,
        "all_silent_count": silent,
        "all_silent_fraction": silent / samples,
    }


def train_epoch(model: IntegerForwardSNN, loader, optimizer) -> dict:
    model.train()
    total_loss, total_correct, total_count = 0.0, 0, 0
    for pixels, labels in loader:
        optimizer.zero_grad(set_to_none=True)
        counts = model(pixels)
        loss = F.cross_entropy(counts * LOGIT_SCALE, labels)
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("nonfinite training loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        with torch.no_grad():
            for parameter in (model.w_input_hidden, model.w_hidden_output):
                if not bool(torch.isfinite(parameter).all()):
                    raise RuntimeError("nonfinite trained parameter")
                parameter.clamp_(-WEIGHT_CLAMP, WEIGHT_CLAMP)
        size = len(labels)
        total_loss += float(loss.detach()) * size
        total_correct += int((counts.detach().argmax(1) == labels).sum())
        total_count += size
    if not total_count:
        raise ValueError("empty training loader")
    return {
        "count": total_count, "accuracy": total_correct / total_count,
        "mean_cross_entropy": total_loss / total_count,
    }


def integer_weights_sha256(model: IntegerForwardSNN) -> str:
    """Portable signed32 little-endian representation of signed24 weights."""
    network = model.to_integer_network()
    h = hashlib.sha256()
    for label, rows in (
        (b"input_to_hidden/32x784/v1", network.input_to_hidden),
        (b"hidden_to_output/10x32/v1", network.hidden_to_output),
    ):
        h.update(struct.pack("<H", len(label)))
        h.update(label)
        for row in rows:
            for value in row:
                h.update(struct.pack("<i", value))
    return h.hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_candidate(
    model: IntegerForwardSNN,
    output_directory: str | Path,
    settings: TrainSettings,
    dataset_manifest: dict,
    history: list[dict],
    best_epoch: int,
) -> dict:
    if not history or not 1 <= best_epoch <= len(history):
        raise ValueError("cannot save candidate without completed validation")
    out = Path(output_directory)
    out.mkdir(parents=True, exist_ok=False)
    weights_file = out / "weights_state_dict.pt"
    torch.save(model.cpu().state_dict(), weights_file)
    best = history[best_epoch - 1]["validation"]
    is_canonical = dataset_manifest.get("schema") == SPLIT_SCHEMA
    metrics = {
        "schema": TRAINING_SCHEMA, "profile": TRAINING_PROFILE,
        "input_encoder": ENCODER_PROFILE, "readout": READOUT_PROFILE,
        "timesteps": 26, "architecture": [784, 32, 10],
        "source_dataset": dataset_manifest,
        "training_settings": asdict(settings),
        "neuron_config": {"hidden": asdict(HIDDEN_LIF), "output": asdict(OUTPUT_LIF)},
        "optimizer": "Adam", "loss": "cross_entropy(2.0 * exact_integer_output_spike_counts)",
        "surrogate": "strict comparator forward; fast-sigmoid backward; STE rounding/clipping",
        "initializer": "torch.Generator(seed) uniform hidden[-6,6] output[-4,4]",
        "validation_go_floor_predeclared": MIN_VALIDATION_ACCURACY,
        "best_epoch": best_epoch, "best_validation": best, "history": history,
        "candidate_go": is_canonical and best["accuracy"] >= MIN_VALIDATION_ACCURACY,
        "weights_file": weights_file.name,
        "weights_file_sha256": _sha_file(weights_file),
        "exported_integer_weights_sha256": integer_weights_sha256(model),
        "versions": {"python": sys.version.split()[0], "torch": torch.__version__},
        "official_mnist_test_status": "SEALED / NOT READ",
        "physical_fpga_status": "NOT TESTED",
        "provenance": "project-trained candidate only; not published tutorial weights",
    }
    (out / "candidate_manifest.json").write_text(
        json.dumps(metrics, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return metrics


def load_candidate(folder: str | Path) -> tuple[IntegerForwardSNN, dict]:
    """Verify checkpoint and integer weight hashes before using a candidate."""
    directory = Path(folder)
    manifest = json.loads((directory / "candidate_manifest.json").read_text())
    if manifest.get("schema") != TRAINING_SCHEMA:
        raise ValueError("unsupported candidate manifest schema")
    if manifest.get("input_encoder") != ENCODER_PROFILE or manifest.get("readout") != READOUT_PROFILE:
        raise ValueError("incompatible encoder or spike readout")
    if manifest.get("neuron_config") != {"hidden": asdict(HIDDEN_LIF), "output": asdict(OUTPUT_LIF)}:
        raise ValueError("unexpected fixed training neuron contract")
    checkpoint = directory / manifest["weights_file"]
    if checkpoint.name != "weights_state_dict.pt" or _sha_file(checkpoint) != manifest["weights_file_sha256"]:
        raise ValueError("checkpoint file name/hash mismatch")
    config = TrainSettings(**manifest["training_settings"])
    model = initialize_model(config)
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    if integer_weights_sha256(model) != manifest["exported_integer_weights_sha256"]:
        raise ValueError("quantized integer checkpoint hash mismatch")
    return model, manifest


def fit_canonical_mnist(split: TrainingSplit, directory: str | Path, settings: TrainSettings) -> dict:
    """Run a single declared train/validation trial and save the best epoch.

    The held-out MNIST official test partition is NEVER used for any action.
    Epoch selection uses validation only. P06-A4 freeze and first official
    test evaluation are distinct future acceptance gates.
    """
    if split.manifest.get("schema") != SPLIT_SCHEMA:
        raise ValueError("only canonical verified 60k TRAIN archives may be fitted")
    random.seed(settings.seed)
    torch.manual_seed(settings.seed)
    torch.use_deterministic_algorithms(True)
    model = initialize_model(settings)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings.learning_rate)
    history, best_epoch, best_score = [], 0, -1.0
    best_state = None
    for epoch in range(1, settings.epochs + 1):
        train_loader, validation_loader = _data_loaders(split, settings, epoch)
        tr = train_epoch(model, train_loader, optimizer)
        val = evaluate(model, validation_loader)
        print(f"A3 epoch {epoch}/{settings.epochs} train={tr['accuracy']:.4f} "
              f"validation={val['accuracy']:.4f} silent={val['all_silent_fraction']:.4f}", flush=True)
        history.append({"epoch": epoch, "train": tr, "validation": val})
        if val["accuracy"] > best_score:
            best_score = val["accuracy"]
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("no validated epoch")
    model.load_state_dict(best_state, strict=True)
    return save_candidate(model, directory, settings, split.manifest, history, best_epoch)
