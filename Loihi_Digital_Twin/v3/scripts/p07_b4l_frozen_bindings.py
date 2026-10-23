#!/usr/bin/env python3
"""B4l: emit original B2.4-derived core metadata + legal-axon 16KiB image.

Host ONLY: never opens official TEST, writes P02 freeze or contacts board.
Same frozen identity as physically accepted 27-core DDR bundle. This is
intentionally NOT an inferred/guessed 27-core model graph.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import p07_b4l1_stage_frozen_27core as b1
import p07_b4l_physical_model_deploy as deploy

MAGIC=b"B4BIND01"
SIZE=0x4000
HEADER=128
ENTRIES=27
STRIDE=528
BASE=0x43FC0000
TABLE_BYTES=ENTRIES*STRIDE
FILENAME="p07_b4l_frozen_27core_bindings_16k.bin"
INDEXNAME="p07_b4l_frozen_27core_bindings.json"
SCHEMA="p07-b4l-original-b24-frozen-27core-registrations-v1"


class BindingError(ValueError):
    pass


def canonical_sha(x:dict)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def original_core_bindings(frozen:Path)->list[dict]:
    """Parse the actual accepted B1.2 graph, cross-check every P02 axon."""
    # The original B2.4 verifier and accepted materialized packer are used,
    # not synthetic native fixtures nor a newly reconstructed trained graph.
    src=b1.V3/"src"
    if str(src) not in sys.path:
        sys.path.insert(0,str(src))
    from loihi_twin_v2.p06_b12_partition import B12Result
    from loihi_twin_v2.hardware_p03 import export_one_core_image
    source=frozen/"packed_deployment.json"
    if source.is_symlink() or not source.is_file():
        raise BindingError("NO-GO: canonical frozen packed deployment missing")
    compilation=B12Result.from_json(source.read_text(encoding="utf-8"))
    if (compilation.compiled.fingerprint!=b1.DEPLOYMENT_SHA
            or compilation.compiled.source_fingerprint!=b1.SOURCE_NETWORK_SHA
            or compilation.capacity_audit.get("audit_sha256")!=b1.CAPACITY_SHA):
        raise BindingError("NO-GO: accepted B2.4 graph digest mismatch")
    configs=compilation.compiled.logical_deployment.core_configs
    if len(configs)!=27 or [cfg.core_id for cfg in configs]!=list(range(27)):
        raise BindingError("NO-GO: original ordered 27 core configs missing")
    rows=[]
    for cfg in configs:
        cid=cfg.core_id
        count=len(cfg.compartments)
        if not 1<=count<=1024:
            raise BindingError("NO-GO: invalid source core compartment count")
        axons=[b.axon_id for b in cfg.input_axons]
        if len(set(axons))!=len(axons) or any(type(x)!=int or not 0<=x<4096 for x in axons):
            raise BindingError("NO-GO: invalid frozen accepted input axons")
        original=(frozen/b1.record_filename(cid)).read_bytes()
        if len(original)!=b1.STRIDE:
            raise BindingError("NO-GO: altered frozen P02 size")
        header=struct.unpack_from("<8s12I",original)
        if (header[0]!=b"LTV3CTX1" or header[1]!=1
                or header[2]!=0x1000 or header[3]!=b1.STRIDE or header[4]!=cid
                or header[7]!=count or header[10]!=0
                or header[11]!=0 or header[12]!=0):
            raise BindingError("NO-GO: frozen P02 header/size/core/count/empty banks drift")
        image=export_one_core_image(cfg)
        expected={w.index:w.word for w in image.axon_words}
        if set(expected)!=set(axons):
            raise BindingError("NO-GO: packed P03 axon address mismatch")
        for axon in axons:
            value=struct.unpack_from("<Q",original,0x7000+axon*8)[0]
            if value!=expected[axon]:
                raise BindingError(f"NO-GO: P02 original core {cid} axon {axon} image drift")
        bitmap=bytearray(512)
        for x in axons:
            bitmap[x//8] |= 1<<(x%8)
        rows.append({
            "core_id":cid,
            "compartments":count,
            "metadata":cid | (count<<7),
            "axon_count":len(axons),
            "bitmap_hex":bytes(bitmap).hex(),
        })
    return rows


def build_payload(rows:list[dict])->bytes:
    if len(rows)!=ENTRIES:
        raise BindingError("NO-GO: exactly 27 source-bound core registrations required")
    table=bytearray(TABLE_BYTES)
    for i,row in enumerate(rows):
        if row["core_id"]!=i or not 1<=row["compartments"]<=1024:
            raise BindingError("NO-GO: registered core order/count mismatch")
        if row["metadata"]!=i|(row["compartments"]<<7):
            raise BindingError("NO-GO: registered P03 metadata does not match compartments")
        bitmap=bytes.fromhex(row["bitmap_hex"])
        if len(bitmap)!=512 or sum(x.bit_count() for x in bitmap)!=row["axon_count"]:
            raise BindingError("NO-GO: input axon bitmap inconsistent with frozen count")
        struct.pack_into("<QHHI",table,i*STRIDE,
                         row["metadata"],row["compartments"],row["axon_count"],i)
        table[i*STRIDE+16:(i+1)*STRIDE]=bitmap
    output=bytearray(SIZE)
    struct.pack_into("<8s6I",output,0,
        MAGIC,1,SIZE,ENTRIES,STRIDE,HEADER,TABLE_BYTES)
    output[32:64]=bytes.fromhex(deploy.ACCEPTED_BUNDLE_SHA)
    output[64:96]=bytes.fromhex(b1.DEPLOYMENT_SHA)
    output[96:128]=hashlib.sha256(table).digest()
    output[HEADER:HEADER+TABLE_BYTES]=table
    return bytes(output)


def verify_payload(data:bytes, rows:list[dict])->dict:
    if len(data)!=SIZE:
        raise BindingError("NO-GO: full 16KiB original metadata descriptor required")
    if data!=build_payload(rows):
        raise BindingError("NO-GO: frozen core/bitmap/header/padding or SHA identity mismatch")
    return {"schema":SCHEMA,
        "binary_sha256":hashlib.sha256(data).hexdigest(),
        "accepted_27core_bundle_sha256":deploy.ACCEPTED_BUNDLE_SHA,
        "frozen_b12_compilation_sha256":b1.DEPLOYMENT_SHA,
        "core_count":ENTRIES,"record_bytes":STRIDE,
        "bytes":SIZE,"physical_staging_address":f"0x{BASE:08X}",
        "physical_staging_end_exclusive":f"0x{BASE+SIZE:08X}",
        "registered_axons_total":sum(x["axon_count"] for x in rows),
        "official_test":"SEALED_NOT_ACCESSED","hardware_dispatched":False}


def check_paths(out:Path,frozen:Path,stage:Path,creating:bool):
    if (not out.is_absolute() or out.is_symlink() or
            out.resolve().is_relative_to(b1.REPO.resolve()) or
            out.resolve().is_relative_to(frozen.resolve()) or
            out.resolve().is_relative_to(stage.resolve()) or
            frozen.resolve().is_relative_to(out.resolve())):
        raise BindingError("NO-GO: unique independent absolute output outside source and repository")
    if creating and (out.exists() or not out.parent.is_dir()):
        raise BindingError("NO-GO: new evidence output required")
    if not creating and (not out.is_dir() or out.is_symlink()):
        raise BindingError("NO-GO: existing regular evidence directory required")


def stage(frozen:Path,source_stage:Path,out:Path,mode:str)->dict:
    deploy.prepare_verified_contexts(frozen,source_stage)
    check_paths(out,frozen,source_stage,mode=="prepare")
    rows=original_core_bindings(frozen)
    packed=build_payload(rows)
    if mode=="prepare":
        out.mkdir(mode=0o700,exist_ok=False)
        (out/FILENAME).write_bytes(packed)
        receipt=verify_payload(packed,rows)
        receipt["index_sha256"]=canonical_sha(receipt)
        (out/INDEXNAME).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    if {x.name for x in out.iterdir()}!={FILENAME,INDEXNAME}:
        raise BindingError("NO-GO: missing/extra bindings output files")
    binary=out/FILENAME
    index=out/INDEXNAME
    if binary.is_symlink() or index.is_symlink() or not binary.is_file() or not index.is_file():
        raise BindingError("NO-GO: symlink/non-regular descriptor")
    receipt=verify_payload(binary.read_bytes(),rows)
    expect=dict(receipt)
    expect["index_sha256"]=canonical_sha(expect)
    actual=json.loads(index.read_text())
    if actual!=expect:
        raise BindingError("NO-GO: binding descriptor independent index mismatch")
    return receipt


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("prepare","verify"),required=True)
    p.add_argument("--frozen-dir",type=Path,required=True)
    p.add_argument("--staged-dir",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        receipt=stage(a.frozen_dir,a.staged_dir,a.output_dir,a.mode)
    except (BindingError,b1.StageError,ValueError,KeyError,OSError,TypeError) as e:
        print("P07_B4L_FROZEN_BINDINGS_NO_GO="+str(e),file=sys.stderr)
        return 3
    print(json.dumps(receipt,indent=2,sort_keys=True))
    print("P07_B4L_REAL_B24_27CORE_METADATA_AND_AXONS_VERIFIED=1")
    print("P07_B4L_FROZEN_MODEL_UNMODIFIED=1")
    print("P07_B4L_PHYSICAL_SCHEDULER_DISPATCH_EXECUTED=0")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
