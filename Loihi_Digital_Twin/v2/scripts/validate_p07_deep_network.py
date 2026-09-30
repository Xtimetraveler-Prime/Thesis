#!/usr/bin/env python3
"""Validate and report the P07 six-layer mapped workload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2 import (
    CompiledDeployment,
    MappingError,
    MappingOptions,
    NetworkSpec,
    compile_network,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("network", type=Path)
    parser.add_argument("deployment", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--capacity-failure", type=Path, required=True)
    args = parser.parse_args()

    network = NetworkSpec.read_json(args.network)
    compiled = CompiledDeployment.read_json(args.deployment)
    if compiled.source_fingerprint != network.fingerprint:
        raise RuntimeError("P07 deployment source fingerprint mismatch")

    report = compiled.report()
    expected_static = {"total": 10, "local": 6, "remote": 4}
    expected_sharing = {
        "expanded_connections": 28,
        "stored_shared_parameters": 6,
    }
    if report["logical_core_count"] != 3:
        raise RuntimeError("P07 workload must map to exactly three logical cores")
    if report["placement_count"] != 12:
        raise RuntimeError("P07 workload must place exactly twelve neurons")
    if report["ingress_route_count"] != 4:
        raise RuntimeError("P07 workload must expose four external ingress routes")
    if report["static_route_estimate"] != expected_static:
        raise RuntimeError(
            f"P07 static traffic mismatch: {report['static_route_estimate']} != {expected_static}"
        )
    sharing = report["connection_sharing"]
    for key, expected in expected_sharing.items():
        if sharing[key] != expected:
            raise RuntimeError(f"P07 sharing mismatch {key}: {sharing[key]} != {expected}")
    if [core["usage"]["compartments"] for core in report["cores"]] != [4, 4, 4]:
        raise RuntimeError("P07 expected four occupied compartments in every logical core")

    capacity_record: dict[str, object]
    try:
        compile_network(
            network,
            MappingOptions(compartments_per_core=4, max_logical_cores=2),
        )
    except MappingError as error:
        if error.code != "logical_core_capacity" or error.context != {
            "required": 3,
            "limit": 2,
        }:
            raise
        capacity_record = {
            "result": "EXPECTED_REJECTION",
            "code": error.code,
            "message": str(error),
            "context": error.context,
        }
    else:
        raise RuntimeError("P07 two-core capacity probe unexpectedly mapped successfully")

    summary = {
        "schema": "p07-deep-mapped-snn-summary-v1",
        "source_fingerprint": network.fingerprint,
        "deployment_fingerprint": compiled.fingerprint,
        "layers": 6,
        "neurons": 12,
        "input_channels": 4,
        "logical_cores": 3,
        "physical_engines": 1,
        "compartments_per_core_policy": 4,
        "static_route_estimate": report["static_route_estimate"],
        "connection_sharing": sharing,
        "cores": report["cores"],
        "capacity_probe": capacity_record,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    args.capacity_failure.write_text(
        json.dumps(capacity_record, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "P07 deep mapped analysis PASS: "
        f"deployment={compiled.fingerprint} cores=3 layers=6 "
        f"expanded={sharing['expanded_connections']} stored={sharing['stored_shared_parameters']} "
        "two_core_probe=EXPECTED_REJECTION"
    )


if __name__ == "__main__":
    main()
