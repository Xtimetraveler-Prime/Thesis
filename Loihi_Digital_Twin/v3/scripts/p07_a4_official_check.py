#!/usr/bin/env python3
"""Read-only verify already authorized canonical 10000-stage vs official IDX.

NEVER download. Must explicitly attest unseal and trace policy;
requires independently accepted original synthetic physical fault
evidence on every call. No scoring, inference or hardware access.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from loihi_twin_v2.p07_a4_fault import verify_physical_fault
from loihi_twin_v2.p07_a4_protocol import load_canonical_official_test
from loihi_twin_v2.p07_a4_official import check_official_stage


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",required=True,type=Path)
    p.add_argument("--test-data-dir",type=Path,required=True)
    p.add_argument("--fault-stage-dir",type=Path,required=True)
    p.add_argument("--fault-evidence-dir",type=Path,required=True)
    p.add_argument("--i-accept-unseal",action="store_true")
    p.add_argument("--i-accept-one-trace-policy",action="store_true")
    args=p.parse_args()
    if not args.i_accept_unseal or not args.i_accept_one_trace_policy:
        p.error("refuse official TEST access without explicit unseal + one-trace-policy approval")
    report=verify_physical_fault(stage=args.fault_stage_dir,
                                 evidence=args.fault_evidence_dir)
    if report["status_word"]!="0xDEAD0001":
        raise ValueError("official TEST provenance refused: physical fault gate incomplete")
    official=load_canonical_official_test(args.test_data_dir)
    stream,meta,ledger=check_official_stage(args.stage_dir,official)
    print("P07_A4_3_PHYSICAL_FAULT_GATE_PASS=1")
    print("P07_A4_3_ORIGINAL_CANONICAL_TEST_ARCHIVES_PASS=1")
    print(f"P07_A4_3_COMPLETE_STAGED_ORIGINAL_IDX_ORDER={stream.image_count}/10000")
    print("P07_A4_3_SELECTED_FULL_TRACE_INDEX=9999")
    print("P07_A4_3_LABELS_HOST_ONLY=1")
    print("P07_A4_3_PHYSICAL_STATUS=NOT_YET_VERIFIED")
    print("P07_A4_3_OFFICIAL_STAGE_CHECK_PASS=1")


if __name__=="__main__":
    main()
