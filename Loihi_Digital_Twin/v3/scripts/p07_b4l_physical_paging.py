#!/usr/bin/env python3
"""P07-B.4l integrated real 27-core DDR staging + standalone PL paging pilot.

DEFAULT preflight is read-only PC work. Execute mode overwrites Linux-owned
DDR, resets A53, runs the REAL P03 page engine (28 ins/1 dirty out),
and verifies a 256-byte mailbox. A new dedicated JTAG session, never live
Linux. No handwritten operator note, no neural inference, no official TEST.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import p07_b4i_physical_pilot as b4i
import p07_b4j_shell_program_pilot as b4j
import p07_b4l_physical_model_deploy as deploy

TCL="vivado/p07_b4l_xsdb_page_probe_run.tcl"
ELF_ID="P07_B4L_A53_27CORE_PAGING_PROBE_V1"
ELF_MAX_EXCLUSIVE=0x29D80  # SHA-matched historically working Track A A53 LOAD.
APPROVALS=(
    "dedicated_jtag_owner","cpu_takeover_approved",
    "low_ddr_destructive_overwrite_approved",
    "ddr_27core_overwrite_approved","mailbox_overwrite_approved",
    "diagnostic_state_mutation_approved",
    "firmware_coexistence_risk_acknowledged",
    "pl_program_approved","reboot_recovery_approved",
)


class PagingAdmissionError(ValueError):
    pass


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1<<20),b""):
            h.update(part)
    return h.hexdigest()


def admit_real_elf(elf:Path,expected_sha:str)->dict:
    if (not elf.is_absolute() or elf.is_symlink() or not elf.is_file()
            or not re.fullmatch(r"[0-9a-f]{64}",expected_sha)):
        raise PagingAdmissionError("NO-GO: real absolute ELF and 64-hex SHA required")
    if sha(elf)!=expected_sha or ELF_ID.encode() not in elf.read_bytes():
        raise PagingAdmissionError("NO-GO: genuine B4l Vitis paging ELF SHA/identity mismatch")
    exe=shutil.which("aarch64-none-elf-readelf")
    if exe is None:
        raise PagingAdmissionError("NO-GO: source Vitis 2025.2 readelf first")
    run=subprocess.run([exe,"-W","-h","-l",str(elf)],
                       capture_output=True,text=True,timeout=45)
    if run.returncode or "Machine:                           AArch64" not in run.stdout:
        raise PagingAdmissionError("NO-GO: genuine ELF64 AArch64 header inspection failed")
    found=re.search(r"Entry point address:\s+(0x[0-9a-fA-F]+)",run.stdout)
    if not found or int(found.group(1),16)!=0:
        raise PagingAdmissionError("NO-GO: candidate does not use accepted standalone entry 0")
    loads=[]
    for line in run.stdout.splitlines():
        fields=line.split()
        if fields and fields[0]=="LOAD":
            if len(fields)<7: raise PagingAdmissionError("NO-GO: malformed PT_LOAD")
            loads.append((int(fields[3],16),int(fields[5],16)))
    if (len(loads)!=1 or loads[0][0]!=0
            or not 0<loads[0][1]<=ELF_MAX_EXCLUSIVE):
        raise PagingAdmissionError("NO-GO: ELF physical PT_LOAD exceeds verified Track A low-DDR envelope")
    # Real locally emitted map from this same Vitis build, not a synthetic map.
    mapfile=elf.with_suffix(".map")
    if not mapfile.is_file() or mapfile.is_symlink():
        raise PagingAdmissionError("NO-GO: actual paging ELF linker map missing")
    maptext=mapfile.read_text(errors="replace")
    if ("Linker script and memory map" not in maptext
            or ".text" not in maptext or ".bss" not in maptext
            or "main" not in maptext):
        raise PagingAdmissionError("NO-GO: paging ELF genuine GNU linker map invalid")
    return {"elf_sha256":expected_sha,"map_sha256":sha(mapfile),
            "entry":0,"load_start":0,"load_end_exclusive":loads[0][1],
            "size_bytes":elf.stat().st_size}


def preflight(a:argparse.Namespace)->tuple[dict,dict]:
    index=deploy.prepare_verified_contexts(a.frozen_dir,a.staged_dir)
    # Original accepted B4i P03 build preflight independently pins XSA,
    # routed 128-bit FPD, BIT and LTX. B4l uses precisely these artifacts.
    b4i.preflight(a.b4i_build,a.reports)
    elf=admit_real_elf(a.elf,a.expected_elf_sha)
    return index,elf


def check_execute(a:argparse.Namespace)->None:
    for flag in APPROVALS:
        if getattr(a,flag)!="YES":
            raise PagingAdmissionError("NO-GO: missing --"+flag.replace("_","-")+" YES")
    if (a.evidence is None or not a.evidence.is_absolute()
            or a.evidence.is_symlink() or a.evidence.exists()
            or a.evidence.resolve().is_relative_to(b4i.ROOT)
            or not a.evidence.parent.is_dir()):
        raise PagingAdmissionError("NO-GO: require NEW absolute evidence directory outside Thesis")
    for command in ("xsdb","vivado"):
        if shutil.which(command) is None:
            raise PagingAdmissionError("NO-GO: missing hardware tool "+command)


def run_hardware(a:argparse.Namespace,index:dict,real_elf:dict)->None:
    check_execute(a)
    out=a.evidence
    out.mkdir(mode=0o700,exist_ok=False)
    (out/"stage.txt").write_text("SAME_SESSION_UNSTARTED_REBOOT_AFTER_ATTEMPT\n")
    (out/"manifest.json").write_text(json.dumps({
        "milestone":"P07-B.4l","scope":"REAL_PL_PAGE_IN_DIRTY_OUT_NO_INFERENCE",
        "original_frozen_bundle_sha256":deploy.ACCEPTED_BUNDLE_SHA,
        "paging_elf":real_elf,
        "ddr_destination":"[0x40000000,0x40D80000)",
        "low_ddr_exclusivity_proven":False,
        "mailbox":"[0x43FF0000,0x43FF0100)",
        "diagnostic_dirty_core0_word_mask":"0x00000100",
        "reboot_required":True,
    },indent=2,sort_keys=True)+"\n")
    print("P07_B4L_LOW_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0",flush=True)
    try:
        deploy.prep_transfer_files(a.staged_dir,out/"transfer_inputs",index)
        (out/"physical_readback").mkdir(mode=0o700)
        (out/"stage.txt").write_text("INPUTS_PREPARED_A53_TAKEOVER_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call(["xsdb",b4j.TAKEOVER_TCL,"DEDICATED_DISCARD_LINUX_APPROVED",
                      "tcp:127.0.0.1:3121"],out/"ps_width.log")
        b4i.verify_takeover_log((out/"ps_width.log").read_text())
        print("P07_B4L_REAL_PS_FPD128_LPD128_PASS=1",flush=True)
        (out/"stage.txt").write_text("A53_HALTED_PL_PROGRAM_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call(["vivado","-mode","batch","-source",b4j.PROGRAM_TCL,"-tclargs",
                      str(a.reports/"p03_2_ps_mmio.bit"),
                      str(a.reports/"p03_2_ps_mmio.ltx"),"localhost:3121"],out/"program.log")
        b4j.require_programmed_shell((out/"program.log").read_text())
        print("P07_B4L_REAL_ACCEPTED_P03_PROGRAM_PASS=1",flush=True)
        (out/"stage.txt").write_text("PL_PASS_DDR_27_STAGE_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call(["xsdb",deploy.CORE_TCL,"DEDICATED_27_DDR_OVERWRITE_APPROVED",
                      str(out/"transfer_inputs"),str(out/"physical_readback"),
                      "tcp:127.0.0.1:3121"],out/"ddr_stage.log")
        lines=(out/"ddr_stage.log").read_text().splitlines()
        if (lines.count("P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1")!=1
                or any(lines.count(f"P07_B4L_CORE_{i}_512K_PHYSICAL_READBACK_PASS=1")!=1
                       for i in range(27))):
            raise PagingAdmissionError("NO-GO: full same-session DDR Tcl stage proof missing")
        independent=deploy.verify_physical_readback(
            a.staged_dir,out/"physical_readback",index)
        (out/"ddr_verified.json").write_text(json.dumps(independent,indent=2)+"\n")
        print("P07_B4L_SAME_SESSION_PHYSICAL_DDR_27_CORE_PASS=1",flush=True)
        (out/"stage.txt").write_text("ALL_27_DDR_VERIFIED_A53_PAGE_PROBE_PENDING_REBOOT_REQUIRED\n")
        # Final ELF identity rechecked immediately before destructive download.
        if sha(a.elf)!=real_elf["elf_sha256"]:
            raise PagingAdmissionError("NO-GO: ELF changed since preflight")
        (out/"mailbox_zero_256.bin").write_bytes(bytes(256))
        raw=out/"paging_mailbox_256.bin"
        b4i.log_call(["xsdb",TCL,"B4L_SAME_SESSION_27_DDR_EXCLUSIVE_OPERATOR_APPROVED",
                      str(a.elf),str(out/"mailbox_zero_256.bin"),str(raw),
                      "tcp:127.0.0.1:3121"],out/"a53_page_probe.log")
        lines=(out/"a53_page_probe.log").read_text().splitlines()
        if (lines.count("P07_B4L_A53_PAGING_ELF_DOWNLOADED=1")!=1 or
                lines.count("P07_B4L_PAGE_PROBE_MAILBOX_CAPTURED_256_BYTES=1")!=1 or
                lines.count("P07_B4L_A53_PAGING_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1")!=1):
            raise PagingAdmissionError("NO-GO: actual A53 paging/memory capture markers missing")
        if not raw.is_file() or raw.stat().st_size!=256:
            raise PagingAdmissionError("NO-GO: real A53 256-byte paging mailbox absent")
        (out/"stage.txt").write_text("A53_PAGING_MAILBOX_CAPTURED_VERIFY_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call([sys.executable,"scripts/p07_b4l_verify_page_probe.py",
                      "--mailbox",str(raw)],out/"verify.log")
        if (out/"verify.log").read_text().splitlines().count(
                "P07_B4L_PHYSICAL_27_CORE_3_SLOT_PAGE_DIRTY_SAVE_VERIFIED=1")!=1:
            raise PagingAdmissionError("NO-GO: independent real page probe mailbox verification failed")
        (out/"stage.txt").write_text("REAL_A53_27_CORE_THREE_SLOT_PAGE_DIRTY_SAVE_PASS_REBOOT_REQUIRED\n")
        print("P07_B4L_REAL_A53_27_CORE_3_SLOT_PAGE_DIRTY_SAVE_PASS=1",flush=True)
        print("P07_B4L_TRAINED_NEURAL_INFERENCE_EXECUTED=0",flush=True)
    finally:
        print("P07_B4L_REBOOT_REQUIRED=1",flush=True)
        print("REBOOT KV260; never resume halted Linux.",flush=True)


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    for key in ("frozen-dir","staged-dir","reports","b4i-build","elf"):
        p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--expected-elf-sha",required=True)
    p.add_argument("--evidence",type=Path)
    for flag in APPROVALS:
        p.add_argument("--"+flag.replace("_","-"),choices=("NO","YES"),default="NO")
    a=p.parse_args()
    try:
        index,real_elf=preflight(a)
        print("P07_B4L_REAL_PAGING_ELF_SOURCE_DDR_P03_OFFLINE_PREFLIGHT_PASS=1")
        print("P07_B4L_REAL_PAGING_ELF_BOUNDS="+json.dumps(real_elf,sort_keys=True))
        if a.mode=="preflight":
            print("P07_B4L_PAGE_PROBE_OFFLINE_ONLY_NO_BOARD_ACCESS=1")
            print("P07_B4L_PHYSICAL_PAGING_EXECUTED=0")
            return 0
        run_hardware(a,index,real_elf)
        return 0
    except (PagingAdmissionError,ValueError,OSError,RuntimeError,
            subprocess.TimeoutExpired,KeyError,TypeError) as exc:
        print("P07_B4L_REAL_PAGING_NO_GO="+str(exc),file=sys.stderr,flush=True)
        return 3


if __name__=="__main__":
    raise SystemExit(main())
