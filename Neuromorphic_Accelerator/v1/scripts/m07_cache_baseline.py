#!/usr/bin/env python3
"""Immutable, SOURCE-ONLY M07.1 matched cache baseline report (no board)."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m03_workloads import WorkloadSpec, build_workload
from neuromorphic_accelerator_v1.m06_block_residency import Geometry
from neuromorphic_accelerator_v1.m07_policy_baseline import run_policy


def build_report(*, neurons: int = 32, active_roles: int = 8,
                 fanout: int = 3, events_per_tick: int = 4,
                 ticks: int = 12, seed: int = 20261110,
                 block_neurons: int = 4, slots: int = 2,
                 transfer_bytes: int = 16) -> dict:
    spec = WorkloadSpec(neuron_count=neurons, active_roles=active_roles,
                        fanout_per_active=fanout,
                        external_events_per_tick=events_per_tick,
                        ticks=ticks, seed=seed)
    geometry = Geometry(logical_neurons=neurons, bytes_per_neuron=16,
                        neurons_per_block=block_neurons,
                        resident_budget_bytes=slots*block_neurons*16,
                        max_model_transfer_bytes=transfer_bytes)
    geometry.validate()
    results = {}
    for locality in ("clustered", "dispersed"):
        w = build_workload(replace(spec, locality=locality))
        results[locality] = {
            policy: run_policy(w, geometry, policy=policy)
            for policy in ("direct", "lru")
        }
    c = results["clustered"]["direct"]
    for locality in ("clustered", "dispersed"):
        for policy in ("direct", "lru"):
            r = results[locality][policy]
            for field in ("role_workload_sha256", "canonical_trace_sha256",
                          "evaluations", "spikes", "delivered_events",
                          "fanout_edge_visits"):
                if r[field] != c[field]:
                    raise AssertionError("unmatched role-isomorphic experiment " + field)
    return {
        "schema": "m07-cache-policy-comparison-v1",
        "measurement_boundary": "PC software canonical state transfers only",
        "role_isomorphic_checked": True,
        "physical_hardware_measured": False,
        "vendor_hls_amd_rtl_executed": False,
        "queue_timing_measured": False,
        "config": {
            "workload": vars(spec), "geometry": vars(geometry),
            "state_placement": "emulated canonical full-page backing",
            "synapse_placement": "M06 replay on-chip adjacency (NOT counted)",
        },
        "results": results,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--neurons", type=int, default=32)
    p.add_argument("--active-roles", type=int, default=8)
    p.add_argument("--fanout", type=int, default=3)
    p.add_argument("--events-per-tick", type=int, default=4)
    p.add_argument("--ticks", type=int, default=12)
    p.add_argument("--seed", type=int, default=20261110)
    p.add_argument("--block-neurons", type=int, default=4)
    p.add_argument("--slots", type=int, default=2)
    p.add_argument("--transfer-bytes", type=int, default=16)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = build_report(neurons=args.neurons, active_roles=args.active_roles,
                          fanout=args.fanout, events_per_tick=args.events_per_tick,
                          ticks=args.ticks, seed=args.seed,
                          block_neurons=args.block_neurons, slots=args.slots,
                          transfer_bytes=args.transfer_bytes)
    # Exclusive create preserves the first result and never silently
    # overwrites user evidence. Owner should use a fresh timestamped path.
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")
    print("M07_1_MODEL_ONLY_PASS", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
