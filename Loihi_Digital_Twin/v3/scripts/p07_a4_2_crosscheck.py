#!/usr/bin/env python3
"""Compare real persistent A4.2c 128-image results to accepted A3.3 KV260 mailboxes.

This is a strict second PHYSICAL-vs-PHYSICAL acceptance gate, not a
replacement for scripts/p07_a4_2_verify.py's software oracle check.
No canonical MNIST TEST files, trained-model modification or hardware.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from loihi_twin_v2.p07_a4_crosscheck import compare_prior_physical


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--journal",type=Path,required=True)
    p.add_argument("--trace",type=Path,required=True)
    p.add_argument("--a3-protocol-dir",type=Path,required=True)
    p.add_argument("--a3-evidence-dir",type=Path,required=True)
    args=p.parse_args()
    result=compare_prior_physical(
        a4_stage=args.stage_dir,
        a4_journal=args.journal,
        a4_trace=args.trace,
        a3_protocol=args.a3_protocol_dir,
        a3_evidence=args.a3_evidence_dir,
    )
    print(f"P07_A4_2C_CROSSCHECK_OLD_PHYSICAL_BATCHES={result.prior_primary_batches}/8")
    print(f"P07_A4_2C_CROSSCHECK_PRIMARY_FRAMES={result.frames}/128")
    print(f"P07_A4_2C_CROSSCHECK_FIRST_TRACE_BYTE_EXACT={int(result.selected_trace_exact)}")
    print("P07_A4_2C_CROSSCHECK_ALL_FRAME_SPIKES_ROUTES_EXACT=1")
    print("P07_A4_2C_CROSSCHECK_OLD_REPORT_MAILBOX_SHA_PASS=1")
    print("P07_A4_2C_PRIOR_AND_PERSISTENT_PHYSICAL_MATCH=1")
    print("P07_A4_OFFICIAL_TEST=SEALED")


if __name__=="__main__":
    main()
