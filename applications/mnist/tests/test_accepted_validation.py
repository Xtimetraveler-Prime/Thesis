from pathlib import Path

import numpy as np
import pytest

from mnist_app.accepted_validation import sha256_file, validate_accepted_checkpoint


def _write_checkpoint(path: Path, profile: str, weights: np.ndarray) -> None:
    np.savez_compressed(
        path,
        profile=np.asarray(profile),
        weights=weights.astype(np.float32),
        presentation_ticks=np.int32(16),
        threshold=np.float32(1.0),
    )


def test_sha256_file_is_stable(tmp_path: Path):
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"mnist-validation")
    assert sha256_file(path) == sha256_file(path)
    assert len(sha256_file(path)) == 64


def test_validate_cropped_dense_checkpoint(tmp_path: Path):
    path = tmp_path / "cropped.npz"
    weights = np.ones((400, 10), dtype=np.float32)
    _write_checkpoint(path, "cropped-dense", weights)
    result = validate_accepted_checkpoint(path, "cropped-dense")
    assert result["profile"] == "cropped-dense"
    assert result["nonzero_weights"] == 4000
    assert result["presentation_ticks"] == 16


def test_validate_native_sparse_checkpoint_at_budget(tmp_path: Path):
    path = tmp_path / "native.npz"
    weights = np.zeros((784, 10), dtype=np.float32)
    weights.reshape(-1)[:4096] = 1.0
    _write_checkpoint(path, "native-sparse", weights)
    result = validate_accepted_checkpoint(path, "native-sparse")
    assert result["nonzero_weights"] == 4096


def test_validate_checkpoint_rejects_profile_and_budget_mismatch(tmp_path: Path):
    path = tmp_path / "bad.npz"
    weights = np.ones((784, 10), dtype=np.float32)
    _write_checkpoint(path, "native-sparse", weights)
    with pytest.raises(ValueError, match="exceeding"):
        validate_accepted_checkpoint(path, "native-sparse")
    with pytest.raises(ValueError, match="does not match"):
        validate_accepted_checkpoint(path, "cropped-dense")
