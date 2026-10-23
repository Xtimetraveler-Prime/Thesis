#!/usr/bin/env python3
"""P07-B.4f: genuine A53 ELF + accepted XSA/offline boot-safety assessment.

This tool NEVER invokes Vitis, Vivado, XSDB, JTAG, UART or board operations.
It proves only consistency of user-local files using actual cross-binutils.
An ELF whose PT_LOAD starts at low DDR 0x0 is NOT automatically safe to
download, even when the executable passes the B.4c ELF+map checker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"scripts"))
from p07_b3c3_elf_admission import parse_load_segments
from p07_b4d_readonly_evidence import admission_inputs, digest

APP="p07_b4c_readonly_probe"
SHA256=re.compile(r"[a-fA-F0-9]{64}\Z")
# AMD UG1085 APU system physical DDR: 0x00000000-0x7fffffff.
# 1MiB here is a conservative *risk flag* for current default entry at 0,
# NOT an assertion that anything above 1MiB is safe to overwrite.
LOW_DDR_BOOT_RISK=(0,0x100000)
P02_BACKING=(0x40000000,0x44000000)


def admitted_hash(path:Path, expected:str, label:str)->str:
    if not SHA256.fullmatch(expected):
        raise ValueError(label+" pin must be exactly 64 hex characters")
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        raise ValueError(label+" missing, empty or symlinked")
    actual=digest(path)
    if actual!=expected.lower():
        raise ValueError(label+" SHA256 mismatch")
    return actual


def binutils(tool:str, args:list[str], path:Path)->str:
    return subprocess.run([tool,*args,str(path)],check=True,text=True,
                          capture_output=True).stdout


def check(
    *,build_dir:Path,xsa:Path,bit:Path,ltx:Path,route_metrics:Path,
    xsa_sha256:str,bit_sha256:str,elf_sha256:str,map_sha256:str,
    bit_provenance:str,readelf:str,nm:str
)->dict:
    if bit_provenance not in ("observed","independently_accepted"):
        raise ValueError("bitstream provenance must be explicit")
    workspace=build_dir/"vitis_workspace"
    elf=workspace/(APP+".elf")
    linker=workspace/(APP+".map")
    # Verify ELF/MAP immutable identity BEFORE costly tool checks, and bind
    # every input/source to the existing B.4d preflight implementation.
    pinned_elf=admitted_hash(elf,elf_sha256,"ELF")
    pinned_map=admitted_hash(linker,map_sha256,"MAP")
    provenance=admission_inputs(
        build_dir,xsa,bit,ltx,route_metrics,xsa_sha256,bit_sha256,
        "auto","auto",readelf,nm,
    )
    if provenance["sha256"]["elf"]!=pinned_elf or \
       provenance["sha256"]["linker_map"]!=pinned_map:
        raise ValueError("B.4d input digests disagree with pinned ELF/map")
    sections=binutils(readelf,["-W","-h"],elf)
    entry_match=re.search(r"Entry point address:\s*(0x[0-9a-fA-F]+)",sections)
    if not entry_match:
        raise ValueError("cannot determine actual AArch64 ELF entry point")
    entry=int(entry_match.group(1),16)
    loads=parse_load_segments(binutils(readelf,["-W","-l"],elf))
    if not any(s.first<=entry<s.end for s in loads):
        raise ValueError("A53 ELF entry point is outside all LOAD segments")
    low_risk=any(s.first<LOW_DDR_BOOT_RISK[1] and
                 LOW_DDR_BOOT_RISK[0]<s.end for s in loads)
    reserved=any(s.first<P02_BACKING[1] and P02_BACKING[0]<s.end
                 for s in loads)
    if reserved:
        raise ValueError("ELF LOAD overlaps frozen P02 64MiB reserved DDR")
    elf_gate=provenance["elf_admission"]
    if not elf_gate.get("heap_stack_crosschecked_with_actual_allocated_ELF_sections"):
        raise ValueError("actual ELF heap/stack section proof missing")
    if elf_gate.get("inference_authorized") is not False:
        raise ValueError("unsafe ELF authorization output")
    return {
        "schema":"p07-b4f-offline-physical-launch-readiness-v1",
        "user_local_real_elf_and_map_hash_matched":True,
        "read_only_source_and_accepted_XSA_inputs_checked":True,
        "sha256":{"elf":pinned_elf,"linker_map":pinned_map,
                  "xsa":provenance["sha256"]["xsa"],
                  "bit":provenance["sha256"]["bit"],
                  "ltx":provenance["sha256"]["ltx"]},
        "bit_fingerprint_provenance":bit_provenance,
        "bit_independently_accepted":bit_provenance=="independently_accepted",
        "actual_ELF_entry":f"0x{entry:x}",
        "actual_ELF_LOAD_spans":[f"0x{s.first:x}:0x{s.end:x}" for s in loads],
        "low_DDR_first_1MiB_overlap":low_risk,
        "low_DDR_start_zero":any(s.first==0 for s in loads),
        "ELF_heap_section":elf_gate["ELF_heap_section"],
        "ELF_stack_section":elf_gate["ELF_stack_section"],
        "reserved_P02_nonoverlap":True,
        "physical_A53_low_DDR_owner":"NOT_ESTABLISHED",
        "Linux_SMP_stopped_or_absent":"NOT_ESTABLISHED",
        "boot_chain_FSBL_TFA_UBoot_memory_owner":"NOT_ESTABLISHED",
        "physical_PL_bitstream_identity":"NOT_ESTABLISHED",
        "PS_FPD128_live_registers":"NOT_OBSERVED",
        "DDR_64MiB_exclusivity":"NOT_ESTABLISHED",
        "MMU_and_cache_attributes":"NOT_ESTABLISHED",
        "UART_output":"NOT_OBSERVED",
        "XSDB_readonly_snapshot":"NOT_EXECUTED",
        "board_ELF_download_authorized":False,
        "board_programming_authorized":False,
        "physical_inference_authorized":False,
        "next_safe_gate":"Separately operator-approved non-halting read-only PS/PL register snapshot; no firmware download",
        "B2_official_MNIST_TEST":"SEALED",
    }


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    for opt in ("--build-dir","--xsa","--bit","--ltx","--route-metrics"):
        parser.add_argument(opt,type=Path,required=True)
    for opt in ("--xsa-sha256","--bit-sha256","--elf-sha256","--map-sha256"):
        parser.add_argument(opt,required=True)
    parser.add_argument("--bit-provenance",choices=["observed","independently_accepted"],
                        required=True)
    parser.add_argument("--readelf",default="aarch64-none-elf-readelf")
    parser.add_argument("--nm",default="aarch64-none-elf-nm")
    parser.add_argument("--json-out",type=Path)
    args=parser.parse_args()
    try:
        result=check(
            build_dir=args.build_dir,xsa=args.xsa,bit=args.bit,ltx=args.ltx,
            route_metrics=args.route_metrics,xsa_sha256=args.xsa_sha256,
            bit_sha256=args.bit_sha256,elf_sha256=args.elf_sha256,
            map_sha256=args.map_sha256,bit_provenance=args.bit_provenance,
            readelf=args.readelf,nm=args.nm,
        )
        out=json.dumps(result,sort_keys=True,indent=2)+"\n"
        if args.json_out is not None:
            where=args.json_out.resolve(strict=False)
            project=HERE.parent.parent
            if where==project or project in where.parents:
                raise ValueError("evidence output must be outside repository")
            if args.json_out.exists() or args.json_out.is_symlink() or \
               not args.json_out.parent.is_dir():
                raise ValueError("output JSON must be a new path in existing directory")
            args.json_out.write_text(out,encoding="utf-8")
        print(out,end="")
        print("P07_B4F_OFFLINE_LAUNCH_SAFETY_AUDIT_PASS_NO_BOARD_GO=1")
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__=="__main__":
    main()
