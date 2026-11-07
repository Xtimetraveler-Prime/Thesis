#!/usr/bin/env python3
"""P08-B2.3 read-only ELF64/AArch64 PT_LOAD and source-provenance audit.

Requires GENUINE Vitis 2025.2 linker-emitted ELF and map, new image-only
identity, original frozen reset header SHA and exact accepted P03 XSA.
Never contacts FPGA. PT_LOAD checks do not prove PS Linux/boot DDR ownership.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

MAGIC=b"\x7fELF"
IDENTITY=b"P08_B2_3_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1"
# Original B2.1 C stage + B2.2 locally verified original context SHA pins.
EXPECTED_PINS_SHA="5be79b38ec7f42622573a7fa59adb689a65bfcf5d8e5a6e8cdaec0e75c9f7171"
EXPECTED_XSA_SHA="52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
ROOT=Path(__file__).resolve().parents[3]
NEW_DDR_BASE=0x40000000
ELF_HDR="<16sHHIQQQIHHHHHH"
PHDR="<IIQQQQQQ"
ELF_HDR_SIZE=struct.calcsize(ELF_HDR)
PHDR_SIZE=struct.calcsize(PHDR)

class ElfNoGo(ValueError):pass

def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def load_segments(raw:bytes)->list[dict]:
    if len(raw)<ELF_HDR_SIZE:raise ElfNoGo("not an ELF64 file")
    head=struct.unpack_from(ELF_HDR,raw)
    ident,e_type,e_machine,e_version,e_entry,phoff,shoff,flags,ehsize,phentsize,phnum,shentsize,shnum,shstrndx=head
    if (ident[:4]!=MAGIC or ident[4]!=2 or ident[5]!=1 or
        ident[6]!=1 or e_type!=2 or e_machine!=183 or e_version!=1 or
        ehsize!=ELF_HDR_SIZE or phentsize!=PHDR_SIZE or
        phnum==0 or phnum>128 or phoff>len(raw) or
        phnum*phentsize>len(raw)-phoff or
        e_entry>=NEW_DDR_BASE):
        raise ElfNoGo("not a valid EXEC AArch64 little-endian ELF64 program-header table")
    segments=[]
    entry_loaded=False
    for i in range(phnum):
        (type_,flags_,offset,vaddr,paddr,filesz,memsz,align)=struct.unpack_from(
            PHDR,raw,phoff+i*phentsize)
        if type_!=1:continue
        if (memsz==0 or filesz>memsz or offset>len(raw) or
            filesz>len(raw)-offset or vaddr>=NEW_DDR_BASE or
            paddr>=NEW_DDR_BASE or
            memsz>NEW_DDR_BASE-vaddr or
            memsz>NEW_DDR_BASE-paddr or
            (align!=0 and (align&(align-1))) or
            (align>1 and (vaddr-offset)%align)):
            raise ElfNoGo(f"PT_LOAD #{i} overlaps original P08 P03 DDR owner or invalid memory")
        if vaddr<=e_entry<vaddr+memsz:
            entry_loaded=True
        segments.append({
            "index":i,"file_offset":offset,
            "vaddr_start":f"0x{vaddr:016X}",
            "vaddr_end_exclusive":f"0x{vaddr+memsz:016X}",
            "paddr_start":f"0x{paddr:016X}",
            "paddr_end_exclusive":f"0x{paddr+memsz:016X}",
            "mem_bytes":memsz,"file_bytes":filesz,
        })
    if not segments or not entry_loaded:
        raise ElfNoGo("AArch64 entry point missing from executable PT_LOAD")
    # Nonoverlap within ELF LOAD program segments (overlapping shared
    # pages require explicit linker map investigation, not guessed safe).
    for kind in ("vaddr","paddr"):
        ranges=sorted((int(s[kind+"_start"],16),
                       int(s[kind+"_end_exclusive"],16)) for s in segments)
        for (lo,hi),(next_lo,next_hi) in zip(ranges,ranges[1:]):
            if next_lo<hi:
                raise ElfNoGo("new ELF has overlapping "+kind+" LOAD intervals")
    return segments

def audit(elf:Path,map_path:Path,xsa:Path,pins:Path,out:Path)->dict:
    if (not out.is_absolute() or out.is_symlink() or out.exists() or
        not out.parent.is_dir() or out.resolve().is_relative_to(ROOT)):
        raise ElfNoGo("new external absolute JSON report required")
    for name,path in {"elf":elf,"linker_map":map_path,"original_pins":pins,"xsa":xsa}.items():
        if not path.is_file() or path.is_symlink():
            raise ElfNoGo("missing or symlinked "+name)
    image=elf.read_bytes()
    map_raw=map_path.read_bytes()
    hdr=pins.read_bytes()
    if sha(hdr)!=EXPECTED_PINS_SHA:
        raise ElfNoGo("original 27-core SHA pin header differs from B2.2 accepted local output")
    if sha(xsa.read_bytes())!=EXPECTED_XSA_SHA:
        raise ElfNoGo("new project uses wrong original routed P03 XSA")
    if IDENTITY not in image:
        raise ElfNoGo("new image-only A53 ELF missing signed application identity")
    if not all(x in map_raw for x in (
        b"Linker script and memory map",b".text",b".bss",b"main")):
        raise ElfNoGo("not a genuine complete P08 Vitis linker map")
    segments=load_segments(image)
    result={
        "schema":"p08-b2-3-new-original-b24-image-only-A53-elf-source-preflight-v1",
        "ELF_sha256":sha(image),
        "linker_map_sha256":sha(map_raw),
        "original_reset_header_sha256":sha(hdr),
        "accepted_p03_XSA_sha256":sha(xsa.read_bytes()),
        "load_segments":segments,
        "low_DDR_PT_LOAD_disjoint_with_proposed_P03_64MiB":True,
        "A53_stack_heap_and_boot_reserved_memory_independently_proven":False,
        "PS_OS_FSBL_Uboot_DMA_memory_ownership_proven":False,
        "new_A53_firmware_physical_launch_authorized":False,
        "KV260_physical_execution":"NOT_RUN",
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("elf","map","xsa","pins-header","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    try:
        result=audit(a.elf,a.map,a.xsa,a.pins_header,a.out)
        print("P08_B2_3_NEW_A53_GENUINE_LOW_DDR_PT_LOAD_OFFLINE_PASS=1")
        print("P08_B2_3_ELF_SHA256="+result["ELF_sha256"])
        print("P08_B2_3_MAP_SHA256="+result["linker_map_sha256"])
        print("P08_B2_3_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0")
        print("P08_B2_3_JTAG_LAUNCH_AUTHORIZED=0")
        print("P08_B2_3_PT_LOAD_REPORT="+str(a.out))
    except (ElfNoGo,ValueError,OSError,TypeError) as e:
        print("P08_B2_3_ELF_OFFLINE_NO_GO="+str(e),file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
