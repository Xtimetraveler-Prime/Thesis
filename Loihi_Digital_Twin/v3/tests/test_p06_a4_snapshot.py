"""P06-A4 trained-word snapshot gates; synthetic fixture does NOT impersonate MNIST."""
from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from loihi_twin_v2.p06_a4_snapshot import (
    PINNED_CHECKPOINT_SHA256, PINNED_INTEGER_WEIGHTS_SHA256,
    PINNED_TRAIN_INDICES_SHA256, PINNED_VALIDATION_INDICES_SHA256,
    FREEZE_SCHEMA, _word_stream, packed_word_snapshot,
    require_pinned_training_candidate, compile_and_check_traces,
    run_a4_snapshot,
)
from loihi_twin_v2.p06_a3_training import initialize_model, TrainSettings
from loihi_twin_v2.p06_input_contract import ENCODER_PROFILE, READOUT_PROFILE


def _accepted_fixture():
    return {
        "candidate_go": True,
        "weights_file_sha256": PINNED_CHECKPOINT_SHA256,
        "exported_integer_weights_sha256": PINNED_INTEGER_WEIGHTS_SHA256,
        "best_epoch": 8, "best_validation": {"accuracy": 0.9439},
        "source_dataset": {
            "train_indices_le32_sha256": PINNED_TRAIN_INDICES_SHA256,
            "validation_indices_le32_sha256": PINNED_VALIDATION_INDICES_SHA256,
        },
        "official_mnist_test_status": "SEALED / NOT READ",
        "input_encoder": ENCODER_PROFILE,
        "readout": READOUT_PROFILE,
    }


def test_pinned_candidate_identifies_user_trained_artifact():
    require_pinned_training_candidate(_accepted_fixture(), PINNED_INTEGER_WEIGHTS_SHA256)


@pytest.mark.parametrize("field,incorrect", [
    ("candidate_go", False),
    ("weights_file_sha256", "f" * 64),
    ("exported_integer_weights_sha256", "0" * 64),
    ("best_epoch", 7),
    ("best_validation", {"accuracy": 0.90}),
    ("official_mnist_test_status", "UNSEALED"),
    ("input_encoder", "different-encoder"),
    ("readout", "different-readout"),
])
def test_tampered_training_manifest_rejected(field, incorrect):
    manifest = _accepted_fixture()
    manifest[field] = incorrect
    with pytest.raises(ValueError):
        require_pinned_training_candidate(manifest, PINNED_INTEGER_WEIGHTS_SHA256)


def test_wrong_candidate_exported_hash_and_changed_split_fail_closed():
    fixture = _accepted_fixture()
    with pytest.raises(ValueError):
        require_pinned_training_candidate(fixture, "e" * 64)
    fixture = _accepted_fixture()
    fixture["source_dataset"]["validation_indices_le32_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="validation index"):
        require_pinned_training_candidate(fixture, PINNED_INTEGER_WEIGHTS_SHA256)


def test_packed_word_snapshot_exact_endian_and_sparse_record_structure():
    hw = SimpleNamespace(
        config_words=(0x1234, 0xABCD),
        state_words=(0x0001020304050607,),
        synapse_words=(0, 0xAABBCCDD),
        axon_words=(SimpleNamespace(index=0x0003, word=0x0123456789ABCDEF),),
        route_descriptor_words=(SimpleNamespace(index=0x23, word=0x11223344),),
        route_words=(0x55443322, 0x01020304),
    )
    data = packed_word_snapshot(hw)
    assert data["compartment_config_le128.bin"] == (0x1234).to_bytes(16, "little") + (0xABCD).to_bytes(16, "little")
    assert data["compartment_state_le64.bin"] == b"\x07\x06\x05\x04\x03\x02\x01\x00"
    assert data["synapses_le64.bin"] == (0).to_bytes(8, "little") + (0xAABBCCDD).to_bytes(8, "little")
    assert data["axon_index_le16_word_le64.bin"] == b"\x03\x00" + (0x0123456789ABCDEF).to_bytes(8, "little")
    assert data["route_descriptor_index_le16_word_le32.bin"] == b"\x23\x00\x44\x33\x22\x11"
    assert data["route_words_le32.bin"] == b"\x22\x33\x44\x55\x04\x03\x02\x01"
    assert hashlib.sha256(data["route_words_le32.bin"]).hexdigest() == hashlib.sha256(b"\x22\x33\x44\x55\x04\x03\x02\x01").hexdigest()


@pytest.mark.parametrize("width", [0, 1, 3, 5, 32])
def test_unsupported_snapshot_word_width_fails_closed(width):
    with pytest.raises(ValueError, match="word width"):
        _word_stream((0,), width)


def test_untrained_synthetic_weights_still_compile_and_match_four_software_paths():
    """Compiler structural test, not accepted trained accuracy."""
    model = initialize_model(TrainSettings())
    frames = (("synthetic-black", bytes(784)),
              ("synthetic-white", bytes([255] * 784)),
              ("synthetic-pattern", bytes(i % 256 for i in range(784))))
    image, compiler, results = compile_and_check_traces(model, frames)
    assert (image.core_id, image.compartment_count, len(compiler.ingress_routes)) == (0, 42, 784)
    assert (image.synapse_count, image.route_count) == (25408, 32)
    assert len(results) == 3
    assert all(len(row["timesteps"]) == 26 for row in results)
    assert all(len(row["output_counts"]) == 10 for row in results)
    assert results[0]["event_schedule_sha256"] != results[1]["event_schedule_sha256"]


def test_refuse_existing_output_and_bad_trace_counts_without_loading_candidate(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        run_a4_snapshot(tmp_path / "missing", tmp_path / "missing", existing)
    with pytest.raises(ValueError, match="diagnostic_validation_count"):
        run_a4_snapshot(tmp_path / "missing", tmp_path / "missing", tmp_path / "new", diagnostic_validation_count=0)


def test_unverified_candidate_is_not_a_snapshot(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_a4_snapshot(tmp_path / "missing", tmp_path / "missing", tmp_path / "new")
    assert not (tmp_path / "new").exists()
