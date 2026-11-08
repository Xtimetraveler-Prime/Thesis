#!/usr/bin/env python3
"""M03 deterministic role-isomorphic neural work/traffic experiment, NO BOARD."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m03_workloads import (
    WorkloadSpec, build_workload, sha256_json,
)
from neuromorphic_accelerator_v1.m03_traffic import ComparisonConfig, compare_workload


def build_report(spec: WorkloadSpec, config: ComparisonConfig, *,
                 locality: str = "both") -> dict:
    if locality not in ("clustered", "dispersed", "both"):
        raise ValueError("locality must be clustered, dispersed or both")
    localities = (("clustered", "dispersed") if locality == "both"
                  else (locality,))
    results = {}
    for place in localities:
        options = WorkloadSpec(
            neuron_count=spec.neuron_count,
            active_roles=spec.active_roles,
            fanout_per_active=spec.fanout_per_active,
            external_events_per_tick=spec.external_events_per_tick,
            ticks=spec.ticks, seed=spec.seed, state_bits=spec.state_bits,
            locality=place,
        )
        work = build_workload(options)
        results[place] = compare_workload(work, config)
    if locality == "both":
        a, b = results["clustered"], results["dispersed"]
        if (a["canonical_role_workload_sha256"] !=
                b["canonical_role_workload_sha256"]):
            raise AssertionError("locality changed the canonical network/input")
        if (a["canonical_functional_trace_sha256"] !=
                b["canonical_functional_trace_sha256"]):
            raise AssertionError("locality changed expected LIF outputs")
        for mode in ("timestep", "event"):
            for place in ("clustered", "dispersed"):
                row = results[place]["four_way_models"]
                if not row[f"{mode}/ddr"]["functional_parity_verified"]:
                    raise AssertionError("invalid neural parity")
        # Traffic must be evaluated after functional parity; no need to force
        # it to differ in every case (zero-spike cases can be identical).
    return {
        "schema": "m03-isomorphic-workload-comparison-v1",
        "measurement_status": "PC_ONLY_FUNCTIONAL_ORACLE_AND_ANALYTICAL_TRAFFIC",
        "claim_boundary": "No board, no DMA/DDR hardware timing, no synaptic network accuracy",
        "isomorphic_pair_verified": locality == "both",
        "experimental_results": results,
        "report_content_sha256": sha256_json(results),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neuron-count", type=int, default=128)
    parser.add_argument("--active-roles", type=int, default=16)
    parser.add_argument("--fanout-per-active", type=int, default=4)
    parser.add_argument("--external-events-per-tick", type=int, default=6)
    parser.add_argument("--ticks", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--state-bits", type=int, default=16)
    parser.add_argument("--locality", default="both",
                        choices=("clustered", "dispersed", "both"))
    parser.add_argument("--state-bytes", type=int, default=16)
    parser.add_argument("--resident-budget-bytes", type=int, default=512)
    parser.add_argument("--onchip-capacity-bytes", type=int, default=2048)
    parser.add_argument("--block-neurons", type=int, default=8)
    parser.add_argument("--synapse-record-bytes", type=int, default=8)
    parser.add_argument("--max-transfer-bytes", type=int, default=256)
    parser.add_argument("--policy", choices=("individual", "block", "hybrid"),
                        default="block")
    parser.add_argument("--hybrid-pins", type=int, default=0)
    parser.add_argument("--out", type=Path,
                        help="exclusive-create JSON evidence path, else stdout")
    args = parser.parse_args(argv)
    try:
        spec = WorkloadSpec(
            neuron_count=args.neuron_count, active_roles=args.active_roles,
            fanout_per_active=args.fanout_per_active,
            external_events_per_tick=args.external_events_per_tick,
            ticks=args.ticks, seed=args.seed, state_bits=args.state_bits,
        )
        cfg = ComparisonConfig(
            state_bytes=args.state_bytes,
            onchip_state_capacity_bytes=args.onchip_capacity_bytes,
            ddr_state_cache_bytes=args.resident_budget_bytes,
            block_neurons=args.block_neurons,
            max_transfer_bytes=args.max_transfer_bytes,
            synapse_record_bytes=args.synapse_record_bytes,
            residency_policy=args.policy,
            hybrid_pinned_neurons=args.hybrid_pins,
        )
        data = build_report(spec, cfg, locality=args.locality)
        output = json.dumps(data, sort_keys=True, indent=2) + "\n"
        if args.out is None:
            print(output, end="")
        else:
            with args.out.open("x", encoding="utf-8") as handle:
                handle.write(output)
            print(f"M03_PC_ONLY_ORIGINAL_REPORT={args.out}")
        print("M03_CANONICAL_LIF_PARITY_AND_TRAFFIC_PASS=1", file=sys.stderr)
        return 0
    except (ValueError, OSError, AssertionError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
