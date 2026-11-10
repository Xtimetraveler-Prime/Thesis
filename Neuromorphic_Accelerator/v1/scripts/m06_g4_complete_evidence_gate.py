#!/usr/bin/env python3
"""M06 G4 evidence-completeness gate before simulation-scoped acceptance.

OFFLINE/READ-ONLY. No originals or Vivado RTL copied, no FPGA operations.
Every first genuine owner gate must have its own independently auditable
PASS ZIP. The occurrence of a later PASS does NOT substitute for a
missing intermediate result, even when the owner loop was sequential.

This is a conservative evidence gate, not physical PS DDR certification.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
from zipfile import ZipFile, BadZipFile

from m06_g4_owner_zip_audit import check_zip, GATES

G3_PARITY_SHA256 = (
    "c3c9c6c1b21989b11f2d632b306981b10261aa1c6aedd8e54f7cd1c88ed4eb6c"
)
G3_PARITY_MARKER = "M06_G3_3_ACTUAL_HLS_AMD_M02_M03_TRACE_STATE_PARITY_XSIM_PASS"
MODES = ("g4_first_b_slverr","g4_first_r_slverr",
         "g4_stalled_b","g4_discard_restore")
ORIGINALS = ("hls_sources_before_sha256.txt",
             "hls_dat_sources_before_sha256.txt",
             "vendor_sha_before.txt")

def require(condition:bool, why:str)->None:
    if not condition:
        raise ValueError(why)

def read_g3(path:Path,*,expected_sha256:str=G3_PARITY_SHA256)->dict:
    require(path.is_file(),"M06 G3.3 independently verified parity ZIP missing: "+str(path))
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    require(digest==expected_sha256,
            "M06 G3.3 accepted original owner ZIP SHA mismatch")
    with ZipFile(path) as z:
        names=set(z.namelist())
        needed={"result.txt","commit.txt","07_xsim.log",
                "original_xci_after_sha_check.txt",*ORIGINALS,
                *(s.replace("_before_","_after_") for s in ORIGINALS)}
        require(needed<=names,
                "M06 G3.3 accepted original parity ZIP incomplete")
        require(z.read("result.txt").strip()==b"exit_status=0",
                "M06 G3.3 original parity failed")
        marker=z.read("07_xsim.log").decode("utf-8",errors="replace")
        require(marker.count(G3_PARITY_MARKER)==1 and
                "$finish called at time" in marker and
                "exit 0" in marker and
                "32_NEURONS 4_TICKS" in marker and
                "B_BEFORE_AR NO_DDR_NO_BOARD" in marker and
                "M06_G3_3_PARITY_FAIL" not in marker,
                "M06 G3.3 genuine original HLS/AMD neural parity missing")
        for name,size in zip(ORIGINALS,(40,14,67)):
            before=z.read(name)
            after=z.read(name.replace("_before_","_after_"))
            require(before==after and len(before.splitlines())==size,
                    "M06 G3.3 original source integrity drift "+name)
        xci=z.read("original_xci_after_sha_check.txt").decode(errors="replace")
        require(len(xci.strip().splitlines())==2 and
                all(".xci: OK" in row for row in xci.strip().splitlines()),
                "M06 G3.3 original AMD width-converter XCI identity invalid")
        return {"sha256":digest,
                "original":{name:z.read(name) for name in ORIGINALS}}

def verify_complete(parity:Path, artifacts:dict[str,Path],
                    *,expected_g3_sha256:str=G3_PARITY_SHA256)->dict:
    require(set(artifacts)==set(MODES),
            "M06 G4 missing mode-specific owner ZIP path(s): "+
            ", ".join(sorted(set(MODES)-set(artifacts))))
    paths=[parity,*artifacts.values()]
    require(len({str(p.resolve()) for p in paths})==len(paths),
            "same ZIP path supplied for different owner experiments")
    # Check presence and COMPLETE G4 results up front. In particular,
    # the earlier original stalled B FIRST-FAIL archives remain failures;
    # the later recovery PASS cannot silently waive stalled B.
    for mode,path in artifacts.items():
        require(path.is_file(),
                "M06 G4 UNVERIFIED: independent "+mode+
                " original-owner ZIP MISSING: "+str(path))
    source=read_g3(parity,expected_sha256=expected_g3_sha256)
    reports={}
    for mode in MODES:
        path=artifacts[mode]
        report=check_zip(path,mode)
        with ZipFile(path) as z:
            for name,reference in source["original"].items():
                require(z.read(name)==reference,
                    "M06 original HLS/dat/AMD identity changed across accepted "
                    "owner experiments: "+mode+" "+name)
        reports[mode]=report
    return {
        "status":"M06_G4_ALL_ORIGINAL_OWNER_ZIPS_AUDITED",
        "g3_parity_sha256":source["sha256"],
        "g4":reports,
        "scope":"OFFLINE_64K_SCRATCH_ONLY_NO_AUTO_ROLLBACK_NO_PS_DDR_NO_BOARD"
    }

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--g3-parity",type=Path,required=True)
    for mode in MODES:
        ap.add_argument("--"+mode.replace("_","-"),type=Path,required=True)
    args=ap.parse_args()
    files={mode:getattr(args,mode) for mode in MODES}
    try:
        result=verify_complete(args.g3_parity,files)
    except (OSError,ValueError,KeyError,BadZipFile) as error:
        print("M06_G4_CLOSEOUT_NOT_YET_ACCEPTED:",error,file=sys.stderr)
        return 2
    print(result["status"],
          "ORIGINAL_HLS_AMD_G3_PARITY_AND_4_G4_GATES_PASS",
          result["scope"])
    for mode,item in result["g4"].items():
        print(mode,"commit="+str(item["commit"]),
              "sha256="+str(item["zip_sha256"]))
    print("EVIDENCE_COMPLETENESS_ONLY_NO_PHYSICAL_CLAIM")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
