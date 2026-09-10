#!/usr/bin/env python3
"""Validate and materialize the frozen M13.3 normalization interface."""

from __future__ import annotations

import argparse

from neuromorphic_twin.comparison.m13_normalization import (
    build_small_translation_corpus,
    load_normalization_spec,
    write_translation_smoke_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        help="Write the small translation-smoke evidence bundle to this directory.",
    )
    parser.add_argument(
        "--execute-catalyst-cpu",
        action="store_true",
        help=(
            "Execute Catalyst CPU native plans. The pinned Catalyst sdk directory "
            "must already be on PYTHONPATH."
        ),
    )
    args = parser.parse_args()

    spec = load_normalization_spec()
    corpus = build_small_translation_corpus()
    print(
        "M13.3 normalization spec PASS: "
        f"schema={spec['schema']} status={spec['status']} "
        f"version={spec['version']} cases={len(corpus)}"
    )

    if args.output:
        manifest = write_translation_smoke_bundle(
            args.output,
            execute_catalyst_cpu=args.execute_catalyst_cpu,
        )
        print(f"M13.3 translation smoke PASS: manifest={manifest}")
    elif args.execute_catalyst_cpu:
        parser.error("--execute-catalyst-cpu requires --output")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
