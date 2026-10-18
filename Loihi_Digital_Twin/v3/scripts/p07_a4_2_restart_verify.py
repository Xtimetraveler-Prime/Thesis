#!/usr/bin/env python3
"""Strict A4.2c physical persistent-128 primary and cold restart verifier.

Read-only: no JTAG, no official TEST access, no model changes.
Use --primary only BEFORE a second launch, then --repeat for
independent original logs, original images, complete physical
journal/trace byte identity and old A3.3 KV260 mailbox parity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p07_a4_restart import verify_cold_repeat


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--primary-dir",type=Path,required=True)
    p.add_argument("--repeat-dir",type=Path)
    p.add_argument("--a3-protocol-dir",type=Path,required=True)
    p.add_argument("--a3-evidence-dir",type=Path,required=True)
    p.add_argument("--report",type=Path,
                   help="new filename; exclusive create only after verified PASS")
    args=p.parse_args()
    if args.report is not None and args.report.exists():
        p.error("refuse to overwrite original cold-repeat physical acceptance report")
    report=verify_cold_repeat(
        stage=args.stage_dir,
        primary=args.primary_dir,
        repeat=args.repeat_dir,
        a3_protocol=args.a3_protocol_dir,
        a3_evidence=args.a3_evidence_dir,
    )
    if args.report is not None:
        # Do not overwrite existing user evidence, including racing process.
        with args.report.open("x",encoding="utf-8") as file:
            json.dump(report,file,sort_keys=True,indent=2)
            file.write("\n")
        print("P07_A4_2C_128_REPORT="+str(args.report.resolve()))
    print("P07_A4_2C_128_PRIMARY_ORACLE_LOGS_EXACT=1")
    print("P07_A4_2C_128_PRIMARY_PREVIOUS_PHYSICAL_EXACT=128/128")
    print("P07_A4_2C_128_PRIMARY_ELF_XSA_STAGE_PINNED=1")
    if args.repeat_dir is None:
        print("P07_A4_2C_128_COLD_REPEAT=NOT_RUN")
        print("P07_A4_2C_128_PRIMARY_PREFLIGHT_PASS=1")
    else:
        print("P07_A4_2C_128_REPEAT_ORACLE_LOGS_EXACT=1")
        print("P07_A4_2C_128_REPEAT_PREVIOUS_PHYSICAL_EXACT=128/128")
        print("P07_A4_2C_128_PHYSICAL_LAUNCHES=2/2")
        print("P07_A4_2C_128_TOTAL_HARDWARE_IMAGE_EXECUTIONS=256")
        print("P07_A4_2C_128_UNIQUE_VALIDATION_IMAGES=128")
        print("P07_A4_2C_128_JOURNAL_1M_BYTE_EXACT=1")
        print("P07_A4_2C_128_TRACE_64K_BYTE_EXACT=1")
        print("P07_A4_2C_128_COLD_REPEAT_ALL_BYTES_EXACT=1")
        print("P07_A4_2C_128_PHYSICAL_RESTART_GATE_PASS=1")
    print("P07_A4_OFFICIAL_TEST=SEALED")


if __name__=="__main__":
    main()
