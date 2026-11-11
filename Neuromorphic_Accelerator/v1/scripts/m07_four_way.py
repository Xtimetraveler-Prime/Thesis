#!/usr/bin/env python3
"""M07.2 SOURCE-ONLY matched four-way neural-state and synapse-traffic study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m03_workloads import WorkloadSpec
from neuromorphic_accelerator_v1.m07_matched_controls import (
    FourWayPolicyConfig, build_matched_locality_report,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--neurons", type=int, default=128)
    ap.add_argument("--active-roles", type=int, default=16)
    ap.add_argument("--fanout", type=int, default=4)
    ap.add_argument("--events-per-tick", type=int, default=6)
    ap.add_argument("--ticks", type=int, default=16)
    ap.add_argument("--seed", type=int, default=20261110)
    ap.add_argument("--block-neurons", type=int, default=8)
    ap.add_argument("--resident-slots", type=int, default=4)
    ap.add_argument("--state-bytes", type=int, default=16)
    ap.add_argument("--onchip-capacity-bytes", type=int, default=2048)
    ap.add_argument("--max-transfer-bytes", type=int, default=256)
    ap.add_argument("--synapse-record-bytes", type=int, default=8)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    spec = WorkloadSpec(neuron_count=args.neurons, active_roles=args.active_roles,
                        fanout_per_active=args.fanout,
                        external_events_per_tick=args.events_per_tick,
                        ticks=args.ticks, seed=args.seed)
    cfg = FourWayPolicyConfig(
        state_bytes=args.state_bytes, block_neurons=args.block_neurons,
        resident_slots=args.resident_slots,
        onchip_state_capacity_bytes=args.onchip_capacity_bytes,
        max_model_transfer_bytes=args.max_transfer_bytes,
        synapse_record_bytes=args.synapse_record_bytes)
    report = build_matched_locality_report(spec, cfg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("M07_2_FOUR_WAY_MODEL_ONLY_PASS", args.output)
    for locality in ("clustered", "dispersed"):
        for policy in ("direct", "lru"):
            rows = report["results_by_locality"][locality]["controls_by_policy"][policy]
            print("M07_2_MODEL_ONLY", locality, policy,
                  "event_ddr_state_bytes=",
                  rows["event/ddr"]["state_read_bytes"] +
                  rows["event/ddr"]["state_write_bytes"],
                  "timestep_ddr_state_bytes=",
                  rows["timestep/ddr"]["state_read_bytes"] +
                  rows["timestep/ddr"]["state_write_bytes"],
                  "onchip_available=",
                  rows["event/onchip"]["available"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
