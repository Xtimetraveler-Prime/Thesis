from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from neuromorphic_twin.m13_closure import (
    M13_6_CLOSURE_SCHEMA,
    M13_6_CLOSURE_STATUS,
    VALIDATED_BRANCH_HEAD,
    build_m13_6_closure,
    candidate_sha256,
    validate_m13_6_closure,
)

ROOT = Path(__file__).resolve().parents[1]


def _path(name: str) -> Path:
    return ROOT / "references" / name


def _load(name: str) -> dict:
    return json.loads(_path(name).read_text(encoding="utf-8"))


def _candidate_inputs() -> tuple[dict, bytes, dict, dict, dict]:
    candidate_path = _path("m13_6_findings.json")
    candidate_bytes = candidate_path.read_bytes()
    return (
        json.loads(candidate_bytes.decode("utf-8")),
        candidate_bytes,
        _load("m13_2_feature_crosswalk.json"),
        _load("m13_4_candidate_findings.json"),
        _load("m13_5_closure.json"),
    )


def test_closure_accepts_independently_validated_candidate_without_mutation() -> None:
    closure = build_m13_6_closure(*_candidate_inputs())

    assert closure["schema"] == M13_6_CLOSURE_SCHEMA
    assert closure["status"] == M13_6_CLOSURE_STATUS
    assert closure["milestones"] == {"M13.6": "complete", "M13": "complete"}
    assert closure["validated_candidate"]["branch_head"] == VALIDATED_BRANCH_HEAD
    assert closure["validated_candidate"]["disposition"] == (
        "accepted_without_mutation_after_independent_reproduction"
    )


def test_closure_binds_exact_candidate_bytes() -> None:
    candidate, candidate_bytes, crosswalk, directed, hardware = _candidate_inputs()
    closure = build_m13_6_closure(
        candidate, candidate_bytes, crosswalk, directed, hardware
    )

    assert closure["validated_candidate"]["sha256"] == candidate_sha256(candidate_bytes)
    with pytest.raises(ValueError, match="tracked M13.6 closure"):
        validate_m13_6_closure(
            closure,
            candidate,
            candidate_bytes + b"\n",
            crosswalk,
            directed,
            hardware,
        )


def test_closure_records_independent_local_reproduction() -> None:
    closure = build_m13_6_closure(*_candidate_inputs())
    validation = closure["independent_validation"]

    assert validation["candidate_regeneration"]["reported_result"].startswith(
        "M13.6 findings candidate PASS"
    )
    assert validation["byte_identity_check"]["reported_result"] == "success_with_no_output"
    assert validation["focused_tests"]["passed"] == 9
    assert validation["full_project_regression"]["passed"] == 367
    assert validation["working_tree_note"]["reported_untracked_paths"] == [
        "Neuromorphic",
        "Neuromorphic Digital Twin/rtl/core_v1/xvlog.pb",
    ]


def test_zero_ab_result_closes_change_control_without_m12_rerun() -> None:
    closure = build_m13_6_closure(*_candidate_inputs())
    change = closure["change_control"]

    assert change["observed_trigger_findings"] == 0
    assert change["project_baseline_status"] == "frozen_unchanged"
    assert change["normative_specification_update_required"] is False
    assert change["hls_rtl_regeneration_required"] is False
    assert change["m12_evidence_superseded"] is False
    assert change["m12_physical_revalidation_required"] is False


def test_closure_rejects_candidate_that_would_reopen_change_control() -> None:
    candidate, candidate_bytes, crosswalk, directed, hardware = _candidate_inputs()
    candidate = deepcopy(candidate)
    candidate["summary"]["class_A_or_B_findings"] = 1

    with pytest.raises(ValueError):
        build_m13_6_closure(
            candidate,
            candidate_bytes,
            crosswalk,
            directed,
            hardware,
        )


def test_tracked_closure_matches_deterministic_record_when_present() -> None:
    closure_path = _path("m13_6_closure.json")
    if not closure_path.exists():
        pytest.skip("closure record is generated only after independent validation")

    validate_m13_6_closure(_load("m13_6_closure.json"), *_candidate_inputs())
