#!/usr/bin/env python3
"""Compile a P06 network document into one deterministic deployment artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from loihi_twin_v2 import (
    CompiledDeployment,
    MappingOptions,
    NetworkSpec,
    compile_network,
    export_compiled_fpga_image,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("network", type=Path, help="P06 network JSON")
    parser.add_argument("--output", type=Path, required=True, help="compiled deployment JSON")
    parser.add_argument("--report", type=Path, help="optional mapping report JSON")
    parser.add_argument(
        "--compartments-per-core",
        type=int,
        default=1024,
        help="deterministic packing target; does not change logical core capacity",
    )
    parser.add_argument(
        "--fpga-report",
        type=Path,
        help="optional current P05/P06 FPGA-context export report; requires <=3 cores",
    )
    args = parser.parse_args()

    network = NetworkSpec.read_json(args.network)
    compiled = compile_network(
        network,
        MappingOptions(compartments_per_core=args.compartments_per_core),
    )
    compiled.write_json(args.output)

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(compiled.report(), sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.fpga_report is not None:
        fpga = export_compiled_fpga_image(compiled)
        args.fpga_report.parent.mkdir(parents=True, exist_ok=True)
        args.fpga_report.write_text(
            json.dumps(fpga.report(), sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    # Read back the artifact we just wrote. This makes corruption/version errors
    # fail the compiler command instead of surfacing later in a consumer.
    reloaded = CompiledDeployment.read_json(args.output)
    if reloaded.fingerprint != compiled.fingerprint:
        raise RuntimeError("compiled deployment readback fingerprint mismatch")

    print(
        "P06 compile PASS: "
        f"source={network.fingerprint} deployment={compiled.fingerprint} "
        f"logical_cores={len(compiled.logical_deployment.core_configs)}"
    )


if __name__ == "__main__":
    main()
