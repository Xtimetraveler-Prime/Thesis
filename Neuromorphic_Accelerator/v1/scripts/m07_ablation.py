#!/usr/bin/env python3
"""M07.3 controlled state-cache/model traffic grid, NO FPGA OR VITIS."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuromorphic_accelerator_v1.m07_ablation_sweep import AblationPlan, run_ablation


def _csv_ints(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(item) for item in text.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated decimal integers") from exc


def source_hashes() -> dict[str, str]:
    sources = (
        "src/neuromorphic_accelerator_v1/m02_dense_reference.py",
        "src/neuromorphic_accelerator_v1/m02_event_reference.py",
        "src/neuromorphic_accelerator_v1/m03_sparse_reference.py",
        "src/neuromorphic_accelerator_v1/m03_workloads.py",
        "src/neuromorphic_accelerator_v1/m03_traffic.py",
        "src/neuromorphic_accelerator_v1/m06_block_residency.py",
        "src/neuromorphic_accelerator_v1/m06_paged_replay.py",
        "src/neuromorphic_accelerator_v1/m07_policy_baseline.py",
        "src/neuromorphic_accelerator_v1/m07_matched_controls.py",
        "src/neuromorphic_accelerator_v1/m07_ablation_sweep.py",
        "scripts/m07_ablation.py",
    )
    return {s: sha256((ROOT / s).read_bytes()).hexdigest() for s in sources}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--neurons", type=int, default=128)
    p.add_argument("--active-roles", type=int, default=16)
    p.add_argument("--fanout", type=int, default=3)
    p.add_argument("--events-per-tick", type=int, default=4)
    p.add_argument("--ticks", type=int, default=8)
    p.add_argument("--seeds", type=_csv_ints, default=(17, 23))
    p.add_argument("--blocks", type=_csv_ints, default=(2, 4, 8))
    p.add_argument("--budgets", type=_csv_ints, default=(128, 256, 512))
    p.add_argument("--state-bytes", type=int, default=16)
    p.add_argument("--onchip-capacity-bytes", type=int, default=2048)
    p.add_argument("--max-transfer-bytes", type=int, default=256)
    p.add_argument("--synapse-record-bytes", type=int, default=8)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    plan = AblationPlan(
        neuron_count=args.neurons, active_roles=args.active_roles,
        fanout_per_active=args.fanout,
        external_events_per_tick=args.events_per_tick, ticks=args.ticks,
        seeds=args.seeds, block_sizes_neurons=args.blocks,
        resident_budgets_bytes=args.budgets, state_bytes=args.state_bytes,
        onchip_state_capacity_bytes=args.onchip_capacity_bytes,
        max_model_transfer_bytes=args.max_transfer_bytes,
        synapse_record_bytes=args.synapse_record_bytes,
    )
    results = run_ablation(plan)
    results["source_sha256"] = source_hashes()
    results["prior_art_comparison_document"] = (
        "docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md")
    results["prior_art_comparison_status"] = (
        "ARCHITECTURAL_ANALOGY_ONLY_NO_NUMERIC_HARDWARE_COMPARISON")
    # Source-only provenance is immutable: Python 'x' never overwrites an
    # accepted or failed prior run. Owner supplies fresh timestamped path.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("M07_3_ABLATION_MODEL_ONLY_PASS",
          "parameter_combinations=", results["num_parameter_combinations"],
          "four_way_rows=", results["num_policy_locality_four_way_rows"],
          "output=", args.output)
    for row in results["rows"]:
        print("M07_3_MODEL_ONLY", "seed=", row["seed"],
              "budget_bytes=", row["resident_budget_bytes"],
              "block_neurons=", row["block_neurons"],
              "slots=", row["resident_slots"],
              "lru_locality_penalty_bytes=", row["lru_event_state_locality_penalty_bytes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
