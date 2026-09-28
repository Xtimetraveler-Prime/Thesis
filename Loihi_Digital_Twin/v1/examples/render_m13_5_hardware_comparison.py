#!/usr/bin/env python3
"""Render a fairness-preserving M13.5 comparison from a routed Catalyst result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.m13_hardware_comparison import (
    build_hardware_comparison,
    load_catalyst_result,
    render_hardware_comparison_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalyst-result", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    comparison = build_hardware_comparison(load_catalyst_result(args.catalyst_result))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_hardware_comparison_markdown(comparison), encoding="utf-8")
    print(
        "M13.5 routed comparison PASS: "
        f"project_part={comparison['targets']['project']} "
        f"catalyst_part={comparison['targets']['catalyst']} "
        f"latency=withheld power=withheld physical_catalyst=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
