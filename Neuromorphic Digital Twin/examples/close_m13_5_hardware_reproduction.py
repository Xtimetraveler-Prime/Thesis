#!/usr/bin/env python3
"""Validate preserved M13.5 Vivado evidence and promote a tracked closure record."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.m13_hardware_closure import write_hardware_closure


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path("build/m13_5/catalyst-k26-vivado"),
        help="Preserved output directory from run_m13_5_catalyst_k26_vivado.sh",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("references/m13_5_closure.json"),
        help="Tracked compact closure artifact",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("build/m13_5/m13_5_closure_summary.md"),
        help="Human-readable closure summary (kept in ignored build/ by default)",
    )
    args = parser.parse_args()

    closure = write_hardware_closure(
        args.evidence_dir,
        output_json=args.output_json,
        output_markdown=args.output_md,
    )

    timing = closure["routed_timing"]["catalyst"]
    catalyst_resources = {
        row["resource"]: row["catalyst"]
        for row in closure["resources"]
    }

    def used(name: str) -> str:
        value = catalyst_resources.get(name)
        if not isinstance(value, dict) or value.get("used") is None:
            return "n/a"
        observed = value["used"]
        return f"{observed:g}" if isinstance(observed, float) else str(observed)

    print(
        "M13.5.3 evidence promotion PASS: "
        f"boundary={closure['strongest_catalyst_boundary'].replace(' ', '_')} "
        f"WNS={timing['wns_ns']:.3f}ns WHS={timing['whs_ns']:.3f}ns "
        f"LUTs={used('CLB LUTs')} regs={used('CLB registers')} "
        f"BRAM={used('Block RAM tiles')} DSPs={used('DSPs')} URAM={used('URAM')} "
        "latency=withheld power=withheld physical_catalyst=0"
    )
    print(f"M13.5 tracked closure artifact: {args.output_json}")
    print(f"M13.5 closure summary: {args.output_md}")
    print(f"M13.5 evidence manifest SHA256: {closure['evidence']['evidence_manifest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
