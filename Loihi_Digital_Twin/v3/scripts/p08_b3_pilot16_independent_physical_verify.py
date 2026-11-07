#!/usr/bin/env python3
"""Independent P08-B3 first16 same-session physical evidence verifier.

Must re-read genuine runner-produced XSDB/Vivado logs, original staged
physical PSU DDR readbacks of 2x original 27cores + 4 original artifacts,
exact operator-pinned pilot ELF/map, and complete terminal 16-frame
journal/timing/mailbox. No board contact. Rejects anything copied only
from scalar fixtures without expected same-session hardware transcript.

Physical journal's 26tick per-neuron FNV equality is a FINGERPRINT proof;
it does not replace 840320B direct raw trace capture or energy measurement.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import p08_b3_pilot16_physical_run as physical
import p08_b2_4_verify_untrusted_first16 as neural

SCHEMA="p08-b3-original-b24-first16-independent-physical-jtag-oracle-verification-v1"
STAGE_OK="P08_B3_FIRST16_JTAG_RESULTS_MATCH_SCALAR_PRECHECK_INDEPENDENT_PHYSICAL_ATTESTATION_PENDING_REBOOT_REQUIRED"
LOGS={
    "a53_takeover_and_ps128.log":(
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128"),
    "accepted_p03_program.log":(
        physical.b4j.PASS_MARKER,),
    "six_original_ddr_physical_stage.log":(
        "P08_B3_PILOT_mutable_27CORES_BYTE_EXACT_PASS=1",
        "P08_B3_PILOT_backup_27CORES_BYTE_EXACT_PASS=1",
        "P08_B3_PILOT_SIX_PHYSICAL_DDR_TRANSFERS_BYTE_EXACT_PASS=1"),
    "pilot16_a53_physical_run.log":(
        "P08_B3_PILOT_EXACT_OPERATOR_SHA_PINNED_ELF_DOWNLOADED=1",
        "P08_B3_PILOT_PHYSICAL_TERMINAL_MAILBOX_CAPTURED_256B=1",
        "P08_B3_PILOT_REAL_16_JOURNAL_AND_TIMING_SIDECARS_PHYSICAL_CAPTURED=1",
        "P08_B3_PILOT_EXACT_16_FRAME_HARDWARE_TERMINAL_OBSERVED=1",
        "P08_B3_PILOT_PHYSICAL_CAPTURE_PENDING_INDEPENDENT_SCALAR_VERIFICATION=1",
    ),
}

class EvidenceNoGo(ValueError):pass

def ensure(cond:bool,msg:str):
    if not cond:raise EvidenceNoGo("NO-GO: "+msg)

def verify(evidence:Path,stage:Path,oracle:Path,pilot_build:Path,
           reports:Path,reset_pins:Path,out:Path)->dict:
    ensure(out.is_absolute() and not out.exists() and not out.is_symlink() and
           out.parent.is_dir() and
           not out.resolve().is_relative_to(physical.b4i.ROOT.resolve()),
           "independent new outside-repo evidence report required")
    ensure(evidence.is_absolute() and evidence.is_dir() and not evidence.is_symlink(),
           "genuine external physical evidence directory required")
    a=argparse.Namespace(stage=stage,oracle=oracle,pilot_build=pilot_build,
                         reports=reports,reset_pins=reset_pins)
    prior=physical.offline_gate(a)
    meta=evidence/"preflight.json"
    m=json.loads(meta.read_text())
    for key,value in prior.items():
        if key in ("operator_hardware_approvals_received",):
            continue
        ensure(m.get(key)==value,"physical preflight source SHA changed: "+key)
    ensure(m.get("operator_hardware_approvals_received") is True and
           m.get("exclusive_boot_ddr_dma_owners_independently_proven") is False,
           "physical explicit risk consent evidence absent")
    ensure((evidence/"stage.txt").read_text().strip()==STAGE_OK,
           "same-session pilot evidence did not reach ready-for-independent-check stage")
    for filename,markers in LOGS.items():
        path=evidence/filename
        ensure(path.is_file() and not path.is_symlink(),"authentic log missing: "+filename)
        lines=path.read_text().splitlines()
        for marker in markers:
            ensure(lines.count(marker)==1,
                   "physical log missing or repeated acceptance marker: "+marker)
        ensure(not any("ATTEMPT_FAILED_REBOOT_REQUIRED=1" in row for row in lines),
               "physical session reported failure: "+filename)
    # Reuse original accepted strict A53 core halt + live 128-bit PS-width
    # parser. Original physical PL program marker count checked separately.
    physical.b4i.verify_takeover_log(
        (evidence/"a53_takeover_and_ps128.log").read_text())
    physical.b4j.require_programmed_shell(
        (evidence/"accepted_p03_program.log").read_text())
    physical.original_inputs(stage,oracle)
    observed=physical.readback_original(stage,evidence/"source_physical_readback")
    proof=json.loads((evidence/"same_session_six_source_receipt.json").read_text())
    ensure(proof.get("original_six_physical_source_sha256")==observed and
           proof.get("operator_pilot16_sha256")==physical.ELF_SHA and
           proof.get("operator_pilot16_map_sha256")==physical.MAP_SHA and
           proof.get("new_a53_elf_downloaded") is False and
           proof.get("same_session_jtag_source_readback") is True and
           proof.get("exclusive_boot_ddr_dma_owners_independently_proven") is False and
           proof.get("reboot_required") is True and
           proof.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
           "original 6 signed DDR readback receipt mismatches exact physical data")
    cap=evidence/"pilot16_physical_capture"
    expected={
        "mailbox_zero_physical.bin":256,
        "journal_zero_physical.bin":4096,
        "timing_zero_physical.bin":4096,
        "mailbox_terminal_physical.bin":256,
        "journal16_physical.bin":4096,
        "timing16_physical.bin":4096,
    }
    ensure(cap.is_dir() and not cap.is_symlink() and
           {p.name for p in cap.iterdir()}==set(expected),
           "pilot physical captures set incomplete or unexpected")
    for name,size in expected.items():
        p=cap/name
        ensure(p.is_file() and not p.is_symlink() and p.stat().st_size==size,
               "bad physical capture "+name)
        if name.endswith("_zero_physical.bin"):
            ensure(p.read_bytes()==bytes(size),
                   "physical pilot source output not independently zero initialized "+name)
    with __import__("tempfile").TemporaryDirectory(prefix="p08_b3_independent_") as tmp:
        unverified=neural.verify(
            oracle,cap/"journal16_physical.bin",cap/"timing16_physical.bin",
            cap/"mailbox_terminal_physical.bin",Path(tmp)/"temp.json")
    ensure(unverified["verified_frames"]==16 and
           unverified["all_16_independent_scalar_counters_match"] is True and
           unverified["all_16_full_26tick_trace_FNV_match"] is True,
           "physical original pilot16 numerical FNV or trained readout mismatch")
    result={
        "schema":SCHEMA,
        "original_first16_scalar_source_sha256":physical.gate.ORACLE_SHA,
        "genuine_original_B24_pilot16_ELF_SHA256":physical.ELF_SHA,
        "genuine_original_B24_pilot16_map_SHA256":physical.MAP_SHA,
        "original_model_and_separate_backup_27core_sha256":
            physical.source.EXPECTED_SHA[physical.source.FILES[0][0]],
        "same_session_original_6_DDR_physical_readbacks_byte_exact":True,
        "same_session_accepted_P03_shell_program_transcript":True,
        "same_session_A53_halt_and_FPD128_transcript":True,
        "actual_new_A53_16_frame_terminal_observed":True,
        "all_16_original_neural_classifier_and_10_output_spike_vectors_equal_scalar":True,
        "all_16_full_26tick_1010_neuron_FNV_fingerprint_equal_scalar":True,
        "all_16_A53_full_service_timers_structurally_valid":True,
        "physical_capture_untrusted_gate_sha256":hashlib.sha256(
            json.dumps(unverified,sort_keys=True).encode()).hexdigest(),
        "physical_journal_sha256":physical.sha(cap/"journal16_physical.bin"),
        "physical_timing_sha256":physical.sha(cap/"timing16_physical.bin"),
        "physical_terminal_mailbox_sha256":physical.sha(cap/"mailbox_terminal_physical.bin"),
        "physical_source_readback_sha256":observed,
        "independent_boot_firmware_DDR_ownership_proven":False,
        "direct_raw_full_neuron_26x1010_trace_readback_during_pilot":False,
        "physical_numeric_source_trace_FNV_parity":True,
        "physical_sample_count":16,
        "benchmark_latency_sessions_accepted":False,
        "operator_reboot_required":True,
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,indent=2,sort_keys=True);fp.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("evidence","stage","oracle","pilot-build","reports","reset-pins","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    try:
        result=verify(a.evidence,a.stage,a.oracle,a.pilot_build,
                      a.reports,a.reset_pins,a.out)
        print("P08_B3_PILOT16_SIGNED_ORIGINAL_27CORE_MUTABLE_BACKUP_PHYSICAL_PASS=1")
        print("P08_B3_PILOT16_REAL_16_FRAMES_ORIGINAL_SCALAR_NUMERICAL_FNV_PASS=1")
        print("P08_B3_PILOT16_FULL_SERVICE_TIMER_INTERNAL_CONSISTENCY_PASS=1")
        print("P08_B3_PILOT16_PHYSICAL_RAW_TRACE_DIRECT_CAPTURED=0")
        print("P08_B3_PILOT16_DDR_BOOT_DMA_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0")
        print("P08_B3_PILOT16_NEW_PHYSICAL_LATENCY_BENCHMARK_ACCEPTED=0")
        print("P08_B3_PILOT16_INDEPENDENT_REPORT="+str(a.out))
        return 0
    except (EvidenceNoGo,physical.PilotPhysicalNoGo,ValueError,TypeError,
            OSError,KeyError,AssertionError) as e:
        print("P08_B3_PILOT16_PHYSICAL_EVIDENCE_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
