#!/usr/bin/env python3
"""Parse Catalyst K26 Vivado implementation reports into M13.5 JSON evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.m13_hardware_audit import build_catalyst_hardware_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--utilization", type=Path, required=True)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--vivado-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = build_catalyst_hardware_result(
        vivado_version=args.vivado_version,
        utilization_text=args.utilization.read_text(encoding="utf-8", errors="replace"),
        timing_text=args.timing.read_text(encoding="utf-8", errors="replace"),
        source_reports={
            "utilization": str(args.utilization),
            "timing": str(args.timing),
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "M13.5 Catalyst routed report PASS: "
        f"part={result['target_part']} vivado={result['vivado']} "
        f"WNS={result['timing']['wns_ns']:.3f}ns WHS={result['timing']['whs_ns']:.3f}ns "
        f"timing_closed={int(result['timing_closed'])}"
    )
    print(f"M13.5 result: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
