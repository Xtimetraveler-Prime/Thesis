#!/usr/bin/env python3
"""P08-B4.4.2 parse NEW 1024x256B reset-profile sidecar, PC ONLY.

This tool can ONLY validate structural fields and per-row A53 reset
subphase totals. NO physical provenance, signed baseline ELF equivalence,
original 1024 neural scalar parity or physical latency comparison is
claimed. Original B2.3 production sidecars are distinct and immutable.
No XSDB, JTAG, hardware, Vitis, external downloads, or official TEST.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import struct
import sys
import zlib

MAGIC=0x50523434
VERSION=1
PASS=0x600D0823
DONE=0xC0DEF00D
COUNT=1024
BYTES=256
COPIED=27*512*1024
PHASES=(
    "original_immutable_cache_invalidate",
    "original_immutable_sha256",
    "mutable_27core_memcpy",
    "mutable_cache_clean_invalidate",
    "mutable_sha256_readback",
)
SCHEMA="p08-b44-reset-profile-1024-structural-local-only-v1"
class ProfileNoGo(ValueError):pass

def require(ok:bool,msg:str)->None:
    if not ok:raise ProfileNoGo("NO-GO: "+msg)

def u64(w:tuple[int,...],pos:int)->int:
    return w[pos] | (w[pos+1]<<32)

def decode_row(row:bytes,ordinal:int,hz:int)->dict:
    require(len(row)==BYTES, f"profile {ordinal}: wrong row byte count")
    w=struct.unpack("<64I",row)
    require((w[0],w[1],w[2],w[3],w[4])==
            (MAGIC,VERSION,ordinal,PASS,ordinal+1),
            f"profile {ordinal}: original profile ID/success/sequence wrong")
    require((w[5],w[6],w[7],w[8])==(27,COPIED,27,27),
            f"profile {ordinal}: 27 trusted source/destination SHA/copy counts changed")
    require(u64(w,9)==hz and hz>0 and w[63]==DONE and w[62]==0
            and not any(w[25:61]),
            f"profile {ordinal}: A53 clock/DONE/reserved bytes invalid")
    require(w[61]==zlib.crc32(row[:61*4]),
            f"profile {ordinal}: CRC corrupted")
    full=u64(w,11)
    durations=[u64(w,13+2*j) for j in range(5)]
    residual=u64(w,23)
    require(full>0 and residual<=full and all(p<=full for p in durations)
            and sum(durations)+residual==full,
            f"profile {ordinal}: non-additive subphase service timing")
    return {
        "ordinal":ordinal,
        "total_reset_ticks":full,
        "phase_ticks":dict(zip(PHASES,durations)),
        "unattributed_ticks":residual,
        "verified_immutable_source_records":27,
        "verified_mutable_destination_records":27,
        "copied_bytes":COPIED,
        "actual_a53_counter_frequency_hz":hz,
    }

def summary(vals:list[int],hz:int)->dict:
    require(len(vals)==COUNT-1,"must use 1023 ordinary trace-excluded frames")
    sorted_vals=sorted(vals)
    med=statistics.median(vals)
    p95=sorted_vals[(len(vals)*95+99)//100-1]
    return {
        "n":len(vals),"median_ticks":med,
        "median_ms":med*1000/hz,
        "p95_nearest_rank_ms":p95*1000/hz,
        "min_ms":sorted_vals[0]*1000/hz,
        "max_ms":sorted_vals[-1]*1000/hz,
        "sum_ticks":sum(vals),
    }

def audit(raw:bytes,hz:int)->dict:
    require(len(raw)==COUNT*BYTES and hz>0,
            "1024 exact profile rows and observed A53 CNTFRQ required")
    rows=[decode_row(raw[i*BYTES:(i+1)*BYTES],i,hz) for i in range(COUNT)]
    ordinary=rows[:1023]
    total=[x["total_reset_ticks"] for x in ordinary]
    phase_summary={name:summary([x["phase_ticks"][name] for x in ordinary],hz)
                   for name in PHASES}
    residual=summary([x["unattributed_ticks"] for x in ordinary],hz)
    all_ticks=sum(total)
    require(sum(x["sum_ticks"] for x in phase_summary.values())+
            residual["sum_ticks"]==all_ticks,
            "original five exact subspans/residual not additive")
    return {
        "schema":SCHEMA,
        "n_capture_rows":COUNT,
        "n_ordinary":1023,
        "selected_trace_ordinal_excluded":1023,
        "recorded_a53_counter_frequency_hz":hz,
        "profile_binary_sha256":hashlib.sha256(raw).hexdigest(),
        "ordinary_reset_service":summary(total,hz),
        "ordinary_five_reset_subphases":{
            name:{**item,
                  "share_of_total_reset_ticks_pct":
                    100*item["sum_ticks"]/all_ticks}
            for name,item in phase_summary.items()},
        "ordinary_unattributed_counter_overhead":{
            **residual,"share_of_total_reset_ticks_pct":
            100*residual["sum_ticks"]/all_ticks},
        "selected_trace_1023":rows[1023],
        "actual_KV260_physical_provenance_independently_proven":False,
        "full1024_original_FNV_classifier_parity_proven":False,
        "measured_neural_FPGA_PL_only_time":False,
        "accepted_multisession_A_v_B_comparison":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile",required=True,type=Path,
                   help="experimental 1024x256B physical profile sidecar")
    p.add_argument("--actual-hz",required=True,type=int)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    try:
        require(a.profile.is_absolute() and a.profile.is_file() and
                not a.profile.is_symlink(),"external new profile binary required")
        require(a.out.is_absolute() and a.out.parent.is_dir() and
                not a.out.exists() and not a.out.is_symlink() and
                not a.out.resolve().is_relative_to(Path(__file__).resolve().parents[3]),
                "new outside-repo no-overwrite report required")
        data=audit(a.profile.read_bytes(),a.actual_hz)
        with a.out.open("x",encoding="utf-8") as stream:
            json.dump(data,stream,sort_keys=True,indent=2)
            stream.write("\n")
        print("P08_B44_RESET_PROFILE_1024_STRUCTURAL_ONLY_PASS=1")
        print("P08_B44_RESET_PROFILE_INDEPENDENT_PHYSICAL_PROVENANCE_PASS=0")
        print("P08_B44_RESET_PROFILE_ORIGINAL_NEURAL_PARITY_PASS=0")
        print("P08_B44_RESET_PROFILE_MULTISESSION_LATENCY_ACCEPTED=0")
        print("P08_B44_RESET_PROFILE_LOCAL_OUTPUT="+str(a.out))
        return 0
    except (OSError,TypeError,ValueError,ProfileNoGo) as e:
        print("P08_B44_RESET_PROFILE_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
