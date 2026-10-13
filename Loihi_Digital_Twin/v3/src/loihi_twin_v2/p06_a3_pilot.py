"""P06-A3.4 bounded TRAIN/validation learning-activity pilot.

A pilot uses only already-verified canonical *TRAIN* IDX data, never any
t10k test records. It does not generate an accuracy claim, save a checkpoint,
change the frozen A2 forward contract, or automatically select new hyperparams.

Purpose: detect the all-silent/zero-quantized-update regime before an
eight-epoch full training run on CPU.
"""
from __future__ import annotations

import json

import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader, TensorDataset

from .p06_a3_data import (
    TOTAL_IMAGES, TRAIN_IMAGES, VALIDATION_IMAGES, SPLIT_SCHEMA, TrainingSplit,
)
from .p06_a3_training import (
    LOGIT_SCALE, TrainSettings, evaluate, initialize_model,
    integer_weights_sha256, train_epoch,
)

PILOT_SCHEMA = "p06-a3-learning-pilot-v1"
PILOT_TRAIN_N = 256
PILOT_VALIDATION_N = 128
PILOT_EPOCHS = 2
PILOT_BATCH = 32


def _nonzero_grad(tensor: torch.Tensor | None) -> int:
    if tensor is None:
        return 0
    return int(torch.count_nonzero(tensor).detach().cpu().item())


def gradient_probe(model, loader) -> dict:
    """A single read-only gradient check: no optimization or state updates."""
    model.train()
    pixels, labels = next(iter(loader))
    model.zero_grad(set_to_none=True)
    scores = model(pixels)
    loss = F.cross_entropy(scores * LOGIT_SCALE, labels)
    loss.backward()
    result = {
        "loss": float(loss.detach().cpu()),
        "input_hidden_nonzero_gradient_elements": _nonzero_grad(model.w_input_hidden.grad),
        "hidden_output_nonzero_gradient_elements": _nonzero_grad(model.w_hidden_output.grad),
        "input_hidden_gradient_finite": (
            model.w_input_hidden.grad is not None
            and bool(torch.isfinite(model.w_input_hidden.grad).all())
        ),
        "hidden_output_gradient_finite": (
            model.w_hidden_output.grad is not None
            and bool(torch.isfinite(model.w_hidden_output.grad).all())
        ),
    }
    model.zero_grad(set_to_none=True)
    return result


def count_integer_weight_changes(before, after) -> dict[str, int]:
    """Compare exported signed24 weights, not merely floating optimizer updates."""
    return {
        "input_hidden": sum(
            x != y for old, new in zip(before.input_to_hidden, after.input_to_hidden)
            for x, y in zip(old, new)
        ),
        "hidden_output": sum(
            x != y for old, new in zip(before.hidden_to_output, after.hidden_to_output)
            for x, y in zip(old, new)
        ),
    }


