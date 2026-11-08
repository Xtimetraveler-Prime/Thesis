#!/usr/bin/env python3
"""P08-B4.1: offline-only merge/admit 64 independent original 16-row shards.

No hardware contact. Fail closed on a missing, duplicated, reordered,
changed or improperly sourced frame. A complete PC-only 1024 oracle is
NECESSARY, not sufficient, for later physical latency admission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import p08_b4_1_scalar_shard as shard
import p08_b3_pilot16_admission as first16
import p08_b2_4_scalar_first16 as baseline

SCHEMA="p08-b4-1-original-b24-full1024-independent-scalar-oracle-v1"
SHARD_PATTERN="p08_b4_1_scalar_shard_{:02d}.json"
FNV=re.compile(r"^0x[0-9A-F]{16}$")
SHA=re.compile(r"^[0-9a-f]{64}$")
NEURAL_FIELDS=(
    "expected_external_current","expected_source_spikes",
    "expected_captured_packets","expected_inserted_next",
    "expected_prediction","expected_all_26_ticks_1010_neuron_FNV64",
    "expected_output_spike_counts","expected_per_tick_neuron_FNV64",
    "original_scalar_trace_sha256",
)
class MergeNoGo(ValueError):pass

def check(ok:bool,msg:str)->None:
    if not ok:raise MergeNoGo("NO-GO: "+msg)

def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def load(p:Path)->bytes:
    check(p.is_file() and not p.is_symlink(),"source absent or symlinked "+str(p))
    return p.read_bytes()

def check_frame(row:dict,ordinal:int,source:dict,ledger_hash:str)->None:
    check(isinstance(row,dict) and row.get("ordinal")==ordinal and
          row.get("TRAIN_source_index")==source.get("TRAIN_source_index") and
          row.get("raw_pixels_sha256")==source.get("raw_pixels_sha256") and
          row.get("original_27core_ingress_sha256")==ledger_hash,
          f"frame {ordinal}: original source ID/raw/wire hash drift")
    check(all(type(row.get(k)) is int and
              0<=row[k]<=0xffffffff for k in (
                  "expected_prediction","expected_external_current",
                  "expected_source_spikes","expected_captured_packets",
                  "expected_inserted_next","expected_dispatches",
                  "expected_barriers","expected_trace_compartments_per_tick")),
          f"frame {ordinal}: missing unsigned scalar receipts")
    check(row["expected_prediction"]<=9 and
          row["expected_dispatches"]==702 and
          row["expected_barriers"]==26 and
          row["expected_trace_compartments_per_tick"]==1010,
          f"frame {ordinal}: invalid original 27core geometry")
    check(isinstance(row.get("expected_output_spike_counts"),list) and
          len(row["expected_output_spike_counts"])==10 and
          all(type(x) is int and 0<=x<=0xffffffff
              for x in row["expected_output_spike_counts"]),
          f"frame {ordinal}: 10 readout spike counts missing")
    check(isinstance(row.get("expected_per_tick_neuron_FNV64"),list) and
          len(row["expected_per_tick_neuron_FNV64"])==26 and
          all(isinstance(s,str) and FNV.fullmatch(s)
              for s in row["expected_per_tick_neuron_FNV64"]) and
          isinstance(row.get("expected_all_26_ticks_1010_neuron_FNV64"),str)
          and FNV.fullmatch(row["expected_all_26_ticks_1010_neuron_FNV64"]),
          f"frame {ordinal}: complete 26tick scalar fingerprints missing")
    check(isinstance(row.get("original_scalar_trace_sha256"),str) and
          SHA.fullmatch(row["original_scalar_trace_sha256"]),
          f"frame {ordinal}: monolithic original trace SHA absent")

def merge(shards:Path,ingress:Path,first16_oracle:Path,out:Path)->dict:
    check(out.is_absolute() and not out.exists() and not out.is_symlink()
          and out.parent.is_dir() and not out.resolve().is_relative_to(shard.ROOT),
          "new external absolute output JSON required")
    check(shards.is_absolute() and shards.is_dir() and not shards.is_symlink(),
          "64 original scalar shards external directory required")
    check(digest(load(first16_oracle))==first16.ORACLE_SHA,
          "original accepted first16 scalar SHA drift")
    accepted=first16.source_oracle(first16_oracle)
    manifest_bytes=load(ingress/shard.MANIFEST_FILENAME)
    check(digest(manifest_bytes)==baseline.B2_MANIFEST_SHA,
          "original B2.1 source manifest SHA drift")
    manifest=json.loads(manifest_bytes)
    check(manifest.get("schema")=="p08-b2-1-original27-matched1024-train-only-ingress-v1"
          and manifest.get("count")==1024
          and manifest.get("original_OFFICIAL_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "original 1024 TRACK A source manifest changed")
    pixels=load(ingress/shard.RAW_FILENAME)
    check(len(pixels)==1024*784 and digest(pixels)==baseline.RAW_POOL_SHA,
          "original 1024 raw source pool corrupted")
    hashes_raw=load(ingress/shard.HASH_FILENAME)
    check(digest(hashes_raw)==baseline.B2_INGRESS_LEDGER_SHA,
          "original 1024 B input wire SHA list changed")
    hashes=hashes_raw.decode("ascii").splitlines()
    sources=manifest["frames"]
    check(len(hashes)==len(sources)==1024,
          "original 1024 source count drift")
    for i,src in enumerate(sources):
        check(src.get("frame")==i and
              src.get("raw_pixels_sha256")==digest(pixels[i*784:(i+1)*784]) and
              src.get("B24_27core_B13_ingress_sha256")==hashes[i] and
              src.get("encoded_wire_bytes")==123216,
              f"original B2.1 ingress frame {i} corrupted")
    expected_names={SHARD_PATTERN.format(i) for i in range(64)}
    check({p.name for p in shards.iterdir()}==expected_names,
          "64 consecutive expected scalar shards required; extra/duplicate/missing")
    all_frames=[]
    proof={}
    expected={
        "schema":shard.SCHEMA,
        "dataset_count":1024,
        "count":16,
        "original_first16_scalar_sha256":first16.ORACLE_SHA,
        "original_raw1024_sha256":baseline.RAW_POOL_SHA,
        "original_1024_ingress_manifest_sha256":baseline.B2_MANIFEST_SHA,
        "original_1024_wire_SHA_ledger_sha256":baseline.B2_INGRESS_LEDGER_SHA,
        "original_27core_p02_sha256":
            "3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e",
        "original_full1024_A53_ELF_expected_sha256":baseline.B23_ELF_SHA,
        "original_full1024_A53_map_expected_sha256":baseline.B23_MAP_SHA,
        "independent_KV260_physical_execution":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    model_pin=None
    compiled_pin=None
    for s in range(64):
        name=SHARD_PATTERN.format(s)
        raw=load(shards/name)
        entry=json.loads(raw)
        check(all(entry.get(k)==v for k,v in expected.items()) and
              entry.get("shard")==s and entry.get("start_ordinal")==s*16
              and entry.get("end_ordinal_exclusive")==s*16+16 and
              len(entry.get("frames",[]))==16,
              "scalar shard provenance/ordinal drift: "+name)
        check(entry.get("original_b24_source_sha256")==
              "0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a" and
              entry.get("original_b24_compiled_sha256")==
              "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a",
              "original B2.4 model/checkpoint SHA drift")
        if s==0:
            model_pin=entry["original_b24_source_sha256"]
            compiled_pin=entry["original_b24_compiled_sha256"]
        check(entry["original_b24_source_sha256"]==model_pin and
              entry["original_b24_compiled_sha256"]==compiled_pin,
              "64 shards from inconsistent B2.4 original models")
        for j,row in enumerate(entry["frames"]):
            ordinal=s*16+j
            check_frame(row,ordinal,sources[ordinal],hashes[ordinal])
            if ordinal<16:
                check(row==accepted["frames"][ordinal],
                      "original accepted physical first16 independent scalar mismatch")
            all_frames.append(row)
        proof[name]=digest(raw)
    check(len(all_frames)==1024 and
          [frame["ordinal"] for frame in all_frames]==list(range(1024)),
          "full original 1024 ordinal ledger incomplete")
    frames_raw=json.dumps(all_frames,sort_keys=True,separators=(",",":")).encode("utf-8")
    result={
        "schema":SCHEMA,"count":1024,
        "shard_count":64,"shard_size":16,
        "source_validation_pool":"original P08-A matched TRAIN-only 1024",
        "original_first16_physically_verified_scalar_oracle_sha256":
            first16.ORACLE_SHA,
        "original_raw1024_sha256":baseline.RAW_POOL_SHA,
        "original_1024_ingress_manifest_sha256":baseline.B2_MANIFEST_SHA,
        "original_1024_wire_sha_ledger_sha256":baseline.B2_INGRESS_LEDGER_SHA,
        "original_B24_compiled_sha256":compiled_pin,
        "original_B24_source_sha256":model_pin,
        "original_1024_ELF_reference_sha256":baseline.B23_ELF_SHA,
        "original_1024_map_reference_sha256":baseline.B23_MAP_SHA,
        "source_shards_sha256":proof,
        "all_1024_scalar_frame_rows_sha256":digest(frames_raw),
        "frames":all_frames,
        "actual_KV260_1024_physical_execution":False,
        "physical_latency_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fd:
        json.dump(result,fd,sort_keys=True,indent=2)
        fd.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("shards-dir","ingress-dir","first16-oracle","out"):
        p.add_argument("--"+arg,required=True,type=Path)
    args=p.parse_args()
    try:
        result=merge(args.shards_dir,args.ingress_dir,
                     args.first16_oracle,args.out)
        print("P08_B4_1_ALL_1024_ORIGINAL_SCALAR_ROWS_ADMITTED=1")
        print("P08_B4_1_ALL_64_SHARDS_SHA_VERIFIED=1")
        print("P08_B4_1_ACCEPTED_FIRST16_SCALAR_REPRODUCED=1")
        print("P08_B4_1_PHYSICAL_1024_KV260_EXECUTED=0")
        print("P08_B4_1_FULL_SCALAR_ORACLE="+str(args.out))
        return 0
    except (MergeNoGo,ValueError,TypeError,OSError,KeyError,AssertionError) as e:
        print("P08_B4_1_1024_ORACLE_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
