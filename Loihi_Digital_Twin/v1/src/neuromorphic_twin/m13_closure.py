"""M13.6/M13 closure record construction and validation.

The M13.6 candidate findings remain immutable after independent validation. This
module creates a separate closure record that binds the exact candidate bytes to
the independently reported local reproduction and the automated candidate
preflight, while preserving the zero-A/B change-control decision.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from .m13_findings import validate_tracked_m13_6_findings

M13_6_CLOSURE_SCHEMA = "neuromorphic-twin-m13-closure-v1"
M13_6_CLOSURE_STATUS = "validated_complete"
VALIDATED_BRANCH = "agent/m13-6-adjudicate-freeze-findings"
VALIDATED_BRANCH_HEAD = "dedd3adcffd4f6080bfbb17153110539d8d45061"
COMPLETION_DATE = "2026-09-10"


def candidate_sha256(candidate_bytes: bytes) -> str:
    return sha256(candidate_bytes).hexdigest()


def build_m13_6_closure(
    candidate: Mapping[str, Any],
    candidate_bytes: bytes,
    crosswalk: Mapping[str, Any],
    directed: Mapping[str, Any],
    hardware: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the final M13.6/M13 closure around the validated candidate."""

    validate_tracked_m13_6_findings(candidate, crosswalk, directed, hardware)
    summary = candidate["summary"]
    change = candidate["change_control"]

    if summary["class_A_or_B_findings"] != 0:
        raise ValueError("M13 cannot close with an unresolved Class-A/B finding")
    if change["m12_physical_revalidation_required"] is not False:
        raise ValueError("M13 cannot close while M12 physical revalidation is required")
    if change["project_baseline_status"] != "frozen_unchanged":
        raise ValueError("M13 cannot close unless the accepted baseline disposition is frozen_unchanged")

    return {
        "schema": M13_6_CLOSURE_SCHEMA,
        "status": M13_6_CLOSURE_STATUS,
        "completed_on": COMPLETION_DATE,
        "milestones": {"M13.6": "complete", "M13": "complete"},
        "validated_candidate": {
            "path": "references/m13_6_findings.json",
            "schema": candidate["schema"],
            "candidate_status": candidate["status"],
            "branch": VALIDATED_BRANCH,
            "branch_head": VALIDATED_BRANCH_HEAD,
            "sha256": candidate_sha256(candidate_bytes),
            "disposition": "accepted_without_mutation_after_independent_reproduction",
        },
        "evidence_chain": {
            "m13_2_crosswalk": "references/m13_2_feature_crosswalk.json",
            "m13_4_directed_findings": "references/m13_4_candidate_findings.json",
            "m13_5_hardware_closure": "references/m13_5_closure.json",
            "m13_6_candidate": "references/m13_6_findings.json",
        },
        "accepted_summary": deepcopy(summary),
        "change_control": {
            "trigger_classes": ["A", "B"],
            "observed_trigger_findings": change["observed_trigger_findings"],
            "project_baseline_status": change["project_baseline_status"],
            "project_baseline_commit": change["project_baseline_commit"],
            "normative_specification_update_required": change[
                "normative_specification_update_required"
            ],
            "hls_rtl_regeneration_required": change["hls_rtl_regeneration_required"],
            "m12_evidence_superseded": change["m12_evidence_superseded"],
            "m12_physical_revalidation_required": change[
                "m12_physical_revalidation_required"
            ],
            "closure_reason": (
                "The accepted M13 audit contains zero Class-A/B findings. Classes C-G are retained "
                "as architectural/modeling/ambiguity/scope findings and the two Class-H harness "
                "issues were resolved before the accepted M13.4 snapshot. Therefore the validated "
                "M10/M12 FPGA-v1 baseline remains authoritative and no M12 rerun is required."
            ),
        },
        "independent_validation": {
            "date": COMPLETION_DATE,
            "source": "independent local user reproduction from a Linux VS Code terminal",
            "validated_branch": VALIDATED_BRANCH,
            "validated_head": VALIDATED_BRANCH_HEAD,
            "candidate_regeneration": {
                "command": "python3 examples/generate_m13_6_findings.py",
                "reported_result": (
                    "M13.6 findings candidate PASS: crosswalk=19 directed=12 agreements=6 "
                    "adjudications=6 A/B=0 scope=8 m12_revalidation=False"
                ),
            },
            "byte_identity_check": {
                "command": (
                    "cmp references/m13_6_findings.json "
                    "build/m13_6/m13_6_findings.json"
                ),
                "reported_result": "success_with_no_output",
            },
            "focused_tests": {
                "command": (
                    "python3 -m pytest --override-ini addopts='' -q "
                    "tests/test_m13_6_findings.py"
                ),
                "passed": 9,
                "elapsed_seconds_reported": 0.12,
            },
            "full_project_regression": {
                "command": "python3 -m pytest --override-ini addopts='' -q",
                "passed": 367,
                "elapsed_seconds_reported": 5.63,
            },
            "working_tree_note": {
                "reported_untracked_paths": [
                    "Neuromorphic",
                    "Neuromorphic Digital Twin/rtl/core_v1/xvlog.pb",
                ],
                "interpretation": (
                    "These paths were untracked local artifacts and were not included in the "
                    "source-controlled branch diff or accepted as M13 evidence."
                ),
            },
        },
        "automated_candidate_preflight": {
            "platform": "GitHub Actions Ubuntu 24.04",
            "workflow_run_id": 34494689724,
            "candidate_validation": "pass",
            "byte_identical_regeneration": True,
            "focused_tests_passed": 9,
            "full_project_tests_passed": 367,
            "frozen_baseline_diff_guard": "pass",
        },
        "final_claim_boundary": {
            "project_fpga_v1_baseline": "retained",
            "m12_physical_evidence": "retained_not_superseded",
            "catalyst_hardware_boundary": summary[
                "strongest_catalyst_hardware_boundary"
            ],
            "physical_catalyst_execution_claim": False,
            "universal_loihi_equivalence_claim": False,
            "raw_cross_architecture_efficiency_ranking": False,
        },
        "conclusion": (
            "M13 is complete. The project has been cross-audited against published Loihi evidence, "
            "Brian2Loihi, and pinned Catalyst N1 evidence at explicitly normalized behavioral and "
            "hardware boundaries. The audit found meaningful differences and scope limits but no "
            "supported defect or stronger-evidence contradiction requiring a change to the "
            "physically validated FPGA-v1 computational baseline."
        ),
    }


def validate_m13_6_closure(
    closure: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_bytes: bytes,
    crosswalk: Mapping[str, Any],
    directed: Mapping[str, Any],
    hardware: Mapping[str, Any],
) -> None:
    """Validate the final closure against the exact candidate and upstream evidence."""

    expected = build_m13_6_closure(
        candidate, candidate_bytes, crosswalk, directed, hardware
    )
    if dict(closure) != expected:
        raise ValueError("tracked M13.6 closure does not match deterministic closure record")
