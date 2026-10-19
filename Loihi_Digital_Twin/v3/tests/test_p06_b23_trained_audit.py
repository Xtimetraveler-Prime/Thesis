"""B2.3 read-only audit contract and fail-closed negative tests.

The real H=1000 user checkpoint lives only on the user's PC; these tests
never forge a B2.2 trained numerical PASS or touch MNIST TEST archives.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from loihi_twin_v2.p06_b23_trained_audit import (
    B23AuditError, B23AuditedCandidate, PINNED_B22_WEIGHTS_SHA256,
    PINNED_B22_INTEGER_SHA256, audit_candidate,
)


def _manifest(*, file_sha=PINNED_B22_WEIGHTS_SHA256,
              integer_sha=PINNED_B22_INTEGER_SHA256):
    return {
        "weights_file_sha256": file_sha,
        "effective_integer_weights_sha256": integer_sha,
        "architecture": [784, 1000, 10], "best_epoch": 6,
        "best_validation": {
            "count": 10000, "accuracy": 0.9708, "all_silent_count": 0,
        },
        "candidate_go": True,
    }


def _mock_checkpoint(monkeypatch, manifest):
    import loihi_twin_v2.p06_b23_trained_audit as a
    def fake_load(_):
        return SimpleNamespace(eval=lambda: None,
                               to_network_spec=lambda: (_ for _ in ()).throw(
                                   AssertionError("must reject before source graph build"))), manifest
    monkeypatch.setattr(a, "load_candidate", fake_load)


@pytest.mark.parametrize("bad", (
    {"file_sha": "wrong"},
    {"integer_sha": "wrong"},
    {"accuracy": 0.9707},
    {"best_epoch": 5},
    {"architecture": [784, 999, 10]},
    {"all_silent_count": 1},
))
def test_rejects_different_weight_bytes_quantized_values_or_validation_before_compilation(monkeypatch, bad):
    source = _manifest(file_sha=bad.get("file_sha", PINNED_B22_WEIGHTS_SHA256),
                       integer_sha=bad.get("integer_sha", PINNED_B22_INTEGER_SHA256))
    if "accuracy" in bad:
        source["best_validation"]["accuracy"] = bad["accuracy"]
    if "best_epoch" in bad:
        source["best_epoch"] = bad["best_epoch"]
    if "architecture" in bad:
        source["architecture"] = bad["architecture"]
    if "all_silent_count" in bad:
        source["best_validation"]["all_silent_count"] = bad["all_silent_count"]
    _mock_checkpoint(monkeypatch, source)
    with pytest.raises(B23AuditError, match="checkpoint|validation provenance"):
        audit_candidate("/unused/read_only_test_path")


@pytest.mark.parametrize("ordinals", (
    (1, 0), (1, 1), (-1,), (10000,), (True,), [0],
))
def test_rejects_invalid_validation_sample_selection(monkeypatch, ordinals):
    _mock_checkpoint(monkeypatch, _manifest())
    with pytest.raises(B23AuditError, match="validation ordinals"):
        audit_candidate("/unused/read_only_test_path",
                        data_dir="/unused/train_dir", validation_ordinals=ordinals)


def test_requires_train_only_source_if_validation_parity_selected(monkeypatch):
    _mock_checkpoint(monkeypatch, _manifest())
    with pytest.raises(B23AuditError, match="TRAIN-only data-dir"):
        audit_candidate("/unused/candidate", validation_ordinals=(0,))


def test_zero_frames_report_is_explicitly_structural_only():
    report = B23AuditedCandidate(
        manifest=_manifest(), network_sha256="source",
        deployment_sha256="compiled", capacity_audit_sha256="audit",
        core_count=27, backing_bytes=14155776, worst_current_events=1000,
        validated_frames=()).report()
    assert report["validation_frame_count"] == 0
    assert report["full_dense_26_tick_numerics_executed_for_selected_frames"] is False
    assert report["checkpoint_frozen"] is False
    assert report["physical_kv260_execution"] == "NOT_TESTED"
    assert report["official_mnist_test_status"] == "SEALED_NOT_ACCESSED"


def test_report_frames_do_not_impersonate_full_validation_or_official_test():
    row = {
        "validation_ordinal": 0, "canonical_train_idx": 12,
        "all_26_ticks_full_neuron_parity": True,
    }
    report = B23AuditedCandidate(
        manifest=_manifest(), network_sha256="source", deployment_sha256="compiled",
        capacity_audit_sha256="audit", core_count=27,
        backing_bytes=14155776, worst_current_events=1000,
        validated_frames=(row,)).report()
    assert report["validation_frame_count"] == 1
    assert report["full_dense_26_tick_numerics_executed_for_selected_frames"] is True
    assert report["candidate_validation_count"] == 10000
    assert report["validation_frames"][0]["validation_ordinal"] == 0
    assert report["B2_4_freeze_accepted"] is False
