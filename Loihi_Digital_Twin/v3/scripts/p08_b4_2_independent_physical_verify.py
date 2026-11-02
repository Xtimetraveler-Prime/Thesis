#!/usr/bin/env python3
"""P08-B4.2 independently attest original full1024 KV260 same-session evidence.

No board contact. Recompute original full-1024 oracle from all 64 signed
shards, validate genuine original full1024 ELF and P03 pins, genuine
readback of all six original DDR transfers, XSDB transcripts and complete
1024 neural/timer/mailbox records. Does NOT accept 6-session latency,
energy or PL-only speedup by itself.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import p08_b4_2_physical_run as physical
import p08_b4_2_verify_full1024 as numerical

SCHEMA="p08-b4-2-original1024-independent-physical-jtag-numerical-v1"
STAGE_OK="P08_B4_2_1024_REAL_A53_TERMINAL_AND_NUMERICAL_PRECHECK_PASS_INDEPENDENT_JTAG_VERIFICATION_PENDING_REBOOT_REQUIRED"
LOGS={
    "a53_takeover_and_ps128.log":(
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
    ),
    "accepted_p03_program.log":(physical.b4j.PASS_MARKER,),
    "six_original_ddr_physical_stage.log":(
        "P08_B3_PILOT_mutable_27CORES_BYTE_EXACT_PASS=1",
        "P08_B3_PILOT_backup_27CORES_BYTE_EXACT_PASS=1",
        "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1",
    ),
    "full1024_a53_physical_run.log":(
        "P08_B4_FULL1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
        "P08_B4_FULL1024_PHYSICAL_TERMINAL_MAILBOX_CAPTURED_256B=1",
        "P08_B4_FULL1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
        "P08_B4_FULL1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B4_FULL1024_PHYSICAL_CAPTURE_PENDING_INDEPENDENT_SCALAR_VERIFICATION=1",
    ),
}
class AttestationNoGo(ValueError):pass

def check(ok:bool,msg:str)->None:
    if not ok:raise AttestationNoGo("NO-GO: "+msg)

def verify(args:argparse.Namespace)->dict:
    report=args.out
    check(report.is_absolute() and not report.exists() and not report.is_symlink()
          and report.parent.is_dir() and
          not report.resolve().is_relative_to(physical.b4i.ROOT.resolve()),
          "NEW external independent JSON evidence path required")
    evidence=args.evidence
    check(evidence.is_absolute() and evidence.is_dir() and
          not evidence.is_symlink(),"authentic external physical evidence directory required")
    offline=physical.admission(args)
    original=json.loads((evidence/"preflight.json").read_text())
    for key,value in offline.items():
        check(original.get(key)==value,
              "genuine full1024 original source/ELF preflight drift: "+key)
    check(original.get("eight_distinct_operator_execute_approvals") is True and
          original.get("physical_JTAG_session_started") is False and
          original.get("physical_DDR_owner_exclusivity_proven") is False,
          "genuine full1024 operator risk acceptance record absent")
    check((evidence/"stage.txt").read_text().strip()==STAGE_OK,
          "full1024 physical run has not reached numerical precheck PASS")
    for name,markers in LOGS.items():
        path=evidence/name
        check(path.is_file() and not path.is_symlink(),
              "real same-session hardware log missing: "+name)
        rows=path.read_text().splitlines()
        for marker in markers:
            check(rows.count(marker)==1,
                  "full1024 independent physical marker missing/duplicate: "+marker)
        check(not any("ATTEMPT_FAILED_REBOOT_REQUIRED=1" in r for r in rows),
              "physical XSDB stage reported failure: "+name)
    physical.b4i.verify_takeover_log(
        (evidence/"a53_takeover_and_ps128.log").read_text())
    physical.b4j.require_programmed_shell(
        (evidence/"accepted_p03_program.log").read_text())
    physical.prior.original_inputs(args.stage,args.first16)
    observed=physical.prior.readback_original(
        args.stage,evidence/"source_physical_readback")
    receipt=json.loads(
        (evidence/"same_session_six_source_receipt.json").read_text())
    check(receipt.get("original_six_physical_source_sha256")==observed and
          receipt.get("exact_full1024_original_ELF_sha256")==physical.ELF_SHA and
          receipt.get("original_full1024_scalar_sha256")==
          offline["original_full1024_scalar_oracle_sha256"] and
          receipt.get("same_session_JTAG_physical_DDR_readbacks") is True and
          receipt.get("full1024_A53_ELF_downloaded_at_receipt_time") is False and
          receipt.get("operator_reboot_required") is True and
          receipt.get("original_OFFICIAL_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "six original physical source receipt mismatched actual readback")
    captured=evidence/"full1024_capture"
    sizes={
        "mailbox_zero_physical.bin":256,
        "journal_zero_physical.bin":1024*256,
        "timing_zero_physical.bin":1024*256,
        "mailbox_terminal_physical.bin":256,
        "journal1024_physical.bin":1024*256,
        "timing1024_physical.bin":1024*256,
    }
    check(captured.is_dir() and not captured.is_symlink() and
          {f.name for f in captured.iterdir()}==set(sizes),
          "actual full1024 physical journal/timing/zero capture set invalid")
    for name,size in sizes.items():
        p=captured/name
        check(p.is_file() and not p.is_symlink() and p.stat().st_size==size,
              "wrong actual full1024 capture byte length: "+name)
        if name.endswith("_zero_physical.bin"):
            check(p.read_bytes()==bytes(size),
                  "physical PSU zero baseline memory differs: "+name)
    with TemporaryDirectory(prefix="p08_b4_2_independent_") as tmp:
        numerical_proof=numerical.verify(
            args.oracle,args.first16,captured/"journal1024_physical.bin",
            captured/"timing1024_physical.bin",
            captured/"mailbox_terminal_physical.bin",
            Path(tmp)/"untrusted.json")
    check(numerical_proof.get("count")==1024 and
          numerical_proof.get(
              "all_1024_original_full26_tick_neural_FNV_equal_scalar") is True and
          numerical_proof.get(
              "all_1024_timing_rows_additive_and_monotonic") is True,
          "1024 original neural/temporal equality incomplete")
    result={
        "schema":SCHEMA,
        "accepted_B3_physical_report_sha256":
            offline["genuine_B3_physically_accepted_pilot16_report_sha256"],
        "original_full1024_scalar_sha256":
            offline["original_full1024_scalar_oracle_sha256"],
        "accepted_full1024_original_B23_A53_ELF_sha256":physical.ELF_SHA,
        "accepted_full1024_original_B23_A53_linker_map_sha256":physical.MAP_SHA,
        "all_six_original_same_session_physical_DDR_sources_readback_sha256":observed,
        "same_session_A53_halt_and_FPD128_proven":True,
        "same_session_accepted_P03_PL_bitstream_proven":True,
        "real_1024_A53_terminal_PASS_observed":True,
        "all_1024_full_26tick_1010_neuron_FNV_fingerprints_equal_scalar":True,
        "all_1024_original_10_output_spikes_and_classifications_equal_scalar":True,
        "all_1024_A53_complete_service_timers_structurally_valid":True,
        "numerical_raw_source_journal_sha256":
            numerical_proof["journal_sha256"],
        "numerical_full1024_timing_sha256":
            numerical_proof["timing_sha256"],
        "numerical_terminal_mailbox_sha256":
            numerical_proof["terminal_sha256"],
        "single_session_full1024_numerical_parity_accepted":True,
        "A53_latency_distribution_candidate_not_multisession_benchmark":
            numerical_proof["complete_service_counter_ticks"],
        "six_independent_AB_BA_AB_coldboot_sessions_accepted":False,
        "raw_full_neural_trace_direct_byte_capture":False,
        "boot_DDR_DMA_exclusive_owner_proven":False,
        "full_multisession_TrackB_latency_benchmark_accepted":False,
        "energy_or_pure_PL_speedup_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with report.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,sort_keys=True,indent=2);fp.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("evidence","stage","shards","ingress","oracle","first16",
                "b3_report","elf","linker_map","reset_pins","reports","out"):
        p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    args=p.parse_args()
    try:
        result=verify(args)
        print("P08_B4_2_ALL_1024_ORIGINAL_NEURAL_AND_SPIKE_VECTORS_PHYSICAL_PARITY_PASS=1")
        print("P08_B4_2_ALL_1024_A53_SERVICE_TIMERS_PHYSICAL_CAPTURE_VALID=1")
        print("P08_B4_2_INDEPENDENT_SAME_SESSION_PHYSICAL_PROVENANCE_PASS=1")
        print("P08_B4_2_SIX_SESSION_TRACKB_LATENCY_BENCHMARK_ACCEPTED=0")
        print("P08_B4_2_INDEPENDENT_PHYSICAL_REPORT="+str(args.out))
        return 0
    except (AttestationNoGo,physical.FullPhysicalNoGo,
            physical.prior.PilotPhysicalNoGo,numerical.FullRecordNoGo,
            ValueError,TypeError,OSError,KeyError,AssertionError) as e:
        print("P08_B4_2_INDEPENDENT_PHYSICAL_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
