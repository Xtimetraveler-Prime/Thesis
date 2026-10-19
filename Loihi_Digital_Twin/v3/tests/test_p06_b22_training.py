"""P06-B2.2 synthetic-only engineering tests: no MNIST archive access.

Real B2.2 fit is a separate explicit canonical 50k/10k native opt-in.
Small synthetic loaders below may exercise train_epoch/validate_epoch but
CANNOT use fit_canonical_mnist or produce an accepted trained B2 result.
"""
from __future__ import annotations

from dataclasses import asdict
import copy
import json
import math

import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset

from loihi_twin_v2.p06_a3_data import SPLIT_SCHEMA, TRAIN_FILES, TrainingSplit
from loihi_twin_v2.p06_a3_training import HIDDEN_LIF, OUTPUT_LIF
from loihi_twin_v2.p06_a4_snapshot import (
    PINNED_TRAIN_INDICES_SHA256, PINNED_VALIDATION_INDICES_SHA256,
)
from loihi_twin_v2.p06_b21_training_foundation import B21IntegerSNN, B21Settings
from loihi_twin_v2.p06_b22_training import (
    B22_SCHEMA, B22_TEST_STATUS, B22TrainingError,
    _serialize_candidate, _sha_indices, earliest_best_epoch,
    fit_canonical_mnist, load_candidate, resource_preflight,
    require_pinned_train_validation, train_epoch, validate_epoch,
)


def fake_bytes(n: int = 4) -> torch.Tensor:
    # Distinct synthetic uint8 records only; these are NOT MNIST.
    return torch.tensor([
        [(i * (13 + index * 3) + 9) % 256 for i in range(784)]
        for index in range(n)], dtype=torch.uint8)


def toy_loader(batch: int = 2) -> DataLoader:
    ds = TensorDataset(fake_bytes(4), torch.tensor([0, 4, 3, 9]))
    return DataLoader(ds, shuffle=False, batch_size=batch)


def _metadata_fixture_for_integrity_unit_test() -> dict:
    # This fabricates *metadata* to exercise the SHA loader in temporary
    # scratch directories. It is NOT an actual canonical TRAIN-source
    # certificate or eligible input to fit_canonical_mnist; such a fit must
    # first load and checksum-verify the real TRAIN-only gzip IDX files.
    return {
        "schema": SPLIT_SCHEMA, "image_count": 60000,
        "train_count": 50000, "validation_count": 10000,
        "split_seed": 20261013,
        "official_test_set": "sealed: no t10k archives opened",
        "train_indices_le32_sha256": PINNED_TRAIN_INDICES_SHA256,
        "validation_indices_le32_sha256": PINNED_VALIDATION_INDICES_SHA256,
        "archives": {kind: {"filename": filename, "source_md5": digest}
                     for kind, (filename, digest) in TRAIN_FILES.items()},
    }


def _history_fixture() -> list[dict]:
    # Counts intentionally stand in for canonical populations for *internal
    # serialization unit tests*; no real train/validation metrics are claimed.
    return [
        {"epoch": 1,
         "train": {"count": 50000, "accuracy": 0.41},
         "validation": {"count": 10000, "accuracy": 0.55,
                        "all_silent_fraction": 0.10}},
        {"epoch": 2,
         "train": {"count": 50000, "accuracy": 0.60},
         "validation": {"count": 10000, "accuracy": 0.65,
                        "all_silent_fraction": 0.04}},
    ]


def test_default_1000_hidden_preflight_is_shape_only_no_dataset_io():
    settings = B21Settings()
    report = resource_preflight(settings)
    assert report["schema"] == B22_SCHEMA
    assert report["mode"] == "SHAPE_ONLY_NO_TRAIN_NO_DATASET_IO"
    assert report["architecture"] == [784, 1000, 10]
    assert report["dense_connections"] == 794000
    assert report["train_images"] == 50000
    assert report["validation_images"] == 10000
    assert report["float32_trainable_parameter_bytes"] == 794000 * 4
    assert report["float64_effective_weights_bytes_per_forward"] == 794000 * 8
    assert report["float64_hidden_state_single_tensor_batch_bytes"] == 64 * 1000 * 8
    assert report["runtime_seconds"] is None
    assert report["official_mnist_test_status"] == B22_TEST_STATUS
    assert report["checkpoint_frozen"] is False
    with pytest.raises(B22TrainingError, match="device"):
        resource_preflight(settings, device="tpu")


def test_train_epoch_deterministic_seed_and_finite_ste_backward_and_clamp():
    settings = B21Settings(hidden_neurons=3, seed=10, epochs=1, batch_size=2)
    result = []
    for _ in range(2):
        model = B21IntegerSNN.initialized(settings)
        optimizer = torch.optim.Adam(model.parameters(), lr=settings.learning_rate)
        row = train_epoch(model, toy_loader(), optimizer, device=torch.device("cpu"))
        assert row["count"] == 4
        assert 0 <= row["accuracy"] <= 1
        assert math.isfinite(row["mean_cross_entropy"])
        assert torch.isfinite(model.w_input_hidden).all()
        assert torch.isfinite(model.w_hidden_output).all()
        assert float(model.w_input_hidden.abs().max()) <= 512
        assert float(model.w_hidden_output.abs().max()) <= 512
        result.append((row, model.integer_weight_sha256()))
    assert result[0] == result[1]


