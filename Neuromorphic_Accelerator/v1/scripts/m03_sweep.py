#!/usr/bin/env python3
"""M03 PC-ONLY multi-seed N/fanout/event-rate/locality controlled sweep.

Each listed scenario checks *both* role-isomorphic clustered/dispersed
networks, independently against the M02 references, then records only work
and traffic counters. Not 4 implemented RTL variants, not physical replicates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m03_workloads import WorkloadSpec, sha256_json
from neuromorphic_accelerator_v1.m03_traffic import ComparisonConfig
from m03_explore import build_report


def csv_ints(label: str, raw: str, *, minimum: int = 0) -> tuple[int, ...]:
    try:
        values = tuple(int(x.strip()) for x in raw.split(","))
    except ValueError as exc:
        raise ValueError(f"{label} requires CSV integers") from exc
    if not values or len(set(values)) != len(values) or any(
        v < minimum for v in values
    ):
        raise ValueError(
            f"{label} requires distinct CSV integers >= {minimum}"
        )
    return values


def run_sweep(
    *,
    neuron_counts: tuple[int, ...] = (64, 128, 256),
    fanouts: tuple[int, ...] = (0, 2, 4),
    events_per_tick_values: tuple[int, ...] = (0, 3),
    seeds: tuple[int, ...] = (17, 23),
    active_roles: int = 16,
    ticks: int = 10,
    comparison_config: ComparisonConfig = ComparisonConfig(),
) -> dict:
    if any(type(x) is not tuple or not x for x in
           (neuron_counts, fanouts, events_per_tick_values, seeds)):
        raise ValueError("all sweep axes must be nonempty tuples")
    if type(active_roles) is not int or active_roles < 1:
        raise ValueError("active_roles must be >=1")
    if type(ticks) is not int or ticks < 1:
        raise ValueError("ticks must be >=1")
    for name, values, lower in [
        ("neuron_counts", neuron_counts, 1),
        ("fanouts", fanouts, 0),
        ("events_per_tick_values", events_per_tick_values, 0),
        ("seeds", seeds, 0),
    ]:
        if any(type(x) is not int or x < lower for x in values):
            raise ValueError(f"{name}: invalid parameter")
        if len(set(values)) != len(values):
            raise ValueError(f"{name}: duplicate grid axis values")

    rows = []
    for n in neuron_counts:
        for fanout in fanouts:
            for events in events_per_tick_values:
                for seed in seeds:
                    spec = WorkloadSpec(
                        neuron_count=n, active_roles=active_roles,
                        fanout_per_active=fanout,
                        external_events_per_tick=events, ticks=ticks, seed=seed,
                    )
                    case = build_report(spec, comparison_config, locality="both")
                    clustered, dispersed = (case["experimental_results"][where]
                                            for where in ("clustered", "dispersed"))
                    record = {
                        "neuron_count": n,
                        "active_roles": active_roles,
                        "fanout_per_active": fanout,
                        "external_events_per_tick": events,
                        "ticks": ticks,
                        "seed": seed,
                        "canonical_role_workload_sha256": clustered["canonical_role_workload_sha256"],
                        "canonical_functional_trace_sha256": clustered["canonical_functional_trace_sha256"],
                        "spikes": clustered["neural_equivalence"]["total_spikes"],
                        "exact_sparse_neuron_updates": clustered["neural_equivalence"]["exact_sparse_neuron_updates"],
                        "dense_neuron_updates": clustered["neural_equivalence"]["dense_neuron_updates"],
                        "cases": {},
                    }
                    for place, result in (("clustered", clustered),
                                          ("dispersed", dispersed)):
                        record["cases"][place] = {}
                        for mode, m in result["four_way_models"].items():
                            record["cases"][place][mode] = (
                                {"available": False, "reason": m["reason"]}
                                if not m["available"] else {
                                    "available": True,
                                    "neuron_updates": m["evaluated_neuron_steps"],
                                    "synapse_edge_visits": m["synapse_edge_visits"],
                                    "state_read_bytes": m["state_read_bytes"],
                                    "state_write_bytes": m["state_write_bytes"],
                                    "synapse_read_bytes": m["synapse_read_bytes"],
                                    "total_modeled_bytes": m["total_modeled_bytes"],
                                    "total_modeled_transactions": m["total_modeled_transactions"],
                                })
                    if record["cases"]["clustered"]["event/ddr"]["neuron_updates"] != (
                            record["cases"]["dispersed"]["event/ddr"]["neuron_updates"]):
                        raise AssertionError("isomorphic workload altered neuron update count")
                    rows.append(record)
    return {
        "schema": "m03-fixed-work-activity-locality-sweep-v1",
        "status": "PC_ONLY_4_WAY_ANALYTICAL_TRAFFIC_NOT_HARDWARE",
        "independent_pc_seed_count": len(seeds),
        "not_physical_replicates": True,
        "grid_parameters": {
            "neuron_counts": list(neuron_counts),
            "fanouts": list(fanouts),
            "events_per_tick_values": list(events_per_tick_values),
            "seeds": list(seeds),
            "active_roles": active_roles,
            "ticks": ticks,
            "comparison_config": {
                k: getattr(comparison_config, k)
                for k in comparison_config.__dataclass_fields__
            },
        },
        "paired_role_isomorphic_cases": len(rows),
        "grid": rows,
        "grid_sha256": sha256_json(rows),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--neuron-counts", default="64,128,256")
    parser.add_argument("--fanouts", default="0,2,4")
    parser.add_argument("--events-per-tick-values", default="0,3")
    parser.add_argument("--seeds", default="17,23")
    parser.add_argument("--active-roles", type=int, default=16)
    parser.add_argument("--ticks", type=int, default=10)
    parser.add_argument("--out", type=Path)
    a = parser.parse_args(argv)
    try:
        result = run_sweep(
            neuron_counts=csv_ints("neuron counts", a.neuron_counts, minimum=1),
            fanouts=csv_ints("fanouts", a.fanouts, minimum=0),
            events_per_tick_values=csv_ints("events", a.events_per_tick_values, minimum=0),
            seeds=csv_ints("seeds", a.seeds, minimum=0),
            active_roles=a.active_roles, ticks=a.ticks,
        )
        rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
        if a.out:
            with a.out.open("x", encoding="utf-8") as file:
                file.write(rendered)
            print(f"M03_PC_ONLY_SWEEP_ORIGINAL={a.out}")
        else:
            print(rendered, end="")
        print("M03_4_WAY_MATCHED_SEED_SWEEP_PASS=1", file=sys.stderr)
        return 0
    except (ValueError, OSError, AssertionError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
