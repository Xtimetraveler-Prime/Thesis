#!/usr/bin/env python3
"""Offline physical 1024 TRAIN-derived persistent-primary / cold-reboot gate.

Requires independently accepted full P03 software oracle logs for each
original A53 physical run; verifies immutable six raw XSDB staging
readbacks and every physical P07A4R01 frame record; checks full 1MiB
journal/64KiB last-image trace byte equality on separate launches.
Canonical official t10k MNIST TEST is never accessed or scored.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2.p07_a4_val1024_gate import verify_1024


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage-dir",type=Path,required=True)
    p.add_argument("--primary-dir",type=Path,required=True)
    p.add_argument("--repeat-dir",type=Path)
    p.add_argument("--report",type=Path,
                   help="write accepted JSON only to a NEW filename")
    args=p.parse_args()
    if args.report is not None and args.report.exists():
        p.error("refuse overwrite of original 1024 physical evidence report")
    summary=verify_1024(stage=args.stage_dir,primary=args.primary_dir,
                        repeat=args.repeat_dir)
    if args.report is not None:
        with args.report.open("x",encoding="utf-8") as f:
            json.dump(summary,f,sort_keys=True,indent=2)
            f.write("\n")
        print("P07_A4_2C_1024_REPORT="+str(args.report.resolve()))
    print("P07_A4_2C_1024_UNIQUE_TRAIN_VALIDATION=1024")
    print("P07_A4_2C_1024_SELECTED_FINAL_TRACE_INDEX=1023")
    print("P07_A4_2C_1024_PRIMARY_ORACLE_LOGS_EXACT=1")
    print("P07_A4_2C_1024_PRIMARY_DDR_PROVENANCE_EXACT=1")
    print("P07_A4_2C_1024_PRIMARY_PHYSICAL_GATE_PASS=1")
    if args.repeat_dir is None:
        print("P07_A4_2C_1024_COLD_REPEAT=NOT_RUN")
    else:
        print("P07_A4_2C_1024_REPEAT_ORACLE_LOGS_EXACT=1")
        print("P07_A4_2C_1024_REPEAT_DDR_PROVENANCE_EXACT=1")
        print("P07_A4_2C_1024_PHYSICAL_LAUNCHES=2/2")
        print("P07_A4_2C_1024_HARDWARE_IMAGE_EXECUTIONS=2048")
        print("P07_A4_2C_1024_JOURNAL_1M_BYTE_EXACT=1")
        print("P07_A4_2C_1024_TRACE_64K_BYTE_EXACT=1")
        print("P07_A4_2C_1024_RESTART_GATE_PASS=1")
    print("P07_A4_OFFICIAL_TEST=SEALED")


if __name__=="__main__":
    main()
