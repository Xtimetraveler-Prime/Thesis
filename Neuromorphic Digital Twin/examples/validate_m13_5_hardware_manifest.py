#!/usr/bin/env python3
"""Validate the frozen M13.5 hardware boundary and optional Catalyst checkout."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.m13_hardware_audit import (
    load_hardware_manifest,
    verify_catalyst_k26_checkout,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalyst-checkout", type=Path)
    args = parser.parse_args()

    manifest = load_hardware_manifest()
    catalyst = manifest["catalyst_k26"]
    print(
        "M13.5 hardware manifest PASS: "
        f"catalyst={manifest['baseline']['catalyst_commit'][:12]} "
        f"part={catalyst['upstream_target_part']} "
        f"cores={catalyst['configured_cores']} neurons={catalyst['total_configured_neurons']} "
        f"clock_mhz={manifest['reproduction_environment']['clock_target_hz'] // 1_000_000} "
        "physical_programming_source_supported=0"
    )

    if args.catalyst_checkout is not None:
        result = verify_catalyst_k26_checkout(args.catalyst_checkout)
        print(
            "M13.5 Catalyst K26 checkout PASS: "
            f"commit={result['commit'][:12]} files={len(result['source_directory_files'])} "
            f"part={result['upstream_target_part']} clock_ns={result['clock_period_ns']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
