#!/usr/bin/env python3
"""P07-B.6.1 original signed 27core hardware evidence freeze/handoff (PC ONLY).

First inventory the exact existing B2.4 frozen source, original three
TRAIN routes, accepted P03 XSA, new original B5 A53 real ELF/map,
and all numerical report identities WITHOUT changing anything.
A candidate inventory does not close B5 or B6.

Only --mode seal may mark the freeze complete. It requires an already
accepted REAL, EXTERNAL B5.4 --mode accept receipt AND the actual operator
attestation, then independently replays all 5 real physical evidence
validation gates using the B5.4 acceptance function. It does NOT merge
GitHub branches, unseal official TEST, read/write FPGA or alter original
sources. External write-once JSON, not a detached mutable manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import p07_b4l1_stage_frozen_27core as b4l1
import p07_b4m_offline_admission as routes_gate
import p07_b5_raw_trace_offline_admission as raw_gate
import p07_b5_scaled_validation as old
import p07_b5_final_acceptance as b54

ROOT=Path(__file__).resolve().parents[1]
ELF_SHA=b54.PINNED_B5_ELF
MAP_SHA=b54.PINNED_B5_MAP
RAW_SHA=b54.PINNED_RAW_SHA
V3_ELF_SHA="66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904"
V3_MAP_SHA="148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede"
P03_XSA_SHA="52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
MAIN_LITERATURE_BLOB_SHA="3c45d0a0d0b55378d3564d8f82282803a8eb1a3e"
# Frozen B2.4 manifest tracks exactly 33 signed source files (2 checkpoint,
# source graph, compiled deployment, B2.3 evidence, protocol and 27 P02
# contexts). B6 must inventory ALL of them, not a handpicked subset.
ORIGINAL_B24_ASSET_COUNT=33
TRAIN_FILES=(
    "p07_b4m_frozen_inputs_manifest.json",
    "p07_b4m_original_output_routes_80k.bin",
    "p07_b4m_original_input_routes_896k.bin",
    *(f"p07_b4m_original_TRAIN_validation_{i}_ingress.bin" for i in (0,1,2)),
)
SCHEMA="p07-b6-1-original-27core-source-and-hardware-evidence-freeze-v1"

class FreezeNoGo(ValueError):
    pass

def require(condition:bool,message:str)->None:
    if not condition: raise FreezeNoGo("NO-GO: "+message)

def sha_regular(path:Path)->str:
    require(path.is_file() and not path.is_symlink(),
            "missing or symlinked signed source: "+str(path))
    hasher=hashlib.sha256()
    with path.open("rb") as inp:
        for block in iter(lambda:inp.read(1<<20),b""):
            hasher.update(block)
    return hasher.hexdigest()

def verify_b5_review(path:Path)->dict:
    require(path.is_absolute() and path.is_file() and not path.is_symlink() and
            not path.resolve().is_relative_to(ROOT),
            "operator's original B5.4 PC numerical review report required")
    obj=old.read_json(path)
    expected={
        "schema":b54.SCHEMA,
        "mode":"review",
        "signed_original_model_frozen":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "genuine_original_V3_27core_physical_sessions":4,
        "distinct_original_TRAIN_frames":3,
        "original_frame_ordinals":[0,1,2,0],
        "independent_original_multiframe_26tick_FNV64_and_all_counters_pass":True,
        "original_TRAIN0_repeat_physical_counters_and_FNV64_exactly_equal":True,
        "genuine_new_B5_raw_26tick_physical_sessions":1,
        "B5_RAW_original_TRAIN_ordinal":0,
        "B5_RAW_physical_neuron_records":26260,
        "B5_RAW_physical_840320_bytes_exactly_equal_original_scalar":True,
        "B5_RAW_physical_trace_SHA256":RAW_SHA,
        "B5_RAW_terminal_mailbox_SHA256":b54.PINNED_MAILBOX_SHA,
        "B5_RAW_original_26_tick_FNV64":b54.PINNED_RAW_FNV,
        "B5_RAW_7_independent_numerical_checks_pass":True,
        "B5_RAW_original_27core_staging_physically_verified":True,
        "original_P03_PL_and_accepted_original_V3_ELF_modified":False,
        "boot_firmware_and_other_DDR_owner_independently_proven":False,
        "independent_board_powercycle_instrumentation_proof":False,
        "operator_attested_cold_boot_and_recovery_all_five_sessions":False,
        "operator_explicit_final_B5_acceptance":False,
        "P07_B5_final_acceptance":False,
        "P07_B6_started":False,
        "P08_B_started":False,
        "main_merged":False,
        "all_required_B5_numerical_gates_pass":True,
    }
    for key,value in expected.items():
        require(obj.get(key)==value,
                "original genuine B5.4 pre-acceptance numerical report drift: "+key)
    require(len(obj.get("original_V3_evidence_dirs",[]))==4 and
            obj.get("B5_RAW_physical_evidence_dir") not in
                obj["original_V3_evidence_dirs"],
            "four V3 and fifth raw physical evidence folders not distinct")
    for key in ("original_4run_report_sha256",
                "B5_RAW_independent_report_sha256"):
        require(isinstance(obj.get(key),str) and len(obj[key])==64,
                "B5.4 historical independent audit SHA missing: "+key)
    return obj

def validate_source_freeze(args)->dict:
    # All 33 actual B2.4 frozen files checked by original accepted gate.
    b4l1.admit_freeze(args.frozen_dir)
    routes=routes_gate.require_routes(args.routes_dir,args.frozen_dir)
    admitted=raw_gate.admit(frozen=args.frozen_dir,routes=args.routes_dir,
        build=args.build_dir,reports=args.reports)
    require(old.read_json(args.offline_report)==admitted,
            "new B5 ELF/map/XSA original independent admission changed")
    elf=admitted["new_genuine_b5_ELF"]
    require(elf["new_elf_sha256"]==ELF_SHA and
            admitted["new_genuine_b5_linker_map_sha256"]==MAP_SHA and
            admitted["accepted_original_P03_XSA_sha256"]==P03_XSA_SHA,
            "accepted physical P03 XSA or separately built B5 ELF/map drift")
    require(routes["input_routes"]==20384 and
            routes["output_routes"]==1000,
            "pinned original source routing changed")
    manifest_path=args.frozen_dir/"frozen_manifest.json"
    signed=old.read_json(manifest_path)
    assets=signed.get("assets")
    require(isinstance(assets,list) and len(assets)==ORIGINAL_B24_ASSET_COUNT,
            "original B2.4 source manifest must enumerate all 33 files")
    paths={"original_b24/frozen_manifest.json":manifest_path}
    for entry in assets:
        require(isinstance(entry,dict),"malformed B2.4 asset entry")
        name=entry.get("path")
        require(isinstance(name,str) and name and
                not Path(name).is_absolute() and
                ".." not in Path(name).parts and
                chr(92) not in name,
                "unsafe original frozen relative path in signed manifest")
        key="original_b24/"+name
        require(key not in paths,"duplicate original frozen source asset")
        paths[key]=args.frozen_dir/name
    for name in TRAIN_FILES:
        paths["original_TRAIN_routes/"+name]=args.routes_dir/name
    paths["original_P03_XSA/p03_2_ps_mmio.xsa"]=args.reports/"p03_2_ps_mmio.xsa"
    paths["new_B5_A53/p07_b5_raw_trace_v1.elf"]=args.build_dir/"vitis_workspace"/"p07_b5_raw_trace_v1.elf"
    paths["new_B5_A53/p07_b5_raw_trace_v1.map"]=args.build_dir/"vitis_workspace"/"p07_b5_raw_trace_v1.map"
    manifest={key:sha_regular(path) for key,path in sorted(paths.items())}
    require(len([k for k in manifest if k.startswith("original_b24/")])==
            ORIGINAL_B24_ASSET_COUNT+1,
            "complete 33-file original freeze inventory not included")
    signed_sha={e["path"]:e.get("sha256") for e in assets}
    for name,expected in signed_sha.items():
        require(manifest["original_b24/"+name]==expected,
                "signed B2.4 artifact differs from original manifest: "+name)
    require(manifest["original_b24/frozen_manifest.json"]==
            b4l1.FROZEN_SHA and
            manifest["new_B5_A53/p07_b5_raw_trace_v1.elf"]==ELF_SHA and
            manifest["new_B5_A53/p07_b5_raw_trace_v1.map"]==MAP_SHA and
            manifest["original_P03_XSA/p03_2_ps_mmio.xsa"]==P03_XSA_SHA,
            "original B2.4 frozen source or new A53/XSA source SHA drift")
    return {
        "source_sha256_manifest":manifest,
        "original_B24_manifest_entries_individually_SHA256_revalidated":33,
        "immutable_original_B24_33_file_freeze_verified":True,
        "original_compiled_784_1000_10_source_sha256":
            admitted["original_B24_compiled_fingerprint"],
        "original_27_logical_core_count":27,
        "original_P03_3_slot_hardware_shell_sha256":P03_XSA_SHA,
        "original_registered_input_axon_routes":20384,
        "original_registered_output_routes":1000,
        "original_logical_neuron_count":1010,
        "original_V3_A53_accepted_ELF_SHA256_prior_physical_evidence":V3_ELF_SHA,
        "original_V3_A53_accepted_map_SHA256_prior_physical_evidence":V3_MAP_SHA,
        "new_B5_A53_ELF_SHA256":ELF_SHA,
        "new_B5_A53_map_SHA256":MAP_SHA,
    }

def build_inventory(args)->dict:
    require(args.mode in ("inventory","seal"),"unknown B6 freeze mode")
    review=verify_b5_review(args.b5_review)
    original=validate_source_freeze(args)
    result={
        "schema":SCHEMA,
        "mode":args.mode,
        **original,
        "operator_original_5run_numerical_review_sha256":sha_regular(args.b5_review),
        "operator_original_4run_report_sha256":
            review["original_4run_report_sha256"],
        "operator_original_B5_RAW_report_sha256":
            review["B5_RAW_independent_report_sha256"],
        "operator_original_physical_V3_evidence_dirs":
            review["original_V3_evidence_dirs"],
        "operator_original_physical_RAW_evidence_dir":
            review["B5_RAW_physical_evidence_dir"],
        "B5_RAW_physical_840320B_sha256":RAW_SHA,
        "B5_original_five_physical_numerical_validation_pass":True,
        "B5_raw_neuron_bytewise_scalar_parity_pass":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "new_B5_and_B6_board_execution_in_this_tool":False,
        "original_frozen_HLS_RTL_or_bitstream_modified":False,
        "main_only_LitReview_md_expected_blob_SHA":MAIN_LITERATURE_BLOB_SHA,
        "main_only_LitReview_md_unchanged_verified_by_this_PC_tool":False,
        "boot_firmware_DDR_exclusivity_independently_proven":False,
        "independent_power_cycle_hardware_attestation":False,
        "every_individual_packet_word_physically_verified":False,
        "B5_formal_operator_acceptance_verified":False,
        "B6_1_host_only_freeze_inventory_completed":True,
        "B6_final_hardware_freeze_accepted":False,
        "P07_B_complete":False,
        "P08_B_started":False,
        "main_merged":False,
    }
    if args.mode=="inventory":
        require(args.b5_acceptance is None and args.attestation is None and
                not args.run,
                "B6 inventory must not silently use acceptance/attestation arguments")
        return result
    require(args.b5_acceptance is not None and args.attestation is not None and
            len(args.run)==4,
            "B6 seal requires exact operator-created B5.4 acceptance, signed attestation, and 4 real V3 run locations")
    session_args=SimpleNamespace(
        mode="accept",frozen_dir=args.frozen_dir,staged_dir=args.staged_dir,
        routes_dir=args.routes_dir,build_dir=args.build_dir,reports=args.reports,
        offline_report=args.offline_report,fourrun_report=args.fourrun_report,
        raw_evidence=args.raw_evidence,raw_report=args.raw_report,
        run=args.run,attestation=args.attestation,
        confirm_final_acceptance=b54.FINAL_CONFIRM,
    )
    recomputed=b54.closeout(session_args) # all physical evidence re-opened
    accepted=old.read_json(args.b5_acceptance)
    require(recomputed==accepted and
            accepted.get("P07_B5_final_acceptance") is True and
            accepted.get("operator_attested_cold_boot_and_recovery_all_five_sessions") is True and
            accepted.get("operator_explicit_final_B5_acceptance") is True and
            accepted.get("boot_firmware_and_other_DDR_owner_independently_proven") is False and
            accepted.get("independent_board_powercycle_instrumentation_proof") is False,
            "real B5.4 operator-attested physical acceptance does not match independent recomputation")
    attested=old.read_json(args.attestation)
    entries=attested.get("sessions")
    require(isinstance(entries,list) and len(entries)==5 and
            all(isinstance(x,dict) and
                isinstance(x.get("evidence_dir"),str) for x in entries),
            "operator attestation must identify five original source-backed physical sessions")
    require([x["evidence_dir"] for x in entries]==
            [*result["operator_original_physical_V3_evidence_dirs"],
             result["operator_original_physical_RAW_evidence_dir"]],
            "operator acceptance lists changed physical evidence session")
    result.update({
        "operator_accepted_B5_4_report_SHA256":sha_regular(args.b5_acceptance),
        "operator_attestation_source_SHA256":sha_regular(args.attestation),
        "B5_formal_operator_acceptance_verified":True,
        "B6_1_host_only_freeze_inventory_completed":True,
        "B6_final_hardware_freeze_accepted":False,
        "P07_B_complete":False,
        "main_merged":False,
    })
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("inventory","seal"),default="inventory")
    for name in ("frozen-dir","routes-dir","build-dir","reports",
                 "offline-report","b5-review","out"):
        p.add_argument("--"+name,required=True,type=Path)
    for name in ("b5-acceptance","attestation","staged-dir",
                 "fourrun-report","raw-evidence","raw-report"):
        p.add_argument("--"+name,type=Path)
    p.add_argument("--run",action="append",default=[])
    args=p.parse_args()
    try:
        old.require_external_report(args.out)
        result=build_inventory(args)
        old.write_report(args.out,result)
        print("P07_B6_ORIGINAL_27CORE_SIGNED_SOURCE_ARTIFACT_FREEZE_INVENTORY_PASS=1")
        print("P07_B6_B5_FORMAL_ACCEPTANCE_INDEPENDENTLY_RECHECKED="+
              ("1" if result["B5_formal_operator_acceptance_verified"] else "0"))
        print("P07_B6_KV260_BOARD_CONTACT=0")
        print("P07_B6_MAIN_MERGE_PERFORMED=0")
        print("P07_B6_OFFICIAL_MNIST_TEST_SEALED=1")
        print("P07_B6_FINAL_ACCEPTANCE=0")
        print("P07_B6_FREEZE_MANIFEST="+str(args.out))
        return 0
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as exc:
        print("P07_B6_FREEZE_INVENTORY_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
