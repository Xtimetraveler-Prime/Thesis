"""P06-B2.5 native unit checks: policy, pinned freeze provenance and NO-GO.

All fixtures here are small *fabricated dictionaries* to exercise the
B2.5 pure policy checker. They do not substitute for the real user's
33-asset B2.4 freeze or claim to have run a scaled physical KV260.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

import loihi_twin_v2.p06_b25_acceptance as module
from loihi_twin_v2.p06_b24_freeze import (
    B24_SCHEMA, B24_MANIFEST_NAME, B24_PROTOCOL_NAME, PINNED_B23_FRAMES,
    PINNED_B23_SOURCE_SHA256, PINNED_B23_DEPLOYMENT_SHA256,
    PINNED_B23_CAPACITY_SHA256, PINNED_B22_WEIGHTS_SHA256,
    PINNED_B22_INTEGER_SHA256,
)
from loihi_twin_v2.p06_b25_acceptance import (
    B25AcceptanceError, B25_SCHEMA, PINNED_B24_MANIFEST_FILE_SHA256,
    PINNED_B24_CANONICAL_MANIFEST_SHA256, assess_frozen_handoff,
    review_freeze_documents,
)


def _fixtures():
    """Small fake records with pinned names; no actual checkpoint/DDR bytes."""
    shas = [hashlib.sha256(f"fake-core-{i}".encode()).hexdigest()
            for i in range(27)]
    manifest = {
        "schema": B24_SCHEMA,
        "status": "HOST_FROZEN_CANDIDATE_PENDING_NATIVE_ACCEPTANCE",
        "manifest_sha256": PINNED_B24_CANONICAL_MANIFEST_SHA256,
        "checkpoint_frozen": True,
        "user_native_B2_4_accepted": False,
        "official_mnist_test_status": "SEALED_NOT_ACCESSED",
        "physical_kv260_execution": "NOT_TESTED",
        "architecture": [784, 1000, 10],
        "weights_file_sha256": PINNED_B22_WEIGHTS_SHA256,
        "effective_integer_weights_sha256": PINNED_B22_INTEGER_SHA256,
        "source_network_sha256": PINNED_B23_SOURCE_SHA256,
        "deployment_sha256": PINNED_B23_DEPLOYMENT_SHA256,
        "capacity_audit_sha256": PINNED_B23_CAPACITY_SHA256,
        "core_count": 27,
        "backing_bytes": 14155776,
        "ddr_context_sha256": shas,
        "B2_3_parity_validation_ordinals": [0, 1, 2],
        "validation_provenance": {
            "best_epoch": 6, "TRAIN_derived_validation_count": 10000,
            "TRAIN_derived_validation_accuracy": 0.9708,
            "all_silent_validation_count": 0,
        },
    }
    protocol = {
        "schema": "p06-b2.4-sealed-mnist-official-test-protocol-v1",
        "test_population": "canonical MNIST official 10000 TEST images in original IDX order",
        "test_count": 10000, "current_unseal_status": "SEALED_NOT_ACCESSED",
        "no_model_selection_after_unseal": True,
        "board_27_core_run": "NOT_TESTED",
    }
    b23 = {
        "trained_source_network_sha256": PINNED_B23_SOURCE_SHA256,
        "validation_frame_count": 3,
        "validation_frames": [
            {"validation_ordinal": i, "canonical_train_idx": idx,
             "image_sha256": raw, "monolithic_trace_sha256": mono,
             "partitioned_trace_sha256": chip,
             "all_26_ticks_full_neuron_parity": True}
            for i, idx, raw, mono, chip in PINNED_B23_FRAMES
        ],
    }
    cores = [
        {"core_id": i, "record_bytes": 524288,
         "logical_synapse_bytes": 128576 if i < 26 else 0,
         "worst_current_bank_events": 784 if i < 26 else 1000,
         "initial_ddr_sha256": shas[i]}
        for i in range(27)
    ]
    packed = {"manifest": {
        "source_fingerprint": PINNED_B23_SOURCE_SHA256,
        "deployment_fingerprint": PINNED_B23_DEPLOYMENT_SHA256,
        "capacity_audit": {
            "audit_sha256": PINNED_B23_CAPACITY_SHA256,
            "logical_core_count": 27,
            "backing_bytes": 14155776,
            "resident_context_slots": 3, "physical_hls_engines": 1,
            "physical_kv260_execution": "NOT_TESTED", "cores": cores,
        },
    }}
    verified = {
        "manifest_sha256": PINNED_B24_CANONICAL_MANIFEST_SHA256,
        "cores_checked": 27, "files_checked": 33,
        "total_initial_ddr_bytes": 14155776,
        "physical_kv260_execution": "NOT_TESTED",
        "official_mnist_test_status": "SEALED_NOT_ACCESSED",
    }
    return manifest, protocol, b23, packed, verified


def _review(*source):
    return review_freeze_documents(
        *source,
        canonical_hash=PINNED_B24_CANONICAL_MANIFEST_SHA256,
        file_hash=PINNED_B24_MANIFEST_FILE_SHA256,
    )


def test_b25_pins_both_distinct_sha_domains_and_preserves_hardware_no_go():
    documents = _fixtures()
    result = _review(*documents)
    assert result["architecture"] == [784, 1000, 10]
    assert result["connections_full_dense"] == 794000
    assert result["three_26_tick_validation_frames_verified"] == [0, 1, 2]
    assert result["logical_cores"] == 27
    assert result["maximum_per_core_logical_synapse_bytes"] == 128576
    assert result["maximum_per_core_current_bank_events"] == 1000
    assert result["physical_resident_context_slots"] == 3
    assert result["physical_hls_engine_count"] == 1
    assert PINNED_B24_MANIFEST_FILE_SHA256 != PINNED_B24_CANONICAL_MANIFEST_SHA256
    assert len(PINNED_B24_MANIFEST_FILE_SHA256) == 64


@pytest.mark.parametrize("index,key,value", (
    (0, "architecture", [784, 999, 10]),
    (0, "source_network_sha256", "retrained"),
    (0, "ddr_context_sha256", ["f"] * 27),
    (0, "user_native_B2_4_accepted", True),
    (0, "backing_bytes", 512),
    (1, "test_count", 9999),
    (1, "no_model_selection_after_unseal", False),
    (1, "current_unseal_status", "OPENED"),
    (2, "validation_frame_count", 2),
    (3, "deployment_fingerprint", "changed"),
    (4, "cores_checked", 26),
    (4, "physical_kv260_execution", "MISLABELED_AS_EXECUTED"),
))
def test_b25_rejects_changed_source_or_false_test_hardware_claim(index, key, value):
    args = list(_fixtures())
    args[index] = deepcopy(args[index])
    if index == 3:
        args[3]["manifest"][key] = value
    else:
        args[index][key] = value
    with pytest.raises(B25AcceptanceError):
        _review(*args)


def test_b25_rejects_over_budget_synapse_event_or_missing_core():
    for change in ("synapse", "events", "missing", "record_sha"):
        args = list(_fixtures())
        cap = args[3]["manifest"]["capacity_audit"]
        if change == "synapse":
            cap["cores"][0]["logical_synapse_bytes"] = 131073
        elif change == "events":
            cap["cores"][1]["worst_current_bank_events"] = 4097
        elif change == "missing":
            cap["cores"] = cap["cores"][:-1]
        else:
            cap["cores"][26]["initial_ddr_sha256"] = "bad-sha"
        with pytest.raises(B25AcceptanceError):
            _review(*args)


def test_b25_requires_exact_three_original_26_tick_neuron_witnesses():
    docs = list(_fixtures())
    docs[2]["validation_frames"][1]["monolithic_trace_sha256"] = "tampered"
    with pytest.raises(B25AcceptanceError, match="ordinal 1"):
        _review(*docs)


def test_read_only_aggregator_writes_nothing_and_marks_p07b_no_go(tmp_path, monkeypatch):
    import loihi_twin_v2.p06_b25_acceptance as a
    manifest, protocol, b23, packed, verification = _fixtures()
    root = tmp_path / "readonly_copy_fixture"
    root.mkdir()
    for filename, payload in (
        (B24_MANIFEST_NAME, manifest),
        (B24_PROTOCOL_NAME, protocol),
        ("b23_validation_parity.json", b23),
        ("packed_deployment.json", packed),
    ):
        (root / filename).write_text(json.dumps(payload))
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    calls = []
    def fake_verified(path, *, deep=False):
        calls.append((path, deep))
        return verification
    monkeypatch.setattr(a, "verify_frozen_directory", fake_verified)
    monkeypatch.setattr(a, "sha256_file",
                        lambda path: PINNED_B24_MANIFEST_FILE_SHA256)
    report = assess_frozen_handoff(root, deep=True)
    assert calls == [(root, True)]
    assert report["schema"] == B25_SCHEMA
    assert report["B2_5_native_user_accepted"] is False
    assert report["independent_B12_DDR_regeneration_checked"] is True
    assert report["host_go_for_p07b_design_and_planning"] is True
    assert report["go_for_p07b_scaled_physical_execution"] is False
    assert report["go_for_official_mnist_test_unseal"] is False
    assert len(report["blocking_P07B_deliverables"]) >= 6
    assert report["official_TEST_protocol"]["status"] == "SEALED_NOT_ACCESSED"
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
