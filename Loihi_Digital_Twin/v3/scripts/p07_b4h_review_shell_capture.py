#!/usr/bin/env python3
"""P07-B.4h: OFFLINE evidence correlation for separately run B.4g XSDB.

This script only reads local files; it never invokes XSDB/Vitis/Vivado/JTAG
or grants a CPU/PL operation. The submitted XSDB transcript is NOT
independently authenticated. A read-only shell PASS is NOT an A53 ELF
execution PASS, and it does not establish DDR exclusivity or low-DDR safety.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

IDENTITY="p07-b4f-offline-physical-launch-readiness-v1"
REGISTERS={
    "FPD_RAW":None,
    "P03_ID":0x4C543302,
    "P03_VERSION":0x00010000,
    "P03_CAPABILITIES":0x0001031F,
    "P03_GLOBAL_STATUS":0,
    "P03_PAGE_PENDING":0,
}
MARKERS={
    "P07_B4G_READONLY_PS_PL_SNAPSHOT_PASS":"1",
    "P07_B4G_INFERENCE_AUTHORIZED":"0",
    "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED":"0",
}
FORBIDDEN=[
    "P07_B4G_READONLY_PS_PL_SNAPSHOT_FAIL=1",
    "P07_B4C_READONLY_ADMISSION_PROBE_FAIL=",
]


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as inp:
        for data in iter(lambda:inp.read(1024*1024),b""):
            h.update(data)
    return h.hexdigest()


def ordinary(path:Path)->Path:
    if path.is_symlink() or not path.is_file() or path.stat().st_size==0:
        raise ValueError("missing, empty or symlinked evidence file: "+str(path))
    return path


def field(raw:str,key:str)->str:
    lines=re.findall(r"(?m)^"+re.escape(key)+r"=([^\r\n]*)\r?$",raw)
    if len(lines)!=1:
        raise ValueError("missing or duplicated record: "+key)
    return lines[0].strip()


def parse_shell(raw:str)->dict:
    for bad in FORBIDDEN:
        if bad in raw:
            raise ValueError("XSDB transcript includes failure marker")
    for k,expected in MARKERS.items():
        if field(raw,k)!=expected:
            raise ValueError("unexpected XSDB marker "+k)
    target=field(raw,"P07_B4G_PHYSICAL_TARGET")
    if target not in ("PSU","APU"):
        raise ValueError("XSDB physical target not PSU/APU")
    register_values={}
    for k,expected in REGISTERS.items():
        s=field(raw,"P07_B4G_"+k)
        if not re.fullmatch(r"0x[0-9A-Fa-f]{8}",s):
            raise ValueError("XSDB register not an exact 32-bit hex: "+k)
        value=int(s,16)
        if expected is not None and value!=expected:
            raise ValueError("XSDB read-back mismatch: "+k)
        register_values[k]=value
    if ((register_values["FPD_RAW"]>>8)&3)!=2:
        raise ValueError("XSDB FPD width selector is not 128 bit")
    return {
        "read_only_PS_PL_registers_match_accepted_shell":True,
        "XSDB_selected_memory_target":target,
        "observed_registers":{
            key:f"0x{value:08X}" for key,value in register_values.items()
        },
    }


def evaluate(
    *,audit:Path, transcript:Path, elf:Path, linker_map:Path,
    xsa:Path, bit:Path, board_state:str, bit_provenance:str
)->dict:
    for item in (audit,transcript,elf,linker_map,xsa,bit):
        ordinary(item)
    data=json.loads(audit.read_text(encoding="utf8"))
    if data.get("schema")!=IDENTITY:
        raise ValueError("real B.4f offline audit JSON required")
    if data.get("board_ELF_download_authorized") is not False or \
       data.get("physical_inference_authorized") is not False or \
       data.get("board_programming_authorized") is not False:
        raise ValueError("B.4f audit has unsafe launch permissions")
    if data.get("read_only_source_and_accepted_XSA_inputs_checked") is not True:
        raise ValueError("B.4f original source identity was not verified")
    if data.get("user_local_real_elf_and_map_hash_matched") is not True:
        raise ValueError("B.4f executable/map hashes were not verified")
    for name,path in (
        ("elf",elf),("linker_map",linker_map),("xsa",xsa),("bit",bit)
    ):
        pinned=data.get("sha256",{}).get(name)
        if not isinstance(pinned,str) or not re.fullmatch("[a-f0-9]{64}",pinned):
            raise ValueError("B.4f SHA pin missing: "+name)
        if sha256(path)!=pinned:
            raise ValueError("underlying real artifact changed after B.4f: "+name)
    if data.get("bit_fingerprint_provenance")!=bit_provenance:
        raise ValueError("bit provenance claim differs from original offline audit")
    if board_state not in ("linux_running","standalone","unknown"):
        raise ValueError("current KV260 boot state must be recorded or unknown")
    snapshot=parse_shell(transcript.read_text(encoding="utf8",errors="replace"))
    return {
        "schema":"p07-b4h-offline-shell-transcript-receipt-v1",
        "B4f_audit_sha256":sha256(audit),
        "XSDB_raw_log_sha256":sha256(transcript),
        "sha256":{k:sha256(p) for k,p in (
            ("elf",elf),("linker_map",linker_map),("xsa",xsa),("bit",bit)
        )},
        "board_state_operator_reported":board_state,
        "bit_provenance":bit_provenance,
        "XSDB_log_origin_authenticated":False,
        "XSDB_log_format_checks_passed":True,
        **snapshot,
        "live_BIT_SHA_independently_verified":False,
        "physical_A53_entry_or_ownership_verified":False,
        "PS_low_DDR_ownership_verified":False,
        "P02_64MiB_DDR_exclusivity_verified":False,
        "MMU_cache_attributes_verified":False,
        "A53_ELF_download_authorized":False,
        "PL_programming_authorized":False,
        "physical_inference_authorized":False,
        "official_B2_MNIST_TEST":"SEALED",
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("--audit","--transcript","--elf","--linker-map",
                 "--xsa","--bit"):
        p.add_argument(flag,required=True,type=Path)
    p.add_argument("--board-state",choices=[
        "linux_running","standalone","unknown"
    ],required=True)
    p.add_argument("--bit-provenance",choices=[
        "observed","independently_accepted"
    ],required=True)
    p.add_argument("--json-out",type=Path)
    args=p.parse_args()
    try:
        result=evaluate(
            audit=args.audit,transcript=args.transcript,elf=args.elf,
            linker_map=args.linker_map,xsa=args.xsa,bit=args.bit,
            board_state=args.board_state,bit_provenance=args.bit_provenance,
        )
        output=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if args.json_out:
            dest=args.json_out.resolve(strict=False)
            repository=Path(__file__).resolve().parents[3]
            if dest==repository or repository in dest.parents:
                raise ValueError("receipt output inside Thesis repository forbidden")
            if args.json_out.exists() or args.json_out.is_symlink() or \
               not args.json_out.parent.is_dir():
                raise ValueError("receipt output must be fresh with existing parent")
            args.json_out.write_text(output,encoding="utf8")
        print(output,end="")
        print("P07_B4H_OFFLINE_SHELL_LOG_FORMAT_PASS_NOT_PHYSICAL_GO=1")
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        p.error(str(exc))


if __name__=="__main__":
    main()
