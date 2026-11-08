"""P08-B1 native PC-only source/manifest negative gates; no hardware or TEST."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b1_matched_source_audit as b1

from loihi_twin_v2.p07_a3_validation import ValidationFrame
from loihi_twin_v2.p07_a4_stream import make_stream, initial_journal


@pytest.fixture(scope="module")
def pinned_split():
    shuffled = list(range(60000))
    random.Random(20261013).shuffle(shuffled)
    return tuple(shuffled[:50000]), tuple(shuffled[50000:])


def test_a_and_b_train_split_exact_and_no_leakage(pinned_split):
    train, validation = pinned_split
    result = b1.check_membership_indices(train, validation)
    assert result["selected_indices_le32_sha256"] == b1.PREFIX_INDICES_SHA
    assert result["overlap_with_B_training_indices"] == 0
    assert result["first_three_source_indices"] == [37384, 27347, 20178]
    assert result["last_source_index"] == 42925


def test_wrong_order_or_train_inclusion_rejected(pinned_split):
    train, validation = pinned_split
    assert set(validation[:1024]).isdisjoint(train)
    reordered = list(validation)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    with pytest.raises(b1.P08B1Error):
        b1.check_membership_indices(train, reordered)
    with pytest.raises(b1.P08B1Error):
        b1.check_membership_indices(train, (train[0],) + validation[1:])
    with pytest.raises(b1.P08B1Error):
        b1.check_membership_indices(train[:-1] + (train[-2],), validation)


@pytest.fixture
def synthetic_stage(tmp_path, pinned_split):
    """Pseudopixels for tamper detection only, NEVER an admitted real source."""
    validation = pinned_split[1]
    frames = tuple(
        ValidationFrame(i, bytes([(n * 7) & 0xFF]) * 784, n % 10)
        for n, i in enumerate(validation[:1024])
    )
    pixels = b"".join(f.pixels for f in frames)
    source_manifest = {"synthetic_unit_fixture_only": True}
    stream = make_stream(pixels, tuple(range(784)), trace_index=1023)
    contents = {
        "descriptor": stream.header,
        "mapping": stream.mapping_bytes,
        "pixels": pixels,
        "zero_journal_1m": initial_journal(stream),
    }
    for key, payload in contents.items():
        (tmp_path / b1.STAGE_FILES[key]).write_bytes(payload)
    m = {
        "schema": "p07-a4-2a-persistent-ddr-stage-v1",
        "scope": "TRAIN_DERIVED_VALIDATION_FIRST_1024",
        "frame_count": 1024, "trace_index": 1023,
        "image_stride_bytes": 784, "official_mnist_test": "SEALED",
        "physical_hardware": "NOT_RUN",
        "sha256": {key: b1.sha256(value) for key, value in contents.items()},
    }
    ledger = {
        "scope": "TRAIN_DERIVED_VALIDATION_FIRST_1024",
        "source": "canonical TRAIN-only IDX",
        "official_mnist_test": "SEALED",
        "indices": [f.source_index for f in frames],
        "selected_indices_le32_sha256": b1.PREFIX_INDICES_SHA,
        "source_dataset_sha256": b1.canonical_json_sha256(source_manifest),
        "rows": [
            {"position": n, "source_index": f.source_index,
             "label": f.label, "pixels_sha256": b1.sha256(f.pixels)}
            for n, f in enumerate(frames)
        ],
    }
    (tmp_path / b1.STAGE_MANIFEST).write_text(json.dumps(m))
    (tmp_path / b1.STAGE_LEDGER).write_text(json.dumps(ledger))
    return tmp_path, source_manifest, frames


def test_original_a_stage_integrity_validates(synthetic_stage):
    stage, manifest, frames = synthetic_stage
    result = b1.validate_a_stage(stage, manifest, frames)
    assert result["ordinary_frame_count"] == 1023
    assert result["selected_trace_frame"] == 1023
    assert result["original_A_stage_sha256"]["pixels"] == b1.sha256(
        (stage / b1.STAGE_FILES["pixels"]).read_bytes())


def test_corrupt_pixels_even_with_updated_file_hash_rejected(synthetic_stage):
    stage, manifest, frames = synthetic_stage
    p = stage / b1.STAGE_FILES["pixels"]
    payload = bytearray(p.read_bytes())
    payload[12] ^= 1
    p.write_bytes(payload)
    m_path = stage / b1.STAGE_MANIFEST
    m = json.loads(m_path.read_text())
    m["sha256"]["pixels"] = b1.sha256(payload)
    m_path.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        b1.validate_a_stage(stage, manifest, frames)


def test_reordered_ledger_rejected(synthetic_stage):
    stage, manifest, frames = synthetic_stage
    l_path = stage / b1.STAGE_LEDGER
    ledger = json.loads(l_path.read_text())
    ledger["indices"][0], ledger["indices"][1] = ledger["indices"][1], ledger["indices"][0]
    l_path.write_text(json.dumps(ledger))
    with pytest.raises(ValueError):
        b1.validate_a_stage(stage, manifest, frames)


def test_wrong_trace_index_rejected(synthetic_stage):
    stage, manifest, frames = synthetic_stage
    m_path = stage / b1.STAGE_MANIFEST
    data = json.loads(m_path.read_text())
    data["trace_index"] = 0
    m_path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        b1.validate_a_stage(stage, manifest, frames)


def test_tampered_manifest_sha_rejected(synthetic_stage):
    stage, manifest, frames = synthetic_stage
    m_path = stage / b1.STAGE_MANIFEST
    data = json.loads(m_path.read_text())
    data["sha256"]["descriptor"] = "0" * 64
    m_path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        b1.validate_a_stage(stage, manifest, frames)


def test_test_seal_gate_rejected(synthetic_stage):
    stage, manifest, frames = synthetic_stage
    m_path = stage / b1.STAGE_MANIFEST
    data = json.loads(m_path.read_text())
    data["official_mnist_test"] = "OPEN"
    m_path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        b1.validate_a_stage(stage, manifest, frames)


def test_b_candidate_source_and_scope_consistency():
    source = {"synthetic_unit_fixture_only": True}
    candidate = {
        "schema": "p06-b2.2-canonical-train-validation-candidate-v1",
        "architecture": [784, 1000, 10],
        "source_dataset": source,
        "official_mnist_test_status": "SEALED_NOT_ACCESSED",
        "official_mnist_test_images_evaluated": 0,
        "candidate_go": True,
    }
    b1.check_b_candidate(candidate, source)
    for key, wrong in [
        ("architecture", [784, 32, 10]),
        ("source_dataset", {}),
        ("official_mnist_test_status", "UNSEALED"),
        ("official_mnist_test_images_evaluated", 1),
        ("candidate_go", False),
    ]:
        bad = dict(candidate, **{key: wrong})
        with pytest.raises(b1.P08B1Error):
            b1.check_b_candidate(bad, source)



def test_training_byte_identical_images_are_reported_not_silently_ignored():
    # Different image SOURCE indices can still have exactly identical pixels.
    raw = [bytes([1]) * 784, bytes([2]) * 784, bytes([1]) * 784]
    frames = (ValidationFrame(2, raw[2], 7),)
    result = b1.training_pixel_aliases(b"".join(raw), (0, 1), frames)
    assert result["frames_with_byte_identical_B_training_pixels"] == 1
    assert result["cross_partition_pixel_aliases"][0][
        "identical_pixels_in_B_training_source_indices"] == [0]
    no_alias = b1.training_pixel_aliases(b"".join(raw), (1,), frames)
    assert no_alias["frames_with_byte_identical_B_training_pixels"] == 0

def test_symlink_stage_file_rejected(synthetic_stage):
    stage, manifest, frames = synthetic_stage
    p = stage / b1.STAGE_FILES["pixels"]
    original = stage / "different_raw_pixel_source"
    p.rename(original)
    p.symlink_to(original)
    with pytest.raises(b1.P08B1Error):
        b1.validate_a_stage(stage, manifest, frames)