def test_validation_is_gradient_free_and_reports_full_class_and_silence_histograms():
    settings = B21Settings(hidden_neurons=2)
    model = B21IntegerSNN.initialized(settings)
    train_epoch(model, toy_loader(2),
                torch.optim.Adam(model.parameters(), lr=settings.learning_rate),
                device=torch.device("cpu"))
    model.zero_grad(set_to_none=True)
    out = validate_epoch(model, toy_loader(3), device=torch.device("cpu"))
    assert out["count"] == 4
    assert 0 <= out["accuracy"] <= 1
    assert out["all_silent_count"] <= 4
    assert 0 <= out["all_silent_fraction"] <= 1
    assert len(out["predicted_class_histogram"]) == 10
    assert sum(out["predicted_class_histogram"]) == 4
    assert len(out["output_spike_counts_by_class"]) == 10
    assert all(param.grad is None for param in model.parameters())


def test_zero_spike_counts_tie_readout_and_train_selection_earliest_best():
    model = B21IntegerSNN(hidden_neurons=2)
    source = TensorDataset(torch.zeros((4, 784), dtype=torch.uint8),
                           torch.tensor([0, 1, 0, 9]))
    stats = validate_epoch(model, DataLoader(source, batch_size=3),
                           device=torch.device("cpu"))
    assert stats["all_silent_count"] == 4
    assert stats["predicted_class_histogram"] == [4] + [0] * 9
    assert stats["accuracy"] == 0.50
    samples = _history_fixture()
    assert earliest_best_epoch(samples) == 2
    samples[0]["validation"]["accuracy"] = 0.65
    assert earliest_best_epoch(samples) == 1
    samples[0]["validation"]["accuracy"] = float("nan")
    with pytest.raises(B22TrainingError, match="nonfinite"):
        earliest_best_epoch(samples)


def test_official_train_source_gate_never_accepts_short_or_synthetic_dataset():
    split = TrainingSplit(
        images=bytes(784), labels=bytes([1]),
        train_indices=(0,), validation_indices=(),
        manifest={"schema": "synthetic-idx-test-not-benchmark"},
    )
    with pytest.raises(B22TrainingError, match="canonical"):
        require_pinned_train_validation(split)
    with pytest.raises(B22TrainingError, match="canonical"):
        fit_canonical_mnist(
            split, "/tmp/should_never_write_b22_synthetic_candidate",
            B21Settings(hidden_neurons=2), device="cpu")
    assert len(_sha_indices((0, 1))) == 64
    assert _sha_indices((1, 0)) != _sha_indices((0, 1))


def test_candidate_internal_hash_roundtrip_tamper_and_no_overwrite(tmp_path):
    """Only validate serialization; no claimed real TRAIN data or fit."""
    settings = B21Settings(hidden_neurons=2, epochs=2, batch_size=2)
    model = B21IntegerSNN.initialized(settings)
    destination = tmp_path / "synthetic_integrity_fixture"
    manifest = _serialize_candidate(
        model, destination, settings, _metadata_fixture_for_integrity_unit_test(),
        _history_fixture(), best_epoch=2)
    assert manifest["schema"] == B22_SCHEMA
    assert manifest["model_state"] == "TRAINED_CANDIDATE_NOT_FROZEN"
    assert manifest["official_mnist_test_status"] == B22_TEST_STATUS
    assert manifest["official_mnist_test_images_evaluated"] == 0
    assert manifest["candidate_go"] is True
    assert manifest["checkpoint_frozen"] is False
    loaded, verified = load_candidate(destination)
    assert loaded.integer_weight_sha256() == model.integer_weight_sha256()
    assert verified["weights_file_sha256"] == manifest["weights_file_sha256"]
    with pytest.raises(FileExistsError, match="overwrite"):
        _serialize_candidate(
            model, destination, settings, _metadata_fixture_for_integrity_unit_test(),
            _history_fixture(), best_epoch=2)
    weight_file = destination / "weights_state_dict.pt"
    original = weight_file.read_bytes()
    weight_file.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(B22TrainingError, match="SHA256"):
        load_candidate(destination)
    weight_file.write_bytes(original)
    raw = destination / "candidate_manifest.json"
    old = raw.read_text()
    changed = json.loads(old)
    changed["official_mnist_test_status"] = "OPENED"
    raw.write_text(json.dumps(changed))
    with pytest.raises(B22TrainingError, match="TEST seal"):
        load_candidate(destination)
    changed["official_mnist_test_status"] = B22_TEST_STATUS
    changed["source_dataset"]["validation_indices_le32_sha256"] = "corrupted"
    raw.write_text(json.dumps(changed))
    with pytest.raises(B22TrainingError, match="TRAIN source/split"):
        load_candidate(destination)
    changed["source_dataset"]["validation_indices_le32_sha256"] = PINNED_VALIDATION_INDICES_SHA256
    changed["best_epoch"] = 1
    raw.write_text(json.dumps(changed))
    with pytest.raises(B22TrainingError, match="best-validation"):
        load_candidate(destination)
    raw.write_text(old)


def test_bad_validation_histories_cannot_create_candidate(tmp_path):
    model = B21IntegerSNN.initialized(
        B21Settings(hidden_neurons=2, epochs=2))
    bad = _history_fixture()
    bad[0]["train"]["count"] = 49999
    with pytest.raises(B22TrainingError, match="truncate"):
        _serialize_candidate(
            model, tmp_path / "reject_short_train",
            B21Settings(hidden_neurons=2, epochs=2),
            _metadata_fixture_for_integrity_unit_test(), bad, 2)
    with pytest.raises(B22TrainingError, match="earliest best"):
        _serialize_candidate(
            model, tmp_path / "reject_nonbest",
            B21Settings(hidden_neurons=2, epochs=2),
            _metadata_fixture_for_integrity_unit_test(),
            _history_fixture(), 1)
