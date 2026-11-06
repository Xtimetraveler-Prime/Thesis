#!/usr/bin/env python3
"""P08-B4.6.4b signed-input six-session PRE-REGISTRATION (PC ONLY).

Produces a read-only, fail-closed source and pre-existing-evidence plan.
NEVER drives a board, launches a physical runner, or grants JTAG permission.
Previously accepted A and B standalone runs do not count as study sessions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

SCHEMA = "p08-b46-six-new-coldboot-auth-once-A-B-study-readiness-plan-v1"
BOUNDARY_SCHEMA = "p08-b46-a-vs-b-auth-once-service-boundary-static-audit-v1"
SOURCE_SCHEMA = "p08-b46-reconstructed-A21-vs-B-auth-once-offline-source-gate-v1"
A_SCHEMA = "p08-b46-rebuilt-A21-1024-independent-physical-neural-and-timing-v1"
B_SCHEMA = "p08-b45-unprotected-full1024-independent-real-jtag-v1"
A_ARM = "A_REBUILT_A21_SEPARATELY_PHYSICALLY_ACCEPTED_42_NEURONS_26_DISPATCHES"
B_ARM = "B_AUTH_ONCE_UNPROTECTED_V2_1010_NEURONS_702_DISPATCHES"
ORDER = ("A", "B", "B", "A", "A", "B")
PINS = {
    "boundary": "41ea9f2958e9e31aaa120d368b1f325f16bc51ed63834c2748b2dde38d6cb430",
    "matched_source": "ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56",
    "a_prior_independent": "b57f20beb80943fb8d6b526a2e119cd12b17641db6fa7e55dbab8ca9f2f148a6",
    "b_prior_independent": "06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a",
    "a_rebuilt_elf": "fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793",
    "b_auth_once_elf": "a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85",
}
A_MARKER = b"P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1"
B_MARKER = b"P08_B45_PERF_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V2"
B_BAD_MARKER = b"P08_B45_PERF_UNCHECKED_ORIGINAL_27CORE_1024_A53_V2"

class StudyNoGo(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise StudyNoGo("NO-GO: " + why)


def sha(path: Path) -> str:
    need(path.is_absolute() and path.is_file() and
         not path.is_symlink(), "absolute regular non-symlink file required: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def admitted_file(path: Path, label: str) -> None:
    need(sha(path) == PINS[label], "original signed SHA drift: " + label)


def json_file(path: Path, label: str) -> dict:
    admitted_file(path, label)
    body = json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(body, dict), "JSON object required: " + label)
    return body


def prepare(boundary: Path, matched_source: Path, a_prior: Path,
            b_prior: Path, a_elf: Path, b_elf: Path) -> dict:
    bounds = json_file(boundary, "boundary")
    source = json_file(matched_source, "matched_source")
    a_real = json_file(a_prior, "a_prior_independent")
    b_real = json_file(b_prior, "b_prior_independent")
    admitted_file(a_elf, "a_rebuilt_elf")
    admitted_file(b_elf, "b_auth_once_elf")
    need(a_elf.name == "p08_a2_board.elf" and A_MARKER in a_elf.read_bytes(),
         "new distinct rebuilt A2.1 actual A53 ELF marker/basename mismatch")
    elf_b = b_elf.read_bytes()
    need(b_elf.name == "p08_b45_perf_once_full1024.elf" and
         B_MARKER in elf_b and B_BAD_MARKER not in elf_b,
         "B must be genuine V2 authenticate-once, not unchecked or original B4.4")
    need(bounds.get("schema") == BOUNDARY_SCHEMA and
         bounds.get("source_only_static_audit_pass") is True and
         bounds.get("both_broad_entry_to_neural_journal_commit_scope_present") is True and
         bounds.get("A_B_physical_timer_boundary_equivalence_proven") is False and
         bounds.get("new_A_B_physical_sessions_performed") is False and
         bounds.get("new_six_session_hardware_authorization_granted") is False and
         bounds.get("prior_A21_standalone_run_is_one_of_six_future_counterbalanced_sessions") is False and
         bounds.get("rebuilt_A21_new_accepted_ELF_SHA256") == PINS["a_rebuilt_elf"] and
         bounds.get("prior_A21_rebuilt_one_1024_physical_report_SHA256") ==
             PINS["a_prior_independent"] and
         bounds.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED",
         "signed A/B static boundary source admission or safeguards invalid")
    need(source.get("schema") == SOURCE_SCHEMA and
         source.get("selected_A_real_elf_sha256") == PINS["a_rebuilt_elf"] and
         source.get("optimized_B_once_full1024_elf_sha256") == PINS["b_auth_once_elf"] and
         source.get("identical_original_TRAIN_1024_source_index_and_raw_pixel_SHA") is True and
         source.get("frame_count_each") == 1024 and
         source.get("ordinary_frames_each") == 1023 and
         source.get("excluded_trace_ordinal") == 1023 and
         source.get("six_new_physical_JTAG_runs_authorized") is False and
         source.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED",
         "original signed A-vs-B matched TRAIN 1024 source-gate invalid")
    scheduled = source.get("planned_six_independently_rebooted_sessions")
    need(isinstance(scheduled, list) and len(scheduled) == 6 and
         all(isinstance(row, dict) and row.get("sequence_number") == i + 1 and
             row.get("pair") == i // 2 + 1 and
             row.get("arm") == (
                 "A_REBUILT_A21_CANDIDATE_42_NEURONS_26_DISPATCHES"
                 if arm == "A" else B_ARM) and
             row.get("fresh_coldboot_required") is True and
             row.get("individual_physical_JTAG_permission_granted") is False and
             row.get("new_signed_physical_capture_accepted") is False
             for i, (arm, row) in enumerate(zip(ORDER, scheduled))),
         "original pre-registered six-slot counterbalance tampered")
    need(a_real.get("schema") == A_SCHEMA and
         a_real.get("new_rebuilt_A2_1_distinct_ELF_SHA256") == PINS["a_rebuilt_elf"] and
         a_real.get("original_P07_all_1024_independent_packed_neural_oracle") == "PASS" and
         a_real.get("original_P07_selected_26x42_neural_trace") == "EXACT" and
         a_real.get("new_A53_image_sidecar_crc_and_cntfrq") == "PASS" and
         a_real.get("ordinary_frames") == 1023 and
         a_real.get("special_trace_ordinal_excluded") == 1023 and
         a_real.get("new_A_candidate_physically_revalidated_for_THIS_1024_session") is True and
         a_real.get("old_original_historical_A21_ELF_reproduced") is False and
         a_real.get("A_vs_B_auth_once_service_timer_boundaries_matched") is False and
         a_real.get("B46_six_repeated_A_B_auth_once_sessions_accepted") is False and
         a_real.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED" and
         isinstance(a_real.get("original_A53_observed_CNTFRQ_EL0_hz"), int) and
         a_real["original_A53_observed_CNTFRQ_EL0_hz"] > 0,
         "new rebuilt A2.1 prior independent 1024 evidence invalid")
    need(b_real.get("schema") == B_SCHEMA and
         b_real.get("experiment") == "once" and
         b_real.get("genuine_new_mode_specific_A53_ELF_sha256") == PINS["b_auth_once_elf"] and
         b_real.get("new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar") is True and
         b_real.get("new_all_1024_A53_timing_and_reset_profiles_valid") is True and
         b_real.get("new_all_27_post_run_backup_records_identical_to_original") is True and
         b_real.get("last_trace_ordinal_1023_excluded_from_ordinary_performance") is True and
         b_real.get("hardware_DDR_backup_protection_proven") is False and
         b_real.get("paired_AB_BA_AB_six_session_speedup_not_established") is True and
         b_real.get("original_OFFICIAL_MNIST_TEST") == "SEALED_NOT_ACCESSED" and
         isinstance(b_real.get("actual_A53_CNTFRQ_hz"), int) and
         b_real["actual_A53_CNTFRQ_hz"] > 0 and
         isinstance(b_real.get("whole_image_service_descriptive_1023"), dict) and
         b_real["whole_image_service_descriptive_1023"].get("ordinary_frame_count") == 1023,
         "B4.5 V2 original once standalone independent evidence invalid")

    slots = []
    for i, arm in enumerate(ORDER):
        slots.append({
            "slot": i + 1,
            "pair": i // 2 + 1,
            "position": "first" if i % 2 == 0 else "second",
            "arm": A_ARM if arm == "A" else B_ARM,
            "fresh_independent_KV260_coldboot_required": True,
            "prior_KV260_JTAG_attempt_power_cycle_independently_confirmed": False,
            "operator_specific_destructive_approval_granted": False,
            "new_unique_external_capture_path_reserved": False,
            "new_original_source_and_ELF_rechecked": False,
            "new_original_1024_neural_oracle_and_trace_verified": False,
            "new_1024_A53_CRC_CNTFRQ_and_1023_ordinary_frames_verified": False,
            "new_B_27_backup_endpoint_equality_verified": False,
            "new_experiment_physical_session_started": False,
            "new_independently_accepted_session_receipt": False,
            "new_session_receipt_sha256": None,
        })
    return {
        "schema": SCHEMA,
        "study": "A rebuilt 42-neuron / B_AUTH_ONCE V2 1010-neuron ORIGINAL TRAIN full-image system service",
        "read_only_PC_inputs_sha256": dict(PINS),
        "old_historical_A2_1_ELF_reproduced": False,
        "A_rebuilt_1024_single_prior_validation_accepted_separately": True,
        "B_auth_once_1024_single_prior_validation_accepted_separately": True,
        "accepted_old_standalone_sessions_count_toward_NEW_ABBAAB": 0,
        "original_1024_identical_TRAIN_image_ids_and_pixel_SHA": True,
        "both_source_A53_entry_through_neural_journal_commit_scope": True,
        "strict_IDENTICAL_physical_timer_scope_proven": False,
        "same_neuron_workload_or_computational_complexity": False,
        "B_memory_backup_XMPU_protection_proven": False,
        "physical_owners_boot_DDR_DMA_exclusivity_proven": False,
        "six_separate_coldboots_required": True,
        "each_session_requires_fresh_risk_review_and_approval": True,
        "mandatory_KV260_power_cycle_after_ANY_JTAG_attempt": True,
        "ordinal_1023_trace_validated_but_excluded_from_ordinary_1023": True,
        "frame_count_per_session": 1024,
        "ordinary_frames_per_session": 1023,
        "preregistered_exact_order": "A B / B A / A B",
        "study_independent_statistical_unit": "3 matched physical session pairs (not 1023 images)",
        "proposed_six_slots": slots,
        "source_only_plan_not_hardware_admission": True,
        "all_new_session_authorizations_granted": False,
        "any_new_B46_AB_physical_session_executed": False,
        "all_six_new_sessions_accepted": False,
        "paired_study_statistics_accepted": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }


def write_plan(result: dict, out: Path, project_root: Path) -> None:
    need(out.is_absolute() and out.parent.is_dir() and not out.is_symlink() and
         not out.exists(), "fresh absolute no-overwrite output path required")
    actual = out.resolve()
    need(not actual.is_relative_to(project_root.resolve()) and
         not any(actual.is_relative_to(p) for p in (Path("/tmp"), Path("/var/tmp"))),
         "durable study plan must be outside checkout, /tmp and /var/tmp")
    with out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("boundary", "matched_source", "a_prior", "b_prior",
                 "a_elf", "b_elf", "out"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = prepare(args.boundary, args.matched_source,
                         args.a_prior, args.b_prior, args.a_elf, args.b_elf)
        write_plan(report, args.out, Path(__file__).resolve().parents[1])
    except (StudyNoGo, OSError, TypeError, KeyError, ValueError) as exc:
        print("P08_B46_SIX_SESSION_PRE_REGISTRATION_PC_NO_GO=" + str(exc),
              file=sys.stderr)
        return 3
    print("P08_B46_SIX_SESSION_PRE_REGISTERED_SOURCE_EVIDENCE_PASS=1")
    print("P08_B46_STANDALONE_PREVIOUS_PHYSICAL_RUNS_COUNTED_AS_NEW=0")
    print("P08_B46_FIRST_SCHEDULED_ARM=A_REBUILT_A2_1")
    print("P08_B46_SIX_NEW_SESSION_JTAG_AUTHORIZED=0")
    print("P08_B46_NEW_AB_BA_AB_PHYSICAL_SESSIONS_PERFORMED=0")
    print("P08_B46_STUDY_PLAN=" + str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
