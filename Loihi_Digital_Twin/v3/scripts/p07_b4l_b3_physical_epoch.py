#!/usr/bin/env python3
"""B4l original B2.4 one-epoch physical dispatch: offline gate + real runner.

No background work. DEFAULT --mode preflight NEVER contacts the KV260.
A destructive execute request needs a fresh dedicated session and per-action
YES approvals. At each step any missing acceptance marker is NO-GO.
ELF is pinned to USER-BUILT 2026-10-23 A53 first-epoch sha, 0x42D40
physical memsz, expands earlier 0x29D80 physical precedent; CPU halt and
approval flags do not independently prove firmware RAM ownership.
Never claim B2b NEXT delivery, 26-tick inference or official TEST access.
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
import p07_b4l_frozen_bindings as bind
import p07_b4l_verify_b3_epoch as verify_epoch

ELF_SHA="3e462e3b12c525820d91b0af06f73f36afc960e39d834424fc507c4fd89a747d"
ACCEPTED_DESCRIPTOR_SHA="2f0a5299a3948d7e0d4d48c265d199616fd3709d966343629596464687f611eb"
ELF_NAME="p07_b4l_b3_first_epoch.elf"
ELF_ID=b"P07_B4L_A53_B3_ONE_EPOCH_V1"
LOAD_PHYSICAL_START=0
LOAD_MEMORY_END=0x42D40
LOAD_FILESZ=0x15054
EXPECTED_LOW_DDR_MEMORY_BYTES=0x42D40
BIND_STAGE_TCL="vivado/p07_b4l_b3_stage_frozen_bindings.tcl"
A53_RUN_TCL="vivado/p07_b4l_b3_xsdb_first_epoch_run.tcl"
REPORT_MARKER="P07_B4L_B3_REAL_27_DISPATCH_BAR_PRE_ACK_PHYSICAL_RECEIPT_PASS=1"
APPROVALS=(
    "dedicated_jtag_owner",
    "cpu_takeover_approved",
    "expanded_low_ddr_footprint_approved",
    "ddr_27core_overwrite_approved",
    "frozen_binding_overwrite_approved",
    "mailbox_overwrite_approved",
    "one_epoch_p03_dispatch_approved",
    "firmware_coexistence_risk_acknowledged",
    "pl_program_approved",
    "reboot_recovery_approved",
)


class EpochNoGo(ValueError):
    pass


def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()


def require_real_b3_elf(elf:Path)->dict:
    """Pin exact user built A53 executable, genuine ELF LOAD and linker map.

    This SHA/shape gate is intentionally narrower than a generic memory
    cap. A re-link, even with identical source, is a NEW artifact and NO-GO.
    """
    if (not elf.is_absolute() or elf.is_symlink() or not elf.is_file()
            or elf.name!=ELF_NAME or file_sha(elf)!=ELF_SHA
            or ELF_ID not in elf.read_bytes()):
        raise EpochNoGo("NO-GO: exact operator-built 2026-10-23 B3 first-epoch ELF identity/SHA mismatch")
    readelf=shutil.which("aarch64-none-elf-readelf")
    if readelf is None:
        raise EpochNoGo("NO-GO: Vitis AArch64 readelf missing")
    result=subprocess.run([readelf,"-W","-h","-l","-S",str(elf)],
                          capture_output=True,text=True,timeout=45)
    text=result.stdout
    if (result.returncode or
            not re.search(r"Class:\s+ELF64",text) or
            not re.search(r"Machine:\s+AArch64",text) or
            not re.search(r"Data:\s+2's complement, little endian",text) or
            not re.search(r"Type:\s+EXEC",text) or
            not re.search(r"Entry point address:\s+0x0\b",text)):
        raise EpochNoGo("NO-GO: B3 ELF64 AArch64 little-endian executable/entry mismatch")
    loads=[]
    for line in text.splitlines():
        fields=line.split()
        if fields and fields[0]=="LOAD":
            if len(fields)<7:
                raise EpochNoGo("NO-GO: malformed ELF program LOAD header")
            loads.append({
                "offset":int(fields[1],16),"vaddr":int(fields[2],16),
                "paddr":int(fields[3],16),"filesz":int(fields[4],16),
                "memsz":int(fields[5],16),"flags":fields[6],
            })
    if (len(loads)!=1 or
            loads[0]["offset"]!=0x10000 or
            loads[0]["vaddr"]!=0 or
            loads[0]["paddr"]!=LOAD_PHYSICAL_START or
            loads[0]["filesz"]!=LOAD_FILESZ or
            loads[0]["memsz"]!=LOAD_MEMORY_END or
            LOAD_MEMORY_END>=0x40000000 or
            LOAD_MEMORY_END>=bind.BASE or
            LOAD_MEMORY_END>=0x43FF0000):
        raise EpochNoGo("NO-GO: new real A53 first epoch LOAD/filesz/memsz shape not admitted")
    if not all(x in text for x in (".heap",".stack",".bss",".text","Segment Sections")):
        raise EpochNoGo("NO-GO: B3 ELF section/memory map incomplete")
    # Genuine ELF section header addresses and sizes (hex) must be entirely
    # covered by the exact *in-memory* LOAD. Merely mentioning ".stack"
    # in a linker map does NOT mean the stack is owned by that segment.
    required_sections={".text",".bss",".heap",".stack"}
    section_ranges={}
    section_pattern=re.compile(
        r"^\s*\[\s*\d+\]\s+(\.[-A-Za-z0-9_.]+)\s+\S+"
        r"\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)"
    )
    for section_line in text.splitlines():
        match=section_pattern.match(section_line)
        if match and match.group(1) in required_sections:
            name=match.group(1)
            if name in section_ranges:
                raise EpochNoGo("NO-GO: duplicated ELF allocatable section "+name)
            start=int(match.group(2),16)
            size=int(match.group(4),16)
            if size<=0 or start<LOAD_PHYSICAL_START or start+size>LOAD_MEMORY_END:
                raise EpochNoGo("NO-GO: original A53 "+name+" section falls outside pinned 0x42D40 memory LOAD")
            section_ranges[name]={"start":start,"end_exclusive":start+size,"bytes":size}
    if set(section_ranges)!=required_sections:
        raise EpochNoGo("NO-GO: ELF sections lack inspectable actual .text/.bss/.heap/.stack ranges")
    if loads[0]["flags"]!="RWE":
        raise EpochNoGo("NO-GO: original operator LOAD executable/data flags drift")
    mapfile=elf.with_suffix(".map")
    if mapfile.is_symlink() or not mapfile.is_file():
        raise EpochNoGo("NO-GO: genuine same-build B3 linker map missing")
    mapping=mapfile.read_text(errors="replace")
    if ("Linker script and memory map" not in mapping or
            ".heap" not in mapping or ".stack" not in mapping or
            ".text" not in mapping or "main" not in mapping):
        raise EpochNoGo("NO-GO: B3 first epoch linker map invalid/absent")
    return {
        "operator_reported_elf_sha256":ELF_SHA,
        "verified_elf_sha256":file_sha(elf),
        "genuine_linker_map_sha256":file_sha(mapfile),
        "physical_load_start":"0x00000000",
        "physical_load_end_exclusive":f"0x{LOAD_MEMORY_END:08X}",
        "elf_initial_file_bytes":LOAD_FILESZ,
        "elf_runtime_mem_bytes":EXPECTED_LOW_DDR_MEMORY_BYTES,
        "checked_genuine_elf_section_bounds":section_ranges,
        "historical_accepted_A53_envelope_end":"0x00029D80",
        "expanded_memory_proven_exclusive":False,
        "physical_execution_authorized_by_preflight":False,
    }


def require_real_bindings(frozen:Path,staged:Path,bindings_dir:Path)->dict:
    """Original unmodified B2.4 graph/axon/bitmap must agree exactly."""
    verified=bind.stage(frozen,staged,bindings_dir,"verify")
    descriptor=bindings_dir/bind.FILENAME
    if (verified["bytes"]!=0x4000 or
            verified["physical_staging_address"]!="0x43FC0000" or
            verified["physical_staging_end_exclusive"]!="0x43FC4000" or
            verified["core_count"]!=27 or
            verified["accepted_27core_bundle_sha256"]!=deploy.ACCEPTED_BUNDLE_SHA or
            verified["binary_sha256"]!=ACCEPTED_DESCRIPTOR_SHA or
            verified["binary_sha256"]!=file_sha(descriptor)):
        raise EpochNoGo("NO-GO: immutable frozen 16KiB 27-core descriptor SHA/DDR geometry mismatch")
    return verified


def preflight(args:argparse.Namespace)->tuple[dict,dict,dict]:
    original=deploy.prepare_verified_contexts(args.frozen_dir,args.staged_dir)
    desc=require_real_bindings(args.frozen_dir,args.staged_dir,args.bindings_dir)
    b4i.preflight(args.b4i_build,args.reports)
    elf=require_real_b3_elf(args.elf)
    return original,desc,elf


def require_execute(args:argparse.Namespace)->None:
    for name in APPROVALS:
        if getattr(args,name)!="YES":
            raise EpochNoGo("NO-GO: explicit --"+name.replace("_","-")+" YES required")
    evidence=args.evidence
    if (evidence is None or not evidence.is_absolute()
            or evidence.exists() or evidence.is_symlink()
            or evidence.resolve().is_relative_to(b4i.ROOT)
            or not evidence.parent.is_dir()):
        raise EpochNoGo("NO-GO: fresh absolute evidence path outside repository required")
    for tool in ("xsdb","vivado"):
        if not shutil.which(tool):
            raise EpochNoGo("NO-GO: accepted hardware tool missing: "+tool)


def checked_marker(log:Path,marker:str)->None:
    if log.read_text().splitlines().count(marker)!=1:
        raise EpochNoGo("NO-GO: expected unique genuine marker not found in "+log.name+": "+marker)


def run_hardware(args:argparse.Namespace,index:dict,descriptor:dict,elf:dict)->None:
    require_execute(args)
    out=args.evidence
    out.mkdir(mode=0o700,exist_ok=False)
    (out/"stage.txt").write_text("STARTED_DESTRUCTIVE_EXPERIMENT_REBOOT_REQUIRED\n")
    (out/"manifest.json").write_text(json.dumps({
        "milestone":"P07-B.4l consolidated B3 first physical dispatch candidate",
        "model_original_27core_sha256":deploy.ACCEPTED_BUNDLE_SHA,
        "descriptor_original_bytes_sha256":descriptor["binary_sha256"],
        "descriptor_location":"[0x43FC0000,0x43FC4000)",
        "elf":elf,
        "envelope_from_previous_physical_probe_exceeded":True,
        "low_DDR_firmware_exclusive_ownership_independently_proven":False,
        "no_external_CURRENT_ingress":True,
        "B2b_NEXT_traffic_committed":False,
        "B3_first_barrier_acknowledged":False,
        "trained_26_tick_inference_verified":False,
        "reboot_required":True,
    },sort_keys=True,indent=2)+"\n")
    print("P07_B4L_B3_LOW_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0",flush=True)
    try:
        # All complete host-byte checks done before contacting physical board.
        deploy.prep_transfer_files(args.staged_dir,out/"transfer_inputs",index)
        (out/"physical_readback").mkdir(mode=0o700)
        data=(args.bindings_dir/bind.FILENAME).read_bytes()
        if (len(data)!=bind.SIZE or
                hashlib.sha256(data).hexdigest()!=ACCEPTED_DESCRIPTOR_SHA or
                hashlib.sha256(data).hexdigest()!=descriptor["binary_sha256"]):
            raise EpochNoGo("NO-GO: frozen B2.4 metadata descriptor mutated since preflight")
        (out/"binding_input_16k.bin").write_bytes(data)
        (out/"stage.txt").write_text("27_ORIGINAL_CORES_AND_SHA_BOUND_DESCRIPTOR_PREPARED\n")
        b4i.log_call(["xsdb",b4j.TAKEOVER_TCL,"DEDICATED_DISCARD_LINUX_APPROVED",
                      "tcp:127.0.0.1:3121"],out/"ps_width.log")
        b4i.verify_takeover_log((out/"ps_width.log").read_text())
        print("P07_B4L_B3_REAL_A53_WIDTH_GATE_PASS=1",flush=True)
        (out/"stage.txt").write_text("A53_HALTED_PL_PROGRAM_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call(["vivado","-mode","batch","-source",b4j.PROGRAM_TCL,"-tclargs",
                      str(args.reports/"p03_2_ps_mmio.bit"),
                      str(args.reports/"p03_2_ps_mmio.ltx"),"localhost:3121"],out/"program.log")
        b4j.require_programmed_shell((out/"program.log").read_text())
        print("P07_B4L_B3_P03_BIT_VIO_RELEASE_PASS=1",flush=True)
        (out/"stage.txt").write_text("PL_PROGRAM_PASS_27_CORE_STAGE_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call(["xsdb",deploy.CORE_TCL,"DEDICATED_27_DDR_OVERWRITE_APPROVED",
                      str(out/"transfer_inputs"),str(out/"physical_readback"),
                      "tcp:127.0.0.1:3121"],out/"ddr_stage.log")
        checked_marker(out/"ddr_stage.log","P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1")
        for cid in range(27):
            checked_marker(out/"ddr_stage.log",f"P07_B4L_CORE_{cid}_512K_PHYSICAL_READBACK_PASS=1")
        original=deploy.verify_physical_readback(args.staged_dir,out/"physical_readback",index)
        (out/"ddr_verified.json").write_text(json.dumps(original,sort_keys=True,indent=2)+"\n")
        print("P07_B4L_B3_SAME_SESSION_ALL_27_DDR_BYTE_EXACT_PASS=1",flush=True)
        (out/"stage.txt").write_text("MODEL_DDR_PASS_DESCRIPTOR_16K_STAGE_PENDING_REBOOT_REQUIRED\n")
        b4i.log_call(["xsdb",BIND_STAGE_TCL,"B4L_FROZEN_BINDING_16K_OVERWRITE_APPROVED",
                      str(out/"binding_input_16k.bin"),str(out/"binding_readback_16k.bin"),
                      "tcp:127.0.0.1:3121"],out/"binding_stage.log")
        checked_marker(out/"binding_stage.log",
                       "P07_B4L_B3_FROZEN_DESCRIPTOR_16K_PHYSICAL_READBACK_TCL_PASS=1")
        returned=(out/"binding_readback_16k.bin")
        if (not returned.is_file() or returned.is_symlink() or returned.stat().st_size!=bind.SIZE
                or file_sha(returned)!=descriptor["binary_sha256"]
                or returned.read_bytes()!=data):
            raise EpochNoGo("NO-GO: independent real 16KiB metadata physical readback mismatch")
        (out/"descriptor_verified.json").write_text(json.dumps({
            "physical_ddr_address":f"0x{bind.BASE:08X}",
            "sha256":file_sha(returned),
            "bytes":bind.SIZE,
            "operator_model_sha256":deploy.ACCEPTED_BUNDLE_SHA,
        },indent=2,sort_keys=True)+"\n")
        print("P07_B4L_B3_SAME_SESSION_REAL_BINDING_16K_BYTE_EXACT_PASS=1",flush=True)
        (out/"stage.txt").write_text("MODEL_AND_BINDING_DDR_PASS_A53_EXECUTION_PENDING_REBOOT_REQUIRED\n")
        if file_sha(args.elf)!=ELF_SHA:
            raise EpochNoGo("NO-GO: ELF SHA changed before A53 execution")
        (out/"mailbox_zero_256.bin").write_bytes(bytes(256))
        b4i.log_call(["xsdb",A53_RUN_TCL,
                      "B4L_B3_FIRST_EPOCH_AFTER_27_DDR_AND_BINDINGS_APPROVED",
                      str(args.elf),str(out/"mailbox_zero_256.bin"),
                      str(out/"b3_epoch_mailbox_256.bin"),"tcp:127.0.0.1:3121"],
                     out/"a53_b3_epoch.log")
        checked_marker(out/"a53_b3_epoch.log","P07_B4L_B3_A53_EPOCH_ELF_DOWNLOADED=1")
        checked_marker(out/"a53_b3_epoch.log","P07_B4L_B3_A53_EPOCH_MAILBOX_CAPTURED_256_BYTES=1")
        checked_marker(out/"a53_b3_epoch.log",
                       "P07_B4L_B3_A53_EPOCH_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1")
        raw=out/"b3_epoch_mailbox_256.bin"
        verified=verify_epoch.verify(raw.read_bytes())
        (out/"independent_b3_epoch_receipt.json").write_text(
            json.dumps(verified,sort_keys=True,indent=2)+"\n")
        print(REPORT_MARKER,flush=True)
        print("P07_B4L_B3_26_TICK_NUMERICAL_PARITY_VERIFIED=0",flush=True)
        (out/"stage.txt").write_text("REAL_B3_FIRST_EPOCH_27_DISPATCH_BARRIER_PENDING_PASS_REBOOT_REQUIRED\n")
    finally:
        print("P07_B4L_B3_REBOOT_REQUIRED=1",flush=True)
        print("REBOOT KV260; NEVER resume halted Linux.",flush=True)


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    for attr in ("frozen-dir","staged-dir","bindings-dir","reports","b4i-build","elf"):
        p.add_argument("--"+attr,required=True,type=Path)
    p.add_argument("--evidence",type=Path)
    for name in APPROVALS:
        p.add_argument("--"+name.replace("_","-"),choices=("NO","YES"),default="NO")
    args=p.parse_args()
    try:
        idx,desc,elf=preflight(args)
        print("P07_B4L_B3_EXACT_ORIGINAL_MODEL_BINDINGS_NEW_ELF_PC_PREFLIGHT_PASS=1")
        print("P07_B4L_B3_PINNED_ELF_PHYSICAL_MEMSZ="+hex(LOAD_MEMORY_END))
        print("P07_B4L_B3_GENUINE_BINDINGS_SHA256="+desc["binary_sha256"])
        if args.mode=="preflight":
            print("P07_B4L_B3_OFFLINE_ONLY_NO_BOARD_ACCESS=1")
            print("P07_B4L_B3_PHYSICAL_DISPATCH_AUTHORIZED=0")
            return 0
        run_hardware(args,idx,desc,elf)
        return 0
    except (EpochNoGo,ValueError,OSError,KeyError,TypeError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print("P07_B4L_B3_NO_GO="+str(exc),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
