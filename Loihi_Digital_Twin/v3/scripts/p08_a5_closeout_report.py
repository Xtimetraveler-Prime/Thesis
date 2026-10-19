#!/usr/bin/env python3
"""Offline P08-A5 CPU-vs-KV260 acceptance-CANDIDATE Markdown; never merges."""
from __future__ import annotations
import argparse
from pathlib import Path

from loihi_twin_v2.p08_a5_closeout import (
    read_json,sha256,make_draft,
)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cpu-report",type=Path,required=True)
    p.add_argument("--physical-three-pair-report",type=Path,required=True)
    p.add_argument("--output-md",type=Path,required=True)
    a=p.parse_args()
    if not a.output_md.is_absolute() or a.output_md.exists() or a.output_md.is_symlink():
        p.error("A5 final report must be a new absolute no-overwrite filename")
    root=Path(__file__).resolve().parents[3]
    if root in a.output_md.resolve().parents:
        p.error("A5 physical/CPU measurement output must remain outside git")
    doc=make_draft(
        read_json(a.cpu_report),
        read_json(a.physical_three_pair_report),
        cpu_sha=sha256(a.cpu_report),
        physical_sha=sha256(a.physical_three_pair_report),
    )
    with a.output_md.open("x",encoding="utf8") as file:
        file.write(doc)
    print("P08_A5_CPU_AND_PHYSICAL_SAME_TRAIN_STAGE_SHA256_PASS=1")
    print("P08_A5_TWO_CPU_ENDPOINTS_SEPARATE=1")
    print("P08_A5_FINAL_REPORT_CANDIDATE_BUILT=1")
    print("P08_A5_FPGA_SPEEDUP=NOT_CLAIMED_NON_EQUIVALENT_ENDPOINTS")
    print("P08_A5_FINAL_USER_ACCEPTANCE=PENDING")
    print("P08_A4_POWER=DEFERRED")


if __name__=="__main__":
    main()
