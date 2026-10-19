#!/usr/bin/env python3
"""P06-B1.4 host-only differential 26-tick integer proof.

--shape dense6 (default): 784→6→10 dense synthetic effective integer weights.
--shape dense40 (optional): B1.2 39+1 partition with 31,760 dense connections.
--shape sparse27 (optional): 784→1000→10 sparse NUMERICAL graph in 27 cores.
These are synthetic weights ONLY, not trained data or a physical FPGA run.
"""
from __future__ import annotations

import argparse
import json

from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware
from loihi_twin_v2.p06_b14_differential import run_and_compare
from loihi_twin_v2.p06_b14_monolithic import pixel_schedule_independent
from loihi_twin_v2.p06_b14_synthetic_fixtures import sparse_27_core_network
from p06_b12_synthetic_probe import synthetic_dense_network


def run(shape: str) -> dict:
    if shape == "sparse27":
        source = sparse_27_core_network()
        options = B12Options(readout_population="z", compartments_per_core=39)
    elif shape in ("dense6", "dense40"):
        source = synthetic_dense_network(6 if shape == "dense6" else 40)
        options = B12Options(readout_population="z")
    else:
        raise ValueError("supported synthetic shapes: dense6, dense40, sparse27")
    result = compile_synapse_aware(source, options)
    events = {"pixels": pixel_schedule_independent(bytes([255] * 784))}
    pass1 = run_and_compare(source, result, events, readout_population="z")
    core_ids = tuple(c.core_id for c in result.compiled.logical_deployment.core_configs)
    pass2 = run_and_compare(
        source, result, events, readout_population="z",
        service_order=core_ids[::-1], reverse_packet_drain=True)
    if pass1.output_trace_sha256 != pass2.output_trace_sha256:
        raise AssertionError("B1.4 alternative legal service ordering diverged")
    if pass1.reference.trace_sha256 != pass2.reference.trace_sha256:
        raise AssertionError("B1.4 independent monolithic hash changed across runs")
    report = pass1.report()
    report.update({
        "synthetic_shape": shape,
        "logical_core_count": result.capacity_audit["logical_core_count"],
        "capacity_audit_sha256": result.capacity_audit["audit_sha256"],
        "service_order_invariance": "PASS",
        "synthetic_integer_weights_only": True,
        "full_dense_784_1000_10_numerical_execution": False,
    })
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", choices=("dense6", "dense40", "sparse27"),
                        default="dense6")
    args = parser.parse_args()
    report = run(args.shape)
    print(json.dumps(report, indent=2, sort_keys=True))
    print("P06_B14_INDEPENDENT_DIFFERENTIAL_PASS=1")


if __name__ == "__main__":
    main()
