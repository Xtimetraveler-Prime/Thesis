#!/usr/bin/env python3
"""P08-B4.4.2: new profile-only Vitis ELF64 AArch64 source admission, NO JTAG.

This cannot authorize destructive board launch. Validates genuine
original signed B2.3 ELF/accepted P03 XSA/B2.2 27-context SHA header
and a NEW distinct experimental profiled image/map and PT_LOAD regions.
Does not prove heap/stack/boot/PS DMA ownership or full original scalar
neural equality on FPGA. The new profile sidecar at 0x42400000 is
external DDR and MUST be separately authorized, zeroed and read back.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import p08_b2_3_elf_admission as orig

PROFILE_ID=b"P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1"
PROFILE_DONE=b"P08_B44_RESET_PROFILE_1024_TERMINAL_DONE=1"
ORIGINAL_ELF_SHA="0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
ORIGINAL_XSA_SHA=orig.EXPECTED_XSA_SHA
ORIGINAL_PINS_SHA=orig.EXPECTED_PINS_SHA
PROFILE_BASE=0x42400000
PROFILE_BYTES=1024*256
SCHEMA="p08-b44-original27-reset-profile-genuine-a53-vitis-offline-admission-v1"
class ProfileElfNoGo(ValueError):pass

def require(ok:bool,reason:str)->None:
    if not ok:raise ProfileElfNoGo("NO-GO: "+reason)

def read_original(p:Path)->bytes:
    require(p.is_absolute() and p.is_file() and not p.is_symlink(),
            "absolute existing non-symlink original pinned source required: "+str(p))
    return p.read_bytes()

def audit(profile_elf:Path,profile_map:Path,original_elf:Path,
          xsa:Path,pins:Path,out:Path)->dict:
    require(out.is_absolute() and out.parent.is_dir()
            and not out.exists() and not out.is_symlink()
            and not out.resolve().is_relative_to(orig.ROOT),
            "new no-overwrite external JSON report path required")
    original=read_original(original_elf)
    require(orig.sha(original)==ORIGINAL_ELF_SHA and
            orig.IDENTITY in original and PROFILE_ID not in original,
            "original accepted full1024 B2.3 Vitis ELF identity/SHA drift")
    require(orig.sha(read_original(xsa))==ORIGINAL_XSA_SHA and
            orig.sha(read_original(pins))==ORIGINAL_PINS_SHA,
            "original P03.2c XSA or original 27-context SHA header changed")
    profile=read_original(profile_elf)
    new_map=read_original(profile_map)
    require(PROFILE_ID in profile and PROFILE_DONE in profile
            and orig.IDENTITY not in profile and orig.sha(profile)!=ORIGINAL_ELF_SHA,
            "distinct original 27core B4.4 reset-profile A53 identity/ELF absent")
    require(all(x in new_map for x in (
            b"Linker script and memory map",b".text",b".bss",b"main",
            b"p08_b44_profile_reset_image")),
            "new genuine Vitis linker map missing unique profiler symbol / text / bss")
    try:
        original_segments=orig.load_segments(original)
        segments=orig.load_segments(profile)
    except orig.ElfNoGo as e:
        raise ProfileElfNoGo("original/profiler AArch64 PT_LOAD invalid: "+str(e)) from e
    require(len(segments)>0 and all(
            int(item["paddr_end_exclusive"],16)<=orig.NEW_DDR_BASE
            for item in segments),
            "profile ELF PT_LOAD may overlap original frozen DDR or new profiling region")
    # Static source memory geometry is fixed but actual boot ownership
    # and A53 DDR exclusivity must NOT be inferred from this check.
    require(PROFILE_BASE==0x42400000 and PROFILE_BYTES==262144 and
            PROFILE_BASE+PROFILE_BYTES<0x43000000,
            "extra profile sidecar does not fit proposed original DDR slack")
    result={
        "schema":SCHEMA,
        "original_immutable_B2_3_full1024_ELF_sha256":ORIGINAL_ELF_SHA,
        "original_P03_XSA_sha256":ORIGINAL_XSA_SHA,
        "original_B2_2_27context_SHA_header_sha256":ORIGINAL_PINS_SHA,
        "new_profile_ELF_sha256":orig.sha(profile),
        "new_profile_linker_map_sha256":orig.sha(new_map),
        "new_profile_program_segments":segments,
        "original_immutable_program_segments":original_segments,
        "distinct_embedded_profile_identity":PROFILE_ID.decode(),
        "new_profile_sidecar_base":"0x42400000",
        "new_profile_sidecar_byte_count":PROFILE_BYTES,
        "new_ELF64_AArch64_low_DDR_PT_LOAD_static_disjoint":True,
        "new_image_actual_KV260_neural_FNV_parity_verified":False,
        "new_profile_sidecar_physical_readback_verified":False,
        "PS_FSBL_firmware_RPU_PL_DMA_DDR_owner_exclusivity_proven":False,
        "actual_Vitis_generated_profile_ELF_admitted_only":True,
        "destructive_JTAG_launch_authorized":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fd:
        json.dump(result,fd,indent=2,sort_keys=True)
        fd.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("profile-elf","profile-map","original-elf","xsa","pins-header","out"):
        p.add_argument("--"+k,required=True,type=Path)
    a=p.parse_args()
    try:
        report=audit(a.profile_elf,a.profile_map,a.original_elf,
                     a.xsa,a.pins_header,a.out)
        print("P08_B44_SEPARATE_GENUINE_PROFILE_ELF_STATIC_SOURCE_ADMISSION_PASS=1")
        print("P08_B44_NEW_PROFILE_ELF_SHA="+report["new_profile_ELF_sha256"])
        print("P08_B44_NEW_PROFILE_MAP_SHA="+report["new_profile_linker_map_sha256"])
        print("P08_B44_NEW_PROFILE_REAL_KV260_RUN_EXECUTED=0")
        print("P08_B44_NEW_PROFILE_ELF_DESTRUCTIVE_JTAG_AUTHORIZED=0")
        print("P08_B44_PROFILE_ELF_OFFLINE_REPORT="+str(a.out))
        return 0
    except (orig.ElfNoGo,ProfileElfNoGo,TypeError,OSError,KeyError,ValueError) as e:
        print("P08_B44_PROFILE_A53_ELF_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
