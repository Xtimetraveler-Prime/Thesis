"""P06-A3.1 dataset provenance and no-test-leakage synthetic fixtures."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import struct

import pytest

from loihi_twin_v2.p06_a3_data import (
    SPLIT_SCHEMA, TRAIN_FILES, SPLIT_SEED, _hash_indices, _unpack_idx,
    download_training_archives, load_train_validation,
)


def _fixtures(tmp_path, n=12, image_value=19):
    image_payload = bytes((image_value + j) % 256 for j in range(n * 784))
    label_payload = bytes(j % 10 for j in range(n))
    img = struct.pack(">IIII", 2051, n, 28, 28) + image_payload
    lab = struct.pack(">II", 2049, n) + label_payload
    (tmp_path / TRAIN_FILES["images"][0]).write_bytes(gzip.compress(img, mtime=0))
    (tmp_path / TRAIN_FILES["labels"][0]).write_bytes(gzip.compress(lab, mtime=0))
    return img, lab


def test_split_determinism_nonoverlap_and_sha256(tmp_path):
    _fixtures(tmp_path)
    a = load_train_validation(tmp_path, strict=False)
    b = load_train_validation(tmp_path, strict=False)
    other = load_train_validation(tmp_path, strict=False, seed=SPLIT_SEED + 1)
    assert (a.count, len(a.train_indices), len(a.validation_indices)) == (12, 10, 2)
    assert a.train_indices == b.train_indices
    assert a.validation_indices == b.validation_indices
    assert a.train_indices != other.train_indices
    assert len(set(a.train_indices) & set(a.validation_indices)) == 0
    assert sorted(a.train_indices + a.validation_indices) == list(range(12))
    assert a.manifest == json.loads(a.manifest_json())
    assert a.manifest["schema"] == "synthetic-idx-test-not-benchmark"
    assert a.manifest["train_indices_le32_sha256"] == _hash_indices(a.train_indices)
    assert a.manifest["validation_indices_le32_sha256"] == _hash_indices(a.validation_indices)
    assert a.manifest["official_test_set"].startswith("sealed")


def test_does_not_open_even_poisoned_official_test_archive(tmp_path):
    _fixtures(tmp_path)
    (tmp_path / "t10k-images-idx3-ubyte.gz").write_bytes(b"NOT AN IDX")
    (tmp_path / "t10k-labels-idx1-ubyte.gz").write_bytes(b"NOT AN IDX")
    assert load_train_validation(tmp_path, strict=False).count == 12


def test_default_strict_rejects_synthetic_archives(tmp_path):
    _fixtures(tmp_path)
    with pytest.raises(ValueError, match="noncanonical"):
        load_train_validation(tmp_path)


def test_missing_archive_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="download"):
        load_train_validation(tmp_path)


def test_bad_image_magic_dimensions_and_trailing_bytes(tmp_path):
    _fixtures(tmp_path)
    with pytest.raises(ValueError, match="image IDX"):
        _unpack_idx(struct.pack(">IIII", 3, 1, 28, 28) + bytes(784), "images")
    with pytest.raises(ValueError, match="image IDX"):
        _unpack_idx(struct.pack(">IIII", 2051, 1, 27, 28) + bytes(784), "images")
    with pytest.raises(ValueError, match="truncated or trailing"):
        _unpack_idx(struct.pack(">IIII", 2051, 1, 28, 28) + bytes(783), "images")
    with pytest.raises(ValueError, match="truncated or trailing"):
        _unpack_idx(struct.pack(">IIII", 2051, 1, 28, 28) + bytes(785), "images")


def test_bad_label_magic_and_label_range_rejected():
    with pytest.raises(ValueError, match="label IDX"):
        _unpack_idx(struct.pack(">II", 100, 1) + bytes([3]), "labels")
    with pytest.raises(ValueError, match="labels"):
        _unpack_idx(struct.pack(">II", 2049, 1) + bytes([11]), "labels")


def test_dataset_image_label_count_mismatch(tmp_path):
    _fixtures(tmp_path)
    label_raw = struct.pack(">II", 2049, 3) + bytes([0, 1, 2])
    (tmp_path / TRAIN_FILES["labels"][0]).write_bytes(gzip.compress(label_raw, mtime=0))
    with pytest.raises(ValueError, match="count mismatch"):
        load_train_validation(tmp_path, strict=False)


def test_archived_bytes_and_decoded_idx_hash_pinned(tmp_path):
    img, lab = _fixtures(tmp_path)
    split = load_train_validation(tmp_path, strict=False)
    for kind, plain in (("images", img), ("labels", lab)):
        item = split.manifest["archives"][kind]
        packed = (tmp_path / item["filename"]).read_bytes()
        assert item["compressed_sha256"] == hashlib.sha256(packed).hexdigest()
        assert item["decoded_idx_sha256"] == hashlib.sha256(plain).hexdigest()
        assert item["source_md5"] == hashlib.md5(packed).hexdigest()
    assert len(split.images) == 12 * 784
    assert len(split.labels) == 12
