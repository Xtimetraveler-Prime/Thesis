#!/usr/bin/env python3
"""P07-B.4j isolated physical P03 shell PROGRAM+VIO reset checkpoint.

Default OFFLINE: no JTAG, FPGA or A53 accesses.
Physical mode intentionally HALTS all active A53 cores (discards Linux),
then programs ONLY the SHA-pinned accepted P03 BIT/LTX with the original
accepted Vivado/VIO reset-release procedure. No ELF dow, DDR reads/writes,
mailbox, B2 TEST or inference. REBOOT the KV260 after every physical attempt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

import p07_b4i_physical_pilot as b4i

TAKEOVER_TCL = "vivado/p07_b4i_stop_and_width_gate.tcl"
PROGRAM_TCL = "vivado/p03_2c_program_bitstream.tcl"
PASS_MARKER = "PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released"
APPROVAL_FLAGS = (
    "dedicated_jtag_owner", "cpu_takeover_approved",
    "pl_program_approved", "reboot_recovery_approved",
)

def validate_evidence_inputs(args:argparse.Namespace)->None:
    # Require a fresh out-of-tree evidence destination and four independently
    # confirmed hardware approvals. No operator-authored note is required.
    for name in APPROVAL_FLAGS:
        if getattr(args,name) != "YES":
            raise ValueError("NO-GO: missing explicit "+name+"=YES")
    evidence = args.evidence
    if (evidence is None or not evidence.is_absolute() or evidence.exists()
            or evidence.is_symlink() or evidence.is_relative_to(b4i.ROOT)):
        raise ValueError("NO-GO: evidence must be a NEW absolute directory outside Thesis")
    if args.reports.is_symlink() or not args.reports.is_dir():
        raise ValueError("NO-GO: physical accepted reports path missing")

def require_programmed_shell(log:str)->None:
    if log.splitlines().count(PASS_MARKER)!=1:
        raise ValueError("NO-GO: missing or repeated accepted P03 PL program/VIO reset release marker")
    # 'error' in Vivado logs may include harmless internal diagnostics;
    # strict success marker + nonzero exit fail-closed are authoritative.

def execute(args:argparse.Namespace,manifest:dict)->None:
    validate_evidence_inputs(args)
    for name in ("xsdb","vivado"):
        if shutil.which(name) is None:
            raise ValueError("NO-GO: Xilinx tool unavailable: "+name)
    if manifest["entry"]!=0 or manifest["loads"]!=[(0,145984)]:
        raise ValueError("NO-GO: unexpected B4i ELF layout compared to independent physical evidence")
    if manifest["sha256"]["elf"]!="5fcdb0586564f3abef477804a54e0a87163c74654f9d15d1f9600ab2cb85e807":
        raise ValueError("NO-GO: different locally verified B4i ELF")
    if manifest["sha256"]["map"]!="4deb41d9f47bd397ced6a15027b83b74f1d689f25220088bce62e5d2363551ad":
        raise ValueError("NO-GO: different locally verified genuine B4i map")

    out=args.evidence
    out.mkdir(parents=True,exist_ok=False)
    (out/"provenance.json").write_text(json.dumps({
        "milestone":"P07-B.4j","status":"BOARD_ATTEMPT_NOT_YET_VERIFIED",
        "intent":"A53 halt + FPD128/LPD128 gate + accepted P03 PL programming / VIO reset ONLY",
        "no_ddr_access":True,"no_elf_download":True,"no_inference":True,
        "reboot_required":True,"artifact_sha256":manifest["sha256"],
        "elf_entry":hex(manifest["entry"]),"elf_loads":manifest["loads"],
    },indent=2)+"\n")
    try:
        # First operation on hardware. Stops Linux and MUST be followed
        # by reboot regardless of test success or failure.
        b4i.log_call([
            "xsdb",TAKEOVER_TCL,"DEDICATED_DISCARD_LINUX_APPROVED",
            "tcp:127.0.0.1:3121"
        ],out/"ps_width.log")
        states=b4i.verify_takeover_log((out/"ps_width.log").read_text())
        print("P07_B4J_VERIFIED_REAL_TAKEOVER_STATES="+repr(states))
        print("P07_B4J_STOP_WIDTH_GATE_PASS=1")
        b4i.log_call([
            "vivado","-mode","batch","-source",PROGRAM_TCL,"-tclargs",
            str(args.reports/"p03_2_ps_mmio.bit"),
            str(args.reports/"p03_2_ps_mmio.ltx"),"localhost:3121"
        ],out/"program.log")
        require_programmed_shell((out/"program.log").read_text())
        (out/"result.txt").write_text(
            "P07_B4J_PHYSICAL_SHELL_PROGRAM_VIO_RESET_PASS=1\n"
            "P07_B4J_A53_ELF_DOWNLOADED=0\n"
            "P07_B4J_DDR_MAILBOX_TOUCHED=0\n"
            "P07_B4J_TRAINED_INFERENCE_RUN=0\n"
            "P07_B4J_REBOOT_REQUIRED=1\n"
        )
        print((out/"result.txt").read_text(),end="")
    finally:
        print("P07_B4J_REBOOT_REQUIRED=1")
        print("REBOOT KV260; NEVER resume the halted Linux instance.")

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    p.add_argument("--build",required=True,type=Path)
    p.add_argument("--reports",required=True,type=Path)
    p.add_argument("--evidence",type=Path)
    for name in APPROVAL_FLAGS:
        p.add_argument("--"+name.replace("_","-"),choices=("NO","YES"),default="NO")
    args=p.parse_args()
    try:
        manifest=b4i.preflight(args.build,args.reports)
        if (manifest["sha256"]["elf"]!="5fcdb0586564f3abef477804a54e0a87163c74654f9d15d1f9600ab2cb85e807"
                or manifest["sha256"]["map"]!="4deb41d9f47bd397ced6a15027b83b74f1d689f25220088bce62e5d2363551ad"):
            raise ValueError("NO-GO: B4j requires the user-verified B4i ELF/map identity")
        print("P07_B4J_OFFLINE_ACCEPTED_P03_B4I_ARTIFACT_PREFLIGHT_PASS=1")
        if args.mode=="preflight":
            print("P07_B4J_OFFLINE_ONLY_NO_HARDWARE_ACCESS=1")
            print("P07_B4J_A53_DDR_ELF_INFERENCE_AUTHORIZED=0")
            return 0
        execute(args,manifest)
    except (ValueError,OSError,RuntimeError) as exc:
        print("P07_B4J_NO_GO="+str(exc),file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
