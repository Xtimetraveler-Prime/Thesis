"""P06-A3.4 bounded pilot activity gate; no real MNIST labels or checkpoints."""
from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from torch.utils.data import DataLoader, TensorDataset
from loihi_twin_v2.p06_a3_data import TrainingSplit
from loihi_twin_v2.p06_a3_pilot import (
    PILOT_SCHEMA, count_integer_weight_changes, gradient_probe,
    run_canonical_pilot, run_pilot_from_loaders,
)
from loihi_twin_v2.p06_a3_training import TrainSettings, initialize_model


def _loader(images):
    pixels = torch.tensor(images, dtype=torch.uint8)
    labels = torch.tensor([i % 3 for i in range(len(images))], dtype=torch.int64)
    return DataLoader(TensorDataset(pixels, labels), batch_size=4, shuffle=False)


def test_complete_silence_must_not_pass_pilot():
    blank = _loader([[0] * 784 for _ in range(8)])
    report = run_pilot_from_loaders(blank, blank, settings=TrainSettings(batch_size=4), epochs=1)
    assert report["schema"] == PILOT_SCHEMA
    assert report["status"] == "DIAGNOSE_BEFORE_FULL_TRAIN"
    assert "all_validation_outputs_silent" in report["diagnostics"]
    assert report["baseline_validation"]["all_silent_fraction"] == 1.0
    assert report["official_test_status"] == "SEALED"
    assert report["candidate_checkpoint"] == "NOT WRITTEN"


def test_deterministic_bright_pilot_diagnostics_and_exact_effective_weight_changes():
    bright = [
        [255 if (i + n * 31) % 5 != 0 else 0 for i in range(784)]
        for n in range(8)
    ]
    loader = _loader(bright)
    cfg = TrainSettings(seed=20261013, epochs=1, batch_size=4)
    model = initialize_model(cfg)
    zero_changed = count_integer_weight_changes(model.to_integer_network(), model.to_integer_network())
    assert zero_changed == {"input_hidden": 0, "hidden_output": 0}
    grad = gradient_probe(model, loader)
    assert grad["input_hidden_gradient_finite"]
    assert grad["hidden_output_gradient_finite"]
    assert grad["loss"] >= 0
    result = run_pilot_from_loaders(loader, loader, settings=cfg, epochs=1)
    assert result["schema"] == PILOT_SCHEMA
    assert len(result["epochs"]) == 1
    assert result["epochs"][0]["train"]["count"] == 8
    assert result["epochs"][0]["validation"]["count"] == 8
    assert isinstance(result["diagnostics"], list)
    assert isinstance(result["changed_integer_weight_counts"]["input_hidden"], int)
    assert len(result["before_integer_sha256"]) == len(result["after_integer_sha256"]) == 64
    assert result["pilot_accuracy_is_not_official_test_accuracy"] is True


def test_synthetic_split_cannot_be_used_as_canonical_pilot():
    fixture = TrainingSplit(
        images=bytes(784 * 2), labels=bytes([0, 1]),
        train_indices=(0,), validation_indices=(1,),
        manifest={"schema": "synthetic-idx-test-not-benchmark"},
    )
    with pytest.raises(ValueError, match="canonical verified"):
        run_canonical_pilot(fixture)


@pytest.mark.parametrize("bad_epochs", [0, 5, -1, 1.5, True])
def test_pilot_epoch_limit_rejects_invalid(bad_epochs):
    loader = _loader([[0] * 784 for _ in range(4)])
    with pytest.raises(ValueError, match="pilot epochs"):
        run_pilot_from_loaders(loader, loader, settings=TrainSettings(batch_size=4), epochs=bad_epochs)
