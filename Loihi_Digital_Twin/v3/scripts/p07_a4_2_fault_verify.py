#!/usr/bin/env python3
"""Verify ACTUAL KV260 intentional PRE-DISPATCH A4 descriptor rejection.

Expected status = 0xDEAD0001, zero inference dispatch and all-zero result
body and trace. This is a NEGATIVE TEST, NEVER an inference PASS.
Read-only analysis of original independently preserved XSDB output.
Canonical MNIST TEST is SEALED; only synthetic ramp16 admitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p07_a4_fault import verify_physical_fault


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--evidence-dir",type=Path,required=True)
    p.add_argument("--report",type=Path,
                   help="optional NEW JSON path, never overwrite")
    args=p.parse_args()
    if args.report is not None and args.report.exists():
        p.error("refuse overwrite of any existing fault-test physical report")
    proof=verify_physical_fault(stage=args.stage_dir,evidence=args.evidence_dir)
    if args.report is not None:
        with args.report.open("x",encoding="utf-8") as f:
            json.dump(proof,f,sort_keys=True,indent=2)
            f.write("\n")
        print("P07_A4_2C_FAULT_REPORT="+str(args.report.resolve()))
    print("P07_A4_2C_EXPECTED_FAULT_STATUS=0xDEAD0001")
    print("P07_A4_2C_PHYSICAL_DESCRIPTOR_MUTATION_ONE_WORD_EXACT=1")
    print("P07_A4_2C_PHYSICAL_ORIGINAL_PROVISION_EXACT=1")
    print("P07_A4_2C_PHYSICAL_INFERENCE_FRAMES_COMPLETED=0")
    print("P07_A4_2C_PHYSICAL_RESULT_BODY_ALL_ZERO=1")
    print("P07_A4_2C_PHYSICAL_TRACE_ALL_ZERO=1")
    print("P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1")
    print("P07_A4_OFFICIAL_TEST=SEALED")


if __name__=="__main__":
    main()