def run_pilot_from_loaders(
    training_loader, validation_loader, *,
    settings: TrainSettings,
    epochs: int = PILOT_EPOCHS,
) -> dict:
    """Pure training pilot on provided loaders; enables tiny synthetic unit tests."""
    if type(epochs) is not int or not 1 <= epochs <= 4:
        raise ValueError("pilot epochs must be in [1,4]")
    torch.manual_seed(settings.seed)
    torch.use_deterministic_algorithms(True)
    model = initialize_model(settings)
    before_integer = model.to_integer_network()
    before_hash = integer_weights_sha256(model)
    baseline = evaluate(model, validation_loader)
    gradients = gradient_probe(model, training_loader)
    optimizer = torch.optim.Adam(model.parameters(), lr=settings.learning_rate)
    observations = []
    for epoch in range(1, epochs + 1):
        train = train_epoch(model, training_loader, optimizer)
        validation = evaluate(model, validation_loader)
        observations.append({"epoch": epoch, "train": train, "validation": validation})
    after_integer = model.to_integer_network()
    changed = count_integer_weight_changes(before_integer, after_integer)
    last = observations[-1]["validation"]
    reasons = []
    if not (gradients["input_hidden_gradient_finite"] and gradients["hidden_output_gradient_finite"]):
        reasons.append("nonfinite_or_missing_gradients")
    if not gradients["input_hidden_nonzero_gradient_elements"]:
        reasons.append("input_hidden_gradient_zero")
    if not gradients["hidden_output_nonzero_gradient_elements"]:
        reasons.append("hidden_output_gradient_zero")
    if changed["input_hidden"] == 0:
        reasons.append("input_hidden_integer_weights_unchanged")
    if changed["hidden_output"] == 0:
        reasons.append("hidden_output_integer_weights_unchanged")
    if last["all_silent_count"] == last["count"]:
        reasons.append("all_validation_outputs_silent")
    # This is a numerical learning-activity gate, NOT the 60% accuracy gate.
    return {
        "schema": PILOT_SCHEMA,
        "status": "GO_TO_CONTROLLED_FULL_TRAIN" if not reasons else "DIAGNOSE_BEFORE_FULL_TRAIN",
        "diagnostics": reasons,
        "baseline_validation": baseline,
        "gradient_probe": gradients,
        "epochs": observations,
        "changed_integer_weight_counts": changed,
        "before_integer_sha256": before_hash,
        "after_integer_sha256": integer_weights_sha256(model),
        "pilot_accuracy_is_not_official_test_accuracy": True,
        "official_test_status": "SEALED",
        "candidate_checkpoint": "NOT WRITTEN",
    }


def run_canonical_pilot(split: TrainingSplit) -> dict:
    """Fixed first training/validation indices from the accepted shuffled split."""
    if (
        split.manifest.get("schema") != SPLIT_SCHEMA
        or split.count != TOTAL_IMAGES
        or len(split.train_indices) != TRAIN_IMAGES
        or len(split.validation_indices) != VALIDATION_IMAGES
    ):
        raise ValueError("pilot requires canonical verified 60k TRAIN-only split")
    # Fresh CPU tensor buffers, no stochastic augmentation, no test IDX access.
    rows = torch.frombuffer(bytearray(split.images), dtype=torch.uint8).view(split.count, 784)
    labels = torch.frombuffer(bytearray(split.labels), dtype=torch.uint8).to(torch.int64)
    tr_idx = torch.tensor(split.train_indices[:PILOT_TRAIN_N], dtype=torch.int64)
    va_idx = torch.tensor(split.validation_indices[:PILOT_VALIDATION_N], dtype=torch.int64)
    train_loader = DataLoader(
        TensorDataset(rows[tr_idx], labels[tr_idx]),
        batch_size=PILOT_BATCH, shuffle=False, num_workers=0,
    )
    validation_loader = DataLoader(
        TensorDataset(rows[va_idx], labels[va_idx]),
        batch_size=PILOT_BATCH, shuffle=False, num_workers=0,
    )
    settings = TrainSettings(seed=20261013, epochs=PILOT_EPOCHS, batch_size=PILOT_BATCH)
    report = run_pilot_from_loaders(
        train_loader, validation_loader, settings=settings, epochs=PILOT_EPOCHS,
    )
    report.update({
        "source_split_manifest_train_indices_sha256":
            split.manifest["train_indices_le32_sha256"],
        "source_split_manifest_validation_indices_sha256":
            split.manifest["validation_indices_le32_sha256"],
        "pilot_training_count": PILOT_TRAIN_N,
        "pilot_validation_count": PILOT_VALIDATION_N,
        "pilot_epochs": PILOT_EPOCHS,
        "pilot_batch_size": PILOT_BATCH,
        "pilot_train_indices": "first 256 accepted shuffled training IDs",
        "pilot_validation_indices": "first 128 accepted shuffled validation IDs",
    })
    return report


def run_pilot_cli(split: TrainingSplit) -> None:
    result = run_canonical_pilot(split)
    print("P06_A3_PILOT=" + json.dumps(result, sort_keys=True), flush=True)
    print("P06_A3_PILOT_STATUS=" + result["status"], flush=True)
    print("P06_A3_OFFICIAL_TEST_STATUS=SEALED", flush=True)
