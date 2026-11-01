#!/usr/bin/env python3
"""P07-B5.3 PC-ONLY exact new RAW A53/DDR risk review.

READ-ONLY. Not a hardware memory ownership proof; does NOT contact the KV260,
halt Linux, program PL, download ELF or authorize JTAG execution. It highlights
that the sidecar and B5 mailbox lie inside the wider original P03 DDR backing
APERTURE despite being disjoint from the narrower 27 original P02 records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import p07_b5_raw_trace_offline_admission as gate
import p07_b5_raw_physical_capture as runner
import p07_b5_scaled_validation as prior

ROOT=Path(__file__).resolve().parents[1]
BASE=0x40000000
APERTURE_END=0x44000000
RECORD_END=0x40D80000
OLD_MAILBOX=(0x43FF0000,0x43FF0100)
TRACE=(0x42000000,0x420CD280)
MAILBOX=(0x43FF0100,0x43FF0200)
LOW_DDR=(0,0x00107BC0)
V3_LOW_DDR=(0,0x00106B00)
PREVIOUS_ELF_SHA=runner.ELF_SHA
PREVIOUS_MAP_SHA=runner.MAP_SHA

class RiskReviewNoGo(ValueError):
    pass

def check_source_memory_contract()->dict:
    """Cross-check real repository constants without changing them."""
    physical=(ROOT/"software/p03/include/p03_hw_adapter.h").read_text()
    b5=(ROOT/"software/p07/include/p07_b5_raw_capture.h").read_text()
    entry=(ROOT/"software/p07/p07_b5_full_board_raw_trace_v1.c").read_text()
    checks={
        "accepted_P03_64MiB_backing_aperture":
            "#define P03_HW_BACKING_BYTES UINT64_C(0x04000000)" in physical and
            "#define P03_HW_BACKING_BASE UINT64_C(0x40000000)" in physical,
        "accepted_P03_512KiB_record":
            "#define P03_HW_RECORD_BYTES UINT64_C(0x00080000)" in physical,
        "B5_trace_start":
            "#define P07_B5_CAPTURE_DDR_CANDIDATE_BASE UINT32_C(0x42000000)" in b5,
        "B5_trace_full_840320B":
            "#define P07_B5_CAPTURE_BYTES (P07_B5_CAPTURE_TICKS*P07_B5_CAPTURE_NEURONS*32u)" in b5,
        "B5_mailbox_start":
            "#define B5_MAILBOX UINT32_C(0x43FF0100)" in entry,
        "B5_terminal_receipt_separate":
            "#define B5_MAILBOX_MAGIC UINT32_C(0x42355331)" in entry,
    }
    if not all(checks.values()):
        raise RiskReviewNoGo("NO-GO: P03/B5 address, record, mailbox or raw size contract drift")
    if (not (BASE<=TRACE[0]<TRACE[1]<=APERTURE_END and
             BASE<=MAILBOX[0]<MAILBOX[1]<=APERTURE_END) or
        TRACE[0]<RECORD_END or MAILBOX[0]<RECORD_END or
        TRACE[1]-TRACE[0]!=840320 or
        LOW_DDR[1]-V3_LOW_DDR[1]!=4288 or
        not(OLD_MAILBOX[1]==MAILBOX[0] and TRACE[1]<MAILBOX[0])):
        raise RiskReviewNoGo("NO-GO: B5 physical address envelope or V3 separation drift")
    return checks

def review(*,offline:Path,build:Path,reports:Path,frozen:Path,routes:Path)->dict:
    checks=check_source_memory_contract()
    current=gate.admit(frozen=frozen,routes=routes,build=build,reports=reports)
    if prior.read_json(offline)!=current:
        raise RiskReviewNoGo("NO-GO: approved exact real Vitis ELF/map offline report changed")
    elf=current["new_genuine_b5_ELF"]
    if (elf["new_elf_sha256"]!=PREVIOUS_ELF_SHA or
        elf["new_linker_map_sha256"]!=PREVIOUS_MAP_SHA or
        elf["pt_load_end_exclusive"]!="0x00107BC0" or
        elf["pt_load_memsz"]!=1080256):
        raise RiskReviewNoGo("NO-GO: genuine B5 ELF/map changed from PC admitted original")
    if (current["capture_geometry"]["trace_candidate_address_range_hex"]!=
        ["0x42000000","0x420cd280"] or
        current["capture_geometry"]["new_B5_mailbox_candidate_address_range_hex"]!=
        ["0x43ff0100","0x43ff0200"]):
        raise RiskReviewNoGo("NO-GO: actual B5 source/ELF candidate memory envelope changed")
    return {
        "schema":"p07-b5-3-host-only-physical-ddr-owner-risk-review-v1",
        "genuine_operator_admitted_elf_sha256":elf["new_elf_sha256"],
        "genuine_operator_admitted_map_sha256":elf["new_linker_map_sha256"],
        "original_accepted_B4M_V3_ELF_untouched":True,
        "original_P03_source_memory_contract_checks":checks,
        "P03_64MiB_backing_aperture":[hex(BASE),hex(APERTURE_END)],
        "original_27x512KiB_context_records":[hex(BASE),hex(RECORD_END)],
        "proposed_B5_trace":[hex(x) for x in TRACE],
        "proposed_B5_mailbox":[hex(x) for x in MAILBOX],
        "original_V3_mailbox":[hex(x) for x in OLD_MAILBOX],
        "proposed_B5_load":[hex(x) for x in LOW_DDR],
        "original_V3_load":[hex(x) for x in V3_LOW_DDR],
        "B5_low_DDR_increment_bytes_over_original_V3":4288,
        "trace_and_new_mailbox_are_WITHIN_broad_P03_64MiB_aperture":True,
        "trace_and_mailbox_disjoint_from_original_27_context_records":True,
        "trace_disjoint_from_narrow_signed_routes_and_ingress":True,
        "trace_sidecar_exclusively_owned_by_new_A53":False,
        "mailbox_exclusively_owned_by_new_A53":False,
        "DDR_unallocated_by_Linux_or_other_agents_independently_proven":False,
        "low_DDR_free_of_boot_firmware_independently_proven":False,
        "other_APU_RPU_or_DMA_masters_quiescent_proven":False,
        "risk_accepted_by_operator_in_this_host_only_review":False,
        "hardware_owner_proof_by_static_memory_range_math":False,
        "destructive_board_execution_authorized":False,
        "actual_KV260_accessed":False,
        "original_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "followup":"Treat 0x42000000 and 0x43FF0100 as new destructive allocations, NOT automatically safe just because they avoid the 27 P02 records. Separately review boot firmware/Linux/other core/device owners, then secure explicit operator approval or choose a demonstrably reserved physical allocation. Never infer hardware owner proof from this PC report."
    }

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ("frozen-dir","routes-dir","build-dir","reports","offline-report","out"):
        parser.add_argument("--"+flag,type=Path,required=True)
    args=parser.parse_args()
    try:
        prior.require_external_report(args.out)
        result=review(offline=args.offline_report,build=args.build_dir,
                      reports=args.reports,frozen=args.frozen_dir,
                      routes=args.routes_dir)
        with args.out.open("x") as dest:
            json.dump(result,dest,sort_keys=True,indent=2)
            dest.write("\n")
        print("P07_B5_RAW_REAL_VITIS_ELF_MAP_AND_SOURCE_MEMORY_CONTRACT_PASS=1")
        print("P07_B5_RAW_CAPTURE_INSIDE_P03_BROAD_DDR_APERTURE=1")
        print("P07_B5_RAW_INDEPENDENT_DDR_AND_BOOT_OWNER_PROOF=0")
        print("P07_B5_RAW_BOARD_EXECUTION_AUTHORIZED=0")
        print("P07_B5_RAW_BOARD_CONTACT=0")
        print("P07_B5_RAW_DDR_RISK_REVIEW="+str(args.out))
        return 0
    except (ValueError,OSError,TypeError,KeyError) as e:
        print("P07_B5_RAW_DDR_RISK_REVIEW_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
