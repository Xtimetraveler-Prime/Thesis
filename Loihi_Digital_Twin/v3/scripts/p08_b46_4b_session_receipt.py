#!/usr/bin/env python3
"""B4.6.4b read-only per-session REAL capture acceptance and hash-chained ledger.

NO hardware execution, JTAG or Vivado. Independent original A/B physical
verifier must have run on THIS NEW dedicated capture first. Power-cycle flags
are explicit operator attestations only; no electrical sensor proof is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import p08_b46_4b_six_session_plan as plan

SCHEMA = "p08-b46-six-independent-coldboot-sequential-session-ledger-v1"
A_OLD_PHYSICAL_SHA = plan.PINS["a_prior_independent"]
B_OLD_PHYSICAL_SHA = plan.PINS["b_prior_independent"]


class SessionNoGo(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise SessionNoGo("NO-GO: " + why)


def sha(path: Path) -> str:
    need(path.is_absolute() and path.is_file() and not path.is_symlink(),
         "file must be regular absolute and non-symlink: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def outside(root: Path, project: Path) -> None:
    need(root.is_absolute() and not root.is_symlink() and
         not root.resolve().is_relative_to(project.resolve()) and
         not root.resolve().is_relative_to(Path("/tmp")) and
         not root.resolve().is_relative_to(Path("/var/tmp")),
         "external durable non-symlink path required, outside Git and temp dirs")


def verify_raw(run: Path, rel: str, expected: str, label: str) -> str:
    need(isinstance(expected, str) and len(expected) == 64,
         label + " missing signed original raw SHA")
    f = run / rel
    need(f.resolve().is_relative_to(run.resolve()) and sha(f) == expected,
         label + " actual physical bytes differ from independent original report")
    return expected


def review(plan_path: Path, expected_plan_sha: str, slot: int, run: Path,
           independent: Path, preflight: Path, previous: Path | None,
           coldboot_before: str, powercycle_after: str, out: Path) -> dict:
    project = Path(__file__).resolve().parents[1]
    outside(plan_path, project)
    outside(independent, project)
    outside(preflight, project)
    outside(run, project)
    outside(out, project)
    need(run.is_dir() and not run.is_symlink(), "new original capture directory required")
    need(out.parent.is_dir() and not out.exists() and not out.is_symlink(),
         "new no-overwrite standalone external signed receipt path required")
    need(isinstance(expected_plan_sha, str) and len(expected_plan_sha) == 64 and
         sha(plan_path) == expected_plan_sha, "strict external study plan SHA mismatch")
    study = json.loads(plan_path.read_text())
    need(study.get("schema") == plan.SCHEMA and
         study.get("read_only_PC_inputs_sha256") == plan.PINS and
         study.get("preregistered_exact_order") == "A B / B A / A B" and
         study.get("accepted_old_standalone_sessions_count_toward_NEW_ABBAAB") == 0 and
         study.get("all_new_session_authorizations_granted") is False and
         study.get("all_six_new_sessions_accepted") is False and
         study.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED",
         "original hash-pinned PC study-plan design/fail-closed state changed")
    slots = study.get("proposed_six_slots")
    need(isinstance(slots, list) and len(slots) == 6 and
         isinstance(slot, int) and not isinstance(slot, bool) and 1 <= slot <= 6,
         "exact six independent sessions and valid slot required")
    role = plan.ORDER[slot - 1]
    need(all(isinstance(s, dict) and s.get("slot") == i + 1 and
             s.get("arm") == (plan.A_ARM if arm == "A" else plan.B_ARM) and
             s.get("new_independently_accepted_session_receipt") is False
             for i, (s, arm) in enumerate(zip(slots, plan.ORDER))),
         "original planned A/B six-slot design tampered")
    need(run.name.startswith(f"p08_b46_s{slot:02d}_{role}_"),
         "new physical evidence directory must identify exact slot and arm")
    need(coldboot_before == "OPERATOR_CONFIRMED_NEW_INDEPENDENT_COLD_BOOT" and
         powercycle_after == "OPERATOR_CONFIRMED_POWER_CYCLE_AFTER_ANY_JTAG",
         "before-session independent coldboot and after-JTAG physical recovery must each be explicitly operator-attested")
    need(preflight != independent and preflight != plan_path and run != plan_path,
         "new independent per-session files must be distinct")
    log = preflight.read_text()
    if role == "A":
        need("P08_B46_REBUILT_A21_ORIGINAL_1024_OFFLINE_PREFLIGHT_PASS=1" in log and
             "P08_B46_PREFLIGHT_AUTHORIZES_PHYSICAL_JTAG=0" in log and
             "P08_B46_REBUILT_A21_KV260_PHYSICAL_STATUS=NOT_RUN" in log,
             "new A offline original source/ELF stage preflight log missing")
    else:
        need("P08_B45_PERF_FULL1024_ORIGINAL_SOURCES_AND_REAL_ELF_OFFLINE_PASS=1" in log and
             "P08_B45_PERF_BOARD_VISITED=0" in log and
             "P08_B45_PERF_DESTRUCTIVE_JTAG_NOT_AUTHORIZED_BY_PREFLIGHT=1" in log,
             "new B once V2 original source/ELF preflight log missing")

    evidence = json.loads(independent.read_text())
    evidence_sha = sha(independent)
    need(evidence_sha != (A_OLD_PHYSICAL_SHA if role == "A" else B_OLD_PHYSICAL_SHA),
         "old standalone A or B physical report cannot count as NEW study session")
    raw = {}
    if role == "A":
        need(evidence.get("schema") == plan.A_SCHEMA and
             evidence.get("new_rebuilt_A2_1_distinct_ELF_SHA256") ==
                 plan.PINS["a_rebuilt_elf"] and
             evidence.get("original_P07_all_1024_independent_packed_neural_oracle") == "PASS" and
             evidence.get("original_P07_selected_26x42_neural_trace") == "EXACT" and
             evidence.get("new_A53_image_sidecar_crc_and_cntfrq") == "PASS" and
             evidence.get("ordinary_frames") == 1023 and
             evidence.get("special_trace_ordinal_excluded") == 1023 and
             evidence.get("new_A_candidate_physically_revalidated_for_THIS_1024_session") is True and
             evidence.get("B46_six_repeated_A_B_auth_once_sessions_accepted") is False and
             evidence.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED" and
             (run / "attempt_exit_status.txt").read_text().strip() == "script_exit_status=0",
             "original NEW A2.1 standalone 1024 physical/neural/trace independent report invalid")
        sources = evidence.get("source_sha256", {})
        for label, relative in (
            ("physical_identity", "physical_identity.txt"),
            ("actual_real_A53_terminal_log", "a53_run.log"),
            ("actual_real_A53_journal", "p07_a4_journal_1m.bin"),
            ("actual_real_A53_selected_trace", "p07_a4_trace_64k.bin"),
            ("actual_real_A53_timing", "p08_a2_1_images_1m.bin"),
        ):
            raw[label] = verify_raw(run, relative, sources.get(label), label)
        hz = evidence.get("original_A53_observed_CNTFRQ_EL0_hz")
        median = evidence.get("original_A2_1_image_service_median_ms")
    else:
        need(evidence.get("schema") == plan.B_SCHEMA and
             evidence.get("experiment") == "once" and
             evidence.get("genuine_new_mode_specific_A53_ELF_sha256") ==
                 plan.PINS["b_auth_once_elf"] and
             evidence.get("new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar") is True and
             evidence.get("new_all_1024_A53_timing_and_reset_profiles_valid") is True and
             evidence.get("new_all_27_post_run_backup_records_identical_to_original") is True and
             evidence.get("last_trace_ordinal_1023_excluded_from_ordinary_performance") is True and
             evidence.get("hardware_DDR_backup_protection_proven") is False and
             evidence.get("original_OFFICIAL_MNIST_TEST") == "SEALED_NOT_ACCESSED" and
             (run / "stage.txt").read_text().strip() ==
                 "B45_PERF1024_NEURAL_AND_POSTBACKUP_PRESERVED_PRELIMINARY_PASS_REBOOT_REQUIRED",
             "NEW B authentic-once full1024 independent JTAG/FNV/backup record invalid")
        for label, relative in (
            ("journal_sha256", "performance1024_capture/journal1024_physical.bin"),
            ("timing_sha256", "performance1024_capture/timing1024_physical.bin"),
            ("reset_sidecar_sha256", "performance1024_capture/reset_profile1024_physical.bin"),
            ("mailbox_sha256", "performance1024_capture/mailbox_terminal_physical.bin"),
            ("same_session_original_immutable_source_JTAG_receipt_sha256",
             "same_session_six_source_receipt.json"),
        ):
            raw[label] = verify_raw(run, relative, evidence.get(label), label)
        hz = evidence.get("actual_A53_CNTFRQ_hz")
        service = evidence.get("whole_image_service_descriptive_1023")
        need(isinstance(service, dict) and
             service.get("ordinary_frames") == 1023,
             "B ordinary 1023-frame counter statistics not present")
        median = service.get("median_ms")
    need(isinstance(hz, int) and not isinstance(hz, bool) and
         1_000_000 < hz < 2_000_000_000 and
         isinstance(median, (int, float)) and not isinstance(median, bool) and
         math.isfinite(median) and median > 0,
         "real per-session A53 frequency or original 1023 median missing")

    if slot == 1:
        need(previous is None, "first session cannot reuse a previous study ledger")
        entries = []
        previous_sha = None
    else:
        need(previous is not None, "prior independently reviewed session ledger required")
        outside(previous, project)
        prev = json.loads(previous.read_text())
        previous_sha = sha(previous)
        entries = prev.get("accepted_sessions")
        need(prev.get("schema") == SCHEMA and
             prev.get("original_study_plan_sha256") == expected_plan_sha and
             isinstance(entries, list) and len(entries) == slot - 1 and
             prev.get("source_only_not_hardware_execution") is True and
             prev.get("exact_last_accepted_slot") == slot - 1 and
             all(isinstance(row, dict) and
                 row.get("slot") == i + 1 and
                 row.get("arm") == (plan.A_ARM if arm == "A" else plan.B_ARM) and
                 row.get("new_independent_original_oracle_and_timing_report_pass") is True and
                 row.get("operator_self_attests_power_cycle_after_JTAG") is True
                 for i, (row, arm) in enumerate(zip(entries, plan.ORDER[:slot-1]))),
             "prior ledger chain order or accepted session status invalid")
        need(run.as_posix() not in [row.get("new_physical_capture_dir") for row in entries] and
             evidence_sha not in [row.get("independent_report_sha256") for row in entries],
             "reused previous physical capture/report cannot be a new coldboot")
    entry = {
        "slot": slot,
        "pair": (slot - 1) // 2 + 1,
        "arm": plan.A_ARM if role == "A" else plan.B_ARM,
        "new_physical_capture_dir": str(run),
        "new_independent_original_oracle_and_timing_report_pass": True,
        "independent_report_sha256": evidence_sha,
        "independent_report_path": str(independent),
        "offline_original_source_preflight_log_sha256": sha(preflight),
        "physical_capture_reopened_original_sha256": raw,
        "actual_A53_CNTFRQ_EL0_hz": hz,
        "ordinary_1023_service_median_ms": median,
        "trace_ordinal_1023_excluded": True,
        "operator_self_attests_fresh_coldboot_before_JTAG": True,
        "operator_self_attests_power_cycle_after_JTAG": True,
        "electrical_power_cycle_independently_proven_by_instrument": False,
        "B_hardware_immutable_backup_protected": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }
    answer = {
        "schema": SCHEMA,
        "original_study_plan_sha256": expected_plan_sha,
        "previous_study_ledger_sha256": previous_sha,
        "accepted_sessions": [*entries, entry],
        "exact_last_accepted_slot": slot,
        "accepted_total_sessions": slot,
        "remaining_scheduled_sessions": 6 - slot,
        "source_only_not_hardware_execution": True,
        "physical_capture_performed_externally_by_operator": True,
        "current_slot_independently_verified_from_genuine_capture": True,
        "power_cycles_only_operator_attested_not_electrically_proven": True,
        "six_session_ABC_order_complete": slot == 6,  # NOT statistical acceptance
        "paired_study_statistics_accepted": False,
        "matched_neuron_count_or_PL_only_energy_speedup_claimed": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }
    with out.open("x", encoding="utf-8") as handle:
        json.dump(answer, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return answer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "plan_sha256", "slot", "evidence",
                 "independent", "preflight", "out"):
        parser.add_argument("--" + name.replace("_","-"), required=True,
                            type=int if name == "slot" else
                            str if name == "plan_sha256" else Path)
    parser.add_argument("--previous-ledger", type=Path)
    parser.add_argument("--operator-new-coldboot", required=True)
    parser.add_argument("--operator-after-jtag-power-cycle", required=True)
    args = parser.parse_args(argv)
    try:
        result = review(args.plan, args.plan_sha256, args.slot, args.evidence,
                        args.independent, args.preflight, args.previous_ledger,
                        args.operator_new_coldboot, args.operator_after_jtag_power_cycle,
                        args.out)
    except (SessionNoGo, OSError, ValueError, TypeError, KeyError) as exc:
        print("P08_B46_NEW_SESSION_INDEPENDENT_LEDGER_NO_GO=" + str(exc), file=sys.stderr)
        return 3
    print("P08_B46_NEW_ABBAAB_SESSION_ORIGINAL_NEURAL_AND_A53_RECEIPT_PASS=1")
    print("P08_B46_CURRENT_NEW_SESSION_ACCEPTED_SLOT=" + str(args.slot))
    print("P08_B46_OPERATOR_REBOOT_ATTESTATION_NOT_INSTRUMENT_PROOF=1")
    print("P08_B46_NEW_SESSION_JTAG_EXECUTED_BY_THIS_TOOL=0")
    print("P08_B46_ABBAAB_NEW_HARDWARE_SESSION_COUNT=" + str(result["accepted_total_sessions"]))
    print("P08_B46_SIX_RUN_STUDY_STATISTICS_ACCEPTED=0")
    print("P08_B46_SIX_SESSION_LEDGER=" + str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
