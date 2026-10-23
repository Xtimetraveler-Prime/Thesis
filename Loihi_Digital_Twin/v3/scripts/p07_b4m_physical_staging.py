#!/usr/bin/env python3
"""P07-B.4m SAME-SESSION REAL KV260 STAGING experiment, NOT A53 inference.

DEFAULT preflight is read-only HOST-ONLY. Stage requires explicit separate
hardware approvals; it deliberately halts Linux, programs accepted P03, and
physically overwrites original 27×512 KiB frozen model, original signed B4l
16KiB bindings, NEW signed B4m 80KiB+896KiB route tables, and exactly one
selected frozen original TRAIN validation ingress frame. EVERY staged byte
is independently read back and compared with the frozen host source.
NO ELF dow, NO low-DDR [0,0x106B00) writes, NO A53 resume, NO inference.
REBOOT KV260 after ANY actual hardware attempt even on failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import p07_b4l_b3_physical_epoch as old
import p07_b4l_physical_model_deploy as model
import p07_b4l_frozen_bindings as binds
import p07_b4m_frozen_inputs as frozen
import p07_b4m_offline_admission as admission

STAGE_TCL="vivado/p07_b4m_stage_original_routes_and_train.tcl"
STAGE_APPROVAL="B4M_ORIGINAL_TRAIN_ROUTE_AND_FRAME_DDR_OVERWRITE_APPROVED"
PASS_STAGE="P07_B4M_ORIGINAL_ROUTES_AND_TRAIN_3_DDR_READBACK_PASS=1"
STAGING_SUCCESS="P07_B4M_ORIGINAL_27CORE_BINDINGS_ROUTES_TRAIN_STAGING_PHYSICAL_PASS_REBOOT_REQUIRED"
EXPECTED_ELF_SHA="ccbd8c531e5571f929e81613cfee71f54abf341c36412ebcfa7d98e2313e6b70"
EXPECTED_MAP_SHA="b6d34c354e34075be2e650335a34ea103b72c7927a36c526841006df59a8e8c3"
EXPECTED_STAGE_SHA={
    frozen.OUT_FILENAME:"2405269110585a3921dfc64ed1b2adbf0622c520cfdce8bb6b1ac6d825f23103",
    frozen.IN_FILENAME:"380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8",
    "p07_b4m_original_TRAIN_validation_0_ingress.bin":"2aa772efd381805bab24fea145186d22f3550b156f155a9ab51dcef10e6d8126",
    "p07_b4m_original_TRAIN_validation_1_ingress.bin":"814d04908c370d367680952fddc67a839b05698f615972f9d96daafc52c8cb78",
    "p07_b4m_original_TRAIN_validation_2_ingress.bin":"67dc1af04623a51ddbeb2d9ac05a8579c3a42e2e4637a0683f4e543cbc8e8f93",
}
APPROVALS=(
    "dedicated_jtag_owner",
    "cpu_takeover_approved",
    "ddr_27core_overwrite_approved",
    "frozen_binding_overwrite_approved",
    "route_train_ddr_overwrite_approved",
    "firmware_coexistence_risk_acknowledged",
    "pl_program_approved",
    "reboot_recovery_approved",
)

class StageNoGo(ValueError):
    pass

def resolve_elf_inspection_tools()->tuple[str,str]:
    """Use a compatible host GNU inspector for read-only AArch64 analysis.

    The accepted historical B4i preflight has fixed cross-binutils command
    defaults, although GNU host readelf (and GNU nm with AArch64 BFD support)
    can inspect an AArch64 ELF without running target code. Pass resolved
    paths *only for this new B4m caller*; do not mutate the older B4i
    acceptance script or relax any original B4i signature/source checks.
    """
    def first(names:tuple[str,...],label:str)->str:
        for name in names:
            candidate=shutil.which(name)
            if candidate:
                return candidate
        raise StageNoGo("NO-GO: missing GNU "+label+
                        "; install binutils or place AMD AArch64 binutils "
                        "on PATH; NO BOARD ACCESS")
    readelf=first((
        "aarch64-none-elf-readelf",
        "aarch64-linux-gnu-readelf",
        "readelf",
    ),"readelf")
    nm=first((
        "aarch64-none-elf-nm",
        "aarch64-linux-gnu-nm",
        "nm",
    ),"nm")
    return readelf,nm


def require_original(args:argparse.Namespace)->tuple[dict,dict,dict,dict]:
    """PC-only: independently validate frozen B2.4 model and exact pinned
    artifacts; require previous successful offline admission report rather
    than trusting its presence as a blank permission to touch the board.
    """
    index=model.prepare_verified_contexts(args.frozen_dir,args.staged_dir)
    desc=old.require_real_bindings(args.frozen_dir,args.staged_dir,args.bindings_dir)
    readelf,nm=resolve_elf_inspection_tools()
    old.b4i.preflight(args.b4i_build,args.reports,readelf=readelf,nm=nm)
    staged=admission.require_routes(args.routes_dir,args.frozen_dir)
    elf=admission.require_elf(args.elf)
    if (elf["new_elf_sha256"]!=EXPECTED_ELF_SHA or
        elf["new_linker_map_sha256"]!=EXPECTED_MAP_SHA or
        elf["pt_load_end_exclusive"]!="0x00106B00" or
        elf["pt_load_filesz"]!=106580 or
        elf["pt_load_memsz"]!=1075968):
        raise StageNoGo("NO-GO: operator-approved B4m ELF/map SHA or low-DDR footprint differs")
    for name,expected_sha in EXPECTED_STAGE_SHA.items():
        if staged["staged_files_sha256"].get(name)!=expected_sha:
            raise StageNoGo("NO-GO: operator original signed TRAIN input/route SHA differs: "+name)
    if staged["input_routes"]!=20384 or staged["output_routes"]!=1000 or (
        staged["registered_axons"]!=21384):
        raise StageNoGo("NO-GO: original frozen B2.4 27-core model count differs")
    source=args.offline_report
    if (not source.is_absolute() or source.is_symlink() or
        not source.is_file() or not source.name.startswith("p07_b4m_admission_")):
        raise StageNoGo("NO-GO: exact original offline admission JSON must exist")
    proof=json.loads(source.read_text())
    if (proof.get("schema")!="p07-b4m-full-26tick-offline-elf-and-stage-gate-v1" or
        proof.get("staging")!=staged or proof.get("elf")!=elf or
        proof.get("destructive_launch_authorized") is not False or
        proof.get("real_KV260_inference_executed") is not False or
        proof.get("full_numerical_parity_verified") is not False or
        proof.get("official_MNIST_TEST")!="SEALED_NOT_ACCESSED"):
        raise StageNoGo("NO-GO: original full PC report no longer agrees with independent source checks")
    return index,desc,staged,elf

def stage_requirements(args:argparse.Namespace)->None:
    for name in APPROVALS:
        if getattr(args,name)!="YES":
            raise StageNoGo("NO-GO: explicit --"+name.replace("_","-")+" YES required")
    e=args.evidence
    if (e is None or not e.is_absolute() or e.is_symlink() or e.exists() or
        e.resolve().is_relative_to(old.b4i.ROOT) or not e.parent.is_dir()):
        raise StageNoGo("NO-GO: NEW external absolute physical evidence directory required")
    for command in ("xsdb","vivado"):
        if not shutil.which(command):
            raise StageNoGo("NO-GO: board utility absent: "+command)

def compare_readback(readback_dir:Path,source:dict[str,Path])->dict:
    if (not readback_dir.is_dir() or readback_dir.is_symlink() or
        {x.name for x in readback_dir.iterdir()}!=set(source)):
        raise StageNoGo("NO-GO: wrong/new/missing physical READBACK files")
    report={}
    for name,original in source.items():
        physical=readback_dir/name
        if (not physical.is_file() or physical.is_symlink() or
            physical.stat().st_size!=original.stat().st_size or
            physical.read_bytes()!=original.read_bytes()):
            raise StageNoGo("NO-GO: independent physical byte mismatch for "+name)
        report[name]={
            "bytes":original.stat().st_size,
            "sha256":old.file_sha(physical),
            "byte_exact_vs_signed_host_input":True,
        }
    return report

def execute_staging(args:argparse.Namespace,index:dict,desc:dict,staged:dict,elf:dict,\n                    *,on_verified=None)->None:
    stage_requirements(args)
    output=args.evidence
    output.mkdir(mode=0o700,exist_ok=False)
    (output/"stage.txt").write_text("STAGING_PREPARATION_STARTED_PHYSICAL_ATTEMPT_REBOOT_REQUIRED\n")
    (output/"manifest.json").write_text(json.dumps({
        "experiment":"P07-B.4m physical staging/readback ONLY",
        "original_model_bundle_sha256":model.ACCEPTED_BUNDLE_SHA,
        "original_16k_descriptor_sha256":desc["binary_sha256"],
        "original_route_and_train_sha256":staged["staged_files_sha256"],
        "training_validation_ordinal":args.validation_ordinal,
        "genuine_full_26tick_elf_sha256":elf["new_elf_sha256"],
        "genuine_full_26tick_pt_load_end":elf["pt_load_end_exclusive"],
        "real_elf_downloaded":False,"inference_executed":False,
        "low_DDR_exclusivity_independently_proven":False,
        "reboot_required_after_actual_hardware_contact":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED"
    },sort_keys=True,indent=2)+"\n")
    print("P07_B4M_STAGING_NO_A53_ELF_DOWNLOAD=1",flush=True)
    try:
        model.prep_transfer_files(args.staged_dir,output/"transfer_inputs",index)
        (output/"physical_readback").mkdir(mode=0o700)
        original_desc=args.bindings_dir/binds.FILENAME
        raw=original_desc.read_bytes()
        if (len(raw)!=binds.SIZE or
            old.file_sha(original_desc)!=old.ACCEPTED_DESCRIPTOR_SHA or
            desc["binary_sha256"]!=old.ACCEPTED_DESCRIPTOR_SHA):
            raise StageNoGo("NO-GO: frozen original B4l descriptor changed")
        (output/"binding_input_16k.bin").write_bytes(raw)
        frame_name=f"p07_b4m_original_TRAIN_validation_{args.validation_ordinal}_ingress.bin"
        stage_inputs={
            "output_routes_80k_physical.bin":args.routes_dir/frozen.OUT_FILENAME,
            "input_routes_896k_physical.bin":args.routes_dir/frozen.IN_FILENAME,
            "original_TRAIN_ingress_physical.bin":args.routes_dir/frame_name,
        }
        for key,path in stage_inputs.items():
            if old.file_sha(path)!=EXPECTED_STAGE_SHA[path.name]:
                raise StageNoGo("NO-GO: TRAIN or original frozen signed source changed since PC admission: "+path.name)
        (output/"b4m_physical_route_readback").mkdir(mode=0o700)
        (output/"stage.txt").write_text("ALL_ORIGINAL_HOST_BYTES_VERIFIED_BEFORE_PHYSICAL_TAKEOVER\n")
        old.b4i.log_call(["xsdb",old.b4j.TAKEOVER_TCL,
                          "DEDICATED_DISCARD_LINUX_APPROVED","tcp:127.0.0.1:3121"],
                         output/"ps_width.log")
        old.b4i.verify_takeover_log((output/"ps_width.log").read_text())
        (output/"stage.txt").write_text("REAL_A53_HALTED_WIDTH128_PASS_REBOOT_REQUIRED\n")
        old.b4i.log_call(["vivado","-mode","batch","-source",old.b4j.PROGRAM_TCL,
                          "-tclargs",str(args.reports/"p03_2_ps_mmio.bit"),
                          str(args.reports/"p03_2_ps_mmio.ltx"),
                          "localhost:3121"],output/"program.log")
        old.b4j.require_programmed_shell((output/"program.log").read_text())
        (output/"stage.txt").write_text("ACCEPTED_P03_SHELL_PROGRAMMED_REBOOT_REQUIRED\n")
        old.b4i.log_call(["xsdb",model.CORE_TCL,"DEDICATED_27_DDR_OVERWRITE_APPROVED",
                          str(output/"transfer_inputs"),str(output/"physical_readback"),
                          "tcp:127.0.0.1:3121"],output/"ddr_stage.log")
        old.checked_marker(output/"ddr_stage.log","P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1")
        for c in range(27):
            old.checked_marker(output/"ddr_stage.log",f"P07_B4L_CORE_{c}_512K_PHYSICAL_READBACK_PASS=1")
        model_receipt=model.verify_physical_readback(
            args.staged_dir,output/"physical_readback",index)
        (output/"model_verified.json").write_text(
            json.dumps(model_receipt,sort_keys=True,indent=2)+"\n")
        (output/"stage.txt").write_text("ALL_27_ORIGINAL_CORE_READBACK_PASS_REBOOT_REQUIRED\n")
        old.b4i.log_call(["xsdb",old.BIND_STAGE_TCL,
                          "B4L_FROZEN_BINDING_16K_OVERWRITE_APPROVED",
                          str(output/"binding_input_16k.bin"),
                          str(output/"binding_readback_16k.bin"),
                          "tcp:127.0.0.1:3121"],output/"binding_stage.log")
        old.checked_marker(output/"binding_stage.log",
                           "P07_B4L_B3_FROZEN_DESCRIPTOR_16K_PHYSICAL_READBACK_TCL_PASS=1")
        physical_desc=output/"binding_readback_16k.bin"
        if (not physical_desc.is_file() or physical_desc.is_symlink() or
            physical_desc.read_bytes()!=raw or
            old.file_sha(physical_desc)!=old.ACCEPTED_DESCRIPTOR_SHA):
            raise StageNoGo("NO-GO: original signed 16KiB descriptor physical readback mismatch")
        (output/"stage.txt").write_text("SIGNED_MODEL_AND_BINDINGS_PASS_NEW_ROUTES_PENDING_REBOOT_REQUIRED\n")
        old.b4i.log_call(["xsdb",STAGE_TCL,STAGE_APPROVAL,
                          str(stage_inputs["output_routes_80k_physical.bin"]),
                          str(stage_inputs["input_routes_896k_physical.bin"]),
                          str(stage_inputs["original_TRAIN_ingress_physical.bin"]),
                          str(output/"b4m_physical_route_readback"),
                          "tcp:127.0.0.1:3121"],output/"b4m_route_stage.log")
        for slot in range(3):
            old.checked_marker(output/"b4m_route_stage.log",
                               f"P07_B4M_DDR_STAGE_{slot}_BYTE_EXACT_PASS=1")
        old.checked_marker(output/"b4m_route_stage.log",PASS_STAGE)
        verified=compare_readback(output/"b4m_physical_route_readback",stage_inputs)
        for key,report in verified.items():
            stage_sha=old.file_sha(stage_inputs[key])
            if report["sha256"]!=stage_sha:
                raise StageNoGo("NO-GO: original signed byte SHA changed during board readback")
        (output/"independent_staging_receipt.json").write_text(
            json.dumps({
                "original_27core_contexts_sha256":model_receipt["physical_readback_sha256"],
                "original_descriptor_16k_sha256":old.file_sha(physical_desc),
                "original_B2_4_routes_and_train_physical_sha256":verified,
                "validation_ordinal":args.validation_ordinal,
                "real_elf_downloaded":False,
                "first_barrier_acknowledged":False,
                "inference_executed":False,
                "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
                "low_DDR_exclusivity_independently_proven":False,
                "reboot_required":True,
            },indent=2,sort_keys=True)+"\n")
        (output/"stage.txt").write_text(STAGING_SUCCESS+"\n")
        print(STAGING_SUCCESS,flush=True)
        if on_verified is None:
            print("P07_B4M_26TICK_A53_INFERENCE_EXECUTED=0",flush=True)
        else:
            # EXACTLY one continuation while original staged bytes and
            # checked host SHA + physical readbacks are still valid in
            # this single destructive JTAG ownership session.
            # No callback is ever used by --mode stage.
            on_verified(output,verified)
    finally:
        print("P07_B4M_STAGE_REBOOT_REQUIRED_AFTER_ACTUAL_JTAG_ATTEMPT=1",flush=True)
        print("REBOOT KV260 before ANY Linux interaction; never resume halted Linux.",flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","stage"),default="preflight")
    for name in ("frozen-dir","staged-dir","bindings-dir","routes-dir","offline-report",
                 "reports","b4i-build","elf"):
        p.add_argument("--"+name,required=True,type=Path)
    p.add_argument("--validation-ordinal",choices=(0,1,2),type=int,default=0)
    p.add_argument("--evidence",type=Path)
    for name in APPROVALS:
        p.add_argument("--"+name.replace("_","-"),choices=("NO","YES"),default="NO")
    args=p.parse_args()
    try:
        index,desc,staged,elf=require_original(args)
        print("P07_B4M_ORIGINAL_MODEL_ROUTES_REAL_ELF_HOST_ADMISSION_PASS=1")
        print(f"P07_B4M_TRAIN_FRAME_ORDINAL={args.validation_ordinal}")
        print("P07_B4M_LOW_DDR_FW_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0")
        if args.mode=="preflight":
            print("P07_B4M_PREPARED_FOR_DEDICATED_PHYSICAL_STAGING_ONLY=1")
            print("P07_B4M_BOARD_TOUCHED=0")
            print("P07_B4M_A53_FULL_26TICK_LAUNCH_AUTHORIZED=0")
            return 0
        execute_staging(args,index,desc,staged,elf)
        return 0
    except (StageNoGo,ValueError,OSError,TypeError,KeyError,RuntimeError,
            subprocess.TimeoutExpired) as exc:
        print("P07_B4M_STAGING_NO_GO="+str(exc),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
