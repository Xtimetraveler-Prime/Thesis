#!/usr/bin/env python3
"""Independent NEW A2.1 rebuilt candidate real physical 1024 verification.

Read only after physical XSDB capture. Historical original A2.1 SHA pins
and old physical acceptance remain immutable. This report is NOT 6-run A/B
approval; hardware DDR write protection not established.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

from loihi_twin_v2.p07_a4_stream import parse_journal
from loihi_twin_v2.p08_a2_timing import parse_timing
from p07_a4_2_verify import validate_staging
from p08_a3_2_pair_check import verified_source,require_original_p07_oracle
import p08_b46_a21_rebuild_admission as candidate
import p08_b46_auth_once_source_gate as b46

SCHEMA="p08-b46-rebuilt-A21-1024-independent-physical-neural-and-timing-v1"
SOURCE_SHA="ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56"

class PhysicalNoGo(ValueError):pass
def need(ok:bool,why:str)->None:
    if not ok:raise PhysicalNoGo("NO-GO: "+why)
def sha(path:Path)->str:
    need(path.is_file() and not path.is_symlink(),"source missing or symlinked: "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda:stream.read(1<<20),b""):h.update(part)
    return h.hexdigest()

def audit(build:Path,xsa:Path,source_report:Path,candidate_report:Path,
          stage:Path,run:Path,report:Path)->dict:
    need(report.is_absolute() and report.parent.is_dir() and
         not report.exists() and not report.is_symlink() and
         not report.resolve().is_relative_to(build.resolve()) and
         not report.resolve().is_relative_to(Path(__file__).resolve().parents[1]),
         "new no-overwrite report outside source build/Git required")
    need(run.is_absolute() and run.is_dir() and stage.is_absolute() and
         stage.is_dir() and run!=stage,
         "actual original staged TRAIN source and distinct physical evidence required")
    actual=candidate.inspect_rebuild(build,xsa)
    need(sha(candidate_report) and
         json.loads(candidate_report.read_text())==actual and
         sha(source_report)==SOURCE_SHA,
         "new candidate admission or signed A-vs-B_AUTH_ONCE source proof incorrect")
    source=json.loads(source_report.read_text())
    need(source.get("schema")==b46.REBUILT_SCHEMA and
         source.get("arm_A")=="A_REBUILT_A21_CANDIDATE_42_NEURONS_26_DISPATCHES" and
         source.get("selected_A_real_elf_sha256")==candidate.NEW_A21_SHA and
         source.get("new_A_rebuilt_candidate_KV260_neural_parity_and_timing_reaccepted") is False and
         source.get("six_new_physical_JTAG_runs_authorized") is False and
         source.get("optimized_B_once_full1024_elf_sha256")==b46.B_ELF_SHA and
         source.get("identical_original_TRAIN_1024_source_index_and_raw_pixel_SHA") is True and
         source.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
         "signed PC source gate differs from original newly-built A and accepted B once")
    identity=(run/"physical_identity.txt").read_text()
    need("b46_selected_source_report_sha256="+SOURCE_SHA in identity.splitlines() and
         "b46_A_candidate_host_only_admission_sha256="+sha(candidate_report) in identity.splitlines(),
         "physical identity missing both signed original PC source proofs")
    elf=build/candidate.A_BUILD_REL
    journal,trace,timing=verified_source(run,"A2_1",candidate.NEW_A21_SHA)
    meta,stream=validate_staging(stage)
    need(meta.get("scope")=="TRAIN_DERIVED_VALIDATION_FIRST_1024" and
         stream.image_count==1024 and stream.trace_index==1023 and
         meta.get("official_mnist_test")=="SEALED",
         "frozen original 1024 TRAIN source and selected trace invalid")
    # Calls the original accepted independent original P07 packed software
    # oracle, not an expected output from the new A53 executable.
    require_original_p07_oracle(stage,journal,trace)
    neural=parse_journal(journal.read_bytes(),stream)
    image=parse_timing(timing.read_bytes(),expected_count=1024)
    need(image.trace_index==1023 and len(image.records)==1024 and len(neural)==1024,
         "actual 1024 neural records and A53 CRC timestamps incomplete")
    need(not (run/"p08_a2_2_ticks_3m.bin").exists(),
         "detailed A2.2 26tick sidecar may not be substituted for A2.1")
    hz=image.cntfrq_hz
    need(isinstance(hz,int) and 1_000_000<hz<2_000_000_000,
         "actual A53 CNTFRQ invalid")
    durations=[r.service_ticks*1000/hz for r in image.records[:1023]]
    need(len(durations)==1023 and all(math.isfinite(v) and v>0 for v in durations),
         "exact 1023 strictly-positive original ordinary service durations missing")
    ordered=sorted(durations)
    evidence={
        "new_rebuilt_ELF":elf,
        "new_rebuilt_build_receipt":build/"build_identity.txt",
        "candidate_PC_admission":candidate_report,
        "B46_original_A_vs_B_auth_once_signed_source":source_report,
        "original_stage_descriptor":stage/"p07_a4_descriptor_256.bin",
        "original_stage_mapping":stage/"p07_a4_mapping_1568.bin",
        "original_stage_pixels":stage/"p07_a4_pixels_raw.bin",
        "original_stage_manifest":stage/"p07_a4_2a_stage_manifest.json",
        "physical_identity":run/"physical_identity.txt",
        "actual_real_A53_terminal_log":run/"a53_run.log",
        "actual_real_A53_journal":journal,
        "actual_real_A53_selected_trace":trace,
        "actual_real_A53_timing":timing,
        "actual_real_physical_DDR_readback_master":run/"readback"/"readback_40000000.bin",
    }
    need(all(v.is_file() for v in evidence.values()),"missing original evidence file")
    result={
        "schema":SCHEMA,
        "genuine_operator_JTAG_A53_P03_once":True,
        "new_rebuilt_A2_1_distinct_ELF_SHA256":candidate.NEW_A21_SHA,
        "historically_accepted_A2_1_ELF_SHA256_unmodified":candidate.HISTORICAL_A21_SHA,
        "original_P03_XSA_SHA256":candidate.P03_XSA_SHA,
        "B46_source_report_sha256":SOURCE_SHA,
        "rebuilt_A21_candidate_PC_admission_sha256":sha(candidate_report),
        "original_P07_all_1024_independent_packed_neural_oracle":"PASS",
        "original_P07_selected_26x42_neural_trace":"EXACT",
        "new_A53_image_sidecar_crc_and_cntfrq":"PASS",
        "original_A53_observed_CNTFRQ_EL0_hz":hz,
        "ordinary_frames":1023,
        "special_trace_ordinal_excluded":1023,
        "original_A2_1_image_service_median_ms":statistics.median(durations),
        "original_A2_1_image_service_p95_nearest_rank_ms":ordered[math.ceil(.95*1023)-1],
        "original_A2_1_image_service_min_ms":ordered[0],
        "original_A2_1_image_service_max_ms":ordered[-1],
        "new_A_candidate_physically_revalidated_for_THIS_1024_session":True,
        "old_original_historical_A21_ELF_reproduced":False,
        "A_vs_B_auth_once_service_timer_boundaries_matched":False,
        "B46_six_repeated_A_B_auth_once_sessions_accepted":False,
        "hardware_DDR_owner_DMA_exclusivity_proven":False,
        "physical_session_requires_KV260_reboot":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "source_sha256":{k:sha(v) for k,v in evidence.items()},
    }
    with report.open("x",encoding="utf-8") as f:
        json.dump(result,f,sort_keys=True,indent=2)
        f.write("\n")
    return result

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("build","xsa","source_report","candidate_report","stage",
                 "evidence","out"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    args=p.parse_args(argv)
    try:
        obj=audit(args.build,args.xsa,args.source_report,
                  args.candidate_report,args.stage,args.evidence,args.out)
    except (PhysicalNoGo,candidate.CandidateNoGo,b46.GateNoGo,
            ValueError,TypeError,OSError,KeyError,IndexError) as e:
        print("P08_B46_REBUILT_A21_NEW_PHYSICAL_NEURAL_VERIFY_NO_GO="+str(e),
              file=sys.stderr)
        return 3
    print("P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1")
    print("P08_B46_REBUILT_A21_KV260_CNTFRQ_HZ="+str(obj["original_A53_observed_CNTFRQ_EL0_hz"]))
    print("P08_B46_REBUILT_A21_A53_ORDINARY_MEDIAN_MS="+
          str(obj["original_A2_1_image_service_median_ms"]))
    print("P08_B46_NEW_A_B_SIX_REPEATED_PHYSICAL_SESSIONS_ACCEPTED=0")
    print("P08_B46_A_B_TIMER_BOUNDARY_EQUIVALENCE_PROVEN=0")
    print("P08_B46_NEW_A21_PHYSICAL_INDEPENDENT_REPORT="+str(args.out))
    return 0
if __name__=="__main__":raise SystemExit(main())
