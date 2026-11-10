#!/usr/bin/env python3
"""M06 existing G4: fail-closed original-Vivado owner ZIP *artifact* audit.

This validates evidence integrity and logs, not a substitute for observing
real Vivado run or independently auditing original AMD/HLS waveforms. It is
read-only: does not mutate owner evidence, generated HLS RTL, IP or .xci.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import sys
from zipfile import ZipFile, BadZipFile

GATES = {
    "g4_first_b_slverr": (
        "M06_G4_ACTUAL_HLS_AMD_FIRST_B_SLVERR_QUARANTINE_XSIM_PASS",
        "tb_m06_g4_actual_hls_original_amd_first_b_slverr.sv",
        "03_g4_first_b_fault_generation.log",
        16),
    "g4_first_r_slverr": (
        "M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS",
        "tb_m06_g4_actual_hls_original_amd_first_r_slverr.sv",
        "03_g4_first_r_slverr_generation.log",
        19),
    "g4_stalled_b": (
        "M06_G4_ACTUAL_HLS_AMD_STALLED_B_WATCHDOG_QUARANTINE_XSIM_PASS",
        "tb_m06_g4_actual_hls_original_amd_stalled_b.sv",
        "03_g4_stalled_b_generation.log",
        19),
    "g4_discard_restore": (
        "M06_G4_ACTUAL_HLS_AMD_FAULT_DISCARD_RESTORE_CLEAN_COMMIT_XSIM_PASS",
        "tb_m06_g4_actual_hls_original_amd_discard_restore.sv",
        "03_g4_discard_restore_generation.log",
        20),
}
INTEGRITY = (
    ("source_before_sha256.txt","source_after_sha256.txt"),
    ("hls_sources_before_sha256.txt","hls_sources_after_sha256.txt"),
    ("hls_dat_sources_before_sha256.txt","hls_dat_sources_after_sha256.txt"),
    ("vendor_sha_before.txt","vendor_sha_after.txt"),
)
COUNTS=(40,14,67)
REQUIRED_LOGS=(
    "01_reaudit_dwc_owner.log","02_vendor_plan.log","03_merge_plan.log",
    "03_hls_original_dat_stage.log","03_control_map.log","03_generation.log",
    "04_xvhdl.log","05_xvlog.log","06_xelab.log","07_xsim.log",
    "08_operator_invocation_console.log",
)
VIVADO_STAGES=(
    "04_xvhdl.log","05_xvlog.log","06_xelab.log","07_xsim.log",
)
# Original G3/4 offline XSim yields known warnings in xelab only; never
# waive a new unexpected warning.
KNOWN_ELAB_WARNINGS=(
    "WARNING: [XSIM 43-3431]",
    "WARNING: [VRFC 10-5021] port 'mb_reset'",
    "WARNING: [VRFC 10-5021] port 'aclk2x'",
)

def reject(condition: bool,message: str) -> None:
    if not condition:
        raise ValueError(message)

def check_zip(path:Path,mode:str) -> dict[str,object]:
    reject(mode in GATES,"unknown G4 owner gate")
    marker,tb,generator,min_local=GATES[mode]
    reject(path.is_file(),"owner ZIP not found")
    with ZipFile(path,"r") as z:
        names=z.namelist()
        reject(len(names)==len(set(names)),"duplicate ZIP members")
        reject(all(n and not n.startswith("/") and
                   ".." not in Path(n).parts and
                   not n.endswith((".xci",".dat",".v",".bit")) for n in names),
               "original proprietary IP or unsafe ZIP path")
        needed={"result.txt","commit.txt","original_xci_after_sha_check.txt",
                "generated_hls_link_tb_sha256.txt",tb,generator,
                *REQUIRED_LOGS}
        for a,b in INTEGRITY:
            needed.update((a,b))
        reject(needed.issubset(names),
               "missing required first-owner logs/source manifests: "+
               ", ".join(sorted(needed-set(names))))
        read=lambda name:z.read(name).decode("utf-8",errors="replace")
        reject(read("result.txt").strip()=="exit_status=0",
               "owner result does not show exit_status=0")
        commit=read("commit.txt").strip()
        reject(re.fullmatch(r"[0-9a-f]{40}",commit) is not None,
               "invalid owner git commit identity")
        for n,(a,b) in enumerate(INTEGRITY):
            reject(z.read(a)==z.read(b),
                   "original/local source mutation: "+a)
            lines=read(a).strip().splitlines()
            expect=min_local if n==0 else COUNTS[n-1]
            reject(len(lines)==expect,
                   "unexpected original/local source file count: "+a)
            reject(all(re.fullmatch(r"[0-9a-f]{64}  \S+",ln) for ln in lines),
                   "bad source digest/manifest format: "+a)
        # The archive records only after-XCI checks (against immutable
        # owner inventory). Two AMD DWCs must both pass SHA.
        xci=read("original_xci_after_sha_check.txt").strip().splitlines()
        reject(len(xci)==2 and
               all(".xci: OK" in ln for ln in xci) and
               any("read_dwc" in ln for ln in xci) and
               any("write_dwc" in ln for ln in xci),
               "real AMD dual DWC XCI identity check failed")
        invocation=read("08_operator_invocation_console.log")
        for stage in (
            "01_reaudit_dwc_owner.log","02_vendor_plan.log",
            "03_merge_plan.log","03_hls_original_dat_stage.log",
            "03_control_map.log","03_generation.log",generator,
            *VIVADO_STAGES
        ):
            reject("OWNER_STAGE "+stage+" rc 0" in invocation,
                   "original owner stage failed/missing: "+stage)
        reject("M06_G3_3_1_OWNER_EVIDENCE" in invocation and
               "exit=0" in invocation and "FAILED" not in invocation,
               "owner invocation does not confirm clean completion")
        rtl=read("05_xvlog.log")
        reject("ERROR:" not in rtl and "WARNING:" not in rtl and
               "analyzing module" in rtl,
               "original xvlog warnings/errors not accepted")
        elaboration=read("06_xelab.log")
        reject("Built simulation snapshot" in elaboration and
               not re.search(r"ERROR:|FATAL:",elaboration),
               "genuine owner xelab did not complete cleanly")
        elab_warn=[ln.strip() for ln in elaboration.splitlines()
                   if ln.lstrip().startswith("WARNING:")]
        reject(len(elab_warn)==4 and
               all(any(w in ln for w in KNOWN_ELAB_WARNINGS)
                   for ln in elab_warn),
               "new or missing original elaboration warning, audit manually")
        xsim=read("07_xsim.log")
        reject(xsim.count(marker)==1 and
               "$finish called at time" in xsim and
               "exit 0" in xsim and
               "INFO: [Common 17-206] Exiting xsim" in xsim and
               not re.search(r"FATAL|Fatal:|ERROR:|M06_G4_FAIL",xsim),
               "missing genuine clean mode-specific original XSim PASS")
        reject("NO_DDR_NO_BOARD" in xsim,
               "scope declaration missing from G4 first-owner marker")
        reject("SOURCE_ONLY" in read(generator),
               "source-only generator stage identity missing")
        return {
            "mode":mode,"commit":commit,"zip_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode_pass":marker,"owner_result":"exit_status=0",
            "original_hls_rtl_count":COUNTS[0],"original_hls_dat_count":COUNTS[1],
            "original_amd_rtl_count":COUNTS[2],
            "local_source_count":min_local,
            "original_xci_count":2,"xelab_warnings":4,
            "no_physical_ddr_board":True,
        }

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode",choices=tuple(GATES),required=True)
    ap.add_argument("--zip",required=True,type=Path)
    a=ap.parse_args()
    try:
        report=check_zip(a.zip,a.mode)
    except (OSError,ValueError,BadZipFile,KeyError) as exc:
        print("M06_G4_OWNER_ZIP_AUDIT_REJECTED:",exc,file=sys.stderr)
        return 2
    print("M06_G4_ORIGINAL_VIVADO_OWNER_ZIP_AUDIT_PASS",
          "mode="+a.mode,"commit="+str(report["commit"]),
          "SHA256="+str(report["zip_sha256"]),
          "ARTIFACT_ONLY_NO_DDR_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
