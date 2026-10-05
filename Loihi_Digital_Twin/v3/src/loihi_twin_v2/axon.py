"""Destination-side input axons and source-side explicit fanout routes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputAxonBinding:
    axon_id: int
    template_id: int
    target_offset: int = 0

    def __post_init__(self) -> None:
        if self.axon_id < 0:
            raise ValueError("axon_id cannot be negative")
        if self.template_id < 0:
            raise ValueError("template_id cannot be negative")
        if self.target_offset < 0:
            raise ValueError("target_offset cannot be negative")


@dataclass(frozen=True, slots=True)
class OutputRoute:
    destination_core: int
    destination_axon: int

    def __post_init__(self) -> None:
        if self.destination_core < 0:
            raise ValueError("destination_core cannot be negative")
        if self.destination_axon < 0:
            raise ValueError("destination_axon cannot be negative")


@dataclass(frozen=True, slots=True)
class OutputRouteEntry:
    source_compartment: int
    routes: tuple[OutputRoute, ...]

    def __post_init__(self) -> None:
        if self.source_compartment < 0:
            raise ValueError("source_compartment cannot be negative")
