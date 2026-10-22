#!/usr/bin/env python3
"""Consolidated B4l deployed-model physical checkpoint (NO neural inference).

Default --mode preflight is PC-only. Execute mode destroys the former Linux
session, programs the *accepted* P03 shell and writes 27 ORIGINAL P02 B2.4
initial 512KiB contexts to reserved JTAG-owned DDR; independently rehashes
all 27 physical XSDB readbacks against the SHA-pinned original host stage.
It DOES NOT launch A53 ELF, page contexts into PL, or dispatch trained B2.
No handwritten operator note required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import p07_b4i_physical_pilot as b4i
import p07_b4j_shell_program_pilot as b4j
import p07_b4l1_stage_frozen_27core as b4l1

ACCEPTED_BUNDLE_SHA="3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e"
CORE_TCL="vivado/p07_b4l_stage_27_ddr.tcl"
APPROVALS=(
    "dedicated_jtag_owner",
    "cpu_takeover_approved",
    "ddr_27core_overwrite_approved",
    "firmware_coexistence_risk_acknowledged",
    "pl_program_approved",
    "reboot_recovery_approved",
)
CORE_INPUT="core_{:03d}_stage_512k.bin"
CORE_READBACK="core_{:03d}_physical_readback_512k.bin"


class DeployError(ValueError):
    pass


def prepare_verified_contexts(frozen:Path,staged:Path)->dict:
    """Check the user-accepted bundle against 33 original frozen B2.4 files."""
    report=b4l1.verify_bundle(frozen,staged)
    if (report["bundle_sha256"]!=ACCEPTED_BUNDLE_SHA
            or report["core_count"]!=27 or report["bytes"]!=14155776
            or report["physical_start"]!="0x40000000"
            or report["physical_end_exclusive"]!="0x40D80000"
            or not report["freeze_untouched"] or report["board_visited"]):
        raise DeployError("NO-GO: original user-attested B4l1 host stage identity drift")
    index=json.loads((staged/b4l1.INDEX_NAME).read_text())
    if (index["bundle_sha256"]!=ACCEPTED_BUNDLE_SHA
            or [r["logical_core_id"] for r in index["records"]]!=list(range(27))):
        raise DeployError("NO-GO: original B4l1 ordered index drift")
    return index


def check_operator_and_tools(args:argparse.Namespace)->None:
    for flag in APPROVALS:
        if getattr(args,flag)!="YES":
            raise DeployError("NO-GO: explicit --"+flag.replace("_","-")+" YES required")
    evidence=args.evidence
    if (evidence is None or not evidence.is_absolute() or evidence.exists()
            or evidence.is_symlink() or evidence.resolve().is_relative_to(b4i.ROOT)):
        raise DeployError("NO-GO: evidence must be a NEW absolute directory outside project")
    if not evidence.parent.is_dir():
        raise DeployError("NO-GO: evidence parent directory must already exist")
    for tool in ("xsdb","vivado"):
        if shutil.which(tool) is None:
            raise DeployError("NO-GO: hardware tool not available: "+tool)
    if args.reports.is_symlink() or not args.reports.is_dir():
        raise DeployError("NO-GO: accepted P03 routed reports not found")


def prep_transfer_files(staged:Path,work:Path,index:dict)->None:
    """Create 27 stable one-record transfer files FROM THE VERIFIED bundle."""
    work.mkdir(mode=0o700,exist_ok=False)
    bundle=staged/b4l1.BUNDLE_NAME
    with bundle.open("rb") as source:
        for row in index["records"]:
            core=row["logical_core_id"]
            piece=source.read(b4l1.STRIDE)
            if (len(piece)!=b4l1.STRIDE
                    or hashlib.sha256(piece).hexdigest()!=row["sha256"]):
                raise DeployError(f"NO-GO: original B4l1 bundle changed: core {core}")
            output=work/CORE_INPUT.format(core)
            with output.open("xb") as f:
                f.write(piece)
        if source.read(1):
            raise DeployError("NO-GO: bundle grew during transfer preparation")
    if b4l1.file_sha(bundle)!=ACCEPTED_BUNDLE_SHA:
        raise DeployError("NO-GO: original bundle drifted during splitting")


def verify_physical_readback(original:Path,readback:Path,index:dict)->dict:
    """Independent byte-exact comparison against original B4l.1 bundle."""
    if (not readback.is_dir() or readback.is_symlink()
            or {p.name for p in readback.iterdir()}!={CORE_READBACK.format(i) for i in range(27)}):
        raise DeployError("NO-GO: missing/extra physical readback file")
    totals=hashlib.sha256()
    proof=[]
    with (original/b4l1.BUNDLE_NAME).open("rb") as full:
        for row in index["records"]:
            cid=row["logical_core_id"]
            path=readback/CORE_READBACK.format(cid)
            if path.is_symlink() or not path.is_file() or path.stat().st_size!=b4l1.STRIDE:
                raise DeployError(f"NO-GO: core {cid} readback missing/short")
            raw=path.read_bytes()
            source=full.read(b4l1.STRIDE)
            digest=hashlib.sha256(raw).hexdigest()
            if digest!=row["sha256"] or raw!=source:
                raise DeployError(f"NO-GO: core {cid} DDR readback SHA/byte mismatch")
            totals.update(raw)
            proof.append({"core":cid,"DDR":row["physical_address"],"sha256":digest})
        if full.read(1):
            raise DeployError("NO-GO: source bundle length drift during readback verification")
    whole=totals.hexdigest()
    if whole!=ACCEPTED_BUNDLE_SHA:
        raise DeployError("NO-GO: physical DDR aggregate bundle digest mismatch")
    return {"physical_readback_sha256":whole,"byte_exact_core_count":27,
            "physical_span":"[0x40000000,0x40D80000)","records":proof,
            "physical_inference_executed":False}


def run_physical(args:argparse.Namespace,index:dict)->dict:
    check_operator_and_tools(args)
    out=args.evidence
    out.mkdir(mode=0o700,parents=False,exist_ok=False)
    (out/"stage.txt").write_text("EVIDENCE_STARTED_NO_HARDWARE_ACCEPTANCE_REBOOT_REQUIRED\n")
    (out/"manifest.json").write_text(json.dumps({
        "milestone":"P07-B.4l consolidated model deployment",
        "candidate_bundle_sha256":ACCEPTED_BUNDLE_SHA,
        "physical_range":"[0x40000000,0x40D80000)",
        "owner_map_note":"This intentionally displaces Linux RAM during a disposable session. "
           "Approval flags do NOT independently prove firmware DDR exclusivity.",
        "frozen_manifest_sha256":b4l1.FROZEN_SHA,
        "real_inference_executed":False,
        "physical_ddr_verified":False,
        "reboot_required":True,
    },sort_keys=True,indent=2)+"\n")
    try:
        # Stage and check all source bytes BEFORE any hardware is contacted.
        prep_transfer_files(args.staged_dir,out/"transfer_inputs",index)
        (out/"physical_readback").mkdir(mode=0o700)
        (out/"stage.txt").write_text("PREPARED_ALL_27_INPUTS_BOARD_GATE_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call([
            "xsdb",b4j.TAKEOVER_TCL,"DEDICATED_DISCARD_LINUX_APPROVED",
            "tcp:127.0.0.1:3121"
        ],out/"ps_width.log")
        states=b4i.verify_takeover_log((out/"ps_width.log").read_text())
        print("P07_B4L_REAL_A53_ACCOUNTING="+repr(states),flush=True)
        print("P07_B4L_REAL_FPD128_LPD128_PASS=1",flush=True)
        (out/"stage.txt").write_text("A53_STOP_WIDTH_PASS_PL_PROGRAM_PENDING_REBOOT_REQUIRED\n")

        b4i.log_call([
            "vivado","-mode","batch","-source",b4j.PROGRAM_TCL,"-tclargs",
            str(args.reports/"p03_2_ps_mmio.bit"),
            str(args.reports/"p03_2_ps_mmio.ltx"),"localhost:3121"
        ],out/"program.log")
        b4j.require_programmed_shell((out/"program.log").read_text())
        print("P07_B4L_ACCEPTED_P03_PROGRAM_VIO_RESET_PASS=1",flush=True)
        (out/"stage.txt").write_text("PL_PASS_27_DDR_WRITES_PENDING_REBOOT_REQUIRED\n")

        b4i.log_call([
            "xsdb",CORE_TCL,"DEDICATED_27_DDR_OVERWRITE_APPROVED",
            str(out/"transfer_inputs"),str(out/"physical_readback"),
            "tcp:127.0.0.1:3121"
        ],out/"ddr_stage.log")
        transcript=(out/"ddr_stage.log").read_text().splitlines()
        if (transcript.count("P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1")!=1
                or any(transcript.count(f"P07_B4L_CORE_{c}_512K_PHYSICAL_READBACK_PASS=1")!=1
                       for c in range(27))):
            raise DeployError("NO-GO: complete 27-core Tcl DDR verification receipt missing")
        (out/"stage.txt").write_text("PHYSICAL_DDR_TCL_PASS_INDEPENDENT_HASH_PENDING_REBOOT_REQUIRED\n")
        independent=verify_physical_readback(args.staged_dir,out/"physical_readback",index)
        (out/"independent_receipt.json").write_text(json.dumps(
            independent,sort_keys=True,indent=2)+"\n")
        (out/"stage.txt").write_text("ALL_27_ORIGINAL_FROZEN_P02_PHYSICAL_DDR_BYTE_EXACT_PASS_REBOOT_REQUIRED\n")
        print("P07_B4L_PHYSICAL_27_CORE_DDR_FULL_BYTE_EXACT_PASS=1",flush=True)
        print("P07_B4L_PHYSICAL_PL_PAGE_IN_EXECUTED=0",flush=True)
        print("P07_B4L_TRAINED_INFERENCE_EXECUTED=0",flush=True)
        return independent
    finally:
        print("P07_B4L_REBOOT_REQUIRED=1",flush=True)
        print("REBOOT KV260; NEVER resume halted Linux.",flush=True)


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    p.add_argument("--frozen-dir",type=Path,required=True)
    p.add_argument("--staged-dir",type=Path,required=True)
    p.add_argument("--reports",type=Path)
    p.add_argument("--evidence",type=Path)
    for flag in APPROVALS:
        p.add_argument("--"+flag.replace("_","-"),choices=("NO","YES"),default="NO")
    a=p.parse_args()
    try:
        index=prepare_verified_contexts(a.frozen_dir,a.staged_dir)
        print("P07_B4L_REAL_27_CONTEXT_HOST_BUNDLE_PREFLIGHT_PASS=1",flush=True)
        if a.mode=="preflight":
            print("P07_B4L_OFFLINE_ONLY_NO_BOARD_ACCESS=1")
            print("P07_B4L_PHYSICAL_DDR_STAGED=0")
            print("P07_B4L_TRAINED_INFERENCE_EXECUTED=0")
            return 0
        if a.reports is None:
            raise DeployError("NO-GO: --reports required for physical accepted P03 PL programming")
        run_physical(a,index)
        return 0
    except (DeployError,ValueError,OSError,RuntimeError,KeyError,TypeError) as e:
        print("P07_B4L_NO_GO="+str(e),file=sys.stderr,flush=True)
        return 3


if __name__=="__main__":
    raise SystemExit(main())
