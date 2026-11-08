#!/usr/bin/env python3
"""P08-B4.2: strict 1,024 row original B2.4 physical-output FORMAT verifier.

This verifies 1,024 raw journals, six-stage service timing counters and
the genuine full 1024 terminal 256B mailbox against an independently
generated full 1024 scalar reference. It does NOT authenticate JTAG/board
provenance; that requires separate same-session evidence attestation.
No XSDB/Vivado/tool subprocesses and NO official MNIST TEST.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import struct
import sys

import p08_b2_4_verify_untrusted_first16 as records
import p08_b4_1_merge_scalar_1024 as merge
import p08_b3_pilot16_admission as original16

COUNT=1024
ROW=256
SCHEMA="p08-b4-2-full1024-unverified-scalar-journal-timing-v1"
class FullRecordNoGo(ValueError):pass

def check(cond:bool,msg:str)->None:
    if not cond:raise FullRecordNoGo("NO-GO: "+msg)

def read(p:Path,length:int|None=None)->bytes:
    check(p.is_file() and not p.is_symlink(),"missing/symlink file "+str(p))
    data=p.read_bytes()
    check(length is None or len(data)==length,"invalid file length "+str(p))
    return data

def check_mailbox(raw:bytes)->dict:
    check(len(raw)==ROW,"full1024 mailbox must be exactly 256 bytes")
    w=struct.unpack("<64I",raw)
    check((w[0],w[1],w[2],w[3],w[4],w[5],w[63])==
          (records.MAILBOX_MAGIC,1,records.PASS,1023,0,1024,records.DONE),
          "terminal A53 mailbox not exact 1024/1024 PASS")
    hz=w[6] | (w[7]<<32)
    check(1_000_000<=hz<=2_000_000_000 and
          (w[8],w[9],w[10],w[11],w[12],w[13])==
          (1024,702,26,0,0,0) and not any(w[14:63]),
          "A53 final generation/page/barrier/error counters or CNTFRQ drift")
    return {"last_completed_ordinal":1023,"count":1024,"CNTFRQ_EL0_hz":hz}

def verify(oracle:Path,first16:Path,journal:Path,timing:Path,
           mailbox:Path,out:Path)->dict:
    check(out.is_absolute() and not out.exists() and not out.is_symlink()
          and out.parent.is_dir() and
          not out.resolve().is_relative_to(merge.shard.ROOT),
          "new external JSON report path required")
    old=original16.source_oracle(first16)
    oracle_raw=read(oracle)
    m=json.loads(oracle_raw)
    check(m.get("schema")==merge.SCHEMA and m.get("count")==COUNT and
          m.get("shard_count")==64 and m.get("shard_size")==16 and
          m.get("original_first16_physically_verified_scalar_oracle_sha256")==
          original16.ORACLE_SHA and
          m.get("original_raw1024_sha256")==merge.baseline.RAW_POOL_SHA and
          m.get("original_B24_compiled_sha256")==
          "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a" and
          m.get("original_B24_source_sha256")==
          "0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a" and
          m.get("actual_KV260_1024_physical_execution") is False and
          m.get("physical_latency_accepted") is False and
          m.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "unauthorized/incomplete first1024 original scalar source")
    rows=m.get("frames")
    check(isinstance(rows,list) and len(rows)==COUNT and
          rows[:16]==old["frames"],
          "1024 oracle first16 differs from accepted signed original B3 oracle")
    frames_in=read(journal,COUNT*ROW)
    timers_in=read(timing,COUNT*ROW)
    mail=check_mailbox(read(mailbox,ROW))
    prior=None
    service=[]
    phases=[[] for _ in range(6)]
    for i in range(COUNT):
        row=rows[i]
        check(row.get("ordinal")==i,"scalar oracle ordinals not consecutive")
        try:
            decoded=records.verify_journal(
                frames_in[i*ROW:(i+1)*ROW],i,row)
            timer=records.verify_timing(
                timers_in[i*ROW:(i+1)*ROW],i,prior)
        except (records.RecordNoGo,KeyError,ValueError) as e:
            raise FullRecordNoGo(f"frame {i}: {e}") from e
        check(timer["CNTFRQ_EL0_hz"]==mail["CNTFRQ_EL0_hz"],
              "physical per-frame CNTFRQ differs from final mailbox")
        check(decoded["TRAIN_source_index"]==row["TRAIN_source_index"] and
              decoded["prediction"]==row["expected_prediction"],
              f"physical frame {i} TRAIN/prediction mismatch")
        prior=timer["after_journal_commit_CNTVCT"]
        service.append(timer["complete_service_counter_ticks"])
        for j,p in enumerate(timer["phase_counter_ticks"]):
            phases[j].append(p)
    def summaries(vals):
        return {"count":len(vals),"min":min(vals),"max":max(vals),
                "median":statistics.median(vals),
                "p95_nearest_rank":sorted(vals)[(len(vals)*95+99)//100-1]}
    result={
        "schema":SCHEMA,"count":COUNT,
        "scalar_oracle_sha256":hashlib.sha256(oracle_raw).hexdigest(),
        "genuine_physical_provenance_verified":False,
        "actual_KV260_1024_numerical_accepted":False,
        "all_1024_original_full26_tick_neural_FNV_equal_scalar":True,
        "all_1024_10_output_spikes_and_classifications_equal_scalar":True,
        "all_1024_timing_rows_additive_and_monotonic":True,
        "terminal":mail,
        "complete_service_counter_ticks":summaries(service),
        "six_separate_phase_counter_tick_summaries":[summaries(v) for v in phases],
        "journal_sha256":hashlib.sha256(frames_in).hexdigest(),
        "timing_sha256":hashlib.sha256(timers_in).hexdigest(),
        "terminal_sha256":hashlib.sha256(read(mailbox,ROW)).hexdigest(),
        "raw_full_neuron_trace_directly_readback":False,
        "physical_energy_or_speedup_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fd:
        json.dump(result,fd,sort_keys=True,indent=2);fd.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("oracle","first16","journal","timing","mailbox","out"):
        p.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args()
    try:
        result=verify(a.oracle,a.first16,a.journal,a.timing,a.mailbox,a.out)
        print("P08_B4_2_UNTRUSTED_1024_NUMERICAL_AND_SERVICE_COUNTERS_EQUAL_SCALAR=1")
        print("P08_B4_2_PHYSICAL_JTAG_PROVENANCE_INDEPENDENTLY_VERIFIED=0")
        print("P08_B4_2_1024_PHYSICAL_LATENCY_ACCEPTED=0")
        print("P08_B4_2_UNTRUSTED_FORMAT_REPORT="+str(a.out))
        return 0
    except (FullRecordNoGo,ValueError,TypeError,OSError,KeyError,AssertionError) as e:
        print("P08_B4_2_FULL1024_FORMAT_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
