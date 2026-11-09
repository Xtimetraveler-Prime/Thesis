#!/usr/bin/env python3
"""Read-only audit of existing owner original AMD 2025.2 XSim A/B archive.

Never extract or copy original vendor source. The archive contains *logs*
and source hashes only. A genuine A+B PASS does not imply neural HLS,
8-slot RTL, physical DDR, AXI crash atomicity or whole M06 completion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

REQUIRED = (
    "result.txt", "commit.txt", "sha_before.txt", "sha_after.txt",
    "installed_vivado_glbl_sha256.txt",
    "02_original_vendor_compile_plan.json",
    "04_xelab.log", "05_xsim.log",
    "06_paged_xelab.log", "07_paged_xsim.log",
)
PRIOR_HEAD = "8c8326ffff1b0a604aab2fc3423394b61ff27b9a"
SIM_SHA = "0ec8a01dfc7c23825a8d5c8934c7f26dc5b92b924be88d51addd9e76555b8e12"
BD_SHA = "c3d7c5021f532aae29c860a63fb92da9529dac489f87a74267b9af82472444f3"
SIM_MARKER = "M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS"
PAGE_MARKER = "M06_ORIGINAL_VENDOR_PAGED_RTL_PASS"
FAULT_MARKER = "M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS"


def verify(archive: Path) -> dict:
    if archive.stat().st_size > 20_000_000:
        raise ValueError("overlarge owner evidence archive")
    with tarfile.open(archive, "r:gz") as source:
        members=source.getmembers()
        names=[m.name for m in members]
        if sorted(names)!=sorted(REQUIRED):
            raise ValueError("missing, extra, or repeated owner XSim evidence member")
        if any(not m.isfile() or m.size > 1_000_000 for m in members):
            raise ValueError("unexpected evidence member type or length")
        files={m.name:source.extractfile(m).read().decode("utf-8")
               for m in members}
    if files["result.txt"].strip()!="exit_status=0":
        raise ValueError("original vendor XSim runner did not exit successfully")
    if files["commit.txt"].strip()!=PRIOR_HEAD:
        raise ValueError("owner XSim provenance is not previously accepted commit")
    if files["sha_before.txt"]!=files["sha_after.txt"]:
        raise ValueError("original AMD source SHA changed during tool run")
    source_hashes=[line.split()[0] for line in
                   files["sha_before.txt"].strip().splitlines()]
    if source_hashes!=[SIM_SHA,BD_SHA]:
        raise ValueError("original vendor source digests not authenticated")
    glbl=files["installed_vivado_glbl_sha256.txt"].split()
    if len(glbl)!=2 or len(glbl[0])!=64 or not glbl[1].endswith("/glbl.v"):
        raise ValueError("invalid installed Vivado glbl provenance")
    plan=json.loads(files["02_original_vendor_compile_plan.json"])
    if (plan.get("vivado_original_source_count")!=186 or
        plan.get("selected_vendor_compilation_source_count")!=56 or
        len(plan.get("original_include_files",()))!=5):
        raise ValueError("original 186-entry Vivado source plan contradicted")
    for name in ("04_xelab.log","06_paged_xelab.log"):
        if "Vivado Simulator v2025.2" not in files[name]:
            raise ValueError("genuine installed 2025.2 elaboration log missing")
        if re.search(r"ERROR:|FATAL",files[name],re.I):
            raise ValueError("original elaboration had tool errors")
    raw=files["05_xsim.log"]
    paged=files["07_paged_xsim.log"]
    for name,log in (("stage A",raw),("stage B",paged)):
        if ("xsim v2025.2" not in log or
            not re.search(r"(?m)^exit 0\s*$",log)):
            raise ValueError(f"original {name} missing real XSim successful exit")
        if re.search(r"ERROR:|FATAL|M06_VENDOR_FAIL|M06_ORIGINAL_PAGED_FAIL",
                     log,re.I):
            raise ValueError(f"original {name} contains simulator fatal")
    if raw.count(SIM_MARKER)!=1 or not re.search(
        r"M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS writes=4 reads=14 "
        r"M00_wbeats=8 M00_rbeats=28 M00_wstalls=6",raw):
        raise ValueError("genuine original SmartConnect byte/AXI scoreboard incomplete")
    if paged.count(PAGE_MARKER)!=1 or paged.count(FAULT_MARKER)!=1:
        raise ValueError("original vendor page/poison checks incomplete")
    if not re.search(
        r"M06_ORIGINAL_VENDOR_PAGED_RTL_PASS fills=3 wb=1 "
        r"reload_byte_exact=1 M00_write=16 M00_read=48",paged):
        raise ValueError("original vendor page writeback/restore counts mismatch")
    if not re.search(
        r"M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS "
        r"M00_read=50 stalls=813",paged):
        raise ValueError("original vendor fault quarantine counts mismatch")
    return {
        "schema":"m06-original-vendor-xsim-evidence-attestation-2026-11-09",
        "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
        "original_owner_commit":PRIOR_HEAD,
        "original_sources_unchanged":True,
        "xsim_version":"2025.2",
        "original_smartconnect_stage_a":"VERIFIED_ORIGINAL_VENDOR_AXITRANSACTIONS",
        "original_paged_stage_b":"VERIFIED_ORIGINAL_VENDOR_PAGING_AND_POISON",
        "stage_c_neural_over_original_vendor":"NOT_IN_ARCHIVE_NOT_EXECUTED",
        "eight_slot_geometry_over_original_vendor":"NOT_IN_ARCHIVE_NOT_EXECUTED",
        "real_physical_ddr":"NOT_TESTED",
        "accepted_m05_hls_stream_neural_paging":"NOT_IN_THIS_ARCHIVE",
        "m06_milestone_complete":False,
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("new exclusive output JSON in existing directory required")
        report=verify(args.archive)
        with args.output.open("x",encoding="utf-8") as fp:
            json.dump(report,fp,sort_keys=True,indent=2)
            fp.write("\n")
    except (OSError,ValueError,json.JSONDecodeError,tarfile.TarError) as err:
        print("M06 authentic original vendor archive REJECTED: "+str(err),
              file=sys.stderr)
        return 2
    print("M06 ORIGINAL AMD VENDOR A+B EVIDENCE VERIFIED; "
          "M05 neural kernel + eight-slot original-vendor RTL still OPEN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
