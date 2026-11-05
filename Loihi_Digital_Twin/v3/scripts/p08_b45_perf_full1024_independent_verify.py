#!/usr/bin/env python3
"""Independent PC-ONLY real B4.5 full1024 benchmark attestation.

Replay accepted 64-shard software scalar original and B3/B4/B44 hashes,
recheck mode-specific real ELF/map and 6 live JTAG DDR source readbacks,
all 1024 actual neural/spike/FNV/timer/reset receipts, all original
27 post-run physical backup records. NO board/JTAG contact.
ONE real run per mode is descriptive, NOT repeated paired AB/BA inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
from tempfile import TemporaryDirectory

import p08_b45_perf_full1024_physical_run as bench
import p08_b4_2_verify_full1024 as neural
import p08_b2_4_verify_untrusted_first16 as timing_parser
import p08_b45_sidecar as sidecar
import p08_b45_perf_full1024_monitor as monitor


def need(ok:bool,why:str)->None:
    if not ok:raise ValueError("NO-GO: "+why)

def sha(path:Path)->str:
    return bench.sha(path)

def measured(vals:list[float])->dict:
    need(len(vals)==1023 and all(v>0 for v in vals),
         "must have 1023 positive ordinary-frame latencies")
    ordered=sorted(vals)
    return {"ordinary_frames":1023,"min_ms":ordered[0],
            "median_ms":statistics.median(ordered),
            "p95_nearest_rank_ms":ordered[math.ceil(.95*1023)-1],
            "max_ms":ordered[-1]}

def review(args:argparse.Namespace)->dict:
    root=args.evidence
    need(root.is_absolute() and root.is_dir() and not root.is_symlink(),
         "absolute, existing real physical receipt root required")
    need(args.out.is_absolute() and args.out.parent.is_dir() and
         not args.out.exists() and not args.out.is_symlink() and
         not args.out.resolve().is_relative_to(bench.V3.resolve()),
         "new no-overwrite external independent report path required")
    verified=bench.admission(args)
    prior=json.loads((root/"preflight.json").read_text())
    for key,value in verified.items():
        need(prior.get(key)==value,
             "original signed source/ELF/accepted baseline changed: "+key)
    need(prior.get("all_ten_independent_operator_approvals_recorded") is True and
         prior.get("physical_JTAG_session_started") is False,
         "explicit risk approvals missing")
    bench.b4i.verify_takeover_log(
        (root/"a53_takeover_and_ps128.log").read_text())
    bench.b4j.require_programmed_shell(
        (root/"accepted_p03_program.log").read_text())
    bench.marker(root/"six_original_ddr_physical_stage.log",
       "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1")
    original=bench.b3.readback_original(
        args.stage,root/"source_physical_readback")
    staged=json.loads((root/"same_session_six_source_receipt.json").read_text())
    need(staged.get("original_six_physical_source_sha256")==original and
         staged.get("signed_new_benchmark_elf_sha256")==
            verified["new_performance_full1024_ELF_sha256"] and
         staged.get("hardware_DDR_backup_immutable") is False,
         "original same-session genuine 6 DDR physical stage receipt mismatch")
    cap=root/"performance1024_capture"
    log=root/"full1024_a53_physical_run.log"
    for marker in (
        "P08_B45_PERF1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
        "P08_B45_PERF1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
        "P08_B45_PERF1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B45_PERF1024_27_BACKUP_POST_RUN_PHYSICAL_READBACKS_CAPTURED=1",
    ):
        bench.marker(log,marker)
    progress=monitor.parse_snapshot(
        (cap/"progress_state.txt").read_text(),expected_mode=args.experiment)
    need(progress["completed"]==1024 and
         progress["state"]=="CAPTURE_DONE_PENDING_INDEPENDENT",
         "final HOST progress snapshot not captured/incorrect mode")
    backups=bench.check_post_backup(args.stage,cap)
    with TemporaryDirectory(prefix="b45_perf1024_independent_neural_") as td:
        actual=neural.verify(
            args.oracle,args.first16,
            cap/"journal1024_physical.bin",
            cap/"timing1024_physical.bin",
            cap/"mailbox_terminal_physical.bin",
            Path(td)/"neural.json")
    need(actual["count"]==1024 and
         actual["all_1024_original_full26_tick_neural_FNV_equal_scalar"] is True and
         actual["all_1024_10_output_spikes_and_classifications_equal_scalar"] is True and
         actual["all_1024_timing_rows_additive_and_monotonic"] is True,
         "all 1024 classifier/10 output spike/FNV/timing equality failed")
    hz=actual["terminal"]["CNTFRQ_EL0_hz"]
    profile=(cap/"reset_profile1024_physical.bin").read_bytes()
    perf=sidecar.audit(profile,mode=args.experiment,expected_rows=1024,
                       observed_hz=hz,require_protection=False)
    need(perf["backing_backup_guard_provisioned_flag"]==0 and
         perf["ordinary_frames"]==1023 and
         perf["strict_protection_required"] is False,
         "full reset sidecar invalid or falsely asserts protected memory")
    timing=(cap/"timing1024_physical.bin").read_bytes()
    need(len(timing)==262144,"incomplete 1024x256B A53 service receipt")
    prior_commit=None
    service=[]
    phase0=[]
    for index in range(1024):
        t=timing_parser.verify_timing(
            timing[index*256:(index+1)*256],index,prior_commit)
        prior_commit=t["after_journal_commit_CNTVCT"]
        values=struct.unpack_from("<64I",profile,index*256)
        reset_ticks=values[15] | (values[16]<<32)
        need(0<reset_ticks<=t["phase_counter_ticks"][0],
             f"frame {index} reset ticks exceed service phase0")
        if index<1023:
            service.append(t["complete_service_counter_ticks"]*1000.0/hz)
            phase0.append(t["phase_counter_ticks"][0]*1000.0/hz)
    service_summary=measured(service)
    phase0_summary=measured(phase0)
    preliminary=json.loads(
        (root/"full1024_unprotected_physical_preliminary.json").read_text())
    need(preliminary.get("schema")==bench.SCHEMA and
         preliminary.get("experiment")==args.experiment and
         preliminary.get("new_full1024_ELF_sha256")==
            verified["new_performance_full1024_ELF_sha256"] and
         preliminary.get("all_1024_original_classifier_spikes_26tick_FNV_match_scalar") is True and
         preliminary.get("all_27_backup_records_byte_identical_to_original_after_run") is True and
         preliminary.get("postrun_backup_sha256_by_core")==backups and
         preliminary.get("physical_backup_protection_claim") is False and
         preliminary.get("transient_backup_mutation_excluded") is False and
         preliminary.get("exclude_trace_image_index_1023_from_ordinary_statistics") is True,
         "operator preliminary report missing, falsified, or wrong experiment")
    # Compare numeric summaries exactly because both reporters operate on
    # the same signed sidecar bytes and same original A53 CNTFRQ.
    need(preliminary.get("whole_image_service_timing")=={
            "ordinary_frame_count":1023,"min_ms":service_summary["min_ms"],
            "median_ms":service_summary["median_ms"],
            "p95_nearest_rank_ms":service_summary["p95_nearest_rank_ms"],
            "max_ms":service_summary["max_ms"]},
         "original captured complete-service statistics disagree")
    record={
        "schema":"p08-b45-unprotected-full1024-independent-real-jtag-v1",
        "experiment":args.experiment,
        "genuine_new_mode_specific_A53_ELF_sha256":
            verified["new_performance_full1024_ELF_sha256"],
        "original_complete1024_scalar_SHA256":
            verified["original_full1024_scalar_oracle_sha256"],
        "prior_accepted_original_B4_1024_physical_sha256":
            verified["accepted_original_1024_JTAG_report_sha256"],
        "prior_accepted_original_B44_single_session_timing_sha256":
            verified["accepted_original_1023_timing_report_sha256"],
        "new_real_JTAG_A53_halt_P03_programming_six_original_DDR_sources_readback":True,
        "new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar":True,
        "new_all_1024_A53_timing_and_reset_profiles_valid":True,
        "new_all_27_post_run_backup_records_identical_to_original":True,
        "new_original_backup_per_core_sha256":backups,
        "actual_A53_CNTFRQ_hz":hz,
        "reset_descriptive":perf,
        "whole_image_service_descriptive_1023":service_summary,
        "restore_phase0_descriptive_1023":phase0_summary,
        "journal_sha256":sha(cap/"journal1024_physical.bin"),
        "timing_sha256":sha(cap/"timing1024_physical.bin"),
        "reset_sidecar_sha256":sha(cap/"reset_profile1024_physical.bin"),
        "mailbox_sha256":sha(cap/"mailbox_terminal_physical.bin"),
        "same_session_original_immutable_source_JTAG_receipt_sha256":
            sha(root/"same_session_six_source_receipt.json"),
        "snapshot_verified_for_progress_only_not_neural":True,
        "last_trace_ordinal_1023_excluded_from_ordinary_performance":True,
        "one_unprotected_session_descriptive_only":True,
        "paired_AB_BA_AB_six_session_speedup_not_established":True,
        "hardware_DDR_backup_protection_proven":False,
        "transient_backup_mutation_excluded":False,
        "boot_DDR_DMA_cross_owner_exclusivity_proven":False,
        "reboot_required_after_ANY_destructive_JTAG_attempt":True,
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with args.out.open("x",encoding="utf-8") as fd:
        json.dump(record,fd,indent=2,sort_keys=True)
        fd.write("\n")
    return record

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experiment",choices=("once","unchecked"),required=True)
    for key in ("evidence","stage","first16","b3_report","shards",
                "ingress","oracle","b4_independent_report",
                "b44_timing_report","build","original_elf","reset_pins",
                "reports","out"):
        p.add_argument("--"+key.replace("_","-"),required=True,type=Path)
    a=p.parse_args(argv)
    try:
        result=review(a)
    except (OSError,ValueError,TypeError,RuntimeError,KeyError) as e:
        print("P08_B45_PERF_FULL1024_INDEPENDENT_NO_GO="+str(e),
              file=sys.stderr,flush=True)
        return 3
    print("P08_B45_PERF_FULL1024_INDEPENDENT_ALL1024_SCALAR_FNV_AND_POSTBACKUP_PASS=1")
    print("P08_B45_PERF_FULL1024_MODE="+result["experiment"])
    print("P08_B45_PERF_FULL1024_RESET_MEDIAN_MS="+str(
        result["reset_descriptive"]["reset_median_ms"]))
    print("P08_B45_PERF_FULL1024_SERVICE_MEDIAN_MS="+str(
        result["whole_image_service_descriptive_1023"]["median_ms"]))
    print("P08_B45_PERF_FULL1024_HARDWARE_BACKUP_PROTECTION_PROVEN=0")
    print("P08_B45_PERF_FULL1024_PAIRED_MULTIRUN_SPEEDUP_ESTABLISHED=0")
    print("P08_B45_PERF_FULL1024_INDEPENDENT_REPORT="+str(a.out))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
