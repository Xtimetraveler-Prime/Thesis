#!/usr/bin/env python3
"""P08-B4.1: original B2.4 full-1024 scalar oracle in 64 PC-only shards.

One independently calculated 16-image shard per invocation; no FPGA/JTAG,
no model training, no official MNIST TEST. Reuses the EXACT accepted P08-B2.4
monolithic scalar and 26-tick FNV implementation, not a hardware prediction.
The first shard must reproduce the original signed 16-image scalar oracle.
All output files are new, absolute and outside the repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import p08_b2_4_scalar_first16 as baseline
import p08_b3_pilot16_admission as pin
from p08_b2_stage_1024_ingress import (
    MANIFEST_FILENAME,RAW_FILENAME,HASH_FILENAME,
    wire_from_pinned_route_bytes,pinned_route_payload
)

SCHEMA="p08-b4-1-original-b24-1024-scalar-shard-v1"
COUNT=1024
SHARD_SIZE=16
SHARDS=64
ROOT=baseline.ROOT

class ShardNoGo(ValueError): pass

def check(ok:bool,msg:str)->None:
    if not ok: raise ShardNoGo("NO-GO: "+msg)

def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()

def read_regular(p:Path)->bytes:
    check(p.is_file() and not p.is_symlink(),"missing/symlinked source "+str(p))
    return p.read_bytes()

def load_original_ingress(ingress:Path,raw:bytes,matched_rows:list[dict]):
    mraw=read_regular(ingress/MANIFEST_FILENAME)
    check(sha(mraw)==baseline.B2_MANIFEST_SHA,"original 1024 ingress manifest SHA drift")
    meta=json.loads(mraw)
    check(meta.get("schema")=="p08-b2-1-original27-matched1024-train-only-ingress-v1" and
          meta.get("count")==COUNT and meta.get("frame_bytes")==123216 and
          meta.get("raw_pool_sha256")==baseline.RAW_POOL_SHA and
          meta.get("original_OFFICIAL_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "original B2.1 full 1024 ingress identity mismatch")
    check(read_regular(ingress/RAW_FILENAME)==raw and
          sha(raw)==baseline.RAW_POOL_SHA,"original matched 1024 raw pool SHA drift")
    ledger=read_regular(ingress/HASH_FILENAME)
    check(sha(ledger)==baseline.B2_INGRESS_LEDGER_SHA,
          "original complete 1024 ingress encoded SHA ledger drift")
    hashes=ledger.decode("ascii").splitlines()
    frames=meta["frames"]
    check(len(hashes)==len(frames)==len(matched_rows)==COUNT,
          "original matched 1024 source length differs")
    for i in range(COUNT):
        row=frames[i];match=matched_rows[i]
        actual_raw=sha(raw[i*784:(i+1)*784])
        check(row.get("frame")==i and row.get("TRAIN_source_index")==
              match.get("TRAIN_source_index") and
              row.get("raw_pixels_sha256")==actual_raw==
              match.get("raw_pixels_sha256") and
              row.get("B24_27core_B13_ingress_sha256")==hashes[i] and
              row.get("encoded_wire_bytes")==123216,
              f"ordinal {i}: source/route/identity drift")
    return frames,hashes

def calculate_shard(
        shard:int,frozen:Path,a_stage:Path,data_dir:Path,routes_dir:Path,
        ingress_dir:Path,first16_oracle:Path,out:Path)->dict:
    check(type(shard) is int and 0<=shard<SHARDS,
          "one of 64 original consecutive 16-image shard IDs required")
    check(out.is_absolute() and not out.exists() and not out.is_symlink()
          and out.parent.is_dir() and
          not out.resolve().is_relative_to(ROOT),
          "new external absolute JSON output required")
    check(sha(read_regular(first16_oracle))==pin.ORACLE_SHA,
          "original independently signed first16 scalar oracle SHA drift")
    old=pin.source_oracle(first16_oracle)
    if str(ROOT/"Loihi_Digital_Twin/v3/src") not in sys.path:
        sys.path.insert(0,str(ROOT/"Loihi_Digital_Twin/v3/src"))
    from loihi_twin_v2.compiler import NetworkSpec
    from loihi_twin_v2.p06_b12_partition import B12Result
    from loihi_twin_v2.p06_b14_monolithic import (
        pixel_schedule_independent,simulate_monolithic
    )
    from loihi_twin_v2.p06_b24_freeze import (
        PINNED_B23_SOURCE_SHA256,PINNED_B23_DEPLOYMENT_SHA256,
        PINNED_B23_FRAMES
    )

    baseline.frozen_check.admit_freeze(frozen)
    baseline.frozen_check.source_index(
        frozen,json.loads(read_regular(frozen/"frozen_manifest.json")))
    baseline.route_check.require_routes(routes_dir,frozen)
    matched=baseline.b1.generate_report(a_stage,data_dir,frozen)
    check(matched.get("B24_original_33_assets_verified") is True and
          len(matched.get("frames",[]))==COUNT and
          matched.get("original_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "original Track A frozen matched-source admission failed")
    network=NetworkSpec.from_json(
        read_regular(frozen/"network_source.json").decode("utf-8"))
    packed=B12Result.from_json(
        read_regular(frozen/"packed_deployment.json").decode("utf-8"))
    check(network.fingerprint==PINNED_B23_SOURCE_SHA256 and
          packed.compiled.fingerprint==PINNED_B23_DEPLOYMENT_SHA256 and
          packed.compiled.source_fingerprint==network.fingerprint,
          "original frozen scalar/checkpoint identity changed")
    route=baseline.b2.pinned_route_payload(
        routes_dir/baseline.b2.ROUTE_FILENAME,packed)
    raw=baseline.b1.read_regular(
        a_stage,baseline.b1.STAGE_FILES["pixels"])
    check(len(raw)==COUNT*784,"original Track A raw source length drift")
    rows,ledger=load_original_ingress(
        ingress_dir,raw,matched["frames"])
    start=shard*SHARD_SIZE
    frames=[]
    witness=json.loads(read_regular(
        frozen/baseline.FROZEN_ORIGINAL_B23))["validation_frames"]
    check(len(witness)==3,"original three B2.3 frozen scalar witnesses missing")
    for ordinal in range(start,start+SHARD_SIZE):
        source=rows[ordinal]
        pixels=raw[ordinal*784:(ordinal+1)*784]
        check(sha(wire_from_pinned_route_bytes(route,pixels))==ledger[ordinal],
              f"original B1.3 encoded ingress mismatch at {ordinal}")
        schedule=pixel_schedule_independent(pixels)
        scalar=simulate_monolithic(network,{"pixels":schedule},
                                   readout_population="readout")
        ref=baseline.pure_reference(
            scalar,schedule,packed.compiled,packed.compiled.placement)
        if ordinal<3:
            w=witness[ordinal]
            check((
                w["validation_ordinal"],w["canonical_train_idx"],
                w["image_sha256"],w["monolithic_trace_sha256"],
                w["partitioned_trace_sha256"])==PINNED_B23_FRAMES[ordinal],
                "original frozen B2.3 witness identity drift")
            check(
                w["canonical_train_idx"]==source["TRAIN_source_index"] and
                w["image_sha256"]==source["raw_pixels_sha256"] and
                w["monolithic_trace_sha256"]==ref["original_scalar_trace_sha256"] and
                w["predicted_class"]==ref["expected_prediction"] and
                w["readout_spike_counts"]==ref["expected_output_spike_counts"],
                "original first-three scalar witness numerical drift")
        item={
            "ordinal":ordinal,
            "TRAIN_source_index":source["TRAIN_source_index"],
            "raw_pixels_sha256":source["raw_pixels_sha256"],
            "original_27core_ingress_sha256":source["B24_27core_B13_ingress_sha256"],
            **ref
        }
        if ordinal<16:
            # Critical: independently reproduce every field of the
            # original physically accepted first16 numerical reference.
            check(item==old["frames"][ordinal],
                  f"accepted first16 scalar evidence differs at frame {ordinal}")
        frames.append(item)
    result={
        "schema":SCHEMA,"shard":shard,
        "start_ordinal":start,
        "end_ordinal_exclusive":start+SHARD_SIZE,
        "count":SHARD_SIZE,
        "dataset_count":COUNT,
        "original_first16_scalar_sha256":pin.ORACLE_SHA,
        "original_raw1024_sha256":baseline.RAW_POOL_SHA,
        "original_1024_ingress_manifest_sha256":baseline.B2_MANIFEST_SHA,
        "original_1024_wire_SHA_ledger_sha256":baseline.B2_INGRESS_LEDGER_SHA,
        "original_27core_p02_sha256":
            "3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e",
        "original_b24_source_sha256":PINNED_B23_SOURCE_SHA256,
        "original_b24_compiled_sha256":PINNED_B23_DEPLOYMENT_SHA256,
        "original_full1024_A53_ELF_expected_sha256":baseline.B23_ELF_SHA,
        "original_full1024_A53_map_expected_sha256":baseline.B23_MAP_SHA,
        "frames":frames,
        "independent_KV260_physical_execution":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,indent=2,sort_keys=True)
        fp.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shard",required=True,type=int)
    for name in ("frozen-dir","a-stage","train-data-dir","routes-dir",
                 "ingress-dir","first16-oracle","out"):
        p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    try:
        result=calculate_shard(
            args.shard,args.frozen_dir,args.a_stage,args.train_data_dir,
            args.routes_dir,args.ingress_dir,args.first16_oracle,args.out)
        print("P08_B4_1_ORIGINAL_SCALAR_SHARD_INDEPENDENT_PASS=1")
        print("P08_B4_1_SHARD="+str(result["shard"]))
        print("P08_B4_1_VERIFIED_ORDINAL_RANGE="+
              str(result["start_ordinal"])+":"+
              str(result["end_ordinal_exclusive"]))
        print("P08_B4_1_ACTUAL_FULL1024_PHYSICAL_TEST_EXECUTED=0")
        print("P08_B4_1_SHARD_REPORT="+str(args.out))
        return 0
    except (ShardNoGo,baseline.OracleNoGo,ValueError,TypeError,
            OSError,KeyError,AssertionError) as e:
        print("P08_B4_1_SCALAR_SHARD_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
