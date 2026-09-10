#!/usr/bin/env python3
"""Validate the frozen M13.4 probe catalog and optionally preserve native reuse evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.comparison.m13_directed_probes import (
    M13NormalizationNotFrozen,
    load_probe_catalog,
    pre_normalization_reuse_names,
    require_frozen_m13_3,
    run_pre_normalization_reuse,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--run-pre-normalization-reuse", type=Path)
    parser.add_argument(
        "--require-normalization",
        action="store_true",
        help="Fail unless the frozen M13.3 normalization specification exists.",
    )
    args = parser.parse_args()

    catalog = load_probe_catalog(args.catalog)
    names = pre_normalization_reuse_names(catalog)
    print(
        "M13.4 probe catalog PASS: "
        f"probes={len(catalog['probes'])} "
        f"directed_reuse={len(names['directed_cases'])} "
        f"weight_reuse={len(names['weight_cases'])} "
        f"normalization={catalog['normalization_gate']['state']}"
    )

    if args.require_normalization:
        try:
            spec = require_frozen_m13_3()
        except M13NormalizationNotFrozen as exc:
            print(f"M13.4 normalized comparison BLOCKED: {exc}")
            return 4
        print(f"M13.4 normalization prerequisite PASS: schema={spec['schema']}")

    if args.run_pre_normalization_reuse is not None:
        manifest = run_pre_normalization_reuse(
            args.run_pre_normalization_reuse,
            catalog_path=args.catalog,
        )
        print(f"M13.4 pre-normalization reuse PASS: manifest={manifest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
