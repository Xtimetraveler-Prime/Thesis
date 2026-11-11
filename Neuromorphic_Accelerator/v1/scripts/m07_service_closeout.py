#!/usr/bin/env python3
"""M07.5 source-only assumed-cycle queue/transfer closure; NO FPGA."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m07_service_model import (
    ServiceAssumptions, ServiceSweepPlan, run_service_sweep)


def parse_nums(s: str) -> tuple[int,...]:
    try:
        return tuple(int(x) for x in s.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma separated integers") from exc


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--neurons",type=int,default=32)
    p.add_argument("--active-roles",type=int,default=8)
    p.add_argument("--ticks",type=int,default=8)
    p.add_argument("--seeds",type=parse_nums,default=(17,23))
    p.add_argument("--batches",type=parse_nums,default=(1,4))
    p.add_argument("--synapse-record-bytes",type=parse_nums,default=(4,8))
    p.add_argument("--fifo-depth-events",type=int,default=4)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    plan=ServiceSweepPlan(neurons=a.neurons,active_roles=a.active_roles,
                          ticks=a.ticks,seeds=a.seeds,batches=a.batches,
                          synapse_record_bytes=a.synapse_record_bytes)
    assumption=ServiceAssumptions(fifo_depth_events=a.fifo_depth_events)
    report=run_service_sweep(plan,assumption)
    sources=(
        "src/neuromorphic_accelerator_v1/m02_dense_reference.py",
        "src/neuromorphic_accelerator_v1/m02_event_reference.py",
        "src/neuromorphic_accelerator_v1/m03_sparse_reference.py",
        "src/neuromorphic_accelerator_v1/m03_traffic.py",
        "src/neuromorphic_accelerator_v1/m06_block_residency.py",
        "src/neuromorphic_accelerator_v1/m06_paged_replay.py",
        "src/neuromorphic_accelerator_v1/m07_policy_baseline.py",
        "src/neuromorphic_accelerator_v1/m07_activity_cache.py",
        "src/neuromorphic_accelerator_v1/m07_service_model.py",
        "scripts/m07_service_closeout.py",
    )
    report["source_sha256"]={
        item:hashlib.sha256((ROOT/item).read_bytes()).hexdigest()
        for item in sources
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2,sort_keys=True)
        f.write("\n")
    print("M07_5_SOURCE_ONLY_SERVICE_PASS",
          "matched_cases",report["number_of_matched_cases"],
          "output",a.output)
    for item in report["rows"]:
        for case in item["cases"]:
            if (case["policy"]=="lru" and case["synapse_record_bytes_hypothetical"]==4):
                print("M07_5_MODEL_ONLY",item["seed"],item["locality"],
                      "batch",case["batch_width"],
                      "queue_stalls",case["ingress_queue"]["producer_full_stall_cycles"],
                      "assumed_run_cycles",
                      case["modeled_serialized_complete_run_cycles_assumed"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
