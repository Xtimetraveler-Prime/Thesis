#!/usr/bin/env python3
"""P08-B4.4 exploratory ONE-SESSION physical timing analysis, PC ONLY.

Re-authenticate the operator's genuine independently verified full1024
physical report SHA and its matching raw 1024*256B A53 timing capture.
Use ACTUAL CNTFRQ from 1024 CRC-checked sidecars and terminal mailbox.
Exclude selected trace ordinal 1023 from 1023 ordinary-frame results,
but retain its separate receipt. Report six *disjoint A53* phase spans,
not PL cycles. No hardware/JTAG, no accepted source modification,
no 6-session paired A/B acceptance or speedup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys

import p08_b2_4_verify_untrusted_first16 as original
import p08_b4_2_verify_full1024 as b42

SCHEMA="p08-b4-4-original-full1024-single-physical-session-timing-descriptive-v1"
PIN="297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032"
ORACLE_SHA="7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8"
SCOPE="original_full_A53_image_service_entry_to_after_journal_commit_excluding_timing_sidecar_and_setup"
PHASES=(
    "restore_original_27_logical_core_states",
    "encode_original_B13_input",
    "restart_virtualized_scheduler",
    "run_all_26_ticks_including_702_dispatches_paging_routing_and_nested_trace",
    "validate_original_full_inference_receipt",
    "commit_original_neural_result_journal",
)
COUNT=1024
TRACE_ORDINAL=1023
class TimingNoGo(ValueError):pass

def require(ok:bool,msg:str)->None:
    if not ok:raise TimingNoGo("NO-GO: "+msg)

def file_data(p:Path)->bytes:
    require(p.is_file() and not p.is_symlink(),"missing/symlink evidence: "+str(p))
    return p.read_bytes()

def checksum(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def quantile_summary(ticks:list[int],hz:int)->dict:
    require(bool(ticks),"empty physical clock sample")
    ordered=sorted(ticks)
    median=statistics.median(ticks)
    mean=sum(ticks)/len(ticks)
    p95=ordered[(95*len(ordered)+99)//100-1]
    return {
        "n":len(ticks),
        "min_ticks":ordered[0],"median_ticks":median,
        "p95_nearest_rank_ticks":p95,"max_ticks":ordered[-1],
        "mean_ticks":mean,
        "min_ms":ordered[0]*1000/hz,
        "median_ms":median*1000/hz,
        "p95_nearest_rank_ms":p95*1000/hz,
        "max_ms":ordered[-1]*1000/hz,
        "mean_ms":mean*1000/hz,
    }

def analyze(report:Path,evidence:Path,out:Path)->dict:
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink() and
            not out.resolve().is_relative_to(b42.merge.shard.ROOT),
            "new external absolute no-overwrite timing report required")
    require(report.is_absolute() and evidence.is_absolute()
            and evidence.is_dir() and not evidence.is_symlink(),
            "exact original independent report and physical evidence required")
    report_bytes=file_data(report)
    require(checksum(report_bytes)==PIN,
            "operator accepted independent full1024 physical SHA changed")
    physical=json.loads(report_bytes)
    require(
        physical.get("schema")==
        "p08-b4-2-original1024-independent-physical-jtag-numerical-v1"
        and physical.get("original_full1024_scalar_sha256")==ORACLE_SHA
        and physical.get("single_session_full1024_numerical_parity_accepted") is True
        and physical.get("real_1024_A53_terminal_PASS_observed") is True
        and physical.get(
            "all_1024_A53_complete_service_timers_structurally_valid") is True
        and physical.get(
            "all_1024_full_26tick_1010_neuron_FNV_fingerprints_equal_scalar") is True
        and physical.get("full_multisession_TrackB_latency_benchmark_accepted") is False
        and physical.get("boot_DDR_DMA_exclusive_owner_proven") is False
        and physical.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
        "independent actual full1024 source/clock/provenance acceptance invalid")
    cap=evidence/"full1024_capture"
    require(cap.is_dir() and not cap.is_symlink(),
            "exact original full1024 physical capture dir absent")
    timing_bytes=file_data(cap/"timing1024_physical.bin")
    require(len(timing_bytes)==COUNT*b42.ROW and
            checksum(timing_bytes)==physical["numerical_full1024_timing_sha256"],
            "physical 1024 timing sidecar differs from accepted independent report")
    mb=file_data(cap/"mailbox_terminal_physical.bin")
    require(checksum(mb)==physical["numerical_terminal_mailbox_sha256"],
            "actual terminal mailbox differs from accepted independent report")
    terminal=b42.check_mailbox(mb)
    hz=terminal["CNTFRQ_EL0_hz"]
    whole=[]
    phases=[[] for _ in PHASES]
    prior=None
    special=None
    for i in range(COUNT):
        try:
            timing=original.verify_timing(
                timing_bytes[i*b42.ROW:(i+1)*b42.ROW],i,prior)
        except (original.RecordNoGo,ValueError,KeyError) as e:
            raise TimingNoGo(f"frame {i}: {e}") from e
        require(timing["CNTFRQ_EL0_hz"]==hz,
                f"frame {i}: actual A53 frequency inconsistent with terminal")
        prior=timing["after_journal_commit_CNTVCT"]
        if i==TRACE_ORDINAL:
            special={
                "ordinal":i,"service_ticks":timing["complete_service_counter_ticks"],
                "service_ms":timing["complete_service_counter_ticks"]*1000/hz,
                "phase_ticks":dict(zip(PHASES,timing["phase_counter_ticks"])),
                "special_trace_scope_excluded_from_ordinary":True,
            }
            continue
        whole.append(timing["complete_service_counter_ticks"])
        for j,span in enumerate(timing["phase_counter_ticks"]):
            phases[j].append(span)
    require(len(whole)==1023 and all(len(x)==1023 for x in phases)
            and special is not None,"ordinary 1023 and selected trace frame incomplete")
    # A53 phase spans are disjoint per image, so their sums and MEANS
    # are additive. Their MEDIANS are not additive; avoid false claims.
    assert sum(sum(p) for p in phases)==sum(whole)
    total=sum(whole)
    result={
        "schema":SCHEMA,
        "independent_physical_full1024_report_sha256":PIN,
        "full1024_original_scalar_oracle_sha256":ORACLE_SHA,
        "original_physical_timer_sha256":checksum(timing_bytes),
        "original_terminal_mailbox_sha256":checksum(mb),
        "recorded_actual_A53_CNTFRQ_EL0_hz":hz,
        "clock":"A53_CNTVCT_EL0_not_FPGA_PL_cycles",
        "service_scope":SCOPE,
        "full_original_frame_count":COUNT,
        "ordinary_frame_count":1023,
        "ordinal_1023_excluded_as_selected_trace":True,
        "ordinary_complete_service":quantile_summary(whole,hz),
        "ordinary_six_disjoint_service_phases":{
            label:{
                **quantile_summary(vals,hz),
                "sum_ticks":sum(vals),
                "share_of_sum_complete_service_pct":100*sum(vals)/total,
            } for label,vals in zip(PHASES,phases)
        },
        "selected_trace_1023":special,
        "one_independently_verified_real_physical_session":True,
        "six_repeated_AB_BA_AB_physical_sessions_accepted":False,
        "cross_track_neural_complexity_matched":False,
        "direct_PL_only_latency_seconds_measured":False,
        "physical_speedup_or_energy_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,indent=2,sort_keys=True)
        fp.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for option in ("report","evidence","out"):
        p.add_argument("--"+option,type=Path,required=True)
    args=p.parse_args()
    try:
        x=analyze(args.report,args.evidence,args.out)
        print("P08_B4_4_ONE_ORIGINAL_VERIFIED_1024_SESSION_A53_DESCRIPTIVE_TIMING_PASS=1")
        print("P08_B4_4_ACTUAL_A53_CNTFRQ_EL0_HZ="+str(x["recorded_actual_A53_CNTFRQ_EL0_hz"]))
        print("P08_B4_4_1023_ORDINARY_MEDIAN_SERVICE_MS="+
              str(x["ordinary_complete_service"]["median_ms"]))
        print("P08_B4_4_1023_ORDINARY_P95_SERVICE_MS="+
              str(x["ordinary_complete_service"]["p95_nearest_rank_ms"]))
        for phase,v in x["ordinary_six_disjoint_service_phases"].items():
            print("P08_B4_4_PHASE_"+phase.upper()+"_MEDIAN_MS="+str(v["median_ms"]))
            print("P08_B4_4_PHASE_"+phase.upper()+"_SHARE_OF_SUM_PCT="+
                  str(v["share_of_sum_complete_service_pct"]))
        print("P08_B4_4_SIX_REPEATED_PHYSICAL_SESSIONS_ACCEPTED=0")
        print("P08_B4_4_DESCRIPTIVE_REPORT="+str(args.out))
        return 0
    except (TimingNoGo,b42.FullRecordNoGo,original.RecordNoGo,
            ValueError,TypeError,OSError,KeyError,AssertionError) as e:
        print("P08_B4_4_SINGLE_SESSION_TIMING_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
