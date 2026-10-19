#!/usr/bin/env python3
"""P06-B1.5 OFF-BOARD deterministic P05-sized paging traffic estimator.

Examples:
  PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape dense40
  PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape dense1000
  PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape sparse27 --numerical
  PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape dense1000 --order alternate
  PYTHONPATH="$PWD/src" python scripts/p06_b15_paging_probe.py --shape dense1000 --assume-gib-s 1

The full dense1000 mode is STRUCTURAL ONLY: it never executes 794k dense
synapses for 26 ticks. There is no physical KV260 access or timing claim.
"""
from __future__ import annotations

import argparse
import json

from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b14_monolithic import pixel_schedule_independent
from loihi_twin_v2.p06_b14_synthetic_fixtures import sparse_27_core_network
from loihi_twin_v2.p06_b15_paging import (
    project_schedule_only, run_paged_model, hypothetical_transport_seconds,
)
from p06_b12_synthetic_probe import synthetic_dense_network


def run(shape: str, mode: str, assumed_gib_s: float | None) -> dict:
    if shape == "dense6":
        source = synthetic_dense_network(6)
        opts = B12Options(readout_population="z")
    elif shape == "dense40":
        source = synthetic_dense_network(40)
        opts = B12Options(readout_population="z")
    elif shape == "dense1000":
        source = synthetic_dense_network(1000)
        opts = B12Options(readout_population="z")
    elif shape == "sparse27":
        source = sparse_27_core_network()
        opts = B12Options(readout_population="z", compartments_per_core=39)
    else:
        raise ValueError("unrecognized profile")
    result = compile_synapse_aware(source, opts)
    ids = tuple(c.core_id for c in result.compiled.logical_deployment.core_configs)
    orders = tuple(ids if tick % 2 == 0 else ids[::-1] for tick in range(26)) if (
        mode == "alternate") else None
    # Both modes use all 26 algorithmic ticks; the new static path is
    # explicitly source-derived and doesn't falsely claim neuron parity.
    structural = project_schedule_only(result, service_orders=orders)
    # The structural path intentionally never invokes the integer neuron
    # engine, even for the densely connected 794k-edge 27-core topology.
    report = structural
    report["profile_shape"] = shape
    if assumed_gib_s is not None:
        report = {
            **report,
            "hypothetical_assumed_sustained_aggregate_GiB_per_s": assumed_gib_s,
            "hypothetical_page_bytes_divided_by_bandwidth_seconds":
                hypothetical_transport_seconds(
                    report["paging"]["estimated_page_engine_total_bytes"], assumed_gib_s),
            "hypothetical_timing_excludes": (
                "PL compute, PS cache/page setup, host packet routing,"
                " global barriers, DDR contention and all other workloads"),
            "hypothetical_not_measured_or_calibrated": True,
        }
    return report


def run_numerical(shape: str, mode: str, assumed_gib_s: float | None) -> dict:
    if shape == "dense1000":
        raise ValueError("B1.5 refuses unverified full-DENSE 794000-edge 26-tick numerical inference")
    if shape == "sparse27":
        source, opts = sparse_27_core_network(), B12Options(
            readout_population="z", compartments_per_core=39)
    else:
        source, opts = synthetic_dense_network(
            6 if shape == "dense6" else 40), B12Options(readout_population="z")
    result = compile_synapse_aware(source, opts)
    ids = tuple(c.core_id for c in result.compiled.logical_deployment.core_configs)
    orders = tuple(ids if tick % 2 == 0 else ids[::-1] for tick in range(26)) if (
        mode == "alternate") else None
    schedule = {"pixels": pixel_schedule_independent(bytes([255] * 784))}
    model = run_paged_model(
        source, result, schedule, readout_population="z", service_orders=orders)
    report = model.report()
    if assumed_gib_s is not None:
        report = {
            **report,
            "hypothetical_assumed_sustained_aggregate_GiB_per_s": assumed_gib_s,
            "hypothetical_page_bytes_divided_by_bandwidth_seconds":
                hypothetical_transport_seconds(
                    report["paging"]["estimated_page_engine_total_bytes"], assumed_gib_s),
            "hypothetical_not_measured_or_calibrated": True,
        }
    report["profile_shape"] = shape
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", choices=("dense6", "dense40", "dense1000", "sparse27"),
                        default="dense40")
    parser.add_argument("--order", choices=("forward", "alternate"), default="forward")
    parser.add_argument("--numerical", action="store_true",
                        help="run B1.4 oracle and resident-scheduled production chip; prohibited for dense1000")
    parser.add_argument("--assume-gib-s", type=float,
                        help="what-if aggregate page-engine GiB/s; never a KV260 measured rate")
    args = parser.parse_args()
    report = (run_numerical(args.shape, args.order, args.assume_gib_s)
              if args.numerical else run(args.shape, args.order, args.assume_gib_s))
    print(json.dumps(report, indent=2, sort_keys=True))
    print("P06_B15_HOST_ONLY_PAGING_ESTIMATE_PASS=1")


if __name__ == "__main__":
    main()
