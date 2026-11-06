#!/usr/bin/env python3
"""P08-B4.6.2 PC-only A vs B_AUTH_ONCE pre-registration source gate.

Real study arm A = original P08-A A2.1 42-neuron original ELF.
Arm B_AUTH_ONCE = P08-B4.5 V2 1010-neuron 27-core 702-dispatch
UNPROTECTED performance-only one-time authenticated ELF (not original
SHA-every-image B4.4). Both on same frozen first1024 TRAIN-derived
input IMAGE identities; no claim of equal model/compute/integrity.

This checks the original canonical TRAIN split and A original stage
through the existing P08-B1 source audit (strict TRAIN archives, 33
original B frozen files), then compares every original A image index
and 784-byte SHA with the accepted independent B 1024 scalar oracle.
Four independent operator files must have exact accepted SHA pins.
NO board/XSDB/JTAG/Vivado actions. It does not authorize any run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import p08_b1_matched_source_audit as b1
# ORIGINAL A2.1 authentic A53 ELF pin from accepted P08-A3.2 source audit.
# Do not import the full A3.2 verifier here: it imports torch at module
# scope, which is unnecessary for this lightweight CI offline gate.
import p08_b4_2_physical_run as original_b
import p08_b45_perf_full1024_elf_admission as b45elf
import p08_b46_a21_rebuild_admission as rebuilt

SCHEMA="p08-b46-original-A-vs-unprotected-B-auth-once-offline-source-gate-v1"
REBUILT_SCHEMA="p08-b46-reconstructed-A21-vs-B-auth-once-offline-source-gate-v1"
A_ELF_SHA="fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0"
B_ELF_SHA="a19b50dffb21d897caa1eb19ea62fadd5dec0a1adc27d99354b2d9b6adab0e85"
B_ONCE_INDEPENDENT_SHA="06a007b73cb3ff31c02910224e28690215bded5bdb401973e6a0347e44d0d65a"
B45_SYNTHESIS_SHA="b04aa0ada133a61ce052ce40f7aa7dbf667da6958031cfdc63b99cc57354eff0"
B_ORACLE_SHA=original_b.ORIGINAL_FULL1024_ORACLE_SHA
A_ARM="A_ORIGINAL_A2_1_42_NEURONS_26_DISPATCHES"
B_ARM="B_AUTH_ONCE_UNPROTECTED_V2_1010_NEURONS_702_DISPATCHES"
ARM_ORDER=(A_ARM,B_ARM,B_ARM,A_ARM,A_ARM,B_ARM)
class GateNoGo(ValueError):
    pass

def check(ok,why):
    if not ok:raise GateNoGo("NO-GO: "+why)

def sha(path:Path)->str:
    check(path.is_absolute() and path.is_file() and not path.is_symlink(),
          "source is not a regular absolute path: "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda:stream.read(1<<20),b""):
            h.update(data)
    return h.hexdigest()

def check_signed_json(path:Path,expected:str,schema:str)->dict:
    check(sha(path)==expected,"accepted signed source SHA drift: "+str(path))
    body=json.loads(path.read_text())
    check(isinstance(body,dict) and body.get("schema")==schema,
          "signed evidence schema drift: "+str(path))
    return body

def audit(a_elf:Path,b_elf:Path,a_stage:Path,train:Path,frozen:Path,
          b_oracle:Path,b_once_report:Path,synthesis:Path,out:Path,
          a_rebuilt_admission:Path|None=None,
          a_rebuilt_xsa:Path|None=None)->dict:
    check(out.is_absolute() and out.parent.is_dir() and
          not out.exists() and not out.is_symlink() and
          not out.resolve().is_relative_to(Path(__file__).resolve().parents[1]),
          "new external absolute no-overwrite manifest required")
    # Default historical path remains EXACTLY fail-closed. A separate
    # explicit candidate option independently re-audits the new build;
    # it NEVER makes the reconstructed SHA masquerade as original A2.1.
    a_candidate=None
    a_provenance="ORIGINAL_HISTORICAL_SHA_PINNED_A21"
    a_actual_sha=A_ELF_SHA
    study_A_arm=A_ARM
    if a_rebuilt_admission is None:
        check(a_rebuilt_xsa is None,
              "rebuilt XSA without distinct candidate admission refused")
        check(sha(a_elf)==A_ELF_SHA and
              a_elf.name=="p08_a2_board.elf",
              "original accepted A2.1 ELF SHA/identity changed")
    else:
        check(a_rebuilt_xsa is not None,
              "rebuilt A2.1 requires original accepted P03 XSA to re-audit")
        check(sha(a_elf)==rebuilt.NEW_A21_SHA and
              a_elf.name=="p08_a2_board.elf",
              "distinct newly rebuilt candidate ELF SHA changed")
        check(a_rebuilt_admission.is_absolute() and
              a_rebuilt_admission.is_file() and
              not a_rebuilt_admission.is_symlink(),
              "rebuilt host-only source admission missing")
        # Re-inspect original actual Vitis build/source/ELF/XSA from disk,
        # rather than trusting self-reported JSON Boolean flags.
        reread=rebuilt.inspect_rebuild(a_elf.parent.parent,a_rebuilt_xsa)
        a_candidate=json.loads(a_rebuilt_admission.read_text())
        check(a_candidate==reread and
              a_candidate.get("new_A2_1_candidate_KV260_1024_neural_oracle_acceptance") is False and
              a_candidate.get("historical_original_A2_1_ELF_recovered") is False,
              "rebuilt source manifest differs from independent read-only audit")
        a_provenance="REBUILT_A21_NEW_SHA_PC_VALIDATED_PHYSICAL_PENDING"
        a_actual_sha=rebuilt.NEW_A21_SHA
        study_A_arm="A_REBUILT_A21_CANDIDATE_42_NEURONS_26_DISPATCHES"
    check(sha(b_elf)==B_ELF_SHA and
          b_elf.name=="p08_b45_perf_once_full1024.elf",
          "real accepted V2 authenticate-once ELF SHA changed")
    elf=b_elf.read_bytes()
    check(b45elf.IDENTITIES["once"] in elf and
          b45elf.IDENTITIES["unchecked"] not in elf and
          b45elf.TERMINAL["once"] in elf,
          "B_AUTH_ONCE distinct original full1024 V2 A53 identity invalid")
    check(sha(b_oracle)==B_ORACLE_SHA,
          "original B4.1 full1024 independently accepted scalar oracle changed")
    bframes=json.loads(b_oracle.read_text())
    check(bframes.get("count")==1024 and
          bframes.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
          isinstance(bframes.get("frames"),list) and len(bframes["frames"])==1024,
          "original frozen B 1024 scalar frame population and TEST seal invalid")
    accepted=check_signed_json(b_once_report,B_ONCE_INDEPENDENT_SHA,
           "p08-b45-unprotected-full1024-independent-real-jtag-v1")
    check(accepted.get("experiment")=="once" and
          accepted.get("genuine_new_mode_specific_A53_ELF_sha256")==B_ELF_SHA and
          accepted.get("original_complete1024_scalar_SHA256")==B_ORACLE_SHA and
          accepted.get("new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar") is True and
          accepted.get("new_all_27_post_run_backup_records_identical_to_original") is True and
          accepted.get("hardware_DDR_backup_protection_proven") is False and
          accepted.get("original_OFFICIAL_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "signed V2 once original 1024 scalar/FNV/backup/limited-integrity source invalid")
    compare=check_signed_json(synthesis,B45_SYNTHESIS_SHA,
                  "p08-b45-physical-cross-session-quantitative-synthesis-v1")
    check(compare.get("both_modes_neural_parity_and_original_backup_endpoints_pass") is True and
          compare.get("hardware_or_JTAG_access_performed") is False and
          compare.get("paired_randomized_repeated_session_speedup_proven") is False and
          compare.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
          compare.get("source_sha256",{}).get("once")==B_ONCE_INDEPENDENT_SHA and
          compare.get("source_sha256",{}).get("original_full1024_scalar_oracle")==B_ORACLE_SHA,
          "B4.5.5 signed quantitative closeout not accepted or rewritten")

    # This is the canonical original A/B same-population proof, NOT just
    # comparing two convenient user-written JSON manifests. It reopens
    # strict IDX TRAIN archives and original A stage, and all 33 B freeze
    # assets. Neither official MNIST TEST nor external network is opened.
    matched=b1.generate_report(a_stage,train,frozen)
    check(matched.get("schema")==
             "p08-b1-canonical-matched-a-stage-b24-train-audit-v1" and
          matched.get("original_track_A_frame_count")==1024 and
          matched.get("original_frame_order_preserved") is True and
          matched.get("B24_original_33_assets_verified") is True and
          matched.get("B24_compiled_model_sha256")==b1.B24_COMPILED_SHA and
          matched.get("original_MNIST_TEST")=="SEALED_NOT_ACCESSED" and
          len(matched.get("frames",[]))==1024,
          "canonical original Track A/B frozen TRAIN source did not pass")
    for i,(ar,br) in enumerate(zip(matched["frames"],bframes["frames"])):
        check(ar.get("frame")==i and br.get("ordinal")==i and
              ar.get("TRAIN_source_index")==br.get("TRAIN_source_index") and
              ar.get("raw_pixels_sha256")==br.get("raw_pixels_sha256") and
              ar.get("in_B_training_partition") is False and
              ar.get("selected_trace")== (i==1023),
              "original A/B frozen TRAIN pixel/order/source mismatch at image "+str(i))

    schedule=[
      {"sequence_number":i+1,"pair":i//2+1,
       "position_in_pair":"first" if i%2==0 else "second",
       "arm":(study_A_arm if arm==A_ARM else arm),
       "fresh_coldboot_required":True,
       "individual_physical_JTAG_permission_granted":False,
       "new_signed_physical_capture_accepted":False}
       for i,arm in enumerate(ARM_ORDER)]
    result={
      "schema":REBUILT_SCHEMA if a_candidate is not None else SCHEMA,
      "study":"A original 42-neuron SOURCE (rebuilt ELF if selected) vs B_AUTH_ONCE V2 unprotected system/workload",
      "arm_A":study_A_arm,
      "arm_B":B_ARM,
      "A_neurons":42,"A_FPGA_dispatches_per_image":26,
      "B_neurons":1010,"B_virtualized_cores":27,
      "B_FPGA_dispatches_per_image":702,
      "B_original_full_SHA_every_image":False,
      "B_once_at_bind_original_source_SHA":True,
      "B_header_check_per_image":True,
      "B_hardware_immutable_backup_write_protection_proven":False,
      "identical_original_TRAIN_1024_source_index_and_raw_pixel_SHA":True,
      "same_network_complexity":False,
      "original_A_image_timing_elf_sha256":A_ELF_SHA,
      "selected_A_real_elf_sha256":a_actual_sha,
      "selected_A_elf_provenance":a_provenance,
      "new_A_rebuilt_candidate_source_manifest_sha256":sha(a_rebuilt_admission) if a_candidate is not None else None,
      "new_A_rebuilt_candidate_KV260_neural_parity_and_timing_reaccepted":False if a_candidate is not None else None,
      "old_historical_A2_1_ELF_recovered":False if a_candidate is not None else True,
      "optimized_B_once_full1024_elf_sha256":B_ELF_SHA,
      "B_original_scalar_oracle_sha256":B_ORACLE_SHA,
      "accepted_B_once_1024_independent_sha256":B_ONCE_INDEPENDENT_SHA,
      "accepted_B45_physical_synthesis_sha256":B45_SYNTHESIS_SHA,
      "canonical_A_stage_source":matched["track_A_stage"],
      "B_frozen_model_compiled_sha256":b1.B24_COMPILED_SHA,
      "first1024_source_indices_SHA256":b1.PREFIX_INDICES_SHA,
      "frame_count_each":1024,"ordinary_frames_each":1023,
      "excluded_trace_ordinal":1023,
      "pre_registered_order":"AB/BA/AB (A,B,B,A,A,B)",
      "session_independent_unit":"one independent coldboot per run (not 1023 trials)",
      "planned_six_independently_rebooted_sessions":schedule,
      "per_run_independent_original_neural_oracle_required":True,
      "per_run_actual_A53_CNTFRQ_and_matched_full_service_scope_required":True,
      "A_and_B_have_demonstrably_IDENTICAL_service_boundaries":False,
      "physical_runner_for_B_AUTH_ONCE_reuse_validated_for_six_replicates":False,
      "physical_runner_for_Track_A_reuse_validated_for_six_replicates":False,
      "ABBAAB_repeated_physical_evidence_accepted":False,
      "hardware_memory_owner_and_DMA_exclusivity_proven":False,
      "six_new_physical_JTAG_runs_authorized":False,
      "independent_paired_session_effect_or_significance_established":False,
      "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
      "PC_only_no_board_contact":True,
    }
    with out.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,sort_keys=True)
        stream.write("\n")
    return result

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("a_elf","b_once_elf","a_stage","train_data_dir",
                 "frozen_b","b_oracle","b_once_report",
                 "b45_synthesis","out"):
        p.add_argument("--"+name.replace("_","-"),required=True,type=Path)
    p.add_argument("--a-rebuilt-admission",type=Path,default=None,
                   help="distinct newly rebuilt A2.1 PC report (NOT historical ELF)")
    p.add_argument("--a-rebuilt-xsa",type=Path,default=None,
                   help="genuine original P03 XSA for separate rebuilt A2.1 reinspection")
    args=p.parse_args(argv)
    try:
        ans=audit(args.a_elf,args.b_once_elf,args.a_stage,
                  args.train_data_dir,args.frozen_b,args.b_oracle,
                  args.b_once_report,args.b45_synthesis,args.out,
                  args.a_rebuilt_admission,args.a_rebuilt_xsa)
    except (GateNoGo,rebuilt.CandidateNoGo,b1.P08B1Error,ValueError,TypeError,
            OSError,KeyError,AssertionError) as err:
        print("P08_B46_AUTH_ONCE_SOURCE_NO_GO="+str(err),
              file=sys.stderr,flush=True)
        return 3
    print("P08_B46_ORIGINAL_A_VS_AUTH_ONCE_FROZEN_1024_TRAIN_POPULATION_PASS=1")
    print("P08_B46_TRACK_A_A21_HISTORICAL_SHA="+A_ELF_SHA)
    print("P08_B46_TRACK_A_ACTUAL_SELECTED_SHA="+ans["selected_A_real_elf_sha256"])
    print("P08_B46_TRACK_A_REBUILT_CANDIDATE_PHYSICAL_REACCEPTED=0" if args.a_rebuilt_admission is not None else "P08_B46_ORIGINAL_A2_1_PINNED_SHA_ACCEPTED=1")
    print("P08_B46_TRACK_B_AUTH_ONCE_V2_EXACT_SHA="+B_ELF_SHA)
    print("P08_B46_B45_VERIFIED_ONE_SESSION_SOURCE_SHA="+B_ONCE_INDEPENDENT_SHA)
    print("P08_B46_NEW_SIX_SESSION_STUDY_JTAG_AUTHORIZED=0")
    print("P08_B46_SOURCE_GATE_PC_ONLY_PASS=1")
    print("P08_B46_SOURCE_GATE_REPORT="+str(args.out))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
