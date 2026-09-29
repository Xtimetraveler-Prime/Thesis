"""Logical-core virtualization policy for the v2 golden model.

The objects in this module deliberately keep physical execution-engine identity
out of the normalized architectural trace.  They model only the implementation
choice required by P05: a smaller set of physical engines services a larger set
of independently retained logical-core contexts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chip import LogicalChip
from .core import LogicalCoreConfig
from .packet import SpikePacket
from .trace import ChipTrace, CoreTrace


@dataclass(frozen=True, slots=True)
class VirtualDispatch:
    """One logical-core service assignment inside a physical scheduling wave."""

    wave: int
    physical_engine_id: int
    logical_core_id: int


@dataclass(frozen=True, slots=True)
class VirtualizationSchedule:
    """Implementation-only service schedule for one algorithmic timestep."""

    algorithmic_timestep: int
    logical_core_ids: tuple[int, ...]
    physical_engine_count: int
    service_order: tuple[int, ...]
    dispatches: tuple[VirtualDispatch, ...]

    @property
    def wave_count(self) -> int:
        if not self.dispatches:
            return 0
        return 1 + max(dispatch.wave for dispatch in self.dispatches)

    def as_dict(self) -> dict[str, object]:
        return {
            "algorithmic_timestep": self.algorithmic_timestep,
            "logical_core_ids": list(self.logical_core_ids),
            "logical_core_count": len(self.logical_core_ids),
            "physical_engine_count": self.physical_engine_count,
            "wave_count": self.wave_count,
            "service_order": list(self.service_order),
            "dispatches": [
                {
                    "wave": dispatch.wave,
                    "physical_engine_id": dispatch.physical_engine_id,
                    "logical_core_id": dispatch.logical_core_id,
                }
                for dispatch in self.dispatches
            ],
        }


@dataclass(frozen=True, slots=True)
class VirtualizationReport:
    """Stable logical-vs-physical resource report for a virtualized chip."""

    logical_core_ids: tuple[int, ...]
    physical_engine_count: int
    scheduler: str = "deterministic-wave-round-robin-v1"

    @property
    def logical_core_count(self) -> int:
        return len(self.logical_core_ids)

    @property
    def virtualization_ratio(self) -> float:
        return self.logical_core_count / self.physical_engine_count

    def as_dict(self) -> dict[str, object]:
        return {
            "logical_core_ids": list(self.logical_core_ids),
            "logical_core_count": self.logical_core_count,
            "physical_engine_count": self.physical_engine_count,
            "virtualization_ratio": self.virtualization_ratio,
            "scheduler": self.scheduler,
        }


class DeterministicCoreScheduler:
    """Map logical cores onto a fixed number of physical execution engines.

    ``service_order`` controls the legal logical-core ordering for one timestep.
    Engine assignment is deterministic round-robin within fixed-size scheduling
    waves.  The scheduler never changes logical core IDs and never owns logical
    architectural state.
    """

    def __init__(
        self,
        logical_core_ids: tuple[int, ...],
        physical_engine_count: int,
    ) -> None:
        if not logical_core_ids:
            raise ValueError("virtualized execution requires at least one logical core")
        if len(logical_core_ids) != len(set(logical_core_ids)):
            raise ValueError("logical core IDs must be unique")
        if physical_engine_count <= 0:
            raise ValueError("physical_engine_count must be positive")
        if physical_engine_count > len(logical_core_ids):
            raise ValueError(
                "physical_engine_count cannot exceed configured logical core count"
            )
        self.logical_core_ids = tuple(sorted(logical_core_ids))
        self.physical_engine_count = physical_engine_count

    def plan(
        self,
        algorithmic_timestep: int,
        service_order: tuple[int, ...] | None = None,
        physical_engine_order: tuple[int, ...] | None = None,
    ) -> VirtualizationSchedule:
        order = self.logical_core_ids if service_order is None else service_order
        if tuple(sorted(order)) != self.logical_core_ids or len(order) != len(self.logical_core_ids):
            raise ValueError("service_order must be a permutation of configured logical core IDs")

        engines = (
            tuple(range(self.physical_engine_count))
            if physical_engine_order is None
            else physical_engine_order
        )
        if tuple(sorted(engines)) != tuple(range(self.physical_engine_count)):
            raise ValueError(
                "physical_engine_order must be a permutation of physical engine IDs"
            )

        dispatches = tuple(
            VirtualDispatch(
                wave=slot // self.physical_engine_count,
                physical_engine_id=engines[slot % self.physical_engine_count],
                logical_core_id=logical_core_id,
            )
            for slot, logical_core_id in enumerate(order)
        )
        return VirtualizationSchedule(
            algorithmic_timestep=algorithmic_timestep,
            logical_core_ids=self.logical_core_ids,
            physical_engine_count=self.physical_engine_count,
            service_order=tuple(order),
            dispatches=dispatches,
        )


class VirtualizedLogicalChip:
    """LogicalChip wrapper that makes physical engine scheduling explicit.

    Architectural state remains owned by the wrapped ``LogicalChip`` and its
    ``LogicalCore`` instances.  Physical scheduling therefore cannot alias one
    logical core's state with another.  Only the evaluation order changes; the
    normalized ``ChipTrace`` remains the same abstraction used before P05.
    """

    def __init__(
        self,
        core_configs: tuple[LogicalCoreConfig, ...],
        *,
        physical_engine_count: int,
    ) -> None:
        self.logical_chip = LogicalChip(core_configs)
        logical_core_ids = tuple(sorted(self.logical_chip.cores))
        self.scheduler = DeterministicCoreScheduler(
            logical_core_ids,
            physical_engine_count,
        )
        self.report = VirtualizationReport(
            logical_core_ids=logical_core_ids,
            physical_engine_count=physical_engine_count,
        )
        self.last_schedule: VirtualizationSchedule | None = None

    @property
    def cores(self):
        return self.logical_chip.cores

    @property
    def router(self):
        return self.logical_chip.router

    @property
    def barrier(self):
        return self.logical_chip.barrier

    @property
    def current_timestep(self) -> int:
        return self.logical_chip.current_timestep

    @property
    def can_advance(self) -> bool:
        return self.logical_chip.can_advance

    def inject_external(self, packet: SpikePacket) -> None:
        self.logical_chip.inject_external(packet)

    def evaluate(
        self,
        external_packets: tuple[SpikePacket, ...] = (),
        service_order: tuple[int, ...] | None = None,
        *,
        physical_engine_order: tuple[int, ...] | None = None,
    ) -> tuple[CoreTrace, ...]:
        schedule = self.scheduler.plan(
            self.current_timestep,
            service_order=service_order,
            physical_engine_order=physical_engine_order,
        )
        self.last_schedule = schedule
        return self.logical_chip.evaluate(
            external_packets=external_packets,
            service_order=schedule.service_order,
        )

    def drain_packets(
        self,
        *,
        reverse: bool = False,
        limit: int | None = None,
    ) -> tuple[SpikePacket, ...]:
        return self.logical_chip.drain_packets(reverse=reverse, limit=limit)

    def advance(self) -> ChipTrace:
        return self.logical_chip.advance()

    def step(
        self,
        external_packets: tuple[SpikePacket, ...] = (),
        service_order: tuple[int, ...] | None = None,
        *,
        reverse_packet_drain: bool = False,
        physical_engine_order: tuple[int, ...] | None = None,
    ) -> ChipTrace:
        self.evaluate(
            external_packets=external_packets,
            service_order=service_order,
            physical_engine_order=physical_engine_order,
        )
        self.drain_packets(reverse=reverse_packet_drain)
        return self.advance()
