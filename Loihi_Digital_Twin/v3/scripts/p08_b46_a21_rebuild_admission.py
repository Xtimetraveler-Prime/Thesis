#!/usr/bin/env python3
"""P08-B4.6.2 PC-ONLY newly rebuilt A2.1 source/ELF admission.

This verifies a DISTINCT, actually built candidate. It NEVER asserts the
old 2026-10-18 A2.1 ELF is recovered or a new candidate has passed the
original KV260 1024-image independent neural tests.

No JTAG/Vivado calls, source writes, original SHA override, TEST access
or changed frozen artifact. All build bytes stay on operator's PC.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="p08-b46-reconstructed-a2-1-host-source-elf-admission-v1"
HISTORICAL_A21_SHA="fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0"
NEW_A21_SHA="fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793"
P03_XSA_SHA="52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
ELF_ID=b"P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1"
PROHIBITED_ELF_ID=b"P07_A4_2B_PERSISTENT_KV260_A53_FROZEN_TRACK_A_V1"
A_BUILD_REL=Path("vitis_workspace/p08_a2_board.elf")
SOURCES={
 "software/p08":("p08_a2_board.c","p08_a2_timing.c","p08_a2_timing.h"),
 "software/p07":("p07_a4_stream.c","p07_a4_supervisor.c",
                 "p07_a2_runtime.c","p07_a1_ingress.c","p07_a2_sha256.c"),
 "software/p07/include":("p07_a1_ingress.h","p07_a2_runtime.h",
                          "p07_a2_batch.h","p07_a2_sha256.h",
                          "p07_a4_stream.h","p07_a4_supervisor.h"),
 "software/p03":("p03_runtime.c","p03_hw_adapter.c",
                 "p03_hw_runtime_bridge.c","p03_hw_xilinx_io.c"),
 "software/p03/include":("p03_mmio.h","p03_runtime.h",
                         "p03_hw_adapter.h","p03_hw_runtime_bridge.h",
                         "p03_hw_xilinx_io.h"),
}
P07_HEADERS=SOURCES["software/p07/include"]

class CandidateNoGo(ValueError):
    pass

def must(ok:bool,why:str)->None:
    if not ok:
        raise CandidateNoGo("NO-GO: "+why)

def sha(path:Path)->str:
    must(path.is_file() and not path.is_symlink(),
         "missing/symlinked input file "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def validate_elf_header_and_loads(blob:bytes)->dict:
    must(len(blob)>=64 and blob[:6]==b"\x7fELF\x02\x01",
         "candidate is not little-endian 64bit ELF")
    etype,emachine=struct.unpack_from("<HH",blob,16)
    must(etype in (2,3) and emachine==183,
         "ELF is not AArch64 executable/shared-object")
    phoff=struct.unpack_from("<Q",blob,32)[0]
    phentsize,phnum=struct.unpack_from("<HH",blob,54)
    must(phnum>0 and phentsize>=56 and
         phoff+phentsize*phnum<=len(blob),
         "ELF program header bounds malformed")
    loads=[]
    for i in range(phnum):
        ptype,flags,offset,vaddr,paddr,filesz,memsz,align=struct.unpack_from(
            "<IIQQQQQQ",blob,phoff+phentsize*i)
        if ptype!=1:
            continue
        must(memsz>0 and memsz>=filesz and offset+filesz<=len(blob),
             "invalid ELF PT_LOAD file/memory span")
        for start in (vaddr,paddr):
            must(start+memsz<=2**64 and
                 not(start < 0x44000000 and start+memsz > 0x40000000),
                 "A2.1 PT_LOAD overlaps reserved original 64MiB DDR")
        loads.append({"vaddr_hex":hex(vaddr),"paddr_hex":hex(paddr),
                      "filesz":filesz,"memsz":memsz,"flags":flags})
    must(bool(loads),"A2.1 ELF has no valid PT_LOAD entries")
    must(ELF_ID in blob and PROHIBITED_ELF_ID not in blob,
         "ELF is not original-source A2.1 image-timing firmware identity")
    return {"aarch64_little_endian_elf64":True,"PT_LOAD":loads,
            "original_64MiB_DDR_disjoint":True}

def attest(build:Path,xsa:Path,out:Path)->dict:
    must(build.is_absolute() and build.is_dir() and not build.is_symlink() and
         not build.resolve().is_relative_to(ROOT.resolve()),
         "isolated existing persistent build dir outside checkout required")
    must("/tmp/" not in str(build)+"/" and "/var/tmp/" not in str(build)+"/" and
         not str(build).startswith(("/tmp","/var/tmp","/dev/shm")),
         "historical volatile /tmp or /var/tmp not a durable build root")
    must(out.is_absolute() and out.parent.is_dir() and
         not out.exists() and not out.is_symlink() and
         not out.resolve().is_relative_to(ROOT.resolve()),
         "fresh no-overwrite external JSON path required")
    must(out.resolve()!=build.resolve() and
         not out.resolve().is_relative_to(build.resolve()),
         "source build must stay immutable (report outside build)")
    must(xsa.is_absolute() and sha(xsa)==P03_XSA_SHA,
         "original accepted P03.2c routed hardware XSA SHA changed")
    elf=build/A_BUILD_REL
    actual=sha(elf)
    must(actual==NEW_A21_SHA,"distinct operator-rebuilt A2.1 SHA pin changed")
    must(actual!=HISTORICAL_A21_SHA,
         "rebuild must NOT impersonate historically accepted original A2.1")
    ph=validate_elf_header_and_loads(elf.read_bytes())
    identity=build/"build_identity.txt"
    lines=identity.read_text().splitlines() if identity.is_file() and not identity.is_symlink() else []
    required={
        "P08_A2_1_XSA_SHA256="+P03_XSA_SHA,
        "P08_A2_1_ELF="+str(elf),
        "P08_A2_1_ELF_SHA256="+NEW_A21_SHA,
        "P08_A2_1_VITIS_BUILD_PASS=1",
        "P08_A2_1_KV260_LATENCY=NOT_RUN",
    }
    must(required.issubset(set(lines)),
         "rebuilt A2.1 identity/NOT_RUN provenance incomplete")
    log=build/"vitis_build.log"
    must(log.is_file() and not log.is_symlink() and
         "P08_A2_A53_VITIS_BUILD_PASS=1" in log.read_text(errors="replace"),
         "real Vitis build success receipt not present")
    hdr=build/"elf_program_headers.txt"
    must(hdr.is_file() and not hdr.is_symlink() and
         "LOAD" in hdr.read_text(),
         "builder original readelf PT_LOAD check missing")

    source_dir=build/"source"
    checks={}
    for relative,names in SOURCES.items():
        for name in names:
            built=source_dir/name
            if relative=="software/p07/include":
                built=source_dir/"include"/name
            original=ROOT/relative/name
            must(sha(built)==sha(original),
                 "A2.1 staged source differs from current frozen Git source "+name)
            checks[str(relative+"/"+name)]=sha(built)
            # Existing original build script keeps the flat staged P07 include
            # as well as the nested include for the app component.
            if relative=="software/p07/include":
                must(sha(source_dir/name)==sha(original),
                     "flat original P07 header drift "+name)
    output={
        "schema":SCHEMA,
        "historical_ACCEPTED_A21_elf_sha256_UNCHANGED":HISTORICAL_A21_SHA,
        "operator_NEW_distinct_A21_candidate_elf_sha256":NEW_A21_SHA,
        "operator_NEW_candidate_ELF":str(elf),
        "operator_NEW_candidate_build_root":str(build),
        "original_accepted_P03_XSA_SHA256":P03_XSA_SHA,
        "source_Git_sha256_checks":checks,
        "original_A2_1_source_files_byte_exact_to_rebuilt_stage":True,
        "original_builder_success_and_not_run_receipts":True,
        "ELF_header_and_PT_LOAD_checks":ph,
        "historical_original_A2_1_ELF_recovered":False,
        "new_A2_1_candidate_PC_build_source_admission_pass":True,
        "new_A2_1_candidate_KV260_1024_neural_oracle_acceptance":False,
        "new_A2_1_candidate_A53_timing_boundary_equivalence_proven":False,
        "new_A2_1_candidate_JTAG_authorized":False,
        "repeated_A_B_AUTH_ONCE_six_session_hardware_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "new_board_or_XSDB_contact":False,
    }
    with out.open("x",encoding="utf-8") as f:
        json.dump(output,f,indent=2,sort_keys=True)
        f.write("\n")
    return output

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",required=True,type=Path)
    parser.add_argument("--xsa",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        obj=attest(args.build,args.xsa,args.out)
    except (CandidateNoGo,OSError,ValueError,KeyError,TypeError,struct.error) as e:
        print("P08_B46_NEW_A21_CANDIDATE_NO_GO="+str(e),file=sys.stderr)
        return 3
    print("P08_B46_NEW_A21_SOURCE_AND_REAL_ELF_PC_ONLY_PASS=1")
    print("P08_B46_OLD_A21_HISTORICAL_ACCEPTANCE_REPRODUCED=0")
    print("P08_B46_NEW_A21_PHYSICAL_NEURAL_PARITY_AND_TIMING_PENDING=1")
    print("P08_B46_KV260_JTAG_AUTHORIZED=0")
    print("P08_B46_NEW_A21_ADMISSION_REPORT="+str(args.out))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
