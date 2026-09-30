#!/usr/bin/env python3
"""Compile the P08 worst-case structural probe and record mapping pressure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2 import MappingOptions, compile_network, export_compiled_fpga_image
from mnist_v2_nxtf import build_network, make_mapping_probe_model, topology_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    model = make_mapping_probe_model()
    network = build_network(model)
    compiled = compile_network(network, MappingOptions(compartments_per_core=1024))
    fpga = export_compiled_fpga_image(compiled)
    report = compiled.report()

    payload = {
        "schema": "p08-candidate-mapping-audit-v1",
        "source_fingerprint": network.fingerprint,
        "deployment_fingerprint": compiled.fingerprint,
        "topology": dict(topology_report()),
        "logical_core_count": report["logical_core_count"],
        "physical_engine_count": fpga.report()["physical_engine_count"],
        "logical_capacity_changed": fpga.report()["logical_capacity_changed"],
        "connection_sharing": report["connection_sharing"],
        "static_route_estimate": report["static_route_estimate"],
        "cores": report["cores"],
    }

    expected_usage = (
        {
            "compartments": 1024,
            "input_axons": 473,
            "output_routes": 940,
            "synapse_bytes": 13388,
            "shared_parameters": 2788,
            "expanded_connections": 25600,
        },
        {
            "compartments": 1024,
            "input_axons": 2099,
            "output_routes": 832,
            "synapse_bytes": 37876,
            "shared_parameters": 7088,
            "expanded_connections": 56000,
        },
        {
            "compartments": 10,
            "input_axons": 20,
            "output_routes": 0,
            "synapse_bytes": 960,
            "shared_parameters": 200,
            "expanded_connections": 200,
        },
    )
    actual_usage = tuple(core["usage"] for core in report["cores"])
    if actual_usage != expected_usage:
        raise RuntimeError(
            "P08 candidate mapping changed unexpectedly:\n"
            f"actual={actual_usage!r}\nexpected={expected_usage!r}"
        )
    if report["static_route_estimate"] != {"total": 1772, "local": 812, "remote": 960}:
        raise RuntimeError(f"unexpected P08 static route profile: {report['static_route_estimate']}")
    sharing = report["connection_sharing"]
    if sharing["expanded_connections"] != 81800 or sharing["stored_shared_parameters"] != 10076:
        raise RuntimeError(f"unexpected P08 sharing profile: {sharing}")
    if report["logical_core_count"] != 3:
        raise RuntimeError("P08 candidate no longer maps to exactly three logical cores")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        "P08 candidate mapping audit PASS: "
        f"cores=3 neurons={payload['topology']['total_spiking_neurons']} "
        f"weights={payload['topology']['trainable_weights']} "
        f"expanded={sharing['expanded_connections']} "
        f"stored={sharing['stored_shared_parameters']} "
        "routes_local=812 routes_remote=960"
    )


if __name__ == "__main__":
    main()
