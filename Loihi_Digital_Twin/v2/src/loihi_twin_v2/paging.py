"""P08 deterministic logical-context paging above the accepted P05 shell.

P05 proved that logical-core identity can be separated from one physical HLS
engine while three full context images remain resident in K26 UltraRAM. P08
extends that separation one level further: architectural state belongs to a
logical core in a backing store, while a bounded number of resident context
slots are only a cache of that state.

The normalized architecture remains the existing :class:`LogicalChip`. The
pager records deterministic load/evict decisions but never rewrites logical IDs
or makes residency visible in normalized neural traces.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chip import LogicalChip
from .core import LogicalCoreConfig
from .hardware_p05 import P05_MAX_RESIDENT_CONTEXTS, P05_PHYSICAL_ENGINE_COUNT
from .packet import SpikePacket
from .trace import ChipTrace, CoreTrace


P08_PAGING_POLICY = "deterministic-round-robin-context-paging-v1"
P08_ROUTE_DELIVERY_POLICY = "host-backing-by-logical-id-v1"


@dataclass(frozen=True, slots=True)
class ContextPageDispatch:
    """One logical-core service decision against the resident context cache."""

    service_index: int
    logical_core_id: int
    context_slot: int
    page_hit: bool
    evicted_logical_core_id: int | None


@dataclass(frozen=True, slots=True)
class ContextPagingSchedule:
    """Implementation-only page schedule for one algorithmic timestep."""

    algorithmic_timestep: int
    logical_core_ids: tuple[int, ...]
    resident_context_count: int
    service_order: tuple[int, ...]
    residency_before: tuple[int | None, ...]
    dispatches: tuple[ContextPageDispatch, ...]
    residency_after: tuple[int | None, ...]
    policy: str = P08_PAGING_POLICY

    @property
    def page_load_count(self) -> int:
        return sum(not dispatch.page_hit for dispatch in self.dispatches)

    @property
    def page_hit_count(self) -> int:
        return sum(dispatch.page_hit for dispatch in self.dispatches)

    @property
    def eviction_count(self) -> int:
        return sum(dispatch.evicted_logical_core_id is not None for dispatch in self.dispatches)

    def as_dict(self) -> dict[str, object]:
        return {
            "algorithmic_timestep": self.algorithmic_timestep,
            "logical_core_ids": list(self.logical_core_ids),
            "logical_core_count": len(self.logical_core_ids),
            "resident_context_count": self.resident_context_count,
            "service_order": list(self.service_order),
            "residency_before": list(self.residency_before),
            "residency_after": list(self.residency_after),
            "page_load_count": self.page_load_count,
            "page_hit_count": self.page_hit_count,
            "eviction_count": self.eviction_count,
            "policy": self.policy,
            "dispatches": [
                {
                    "service_index": dispatch.service_index,
                    "logical_core_id": dispatch.logical_core_id,
                    "context_slot": dispatch.context_slot,
                    "page_hit": dispatch.page_hit,
                    "evicted_logical_core_id": dispatch.evicted_logical_core_id,
                }
                for dispatch in self.dispatches
            ],
        }


@dataclass(frozen=True, slots=True)
class ContextPagingReport:
    """Stable logical/backing/resident/engine resource boundary for P08."""

    logical_core_ids: tuple[int, ...]
    resident_context_count: int
    physical_engine_count: int = P05_PHYSICAL_ENGINE_COUNT
    paging_policy: str = P08_PAGING_POLICY
    route_delivery_policy: str = P08_ROUTE_DELIVERY_POLICY

    @property
    def logical_core_count(self) -> int:
        return len(self.logical_core_ids)

    @property
    def requires_paging(self) -> bool:
        return self.logical_core_count > self.resident_context_count

    def as_dict(self) -> dict[str, object]:
        return {
            "logical_core_ids": list(self.logical_core_ids),
            "logical_core_count": self.logical_core_count,
            "backing_context_count": self.logical_core_count,
            "resident_context_count": self.resident_context_count,
            "physical_engine_count": self.physical_engine_count,
            "requires_paging": self.requires_paging,
            "paging_policy": self.paging_policy,
            "route_delivery_policy": self.route_delivery_policy,
            "logical_capacity_changed": False,
        }


class DeterministicContextPager:
    """Stateful deterministic cache mapping logical cores to resident slots.

    The default initial residency is the lowest logical IDs that fit. A miss
    replaces one resident slot using a round-robin victim pointer. The policy is
    intentionally simple and fully observable; correctness must never depend on
    which legal page schedule is chosen.
    """

    def __init__(
        self,
        logical_core_ids: tuple[int, ...],
        resident_context_count: int = P05_MAX_RESIDENT_CONTEXTS,
    ) -> None:
        if not logical_core_ids:
            raise ValueError("context paging requires at least one logical core")
        if len(logical_core_ids) != len(set(logical_core_ids)):
            raise ValueError("logical core IDs must be unique")
        if resident_context_count <= 0:
            raise ValueError("resident_context_count must be positive")
        if resident_context_count > P05_MAX_RESIDENT_CONTEXTS:
            raise ValueError(
                f"P08 paging cannot exceed the accepted P05 resident-slot count "
                f"({P05_MAX_RESIDENT_CONTEXTS})"
            )
        if resident_context_count > len(logical_core_ids):
            resident_context_count = len(logical_core_ids)

        self.logical_core_ids = tuple(sorted(logical_core_ids))
        self.resident_context_count = resident_context_count
        self._slots: list[int | None] = [None] * resident_context_count
        self._victim_cursor = 0
        self.reset()

    @property
    def residency(self) -> tuple[int | None, ...]:
        return tuple(self._slots)

    def reset(self, resident_core_ids: tuple[int, ...] | None = None) -> None:
        if resident_core_ids is None:
            resident_core_ids = self.logical_core_ids[: self.resident_context_count]
        if len(resident_core_ids) > self.resident_context_count:
            raise ValueError("initial residency exceeds resident context count")
        if len(resident_core_ids) != len(set(resident_core_ids)):
            raise ValueError("initial resident logical IDs must be unique")
        unknown = set(resident_core_ids) - set(self.logical_core_ids)
        if unknown:
            raise ValueError(f"initial residency contains unknown logical cores {sorted(unknown)}")

        self._slots = [None] * self.resident_context_count
        for slot, logical_core_id in enumerate(resident_core_ids):
            self._slots[slot] = logical_core_id
        self._victim_cursor = 0

    def plan(
        self,
        algorithmic_timestep: int,
        service_order: tuple[int, ...] | None = None,
    ) -> ContextPagingSchedule:
        order = self.logical_core_ids if service_order is None else tuple(service_order)
        if tuple(sorted(order)) != self.logical_core_ids or len(order) != len(self.logical_core_ids):
            raise ValueError("service_order must be a permutation of configured logical core IDs")

        before = self.residency
        dispatches: list[ContextPageDispatch] = []
        for service_index, logical_core_id in enumerate(order):
            if logical_core_id in self._slots:
                slot = self._slots.index(logical_core_id)
                dispatches.append(
                    ContextPageDispatch(
                        service_index=service_index,
                        logical_core_id=logical_core_id,
                        context_slot=slot,
                        page_hit=True,
                        evicted_logical_core_id=None,
                    )
                )
                continue

            slot = self._victim_cursor
            evicted = self._slots[slot]
            self._slots[slot] = logical_core_id
            self._victim_cursor = (self._victim_cursor + 1) % self.resident_context_count
            dispatches.append(
                ContextPageDispatch(
                    service_index=service_index,
                    logical_core_id=logical_core_id,
                    context_slot=slot,
                    page_hit=False,
                    evicted_logical_core_id=evicted,
                )
            )

        return ContextPagingSchedule(
            algorithmic_timestep=algorithmic_timestep,
            logical_core_ids=self.logical_core_ids,
            resident_context_count=self.resident_context_count,
            service_order=order,
            residency_before=before,
            dispatches=tuple(dispatches),
            residency_after=self.residency,
        )


class PagedVirtualizedLogicalChip:
    """Logical-chip execution with an explicit three-slot paging schedule.

    ``LogicalChip`` remains the authoritative owner of per-core state and queued
    events; that object is the software backing store. The pager records which
    logical core would be loaded into which P05 resident slot before each one-
    engine dispatch. Packets are still delivered by logical destination ID, so a
    destination need not be resident when its event is created.
    """

    def __init__(
        self,
        core_configs: tuple[LogicalCoreConfig, ...],
        *,
        resident_context_count: int = P05_MAX_RESIDENT_CONTEXTS,
    ) -> None:
        self.logical_chip = LogicalChip(core_configs)
        logical_core_ids = tuple(sorted(self.logical_chip.cores))
        self.pager = DeterministicContextPager(
            logical_core_ids,
            resident_context_count=resident_context_count,
        )
        self.report = ContextPagingReport(
            logical_core_ids=logical_core_ids,
            resident_context_count=self.pager.resident_context_count,
        )
        self.last_page_schedule: ContextPagingSchedule | None = None

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
    ) -> tuple[CoreTrace, ...]:
        schedule = self.pager.plan(
            self.current_timestep,
            service_order=service_order,
        )
        self.last_page_schedule = schedule
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
    ) -> ChipTrace:
        self.evaluate(external_packets=external_packets, service_order=service_order)
        self.drain_packets(reverse=reverse_packet_drain)
        return self.advance()
