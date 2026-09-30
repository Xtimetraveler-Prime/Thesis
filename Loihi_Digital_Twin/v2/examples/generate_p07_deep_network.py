#!/usr/bin/env python3
"""Generate the deterministic six-layer P07 feed-forward validation network."""

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


def _dense_2x2(weight: int = 6) -> tuple[ProjectionConnection, ...]:
    return tuple(
        ProjectionConnection(source_index=source, destination_index=destination, weight=weight)
        for source in range(2)
        for destination in range(2)
    )


def build_network() -> NetworkSpec:
    neuron = CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=5,
    )
    populations = tuple(
        PopulationSpec(name=f"layer{index}", size=2, compartment=neuron)
        for index in range(6)
    )
    projections = tuple(
        ProjectionSpec(
            name=f"layer{index}_to_layer{index + 1}",
            source_population=f"layer{index}",
            destination_population=f"layer{index + 1}",
            connections=_dense_2x2(),
        )
        for index in range(5)
    )
    input_connections = tuple(
        ProjectionConnection(source_index=source, destination_index=destination, weight=6)
        for source in range(4)
        for destination in range(2)
    )
    return NetworkSpec(
        populations=populations,
        projections=projections,
        input_populations=(InputPopulationSpec(name="pixels", size=4),),
        input_projections=(
            InputProjectionSpec(
                name="pixels_to_layer0",
                source_input="pixels",
                destination_population="layer0",
                connections=input_connections,
            ),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    network = build_network()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    network.write_json(args.output)
    print(
        "P07 deep network generation PASS: "
        f"source={network.fingerprint} layers=6 neurons=12 inputs=4 output={args.output}"
    )


if __name__ == "__main__":
    main()
