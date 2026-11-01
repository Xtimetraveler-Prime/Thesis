#!/usr/bin/env python3
"""P07-B.5.4 independent original TRAIN multirun + strict physical RAW closeout.

PC-ONLY: NEVER touches JTAG, never modifies frozen B2.4, P03 PL/V3 ELF,
operator physical evidence, or official TEST. Re-opens all four original V3
board-run evidence trees AND separately signed 840320-byte B5 raw evidence.
Review mode: numerical acceptance only; explicit final operator signoff and
actual reboot attestations remain OPEN.

Accept mode: requires a SEPARATE, new operator-created JSON attestation for
ALL five real board sessions (0,1,2,0 + B5 RAW0), distinct directories,
cold boot BEFORE and cold power-cycle AFTER EACH, dedicated JTAG, explicit
acceptance of remaining unproven DDR ownership, plus exact operator command
acknowledgement. A JSON attestation represents what an operator affirms; it
is NOT independent firmware proof of a power-cycle. Do not generate or
silently set these facts automatically. Never merge to main here.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import p07_b5_scaled_validation as b5
import p07_b5_raw_physical_verify as raw

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="p07-b5-4-independent-final-original-27core-multirun-plus-raw-review-v1"
ATTEST_SCHEMA="p07-b5-4-operator-physical-powercycle-and-final-acceptance-v1"
FINAL_CONFIRM="ACCEPT_P07_B5_WITH_ATTESTED_COLD_BOOTS_AND_UNPROVEN_DDR_OWNERSHIP"
PINNED_RAW_SHA="7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d"
PINNED_MAILBOX_SHA="435b1c903f3323b3bfd156eb271202d82c8738ebe2a7a8c489e6aab7fcdd4d6b"
PINNED_RAW_FNV="0xB59CA8594D6E64AD"
PINNED_B5_ELF="0e018a9cabf45b7e65a366b9e21df0cc90cb5b072053cac8c19d2f601be1d2cf"
PINNED_B5_MAP="1e6cf5d0a9744378fb0aebe2e6271da661b8739a2fb930e983342477fd0e78c8"

class B54NoGo(ValueError):
    pass

def require(cond:bool,description:str)->None:
    if not cond:
        raise B54NoGo("NO-GO: "+description)

def ordered_runs(args)->list[tuple[int,Path]]:
    entries=[b5.parse_run_spec(spec) for spec in args.run]
    require(len(entries)==4 and [ordinal for ordinal,_ in entries]==[0,1,2,0],
            "four original V3 runs required in exact historical order 0,1,2,0")
    sources=[p.resolve() for _,p in entries]
    require(len(set(sources))==4,"four ORIGINAL V3 sessions must use distinct evidence folders")
    require(args.raw_evidence.resolve() not in sources,
            "B5 raw physical run must be a fifth distinct evidence folder")
    return entries

def verify_immutable_user_report(path:Path,computed:dict,label:str)->None:
    saved=b5.read_json(path)
    require(saved==computed,
            "saved original user " +label+" report differs from freshly recomputed physical audit")

def independent_review(args)->tuple[dict,list[tuple[int,Path]]]:
    runs=ordered_runs(args)
    original_args=SimpleNamespace(mode="consolidate",
        frozen_dir=args.frozen_dir,staged_dir=args.staged_dir,
        routes_dir=args.routes_dir,run=args.run)
    original,code=b5.run(original_args)
    require(code==0 and original["genuine_independently_verified_sessions"]==4 and
            original["distinct_train_validation_frames"]==3 and
            original["required_ordinal_sequence"]==[0,1,2,0] and
            original["train0_repeat_physical_metrics_and_FNV64_equal"] is True and
            original["all_independent_fingerprint_gate_conditions_pass"] is True,
            "genuine four-run original V3 signed TRAIN scalar fingerprint repeat failed")
    verify_immutable_user_report(args.fourrun_report,original,"four-run")
    direct=raw.verify_session(
        evidence=args.raw_evidence,ordinal=0,
        frozen=args.frozen_dir,staged=args.staged_dir,
        routes=args.routes_dir,build=args.build_dir,
        reports=args.reports,offline_report=args.offline_report)
    require(direct["schema"]==
            "p07-b5-original-raw-physical-by-neuron-authenticated-scalar-gate-v1" and
            direct["raw_neuron_original_26x1010_bytes_exactly_equal"] is True and
            direct["same_session_original_27core_and_route_stage_verified"] is True and
            direct["actual_physical_trace_size"]==840320 and
            direct["physical_raw_trace_sha256"]==PINNED_RAW_SHA and
            direct["independent_original_raw_trace_sha256"]==PINNED_RAW_SHA and
            direct["physical_B5_mailbox_sha256"]==PINNED_MAILBOX_SHA and
            direct["physical_raw_FNV64"]==PINNED_RAW_FNV and
            direct["new_B5_ELF_sha256"]==PINNED_B5_ELF and
            direct["new_B5_map_sha256"]==PINNED_B5_MAP and
            direct["physical_B5_mailbox"]["physical_dispatches"]==702 and
            direct["physical_B5_mailbox"]["physical_barriers_acked"]==26 and
            direct["physical_B5_mailbox"]["B5_capture_neurons"]==26260 and
            len(direct["physical_per_tick_FNV64"])==26 and
            len(direct["independent_scalar_checks"])==7 and
            all(direct["independent_scalar_checks"].values()),
            "strict original B5 physical RAW neuron bytewise parity and signed source gate not met")
    verify_immutable_user_report(args.raw_report,direct,"raw-neuron")
    record={
        "schema":SCHEMA,
        "mode":args.mode,
        "signed_original_model_frozen":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "genuine_original_V3_27core_physical_sessions":4,
        "distinct_original_TRAIN_frames":3,
        "original_frame_ordinals":[0,1,2,0],
        "independent_original_multiframe_26tick_FNV64_and_all_counters_pass":True,
        "original_TRAIN0_repeat_physical_counters_and_FNV64_exactly_equal":True,
        "original_V3_evidence_dirs":[str(path.resolve()) for _,path in runs],
        "original_4run_report_sha256":hashlib.sha256(args.fourrun_report.read_bytes()).hexdigest(),
        "genuine_new_B5_raw_26tick_physical_sessions":1,
        "B5_RAW_original_TRAIN_ordinal":0,
        "B5_RAW_physical_evidence_dir":str(args.raw_evidence.resolve()),
        "B5_RAW_independent_report_sha256":hashlib.sha256(args.raw_report.read_bytes()).hexdigest(),
        "B5_RAW_physical_neuron_records":26260,
        "B5_RAW_physical_840320_bytes_exactly_equal_original_scalar":True,
        "B5_RAW_physical_trace_SHA256":PINNED_RAW_SHA,
        "B5_RAW_terminal_mailbox_SHA256":PINNED_MAILBOX_SHA,
        "B5_RAW_original_26_tick_FNV64":PINNED_RAW_FNV,
        "B5_RAW_7_independent_numerical_checks_pass":True,
        "B5_RAW_original_27core_staging_physically_verified":True,
        "original_P03_PL_and_accepted_original_V3_ELF_modified":False,
        "packet_level_every_word_numerical_parity_independently_proven":False,
        "boot_firmware_and_other_DDR_owner_independently_proven":False,
        "independent_board_powercycle_instrumentation_proof":False,
        "operator_attested_cold_boot_and_recovery_all_five_sessions":False,
        "operator_explicit_final_B5_acceptance":False,
        "all_required_B5_numerical_gates_pass":True,
        "P07_B5_final_acceptance":False,
        "P07_B6_started":False,
        "P08_B_started":False,
        "main_merged":False,
        "board_contact_this_PC_reviewer":False,
    }
    return record,runs

def validate_operator_attestation(path:Path,review:dict,runs:list[tuple[int,Path]])->dict:
    require(path.is_absolute() and path.is_file() and not path.is_symlink() and
            not path.resolve().is_relative_to(ROOT),
            "new externally stored operator-signed attestation JSON required")
    record=b5.read_json(path)
    require(record.get("schema")==ATTEST_SCHEMA,"wrong operator attestation schema")
    expected=[str(p.resolve()) for _,p in runs]+[review["B5_RAW_physical_evidence_dir"]]
    sessions=record.get("sessions")
    require(isinstance(sessions,list) and len(sessions)==5,
            "exactly 5 genuine distinct physical sessions must have separate attestations")
    for i,(entry,directory) in enumerate(zip(sessions,expected)):
        require(isinstance(entry,dict) and
                set(entry)=={
                    "evidence_dir","ordinal","fresh_cold_power_cycle_before",
                    "cold_power_cycle_after","dedicated_JTAG_ownership",
                    "no_resume_of_halted_Linux"
                } and
                entry["evidence_dir"]==directory and
                type(entry["ordinal"]) is int and
                entry["ordinal"]==([0,1,2,0,0][i]),
                "original four + B5 RAW0 evidence identity differs in physical reboot attestation "+str(i))
        for key in ("fresh_cold_power_cycle_before","cold_power_cycle_after",
                    "dedicated_JTAG_ownership","no_resume_of_halted_Linux"):
            require(entry[key] is True,
                    "operator has not attested physical "+key+" for session "+str(i))
    require(record.get("understands_original_boot_firmware_DDR_exclusivity_UNPROVEN") is True and
            record.get("understands_B5_raw_sidecar_mailbox_DDR_ownership_UNPROVEN") is True and
            record.get("accepts_documented_residual_destructive_DDR_risks") is True and
            record.get("operator_independently_rechecked_B5_2_and_B5_3_evidence") is True and
            record.get("explicitly_accepts_P07_B5_bounded_numerical_completion") is True and
            record.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
            "independent physical evidence review / residual DDR owner risks / final consent not all confirmed")
    return record

def closeout(args)->dict:
    result,runs=independent_review(args)
    if args.mode=="review":
        require(args.attestation is None and args.confirm_final_acceptance is None,
                "review is numerical only and must not take approval flags")
        return result
    require(args.mode=="accept",
            "B5.4 accepts only review or explicit accept")
    require(args.confirm_final_acceptance==FINAL_CONFIRM,
            "operator-specific exact final acceptance command not given")
    attestation=validate_operator_attestation(args.attestation,result,runs)
    result.update({
        "operator_attested_cold_boot_and_recovery_all_five_sessions":True,
        "operator_explicit_final_B5_acceptance":True,
        "operator_attestation_source_sha256":
            hashlib.sha256(args.attestation.read_bytes()).hexdigest(),
        "operator_attestation_path":str(args.attestation.resolve()),
        "P07_B5_final_acceptance":True,
        "P07_B6_started":False,
        "P08_B_started":False,
        "main_merged":False,
        "independent_board_powercycle_instrumentation_proof":False,
        "boot_firmware_and_other_DDR_owner_independently_proven":False,
        "note":"B5.4 accepted based on genuine five physical receipts and operator-reported cold power cycles; independent platform clock or DDR exclusive owner hardware attestation is not claimed.",
    })
    return result

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("review","accept"),default="review")
    for name in ("frozen-dir","staged-dir","routes-dir","build-dir",
                 "reports","offline-report","fourrun-report","raw-evidence",
                 "raw-report","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--run",action="append",required=True,
                        help="Four genuine ORIGINAL ordinal:directory paths, in 0/1/2/0 order")
    parser.add_argument("--attestation",type=Path)
    parser.add_argument("--confirm-final-acceptance")
    args=parser.parse_args()
    try:
        b5.require_external_report(args.out)
        receipt=closeout(args)
        b5.write_report(args.out,receipt)
        print("P07_B5_4_FIVE_PHYSICAL_SESSIONS_ORIGINAL_SIGNED_NUMERICAL_GATE_PASS=1")
        print("P07_B5_4_840320B_REAL_RAW_NEURON_PARITY_PASS=1")
        print("P07_B5_4_BOARD_CONTACT_THIS_AUDIT=0")
        print("P07_B5_4_OFFICIAL_MNIST_TEST_SEALED=1")
        print("P07_B5_4_FINAL_OPERATOR_ACCEPTANCE="+
              ("1" if receipt["P07_B5_final_acceptance"] else "0"))
        print("P07_B5_4_REPORT="+str(args.out))
        return 0
    except (OSError,ValueError,TypeError,KeyError,RuntimeError) as exc:
        print("P07_B5_4_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
