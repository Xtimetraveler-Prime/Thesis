#!/usr/bin/env python3
"""P08-B4.4: independent PC-only genuine 1024 profiling JTAG attestation.

Rechecks NEW pinned genuine B44 profiling A53 ELF/map and accepted B4.2
original model source, full independent original 64-shard scalar oracle,
signed B3 and prior B4 physical proof, SAME SESSION P03/PSU A53 halt
and six physical source DDR readbacks, four genuine zeroed/captured
DDR output regions incl experimental reset profile at 0x42400000,
all 1024 original neural/FNV/out spike vectors, all original six
A53 timing phases and all 1024 5-component+residual reset microprofiles.

Strict source / untrusted 1024 format evidence does not alone prove
same-session physical JTAG. No PL-only speedup, no energy or final
six paired A-vs-B performance claim. Does NOT contact hardware.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import p08_b44_profile_physical_run as experimental
import p08_b4_2_independent_physical_verify as original_provenance
import p08_b4_2_physical_run as old

SCHEMA="p08-b44-original1024-independent-physical-reset-profile-jtag-v1"
LOGS={
    "a53_takeover_and_ps128.log":(
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
    ),
    "accepted_p03_program.log":(old.b4j.PASS_MARKER,),
    "six_original_ddr_physical_stage.log":(
        "P08_B3_PILOT_mutable_27CORES_BYTE_EXACT_PASS=1",
        "P08_B3_PILOT_backup_27CORES_BYTE_EXACT_PASS=1",
        "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1",
    ),
    "profile1024_a53_physical_run.log":(
        "P08_B44_PROFILE1024_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
        "P08_B44_PROFILE1024_EXPERIMENTAL_DDR_0x42400000_ZERO_READBACK_PASS=1",
        "P08_B44_PROFILE1024_PHYSICAL_TERMINAL_MAILBOX_CAPTURED_256B=1",
        "P08_B44_PROFILE1024_REAL_1024_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
        "P08_B44_PROFILE1024_REAL_1024_RESET_PROFILE_SIDECAR_PHYSICAL_CAPTURED=1",
        "P08_B44_PROFILE1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B44_PROFILE1024_PHYSICAL_CAPTURE_PENDING_INDEPENDENT_SCALAR_VERIFICATION=1",
    ),
}
class ProfileAttestationNoGo(ValueError):pass

def check(ok:bool,reason:str)->None:
    if not ok:raise ProfileAttestationNoGo("NO-GO: "+reason)

def sha_file(path:Path)->str:
    check(path.is_file() and not path.is_symlink(),
          "original physical evidence missing/symlink: "+str(path))
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1048576),b""):
            h.update(chunk)
    return h.hexdigest()

def verify(a:argparse.Namespace)->dict:
    report=a.out
    evidence=a.evidence
    check(report.is_absolute() and report.parent.is_dir()
          and not report.exists() and not report.is_symlink()
          and not report.resolve().is_relative_to(old.b4i.ROOT.resolve()),
          "new separate external no-overwrite independent profiling report required")
    check(evidence.is_absolute() and evidence.is_dir()
          and not evidence.is_symlink(),
          "actual new profile dedicated JTAG evidence directory required")
    auth=experimental.admission(a)
    original=json.loads((evidence/"preflight.json").read_text())
    for key,val in auth.items():
        check(original.get(key)==val,
              "same-session original signed frozen/profile source preflight differs: "+key)
    check(original.get("all_nine_separate_operator_execute_approvals") is True
          and original.get("physical_JTAG_session_started") is False
          and original.get("experimental_profile_owner_exclusive_proven") is False,
          "profiled hardware run has no genuine nine operator approvals")
    check((evidence/"stage.txt").read_text().strip()==experimental.STAGE_OK,
          "exact B4.4 physical terminal and both 1024 source/profile prechecks missing")
    for filename,required in LOGS.items():
        f=evidence/filename
        check(f.is_file() and not f.is_symlink(),
              "same-session authenticated XSDB/Vivado log missing: "+filename)
        lines=f.read_text().splitlines()
        for marker in required:
            check(lines.count(marker)==1,
                  "hardware evidence required marker missing/duplicate: "+marker)
        check(not any("ATTEMPT_FAILED_REBOOT_REQUIRED=1" in line
                      for line in lines),
              "actual profiling physical run reported failure: "+filename)
    old.b4i.verify_takeover_log(
        (evidence/"a53_takeover_and_ps128.log").read_text())
    old.b4j.require_programmed_shell(
        (evidence/"accepted_p03_program.log").read_text())
    old.prior.original_inputs(a.stage,a.first16)
    signed=old.prior.readback_original(
        a.stage,evidence/"source_physical_readback")
    receipt=json.loads(
        (evidence/"same_session_six_source_receipt.json").read_text())
    check(receipt.get("original_six_physical_source_sha256")==signed
          and receipt.get("new_distinct_profile_A53_ELF_sha256")==
          experimental.PROFILE_ELF_SHA
          and receipt.get("original_full1024_scalar_sha256")==
          old.ORIGINAL_FULL1024_ORACLE_SHA
          and receipt.get("same_session_JTAG_physical_DDR_readbacks") is True
          and receipt.get("profile_A53_ELF_downloaded_at_receipt_time") is False
          and receipt.get("experimental_new_DDR_region_owner_exclusive_proven") is False
          and receipt.get("operator_reboot_required") is True
          and receipt.get("original_OFFICIAL_MNIST_TEST")=="SEALED_NOT_ACCESSED",
          "same-session physical six source readback receipt missing or changed")
    cap=evidence/"profile1024_capture"
    sizes={
        "mailbox_zero_physical.bin":256,
        "journal_zero_physical.bin":262144,
        "timing_zero_physical.bin":262144,
        "reset_profile_zero_physical.bin":262144,
        "mailbox_terminal_physical.bin":256,
        "journal1024_physical.bin":262144,
        "timing1024_physical.bin":262144,
        "reset_profile1024_physical.bin":262144,
    }
    check(cap.is_dir() and not cap.is_symlink()
          and {f.name for f in cap.iterdir()}==set(sizes),
          "actual new profile physical 4 DDR zero+capture set invalid")
    for name,size in sizes.items():
        file=cap/name
        check(file.is_file() and not file.is_symlink()
              and file.stat().st_size==size,
              "physical captured profiler DDR file truncated/missing: "+name)
        if "_zero_physical.bin" in name:
            check(file.read_bytes()==bytes(size),
                  "actual same-session physical PSU zero initial readback not byte exact: "+name)
    with TemporaryDirectory(prefix="p08_b44_profile_independent_") as tmp:
        v=experimental.structural_profile_check(
            a.oracle,a.first16,cap,Path(tmp)/"independent_untrusted.json")
    check(v.get("all_original_1024_neural_spike_vectors_and_trace_fnv_match_scalar") is True
          and v.get("all_original_1024_A53_timing_records_crc_monotonic") is True
          and v.get("new_original_27core_reset_profile_1024_records_structural_pass") is True
          and v.get("independent_same_session_JTAG_provenance_verified") is False,
          "full original 1024 independent numerical/FNV and profile structure not PASS")
    result={
        "schema":SCHEMA,
        "first_original_1024_B4_2_independent_report_sha256":
            experimental.ORIGINAL_B4_PHYSICAL_REPORT_SHA,
        "accepted_original_1023_B4_4_timing_report_sha256":
            experimental.ORIGINAL_B44_TIMING_SHA,
        "original_1024_scalar_oracle_sha256":
            old.ORIGINAL_FULL1024_ORACLE_SHA,
        "same_session_accepted_original_P03_128bit_shell_proven":True,
        "same_session_all_original_27_mutable_and_27_immutable_core_DDR_sources_verified":True,
        "same_session_all_original_six_DDR_transfers_physical_sha256":signed,
        "distinct_experimental_A53_profile_ELF_sha256":experimental.PROFILE_ELF_SHA,
        "distinct_experimental_A53_profile_map_sha256":experimental.PROFILE_MAP_SHA,
        "new_experimental_profile_region_0x42400000_zero_readback_verified":True,
        "original_1024_real_A53_terminal_exact_1024_observed":True,
        "all_1024_original_neural_predictions_readouts_and_26tick_1010neuron_FNV_equal_scalar":True,
        "all_1024_original_A53_six_phase_counter_records_crc_and_monotone":True,
        "all_1024_new_27core_reset_profiles_sha_copy_cache_crc_and_clock_valid":True,
        "raw1024_neural_journal_sha256":v["original_neural_journal_sha256"],
        "raw1024_a53_timing_sidecar_sha256":v["original_timing_sidecar_sha256"],
        "raw1024_reset_profile_sidecar_sha256":v["new_reset_profile_sha256"],
        "raw_terminal_mailbox_sha256":v["terminal_mailbox_sha256"],
        "actual_A53_counter_frequency_hz":v["observed_A53_frequency_hz"],
        "one_genuine_1024_physical_profile_session_numerical_equivalence_accepted":True,
        "new_1023_ordinary_reset_profile_descriptive":v["new_reset_profile_descriptive"],
        "new_five_phase_timer_instrumentation_changes_execution_cost":True,
        "actual_PL_only_neural_engine_time_measured":False,
        "boot_firmware_DDR_DMA_owner_exclusivity_proven":False,
        "six_new_paired_AB_BA_AB_A_vs_B_sessions_accepted":False,
        "energy_or_hardware_speedup_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with report.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2,sort_keys=True)
        stream.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for key in (
        "evidence","stage","shards","ingress","oracle","first16","b3_report",
        "elf","linker_map","reset_pins","reports","b4_independent_report",
        "b44_timing_report","profile_elf","profile_map","profile_elf_audit","out",
    ):
        p.add_argument("--"+key.replace("_","-"),type=Path,required=True)
    a=p.parse_args()
    try:
        z=verify(a)
        print("P08_B44_NEW_RESET_PROFILE1024_INDEPENDENT_SAME_SESSION_JTAG_PROVENANCE_PASS=1")
        print("P08_B44_NEW_RESET_PROFILE1024_ORIGINAL_1024_NEURAL_FNV_SPIKE_PARITY_PASS=1")
        print("P08_B44_NEW_RESET_PROFILE1024_ALL_1024_REAL_SHA_COPY_CACHE_SUBSPAN_COUNTERS_PASS=1")
        print("P08_B44_NEW_RESET_PROFILE1024_NEW_PAIRED_AB_BA_AB_BENCHMARK_ACCEPTED=0")
        print("P08_B44_NEW_RESET_PROFILE1024_INDEPENDENT_PHYSICAL_REPORT="+str(a.out))
        return 0
    except (ProfileAttestationNoGo,experimental.NewProfileNoGo,
            old.FullPhysicalNoGo,old.prior.PilotPhysicalNoGo,
            old.elfcheck.ElfNoGo,old.full_ref.MergeNoGo,
            experimental.new_elf.ProfileElfNoGo,
            experimental.numerical.FullRecordNoGo,
            experimental.subphase.ProfileNoGo,
            ValueError,TypeError,KeyError,OSError,AssertionError) as exc:
        print("P08_B44_INDEPENDENT_NEW_PROFILE1024_PHYSICAL_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
