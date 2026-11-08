#!/usr/bin/env python3
"""P08-B4.4 dedicated original1024 reset PROFILE physical JTAG experiment.

DEFAULT mode preflight, strictly PC-only. Real JTAG requires NINE
independent operator YES approvals, including separately approved new
0x42400000 DDR overwrite; original accepted B2.3 full1024 ELF is NEVER
downloaded as experimental profile. Original original B4.2 27core
source/1024 scalar, P03 XSA/bitstream, signed B3 AND signed B4.2
independent real physical evidence are reauthenticated offline.
No original physical evidence is modified or substituted; every new
physical run requires independent verification before admission.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import p08_b4_2_physical_run as base
import p08_b44_profile_elf_admission as new_elf
import p08_b44_reset_profile_sidecar as subphase
import p08_b4_2_verify_full1024 as numerical
import p08_b2_4_verify_untrusted_first16 as timerecord

ROOT=Path(__file__).resolve().parents[1]
PROFILE_ELF_SHA="bed1301c69594bf7ebeaa37765ad2cb3035aa0f6d5e9cb4d1fb4637042be3ab3"
PROFILE_MAP_SHA="d94fa2695e82cc3a501442313bb77e89eb046f01450167108832a190fd9fd2c9"
PROFILE_ELF_AUDIT_SHA="7a5818dc5469ea288fefcefb87ebc4fd3ab1e5c7bdce0bbfda717a6f2787b129"
ORIGINAL_B4_PHYSICAL_REPORT_SHA="297114489eb8312733a2e2597f0ee0567f9868552d2bc71d0dd425139368b032"
ORIGINAL_B44_TIMING_SHA="4e0abf43dafab145b2dde6846d5504470c3d122da80923c34441e82877881b81"
RUN_TCL="vivado/p08_b44_profile_full1024_run_and_capture.tcl"
RUN_TOKEN="P08_B44_PROFILE_AFTER_ORIGINAL_SIX_SIGNED_READBACK_NEW_REGION_RISK_APPROVED"
APPROVALS=base.APPROVALS+("extra_profile_ddr_region_overwrite_approved",)
SCHEMA="p08-b44-original1024-profile-readonly-new-elf-source-admission-v1"
STAGE_OK="P08_B44_PROFILE1024_REAL_A53_TERMINAL_NEURAL_AND_RESET_PROFILE_STRUCTURAL_PRECHECK_PASS_INDEPENDENT_JTAG_VERIFICATION_PENDING_REBOOT_REQUIRED"
class NewProfileNoGo(ValueError):pass

def check(ok:bool,msg:str)->None:
    if not ok:raise NewProfileNoGo("NO-GO: "+msg)

def admission(args:argparse.Namespace)->dict:
    old=base.admission(args)
    check(args.profile_elf.is_absolute() and
          args.profile_elf.name=="p08_b44_reset_profile_1024.elf" and
          args.profile_map.is_absolute() and
          args.profile_map.name=="p08_b44_reset_profile_1024.map",
          "only separately staged genuine P08-B44 NEW profile ELF/map canonical names")
    check(base.sha(args.profile_elf)==PROFILE_ELF_SHA and
          base.sha(args.profile_map)==PROFILE_MAP_SHA,
          "operator's genuinely built NEW B4.4 profile ELF/map SHA drift")
    check(base.sha(args.profile_elf_audit)==PROFILE_ELF_AUDIT_SHA,
          "separate operator NEW offline profile ELF source admission report drift")
    independent=json.loads(args.profile_elf_audit.read_text())
    check(independent.get("schema")==new_elf.SCHEMA and
          independent.get("new_profile_ELF_sha256")==PROFILE_ELF_SHA and
          independent.get("new_profile_linker_map_sha256")==PROFILE_MAP_SHA and
          independent.get("original_immutable_B2_3_full1024_ELF_sha256")==base.ELF_SHA and
          independent.get("destructive_JTAG_launch_authorized") is False and
          independent.get("new_image_actual_KV260_neural_FNV_parity_verified") is False and
          independent.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "original genuine NEW offline Vitis artifact preflight not correctly signed")
    with TemporaryDirectory(prefix="p08_b44_profile_elf_again_") as temp:
        rerun=new_elf.audit(
            args.profile_elf,args.profile_map,args.elf,
            args.reports/"p03_2_ps_mmio.xsa",
            args.reset_pins/"p08_b2_2_original_context_sha256.h",
            Path(temp)/"profile_elf.json")
        check(independent==rerun,"genuine new original A53 ELF auditor disagrees with operator source")
    check(base.sha(args.b4_independent_report)==ORIGINAL_B4_PHYSICAL_REPORT_SHA,
          "accepted original full1024 physical numerical/clock report SHA drift")
    phys=json.loads(args.b4_independent_report.read_text())
    check(phys.get("schema")==
          "p08-b4-2-original1024-independent-physical-jtag-numerical-v1" and
          phys.get("single_session_full1024_numerical_parity_accepted") is True and
          phys.get("real_1024_A53_terminal_PASS_observed") is True and
          phys.get("all_1024_full_26tick_1010_neuron_FNV_fingerprints_equal_scalar") is True and
          phys.get("original_full1024_scalar_sha256")==base.ORIGINAL_FULL1024_ORACLE_SHA and
          phys.get("full_multisession_TrackB_latency_benchmark_accepted") is False and
          phys.get("boot_DDR_DMA_exclusive_owner_proven") is False and
          phys.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "first genuine full1024 independent original physical report fields invalid")
    check(base.sha(args.b44_timing_report)==ORIGINAL_B44_TIMING_SHA,
          "operator original 1023 ordinary descriptive timing SHA drift")
    timed=json.loads(args.b44_timing_report.read_text())
    check(timed.get("schema")==
          "p08-b4-4-original-full1024-single-physical-session-timing-descriptive-v1" and
          timed.get("independent_physical_full1024_report_sha256")==
          ORIGINAL_B4_PHYSICAL_REPORT_SHA and
          timed.get("ordinary_frame_count")==1023 and
          timed.get("recorded_actual_A53_CNTFRQ_EL0_hz")==99999001 and
          timed.get("one_independently_verified_real_physical_session") is True and
          timed.get("six_repeated_AB_BA_AB_physical_sessions_accepted") is False and
          timed.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "accepted single-session B4.4 measured A53 source drift")
    check(args.profile_elf.read_bytes().find(new_elf.PROFILE_ID)>=0 and
          new_elf.PROFILE_DONE in args.profile_elf.read_bytes() and
          base.elfcheck.IDENTITY not in args.profile_elf.read_bytes(),
          "new profile ELF identity or terminal missing/old identity present")
    return {
        **old,"schema":SCHEMA,
        "original_independent_full1024_physical_report_sha256":ORIGINAL_B4_PHYSICAL_REPORT_SHA,
        "original_1023_descriptive_timing_report_sha256":ORIGINAL_B44_TIMING_SHA,
        "separate_new_profile_ELF_sha256":PROFILE_ELF_SHA,
        "separate_new_profile_MAP_sha256":PROFILE_MAP_SHA,
        "separate_new_profile_elf_source_admission_sha256":PROFILE_ELF_AUDIT_SHA,
        "experimental_profile_DDR_base":"0x42400000",
        "experimental_profile_DDR_length":262144,
        "experimental_profile_owner_exclusive_proven":False,
        "original_neural_scalar_all1024_already_signed":True,
        "new_profile_actual_KV260_1024_physical_run":False,
        "new_profile_physical_neural_parity_accepted":False,
        "new_profile_destructive_JTAG_authorized_by_preflight":False,
    }

def structural_profile_check(
        oracle:Path,first16:Path,capture:Path,precheck:Path)->dict:
    check(precheck.is_absolute() and precheck.parent.is_dir()
          and not precheck.exists() and not precheck.is_symlink(),
          "new untrusted original neural AND reset-profile combined receipt path required")
    # Do NOT publish successful neural evidence until ALL 1024
    # experimental reset-profile microphase rows ALSO validate.
    with TemporaryDirectory(prefix="p08_b44_neural_pending_profile_") as td:
        observed=numerical.verify(
            oracle,first16,capture/"journal1024_physical.bin",
            capture/"timing1024_physical.bin",capture/"mailbox_terminal_physical.bin",
            Path(td)/"neural_untrusted.json")
    hz=observed["terminal"]["CNTFRQ_EL0_hz"]
    raw=(capture/"reset_profile1024_physical.bin").read_bytes()
    perf=subphase.audit(raw,hz)
    raw_timers=(capture/"timing1024_physical.bin").read_bytes()
    prev=None
    for i in range(1024):
        timer=timerecord.verify_timing(
            raw_timers[i*256:(i+1)*256],i,prev)
        prev=timer["after_journal_commit_CNTVCT"]
        split=subphase.decode_row(raw[i*256:(i+1)*256],i,hz)
        # Instrumented reset spans are measured inside full A53 phase0;
        # additional counter reads and controls MUST be positive residual.
        check(split["total_reset_ticks"]<=timer["phase_counter_ticks"][0],
              f"profile frame {i}: five reset microphases exceed measured full original A53 restore interval")
    combined={
        "all_original_1024_neural_spike_vectors_and_trace_fnv_match_scalar":True,
        "all_original_1024_A53_timing_records_crc_monotonic":True,
        "new_original_27core_reset_profile_1024_records_structural_pass":True,
        "new_profile_trace_ordinal_1023_excluded_from_ordinary":True,
        "observed_A53_frequency_hz":hz,
        "original_neural_journal_sha256":observed["journal_sha256"],
        "original_timing_sidecar_sha256":observed["timing_sha256"],
        "terminal_mailbox_sha256":observed["terminal_sha256"],
        "new_reset_profile_sha256":perf["profile_binary_sha256"],
        "new_reset_profile_descriptive":perf,
        "independent_same_session_JTAG_provenance_verified":False,
        "actual_profile_physical_KV260_numerical_accepted":False,
        "six_paired_A_vs_B_latency_sessions_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with precheck.open("x",encoding="utf-8") as stream:
        json.dump(combined,stream,indent=2,sort_keys=True)
        stream.write("\n")
    return combined

def execute(args:argparse.Namespace,approved:dict)->None:
    for name in APPROVALS:
        check(getattr(args,name)=="YES",
              "separate explicitly approved --"+name.replace("_","-")+" YES required")
    check(args.evidence is not None and args.evidence.is_absolute()
          and not args.evidence.exists() and not args.evidence.is_symlink()
          and args.evidence.parent.is_dir()
          and not args.evidence.resolve().is_relative_to(base.b4i.ROOT.resolve()),
          "fresh outside-repo evidence directory required")
    check(all(shutil.which(t) for t in ("xsdb","vivado")),
          "source rejected: local genuine XSDB/Vivado unavailable")
    root=args.evidence
    root.mkdir(mode=0o700)
    (root/"preflight.json").write_text(json.dumps({
        **approved,"all_nine_separate_operator_execute_approvals":True,
        "physical_JTAG_session_started":False},sort_keys=True,indent=2)+"\n")
    cap=root/"profile1024_capture"
    cap.mkdir()
    reads=root/"source_physical_readback"
    reads.mkdir()
    try:
        (root/"stage.txt").write_text(
            "P08_B44_PROFILE_NEW_REGION_DESTRUCTIVE_JTAG_ATTEMPT_STARTED_REBOOT_REQUIRED\n")
        base.b4i.log_call([
            "xsdb",base.b4j.TAKEOVER_TCL,"DEDICATED_DISCARD_LINUX_APPROVED",
            "tcp:127.0.0.1:3121",
        ],root/"a53_takeover_and_ps128.log")
        base.b4i.verify_takeover_log((root/"a53_takeover_and_ps128.log").read_text())
        base.b4i.log_call([
            "vivado","-mode","batch","-source",base.b4j.PROGRAM_TCL,
            "-tclargs",str(args.reports/"p03_2_ps_mmio.bit"),
            str(args.reports/"p03_2_ps_mmio.ltx"),"localhost:3121",
        ],root/"accepted_p03_program.log")
        base.b4j.require_programmed_shell((root/"accepted_p03_program.log").read_text())
        sources=[args.stage/name for name,_,_ in base.source.FILES]
        base.b4i.log_call([
            "xsdb",base.STAGE_TCL,base.STAGE_TOKEN,*map(str,sources),
            str(reads),"tcp:127.0.0.1:3121",
        ],root/"six_original_ddr_physical_stage.log")
        base.marker(root/"six_original_ddr_physical_stage.log",
                    "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1")
        signed=base.prior.readback_original(args.stage,reads)
        (root/"same_session_six_source_receipt.json").write_text(
            json.dumps({
                "original_six_physical_source_sha256":signed,
                "new_distinct_profile_A53_ELF_sha256":PROFILE_ELF_SHA,
                "original_full1024_scalar_sha256":base.ORIGINAL_FULL1024_ORACLE_SHA,
                "same_session_JTAG_physical_DDR_readbacks":True,
                "profile_A53_ELF_downloaded_at_receipt_time":False,
                "experimental_new_DDR_region_owner_exclusive_proven":False,
                "operator_reboot_required":True,
                "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
            },sort_keys=True,indent=2)+"\n")
        zeros256=root/"zero256.bin"
        zeros262144=root/"zero262144.bin"
        zeros256.write_bytes(bytes(256))
        zeros262144.write_bytes(bytes(262144))
        base.b4i.log_call([
            "xsdb",RUN_TCL,RUN_TOKEN,str(args.profile_elf),
            str(zeros256),str(zeros262144),str(cap),
            "tcp:127.0.0.1:3121"
        ],root/"profile1024_a53_physical_run.log")
        for s in (
            "P08_B44_PROFILE1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
            "P08_B44_PROFILE1024_EXPERIMENTAL_DDR_0x42400000_ZERO_READBACK_PASS=1",
            "P08_B44_PROFILE1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
            "P08_B44_PROFILE1024_REAL_1024_RESET_PROFILE_SIDECAR_PHYSICAL_CAPTURED=1",
            "P08_B44_PROFILE1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        ):
            base.marker(root/"profile1024_a53_physical_run.log",s)
        result=structural_profile_check(
            args.oracle,args.first16,cap,root/"untrusted_profile1024_neural_and_subphase.json")
        check(result["new_original_27core_reset_profile_1024_records_structural_pass"] is True,
              "not all 1024 original reset profiles structural PASS")
        (root/"stage.txt").write_text(STAGE_OK+"\n")
        print("P08_B44_PROFILE1024_ORIGINAL_1024_NEURAL_FNV_SCALAR_PRECHECK_PASS=1")
        print("P08_B44_PROFILE1024_1024_RESET_SHA_MEMCPY_CACHE_STRUCTURAL_PRECHECK_PASS=1")
        print("P08_B44_PROFILE1024_INDEPENDENT_PHYSICAL_PROVENANCE_PENDING=1")
    finally:
        print("P08_B44_PROFILE1024_ANY_DESTRUCTIVE_JTAG_ATTEMPT_REBOOT_REQUIRED=1",flush=True)
        print("REBOOT or power-cycle KV260; NEVER resume halted Linux.",flush=True)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("preflight","execute"),default="preflight")
    for key in (
        "stage","shards","ingress","oracle","first16","b3_report",
        "elf","linker_map","reset_pins","reports",
        "b4_independent_report","b44_timing_report",
        "profile_elf","profile_map","profile_elf_audit",
    ):
        p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    p.add_argument("--evidence",type=Path)
    for name in APPROVALS:
        p.add_argument("--"+name.replace("_","-"),choices=("YES","NO"),default="NO")
    args=p.parse_args()
    try:
        approved=admission(args)
        print("P08_B44_PROFILE1024_ORIGINAL_64_SHARD_SCALAR_AND_SEPARATE_REAL_ELF_PREFLIGHT_PASS=1")
        print("P08_B44_PROFILE1024_PINNED_ELF_SHA="+PROFILE_ELF_SHA)
        print("P08_B44_PROFILE1024_PINNED_MAP_SHA="+PROFILE_MAP_SHA)
        print("P08_B44_PROFILE1024_BOOT_FW_DMA_AND_NEW_DDR_OWNER_EXCLUSIVITY_PROVEN=0")
        if args.mode=="preflight":
            print("P08_B44_PROFILE1024_READONLY_BOARD_VISITED=0")
            print("P08_B44_PROFILE1024_DESTRUCTIVE_JTAG_NOT_AUTHORIZED_BY_PREFLIGHT=1")
            return 0
        execute(args,approved)
        return 0
    except (NewProfileNoGo,base.FullPhysicalNoGo,base.prior.PilotPhysicalNoGo,
            base.elfcheck.ElfNoGo,base.full_ref.MergeNoGo,
            numerical.FullRecordNoGo,subphase.ProfileNoGo,
            new_elf.ProfileElfNoGo,ValueError,TypeError,KeyError,OSError,
            RuntimeError,subprocess.TimeoutExpired) as e:
        print("P08_B44_PROFILE1024_SOURCE_OR_PHYSICAL_NO_GO="+str(e),
              file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
