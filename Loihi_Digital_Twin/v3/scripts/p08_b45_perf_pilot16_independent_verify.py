#!/usr/bin/env python3
"""B4.5 independent PC-only unprotected pilot16 original scalar/JTAG audit.

Checks genuine original six-source JTAG receipt, original P03 CPU/PL
transcripts, signed new mode-specific ELF, 16 neural/spike-FNV/timer rows,
16 reset profile rows and all 27 physical backup postrun source bytes.
No actual hardware contact. Security/boot ownership never claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import statistics
import math
import sys
from tempfile import TemporaryDirectory

import p08_b45_perf_pilot16_physical_run as pilot
import p08_b2_4_verify_untrusted_first16 as neural
import p08_b45_sidecar as sidecar


class IndependentNoGo(ValueError):
    pass


def need(condition: bool, reason: str) -> None:
    if not condition:
        raise IndependentNoGo("NO-GO: " + reason)


def sha(path: Path) -> str:
    return pilot.sha(path)


def review(args: argparse.Namespace) -> dict:
    root = args.evidence
    need(root.is_absolute() and root.is_dir() and
         not root.is_symlink(), "original physical evidence directory")
    need(args.out.is_absolute() and args.out.parent.is_dir() and
         not args.out.exists() and not args.out.is_symlink() and
         not args.out.resolve().is_relative_to(pilot.V3.resolve()),
         "fresh external no-overwrite independent report required")
    offline = pilot.admission(args)
    old = json.loads((root / "preflight.json").read_text())
    for key, value in offline.items():
        need(old.get(key) == value,
             "old physical preflight/source binding changed: " + key)
    need(old.get("all_ten_independent_operator_approvals_recorded") is True and
         old.get("physical_JTAG_session_started") is False,
         "explicit signed operator approvals not preserved")
    takeover = root / "a53_takeover_and_ps128.log"
    pilot.b4i.verify_takeover_log(takeover.read_text())
    pilot.b4j.require_programmed_shell(
        (root / "accepted_p03_program.log").read_text())
    staged_log = root / "six_original_ddr_physical_stage.log"
    pilot.marker(staged_log,
                 "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1")
    signed = pilot.b3.readback_original(args.stage, root / "source_physical_readback")
    original_receipt = json.loads((root / "same_session_six_source_receipt.json").read_text())
    need(original_receipt.get("original_six_physical_source_sha256") == signed and
         original_receipt.get("signed_new_benchmark_elf_sha256") ==
         offline["new_performance_pilot16_ELF_sha256"] and
         original_receipt.get("hardware_DDR_backup_immutable") is False,
         "original same-session physical staging receipt inconsistency")

    cap = root / "performance16_capture"
    log = root / "pilot16_a53_physical_run.log"
    for marker in (
        "P08_B45_PERF16_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
        "P08_B45_PERF16_EXACT_16_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B45_PERF16_REAL_16_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
        "P08_B45_PERF16_27_BACKUP_POST_RUN_PHYSICAL_READBACKS_CAPTURED=1",
    ):
        pilot.marker(log, marker)
    after = pilot.check_post_backup(args.stage, cap)
    with TemporaryDirectory(prefix="p08_b45_perf_neural_") as tmp:
        n = neural.verify(
            args.first16, cap / "journal16_physical.bin",
            cap / "timing16_physical.bin",
            cap / "mailbox_terminal_physical.bin",
            Path(tmp) / "neural.json")
    need(n["verified_frames"] == 16 and
         n["all_16_independent_scalar_counters_match"] is True and
         n["all_16_full_26tick_trace_FNV_match"] is True,
         "original 16 software reference neural/FNV mismatch")
    raw = (cap / "reset_profile16_physical.bin").read_bytes()
    reset = sidecar.audit(
        raw, mode=args.experiment, expected_rows=16,
        observed_hz=n["end_mailbox"]["observed_CNTFRQ_EL0_hz"],
        require_protection=False)
    need(reset["backing_backup_guard_provisioned_flag"] == 0,
         "performance mode cannot claim backed memory protection")
    timers = n["timing_frames"]
    need(len(timers) == 16, "missing accepted original service phase timers")
    for i, timer in enumerate(timers):
        words = struct.unpack_from("<64I", raw, i * 256)
        ticks = words[15] | (words[16] << 32)
        need(0 < ticks <= timer["phase_counter_ticks"][0],
             f"frame {i}: new reset span exceeds complete original phase0")
    hz = n["end_mailbox"]["observed_CNTFRQ_EL0_hz"]
    service_ms = [timer["complete_service_counter_ticks"] * 1000.0 / hz
                  for timer in timers]
    need(len(service_ms) == 16 and min(service_ms) > 0,
         "missing positive complete image-service latency")
    sorted_ms = sorted(service_ms)
    service_descriptive = {
        "frames": 16,
        "actual_A53_counter_frequency_hz": hz,
        "service_min_ms": sorted_ms[0],
        "service_median_ms": statistics.median(service_ms),
        "service_p95_nearest_rank_ms":
            sorted_ms[math.ceil(0.95 * len(sorted_ms)) - 1],
        "service_max_ms": sorted_ms[-1],
        "not_same_session_paired_against_original_B44_baseline": True,
    }
    preliminary = json.loads(
        (root / "pilot16_unprotected_physical_preliminary.json").read_text())
    need(preliminary.get("schema") == pilot.SCHEMA and
         preliminary.get("operator_experiment") == args.experiment and
         preliminary.get("all_16_original_scalar_classifier_and_full_26tick_FNV_match") is True and
         preliminary.get("all_27_backup_records_physically_equal_frozen_after_16_images") is True and
         preliminary.get("backup_hardware_write_exclusion_proven") is False and
         preliminary.get("physical_security_guarantee") == "NOT_CLAIMED" and
         preliminary.get("postrun_original_backup_sha256_by_core") == after,
         "online preliminary source report missing or falsely protected")
    record = {
        "schema": "p08-b45-unprotected-perf-pilot16-independent-hardware-evidence-v1",
        "experiment": args.experiment,
        "genuine_A53_ELF_sha256": offline["new_performance_pilot16_ELF_sha256"],
        "frozen_original_stage_sha256": offline["original_27context_PC_stage_sha256"],
        "original_16frame_scalar_oracle_sha256": offline["original_first16_oracle_sha256"],
        "source_preflight_report_sha256": sha(root / "preflight.json"),
        "same_session_JTAG_A53_halt_P03_programming_and_six_original_stages_pass": True,
        "all_16_original_neural_outputs_and_26tick_trace_FNV_equal_scalar": True,
        "all_16_service_timing_and_reset_subspans_verified": True,
        "all_27_postrun_backup_records_byte_identical_to_original": True,
        "postrun_backup_sha256_by_core": after,
        "reset_timing": reset,
        "whole_image_service_timing": service_descriptive,
        "raw_journal_sha256": sha(cap / "journal16_physical.bin"),
        "raw_timing_sha256": sha(cap / "timing16_physical.bin"),
        "raw_reset_profile_sha256": sha(cap / "reset_profile16_physical.bin"),
        "raw_terminal_mailbox_sha256": sha(cap / "mailbox_terminal_physical.bin"),
        "unprotected_backing_DDR": True,
        "backup_protection_verified": False,
        "independent_boot_DMA_DDR_owner_exclusivity_verified": False,
        "transient_backup_corruption_excluded": False,
        "neural_parity_evidence_not_security_equivalence": True,
        "1024_image_performance_benchmark_accepted": False,
        "reboot_required_after_experiment": True,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return record


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experiment", choices=("once", "unchecked"), required=True)
    for flag in ("evidence", "stage", "first16", "b3_report",
                 "build", "original_elf", "reset_pins", "reports", "out"):
        p.add_argument("--" + flag.replace("_", "-"), type=Path, required=True)
    a = p.parse_args()
    try:
        r = review(a)
    except (IndependentNoGo, pilot.PilotNoGo, pilot.b3.PilotPhysicalNoGo,
            neural.RecordNoGo, sidecar.SidecarNoGo, KeyError, TypeError,
            OSError, ValueError) as e:
        print("P08_B45_PERF_PILOT16_INDEPENDENT_NO_GO=" + str(e),
              file=sys.stderr)
        return 3
    print("P08_B45_PERF_PILOT16_INDEPENDENT_SCALAR_FNV_AND_POSTBACKUP_PASS=1")
    print("P08_B45_PERF_PILOT16_HARDWARE_IMMUTABILITY_PROVEN=0")
    print("P08_B45_PERF_PILOT16_1024_IMAGE_PERFORMANCE_PROVEN=0")
    print("P08_B45_PERF_PILOT16_INDEPENDENT_REPORT=" + str(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
