#!/usr/bin/env python3
"""FINAL independent canonical original-order full10000 KV260 oracle+score.

Never use until officially unsealed and original physical descriptor
fault accepted. No sampling, retraining or result substitutions. The
complete 10000 physical journal, actual JTAG readbacks, input
source+labels, and complete 26x10x10000 oracle are ALL checked BEFORE
any score is calculated, printed, or written.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p07_a4_protocol import load_canonical_official_test
from loihi_twin_v2.p07_a4_official_verify import verify_full10000


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--evidence-dir",type=Path,required=True)
    p.add_argument("--test-data-dir",type=Path,required=True)
    p.add_argument("--candidate-dir",type=Path,default=Path(
        "artifacts/p06_a3_candidate_seed20261013"))
    p.add_argument("--fault-stage-dir",type=Path,required=True)
    p.add_argument("--fault-evidence-dir",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--i-accept-unseal",action="store_true")
    p.add_argument("--i-accept-one-trace-policy",action="store_true")
    args=p.parse_args()
    if not args.i_accept_unseal or not args.i_accept_one_trace_policy:
        p.error("official canonical TEST access denied without explicit unseal and trace-policy consent")
    if args.report.exists():
        p.error("refuse overwrite of original official TEST physical report")
    official=load_canonical_official_test(args.test_data_dir)
    report=verify_full10000(
        stage=args.stage_dir,evidence=args.evidence_dir,official=official,
        candidate_dir=args.candidate_dir,
        fault_stage=args.fault_stage_dir,fault_evidence=args.fault_evidence_dir,
    )
    # Exclusive output creation. No reporting at all if some image failed.
    with args.report.open("x",encoding="utf-8") as output:
        json.dump(report,output,sort_keys=True,indent=2)
        output.write("\n")
    print("P07_A4_4_CANONICAL_FULL_ORIGINAL_ORDER=10000/10000")
    print("P07_A4_4_PHYSICAL_INDEPENDENT_OUTPUT_SPIKES_ROUTES_EXACT=10000/10000")
    print("P07_A4_4_FINAL_IMAGE9999_FULL_COMPARTMENT_TRACE_EXACT=1")
    print("P07_A4_4_ALL_SIX_ORIGINAL_DDR_READBACKS_EXACT=1")
    print("P07_A4_4_PREVIOUS_PHYSICAL_FAULT_ACCEPTANCE_PASS=1")
    print("P07_A4_4_COMPLETE_PHYSICAL_DENOMINATOR=10000")
    print(f"P07_A4_4_OFFICIAL_TEST_CORRECT={report['correct']}/10000")
    print(f"P07_A4_4_OFFICIAL_TEST_ACCURACY_PERCENT={report['accuracy_percent']:.4f}")
    print(f"P07_A4_4_OFFICIAL_TEST_ALL_SILENT={report['all_silent']}/10000")
    print("P07_A4_4_FULL10000_KV260_INDEPENDENT_CLOSEOUT_PASS=1")
    print("P07_A4_4_SCORE_REPORT="+str(args.report.resolve()))


if __name__=="__main__":
    main()
