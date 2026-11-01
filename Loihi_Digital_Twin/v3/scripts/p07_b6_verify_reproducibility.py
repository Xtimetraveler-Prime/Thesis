#!/usr/bin/env python3
"""P07-B.6.2 PC-only independent validation of moved handoff bundle.

Reopens EVERY bundled file, requires exact source/evidence file set and
SHA256, revalidates all 33 signed original B2.4 frozen assets through
unchanged canonical verifier, original B5.4 final operator receipt,
accepted V3/new B5 ELF/map/XSA, physical 840320B B5 RAW trace,
main-only literature blob *identity recorded from previous source audit*.
Never claims current remote main was rechecked; never unseals official TEST,
contacts FPGA, retrains, modifies sources, or merges branches.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import p07_b6_reproducibility_bundle as pack
import p07_b6_freeze_manifest as b6
import p07_b5_scaled_validation as old
import p07_b4l1_stage_frozen_27core as b4l1
import p07_b6_literature_merge_guard as lit

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="p07-b6-2-independent-physical-handoff-archive-source-verified-v1"
RAW_FILE="physical_evidence/RAW0/b5_raw_physical_trace_840320.bin"
V3_ELF="firmware/original_V3_A53_accepted.elf"
V3_MAP="firmware/original_V3_A53_accepted.map"
NEW_ELF="source/new_B5_A53/p07_b5_raw_trace_v1.elf"
NEW_MAP="source/new_B5_A53/p07_b5_raw_trace_v1.map"
XSA="source/original_P03_XSA/p03_2_ps_mmio.xsa"
FROZEN="source/original_b24/frozen_manifest.json"
ACCEPT="acceptance/B5_4_user_accepted.json"
MANIFEST="handoff_manifest.json"
class VerifyNoGo(ValueError): pass

def require(ok:bool,description:str)->None:
    if not ok: raise VerifyNoGo("NO-GO: "+description)

def verify(package:Path)->dict:
    require(package.is_absolute() and package.is_dir() and
            not package.is_symlink() and
            not package.resolve().is_relative_to(ROOT),
            "real external source-backed reproducibility directory required")
    path=package/MANIFEST
    require(path.is_file() and not path.is_symlink(),
            "signed B6.2 handoff manifest missing")
    m=old.read_json(path)
    require(m.get("schema")==pack.SCHEMA and
            m.get("B5_4_real_operator_accepted") is True and
            m.get("B6_1_original_hardware_and_sources_signed") is True and
            m.get("B6_2_handoff_contains_all_five_board_session_files") is True and
            m.get("original_frozen_27core_and_all_routes_copied") is True and
            m.get("signed_original_V3_elf_and_map_copied") is True and
            m.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
            m.get("DDR_owner_exclusivity_independently_proven") is False and
            m.get("B6_final_acceptance") is False and
            m.get("P07_B_complete") is False and
            m.get("main_merged") is False,
            "B6.2 actual copied archive provenance/limitations not accepted")
    files=m.get("files")
    require(isinstance(files,dict) and len(files)<=pack.MAX_FILES,
            "invalid B6.2 per-file independent SHA index")
    required={RAW_FILE,V3_ELF,V3_MAP,NEW_ELF,NEW_MAP,XSA,FROZEN,ACCEPT,
              "acceptance/B5_4_operator_attestation.json",
              "acceptance/B6_1_accepted_source_freeze.json"}
    require(required.issubset(files),
            "missing raw physical neuron evidence, actual V3/new B5 firmware, frozen original source, P03 or B5 acceptance")
    for i in range(4):
        require(any(k.startswith(f"physical_evidence/original_V3_{i}/") for k in files),
                "one of four original historical genuine physical V3 session bundles missing")
    raw_count=sum(k.startswith("physical_evidence/RAW0/") for k in files)
    require(raw_count>1,"fifth original 840320B physical RAW evidence tree incomplete")
    require(sum(k.startswith("source/original_b24/") for k in files)==34,
            "all 33 signed B2.4 frozen assets and original frozen manifest required")
    seen={MANIFEST}
    for name,rec in files.items():
        rel=pack.validate_relative(name)
        require(isinstance(rec,dict) and
                isinstance(rec.get("sha256"),str) and
                len(rec["sha256"])==64 and
                type(rec.get("bytes")) is int and
                0<=rec["bytes"]<=pack.MAX_FILE_BYTES,
                "malformed physical/source per-file acceptance SHA/size: "+name)
        p=package/rel
        require(p.stat().st_size==rec["bytes"] and
                pack.sha(p)==rec["sha256"],
                "physical or frozen source bytewise SHA/size changed: "+name)
        seen.add(name)
    actual=set()
    for p in package.rglob("*"):
        require(not p.is_symlink(),"B6.2 archive evidence symlink forbidden: "+str(p))
        if p.is_file():
            actual.add(p.relative_to(package).as_posix())
        elif not p.is_dir():
            raise VerifyNoGo("NO-GO: archive contains special file: "+str(p))
    require(actual==seen,
            "B6.2 physical package has extra/missing/unindexed source/evidence")
    require(files[RAW_FILE]["bytes"]==840320 and
            files[RAW_FILE]["sha256"]==b6.RAW_SHA and
            files[V3_ELF]["sha256"]==b6.V3_ELF_SHA and
            files[V3_MAP]["sha256"]==b6.V3_MAP_SHA and
            files[NEW_ELF]["sha256"]==b6.ELF_SHA and
            files[NEW_MAP]["sha256"]==b6.MAP_SHA and
            files[XSA]["sha256"]==b6.P03_XSA_SHA and
            files[FROZEN]["sha256"]==b4l1.FROZEN_SHA,
            "accepted signed physical RAW/V3 A53/B5 A53/P03/B2.4 original artifact identity differs")
    require(m.get("main_only_LitReview_git_blob")==lit.EXPECTED_BLOB_SHA,
            "archive failed to retain original main literature Git blob proof")
    b4l1.admit_freeze(package/"source/original_b24")
    accepted=old.read_json(package/ACCEPT)
    require(accepted.get("P07_B5_final_acceptance") is True and
            accepted.get("operator_attested_cold_boot_and_recovery_all_five_sessions") is True and
            accepted.get("operator_explicit_final_B5_acceptance") is True and
            accepted.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
            accepted.get("B5_RAW_physical_trace_SHA256")==b6.RAW_SHA and
            accepted.get("boot_firmware_and_other_DDR_owner_independently_proven") is False,
            "archived B5.4 original operator source proof not independently accepted")
    return {
        "schema":SCHEMA,
        "bundle_root":str(package.resolve()),
        "bundle_handoff_manifest_SHA256":pack.sha(path),
        "original_B24_manifest_and_all_33_assets_independently_admitted":True,
        "total_original_source_firmware_and_physical_files":len(files),
        "all_copy_sources_SHA256_and_lengths_independently_verified":True,
        "original_V3_B5_A53_and_P03_XSA_original_SHA256_verified":True,
        "B5_raw_original_840320_byte_physical_trace_sha256":b6.RAW_SHA,
        "B5_formal_five_session_acceptance_archived":True,
        "recorded_main_only_LitReview_original_blob_sha":lit.EXPECTED_BLOB_SHA,
        "main_current_Git_ref_independently_checked_here":False,
        "operator_attested_power_cycles_not_hardware_instrumented":True,
        "boot_firmware_DDR_owner_exclusivity_independently_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "board_contact":False,
        "B6_final_acceptance":False,
        "P07_B_complete":False,
        "main_merged":False,
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    try:
        old.require_external_report(a.out)
        result=verify(a.package)
        old.write_report(a.out,result)
        print("P07_B6_2_ARCHIVED_EVERY_ORIGINAL_SOURCE_AND_PHYSICAL_FILE_INDEPENDENT_SHA256_PASS=1")
        print("P07_B6_2_ORIGINAL_33_FILE_B24_FREEZE_AND_5_REAL_BOARD_SESSIONS_PASS=1")
        print("P07_B6_2_KV260_CONTACT=0")
        print("P07_B6_2_FINAL_ACCEPTANCE=0")
        print("P07_B6_2_INDEPENDENT_ARCHIVE_REPORT="+str(a.out))
        return 0
    except (OSError,TypeError,ValueError,KeyError,RuntimeError) as exc:
        print("P07_B6_2_HARDWARE_EVIDENCE_ARCHIVE_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
