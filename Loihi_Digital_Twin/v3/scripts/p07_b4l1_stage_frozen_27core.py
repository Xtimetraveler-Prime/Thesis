#!/usr/bin/env python3
"""P07-B.4l1 PC-ONLY: stage the EXACT accepted B2.4 27xP02 DDR records.

Refuses unverified, non-canonical, substituted and incomplete freeze assets.
Reuses the actual P06 B2.4 33-file/P02 ABI verifier unchanged. Packages the
original bytes into an immutable-plan binary+JSON in a NEW out-of-repo directory.
No torch or training is needed during bundle copying; the original B2.4
verifier may import project training dependencies. No FPGA, JTAG, Linux or
official MNIST TEST access, and no claim of physical 27-core inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

V3=Path(__file__).resolve().parents[1]
REPO=V3.parents[1]
FROZEN_SHA="d71e2827a81ab1f00ef1e89446540ac04b7d7b34d89b30d46cd6e4ff013c7a63"
FROZEN_CANONICAL_SHA="d01ccd2d5a85b22f81580cd7800933642e19d1a43e8a2f38eac1f6c4d83cab90"
SOURCE_NETWORK_SHA="0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a"
DEPLOYMENT_SHA="02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a"
CAPACITY_SHA="82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498"
RECORDS=27
STRIDE=0x80000
DDR_BASE=0x40000000
DDR_END=DDR_BASE+RECORDS*STRIDE
SLOTS=3
TOTAL_BYTES=RECORDS*STRIDE
BUNDLE_NAME="p07_b4l1_original_27_p02_ddr.bin"
INDEX_NAME="p07_b4l1_staging_index.json"
FREEZE_REL="frozen_manifest.json"
SCHEMA="p07-b4l1-original-b24-static-p02-ddr-stage-v1"


class StageError(ValueError):
    pass


def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha(obj:dict)->str:
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,separators=(",",":"),ensure_ascii=True
    ).encode("utf-8")).hexdigest()


def path_guard(frozen:Path,out:Path,prepare:bool)->None:
    if not frozen.is_dir() or frozen.is_symlink():
        raise StageError("NO-GO: frozen B2.4 directory missing or symlinked")
    if not out.is_absolute() or out.is_symlink() or out.resolve()==frozen.resolve():
        raise StageError("NO-GO: output must be independent absolute directory")
    if out.resolve().is_relative_to(REPO.resolve()):
        raise StageError("NO-GO: stage output must be outside Thesis repository")
    if frozen.resolve().is_relative_to(out.resolve()) or out.resolve().is_relative_to(frozen.resolve()):
        raise StageError("NO-GO: stage output must not contain or be inside frozen source")
    if prepare and (out.exists() or not out.parent.is_dir()):
        raise StageError("NO-GO: output must be new and its parent must exist")
    if not prepare and (not out.is_dir() or out.is_symlink()):
        raise StageError("NO-GO: existing stage directory required")


def record_filename(core:int)->str:
    if type(core) is not int or not 0<=core<RECORDS:
        raise StageError("NO-GO: illegal logical-core ID")
    return f"initial_ddr/core_{core:03d}_initial_p02_512k.bin"


def admit_freeze(frozen:Path)->dict:
    """Real source-of-truth full 33-asset verifier, never stubbed on user PC."""
    from loihi_twin_v2.p06_b24_freeze import verify_frozen_directory
    frozen_manifest=frozen/FREEZE_REL
    if not frozen_manifest.is_file() or frozen_manifest.is_symlink():
        raise StageError("NO-GO: frozen original manifest absent/symlinked")
    if file_sha(frozen_manifest)!=FROZEN_SHA:
        raise StageError("NO-GO: frozen original pretty-printed manifest SHA mismatch")
    obj=json.loads(frozen_manifest.read_text(encoding="utf-8"))
    if (obj.get("manifest_sha256")!=FROZEN_CANONICAL_SHA
            or obj.get("source_network_sha256")!=SOURCE_NETWORK_SHA
            or obj.get("deployment_sha256")!=DEPLOYMENT_SHA
            or obj.get("capacity_audit_sha256")!=CAPACITY_SHA
            or obj.get("core_count")!=RECORDS or obj.get("backing_bytes")!=TOTAL_BYTES):
        raise StageError("NO-GO: original accepted B2.4 identity mismatch")
    verified=verify_frozen_directory(frozen,deep=False)
    if (verified.get("files_checked")!=33
            or verified.get("cores_checked")!=RECORDS
            or verified.get("total_initial_ddr_bytes")!=TOTAL_BYTES
            or verified.get("official_mnist_test_status")!="SEALED_NOT_ACCESSED"
            or verified.get("manifest_sha256")!=FROZEN_CANONICAL_SHA):
        raise StageError("NO-GO: complete original B2.4 freeze integrity failed")
    if len(obj.get("ddr_context_sha256",[]))!=RECORDS:
        raise StageError("NO-GO: frozen per-core SHA list incomplete")
    return obj


def source_index(frozen:Path,obj:dict)->list[dict]:
    """Only the original SHA-authenticated P02 images, canonical core order."""
    by_path={e["path"]:e for e in obj["assets"]}
    rows=[]
    seen=set()
    for core in range(RECORDS):
        rel=record_filename(core)
        entry=by_path.get(rel)
        if (not isinstance(entry,dict) or rel in seen
                or entry.get("bytes")!=STRIDE
                or entry.get("sha256")!=obj["ddr_context_sha256"][core]):
            raise StageError(f"NO-GO: core {core} original asset mismatch")
        seen.add(rel)
        f=frozen/rel
        if f.is_symlink() or not f.is_file() or f.stat().st_size!=STRIDE:
            raise StageError(f"NO-GO: core {core} missing or symlinked")
        sha=file_sha(f)
        if sha!=entry["sha256"]:
            raise StageError(f"NO-GO: core {core} frozen record SHA mismatch")
        rows.append({
            "logical_core_id":core,
            "source_relative_path":rel,
            "byte_offset":core*STRIDE,
            "physical_address":f"0x{DDR_BASE+core*STRIDE:08X}",
            "bytes":STRIDE,
            "sha256":sha,
        })
    return rows


def expected_manifest(rows:list[dict],image_sha:str)->dict:
    obj={
        "schema":SCHEMA,
        "operation":"HOST_ONLY_ORIGINAL_FROZEN_CONTEXT_STAGING",
        "source_manifest_file_sha256":FROZEN_SHA,
        "source_manifest_canonical_sha256":FROZEN_CANONICAL_SHA,
        "original_network_sha256":SOURCE_NETWORK_SHA,
        "original_deployment_sha256":DEPLOYMENT_SHA,
        "original_capacity_audit_sha256":CAPACITY_SHA,
        "bundle_file":BUNDLE_NAME,
        "bundle_sha256":image_sha,
        "physical_base":f"0x{DDR_BASE:08X}",
        "physical_end_exclusive":f"0x{DDR_END:08X}",
        "bytes":TOTAL_BYTES,
        "record_stride_bytes":STRIDE,
        "logical_core_count":RECORDS,
        "resident_slot_count":SLOTS,
        "physical_engine_count":1,
        "records":rows,
        "official_mnist_test":"SEALED_NOT_ACCESSED",
        "physical_ddr_staged":False,
        "physical_inference_executed":False,
        "physical_a53_elf_executed":False,
    }
    obj["index_sha256"]=canonical_sha(obj)
    return obj


def prepare(frozen:Path,out:Path)->dict:
    path_guard(frozen,out,True)
    freeze=admit_freeze(frozen)
    rows=source_index(frozen,freeze)
    temp=Path(tempfile.mkdtemp(prefix=".p07_b4l1_",dir=out.parent))
    try:
        bundle=temp/BUNDLE_NAME
        h=hashlib.sha256()
        with bundle.open("xb") as dst:
            for row in rows:
                raw=(frozen/row["source_relative_path"]).read_bytes()
                if len(raw)!=STRIDE or hashlib.sha256(raw).hexdigest()!=row["sha256"]:
                    raise StageError("NO-GO: source changed during staging")
                dst.write(raw)
                h.update(raw)
            dst.flush()
            os.fsync(dst.fileno())
        if bundle.stat().st_size!=TOTAL_BYTES:
            raise StageError("NO-GO: 27-core bundle length incorrect")
        manifest=expected_manifest(rows,h.hexdigest())
        (temp/INDEX_NAME).write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        if out.exists():
            raise StageError("NO-GO: output appeared during staging")
        temp.rename(out)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return verify_bundle(frozen,out)


def verify_bundle(frozen:Path,out:Path)->dict:
    path_guard(frozen,out,False)
    freeze=admit_freeze(frozen)
    rows=source_index(frozen,freeze)
    if {p.name for p in out.iterdir()}!={BUNDLE_NAME,INDEX_NAME}:
        raise StageError("NO-GO: missing/extra output staging artifact")
    path=out/BUNDLE_NAME
    index=out/INDEX_NAME
    if path.is_symlink() or index.is_symlink() or not path.is_file() or not index.is_file():
        raise StageError("NO-GO: output files must be regular non-symlinks")
    obj=json.loads(index.read_text(encoding="utf-8"))
    checksum=obj.get("index_sha256")
    if checksum!=canonical_sha({k:v for k,v in obj.items() if k!="index_sha256"}):
        raise StageError("NO-GO: staging index self-hash mismatch")
    if path.stat().st_size!=TOTAL_BYTES:
        raise StageError("NO-GO: staged 27-core image size mismatch")
    complete=file_sha(path)
    if obj!=expected_manifest(rows,complete):
        raise StageError("NO-GO: staged record addresses, content identity or metadata mismatch")
    with path.open("rb") as stream:
        for row in rows:
            raw=stream.read(STRIDE)
            if (len(raw)!=STRIDE or hashlib.sha256(raw).hexdigest()!=row["sha256"]
                    or raw!=(frozen/row["source_relative_path"]).read_bytes()):
                raise StageError("NO-GO: staged record differs byte-for-byte from frozen source")
        if stream.read(1):
            raise StageError("NO-GO: trailing bytes in staged bundle")
    return {
        "bundle_sha256":complete,"core_count":RECORDS,
        "bytes":TOTAL_BYTES,"physical_start":f"0x{DDR_BASE:08X}",
        "physical_end_exclusive":f"0x{DDR_END:08X}",
        "freeze_untouched":True,
        "board_visited":False,
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",required=True,choices=("prepare","verify"))
    parser.add_argument("--frozen-dir",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    try:
        report=(prepare(args.frozen_dir,args.output_dir) if args.mode=="prepare"
                else verify_bundle(args.frozen_dir,args.output_dir))
    except (StageError,ValueError,OSError,KeyError,TypeError) as exc:
        print("P07_B4L1_HOST_STAGING_NO_GO="+str(exc),file=sys.stderr)
        return 3
    print(json.dumps(report,sort_keys=True,indent=2))
    print("P07_B4L1_ALL_27_ORIGINAL_P02_RECORDS_BYTE_EXACT_PASS=1")
    print("P07_B4L1_FROZEN_B2_4_SOURCE_UNMODIFIED=1")
    print("P07_B4L1_PHYSICAL_DDR_STAGED=0")
    print("P07_B4L1_TRAINED_INFERENCE_EXECUTED=0")
    print("P07_B4L1_OFFICIAL_MNIST_TEST=SEALED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
