#!/usr/bin/env python3
"""B4.5 PC-ONLY independent four-report cross-session latency synthesis.

Reads immutable B4.4 service, B4.4.2 reset-profile, once and unchecked
full1024 independent JSON, plus the two optimized saved physical
timing/reset sidecars. Replays 1024 CRC-checked six-phase A53 timings
and 1024 context-reset sidecars; excludes special trace ordinal 1023
from 1023 ordinary-frame metrics. NEVER opens JTAG or rewrites evidence.
A session-median ratio is descriptive, NOT a paired/repeated speedup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

import p08_b2_4_verify_untrusted_first16 as timing
import p08_b45_sidecar as reset

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="p08-b45-physical-cross-session-quantitative-synthesis-v1"
SHA={
 "original_service":"4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81",
 "original_reset":"47f25cada89dd9220636fbb9539aba5bf0d7705ea3788fdc3ebd1d85f1145cfa",
 "once":"06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a",
 "unchecked":"68655383c582577986d7bdd253b21ecf1c933d234136d51b7b5076591c63cf79",
}
ORIGINAL_B4_SHA="297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032"
ORACLE_SHA="7e564d188651aeabdc284328ea65705bcb0b5571468b9f70d5dcacaa3f5493b8"
PHASES=("reset_27_contexts","encode_input","initialize_scheduler",
        "all_26_ticks_702_dispatches_paging_routing","validate_neural_receipt",
        "commit_output_journal")

class SynthesisNoGo(ValueError):pass
def need(ok,why):
    if not ok:raise SynthesisNoGo("NO-GO: "+why)
def sha(path):
    need(path.is_file() and not path.is_symlink(),
         "signed original evidence missing/not regular: "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda:stream.read(1<<20),b""):h.update(part)
    return h.hexdigest()
def signed(path,key,schema):
    need(path.is_absolute(),"source evidence path must be absolute")
    need(sha(path)==SHA[key],"independent "+key+" report SHA drift")
    obj=json.loads(path.read_text())
    need(isinstance(obj,dict) and obj.get("schema")==schema,
         "independent "+key+" report schema drift")
    return obj
def summary(values):
    need(len(values)==1023 and all(math.isfinite(v) and v>0 for v in values),
         "exactly 1023 positive finite ordinary values required")
    ordered=sorted(values)
    return {
      "ordinary_frames":1023,"min_ms":ordered[0],
      "median_ms":statistics.median(values),
      "p95_nearest_rank_ms":ordered[math.ceil(.95*1023)-1],
      "max_ms":ordered[-1],"mean_ms":statistics.mean(values),
      "sum_ms":sum(values),
    }
def replay(mode,report,evidence):
    need(evidence.is_absolute() and evidence.is_dir() and
         not evidence.is_symlink(),"existing absolute physical capture required")
    for key in (
      "new_real_JTAG_A53_halt_P03_programming_six_original_DDR_sources_readback",
      "new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar",
      "new_all_1024_A53_timing_and_reset_profiles_valid",
      "new_all_27_post_run_backup_records_identical_to_original",
      "last_trace_ordinal_1023_excluded_from_ordinary_performance",
      "one_unprotected_session_descriptive_only"):
        need(report.get(key) is True,mode+" independent acceptance missing "+key)
    need(report.get("experiment")==mode and
         report.get("hardware_DDR_backup_protection_proven") is False and
         report.get("transient_backup_mutation_excluded") is False and
         report.get("original_OFFICIAL_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
         report.get("original_complete1024_scalar_SHA256")==ORACLE_SHA and
         report.get("prior_accepted_original_B4_1024_physical_sha256")==ORIGINAL_B4_SHA and
         report.get("prior_accepted_original_B44_single_session_timing_sha256")==SHA["original_service"] and
         len(report.get("new_original_backup_per_core_sha256",{}))==27,
         mode+" original source/backup integrity and unprotected scope mismatch")
    cap=evidence/"performance1024_capture"
    t=cap/"timing1024_physical.bin"
    r=cap/"reset_profile1024_physical.bin"
    need(sha(t)==report.get("timing_sha256") and
         sha(r)==report.get("reset_sidecar_sha256"),
         mode+" saved raw A53 capture hashes differ from independent reports")
    tb=t.read_bytes()
    rb=r.read_bytes()
    need(len(tb)==1024*256 and len(rb)==1024*256,
         mode+" expected two complete 256KiB captures")
    hz=report.get("actual_A53_CNTFRQ_hz")
    need(isinstance(hz,int) and 1000000<=hz<=2000000000,
         mode+" invalid actual A53 counter frequency")
    parsed=reset.audit(rb,mode=mode,expected_rows=1024,
                       observed_hz=hz,require_protection=False)
    need(parsed==report.get("reset_descriptive") and
         parsed["backing_backup_guard_provisioned_flag"]==0,
         mode+" re-parsed reset counters/CRC differ from independent report")
    elapsed=[]
    phase=[[] for _ in PHASES]
    last=None
    for ordinal in range(1024):
        rec=timing.verify_timing(tb[ordinal*256:(ordinal+1)*256],ordinal,last)
        last=rec["after_journal_commit_CNTVCT"]
        need(rec["CNTFRQ_EL0_hz"]==hz,
             mode+" observed actual frequency mismatch at "+str(ordinal))
        if ordinal<1023:
            elapsed.append(rec["complete_service_counter_ticks"]*1000/hz)
            for index,ticks in enumerate(rec["phase_counter_ticks"]):
                phase[index].append(ticks*1000/hz)
    service=summary(elapsed)
    for key in ("min_ms","median_ms","p95_nearest_rank_ms","max_ms"):
        need(service[key]==report["whole_image_service_descriptive_1023"][key],
             mode+" original independent service statistic drift: "+key)
    phases={key:summary(vals) for key,vals in zip(PHASES,phase)}
    need(math.isclose(sum(v["sum_ms"] for v in phases.values()),
                      service["sum_ms"],rel_tol=1e-12,abs_tol=1e-6),
         mode+" six A53 subphases are not additive")
    shares={key:100*value["sum_ms"]/service["sum_ms"]
            for key,value in phases.items()}
    return {
      "actual_a53_cntfrq_hz":hz,"reset_descriptive":parsed,
      "whole_service_descriptive":service,
      "six_disjoint_A53_phase_descriptive":phases,
      "phase_share_of_sum_service_pct":shares,
      "dominant_measured_A53_phase":max(shares,key=shares.get),
      "original_timing_capture_sha256":report["timing_sha256"],
      "original_reset_capture_sha256":report["reset_sidecar_sha256"],
      "1024_classifier_spike_FNV_and_27_backup_endpoints_verified":True,
      "hardware_immutable_backup_write_exclusion_proven":False,
    }

def render(data):
    baseline=data["baseline"]
    result=data["per_mode"]
    ratios=data["descriptive_ratios"]
    lines=[
      "# P08-B4.5 — physical 1,024-image performance synthesis","",
      "**Evidence:** original B4.4 full-service A53 session, separately "
      "instrumented original B4.4.2 reset profile, and independently "
      "accepted once / unchecked V2 full1024 physical sessions. "
      "All sources SHA-256 pinned; original optimized raw timing and reset "
      "sidecars separately rechecked without JTAG.","",
      "| Metric | Original | Authenticate once | Unchecked |",
      "| --- | ---: | ---: | ---: |",
      "| Reset median (ms) | {:.6f} | {:.6f} | {:.6f} |".format(
          baseline["reset_median_ms"],
          result["once"]["reset_descriptive"]["reset_median_ms"],
          result["unchecked"]["reset_descriptive"]["reset_median_ms"]),
      "| Whole-image service median (ms) | {:.6f} | {:.6f} | {:.6f} |".format(
          baseline["service_median_ms"],
          result["once"]["whole_service_descriptive"]["median_ms"],
          result["unchecked"]["whole_service_descriptive"]["median_ms"]),
      "| Reset ratio of session medians | 1x | {:.2f}x | {:.2f}x |".format(
          ratios["once"]["reset_ratio"],ratios["unchecked"]["reset_ratio"]),
      "| Service ratio of session medians | 1x | {:.3f}x | {:.3f}x |".format(
          ratios["once"]["service_ratio"],ratios["unchecked"]["service_ratio"]),
      "","## A53 service-phase attribution after optimization","","| Phase | Once median ms | Once sum share | Unchecked median ms | Unchecked sum share |",
      "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in PHASES:
        a=result["once"]
        b=result["unchecked"]
        lines.append("| {} | {:.3f} | {:.2f}% | {:.3f} | {:.2f}% |".format(
          name,a["six_disjoint_A53_phase_descriptive"][name]["median_ms"],
          a["phase_share_of_sum_service_pct"][name],
          b["six_disjoint_A53_phase_descriptive"][name]["median_ms"],
          b["phase_share_of_sum_service_pct"][name]))
    lines.extend([
       "",
       "## Scientific interpretation and limits","",
       "The original B4.4.2 reset baseline used a DIFFERENT instrumented "
       "physical session from original B4.4 complete service. Each "
       "optimized condition has only ONE accepted JTAG physical session. "
       "The reported ratios compare session medians and are descriptive, "
       "not a randomized AB/BA result or statistical uncertainty estimate.",
       "",
       "Both optimized runs independently matched 1,024 original frozen "
       "predictions, output-spike vectors, and full 26-tick FNV traces; "
       "all 27 original backup records matched at END of each run. "
       "These tests cannot exclude transient DDR writes and cannot "
       "establish hardware memory protection.",
       "",
       "The six A53 service intervals include mixed software/PL paging, "
       "routing, polling and FPGA dispatch. The 26-tick interval is "
       "NOT isolated PL-neural execution or measured energy.",
       "",
       "## Source file SHA-256",
       "",
    ])
    for name,value in data["source_sha256"].items():
        lines.append("- "+name+": "+value)
    lines.extend([
      "",
      "**Next:** Audit the dominant scheduler/pager 26-tick service "
      "phase before modifying the original FPGA. Design a separate "
      "counterbalanced replicated physical protocol with reboots, "
      "source freezes and independent FNV receipts.",
      "",
      "Official MNIST TEST remains SEALED_NOT_ACCESSED.","",
    ])
    return "\n".join(lines)

def analyze(original_service,original_profile,once,unchecked,
            once_evidence,unchecked_evidence,out,md):
    need(out.is_absolute() and md.is_absolute() and
         out!=md and out.parent.is_dir() and md.parent.is_dir() and
         not out.exists() and not md.exists() and
         not out.is_symlink() and not md.is_symlink() and
         not out.resolve().is_relative_to(ROOT.resolve()) and
         not md.resolve().is_relative_to(ROOT.resolve()),
         "new external distinct no-overwrite JSON/Markdown outputs required")
    s=signed(original_service,"original_service",
         "p08-b4-4-original-full1024-single-physical-session-timing-descriptive-v1")
    p=signed(original_profile,"original_reset",
         "p08-b44-original1024-independent-physical-reset-profile-jtag-v1")
    a=signed(once,"once",
         "p08-b45-unprotected-full1024-independent-real-jtag-v1")
    b=signed(unchecked,"unchecked",
         "p08-b45-unprotected-full1024-independent-real-jtag-v1")
    need(s.get("ordinary_frame_count")==1023 and
         s.get("full_original_frame_count")==1024 and
         s.get("ordinary_complete_service",{}).get("n")==1023 and
         s.get("independent_physical_full1024_report_sha256")==ORIGINAL_B4_SHA and
         s.get("full1024_original_scalar_oracle_sha256")==ORACLE_SHA and
         s.get("service_scope")==
          "original_full_A53_image_service_entry_to_after_journal_commit_excluding_timing_sidecar_and_setup",
         "original B4.4 complete image-service scope wrong")
    need(p.get("first_original_1024_B4_2_independent_report_sha256")==ORIGINAL_B4_SHA and
         p.get("accepted_original_1023_B4_4_timing_report_sha256")==SHA["original_service"] and
         p.get("original_1024_scalar_oracle_sha256")==ORACLE_SHA and
         p.get("one_genuine_1024_physical_profile_session_numerical_equivalence_accepted") is True and
         p.get("all_1024_new_27core_reset_profiles_sha_copy_cache_crc_and_clock_valid") is True and
         p.get("new_five_phase_timer_instrumentation_changes_execution_cost") is True,
         "original B4.4.2 reset profile scope or genuine physical source changed")
    summary_reset=p["new_1023_ordinary_reset_profile_descriptive"]
    need(summary_reset.get("n_ordinary")==1023 and
         summary_reset.get("ordinary_reset_service",{}).get("n")==1023,
         "profile ordinary-frame geometry mismatch")
    baseline_reset=summary_reset["ordinary_reset_service"]["median_ms"]
    baseline_service=s["ordinary_complete_service"]["median_ms"]
    need(baseline_reset>0 and baseline_service>0,
         "original signed baseline latency not positive")
    per={"once":replay("once",a,once_evidence),
         "unchecked":replay("unchecked",b,unchecked_evidence)}
    ratios={}
    for mode,value in per.items():
        rr=value["reset_descriptive"]["reset_median_ms"]
        ss=value["whole_service_descriptive"]["median_ms"]
        ratios[mode]={
          "reset_ratio":baseline_reset/rr,
          "reset_reduction_percent":100*(1-rr/baseline_reset),
          "service_ratio":baseline_service/ss,
          "service_reduction_percent":100*(1-ss/baseline_service),
          "service_median_difference_ms":baseline_service-ss,
        }
    result={
      "schema":SCHEMA,
      "source_sha256":{**SHA,"original_B4_physical":ORIGINAL_B4_SHA,
                       "original_full1024_scalar_oracle":ORACLE_SHA},
      "baseline":{
        "reset_median_ms":baseline_reset,
        "reset_p95_ms":summary_reset["ordinary_reset_service"]["p95_nearest_rank_ms"],
        "service_median_ms":baseline_service,
        "service_p95_ms":s["ordinary_complete_service"]["p95_nearest_rank_ms"],
        "reset_instrumented_session_is_DISTINCT_from_service_session":True,
      },
      "per_mode":per,
      "descriptive_ratios":ratios,
      "once_minus_unchecked_reset_median_ms":
        per["once"]["reset_descriptive"]["reset_median_ms"]-
        per["unchecked"]["reset_descriptive"]["reset_median_ms"],
      "once_minus_unchecked_service_median_ms":
        per["once"]["whole_service_descriptive"]["median_ms"]-
        per["unchecked"]["whole_service_descriptive"]["median_ms"],
      "ordinary_frames_per_session":1023,
      "excluded_trace_ordinal":1023,
      "both_modes_neural_parity_and_original_backup_endpoints_pass":True,
      "paired_randomized_repeated_session_speedup_proven":False,
      "statistical_significance_or_cross_session_uncertainty_proven":False,
      "DDR_hardware_backup_write_exclusion_proven":False,
      "pure_FPGA_only_accelerator_timing_proven":False,
      "energy_improvement_proven":False,
      "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
      "hardware_or_JTAG_access_performed":False,
    }
    with out.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,sort_keys=True,indent=2)
        fp.write("\n")
    with md.open("x",encoding="utf-8") as fp:fp.write(render(result))
    return result

def main(argv=None):
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ("original_service","original_profile","once_report",
                 "unchecked_report","once_evidence","unchecked_evidence",
                 "out","markdown_out"):
        cli.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    a=cli.parse_args(argv)
    try:
        result=analyze(a.original_service,a.original_profile,a.once_report,
                       a.unchecked_report,a.once_evidence,a.unchecked_evidence,
                       a.out,a.markdown_out)
    except (SynthesisNoGo,ValueError,TypeError,KeyError,IndexError,OSError) as exc:
        print("P08_B45_SYNTHESIS_NO_GO="+str(exc),file=sys.stderr)
        return 3
    print("P08_B45_SIGNED_FOUR_REPORT_AND_RAW_A53_SIDECAR_COMPARE_PASS=1")
    for mode in ("once","unchecked"):
        detail=result["descriptive_ratios"][mode]
        print("P08_B45_"+mode.upper()+"_RESET_RATIO_OF_MEDIANS="+str(detail["reset_ratio"]))
        print("P08_B45_"+mode.upper()+"_SERVICE_RATIO_OF_MEDIANS="+str(detail["service_ratio"]))
        print("P08_B45_"+mode.upper()+"_DOMINANT_A53_PHASE="+
              result["per_mode"][mode]["dominant_measured_A53_phase"])
    print("P08_B45_STATISTICAL_PAIRED_REPEATED_SPEEDUP_PROVEN=0")
    print("P08_B45_PC_ONLY_NO_BOARD_CONTACT=1")
    print("P08_B45_SYNTHESIS_JSON="+str(a.out))
    print("P08_B45_SYNTHESIS_MARKDOWN="+str(a.markdown_out))
    return 0

if __name__=="__main__":raise SystemExit(main())
