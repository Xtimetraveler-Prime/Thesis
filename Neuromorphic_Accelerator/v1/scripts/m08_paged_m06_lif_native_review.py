#!/usr/bin/env python3
"""READ-ONLY first-original owner M08.4 native K26 candidate inventory.

ALWAYS returns 2 even when Vivado routed and bitgen succeeded. New K26
DRC warning instances, pin/equations, routed slack, clocks, physical fan
and image/source SHA need a separate original owner image-specific review.
This is NOT equivalent to the accepted older M32Q bit acceptance.
Absolutely no board actions, and never modify owner original receipts.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
NAMES=(
    "00_vivado.log","01_vivado.jou","02_vivado_exit.txt",
    "reports/10_fan_a12.xdc","reports/11_fabric_por.v",
    "reports/12_paged_lif_shell.v","reports/13_paged_lif_engine.v",
    "reports/14_paged_axil_control.sv","reports/15_paged_host_page_bank.sv",
    "reports/20_route_drc.rpt","reports/21_route_timing.rpt",
    "reports/22_route_utilization.rpt","reports/23_route_clocks.rpt",
    "reports/30_native_result.txt",
    "bitstream_candidate/m08_paged_m06_lif_jtag_UNRELEASED.bit",
)
SOURCE_MAP={
    "reports/11_fabric_por.v":"rtl/m08_d3c_fabric_por.v",
    "reports/12_paged_lif_shell.v":"rtl/m08/m08_paged_m06_lif_shell.v",
    "reports/13_paged_lif_engine.v":"rtl/m08/m08_paged_m06_lif_engine.v",
    "reports/14_paged_axil_control.sv":"rtl/m08/m08_axil_page_control.sv",
    "reports/15_paged_host_page_bank.sv":"rtl/m08/m08_host_staged_page_bank.sv",
}
BIT=NAMES[-1]
class Reject(ValueError): pass

def require(value:bool,reason:str):
    if not value: raise Reject(reason)

def digest(p:Path):
    return sha256(p.read_bytes()).hexdigest()

def inspect(run:Path):
    require(run.exists() and run.is_dir() and not run.is_symlink() and
            run.parent==(Path.home()/"Thesis_Evidence/M08") and
            run.name.startswith("m08_paged_m06_lif_"),
            "must supply unmodified original owner M08 native image path")
    receipt=run/"99_evidence_sha256.txt"
    require(receipt.is_file() and not receipt.is_symlink(),"original SHA ledger missing")
    rows=receipt.read_text(encoding="ascii").splitlines()
    require(len(rows)==len(NAMES),"original SHA entry count not expected 15")
    parsed=[]
    for line in rows:
        require(len(line)>66 and line[64:66]=="  ","malformed original SHA row")
        hash_str,rel=line[:64],line[66:]
        require(len(hash_str)==64 and all(ch in "0123456789abcdef" for ch in hash_str),
                "SHA256 row malformed")
        require(rel in NAMES and rel not in parsed,"foreign or duplicate original evidence")
        target=run/rel
        require(target.is_file() and not target.is_symlink() and
                target.stat().st_size>0 and digest(target)==hash_str,
                "owner original file changed or missing: "+rel)
        parsed.append(rel)
    require(set(parsed)==set(NAMES),"original SHA ledger missing a required file")
    for dest,src in SOURCE_MAP.items():
        require(digest(run/dest)==digest(ROOT/src),
                "native-built source drift from current repository: "+src)
    bit=run/BIT
    require(bit.stat().st_size>100000,"K26 bit lacks plausible size")
    meta=(run/"reports/30_native_result.txt").read_text(encoding="utf-8")
    require("neural_mode=SIGNED16_32_NEURON_4_TICK_5_EDGE_PAGED_LIF" in meta and
            "physical_m06_ddr=NO" in meta and
            "physical_jtag_test_authorized=NO" in meta and
            "hardware_bitstream_programmed=NO" in meta,
            "owner metadata does not explicitly prevent physical claims")
    return {
       "status":"M08_4_NEW_PAGED_M06_NATIVE_FIRST_IMAGE_NOT_RELEASED_NO_BOARD",
       "original_15_sha_entries_verified":True,
       "candidate_bitstream_sha256":digest(bit),
       "candidate_size_bytes":bit.stat().st_size,
       "source_sha_current_exact":True,
       "vivado_drc_image_warning_review":"REQUIRED_NOT_WAIVED",
       "vivado_routed_timing_image_specific_review":"REQUIRED",
       "image_specific_gate":"BLOCKED",
       "physical_programming_authorized":False,
       "physical_KV260_execution":False,
       "physical_ddr":False,
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir",type=Path,required=True)
    args=ap.parse_args()
    try:
        print(json.dumps(inspect(args.run_dir),indent=2,sort_keys=True))
    except (Reject,ValueError,OSError,UnicodeError) as exc:
        print("M08_4_PAGED_NATIVE_FIRST_IMAGE_SOURCE_OR_SHA_REJECTED: "+str(exc),
              file=sys.stderr)
    print("M08_4_NEW_IMAGE_DRC_TIMING_SOURCE_SHA_REVIEW_REQUIRED_NO_BOARD",
          file=sys.stderr)
    return 2

if __name__=="__main__":
    raise SystemExit(main())
