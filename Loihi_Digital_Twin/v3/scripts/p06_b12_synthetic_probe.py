#!/usr/bin/env python3
"""P06-B1.2 synthetic-only structural resource probe.

No MNIST archive, trained checkpoint, board connection, Vitis/XSDB, or DDR
overwrites. The graph is explicitly project-synthetic, not a classifier.
"""
from __future__ import annotations

import argparse
import json

from loihi_twin_v2.compiler import (
    InputPopulationSpec, InputProjectionSpec, NetworkSpec, PopulationSpec,
    ProjectionConnection, ProjectionSpec,
)
from loihi_twin_v2.compartment import CompartmentConfig
from loihi_twin_v2.p06_b12_partition import B12Options, compile_synapse_aware


def synthetic_dense_network(hidden: int) -> NetworkSpec:
    if not 1 <= hidden <= 1000:
        raise ValueError("synthetic hidden neurons must be between 1 and 1000")
    cfg_h = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=2)
    cfg_z = CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)
    return NetworkSpec(
        populations=(PopulationSpec("h", hidden, cfg_h), PopulationSpec("z", 10, cfg_z)),
        input_populations=(InputPopulationSpec("pixels", 784),),
        input_projections=(InputProjectionSpec(
            "synthetic_input", "pixels", "h",
            tuple(ProjectionConnection(s, d, 1 + (41 * s + 13 * d) % 997)
                  for s in range(784) for d in range(hidden)),
        ),),
        projections=(ProjectionSpec(
            "synthetic_readout", "h", "z",
            tuple(ProjectionConnection(s, d, 1 + (43 * s + 17 * d) % 3001)
                  for s in range(hidden) for d in range(10)),
        ),),
    )


def run(hidden: int) -> dict:
    network = synthetic_dense_network(hidden)
    result = compile_synapse_aware(network, B12Options(readout_population="z"))
    manifest = result.capacity_audit
    report = result.compiled.report()
    want_connections = hidden * 784 + hidden * 10
    if report["connection_sharing"]["expanded_connections"] != want_connections:
        raise AssertionError("B1.2 packed image expanded connection count differs from graph")
    if sum(core["synapse_words"] for core in manifest["cores"]) != want_connections:
        raise AssertionError("unexpected synapse sharing in unique-weight probe")
    if sum(core["compartments"] for core in manifest["cores"]) != hidden + 10:
        raise AssertionError("lost/duplicated source destination neuron")
    if not 1 <= manifest["logical_core_count"] <= 126:
        raise AssertionError("invalid hardware logical core count")
    if any(row["worst_current_bank_events"] > 4096 for row in manifest["cores"]):
        raise AssertionError("core CURRENT-event bank overflow")
    if any(row["record_bytes"] != 524288 for row in manifest["cores"]):
        raise AssertionError("not all initial DDR images are complete 512 KiB records")
    if manifest["physical_kv260_execution"] != "NOT_TESTED":
        raise AssertionError("synthetic host probe cannot report physical execution")
    roles = result.manifest()["per_core_roles"]
    if roles[-1]["role"] != "readout" or any(row["role"] == "readout" for row in roles[:-1]):
        raise AssertionError("readout placement not separate")
    return {
        "schema": "p06-b1.2-synthetic-structure-summary-v1",
        "model_profile": "SYNTHETIC_NOT_TRAINED",
        "model_shape": [784, hidden, 10],
        "expected_expanded_connections": want_connections,
        "logical_cores": manifest["logical_core_count"],
        "hidden_partition_sizes": [row["compartments"] for row in manifest["cores"][:-1]],
        "readout_compartments": manifest["cores"][-1]["compartments"],
        "total_stored_synapse_words": sum(row["synapse_words"] for row in manifest["cores"]),
        "max_core_synapse_bytes": max(row["logical_synapse_bytes"] for row in manifest["cores"]),
        "max_core_current_events": max(row["worst_current_bank_events"] for row in manifest["cores"]),
        "source_sha256": result.compiled.source_fingerprint,
        "mapped_sha256": result.fingerprint,
        "capacity_audit_sha256": manifest["audit_sha256"],
        "backing_bytes": manifest["backing_bytes"],
        "physical": "NOT_TESTED",
        "official_test": "NOT_ACCESSED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hidden", type=int, default=40,
                        help="synthetic hidden width, 1..1000 (1000 is memory/CPU-intensive)")
    args = parser.parse_args()
    answer = run(args.hidden)
    print(json.dumps(answer, indent=2, sort_keys=True))
    print("P06_B12_SYNTHETIC_STRUCTURAL_PASS=1")


if __name__ == "__main__":
    main()
