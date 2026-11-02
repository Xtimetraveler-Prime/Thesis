#!/usr/bin/env python3
"""P08-B3 PILOT16 PC-ONLY ORIGINAL frozen DDR payload and transfer plan.

Creates immutable-reference COPIES only in a fresh external stage; never calls
xsdb, Vivado, JTAG, /dev/mem or a PL peripheral, and never asserts DDR owner.
Separate operator-approved hardware staging and independent readback required.
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

import p07_b4l1_stage_frozen_27core as core
import p07_b4l_frozen_bindings as binding
import p07_b4m_frozen_inputs as routed
import p07_b4m_offline_admission as prior_routes
import p08_b2_stage_1024_ingress as ingress
import p08_b3_pilot16_admission as pilot

SCHEMA="p08-b3-pilot16-pc-only-authentic-original-27core-ddr-plan-v1"
FILES=(
    ("original_27core_backup_source_14155776.bin","0x40000000", "0x40D80000"),
    ("original_27core_B4L_binding_16384.bin","0x43FC0000","0x43FC4000"),
    ("original_B4M_input_routes_917504.bin","0x41000000","0x410E0000"),
    ("original_B4M_output_routes_81920.bin","0x43FC4000","0x43FD8000"),
    ("matched_original_1024_raw_pixels_802816.bin","0x42100000","0x421C4000"),
)
EXPECTED_SHA={
    FILES[0][0]:"3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e",
    FILES[1][0]:"2f0a5299a3948d7e0d4d48c265d199616fd3709d966343629596464687f611eb",
    FILES[2][0]:"380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8",
    FILES[3][0]:"2405269110585a3921dfc64ed1b2adbf0622c520cfdce8bb6b1ac6d825f23103",
    FILES[4][0]:"739006f03b37c36d7aa11b6b68612338fc5249c7f48b9d854520ee7e3ea9c06e",
}
PLAN_FILE="p08_b3_pilot16_offline_staging_plan.json"

class StageNoGo(ValueError):pass

def ensure(ok:bool,msg:str):
    if not ok:raise StageNoGo("NO-GO: "+msg)

def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()

def plan_locations()->list[dict]:
    stage=[
        {"filename":name,"source_sha256":EXPECTED_SHA[name],
         "bytes":int(hi,16)-int(lo,16),"DDR_destination_start":lo,
         "DDR_destination_end_exclusive":hi,
         "physical_write_authorized":False,
         "physical_readback_required":True}
        for name,lo,hi in FILES
    ]
    stage.append({
        "filename":FILES[0][0],
        "source_sha256":EXPECTED_SHA[FILES[0][0]],
        "bytes":0xD80000,
        "DDR_destination_start":"0x43000000",
        "DDR_destination_end_exclusive":"0x43D80000",
        "operation":"SECOND separate 27core immutable BACKUP COPY",
        "physical_write_authorized":False,
        "physical_readback_required":True,
    })
    proposed=ingress.validate_memory_ranges()["ranges"]
    spans=sorted((int(x["DDR_destination_start"],16),
                  int(x["DDR_destination_end_exclusive"],16),x["filename"])
                 for x in stage)
    for a,b in zip(spans,spans[1:]):
        ensure(a[1]<=b[0],"overlapping target physical source/backup copies")
    for lo,hi,name in spans:
        ensure(0x40000000<=lo<hi<=0x44000000,
               "proposed physical data outside accepted 64MiB envelope")
    ensure(proposed["immutable_27_P02_backup_candidate"]==[
        "0x43000000","0x43D80000"] and
        proposed["1024_raw_pixels_pool"]==[
        "0x42100000","0x421C4000"],
        "original candidate DDR owner plan has changed")
    return stage

def stage(frozen:Path,routes:Path,b2_stage:Path,oracle:Path,out:Path)->dict:
    ensure(out.is_absolute() and not out.exists() and not out.is_symlink() and
           out.parent.is_dir() and
           not out.resolve().is_relative_to(core.REPO.resolve()),
           "NEW outside-repo absolute directory required")
    pilot.source_oracle(oracle)  # user-accepted 13e3... SHA and 16 rows
    frozen_manifest=core.admit_freeze(frozen)
    rows=core.source_index(frozen,frozen_manifest)
    prior_routes.require_routes(routes,frozen)
    original_binding= binding.build_payload(
        binding.original_core_bindings(frozen))
    with (b2_stage/ingress.RAW_FILENAME).open("rb") as file:
        pool=file.read()
    ensure(len(pool)==1024*784 and sha(pool)==EXPECTED_SHA[FILES[4][0]],
           "original matched raw 1024 source pool differs")
    original_stage_manifest=b2_stage/ingress.MANIFEST_FILENAME
    ensure(original_stage_manifest.is_file() and
           not original_stage_manifest.is_symlink() and
           sha(original_stage_manifest.read_bytes())==
           "996d48b1d4e83ec2433d445a4be37cff8ef50b599d07db23c165f1be10337e6e",
           "original 1024 ingress provenance changed")
    ledger=b2_stage/ingress.HASH_FILENAME
    ensure(ledger.is_file() and not ledger.is_symlink() and
           sha(ledger.read_bytes())==
           "5f21aa4e64f31918272b4d7ef84830bc309c6c205744f6735cec4bc69a1a719e",
           "original 1024 exact wire SHA ledger changed")
    data={}
    original_cores=bytearray()
    for index,row in enumerate(rows):
        bytes_=corefile=(frozen/row["source_relative_path"]).read_bytes()
        ensure(len(bytes_)==core.STRIDE and
               sha(bytes_)==row["sha256"] and row["logical_core_id"]==index,
               "original frozen 27 P02 cores changed during stage")
        original_cores.extend(bytes_)
    data[FILES[0][0]]=bytes(original_cores)
    data[FILES[1][0]]=original_binding
    data[FILES[2][0]]=(routes/routed.IN_FILENAME).read_bytes()
    data[FILES[3][0]]=(routes/routed.OUT_FILENAME).read_bytes()
    data[FILES[4][0]]=pool
    for name,lo,hi in FILES:
        payload=data[name]
        ensure(len(payload)==int(hi,16)-int(lo,16) and
               sha(payload)==EXPECTED_SHA[name],
               "original frozen input bytes SHA/size changed: "+name)
    targets=plan_locations()
    tmp=Path(tempfile.mkdtemp(prefix=".p08_b3_stage_",dir=out.parent))
    try:
        for name,_,_ in FILES:
            with (tmp/name).open("xb") as fp:
                fp.write(data[name]);fp.flush();os.fsync(fp.fileno())
        manifest={
            "schema":SCHEMA,
            "first16_scalar_oracle_sha256":pilot.ORACLE_SHA,
            "pilot_executed_frames":0,
            "full_matched_source_images":1024,
            "original_27_core_count":27,
            "original_27_cores_aggregate_sha256":EXPECTED_SHA[FILES[0][0]],
            "original_signed_33_B24_asset_verifier":True,
            "original_1024_B1_3_ingress_sha256_ledger":
                "5f21aa4e64f31918272b4d7ef84830bc309c6c205744f6735cec4bc69a1a719e",
            "ordered_core_p02_sha256":[row["sha256"] for row in rows],
            "proposed_ddr_transfers":targets,
            "planned_immutable_backup_distinct_from_mutable_source":True,
            "original_27core_P02_bytes_are_NOT_modified":True,
            "physical_DDR_exclusivity_independently_proven":False,
            "same_session_JTAG_readback_verified":False,
            "operator_approved_dedicated_JTAG_takeover":False,
            "new_pilot_ELF_downloaded":False,
            "board_contact":False,
            "reboot_required_if_later_destructive_session_approved":True,
            "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
        }
        (tmp/PLAN_FILE).write_text(json.dumps(
            manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        for name in data:
            ensure(sha((tmp/name).read_bytes())==EXPECTED_SHA[name],
                   "new external stage reread mismatch: "+name)
        tmp.rename(out)
    finally:
        if tmp.exists():shutil.rmtree(tmp)
    return manifest

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("frozen-dir","routes-dir","ingress-dir",
                 "oracle","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    try:
        rec=stage(a.frozen_dir,a.routes_dir,a.ingress_dir,a.oracle,a.out)
        print("P08_B3_PILOT16_PC_ONLY_ORIGINAL_DDR_STAGE_PASS=1")
        print("P08_B3_PILOT16_ORIGINAL_27CORE_REUSE_SHA256="+rec[
            "original_27_cores_aggregate_sha256"])
        print("P08_B3_PILOT16_STAGE_FILES=5")
        print("P08_B3_PILOT16_PROPOSED_WRITES=6")
        print("P08_B3_PILOT16_PHYSICAL_JTAG_BYTES_WRITTEN=0")
        print("P08_B3_PILOT16_PHYSICAL_DDR_OWNER_PROVEN=0")
        print("P08_B3_PILOT16_PC_STAGE="+str(a.out))
        return 0
    except (StageNoGo,ValueError,KeyError,TypeError,OSError,AssertionError) as err:
        print("P08_B3_PILOT16_PC_STAGE_NO_GO="+str(err),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
