"""B2.4 no-TEST freeze contract unit tests (no user checkpoint required).

Only real B2.4 CLI run against actual candidate may establish 27 P02
frozen bytes. These tests exercise source-bound evidence, test protocol,
manifest paths and fail-closed behavior entirely on synthetic metadata.
"""
from __future__ import annotations

from pathlib import Path
import json
import os

import pytest

from loihi_twin_v2.p06_b24_freeze import (
    B24FreezeError, B24_MANIFEST_NAME, B24_SCHEMA,
    B24_VALIDATION_ORDINALS, PINNED_B23_FRAMES,
    PINNED_B23_SOURCE_SHA256, PINNED_B23_DEPLOYMENT_SHA256,
    PINNED_B23_CAPACITY_SHA256, PINNED_B22_WEIGHTS_SHA256,
    PINNED_B22_INTEGER_SHA256, _check_b23_against_user_report,
    _safe_asset_path, canonical_sha, freeze_trained_candidate,
    predeclared_official_test_protocol, verify_frozen_directory,
)


def accepted_frame_report():
    return {
        "weights_file_sha256": PINNED_B22_WEIGHTS_SHA256,
        "effective_integer_weights_sha256": PINNED_B22_INTEGER_SHA256,
        "trained_source_network_sha256": PINNED_B23_SOURCE_SHA256,
        "compiled_deployment_sha256": PINNED_B23_DEPLOYMENT_SHA256,
        "capacity_audit_sha256": PINNED_B23_CAPACITY_SHA256,
        "core_count": 27, "initial_ddr_backing_bytes": 14155776,
        "validation_frame_count": 3,
        "official_mnist_test_status": "SEALED_NOT_ACCESSED",
        "validation_frames": [{
            "validation_ordinal": ordinal,
            "canonical_train_idx": idx,
            "image_sha256": img,
            "monolithic_trace_sha256": mono,
            "partitioned_trace_sha256": part,
            "all_26_ticks_full_neuron_parity": True,
        } for ordinal, idx, img, mono, part in PINNED_B23_FRAMES],
    }


def test_exact_user_reported_b23_three_full_26_tick_validation_witnesses():
    report = accepted_frame_report()
    assert B24_VALIDATION_ORDINALS == (0, 1, 2)
    _check_b23_against_user_report(report)
    assert [f["canonical_train_idx"] for f in report["validation_frames"]] == [
        37384, 27347, 20178]
    assert all(a["monolithic_trace_sha256"] != a["partitioned_trace_sha256"]
               for a in report["validation_frames"])
    # These traces have distinct formats; every neural state was checked
    # independently, so differing hash strings are not a mismatch.


@pytest.mark.parametrize("field,value", (
    ("weights_file_sha256", "changed"),
    ("effective_integer_weights_sha256", "changed"),
    ("trained_source_network_sha256", "changed"),
    ("compiled_deployment_sha256", "changed"),
    ("capacity_audit_sha256", "changed"),
    ("core_count", 26),
    ("initial_ddr_backing_bytes", 512),
    ("validation_frame_count", 1),
    ("official_mnist_test_status", "OPENED"),
))
def test_b23_freeze_rejects_changed_source_checkpoint_resources_and_seal(field, value):
    report = accepted_frame_report()
    report[field] = value
    with pytest.raises(B24FreezeError, match="B2.3"):
        _check_b23_against_user_report(report)


@pytest.mark.parametrize("field,value", (
    ("validation_ordinal", 9), ("canonical_train_idx", 0),
    ("image_sha256", "different"), ("monolithic_trace_sha256", "different"),
    ("partitioned_trace_sha256", "different"),
    ("all_26_ticks_full_neuron_parity", False),
))
def test_b23_freeze_requires_original_three_frame_witnesses(field, value):
    report = accepted_frame_report()
    report["validation_frames"][1][field] = value
    with pytest.raises(B24FreezeError, match="ordinal 1"):
        _check_b23_against_user_report(report)


def test_frozen_test_protocol_declares_all_10000_but_cannot_open_official_data():
    p = predeclared_official_test_protocol()
    assert p["test_count"] == 10000
    assert p["model_identity"]["weights_file_sha256"] == PINNED_B22_WEIGHTS_SHA256
    assert p["model_identity"]["trained_network_sha256"] == PINNED_B23_SOURCE_SHA256
    assert p["current_unseal_status"] == "SEALED_NOT_ACCESSED"
    assert p["no_model_selection_after_unseal"] is True
    assert "B2.4 user-native" in p["first_unseal_conditions"][0]
    assert "P07-B" in p["first_unseal_conditions"][1]
    assert p["board_27_core_run"] == "NOT_TESTED"


@pytest.mark.parametrize("path", (
    "../other", "/absolute/path", "a/../foo", "a/./b", "a//b", "", "./file",
))
def test_freeze_rejects_noncanonical_asset_paths(tmp_path, path):
    with pytest.raises(B24FreezeError, match="relative frozen"):
        _safe_asset_path(tmp_path, path)


def test_freeze_rejects_asset_symlink(tmp_path):
    src = tmp_path / "real"
    src.write_bytes(b"payload")
    symlink = tmp_path / "alias"
    symlink.symlink_to(src)
    with pytest.raises(B24FreezeError, match="symlinked"):
        _safe_asset_path(tmp_path, "alias")


def test_canonical_document_digest_independent_of_dict_insertion_order():
    a = {"schema": B24_SCHEMA, "status": "pending", "x": 2}
    b = {"x": 2, "status": "pending", "schema": B24_SCHEMA}
    assert canonical_sha(a) == canonical_sha(b)
    assert canonical_sha(a) != canonical_sha({**a, "x": 3})
    assert len(canonical_sha(a)) == 64


def test_read_only_verifier_rejects_missing_and_modified_manifest(tmp_path):
    with pytest.raises(B24FreezeError, match="manifest missing"):
        verify_frozen_directory(tmp_path)
    manifest = tmp_path / B24_MANIFEST_NAME
    manifest.write_text(json.dumps({"schema": B24_SCHEMA, "manifest_sha256": "x"}))
    with pytest.raises(B24FreezeError, match="checksum mismatch"):
        verify_frozen_directory(tmp_path)


def test_freeze_protects_existing_output_even_before_any_expensive_b23_replay(tmp_path):
    existed = tmp_path / "already_frozen"
    existed.mkdir()
    sentinel = existed / "keep_original.txt"
    sentinel.write_text("never overwrite")
    with pytest.raises(FileExistsError, match="refusing overwrite"):
        freeze_trained_candidate(tmp_path / "checkpoint", tmp_path / "train", existed)
    assert sentinel.read_text() == "never overwrite"


def test_freeze_refuses_missing_output_parent_without_accessing_user_checkpoint(tmp_path):
    dest = tmp_path / "missing_parent" / "new_freeze"
    with pytest.raises(FileNotFoundError, match="parent"):
        freeze_trained_candidate(tmp_path / "ckpt", tmp_path / "train", dest)
