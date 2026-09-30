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
            "input_axons": 514,
            "output_routes": 1069,
            "synapse_bytes": 13680,
            "shared_parameters": 2800,
            "expanded_connections": 25600,
        },
        {
            "compartments": 1024,
            "input_axons": 1134,
            "output_routes": 925,
            "synapse_bytes": 19152,
            "shared_parameters": 3473,
            "expanded_connections": 26240,
        },
        {
            "compartments": 424,
            "input_axons": 1661,
            "output_routes": 414,
            "synapse_bytes": 12372,
            "shared_parameters": 1286,
            "expanded_connections": 16850,
        },
    )
    actual_usage = tuple(core["usage"] for core in report["cores"])
    if actual_usage != expected_usage:
        raise RuntimeError(
            "P08 candidate mapping changed unexpectedly:\n"
            f"actual={actual_usage!r}\nexpected={expected_usage!r}"
        )
    if report["static_route_estimate"] != {"total": 2408, "local": 414, "remote": 1994}:
        raise RuntimeError(f"unexpected P08 static route profile: {report['static_route_estimate']}")
    sharing = report["connection_sharing"]
    if sharing["expanded_connections"] != 68690 or sharing["stored_shared_parameters"] != 7559:
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
        f"routes_local=414 routes_remote=1994"
    )


if __name__ == "__main__":
    main()
