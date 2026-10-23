#!/usr/bin/env python3
"""P07-B.4c actual read-only A53 candidate ELF admission.

Unlinked source and synthetic host-CI fixtures never constitute a real ELF.
Actual Vitis AArch64 ELF, companion map, external stack/heap physical extents
and retained B4c read-only identity are mandatory. Outputs NO permission to
dispatch, page or write P02 DDR. Do not flash or upload from this command.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from p07_b3c3_elf_admission import parse_named_span
from p07_b4b_elf_probe_admission import (
    validate_elf_evidence, actual_allocated_elf_span,
)

IDENTITY=b"P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1"


def verify(elf: Path, linker_map: Path, stack: str, heap: str,
           *, readelf: str="readelf", nm: str="nm") -> dict:
    if not elf.is_file() or not linker_map.is_file():
        raise ValueError("real ELF and matching linker map are mandatory")
    if elf.is_symlink() or linker_map.is_symlink():
        raise ValueError("symlinked ELF/map not admitted")
    # Check ELF magic before invoking external binutils; no text substitutes.
    with elf.open("rb") as handle:
        first=handle.read(5)
    if first!=b"\x7fELF\x02":
        raise ValueError("not a genuine ELF64 binary")
    elf_bytes=elf.read_bytes()
    if IDENTITY not in elf_bytes:
        raise ValueError("ELF lacks the unique B4c read-only firmware identity")
    map_text=linker_map.read_text(encoding="utf-8")
    if not map_text.strip():
        raise ValueError("empty linker map")
    def call(tool: str, *args: str) -> str:
        return subprocess.run([tool,*args,str(elf)],check=True,text=True,
                              capture_output=True).stdout
    sections=call(readelf,"-W","-S")
    if (stack=="auto") != (heap=="auto"):
        raise ValueError("stack/heap must BOTH be 'auto' or BOTH explicit")
    stack_span=(actual_allocated_elf_span(sections,".stack")
                if stack=="auto" else parse_named_span(stack,label="physical stack"))
    heap_span=(actual_allocated_elf_span(sections,".heap")
               if heap=="auto" else parse_named_span(heap,label="physical heap"))
    evidence=validate_elf_evidence(
        call(readelf,"-W","-h"),
        call(readelf,"-W","-l"),
        call(nm,"-S","--defined-only"),
        map_text,stack_span,heap_span,sections,
    )
    return {
        **evidence,
        "schema": "p07-b4c-real-readonly-a53-elf-gate-v1",
        "elf_sha256": hashlib.sha256(elf_bytes).hexdigest(),
        "map_sha256": hashlib.sha256(linker_map.read_bytes()).hexdigest(),
        "read_only_firmware_identity_present": True,
        "board_probe_executed": False,
        "inference_authorized": False,
        "DDR_exclusivity_verified": False,
        "MMU_cache_attributes_verified": False,
        "standalone_BSP_stack_heap_ranges_verified_from_linker": False,
        "heap_stack_crosschecked_with_actual_allocated_ELF_sections": True,
        "ELF_heap_section": f"0x{heap_span.first:x}:0x{heap_span.end:x}",
        "ELF_stack_section": f"0x{stack_span.first:x}:0x{stack_span.end:x}",
        "BSP_physical_address_owner_verified": False,
        "physical_PL_bitstream_SHA_verified": False,
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--elf",type=Path,required=True)
    p.add_argument("--linker-map",type=Path,required=True)
    p.add_argument("--stack",required=True,help="START:END or auto (derive actual ELF .stack)")
    p.add_argument("--heap",required=True,help="START:END or auto (derive actual ELF .heap)")
    p.add_argument("--readelf",default="readelf")
    p.add_argument("--nm",default="nm")
    args=p.parse_args()
    try:
        result=verify(args.elf,args.linker_map,args.stack,args.heap,
                      readelf=args.readelf,nm=args.nm)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        p.error(str(error))
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
