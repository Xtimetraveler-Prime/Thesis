#!/usr/bin/env python3
"""A3.2.3 OFFLINE only: check three complete paired physical 1024-image reports.

Only consumes reports output by scripts/p08_a3_2_pair_check.py following
BOTH original physical packed-neuron oracle PASSes. Never accesses KV260.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from loihi_twin_v2.p08_a3_2_repeats import aggregate_three_pairs


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pair-reports", type=Path, nargs=3, required=True,
                   metavar="PAIRED_JSON",help="exactly three independent paired A3.2.1 reports, chronological")
    p.add_argument("--report",type=Path,required=True,help="new no-overwrite untracked JSON report")
    args=p.parse_args()
    if args.report.exists() or args.report.is_symlink():
        p.error("P08-A3.2.3 refuses to overwrite a report")
    report=aggregate_three_pairs(args.pair_reports)
    with args.report.open("x",encoding="utf-8") as file:
        json.dump(report,file,sort_keys=True,indent=2)
        file.write("\n")
    print("P08_A3_2_3_DISTINCT_PHYSICAL_SESSIONS=6")
    print("P08_A3_2_3_SAME_ORIGINAL_TRAIN_FIRST1024_PASS=1")
    print("P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1")
    print("P08_A3_2_3_ORDINARY_PAIR_MEDIAN_DELTAS_MS="+",".join(
        f"{x:.6f}" for x in report["paired_ordinary_median_delta_ms_by_pair"]))
    print("P08_A3_2_3_RESULT_SCOPE=DESCRIPTIVE_REPEATED_PILOT")
    print("P08_A3_2_3_POWER=DEFERRED")


if __name__=="__main__":
    main()
