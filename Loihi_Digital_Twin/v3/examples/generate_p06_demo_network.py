#!/usr/bin/env python3
"""Generate a small three-layer P06 network document for compiler validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from loihi_twin_v2 import (
    CompartmentConfig,
    InputPopulationSpec,
    InputProjectionSpec,
    NetworkSpec,
    PopulationSpec,
    ProjectionConnection,
    ProjectionSpec,
)


def lif() -> CompartmentConfig:
    return CompartmentConfig(current_decay=4096, voltage_decay=4096, threshold=5)


def build_network() -> NetworkSpec:
    return NetworkSpec(
        populations=(
            PopulationSpec("layer0", 2, lif()),
            PopulationSpec("layer1", 2, lif()),
            PopulationSpec("layer2", 2, lif()),
        ),
        projections=(
            ProjectionSpec(
                "layer0_to_layer1",
                "layer0",
                "layer1",
                (
                    ProjectionConnection(0, 0, 6),
                    ProjectionConnection(0, 1, 2),
                    ProjectionConnection(1, 0, 2),
                    ProjectionConnection(1, 1, 6),
                ),
            ),
            ProjectionSpec(
                "layer1_to_layer2",
                "layer1",
                "layer2",
                (
                    ProjectionConnection(0, 0, 6),
                    ProjectionConnection(1, 1, 6),
                ),
            ),
        ),
        input_populations=(InputPopulationSpec("pixels", 2),),
        input_projections=(
            InputProjectionSpec(
                "pixels_to_layer0",
                "pixels",
                "layer0",
                (
                    ProjectionConnection(0, 0, 6),
                    ProjectionConnection(1, 1, 6),
                ),
            ),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    network = build_network()
    network.write_json(args.output)
    print(
        f"P06 demo network generation PASS: source={network.fingerprint} output={args.output}"
    )


if __name__ == "__main__":
    main()
