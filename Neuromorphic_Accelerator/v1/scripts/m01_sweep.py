#!/usr/bin/env python3
"""M01 reproducible PC-ONLY grid over block granularity and on-chip capacity.

No timing claims: each result counts write-modifying neuron-state access
transfers only, never synapses or full SNN inference. Each policy uses the
identical trace and explicit shared byte budget within each grid cell.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m01_residency import StudyConfig, run_study


def parse_ints(label: str, raw: str) -> tuple[int, ...]:
    try:
        values = tuple(int(v.strip()) for v in raw.split(","))
    except ValueError as exc:
        raise ValueError(f"{label}: expected comma-separated integers") from exc
    if not values or any(v <= 0 for v in values) or len(set(values)) != len(values):
        raise ValueError(f"{label}: distinct positive comma-separated integers required")
    return values


def evaluate_grid(
    *,
    neuron_count: int,
    active_neurons: int,
    requests: int,
    state_bytes: int,
    pinned_neurons: int,
    max_transfer_bytes: int,
    seed: int,
    block_sizes: tuple[int, ...],
    resident_budgets: tuple[int, ...],
) -> dict:
    grid = []
    for budget in resident_budgets:
        for block_size in block_sizes:
            config = StudyConfig(
                neuron_count=neuron_count,
                state_bytes=state_bytes,
                resident_budget_bytes=budget,
                block_neurons=block_size,
                hybrid_pinned_neurons=pinned_neurons,
                max_transfer_bytes=max_transfer_bytes,
            )
            config.validate()  # no silently skipped unsupported grid cells
            for locality in ("clustered", "dispersed"):
                raw = run_study(
                    config, active_neurons=active_neurons, requests=requests,
                    seed=seed, locality=locality,
                )
                rows = {}
                for approach, m in raw["results"].items():
                    rows[approach] = {
                        "total_bytes": m["total_bytes"],
                        "read_bytes": m["read_bytes"],
                        "write_bytes": m["write_bytes"],
                        "total_transactions": m["total_transactions"],
                        "misses": m["misses"],
                        "resident_hits": m["resident_hits"],
                        "evictions": m["evictions"],
                        "dynamic_cache_slots": m["dynamic_cache_slots"],
                        "allocated_resident_bytes": m["allocated_resident_bytes"],
                        "wasted_resident_budget_bytes": m["wasted_resident_budget_bytes"],
                    }
                grid.append({
                    "resident_budget_bytes": budget,
                    "block_neurons": block_size,
                    "locality": locality,
                    "trace_sha256": raw["trace"]["sha256"],
                    "results": rows,
                })
    return {
        "schema": "m01-capacity-granularity-sweep-v1",
        "status": "PC_ONLY_ANALYTICAL_TRAFFIC_NOT_REAL_DDR_OR_SNN",
        "request_semantics": "one write-modifying neuron-state access",
        "arguments": {
            "neuron_count": neuron_count,
            "active_neurons": active_neurons,
            "requests": requests,
            "state_bytes": state_bytes,
            "pinned_neurons": pinned_neurons,
            "max_transfer_bytes": max_transfer_bytes,
            "seed": seed,
            "block_sizes": list(block_sizes),
            "resident_budgets": list(resident_budgets),
        },
        "grid": grid,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neuron-count", type=int, default=4096)
    parser.add_argument("--active-neurons", type=int, default=64)
    parser.add_argument("--requests", type=int, default=512)
    parser.add_argument("--state-bytes", type=int, default=16)
    parser.add_argument("--pinned-neurons", type=int, default=32)
    parser.add_argument("--max-transfer-bytes", type=int, default=256)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--block-sizes", default="4,8,16,32")
    parser.add_argument("--resident-budgets", default="1024,2048,4096")
    parser.add_argument("--out", type=Path,
                        help="exclusive-create JSON report path, else stdout")
    args = parser.parse_args(argv)
    try:
        record = evaluate_grid(
            neuron_count=args.neuron_count,
            active_neurons=args.active_neurons,
            requests=args.requests,
            state_bytes=args.state_bytes,
            pinned_neurons=args.pinned_neurons,
            max_transfer_bytes=args.max_transfer_bytes,
            seed=args.seed,
            block_sizes=parse_ints("block sizes", args.block_sizes),
            resident_budgets=parse_ints("resident budgets", args.resident_budgets),
        )
        output = json.dumps(record, indent=2, sort_keys=True) + "\n"
        if args.out is None:
            sys.stdout.write(output)
        else:
            with args.out.open("x", encoding="utf-8") as handle:
                handle.write(output)
            print(f"M01_PC_ONLY_SWEEP_PATH={args.out}")
        print("M01_PC_ONLY_CAPACITY_GRANULARITY_SWEEP_PASS=1", file=sys.stderr)
        return 0
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
