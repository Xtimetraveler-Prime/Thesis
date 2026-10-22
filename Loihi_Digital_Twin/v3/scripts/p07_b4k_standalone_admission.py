#!/usr/bin/env python3
"""P07-B.4k: guarded first REAL standalone A53 read-only admission.

Default OFFLINE, no board actions. Physical execution is an intentional
DESTRUCTIVE JTAG takeover of the former Linux A53 context and low DDR.
This reuses verified P07-B.4i ELF, accepted P03 programmer, strict B4i
A53/FPD128/LPD128 gate and independent P07-B.4i mailbox verifier.
NEVER run while retaining Linux or its DDR contents. Power-cycle afterward.
B4k does NOT execute 27-core trained B2 inference.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import p07_b4i_physical_pilot as b4i
import p07_b4j_shell_program_pilot as b4j

ELF_SHA = "5fcdb0586564f3abef477804a54e0a87163c74654f9d15d1f9600ab2cb85e807"
MAP_SHA = "4deb41d9f47bd397ced6a15027b83b74f1d689f25220088bce62e5d2363551ad"
PT_LOAD = [(0, 0x23A40)]
MBOX = 0x43FF0000
MBOX_SIZE = 64

# A specific, explicit *destructive overwrite consent*, NOT a false
# assertion that Linux/TF-A/firmware low-DDR exclusivity has been measured.
APPROVALS = (
    "dedicated_jtag_owner",
    "cpu_takeover_approved",
    "low_ddr_destructive_overwrite_approved",
    "firmware_coexistence_risk_acknowledged",
    "mailbox_overwrite_approved",
    "pl_program_approved",
    "reboot_recovery_approved",
)


def offline_manifest(build:Path,reports:Path)->dict:
    report=b4i.preflight(build,reports)
    if report["entry"]!=0 or report["loads"]!=PT_LOAD:
        raise ValueError("NO-GO: actual ELF entry/PT_LOAD differs from accepted local B4i")
    if report["sha256"]["elf"]!=ELF_SHA or report["sha256"]["map"]!=MAP_SHA:
        raise ValueError("NO-GO: accepted B4i ELF/map SHA drift")
    start,end=PT_LOAD[0]
    if end>0x100000 or start!=0:
        raise ValueError("NO-GO: physical low-DDR ELF bounds drift")
    if not (end<=MBOX or MBOX+MBOX_SIZE<=start):
        raise ValueError("NO-GO: mailbox intersects A53 load span")
    if not (0x40000000<=MBOX and MBOX+MBOX_SIZE<=0x44000000):
        raise ValueError("NO-GO: unexpected historical mailbox address")
    if not (end<=0x40000000):
        raise ValueError("NO-GO: protected 64MiB P02 training DDR overlap")
    return report


def validate_execution_inputs(args:argparse.Namespace)->None:
    for flag in APPROVALS:
        if getattr(args,flag)!="YES":
            raise ValueError("NO-GO: explicit "+flag.replace("_","-")+" YES required")
    evidence=args.evidence
    if (evidence is None or not evidence.is_absolute() or evidence.exists()
            or evidence.is_symlink() or evidence.is_relative_to(b4i.ROOT)):
        raise ValueError("NO-GO: evidence must be a new absolute path outside Thesis")
    for name in ("xsdb","vivado"):
        if shutil.which(name) is None:
            raise ValueError("NO-GO: required hardware tool missing: "+name)
    if args.reports.is_symlink() or not args.reports.is_dir():
        raise ValueError("NO-GO: missing accepted P03 routed artifact directory")


def run_physical(args:argparse.Namespace,report:dict)->None:
    validate_execution_inputs(args)
    evidence=args.evidence
    evidence.mkdir(parents=True,exist_ok=False)
    identity={
        "milestone":"P07-B.4k",
        "state":"BOARD_ATTEMPT_STARTED_NOT_VERIFIED",
        "actual_candidate_sha256":report["sha256"],
        "elf_entry":report["entry"],
        "physical_loads":report["loads"],
        "mailbox_addr":hex(MBOX),
        "mailbox_size":MBOX_SIZE,
        "accepted_risk":"Linux/firmware low-DDR ownership is NOT independently verified. "
                        "Explicit destructive overwrite approval is NOT such verification.",
        "scope":"Read-only P03 shell admission ONLY; NO trained B2 inference",
        "reboot_required":True,
    }
    (evidence/"manifest.json").write_text(json.dumps(identity,indent=2)+"\n")
    (evidence/"stage.txt").write_text("BOARD_ATTEMPT_STARTED_REBOOT_REQUIRED\n")
    print("P07_B4K_PHYSICAL_INTENTIONAL_LINUX_AND_LOW_DDR_TAKEOVER=1",flush=True)
    print("P07_B4K_LOW_DDR_EXCLUSIVE_OWNERSHIP_PROVEN=0",flush=True)
    try:
        # B4j was physically accepted on 2026-10-22. Repeat its controls
        # after a FRESH REBOOT: no stale fabric/suspended Linux reuse.
        b4i.log_call([
            "xsdb",b4j.TAKEOVER_TCL,"DEDICATED_DISCARD_LINUX_APPROVED",
            "tcp:127.0.0.1:3121"
        ],evidence/"ps_width.log")
        states=b4i.verify_takeover_log((evidence/"ps_width.log").read_text())
        print("P07_B4K_REAL_A53_ACCOUNTING="+repr(states),flush=True)
        print("P07_B4K_REAL_PS_FPD128_LPD128_PASS=1",flush=True)
        (evidence/"stage.txt").write_text("TAKEOVER_WIDTH_PASS_PROGRAM_PENDING_REBOOT_REQUIRED\n")

        b4i.log_call([
            "vivado","-mode","batch","-source",b4j.PROGRAM_TCL,"-tclargs",
            str(args.reports/"p03_2_ps_mmio.bit"),
            str(args.reports/"p03_2_ps_mmio.ltx"),
            "localhost:3121"
        ],evidence/"program.log")
        b4j.require_programmed_shell((evidence/"program.log").read_text())
        print("P07_B4K_REAL_ACCEPTED_P03_PROGRAM_VIO_RESET_PASS=1",flush=True)
        (evidence/"stage.txt").write_text("PL_PROGRAM_PASS_A53_ELF_PENDING_REBOOT_REQUIRED\n")

        # Intentional data-area overwrite: just the 64-byte mailbox.
        # Plus: executable's physical [0x0,0x23A40) PT_LOAD overwritten
        # by the unchanged accepted P07-B.4i XSDB Tcl.
        zeros=evidence/"mailbox_zero_64.bin"
        zeros.write_bytes(bytes(MBOX_SIZE))
        raw=evidence/"p07_b4k_mailbox_64.bin"
        elf=args.build/"vitis_workspace/p07_b4i_mailbox_probe.elf"
        b4i.log_call([
            "xsdb","vivado/p07_b4i_xsdb_run.tcl",
            "DEDICATED_A53_DDR_OWNER_VERIFIED",
            str(elf),str(zeros),str(raw),"tcp:127.0.0.1:3121"
        ],evidence/"a53_run.log")
        (evidence/"stage.txt").write_text("A53_COMPLETED_MAILBOX_PENDING_VERIFICATION_REBOOT_REQUIRED\n")
        if not raw.is_file() or raw.stat().st_size!=MBOX_SIZE:
            raise ValueError("NO-GO: real DDR 64-byte mailbox not captured")
        b4i.log_call([
            sys.executable,"scripts/p07_b4i_verify_mailbox.py","--mailbox",str(raw)
        ],evidence/"verify.log")
        if (evidence/"verify.log").read_text().splitlines().count(
                "P07_B4I_PHYSICAL_READONLY_ADMISSION_PASS=1")!=1:
            raise ValueError("NO-GO: independent strict mailbox verifier did not PASS")
        (evidence/"stage.txt").write_text("P07_B4K_STANDALONE_ADMISSION_VERIFIED_REBOOT_REQUIRED\n")
        print("P07_B4K_REAL_STANDALONE_A53_ADMISSION_PASS=1",flush=True)
        print("P07_B4K_TRAINED_27_CORE_INFERENCE_EXECUTED=0",flush=True)
    finally:
        print("P07_B4K_REBOOT_REQUIRED=1",flush=True)
        print("REBOOT KV260; do not resume the halted Linux instance.",flush=True)


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    p.add_argument("--build",required=True,type=Path)
    p.add_argument("--reports",required=True,type=Path)
    p.add_argument("--evidence",type=Path)
    for flag in APPROVALS:
        p.add_argument("--"+flag.replace("_","-"),choices=("NO","YES"),default="NO")
    args=p.parse_args()
    try:
        report=offline_manifest(args.build,args.reports)
        print("P07_B4K_REAL_ELF_MAP_P03_OFFLINE_PREFLIGHT_PASS=1")
        print("P07_B4K_ELF_PT_LOAD="+repr(report["loads"]))
        if args.mode=="preflight":
            print("P07_B4K_OFFLINE_ONLY_NO_HARDWARE_ACCESS=1")
            print("P07_B4K_PHYSICAL_LAUNCH_AUTHORIZED=0")
            return 0
        run_physical(args,report)
    except (ValueError,OSError,RuntimeError) as exc:
        print("P07_B4K_NO_GO="+str(exc),file=sys.stderr)
        return 3
    return 0


if __name__=="__main__":
    raise SystemExit(main())
