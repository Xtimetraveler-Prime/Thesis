#!/usr/bin/env python3
"""P07-B.6.2 PC-only complete original 27core physical evidence handoff package.

Build only from a genuine source-revalidated B6.1 --mode seal receipt,
accepted B5.4 operator report, physical source folders, genuine original
V3 and new B5 A53 ELF/map, original B2.4 freeze, original routes/P03 XSA
and read-only main literature blob check. NEVER JTAG, retrain, read TEST,
alter accepted inputs, merge branches, or trust a bare 'PASS' flag.

Copies unchanged signed sources and physical session evidence into a NEW
external directory, records SHA256 for EVERY copied file, and independently
rehashes the output. Operators keep this as a new audit package rather than
overwriting their original real KV260 evidence. B6.2 prep is NOT B6 final.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import p07_b6_freeze_manifest as b6
import p07_b6_literature_merge_guard as lit
import p07_b5_scaled_validation as reports

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
SCHEMA="p07-b6-2-original-27core-a53-xsa-physical-evidence-full-reproducibility-package-v1"
MAX_FILES=1500
MAX_FILE_BYTES=1<<30
class BundleNoGo(ValueError): pass

def require(ok:bool,msg:str)->None:
    if not ok: raise BundleNoGo("NO-GO: "+msg)

def validate_relative(name:str)->Path:
    require(isinstance(name,str) and len(name)>0 and
            not name.startswith("/") and chr(92) not in name and
            all(p not in ("..",".","") for p in name.split("/")),
            "unsafe evidence relative name: "+repr(name))
    p=Path(name)
    require(not p.is_absolute(),"absolute evidence path rejected")
    return p

def sha(path:Path)->str:
    require(path.is_file() and not path.is_symlink(),
            "expected regular signed evidence, no symlinks: "+str(path))
    require(path.stat().st_size<=MAX_FILE_BYTES,
            "single signed evidence file exceeds 1GiB explicit limit")
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()

def validate_sealed_inputs(args)->tuple[dict,dict]:
    source=reports.read_json(args.seal)
    require(source.get("schema")==b6.SCHEMA and
            source.get("mode")=="seal" and
            source.get("B5_formal_operator_acceptance_verified") is True and
            source.get("B6_1_host_only_freeze_inventory_completed") is True and
            source.get("B6_final_hardware_freeze_accepted") is False and
            source.get("P07_B_complete") is False and
            source.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
            "genuine separately approved B5 accepted and signed B6.1 SEALED preflight required")
    expected={
        "operator_accepted_B5_4_report_SHA256":args.accept,
        "operator_attestation_source_SHA256":args.attest,
    }
    for key,path in expected.items():
        require(source.get(key)==sha(path),
                "accepted B5.4 report or signed user physical attestation has changed: "+key)
    accepted=reports.read_json(args.accept)
    require(accepted.get("P07_B5_final_acceptance") is True and
            accepted.get("operator_explicit_final_B5_acceptance") is True and
            accepted.get("operator_attested_cold_boot_and_recovery_all_five_sessions") is True and
            accepted.get("boot_firmware_and_other_DDR_owner_independently_proven") is False,
            "actual accepted operator B5 report not in bounded accepted scope")
    liter=lit.verify_literature(REPO,"origin/main")
    require(liter["checked_main_tree_literature_blob_sha"]==
            source["main_only_LitReview_md_expected_blob_SHA"],
            "original main Git literature blob changed or not fetched")
    require(sha(args.v3_elf)==b6.V3_ELF_SHA and
            sha(args.v3_map)==b6.V3_MAP_SHA,
            "original physically accepted V3 ELF or GNU linker map SHA differs")
    require(len(source.get("source_sha256_manifest",{}))==b6.ORIGINAL_B24_ASSET_COUNT+1+len(b6.TRAIN_FILES)+3,
            "B6 source manifest must cover all 33 original frozen assets, routes, XSA and new A53")
    dirs=source.get("operator_original_physical_V3_evidence_dirs")
    raw=source.get("operator_original_physical_RAW_evidence_dir")
    require(isinstance(dirs,list) and len(dirs)==4 and
            len(set(dirs))==4 and isinstance(raw,str) and raw not in dirs,
            "original four V3 and fifth B5 raw source evidence directory list changed")
    require(all(Path(p).is_absolute() and Path(p).is_dir() and
                not Path(p).is_symlink() for p in [*dirs,raw]),
            "actual original 5 hardware evidence directory trees missing")
    return source, liter

def source_items(args,seal:dict)->dict[str,Path]:
    items={}
    for name in seal["source_sha256_manifest"]:
        rel=validate_relative(name)
        first=rel.parts[0]
        remainder=Path(*rel.parts[1:])
        roots={
            "original_b24":args.frozen_dir,
            "original_TRAIN_routes":args.routes_dir,
            "original_P03_XSA":args.reports,
            "new_B5_A53":args.build_dir/"vitis_workspace",
        }
        require(first in roots and len(rel.parts)>1,
                "unknown signed source manifest namespace: "+name)
        items["source/"+name]=roots[first]/remainder
    items["firmware/original_V3_A53_accepted.elf"]=args.v3_elf
    items["firmware/original_V3_A53_accepted.map"]=args.v3_map
    items["acceptance/B5_4_user_accepted.json"]=args.accept
    items["acceptance/B5_4_operator_attestation.json"]=args.attest
    items["acceptance/B6_1_accepted_source_freeze.json"]=args.seal
    for i,p in enumerate(seal["operator_original_physical_V3_evidence_dirs"]):
        source=Path(p)
        for f in source.rglob("*"):
            require(not f.is_symlink(),"hardware evidence contains symlink: "+str(f))
            if f.is_dir(): continue
            require(f.is_file(),"hardware evidence contains special file: "+str(f))
            rel=f.relative_to(source).as_posix()
            validate_relative(rel)
            key=f"physical_evidence/original_V3_{i}/"+rel
            require(key not in items,"duplicate physical evidence path: "+key)
            items[key]=f
    source=Path(seal["operator_original_physical_RAW_evidence_dir"])
    for f in source.rglob("*"):
        require(not f.is_symlink(),"RAW evidence contains symlink: "+str(f))
        if f.is_dir(): continue
        require(f.is_file(),"RAW evidence contains special file: "+str(f))
        rel=f.relative_to(source).as_posix()
        validate_relative(rel)
        key="physical_evidence/RAW0/"+rel
        require(key not in items,"duplicate raw evidence path: "+key)
        items[key]=f
    require(len(items)<=MAX_FILES,"physical handoff has too many original source files")
    return dict(sorted(items.items()))

def bundle(args)->dict:
    require(args.out_dir.is_absolute() and
            not args.out_dir.exists() and
            args.out_dir.parent.is_dir() and
            not args.out_dir.resolve().is_relative_to(REPO.resolve()),
            "new external output directory required; original data and Git tree never overwritten")
    sealed,liter=validate_sealed_inputs(args)
    items=source_items(args,sealed)
    # A NEW output may be a sibling of B5 acceptance JSON in the same
    # external Thesis_Evidence folder. Disallow nested writes inside
    # original source/firmware/physical-session trees, not the parent.
    roots=[args.frozen_dir,args.routes_dir,args.reports,args.build_dir,
           *(Path(p) for p in sealed["operator_original_physical_V3_evidence_dirs"]),
           Path(sealed["operator_original_physical_RAW_evidence_dir"])]
    require(all(not args.out_dir.resolve().is_relative_to(p.resolve()) for p in roots),
            "do not create handoff inside any original source or physical evidence tree")
    checks={}
    for name,source in items.items():
        digest=sha(source)
        manifest_sha=sealed["source_sha256_manifest"].get(name.removeprefix("source/"))
        if name.startswith("source/"):
            require(digest==manifest_sha,"original signed source changed after B6.1 seal: "+name)
        checks[name]={"sha256":digest,"bytes":source.stat().st_size}
    require(checks["firmware/original_V3_A53_accepted.elf"]["sha256"]==b6.V3_ELF_SHA and
            checks["firmware/original_V3_A53_accepted.map"]["sha256"]==b6.V3_MAP_SHA,
            "accepted original physical V3 firmware changed")
    payload={
        "schema":SCHEMA,
        "status":"B6_2_PACKAGE_CANDIDATE_PENDING_USER_INDEPENDENT_RECHECK",
        "B5_4_real_operator_accepted":True,
        "B6_1_original_hardware_and_sources_signed":True,
        "B6_2_handoff_contains_all_five_board_session_files":True,
        "signed_original_V3_elf_and_map_copied":True,
        "original_frozen_27core_and_all_routes_copied":True,
        "physical_original_26tick_840320B_neuron_parity_SHA256":b6.RAW_SHA,
        "accepted_original_P03_XSA_sha256":b6.P03_XSA_SHA,
        "main_only_LitReview_git_blob":liter["checked_main_tree_literature_blob_sha"],
        "main_only_LitReview_md_preservation_origin_main_verified":True,
        "source_5_session_reboot_user_attested_not_instrumented":True,
        "DDR_owner_exclusivity_independently_proven":False,
        "per_packet_word_trace_full_parity_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "files":checks,
        "B6_final_acceptance":False,
        "P07_B_complete":False,
        "main_merged":False,
        "board_contact":False,
    }
    temp=Path(tempfile.mkdtemp(prefix=".p07_b6_2_",dir=args.out_dir.parent))
    try:
        for name,source in items.items():
            destination=temp/validate_relative(name)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with source.open("rb") as inp,destination.open("xb") as out:
                shutil.copyfileobj(inp,out,length=1<<20)
            require(sha(destination)==checks[name]["sha256"],
                    "copy changed original physical/source evidence bytes: "+name)
        (temp/"handoff_manifest.json").write_text(
            json.dumps(payload,sort_keys=True,indent=2)+"\n",
            encoding="utf-8")
        require(not args.out_dir.exists(),
                "target appeared during B6 packaging; do not overwrite")
        os.rename(temp,args.out_dir)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True)
        raise
    return payload

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("seal","accept","attest","frozen-dir","routes-dir",
                 "reports","build-dir","v3-elf","v3-map","out-dir"):
        p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    try:
        result=bundle(args)
        print("P07_B6_2_COMPLETE_ORIGINAL_SOURCE_AND_5_PHYSICAL_SESSION_COPY_SHA_PASS=1")
        print("P07_B6_2_ACCEPTED_ORIGINAL_V3_AND_B5_A53_FIRMWARE_COPY_PASS=1")
        print("P07_B6_2_MAIN_LITREVIEW_ORIGINAL_GIT_BLOB_PASS=1")
        print("P07_B6_2_NEW_PHYSICAL_BOARD_CONTACT=0")
        print("P07_B6_2_FINAL_ACCEPTANCE=0")
        print("P07_B6_2_EXTERNAL_PACKAGE="+str(args.out_dir))
        print("P07_B6_2_PACKAGE_MANIFEST_SHA256="+sha(args.out_dir/"handoff_manifest.json"))
        return 0
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as e:
        print("P07_B6_2_PACKAGE_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
