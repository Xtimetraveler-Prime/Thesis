#!/usr/bin/env python3
"""B4m host-only ORIGINAL frozen B2.4 route tables and TRAIN witness ingress.

Produces entirely NEW out-of-repo fixed-address staging images; never edits
frozen P02 images, former B4l acceptance, TRAIN IDX or official TEST.
Requires canonical original TRAIN-only validation split (no TEST IDX paths).
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

V3=Path(__file__).resolve().parents[1]
OUT_BASE=0x43FC4000
OUT_BYTES=0x14000
IN_BASE=0x41000000
IN_BYTES=0xE0000
FRAME_BASE=0x41100000
FRAME_LIMIT=0xE0000
CORE_COUNT=27
OUT_LIMIT=10000
MAX_INGRESS_ROUTES=784*126
HEADER=128
COMPARTMENT_BYTES=64
EXPECTED_COMPARTMENTS=1010
OUT_FILENAME="p07_b4m_original_output_routes_80k.bin"
IN_FILENAME="p07_b4m_original_input_routes_896k.bin"
PINNED_SHA="02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a"
CAP_SHA="82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498"
FRAME_SHA={
  0:"5978f00e0f60c14e1ee17ea73f08f071516de8d0eb89b0e7cab1753d53d7fcd3",
  1:"3e3c39ef3319fb9dc08c3661f3a9a9575d131db7946ab90f95f457d9189429c3",
  2:"ecba50a209e6d07d7d12d2121a2931330e9085054e63831d38242c10300930c1",
}
FRAME_IDX={0:37384,1:27347,2:20178}

class FrozenRouteError(ValueError):
    pass

def sha(payload:bytes)->str:
    return hashlib.sha256(payload).hexdigest()

def pack_tables(rows:list[dict],ingress_routes:list[tuple[int,int,int]],
                output_routes:list[tuple[int,int,int,int]])->tuple[bytes,bytes]:
    """Pure bounded packing function, separately testable with synthetic rows."""
    if len(rows)!=CORE_COUNT or sum(x["compartments"] for x in rows)!=EXPECTED_COMPARTMENTS:
        raise FrozenRouteError("NO-GO: source must contain original 1010 compartments")
    if not 784<=len(ingress_routes)<=MAX_INGRESS_ROUTES:
        raise FrozenRouteError("NO-GO: original full 784 pixel ingress is absent")
    if len(output_routes)>OUT_LIMIT:
        raise FrozenRouteError("NO-GO: actual frozen output route count exceeds existing 8192 buffer")
    bitmap=[]
    for i,row in enumerate(rows):
        if row["core_id"]!=i or row["compartments"]<=0 or row["compartments"]>1024:
            raise FrozenRouteError("NO-GO: original ordered core ID/size mismatch")
        bits=bytes.fromhex(row["bitmap_hex"])
        if len(bits)!=512 or sum(v.bit_count() for v in bits)!=row["axon_count"]:
            raise FrozenRouteError("NO-GO: original registered axon bitmap drift")
        bitmap.append(bits)
    if rows[26]["compartments"]!=10:
        raise FrozenRouteError("NO-GO: original readout must have 10 compartments")
    for i,(pixel,core,axon) in enumerate(ingress_routes):
        if not(0<=pixel<784 and 0<=core<27 and 0<=axon<4096):
            raise FrozenRouteError("NO-GO: invalid input route")
        if not(bitmap[core][axon>>3]&(1<<(axon&7))):
            raise FrozenRouteError("NO-GO: external route axon not registered")
        if i and (pixel,core)<=(ingress_routes[i-1][0],ingress_routes[i-1][1]):
            raise FrozenRouteError("NO-GO: external route order/unique destination per pixel")
    if {x[0] for x in ingress_routes}!=set(range(784)):
        raise FrozenRouteError("NO-GO: every source pixel must be explicitly routed")
    for i,(core,neuron,dest,axon) in enumerate(output_routes):
        if not(0<=core<27 and 0<=dest<27 and
               0<=neuron<rows[core]["compartments"] and 0<=axon<4096):
            raise FrozenRouteError("NO-GO: invalid original output route geometry")
        if not(bitmap[dest][axon>>3]&(1<<(axon&7))):
            raise FrozenRouteError("NO-GO: output route axon not registered in destination")
        if i and (core,neuron,dest,axon)<=output_routes[i-1]:
            raise FrozenRouteError("NO-GO: output route order or duplicate")
    def header(magic:bytes,size:int,count:int,entry:int,raw:bytearray)->None:
        struct.pack_into("<8s6I",raw,0,magic,1,size,CORE_COUNT,count,entry,HEADER)
        raw[32:64]=bytes.fromhex(PINNED_SHA)
        raw[64:96]=bytes.fromhex(CAP_SHA)
    outs=bytearray(OUT_BYTES)
    header(b"B4MROUT1",OUT_BYTES,len(output_routes),8,outs)
    for i,row in enumerate(rows):
        struct.pack_into("<H",outs,HEADER+i*2,row["compartments"])
    for i,route in enumerate(output_routes):
        struct.pack_into("<4H",outs,HEADER+COMPARTMENT_BYTES+i*8,*route)
    outs[96:128]=hashlib.sha256(outs[HEADER:]).digest()
    ins=bytearray(IN_BYTES)
    header(b"B4MING01",IN_BYTES,len(ingress_routes),6,ins)
    for i,route in enumerate(ingress_routes):
        struct.pack_into("<3H",ins,HEADER+i*6,*route)
    ins[96:128]=hashlib.sha256(ins[HEADER:]).digest()
    return bytes(outs),bytes(ins)

def build_original(frozen:Path,data_dir:Path,out:Path)->dict:
    if out.exists() or out.is_symlink() or not out.is_absolute() or not out.parent.is_dir():
        raise FrozenRouteError("NO-GO: NEW absolute staging dir required")
    if out.resolve().is_relative_to(V3.parents[1].resolve()) or (
        frozen.resolve().is_relative_to(out.resolve()) or
        out.resolve().is_relative_to(frozen.resolve())):
        raise FrozenRouteError("NO-GO: staging must be OUTSIDE original thesis/freeze")
    sys.path.insert(0,str(V3/"src"))
    from loihi_twin_v2.p06_b12_partition import B12Result
    from loihi_twin_v2.p06_a3_data import load_train_validation
    from loihi_twin_v2.p06_b22_training import require_pinned_train_validation
    from loihi_twin_v2.p06_b13_streaming import (
        _ingress_routes,encode_ingress_frame,decode_ingress_frame
    )
    import p07_b4l1_stage_frozen_27core as b1
    import p07_b4l_frozen_bindings as bind
    b1.admit_freeze(frozen)
    rows=bind.original_core_bindings(frozen)
    packed=(frozen/"packed_deployment.json")
    if packed.is_symlink() or not packed.is_file():
        raise FrozenRouteError("NO-GO: original compiled B2.4 file missing")
    b12=B12Result.from_json(packed.read_text(encoding="utf-8"))
    if b12.compiled.fingerprint!=PINNED_SHA or (
        b12.capacity_audit.get("audit_sha256")!=CAP_SHA):
        raise FrozenRouteError("NO-GO: original B2.4 routing SHA mismatches")
    ingress_routes=list(_ingress_routes(b12))
    outputs=sorted((cfg.core_id,desc.source_compartment,
                    dst.destination_core,dst.destination_axon)
                   for cfg in b12.compiled.logical_deployment.core_configs
                   for desc in cfg.output_routes for dst in desc.routes)
    out_bytes,in_bytes=pack_tables(rows,ingress_routes,outputs)
    split=load_train_validation(data_dir,strict=True)
    require_pinned_train_validation(split)
    frames={}
    for ordinal,expected in FRAME_SHA.items():
        idx=split.validation_indices[ordinal]
        if idx!=FRAME_IDX[ordinal]:
            raise FrozenRouteError("NO-GO: deterministic original TRAIN validation ordinal changed")
        image=split.images[idx*784:(idx+1)*784]
        if len(image)!=784 or sha(image)!=expected:
            raise FrozenRouteError("NO-GO: B2.3 accepted validation raw image digest drift")
        wire=encode_ingress_frame(b12,image)
        decode_ingress_frame(wire,b12)
        if len(wire)>FRAME_LIMIT:
            raise FrozenRouteError("NO-GO: frame exceeds physical reserved ingress span")
        frames[ordinal]=wire
    # Only after ALL bytes, train ordinals, SHA and bounds are verified
    # does any physical staging output file get created.
    out.mkdir(mode=0o700,exist_ok=False)
    (out/OUT_FILENAME).write_bytes(out_bytes)
    (out/IN_FILENAME).write_bytes(in_bytes)
    manifests={
        "schema":"p07-b4m-original-B24-physical-route-and-TRAIN-witness-v1",
        "official_MNIST_TEST":"SEALED",
        "original_compiled_sha256":PINNED_SHA,
        "original_capacity_sha256":CAP_SHA,
        "output_route_count":len(outputs),"input_route_count":len(ingress_routes),
        "compartment_count":sum(x["compartments"] for x in rows),
        "spans":{
            "output_routes":[hex(OUT_BASE),hex(OUT_BASE+OUT_BYTES)],
            "input_routes":[hex(IN_BASE),hex(IN_BASE+IN_BYTES)],
            "per_image_ingress":[hex(FRAME_BASE),hex(FRAME_BASE+FRAME_LIMIT)],
        },
        "files":{
            OUT_FILENAME:sha(out_bytes),
            IN_FILENAME:sha(in_bytes),
        },
        "frames":{},
        "hardware_executed":False,
        "frozen_snapshot_modified":False,
    }
    for ordinal,wire in frames.items():
        filename=f"p07_b4m_original_TRAIN_validation_{ordinal}_ingress.bin"
        (out/filename).write_bytes(wire)
        manifests["files"][filename]=sha(wire)
        manifests["frames"][str(ordinal)]={
            "original_TRAIN_idx":FRAME_IDX[ordinal],
            "raw_image_sha256":FRAME_SHA[ordinal],
            "ingress_sha256":sha(wire),
            "bytes":len(wire),
        }
    (out/"p07_b4m_frozen_inputs_manifest.json").write_text(
        json.dumps(manifests,sort_keys=True,indent=2)+"\n")
    return manifests

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-dir",type=Path,required=True)
    p.add_argument("--train-data-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:
        result=build_original(args.frozen_dir,args.train_data_dir,args.out)
        print("P07_B4M_ORIGINAL_B24_ROUTING_TRAIN_FRAMES_HOST_PREPARED=1")
        print(f"P07_B4M_INPUT_ROUTES={result['input_route_count']}")
        print(f"P07_B4M_OUTPUT_ROUTES={result['output_route_count']}")
        print("P07_B4M_REAL_KV260_INFERENCE_VERIFIED=0")
    except (ValueError,KeyError,AssertionError,TypeError,OSError) as exc:
        print("P07_B4M_NO_GO="+str(exc),file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
