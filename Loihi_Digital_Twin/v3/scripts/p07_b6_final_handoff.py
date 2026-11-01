#!/usr/bin/env python3
"""P07-B.6.3 board-local 27core original TRAIN full P07-B final handoff gate.

PC ONLY; original official MNIST TEST SEALED. Nothing here touches KV260,
changes hardware/model, merges GitHub branches, or authorizes P08-B.
--mode review reopens the *actual* copied B6.2 archive, independent
integrity report, the genuine user source B6.1 seal and accepted B5.4
receipt, and checks remote origin/main's original literature Git blob.

--mode accept requires the SAME complete independent real source checks
plus an explicit operator final P07-B.6 handoff authorization token.
A valid archive, review and user approval may close P07-B's bounded
27core board-local physical inference work without claiming every packet
word, independent boot-powercycle instrumentation, DDR owner exclusivity
or MNIST official TEST. Never infer a PR merge from final acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

import p07_b6_verify_reproducibility as audit
import p07_b6_reproducibility_bundle as bundle
import p07_b6_freeze_manifest as freeze
import p07_b6_literature_merge_guard as lit
import p07_b5_scaled_validation as old

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="p07-b6-3-original-trained-27core-complete-P07-B-physical-handoff-v1"
CONFIRM_TOKEN="ACCEPT_P07_B_FINAL_27CORE_FREEZE_AND_HANDOFF_KEEP_TEST_SEALED_AND_MAIN_UNMERGED"
B5_ACCEPT_SHA="d72abc426a0d7a54d5a70994f75de9fca31862441d6507feb0b57c3e3fbbf7b9"
B5_ATTEST_SHA="4dd6cf0d02c477a2992b55b8bc2454ee9800c94ccce78f6cee25a32f2dc7fa31"
B5_REVIEW_SHA="aacc1a466e323f82d8c5eafda268c4f808cf878d6352b685f704473fab6fa0eb"

class HandoffNoGo(ValueError):
    pass

def require(yes:bool,why:str)->None:
    if not yes: raise HandoffNoGo("NO-GO: "+why)

def review(args)->dict:
    require(args.mode in ("review","accept"),"invalid final P07-B mode")
    for name in ("seal","package","bundle_audit","b5_accept"):
        file=getattr(args,name)
        require(isinstance(file,Path) and file.is_absolute() and
                file.exists() and not file.is_symlink() and
                not file.resolve().is_relative_to(ROOT),
                "genuine external P07-B original input required: "+name)
    require(args.seal.is_file() and args.bundle_audit.is_file() and
            args.b5_accept.is_file() and args.package.is_dir(),
            "B6.1 seal and B6.2 independent physical bundle audit files required")

    # Authenticate accepted source report against previously recorded operator
    # receipt; DO NOT substitute a synthetic object, success marker or quote.
    require(bundle.sha(args.b5_accept)==B5_ACCEPT_SHA,
            "user's final original B5.4 accepted source changed")
    seal=old.read_json(args.seal)
    require(seal.get("schema")==freeze.SCHEMA and
            seal.get("mode")=="seal" and
            seal.get("B5_formal_operator_acceptance_verified") is True and
            seal.get("B6_1_host_only_freeze_inventory_completed") is True and
            seal.get("B6_final_hardware_freeze_accepted") is False and
            seal.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
            seal.get("operator_accepted_B5_4_report_SHA256")==B5_ACCEPT_SHA and
            seal.get("operator_attestation_source_SHA256")==B5_ATTEST_SHA and
            seal.get("operator_original_5run_numerical_review_sha256")==B5_REVIEW_SHA and
            seal.get("B5_original_five_physical_numerical_validation_pass") is True and
            seal.get("B5_raw_neuron_bytewise_scalar_parity_pass") is True and
            seal.get("immutable_original_B24_33_file_freeze_verified") is True and
            seal.get("original_B24_manifest_entries_individually_SHA256_revalidated")==33 and
            seal.get("P07_B_complete") is False and
            seal.get("main_merged") is False,
            "genuine five-session B6.1 originally sealed source and acceptance fields drift")
    accepted=old.read_json(args.b5_accept)
    require(accepted.get("P07_B5_final_acceptance") is True and
            accepted.get("operator_explicit_final_B5_acceptance") is True and
            accepted.get("operator_attested_cold_boot_and_recovery_all_five_sessions") is True and
            accepted.get("B5_RAW_physical_trace_SHA256")==freeze.RAW_SHA and
            accepted.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
            accepted.get("independent_board_powercycle_instrumentation_proof") is False and
            accepted.get("boot_firmware_and_other_DDR_owner_independently_proven") is False,
            "genuine operator B5 acceptance scope changed")

    # ALWAYS independently reopen EVERY archived physical/frozen/firmware
    # byte in portable bundle. Operator's prior JSON cannot replace this check.
    freshly=audit.verify(args.package)
    reported=old.read_json(args.bundle_audit)
    require(reported==freshly,
            "user-supplied independent B6.2 package recheck differs from freshly recomputed source evidence")
    package_manifest=old.read_json(args.package/"handoff_manifest.json")
    files=package_manifest["files"]
    require(files["acceptance/B6_1_accepted_source_freeze.json"]["sha256"]==
            bundle.sha(args.seal) and
            files["acceptance/B5_4_user_accepted.json"]["sha256"]==
            B5_ACCEPT_SHA and
            files["acceptance/B5_4_operator_attestation.json"]["sha256"]==
            B5_ATTEST_SHA,
            "B6.2 physical package isn't bound to exactly accepted B6.1/B5.4+attestation")
    stored_seal=old.read_json(args.package/"acceptance/B6_1_accepted_source_freeze.json")
    require(stored_seal==seal,
            "archive B6.1 seal differs from user original source file")
    raw_source=files["physical_evidence/RAW0/b5_raw_physical_trace_840320.bin"]
    require(raw_source["bytes"]==840320 and raw_source["sha256"]==freeze.RAW_SHA,
            "exact physical 26x1010-neuron SHA no longer present in handoff")
    require(freshly["all_copy_sources_SHA256_and_lengths_independently_verified"] is True and
            freshly["original_B24_manifest_and_all_33_assets_independently_admitted"] is True and
            freshly["B5_formal_five_session_acceptance_archived"] is True and
            freshly["B6_final_acceptance"] is False and
            freshly["P07_B_complete"] is False and
            freshly["main_merged"] is False,
            "B6.2 original signed 33core frozen source/hardware bundle not verified")

    # Recheck live fetched main in addition to preserved source-side Git blob.
    literature=lit.verify_literature(lit.REPO,"origin/main")
    require(literature["checked_main_tree_literature_blob_sha"]==
            freeze.MAIN_LITERATURE_BLOB_SHA and
            package_manifest["main_only_LitReview_git_blob"]==
            freeze.MAIN_LITERATURE_BLOB_SHA,
            "main's independent original LitReview.md no longer byte-identical")
    out={
        "schema":SCHEMA,
        "mode":args.mode,
        "P07_B5_final_operator_acceptance_revalidated":True,
        "P07_B6_1_original_source_and_five_physical_evidence_seal_revalidated":True,
        "P07_B6_2_full_portable_archive_independent_bytewise_verifier_pass":True,
        "original_27core_B24_trained_checkpoint_and_P03_XSA_preserved":True,
        "original_4_V3_TRAIN_0_1_2_0_and_one_B5_raw_physical_receipts_archived":True,
        "original_TRAIN0_26260_neuron_840320B_physical_trace_equal_independent_scalar":True,
        "full_raw_physical_trace_SHA256":freeze.RAW_SHA,
        "original_P03_XSA_SHA256":freeze.P03_XSA_SHA,
        "original_V3_A53_ELF_SHA256":freeze.V3_ELF_SHA,
        "original_V3_A53_map_SHA256":freeze.V3_MAP_SHA,
        "new_B5_A53_ELF_SHA256":freeze.ELF_SHA,
        "new_B5_A53_map_SHA256":freeze.MAP_SHA,
        "original_B2_4_33_signed_assets_independently_verified":True,
        "original_20_384_input_routes_and_1_000_output_routes_frozen":True,
        "source_B6_1_seal_SHA256":bundle.sha(args.seal),
        "source_B5_4_operator_accepted_SHA256":B5_ACCEPT_SHA,
        "source_B5_operator_five_session_attestation_SHA256":B5_ATTEST_SHA,
        "portable_B6_2_complete_bundle_manifest_SHA256":
            freshly["bundle_handoff_manifest_SHA256"],
        "original_B6_2_independent_report_SHA256":
            bundle.sha(args.bundle_audit),
        "original_MAIN_LitReview_git_blob":freeze.MAIN_LITERATURE_BLOB_SHA,
        "current_origin_main_LitReview_exact_original_blob_verified":True,
        "operator_attested_cold_power_cycles_and_JTAG_not_hardware_instrumented":True,
        "boot_firmware_and_other_DDR_owner_exclusivity_independently_proven":False,
        "every_individual_packet_word_physically_verified":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "new_KV260_board_contact":False,
        "operator_final_P07_B_acceptance":False,
        "P07_B6_final_hardware_freeze_accepted":False,
        "P07_B_complete":False,
        "P08_B_started":False,
        "github_main_merged":False,
    }
    if args.mode=="review":
        require(args.confirm_final_acceptance is None,
                "review must not accept the operator final acceptance token")
        return out
    require(args.confirm_final_acceptance==CONFIRM_TOKEN,
            "separate explicit final original physical P07-B project acceptance token required")
    out.update({
        "operator_final_P07_B_acceptance":True,
        "P07_B6_final_hardware_freeze_accepted":True,
        "P07_B_complete":True,
        "P08_B_started":False,
        "github_main_merged":False,
        "bounded_handoff_note":"Original 27core/3-slot board-local physical inference validated on selected signed TRAIN 0/1/2 frames only; neuron-level raw parity proven on original TRAIN0. Never claim official TEST, every routed packet word, unproven DDR exclusive ownership or instrumented cold power-cycle. Separate Git merges and next benchmark protocol require their own explicit operator approval."
    })
    return out

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("review","accept"),default="review")
    for name in ("seal","package","bundle-audit","b5-accept","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--confirm-final-acceptance")
    args=p.parse_args()
    try:
        old.require_external_report(args.out)
        result=review(args)
        old.write_report(args.out,result)
        print("P07_B6_3_ORIGINAL_27CORE_SIGNED_PHYSICAL_ARCHIVE_FINAL_RECHECK_PASS=1")
        print("P07_B6_3_MAIN_ONLY_LITREVIEW_ORIGINAL_GIT_BLOB_PASS=1")
        print("P07_B6_3_ORIGINAL_MNIST_TEST_SEALED=1")
        print("P07_B6_3_NEW_BOARD_CONTACT=0")
        print("P07_B6_3_FINAL_OPERATOR_ACCEPTANCE="+
              ("1" if result["P07_B_complete"] else "0"))
        print("P07_B6_3_GITHUB_MAIN_MERGED=0")
        print("P07_B6_3_FINAL_REPORT="+str(args.out))
        return 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        print("P07_B6_3_FINAL_HANDOFF_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
