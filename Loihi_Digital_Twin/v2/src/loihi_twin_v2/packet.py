"""Normalized logical packet boundary for inter-core spike traffic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PacketClass(str, Enum):
    SPIKE = "spike"


@dataclass(frozen=True, slots=True)
class SpikePacket:
    """A logical destination-core/destination-axon spike event.

    ``target_timestep`` is the architectural update on which the destination
    consumes the expanded synaptic contribution. A packet emitted while
    evaluating timestep ``t`` therefore targets ``t + 1``.
    """

    target_timestep: int
    destination_core: int
    destination_axon: int
    source_core: int | None = None
    source_compartment: int | None = None
    source_timestep: int | None = None
    packet_class: PacketClass = PacketClass.SPIKE

    def __post_init__(self) -> None:
        if self.target_timestep < 0:
            raise ValueError("target_timestep cannot be negative")
        if self.destination_core < 0:
            raise ValueError("destination_core cannot be negative")
        if self.destination_axon < 0:
            raise ValueError("destination_axon cannot be negative")
        for name, value in (
            ("source_core", self.source_core),
            ("source_compartment", self.source_compartment),
            ("source_timestep", self.source_timestep),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")

    @property
    def logical_key(self) -> tuple[int, int, int, int, int, int, str]:
        return (
            self.target_timestep,
            self.destination_core,
            self.destination_axon,
            -1 if self.source_core is None else self.source_core,
            -1 if self.source_compartment is None else self.source_compartment,
            -1 if self.source_timestep is None else self.source_timestep,
            self.packet_class.value,
        )
