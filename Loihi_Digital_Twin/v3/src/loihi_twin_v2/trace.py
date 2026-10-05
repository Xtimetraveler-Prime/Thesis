"""Normalized architectural traces for deterministic differential validation."""

from __future__ import annotations

from dataclasses import dataclass

from .compartment import CompartmentState
from .packet import SpikePacket


@dataclass(frozen=True, slots=True)
class AxonExpansionTrace:
    axon_id: int
    template_id: int
    expanded_count: int


@dataclass(frozen=True, slots=True)
class SynapticContributionTrace:
    source_axon: int
    template_id: int
    target_compartment: int
    weight: int


@dataclass(frozen=True, slots=True)
class CompartmentSnapshot:
    compartment_id: int
    state: CompartmentState


@dataclass(frozen=True, slots=True)
class CoreTrace:
    algorithmic_timestep: int
    logical_core_id: int
    phase: str
    packet_in: tuple[SpikePacket, ...]
    axon_expansions: tuple[AxonExpansionTrace, ...]
    synaptic_contributions: tuple[SynapticContributionTrace, ...]
    compartment_state_before: tuple[CompartmentSnapshot, ...]
    compartment_state_after: tuple[CompartmentSnapshot, ...]
    spikes_out: tuple[int, ...]
    packets_out: tuple[SpikePacket, ...]
    local_done: bool

    def normalized(self) -> tuple:
        return (
            self.algorithmic_timestep,
            self.logical_core_id,
            tuple(packet.logical_key for packet in self.packet_in),
            tuple((x.axon_id, x.template_id, x.expanded_count) for x in self.axon_expansions),
            tuple(
                (x.source_axon, x.template_id, x.target_compartment, x.weight)
                for x in self.synaptic_contributions
            ),
            tuple((x.compartment_id, x.state) for x in self.compartment_state_before),
            tuple((x.compartment_id, x.state) for x in self.compartment_state_after),
            self.spikes_out,
            tuple(packet.logical_key for packet in self.packets_out),
            self.local_done,
        )


@dataclass(frozen=True, slots=True)
class BarrierSnapshot:
    timestep: int
    completed_cores: tuple[int, ...]
    in_flight_packets: int
    can_advance: bool


@dataclass(frozen=True, slots=True)
class ChipTrace:
    algorithmic_timestep: int
    cores: tuple[CoreTrace, ...]
    barrier: BarrierSnapshot
    packet_traffic: tuple[tuple[int, int, int, str, int], ...]

    def normalized(self) -> tuple:
        return (
            self.algorithmic_timestep,
            tuple(core.normalized() for core in self.cores),
            (
                self.barrier.timestep,
                self.barrier.completed_cores,
                self.barrier.in_flight_packets,
                self.barrier.can_advance,
            ),
            self.packet_traffic,
        )
