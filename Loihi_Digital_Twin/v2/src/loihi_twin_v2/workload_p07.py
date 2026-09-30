"""Canonical P07 deeper mapped feed-forward SNN workload."""

from __future__ import annotations

from .compartment import CompartmentConfig
from .compiler import (
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


def build_p07_deep_network() -> NetworkSpec:
    """Return the six-layer, twelve-neuron P07 validation network.

    With ``compartments_per_core=4`` the deterministic P06 compiler packs two
    consecutive two-neuron layers into each of three logical cores. The five
    feed-forward stage transitions therefore alternate local and remote routes.
    """

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
