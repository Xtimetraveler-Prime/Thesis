#!/usr/bin/env python3
"""P08-B4.5 explicit reduced-integrity performance-only KV260 full1024.

DEFAULT preflight: NO BOARD. Separately approved execute: destructive JTAG
dedicated standalone A53, ORIGINAL six signed DDR stage/readbacks, accepted
P03 bitstream, new unprotected 16-image A53 app, all 16 scalar/FNV receipts,
all 27 postrun backup readbacks. NO XMPU programming and NO security claims.
DO NOT run on live Linux-owned DDR; REBOOT after every physical attempt.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import statistics
import struct
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

import p07_b4i_physical_pilot as b4i
import p07_b4j_shell_program_pilot as b4j
import p08_b3_full1024_physical_run as b3
import p08_b3_full1024_stage_host as original_stage
import p08_b4_2_verify_full1024 as neural
import p08_b2_4_verify_untrusted_first16 as timing_parser
import p08_b4_1_merge_scalar_1024 as oracle_merge
import p08_b4_2_physical_run as original_full
import p08_b44_profile_physical_run as original_profile
import p08_b45_sidecar as sidecar
import p08_b45_perf_full1024_elf_admission as elf_gate

V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V3 / "software" / "p08"))
import build_p08_b45_perf_full1024 as build_gate

B3_REPORT_SHA = "b21e388ab2c3896e76373aaf1663b3b3b1a6d6e1e3c192684f7da02d40b0ed11"
RUN_TCL = "vivado/p08_b45_perf_full1024_run_and_capture.tcl"
RUN_TOKEN = "P08_B45_PERF_1024_AFTER_SIX_SIGNED_READBACK_UNPROTECTED_RISK_APPROVED"
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
SCHEMA = "p08-b45-perf-unprotected-full1024-scalar-and-backup-physical-v1"


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
        root / f"p08_b45_perf_{args.experiment}_full1024_elf_admission.json",
        root / "source",
    )


def admission(args: argparse.Namespace) -> dict:
    require(args.experiment in build_gate.MODES, "unknown performance experiment")
    # Historical ORIGINAL six-transfer PC-plan. Never restage or mutate it.
    b3.original_inputs(args.stage, args.first16)
    require(sha(args.b3_report) == B3_REPORT_SHA,
            "original B3 independently verified 16-image physical report changed")
    require(sha(args.oracle) == original_full.ORIGINAL_FULL1024_ORACLE_SHA,
            "original complete TRAIN 1024 scalar oracle SHA drift")
    with TemporaryDirectory(prefix="b45_perf1024_64_shards_") as td:
        regenerated=oracle_merge.merge(
            args.shards,args.ingress,args.first16,
            Path(td)/"original1024.json")
    require(json.loads(args.oracle.read_text()) == regenerated,
            "full 1024 original scalar oracle differs from 64 immutable shards")

    require(sha(args.b4_independent_report) ==
            original_profile.ORIGINAL_B4_PHYSICAL_REPORT_SHA,
            "accepted prior original 1024 JTAG numerical evidence drift")
    origphys=json.loads(args.b4_independent_report.read_text())
    require(origphys.get("single_session_full1024_numerical_parity_accepted") is True and
            origphys.get("real_1024_A53_terminal_PASS_observed") is True and
            origphys.get("all_1024_full_26tick_1010_neuron_FNV_fingerprints_equal_scalar") is True and
            origphys.get("original_full1024_scalar_sha256") ==
                original_full.ORIGINAL_FULL1024_ORACLE_SHA and
            origphys.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED",
            "prior full original 1024 independent result invalid")
    require(sha(args.b44_timing_report) ==
            original_profile.ORIGINAL_B44_TIMING_SHA,
            "accepted B4.4 original measured latency report SHA drift")
    prior_timed=json.loads(args.b44_timing_report.read_text())
    require(prior_timed.get("ordinary_frame_count") == 1023 and
            prior_timed.get("one_independently_verified_real_physical_session") is True and
            prior_timed.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED",
            "original B4.4 1023 ordinary-frame baseline invalid")
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
    require(accepted == result and result.get("frames") == 1024 and
            result.get("unprotected_performance_only") is True and
            result.get("physical_DDR_immutability_not_claimed") is True and
            result["new_elf_sha256"] == actual_elf_sha and
            result["new_linker_map_sha256"] == actual_map_sha,
            "new genuine full1024 ELF+map+independent recheck do not agree")
    return {
        "schema": "p08-b45-unprotected-full1024-offline-pc-preflight-v1",
        "original_full1024_scalar_oracle_sha256": original_full.ORIGINAL_FULL1024_ORACLE_SHA,
        "accepted_original_1024_JTAG_report_sha256": original_profile.ORIGINAL_B4_PHYSICAL_REPORT_SHA,
        "accepted_original_1023_timing_report_sha256": original_profile.ORIGINAL_B44_TIMING_SHA,
        "experiment": args.experiment,
        "original_b3_physical_provenance_report_sha256": B3_REPORT_SHA,
        "original_first16_oracle_sha256": sha(args.first16),
        "original_27context_PC_stage_sha256":
            sha(args.stage / original_stage.FILES[0][0]),
        "new_performance_full1024_ELF_sha256": actual_elf_sha,
        "new_performance_full1024_linker_map_sha256": actual_map_sha,
        "new_performance_full1024_admission_sha256": sha(report),
        "new_performance_full1024_source_inventoried": True,
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
    cap=root/"performance1024_capture"
    log=root/"full1024_a53_physical_run.log"
    for line in (
        "P08_B45_PERF1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
        "P08_B45_PERF1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
        "P08_B45_PERF1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B45_PERF1024_27_BACKUP_POST_RUN_PHYSICAL_READBACKS_CAPTURED=1",
    ):
        marker(log,line)
    snapshot=(cap/"progress_state.txt").read_text()
    require("completed=1024" in snapshot and
            "state=CAPTURE_DONE_PENDING_INDEPENDENT" in snapshot,
            "atomic host progress terminal is incomplete")
    after=check_post_backup(args.stage,cap)
    result=neural.verify(
        args.oracle,args.first16,
        cap/"journal1024_physical.bin",cap/"timing1024_physical.bin",
        cap/"mailbox_terminal_physical.bin",
        root/"full1024_untrusted_neural_verify.json")
    require(result["count"]==1024 and
            result["all_1024_original_full26_tick_neural_FNV_equal_scalar"] is True and
            result["all_1024_10_output_spikes_and_classifications_equal_scalar"] is True and
            result["all_1024_timing_rows_additive_and_monotonic"] is True,
            "untrusted 1024 image neural/FNV/clock reference mismatch")
    hz=result["terminal"]["CNTFRQ_EL0_hz"]
    profile=(cap/"reset_profile1024_physical.bin").read_bytes()
    perf=sidecar.audit(profile,mode=args.experiment,expected_rows=1024,
                       observed_hz=hz,require_protection=False)
    require(perf["backing_backup_guard_provisioned_flag"]==0 and
            perf["frames_structurally_verified"]==1024 and
            perf["ordinary_frames"]==1023 and
            perf["strict_protection_required"] is False,
            "unprotected backup reported as protected or profile invalid")
    timers=(cap/"timing1024_physical.bin").read_bytes()
    require(len(timers)==262144,"expected 1024x256B timing")
    prior=None
    service_ms=[]
    phase0_ms=[]
    for i in range(1024):
        timed=timing_parser.verify_timing(timers[i*256:(i+1)*256],i,prior)
        prior=timed["after_journal_commit_CNTVCT"]
        row=struct.unpack_from("<64I",profile,i*256)
        ticks=row[15] | (row[16]<<32)
        require(0<ticks<=timed["phase_counter_ticks"][0],
                f"frame {i}: reset ticks exceed actual original restore phase0")
        if i<1023:
            service_ms.append(timed["complete_service_counter_ticks"]*1000.0/hz)
            phase0_ms.append(timed["phase_counter_ticks"][0]*1000.0/hz)
    def describe(vals: list[float])->dict:
        ordered=sorted(vals)
        return {"ordinary_frame_count":1023,"min_ms":ordered[0],
                "median_ms":statistics.median(ordered),
                "p95_nearest_rank_ms":ordered[math.ceil(0.95*len(ordered))-1],
                "max_ms":ordered[-1]}
    record={
        "schema":SCHEMA,
        "experiment":args.experiment,
        "new_full1024_ELF_sha256":preflight["new_performance_full1024_ELF_sha256"],
        "original_full1024_scalar_SHA256":preflight["original_full1024_scalar_oracle_sha256"],
        "same_session_original_six_DDR_source_readbacks_proven":True,
        "physical_A53_stop_P03_program_and_strict_1024_terminal_observed":True,
        "all_1024_original_classifier_spikes_26tick_FNV_match_scalar":True,
        "all_1024_full_service_timing_and_reset_subspans_valid":True,
        "all_27_backup_records_byte_identical_to_original_after_run":True,
        "postrun_backup_sha256_by_core":after,
        "reset_timing":perf,
        "whole_image_service_timing":describe(service_ms),
        "restore_phase0_timing":describe(phase0_ms),
        "raw_neural_journal_sha256":sha(cap/"journal1024_physical.bin"),
        "raw_service_timing_sha256":sha(cap/"timing1024_physical.bin"),
        "raw_reset_profile_sha256":sha(cap/"reset_profile1024_physical.bin"),
        "raw_terminal_mailbox_sha256":sha(cap/"mailbox_terminal_physical.bin"),
        "original_1023_ordinary_reference_timing_sha256":
            preflight["accepted_original_1023_timing_report_sha256"],
        "exclude_trace_image_index_1023_from_ordinary_statistics":True,
        "physical_backup_protection_claim":False,
        "transient_backup_mutation_excluded":False,
        "FSBL_XMPU_DMA_owner_exclusivity_proven":False,
        "speedup_vs_original_not_paired_or_multisession_accepted":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "reboot_required_after_any_JTAG_attempt":True,
    }
    with (root/"full1024_unprotected_physical_preliminary.json").open(
        "x",encoding="utf-8") as fd:
        json.dump(record,fd,indent=2,sort_keys=True)
        fd.write("\n")
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
    cap = root / "performance1024_capture"
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
                    preflight["new_performance_full1024_ELF_sha256"],
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
            preflight["new_performance_full1024_ELF_sha256"],
            str(z256), str(z4096), str(cap),
            "tcp:127.0.0.1:3121",
        ], root / "full1024_a53_physical_run.log")
        result = verify_capture(args, preflight, root)
        require(result["all_16_original_scalar_classifier_and_full_26tick_FNV_match"] is True,
                "actual original frozen numerical results did not match")
        (root / "stage.txt").write_text(
            "B45_PERF16_NEURAL_AND_POSTBACKUP_PRESERVED_PRELIMINARY_PASS_REBOOT_REQUIRED\n")
        print("P08_B45_PERF_FULL1024_SAME_SESSION_JTAG_SCALAR_FNV_AND_BACKUP_PASS=1")
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
        "stage", "first16", "b3_report", "shards", "ingress", "oracle",
        "b4_independent_report", "b44_timing_report", "build",
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
        print("P08_B45_PERF_FULL1024_ORIGINAL_SOURCES_AND_REAL_ELF_OFFLINE_PASS=1")
        print("P08_B45_PERF_ELF_SHA256=" +
              verified["new_performance_full1024_ELF_sha256"])
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
        print("P08_B45_PERF_FULL1024_NO_GO=" + str(exc), file=sys.stderr, flush=True)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
