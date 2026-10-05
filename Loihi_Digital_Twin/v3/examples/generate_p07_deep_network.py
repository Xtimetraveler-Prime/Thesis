#!/usr/bin/env python3
"""Generate the deterministic six-layer P07 feed-forward validation network."""

from __future__ import annotations

import argparse
from pathlib import Path

from loihi_twin_v2.workload_p07 import build_p07_deep_network


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    network = build_p07_deep_network()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    network.write_json(args.output)
    print(
        "P07 deep network generation PASS: "
        f"source={network.fingerprint} layers=6 neurons=12 inputs=4 output={args.output}"
    )


if __name__ == "__main__":
    main()
