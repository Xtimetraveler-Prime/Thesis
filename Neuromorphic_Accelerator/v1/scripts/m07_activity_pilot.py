#!/usr/bin/env python3
"""M07.4 source-only causal history eviction pilot (no YANA RTL/Vivado/DDR)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuromorphic_accelerator_v1.m07_activity_study import (
    ActivityStudyPlan, run_activity_study,
)


def csv_ints(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(v) for v in text.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc


def geometry_pairs(text: str) -> tuple[tuple[int, int], ...]:
    try:
        return tuple(tuple(int(v) for v in item.split(":")) for item in text.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "expected block:budget,block:budget pairs") from exc


def source_sha256() -> dict[str, str]:
    names = (
        "src/neuromorphic_accelerator_v1/m02_dense_reference.py",
        "src/neuromorphic_accelerator_v1/m02_event_reference.py",
        "src/neuromorphic_accelerator_v1/m03_sparse_reference.py",
        "src/neuromorphic_accelerator_v1/m03_workloads.py",
        "src/neuromorphic_accelerator_v1/m06_block_residency.py",
        "src/neuromorphic_accelerator_v1/m06_paged_replay.py",
        "src/neuromorphic_accelerator_v1/m07_policy_baseline.py",
        "src/neuromorphic_accelerator_v1/m07_activity_cache.py",
        "src/neuromorphic_accelerator_v1/m07_activity_study.py",
        "scripts/m07_activity_pilot.py",
    )
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in names}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--neurons", type=int, default=128)
    ap.add_argument("--active-roles", type=int, default=16)
    ap.add_argument("--fanout", type=int, default=3)
    ap.add_argument("--events-per-tick", type=int, default=4)
    ap.add_argument("--ticks", type=int, default=8)
    ap.add_argument("--seeds", type=csv_ints, default=(17, 23))
    ap.add_argument("--geometries", type=geometry_pairs, default=(
        (4,128),(4,256),(8,256),(8,512)))
    ap.add_argument("--history-depths", type=csv_ints, default=(4, 16, 32))
    ap.add_argument("--state-bytes", type=int, default=16)
    ap.add_argument("--onchip-capacity-bytes", type=int, default=2048)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    plan = ActivityStudyPlan(
        neuron_count=args.neurons, active_roles=args.active_roles,
        fanout_per_active=args.fanout, events_per_tick=args.events_per_tick,
        ticks=args.ticks, seeds=args.seeds, geometries=args.geometries,
        history_depths=args.history_depths, state_bytes=args.state_bytes,
        declared_full_onchip_bytes=args.onchip_capacity_bytes,
    )
    report = run_activity_study(plan)
    report["source_sha256"] = source_sha256()
    report["prior_art_ledger"] = "docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md"
    report["prior_art_classification"] = (
        "ARCHITECTURAL_ANALOGY_ONLY_NO_YANA_HARDWARE_OR_PERFORMANCE_EQUIVALENCE")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("M07_4_HISTORY_PILOT_MODEL_ONLY_PASS",
          "geometry_seed_cases=", report["geometry_seed_cases"],
          "policy_history_comparisons=", report["policy_history_comparisons"],
          "output=", args.output)
    print("M07_4_MICROTRACE_ONLY",
          "LRU_misses=", report["microtrace"]["models"]["lru"]["misses"],
          "history_misses=", report["microtrace"]["models"]["activity_history"]["misses"])
    print("M07_4_M03_PILOT", report["witnessed_outcomes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
