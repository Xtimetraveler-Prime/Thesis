#!/usr/bin/env python3
"""Read-only PC P07-B4m accepted TRAIN input/route and genuine A53 ELF gate.

NO JTAG/Vivado/XSDB interaction and NO physical launch permission. Separate
new full 26-tick ELF must have its own measured PT_LOAD/sections; the frozen
3-frame input/route payloads must be identical to separately generated
manifest SHA values. Expanded low-DDR firmware *exclusivity* remains NO-GO.
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

import p07_b4m_frozen_inputs as frozen
import p07_b4l1_stage_frozen_27core as b4l1

ELF_ID=b"P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1"
ELF_NAME="p07_b4m_full_26tick.elf"
SCHEMA="p07-b4m-original-B24-physical-route-and-TRAIN-witness-v1"
DENSE_ROUTES=10000
LOW_DDR_MAX_END=0x01000000
SPAN={"output_routes":["0x43fc4000","0x43fd8000"],
      "input_routes":["0x41000000","0x410e0000"],
      "per_image_ingress":["0x41100000","0x411e0000"]}
FRAME_IDX={0:37384,1:27347,2:20178}
MAX_FRAME=0xE0000

class AdmissionError(ValueError): pass

def file_sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require_routes(stage:Path)->dict:
    if not stage.is_absolute() or stage.is_symlink() or not stage.is_dir():
        raise AdmissionError("NO-GO: staging must be a real absolute directory")
    manifest=stage/"p07_b4m_frozen_inputs_manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise AdmissionError("NO-GO: signed TRAIN staging manifest missing")
    m=json.loads(manifest.read_text())
    if (m.get("schema")!=SCHEMA or m.get("official_MNIST_TEST")!="SEALED" or
        m.get("hardware_executed") is not False or
        m.get("frozen_snapshot_modified") is not False or
        m.get("original_compiled_sha256")!=frozen.PINNED_SHA or
        m.get("original_capacity_sha256")!=frozen.CAP_SHA or
        m.get("compartment_count")!=1010 or
        m.get("output_route_count")!=DENSE_ROUTES or
        not 784<=m.get("input_route_count",0)<=frozen.MAX_INGRESS_ROUTES):
        raise AdmissionError("NO-GO: original signed trained topology/count/identity mismatch")
    if {k:[v.lower() for v in values] for k,values in m.get("spans",{}).items()}!=SPAN:
        raise AdmissionError("NO-GO: physical DDR span allocations not accepted")
    expected_files={frozen.OUT_FILENAME,frozen.IN_FILENAME} | {
        f"p07_b4m_original_TRAIN_validation_{n}_ingress.bin" for n in FRAME_IDX}
    if set(m.get("files",{}))!=expected_files or set(m.get("frames",{}))!={str(i) for i in FRAME_IDX}:
        raise AdmissionError("NO-GO: incomplete/extra image manifest or three frozen TRAIN ordinals")
    if {p.name for p in stage.iterdir()}!=expected_files|{manifest.name}:
        raise AdmissionError("NO-GO: staging directory contains missing/extra files")
    for name in sorted(expected_files):
        p=stage/name
        if p.is_symlink() or not p.is_file() or file_sha(p)!=m["files"][name]:
            raise AdmissionError("NO-GO: source-to-stage original SHA mismatch: "+name)
    if (stage/frozen.OUT_FILENAME).stat().st_size!=frozen.OUT_BYTES or (
        stage/frozen.IN_FILENAME).stat().st_size!=frozen.IN_BYTES):
        raise AdmissionError("NO-GO: physical table input/output lengths differ")
    out=(stage/frozen.OUT_FILENAME).read_bytes()
    inp=(stage/frozen.IN_FILENAME).read_bytes()
    def header(buf,magic,records,step):
        if buf[:8]!=magic or int.from_bytes(buf[8:12],"little")!=1 or (
            int.from_bytes(buf[20:24],"little")!=records or
            int.from_bytes(buf[24:28],"little")!=step or
            buf[32:64]!=bytes.fromhex(frozen.PINNED_SHA) or
            buf[64:96]!=bytes.fromhex(frozen.CAP_SHA) or
            hashlib.sha256(buf[128:]).digest()!=buf[96:128]):
            raise AdmissionError("NO-GO: frozen B4m route header/internal SHA failure")
    header(out,b"B4MROUT1",DENSE_ROUTES,8)
    header(inp,b"B4MING01",m["input_route_count"],6)
    for n,idx in FRAME_IDX.items():
        name=f"p07_b4m_original_TRAIN_validation_{n}_ingress.bin"
        row=m["frames"][str(n)]
        data=(stage/name).read_bytes()
        if (row.get("original_TRAIN_idx")!=idx or
            row.get("raw_image_sha256")!=frozen.FRAME_SHA[n] or
            row.get("ingress_sha256")!=m["files"][name] or
            row.get("bytes")!=len(data) or not 128<=len(data)<=MAX_FRAME or
            data[:8]!=b"P06B13I1" or
            data[64:96]!=bytes.fromhex(frozen.PINNED_SHA) or
            data[96:128]!=bytes.fromhex(frozen.CAP_SHA) or
            int.from_bytes(data[20:24],"little")!=m["input_route_count"] or
            data[128:128+m["input_route_count"]*6]!=inp[128:128+m["input_route_count"]*6]):
            raise AdmissionError("NO-GO: pinned TRAIN frame SHA/row/route mismatch")
    return {"input_routes":m["input_route_count"],
            "output_routes":DENSE_ROUTES,
            "staged_files_sha256":m["files"],
            "original_B24_snapshot_untouched":True,
            "official_TEST":"SEALED"}

def require_elf(elf:Path)->dict:
    if (not elf.is_absolute() or elf.is_symlink() or not elf.is_file() or
        elf.name!=ELF_NAME or ELF_ID not in elf.read_bytes()):
        raise AdmissionError("NO-GO: exact new unmodified B4m candidate ELF required")
    elf_sha=file_sha(elf)
    source=elf.with_suffix(".map")
    if source.is_symlink() or not source.is_file():
        raise AdmissionError("NO-GO: NEW B4m genuine GNU linker map absent")
    m=source.read_text(errors="replace")
    if not all(x in m for x in ("Linker script and memory map",".text",".bss",".heap",".stack","main")):
        raise AdmissionError("NO-GO: source map lacks real A53 memory/entry evidence")
    tool=shutil.which("aarch64-none-elf-readelf")
    if not tool:
        raise AdmissionError("NO-GO: source AMD AArch64 readelf environment before preflight")
    p=subprocess.run([tool,"-W","-h","-l","-S",str(elf)],capture_output=True,text=True,timeout=60)
    if p.returncode:
        raise AdmissionError("NO-GO: cannot inspect actual new A53 ELF")
    t=p.stdout
    if not all(x in t for x in ("ELF64","AArch64","little endian","EXEC","Entry point address:")):
        raise AdmissionError("NO-GO: wrong A53 ELF format")
    entry=re.search(r"Entry point address:\s*0x([0-9a-fA-F]+)",t)
    if not entry or int(entry.group(1),16)!=0:
        raise AdmissionError("NO-GO: B4m entry physical address !=0")
    loads=[]
    for line in t.splitlines():
        parts=line.split()
        if parts and parts[0]=="LOAD":
            if len(parts)<7:
                raise AdmissionError("NO-GO: truncated ELF LOAD program header")
            start=int(parts[3],16)
            filesz=int(parts[4],16)
            memsz=int(parts[5],16)
            loads.append((start,filesz,memsz,parts[6]))
    if len(loads)!=1 or loads[0][0]!=0 or loads[0][3]!="RWE" or (
        loads[0][2]<loads[0][1] or
        loads[0][2]<=0 or loads[0][2]>LOW_DDR_MAX_END):
        raise AdmissionError("NO-GO: unadmitted ELF LOAD shape/flags/low DDR envelope")
    secs={}
    pat=re.compile(r"^\s*\[\s*\d+\]\s+(\.[-A-Za-z0-9_.]+)\s+\S+\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)")
    for line in t.splitlines():
        mat=pat.match(line)
        if mat and mat.group(1) in (".text",".bss",".heap",".stack"):
            name=mat.group(1)
            addr=int(mat.group(2),16);sz=int(mat.group(4),16)
            if name in secs or sz<=0 or addr+sz>loads[0][2]:
                raise AdmissionError("NO-GO: ELF allocation section outside real PT_LOAD")
            secs[name]={"start":f"0x{addr:X}","end_exclusive":f"0x{addr+sz:X}","bytes":sz}
    if set(secs)!={".text",".bss",".heap",".stack"}:
        raise AdmissionError("NO-GO: incomplete original A53 ELF heap/stack/bss boundaries")
    return {"new_elf_sha256":elf_sha,"new_linker_map_sha256":file_sha(source),
            "pt_load_start":f"0x{loads[0][0]:08X}",
            "pt_load_end_exclusive":f"0x{loads[0][2]:08X}",
            "pt_load_filesz":loads[0][1],"pt_load_memsz":loads[0][2],
            "verified_allocated_sections":secs,
            "expanded_low_DDR_boot_firmware_exclusivity_independently_proven":False}

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--frozen-dir",type=Path,required=True)
    parser.add_argument("--routes-dir",type=Path,required=True)
    parser.add_argument("--elf",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    try:
        if not args.out.is_absolute() or args.out.exists() or args.out.is_symlink() or (
            args.out.resolve().is_relative_to(b4l1.REPO.resolve())):
            raise AdmissionError("NO-GO: new absolute external report required")
        b4l1.admit_freeze(args.frozen_dir)
        record={
            "schema":"p07-b4m-full-26tick-offline-elf-and-stage-gate-v1",
            "staging":require_routes(args.routes_dir),
            "elf":require_elf(args.elf),
            "real_KV260_inference_executed":False,
            "destructive_launch_authorized":False,
            "full_numerical_parity_verified":False,
            "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        }
        args.out.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
        print("P07_B4M_FULL_ORIGINAL_FROZEN_ROUTE_AND_GENUINE_ELF_OFFLINE_PREFLIGHT_PASS=1")
        print("P07_B4M_LOW_DDR_BOOT_FIRMWARE_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0")
        print("P07_B4M_PHYSICAL_LAUNCH_AUTHORIZED=0")
        print("P07_B4M_OFFLINE_REPORT="+str(args.out))
        return 0
    except (AdmissionError,ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:
        print("P07_B4M_OFFLINE_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
