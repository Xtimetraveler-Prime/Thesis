"""Logical drain/advance barrier independent of physical scheduling order."""

from __future__ import annotations

from dataclasses import dataclass, field

from .trace import BarrierSnapshot


@dataclass(slots=True)
class BarrierCoordinator:
    timestep: int = -1
    participants: frozenset[int] = frozenset()
    completed: set[int] = field(default_factory=set)
    in_flight_packets: int = 0
    active: bool = False

    def begin(self, timestep: int, core_ids: tuple[int, ...]) -> None:
        if self.active:
            raise RuntimeError("barrier is already active")
        self.timestep = timestep
        self.participants = frozenset(core_ids)
        self.completed.clear()
        self.in_flight_packets = 0
        self.active = True

    def mark_core_complete(self, core_id: int) -> None:
        if not self.active:
            raise RuntimeError("barrier is not active")
        if core_id not in self.participants:
            raise ValueError(f"core {core_id} is not a barrier participant")
        self.completed.add(core_id)

    def packet_enqueued(self, count: int = 1) -> None:
        if count < 0:
            raise ValueError("count cannot be negative")
        self.in_flight_packets += count

    def packet_delivered(self, count: int = 1) -> None:
        if count < 0 or count > self.in_flight_packets:
            raise ValueError("invalid delivered packet count")
        self.in_flight_packets -= count

    @property
    def can_advance(self) -> bool:
        return (
            self.active
            and self.completed == set(self.participants)
            and self.in_flight_packets == 0
        )

    def snapshot(self) -> BarrierSnapshot:
        return BarrierSnapshot(
            timestep=self.timestep,
            completed_cores=tuple(sorted(self.completed)),
            in_flight_packets=self.in_flight_packets,
            can_advance=self.can_advance,
        )

    def advance(self) -> int:
        if not self.can_advance:
            raise RuntimeError("cannot advance before all cores complete and packets drain")
        completed_timestep = self.timestep
        self.active = False
        self.participants = frozenset()
        self.completed.clear()
        return completed_timestep + 1
