#!/usr/bin/env python3
"""P07-B.4i Track-A-derived A53 mailbox pilot. Default OFFLINE ONLY.

Physical mode is destructive and separately operator approved. It halts A53,
overwrites low-DDR ELF PT_LOAD plus 64 mailbox bytes, programs accepted P03 PL,
and never resumes the old Linux instance. NEVER run while Linux owns memory.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

V3=Path(__file__).resolve().parents[1]
ROOT=V3.parents[1]
EXPECTED_SHA={
    "p03_2_ps_mmio.xsa":"52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f",
    "p03_2_ps_mmio.bit":"beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4",
    "p03_2_ps_mmio.ltx":"31f5771432ffb8c72b35a55e1ef7e88e9d96d406fe8cb306733df474df360238",
}
IDENTITY=b"P07_B4I_A53_MAILBOX_FPD128_PROBE_V1"
REQUIRED_METRICS=(
    "p03_hpm0_data_width_bits=128",
    "p03_hpm0_transport=smartconnect_width_protocol",
    "p03_mmio_slave_data_width_bits=32",
    "p03_ps_mmio_master=FPD",
    "p03_mmio_base=0xA4000000",
)
REQUIRED_SOURCE={
    "p07_b4i_readonly_mailbox_board.c":"software/p07/p07_b4i_readonly_mailbox_board.c",
    "p07_b4b_board_admission.c":"software/p07/p07_b4b_board_admission.c",
    "p07_b4b_xilinx_platform.c":"software/p07/p07_b4b_xilinx_platform.c",
    "p03_hw_adapter.c":"software/p03/p03_hw_adapter.c",
    "p03_hw_xilinx_io.c":"software/p03/p03_hw_xilinx_io.c",
    "p07_b4b_board_admission.h":"software/p07/include/p07_b4b_board_admission.h",
    "p07_b4b_xilinx_platform.h":"software/p07/include/p07_b4b_xilinx_platform.h",
    "p07_b4a_current_ingress.h":"software/p07/include/p07_b4a_current_ingress.h",
    "p07_b2_ingress.h":"software/p07/include/p07_b2_ingress.h",
    "p07_b3_pager.h":"software/p07/include/p07_b3_pager.h",
    "p03_hw_adapter.h":"software/p03/include/p03_hw_adapter.h",
    "p03_hw_xilinx_io.h":"software/p03/include/p03_hw_xilinx_io.h",
    "p03_runtime.h":"software/p03/include/p03_runtime.h",
    "p03_mmio.h":"software/p03/include/p03_mmio.h",
}

def sha256(path:Path)->str:
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        raise ValueError("missing, empty or symlinked input: "+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_layout(text:str)->tuple[int,list[tuple[int,int]]]:
    match=re.search(r"Entry point address:\s*(0x[0-9a-fA-F]+)",text)
    if not match:
        raise ValueError("no actual readelf entry point")
    spans=[]
    for line in text.splitlines():
        cols=line.split()
        if cols and cols[0]=="LOAD" and len(cols)>=7:
            start=int(cols[3],16) # readelf -W -l: physical address
            length=int(cols[5],16) # MemSiz, not FileSiz
            if length<=0:
                raise ValueError("zero-sized PT_LOAD")
            spans.append((start,start+length))
    entry=int(match.group(1),16)
    if not spans or not any(lo<=entry<hi for lo,hi in spans):
        raise ValueError("ELF entry not in any physical PT_LOAD")
    for lo,hi in spans:
        if lo<0x44000000 and hi>0x40000000:
            raise ValueError("ELF overlaps protected P02 64MiB DDR")
        if lo<0xA4001000 and hi>0xA4000000:
            raise ValueError("ELF overlaps P03 MMIO")
    return entry,spans

def preflight(build:Path,reports:Path,readelf:str="aarch64-none-elf-readelf",
              nm:str="aarch64-none-elf-nm")->dict:
    if not build.is_dir() or not reports.is_dir():
        raise ValueError("real B4i build and accepted reports are required")
    hashes={}
    for name,expected in EXPECTED_SHA.items():
        path=reports/name
        got=sha256(path)
        if got!=expected: raise ValueError(f"accepted {name} SHA mismatch")
        hashes[name]=got
    metrics=(reports/"p03_2_post_route_metrics.txt").read_text().splitlines()
    for required in REQUIRED_METRICS:
        if required not in metrics:
            raise ValueError("missing accepted FPD128 routed metric "+required)
    staging=build/"source"
    if {p.name for p in staging.iterdir() if p.is_file()}!=set(REQUIRED_SOURCE):
        raise ValueError("B4i source staging file set drift")
    for staged,original in REQUIRED_SOURCE.items():
        if sha256(staging/staged)!=sha256(V3/original):
            raise ValueError("stale or modified source stage "+staged)
    elf=build/"vitis_workspace/p07_b4i_mailbox_probe.elf"
    linkmap=build/"vitis_workspace/p07_b4i_mailbox_probe.map"
    hashes["elf"]=sha256(elf)
    hashes["map"]=sha256(linkmap)
    if IDENTITY not in elf.read_bytes():
        raise ValueError("wrong B4i ELF build identity")
    map_text=linkmap.read_text(errors="replace")
    if not all(k in map_text for k in ("Linker script and memory map",".text",".bss","main")):
        raise ValueError("genuine linker-generated GNU map missing")
    sections=subprocess.run([readelf,"-W","-h","-l","-S",str(elf)],
                            check=True,text=True,capture_output=True).stdout
    entry,spans=parse_layout(sections)
    for section in (".heap",".stack",".bss"):
        if section not in sections:
            raise ValueError("allocated ELF layout lacks "+section)
    names=subprocess.run([nm,str(elf)],check=True,text=True,
                         capture_output=True).stdout
    for symbol in ("main","p07_b4b_probe","p03_hw_init"):
        if not re.search(r"\b"+symbol+r"\b",names):
            raise ValueError("linked ELF missing "+symbol)
    return {"sha256":hashes,"entry":entry,"loads":spans,
            "low_ddr_risk":any(lo<0x100000 and hi>0 for lo,hi in spans)}

def verify_takeover_log(log:str)->dict[int,str]:
    """Fail-closed, exact-line B4i hardware takeover transcript admission.

    Core #0 MUST be positively halted, either by a successful stop,
    exact Already-stopped state, or by a Track-A-style processor-local
    reset followed by successful/exact-already-stopped halt verification.
    The reset fallback is ONLY allowed after both authentic PS128 reads
    and explicit original power-down observations. Secondary cores must
    each be halted OR reported powered down, never both. External XSDB
    exit code 0 is separately enforced by log_call.
    """
    lines=log.splitlines()
    required=(
        "P03_2C_PS_FPD_AXIFS_RAW=0x00000A00",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "P03_2C_PS_LPD_AXIFS_RAW=0x00000200",
        "P03_2C_PS_LPD_HPM0_WIDTH_BITS=128",
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
    )
    for marker in required:
        if lines.count(marker)!=1:
            raise ValueError("NO-GO: missing or duplicate takeover marker: "+marker)
    primary_markers=(
        "P07_B4I_A53_0_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_0_ALREADY_STOPPED_CONFIRMED=1",
        "P07_B4I_A53_0_TRACK_A_RESET_HALT_CONFIRMED=1",
    )
    if sum(lines.count(item) for item in primary_markers)!=1:
        raise ValueError("NO-GO: A53 #0 must have exactly one positively verified halt state")
    if "P07_B4I_A53_0_POWERED_DOWN_OBSERVED=1" in lines:
        raise ValueError("NO-GO: A53 #0 cannot be powered down")
    pending=lines.count("P07_B4I_A53_0_EXACT_POWER_DOWN_RESET_PENDING=1")
    recovered=lines.count(primary_markers[2])
    if pending!=recovered or pending>1:
        raise ValueError("NO-GO: CPU0 reset requires exact power-down observation and verified post-reset halt")
    for attempt in (1,2):
        marker=f"P07_B4I_A53_0_TRANSIENT_POWER_DOWN_RETRY={attempt}"
        count=lines.count(marker)
        if count>1 or (recovered and count!=1):
            raise ValueError("NO-GO: CPU0 power-down retry transcript inconsistent")
    if lines.count("P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1"):
        raise ValueError("NO-GO: width/stop script reported failure")
    observed={0:"halted"}
    for i in range(1,4):
        halted=lines.count(f"P07_B4I_A53_{i}_STOP_COMMAND_PASS=1")
        down=lines.count(f"P07_B4I_A53_{i}_POWERED_DOWN_OBSERVED=1")
        if (halted,down) not in ((1,0),(0,1)):
            raise ValueError(f"NO-GO: ambiguous or missing A53 #{i} state")
        observed[i]="halted" if halted else "powered_down"
    return observed


def log_call(args:list[str],dest:Path)->None:
    with dest.open("x",encoding="utf-8") as fh:
        proc=subprocess.Popen(args,cwd=V3,stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,text=True)
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line,end="")
            fh.write(line)
        exitcode=proc.wait()
    if exitcode:
        raise RuntimeError(f"hardware command failed (exit {exitcode}); see {dest}")

def run_physical(args:argparse.Namespace,manifest:dict)->None:
    # Explicit operator approvals and real checks remain mandatory; no
    # operator-authored note file is required. Approvals are NOT proof of
    # firmware/low-DDR exclusivity. Do not run while Linux still owns DDR.
    approvals=(args.dedicated_jtag_owner,args.cpu_takeover_approved,
               args.low_ddr_exclusive,args.mailbox_overwrite_approved,
               args.pl_program_approved,args.reboot_recovery_approved)
    if approvals!=("YES",)*6:
        raise ValueError("NO-GO: six distinct hardware-ownership approvals required")
    for name in ("xsdb","vivado"):
        subprocess.run(["which",name],check=True,capture_output=True)
    evidence=args.evidence
    if evidence is None or not evidence.is_absolute() or evidence.exists() or (
        evidence.is_relative_to(ROOT)
    ):
        raise ValueError("NO-GO: new absolute evidence directory outside Thesis required")
    # An ELF beginning at 0x0 is deliberately destructive; on ANY doubt
    # cancel physical run. The operator must verify the *full* LOAD spans.
    evidence.mkdir(parents=True)
    (evidence/"manifest.txt").write_text(
        "P07-B.4i dedicated A53 admission only; NOT inference\n"+
        "ELF entry="+hex(manifest["entry"])+"\n"+
        "LOADs="+repr(manifest["loads"])+"\n"+
        "low DDR risk="+str(manifest["low_ddr_risk"])+"\n"+
        repr(manifest["sha256"])+"\n"
    )
    # FPD/LPD live gate FIRST, mirroring accepted Track A sequence.
    log_call(["xsdb","vivado/p07_b4i_stop_and_width_gate.tcl",
              "DEDICATED_DISCARD_LINUX_APPROVED",
              "tcp:127.0.0.1:3121"],evidence/"ps_width.log")
    cores=verify_takeover_log((evidence/"ps_width.log").read_text())
    print("P07_B4I_TAKEOVER_CORE_STATES="+repr(cores))
    print("P07_B4I_TAKEOVER_WIDTH_GATE_ADMITTED=1")
    reports=args.reports
    log_call(["vivado","-mode","batch","-source",
              "vivado/p03_2c_program_bitstream.tcl","-tclargs",
              str(reports/"p03_2_ps_mmio.bit"),str(reports/"p03_2_ps_mmio.ltx"),
              "localhost:3121"],evidence/"program.log")
    if ("PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released"
        not in (evidence/"program.log").read_text()):
        raise RuntimeError("NO-GO: accepted P03 PL programming not observed")
    zeros=evidence/"zero_mailbox_64.bin"
    zeros.write_bytes(bytes(64))
    result=evidence/"p07_b4i_mailbox.bin"
    elf=args.build/"vitis_workspace/p07_b4i_mailbox_probe.elf"
    log_call(["xsdb","vivado/p07_b4i_xsdb_run.tcl",
              "DEDICATED_A53_DDR_OWNER_VERIFIED",str(elf),str(zeros),
              str(result),"tcp:127.0.0.1:3121"],evidence/"a53_run.log")
    log_call([sys.executable,"scripts/p07_b4i_verify_mailbox.py",
              "--mailbox",str(result)],evidence/"verify.log")
    print("P07_B4I_PHYSICAL_READONLY_ADMISSION_VERIFIED=1")
    print("P07_B4I_INFERENCE_EXECUTED=0")
    print("REBOOT KV260; never resume the old Linux instance")

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    p.add_argument("--build",required=True,type=Path)
    p.add_argument("--reports",required=True,type=Path)
    p.add_argument("--evidence",type=Path)
    for flag in ("dedicated-jtag-owner","cpu-takeover-approved",
                 "low-ddr-exclusive","mailbox-overwrite-approved",
                 "pl-program-approved","reboot-recovery-approved"):
        p.add_argument("--"+flag,default="NO",choices=("NO","YES"))
    a=p.parse_args()
    try:
        report=preflight(a.build,a.reports)
        print("P07_B4I_REAL_ARTIFACT_OFFLINE_PREFLIGHT_PASS=1")
        print("P07_B4I_ELF_ENTRY="+hex(report["entry"]))
        print("P07_B4I_ELF_PT_LOAD="+repr(report["loads"]))
        print("P07_B4I_LOW_DDR_OWNERSHIP_UNKNOWN="+str(report["low_ddr_risk"]))
        if a.mode=="execute":
            run_physical(a,report)
        else:
            print("P07_B4I_OFFLINE_ONLY_NO_BOARD_ACCESS=1")
            print("P07_B4I_PHYSICAL_A53_LAUNCH_AUTHORIZED=0")
    except (ValueError,OSError,RuntimeError,subprocess.CalledProcessError) as exc:
        print("P07_B4I_NO_GO="+str(exc),file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
