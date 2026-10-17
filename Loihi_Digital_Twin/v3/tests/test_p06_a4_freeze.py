"""P06-A4.2 static DDR freeze: rejection + accepted ABI bank equivalence.

All success fixtures use a synthetic non-trained network. The pinned hash
audit and trained checkpoint can only complete on the user's accepted
native artifacts. Never relabel synthetic data as trained accuracy.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from loihi_twin_v2.ddr_abi import (
    P02_DDR_CONTEXT_STRIDE_BYTES, build_initial_ddr_context_record,
    parse_ddr_context_header,
)
from loihi_twin_v2.hardware_p08 import BackingLogicalContextImage
from loihi_twin_v2.p06_a3_training import TrainSettings, initialize_model
from loihi_twin_v2.p06_a4_snapshot import compile_and_check_traces
from loihi_twin_v2.p06_a4_freeze import (
    A4_FREEZE_SCHEMA, DDRBIN, EXPECTED_IMAGE, EXPECTED_STREAMS,
    _verify_ddr_matches_p03_words, audit_snapshot, freeze_static_ddr,
)


def test_frozen_hash_list_matches_user_pasted_p06_a4_1_result():
    assert EXPECTED_IMAGE == {
        "axon_bindings": 816, "compartments": 42, "logical_core_id": 0,
        "profile": "p03-k26-one-core-sat24-v1-compat",
        "route_descriptors": 32, "route_words": 32, "synapse_words": 25408,
    }
    assert len(EXPECTED_STREAMS) == 6
    assert EXPECTED_STREAMS["synapses_le64.bin"] == (
        203264, "d83b4e401cae33f92a2cba7c53f2f681453f88395b65d503c2c590f6c60e31d7"
    )
    assert EXPECTED_STREAMS["compartment_config_le128.bin"][0] == 42 * 16
    assert EXPECTED_STREAMS["compartment_state_le64.bin"][0] == 42 * 8
    assert EXPECTED_STREAMS["axon_index_le16_word_le64.bin"][0] == 816 * (2 + 8)
    assert EXPECTED_STREAMS["route_descriptor_index_le16_word_le32.bin"][0] == 32 * (2 + 4)
    assert EXPECTED_STREAMS["route_words_le32.bin"][0] == 32 * 4
    assert A4_FREEZE_SCHEMA == "p06-a4-p02-ddr-static-seed-v1"
    assert DDRBIN == "core0_initial_p02_ddr_512k.bin"


def test_synthetic_one_core_ddr_is_512k_and_matches_p03_banks():
    model = initialize_model(TrainSettings())
    img, compiled, traces = compile_and_check_traces(model, ())
    assert traces == ()
    record = build_initial_ddr_context_record(
        BackingLogicalContextImage(logical_core_id=0, image=img)
    )
    assert len(record) == P02_DDR_CONTEXT_STRIDE_BYTES == 524288
    header = parse_ddr_context_header(record, verify_payload=True)
    assert header.logical_core_id == 0
    assert (header.compartment_count, header.synapse_count, header.route_count) == (42, 25408, 32)
    _verify_ddr_matches_p03_words(record, img)
    corrupt = bytearray(record)
    corrupt[0x1000] ^= 1
    with pytest.raises(ValueError, match="SHA-256"):
        parse_ddr_context_header(bytes(corrupt), verify_payload=True)


def test_failing_snapshot_audit_does_not_create_any_output(tmp_path):
    candidate = tmp_path / "absent-candidate"
    snapshot = tmp_path / "snapshot"
    output = tmp_path / "output"
    snapshot.mkdir()
    with pytest.raises(FileNotFoundError):
        freeze_static_ddr(candidate, snapshot, output)
    assert not output.exists()


def test_refuse_overwrite_before_snapshot_and_checkpoint_access(tmp_path):
    destination = tmp_path / "output"
    destination.mkdir()
    with pytest.raises(FileExistsError, match="output exists"):
        freeze_static_ddr(tmp_path / "missing", tmp_path / "missing", destination)


def test_incorrect_snapshot_schema_fails_closed(tmp_path):
    snap = tmp_path / "snapshot"
    snap.mkdir()
    (snap / "a4_software_snapshot_manifest.json").write_text(
        json.dumps({"schema": "forged"}), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="wrong P06-A4.1"):
        audit_snapshot(snap)


def test_pinned_hash_metadata_cannot_replace_missing_streams(tmp_path):
    snap = tmp_path / "snapshot"
    snap.mkdir()
    (snap / "a4_software_snapshot_manifest.json").write_text(
        json.dumps({
            "schema": "p06-a4-trained-p03-software-word-freeze-candidate-v1",
            "status": "SOFTWARE_WORD_SNAPSHOT / PHYSICAL_GATE_NOT_RUN",
            "accepted_training_candidate_sha256":
                "0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88",
            "accepted_integer_weights_sha256":
                "1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b",
            "training_best_epoch": 8, "training_best_validation_accuracy": 0.9439,
            "training_validation_go_floor": 0.60,
            "canonical_dataset_manifest": {
                "train_indices_le32_sha256":
                    "1cbcb0b2bf481958d6c917ea6d70fa44a20839406f0c824540f8e691edfdd851",
                "validation_indices_le32_sha256":
                    "3b9520013f30742c3818f55024ea39e3e0632113c487c589fdfbb73c7d274831",
                "official_test_set": "sealed: no t10k archives opened",
            },
            "encoder": "p06-uint8-quota-phase17-v1",
            "readout": "p06-26tick-count-argmax-first-v1",
            "total_timesteps": 26, "reset_per_image": True,
            "image": EXPECTED_IMAGE,
            "packet_gate": {
                "frames": 5, "timesteps_per_frame": 26,
                "status": "ALL_TRACES_EXACTLY_EQUAL",
            },
            "official_test_status": "SEALED / NOT OPENED",
            "hardware_status": "NO PHYSICAL FPGA TEST / NO A53 DDR PAGE IMAGE",
            "packed_word_streams": {
                name: {"bytes": size, "sha256": sha}
                for name, (size, sha) in EXPECTED_STREAMS.items()
            },
        }), encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError):
        audit_snapshot(snap)
