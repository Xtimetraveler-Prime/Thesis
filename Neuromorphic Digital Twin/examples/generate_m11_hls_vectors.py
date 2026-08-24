#!/usr/bin/env python3
"""Generate the deterministic Python-golden vector corpus used by M11.2."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuromorphic_twin.hls_conformance import (
    M11_2_DEFAULT_RANDOM_CASES,
    M11_2_DEFAULT_SEED,
    build_m11_2_hls_vectors,
    directed_hls_neuron_vectors,
    write_m11_2_cpp_initializer,
)


def _parse_int(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to generated C++ initializer include",
    )
    parser.add_argument(
        "--random-cases",
        type=int,
        default=M11_2_DEFAULT_RANDOM_CASES,
        help="Number of seeded pseudo-random vectors",
    )
    parser.add_argument(
        "--seed",
        type=_parse_int,
        default=M11_2_DEFAULT_SEED,
        help="PRNG seed; decimal or 0x-prefixed hexadecimal",
    )
    args = parser.parse_args()

    directed_count = len(directed_hls_neuron_vectors())
    vectors = build_m11_2_hls_vectors(
        random_cases=args.random_cases,
        seed=args.seed,
    )
    output = write_m11_2_cpp_initializer(
        args.output,
        vectors,
        directed_count=directed_count,
        seed=args.seed,
    )

    print(
        "M11.2 Python golden vectors generated: "
        f"directed={directed_count}, random={args.random_cases}, "
        f"total={len(vectors)}, seed=0x{args.seed:X}"
    )
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
