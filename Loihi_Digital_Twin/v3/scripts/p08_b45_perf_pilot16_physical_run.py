#!/usr/bin/env python3
"""P08-B4.5 explicit reduced-integrity performance-only KV260 pilot16.

DEFAULT preflight: NO BOARD. Separately approved execute: destructive JTAG
dedicated standalone A53, ORIGINAL six signed DDR stage/readbacks, accepted
P03 bitstream, new unprotected 16-image A53 app, all 16 scalar/FNV receipts,
all 27 postrun backup readbacks. NO XMPU programming and NO security claims.
DO NOT run on live Linux-owned DDR; REBOOT after every physical attempt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

import p07_b4i_physical_pilot as b4i
import p07_b4j_shell_program_pilot as b4j
import p08_b3_pilot16_physical_run as b3
import p08_b3_pilot16_stage_host as original_stage
import p08_b2_4_verify_untrusted_first16 as neural
import p08_b45_sidecar as sidecar
import p08_b45_perf_pilot16_elf_admission as elf_gate

V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V3 / "software" / "p08"))
import build_p08_b45_perf_pilot16 as build_gate

B3_REPORT_SHA = "b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11"
RUN_TCL = "vivado/p08_b45_perf_pilot16_run_and_capture.tcl"
RUN_TOKEN = "P08_B45_PERF_16_AFTER_SIX_SIGNED_READBACK_UNPROTECTED_RISK_APPROVED"
APPROVALS = (
    "dedicated_jtag_owner",
    "discard_linux_and_halt_all_a53_approved",
    "unproven_boot_ddr_dma_exclusivity_risk_accepted",
    "six_original_ddr_transfers_overwrite_approved",
    "original_p03_pl_programming_approved",
    "low_ddr_new_performance_elf_overwrite_approved",
    "mailbox_and_three_journals_overwrite_approved",
    "unprotected_backup_integrity_tradeoff_accepted",
    "post_run_backup_readback_approved",
    "reboot_and_recovery_approved",
)
SCHEMA = "p08-b45-perf-unprotected-pilot16-scalar-and-backup-physical-v1"


class PilotNoGo(ValueError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise PilotNoGo("NO-GO: " + msg)


def sha(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "regular file required: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    root = args.build
    app = build_gate.APPS[args.experiment]
    return (
        root / "vitis_workspace" / (app + ".elf"),
        root / "vitis_workspace" / (app + ".map"),
        root / f"p08_b45_perf_{args.experiment}_pilot16_elf_admission.json",
        root / "source",
    )


def admission(args: argparse.Namespace) -> dict:
    require(args.experiment in build_gate.MODES, "unknown performance experiment")
    # Historical ORIGINAL six-transfer PC-plan. Never restage or mutate it.
    b3.original_inputs(args.stage, args.first16)
    require(sha(args.b3_report) == B3_REPORT_SHA,
            "original B3 independently verified 16-image physical report changed")
    baseline = json.loads(args.b3_report.read_text())
    require(
        baseline.get("schema") ==
        "p08-b3-original-b24-first16-independent-physical-jtag-oracle-verification-v1"
        and baseline.get("all_16_original_neural_classifier_and_10_output_spike_vectors_equal_scalar") is True
        and baseline.get("all_16_full_26tick_1010_neuron_FNV_fingerprint_equal_scalar") is True
        and baseline.get("same_session_original_6_DDR_physical_readbacks_byte_exact") is True
        and baseline.get("original_OFFICIAL_MNIST_TEST") == "SEALED_NOT_ACCESSED",
        "accepted original B3 physical neural/scalar witness invalid",
    )
    metrics = (args.reports / "p03_2_post_route_metrics.txt").read_text().splitlines()
    require(all(k in metrics for k in b4i.REQUIRED_METRICS),
            "original routed P03 hardware geometry drift")
    for filename, expected in b4i.EXPECTED_SHA.items():
        require(sha(args.reports / filename) == expected,
                "accepted original routed P03 XSA/BIT/LTX drift: " + filename)

    require(args.build.is_absolute() and args.build.is_dir() and
            not args.build.is_symlink() and
            not args.build.resolve().is_relative_to(V3.resolve()),
            "new external Vitis build root required")
    elf, linker, report, source = artifact_paths(args)
    build_gate.check_stage(source, args.experiment)
    require(report.is_file() and not report.is_symlink(),
            "genuine build offline admission receipt missing")
    actual_elf_sha = sha(elf)
    actual_map_sha = sha(linker)
    accepted = json.loads(report.read_text())
    with TemporaryDirectory(prefix="p08_b45_perf_elf_repeat_") as directory:
        result = elf_gate.audit(
            args.experiment, elf, linker, args.original_elf,
            args.reports / "p03_2_ps_mmio.xsa",
            args.reset_pins / "p08_b2_2_original_context_sha256.h",
            Path(directory) / "recheck.json",
        )
    require(accepted == result and result.get("frames") == 16 and
            result.get("unprotected_performance_only") is True and
            result.get("physical_DDR_immutability_not_claimed") is True and
            result["new_elf_sha256"] == actual_elf_sha and
            result["new_linker_map_sha256"] == actual_map_sha,
            "new genuine pilot16 ELF+map+independent recheck do not agree")
    return {
        "schema": "p08-b45-unprotected-pilot16-offline-pc-preflight-v1",
        "experiment": args.experiment,
        "original_b3_physical_provenance_report_sha256": B3_REPORT_SHA,
        "original_first16_oracle_sha256": sha(args.first16),
        "original_27context_PC_stage_sha256":
            sha(args.stage / original_stage.FILES[0][0]),
        "new_performance_pilot16_ELF_sha256": actual_elf_sha,
        "new_performance_pilot16_linker_map_sha256": actual_map_sha,
        "new_performance_pilot16_admission_sha256": sha(report),
        "new_performance_pilot16_source_inventoried": True,
        "original_P03_images_sha256": dict(b4i.EXPECTED_SHA),
        "unprotected_backup": True,
        "DDR_immutable_backup_hardware_protected": False,
        "no_XMPU_configuration": True,
        "actual_boot_DDR_other_master_exclusivity_proven": False,
        "physical_execution_authorized_by_preflight": False,
        "board_contact_during_preflight": False,
        "physical_inference_already_run": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
    }


def marker(path: Path, text: str) -> None:
    require(path.read_text().splitlines().count(text) == 1,
            "missing unique authentic JTAG marker: " + text)


def check_post_backup(stage: Path, cap: Path) -> list[str]:
    # Source is the exact original verified 27x512KiB bundle.
    data = (stage / original_stage.FILES[0][0]).read_bytes()
    require(len(data) == 27 * 524288 and
            hashlib.sha256(data).hexdigest() ==
            original_stage.EXPECTED_SHA[original_stage.FILES[0][0]],
            "original immutable host backup unexpectedly changed")
    folder = cap / "backup_after_27"
    require(folder.is_dir() and not folder.is_symlink() and
            {p.name for p in folder.iterdir()} ==
            {f"core_{i:02d}.bin" for i in range(27)},
            "missing or extra captured backup records")
    pins = []
    for core in range(27):
        p = folder / f"core_{core:02d}.bin"
        raw = p.read_bytes()
        original = data[core * 524288:(core + 1) * 524288]
        require(len(raw) == 524288 and raw == original,
                f"AFTER RUN backup core {core} does not match original frozen bytes")
        pins.append(sha(p))
    return pins


def verify_capture(args: argparse.Namespace, preflight: dict, root: Path) -> dict:
    cap = root / "performance16_capture"
    log = root / "pilot16_a53_physical_run.log"
    for line in (
        "P08_B45_PERF16_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
        "P08_B45_PERF16_REAL_16_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
        "P08_B45_PERF16_EXACT_16_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B45_PERF16_27_BACKUP_POST_RUN_PHYSICAL_READBACKS_CAPTURED=1",
    ):
        marker(log, line)
    sha_source = check_post_backup(args.stage, cap)
    neural_result = neural.verify(
        args.first16,
        cap / "journal16_physical.bin",
        cap / "timing16_physical.bin",
        cap / "mailbox_terminal_physical.bin",
        root / "pilot16_untrusted_neural_verify.json",
    )
    require(neural_result["verified_frames"] == 16 and
            neural_result["all_16_independent_scalar_counters_match"] is True and
            neural_result["all_16_full_26tick_trace_FNV_match"] is True,
            "untrusted 16-image neural/FNV check failed")
    hz = neural_result["end_mailbox"]["observed_CNTFRQ_EL0_hz"]
    profile_raw = (cap / "reset_profile16_physical.bin").read_bytes()
    perf = sidecar.audit(
        profile_raw, mode=args.experiment, expected_rows=16,
        observed_hz=hz, require_protection=False,
    )
    require(perf["backing_backup_guard_provisioned_flag"] == 0 and
            perf["frames_structurally_verified"] == 16 and
            perf["strict_protection_required"] is False,
            "unprotected mode misreported protected DDR or corrupt reset timing")
    # Performance reset must lie inside the identical image-service
    # phase0 interval as in the original accepted full A53 service meter.
    timers = neural_result["timing_frames"]
    require(len(timers) == 16, "incomplete original 16 A53 service timers")
    for ordinal, timer in enumerate(timers):
        words = struct.unpack_from("<64I", profile_raw, ordinal * 256)
        reset_ticks = words[15] | (words[16] << 32)
        require(0 < reset_ticks <= timer["phase_counter_ticks"][0],
                f"frame {ordinal}: measured reset exceeds complete A53 phase0 span")
    record = {
        "schema": SCHEMA,
        "operator_experiment": args.experiment,
        "new_pilot16_elf_sha256": preflight["new_performance_pilot16_ELF_sha256"],
        "same_session_original_six_DDR_source_readbacks_proven": True,
        "actual_JTAG_A53_stop_P03_prog_and_16_terminal_proven": True,
        "all_16_original_scalar_classifier_and_full_26tick_FNV_match": True,
        "all_16_reset_profile_source_and_dest_count_structurally_valid": True,
        "all_27_backup_records_physically_equal_frozen_after_16_images": True,
        "postrun_original_backup_sha256_by_core": sha_source,
        "neural": {
            "verified_frames": 16,
            "original_scalar_sha256": neural_result["independent_scalar_oracle_sha256"],
            "journal_sha256": neural_result["unverified_input_journal_sha256"],
            "timing_sha256": neural_result["unverified_input_timing_sha256"],
            "mailbox_sha256": neural_result["unverified_input_mailbox_sha256"],
        },
        "reset_timing_structural": perf,
        "backup_hardware_write_exclusion_proven": False,
        "backup_transient_mutation_excluded": False,
        "true_XMPU_or_FSBL_configuration_proven": False,
        "physical_inference_computational_correctness": "16_FRAMES_ACCEPTED_ONLY",
        "physical_security_guarantee": "NOT_CLAIMED",
        "physical_1024_image_speedup_accepted": False,
        "unverified_external_DMA_and_early_boot_owners": True,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "reboot_required_after_attempt": True,
    }
    out = root / "pilot16_unprotected_physical_preliminary.json"
    with out.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return record


def execute(args: argparse.Namespace, preflight: dict) -> None:
    for approval in APPROVALS:
        require(getattr(args, approval) == "YES",
                "operator --" + approval.replace("_", "-") + " YES required")
    require(args.evidence is not None and args.evidence.is_absolute() and
            args.evidence.parent.is_dir() and
            not args.evidence.exists() and not args.evidence.is_symlink() and
            not args.evidence.resolve().is_relative_to(V3.resolve()),
            "new external evidence root, NO overwrite required")
    require(all(shutil.which(tool) for tool in ("xsdb", "vivado")),
            "genuine operator Vivado/XSDB tools missing")
    root = args.evidence
    root.mkdir(mode=0o700)
    (root / "preflight.json").write_text(
        json.dumps(preflight | {
            "all_ten_independent_operator_approvals_recorded": True,
            "physical_JTAG_session_started": False
        }, indent=2, sort_keys=True) + "\n"
    )
    cap = root / "performance16_capture"
    cap.mkdir()
    reads = root / "source_physical_readback"
    reads.mkdir()
    try:
        (root / "stage.txt").write_text(
            "B45_PERF16_DESTRUCTIVE_UNPROTECTED_JTAG_ATTEMPT_STARTED_REBOOT_REQUIRED\n")
        b4i.log_call([
            "xsdb", b4j.TAKEOVER_TCL, "DEDICATED_DISCARD_LINUX_APPROVED",
            "tcp:127.0.0.1:3121",
        ], root / "a53_takeover_and_ps128.log")
        b4i.verify_takeover_log(
            (root / "a53_takeover_and_ps128.log").read_text())
        b4i.log_call([
            "vivado", "-mode", "batch", "-source", b4j.PROGRAM_TCL,
            "-tclargs", str(args.reports / "p03_2_ps_mmio.bit"),
            str(args.reports / "p03_2_ps_mmio.ltx"), "localhost:3121",
        ], root / "accepted_p03_program.log")
        b4j.require_programmed_shell(
            (root / "accepted_p03_program.log").read_text())
        originals = [args.stage / n for n, _, _ in original_stage.FILES]
        b4i.log_call([
            "xsdb", b3.STAGE_TCL, b3.STAGE_TOKEN, *map(str, originals),
            str(reads), "tcp:127.0.0.1:3121",
        ], root / "six_original_ddr_physical_stage.log")
        marker(root / "six_original_ddr_physical_stage.log",
               "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1")
        # Reuse original P08-B3 signed physical readback verifier unchanged.
        signed = b3.readback_original(args.stage, reads)
        (root / "same_session_six_source_receipt.json").write_text(
            json.dumps({
                "original_six_physical_source_sha256": signed,
                "signed_new_benchmark_elf_sha256":
                    preflight["new_performance_pilot16_ELF_sha256"],
                "same_session_six_source_JTAG_proven": True,
                "source_frozen_original": True,
                "hardware_DDR_backup_immutable": False,
                "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
            }, indent=2, sort_keys=True) + "\n"
        )
        z256 = root / "zero256.bin"
        z4096 = root / "zero4096.bin"
        z256.write_bytes(bytes(256))
        z4096.write_bytes(bytes(4096))
        elf, _, _, _ = artifact_paths(args)
        b4i.log_call([
            "xsdb", RUN_TCL, RUN_TOKEN, args.experiment, str(elf),
            preflight["new_performance_pilot16_ELF_sha256"],
            str(z256), str(z4096), str(cap),
            "tcp:127.0.0.1:3121",
        ], root / "pilot16_a53_physical_run.log")
        result = verify_capture(args, preflight, root)
        require(result["all_16_original_scalar_classifier_and_full_26tick_FNV_match"] is True,
                "actual original frozen numerical results did not match")
        (root / "stage.txt").write_text(
            "B45_PERF16_NEURAL_AND_POSTBACKUP_PRESERVED_PRELIMINARY_PASS_REBOOT_REQUIRED\n")
        print("P08_B45_PERF_PILOT16_SAME_SESSION_JTAG_SCALAR_FNV_AND_BACKUP_PASS=1")
        print("P08_B45_PERF_PHYSICAL_BACKUP_HARDWARE_PROTECTED=0")
        print("P08_B45_PERF_SECURITY_EQUIVALENCE_WITH_ORIGINAL_CLAIMED=0")
        print("P08_B45_PERF_1024_PERFORMANCE_COMPARISON_ACCEPTED=0")
    finally:
        print("P08_B45_PERF_ANY_DESTRUCTIVE_JTAG_ATTEMPT_REBOOT_REQUIRED=1",
              flush=True)
        print("REBOOT KV260; never resume halted Linux.", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "execute"), default="preflight")
    parser.add_argument("--experiment", choices=build_gate.MODES, required=True)
    for name in (
        "stage", "first16", "b3_report", "build",
        "original_elf", "reset_pins", "reports"
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    for name in APPROVALS:
        parser.add_argument("--" + name.replace("_", "-"),
                            choices=("YES", "NO"), default="NO")
    args = parser.parse_args(argv)
    try:
        verified = admission(args)
        print("P08_B45_PERF_PILOT16_ORIGINAL_SOURCES_AND_REAL_ELF_OFFLINE_PASS=1")
        print("P08_B45_PERF_ELF_SHA256=" +
              verified["new_performance_pilot16_ELF_sha256"])
        print("P08_B45_PERF_BACKUP_HARDWARE_PROTECTED=0")
        print("P08_B45_PERF_UNPROVEN_BOOT_DMA_DDR_OWNERSHIP_EXPLICIT=1")
        if args.mode == "preflight":
            print("P08_B45_PERF_BOARD_VISITED=0")
            print("P08_B45_PERF_DESTRUCTIVE_JTAG_NOT_AUTHORIZED_BY_PREFLIGHT=1")
            return 0
        execute(args, verified)
        return 0
    except (PilotNoGo, b3.PilotPhysicalNoGo, b3.source.StageNoGo,
            elf_gate.VariantElfNoGo, sidecar.SidecarNoGo,
            neural.RecordNoGo, KeyError, TypeError, OSError, ValueError,
            RuntimeError, subprocess.TimeoutExpired) as exc:
        print("P08_B45_PERF_PILOT16_NO_GO=" + str(exc), file=sys.stderr, flush=True)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
