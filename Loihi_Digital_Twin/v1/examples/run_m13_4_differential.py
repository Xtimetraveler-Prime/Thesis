#!/usr/bin/env python3
"""Execute the M13.4 directed differential under frozen M13.3 normalization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuromorphic_twin.comparison.m13_differential import (
    M13_4_DIFFERENTIAL_SCHEMA,
    write_m13_4_differential_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalyst-cuba-log", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = write_m13_4_differential_bundle(
        args.output,
        catalyst_cuba_log=args.catalyst_cuba_log,
    )
    report = json.loads((args.output / "directed-report.json").read_text(encoding="utf-8"))
    if report["schema"] != M13_4_DIFFERENTIAL_SCHEMA:
        raise RuntimeError("unexpected M13.4 differential schema")
    summary = report["summary"]
    print(
        "M13.4 directed differential PASS: "
        f"probes={report['probe_count']} "
        f"agreement={summary['agreement']} "
        f"architectural_difference={summary['architectural_difference']} "
        f"partial_scope={summary['partial_scope']} "
        f"non_comparable={summary['non_comparable']} "
        f"class_A_or_B={summary['class_A_or_B']}"
    )
    print(f"M13.4 differential manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
