"""FPGA-v1 recurrent-route storage and double-buffered queue reference.

M11.5.4 consumes the already-frozen M09/M10 routing semantics and the finite
M11.5.1 physical capacities.  This module is deliberately hardware-oriented:
route storage is CSR by source neuron and runtime recurrence is represented by
two finite event banks with an explicit bank selector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .fpga_core_capacity import FPGA_CORE_CAPACITY_V1, FpgaCoreCapacity
from .model import SpikeRoute


@dataclass(frozen=True, slots=True)
class FrozenRouteStorage:
    """CSR route image grouped by ascending source neuron."""

    neuron_count: int
    row_pointers: tuple[int, ...]
    target_axons: tuple[int, ...]

    def __post_init__(self) -> None:
        _require_count(
            "neuron_count",
            self.neuron_count,
            1,
            FPGA_CORE_CAPACITY_V1.max_neurons,
        )
        if len(self.row_pointers) != self.neuron_count + 1:
            raise ValueError("row_pointers length must equal neuron_count + 1")
        if self.row_pointers[0] != 0:
            raise ValueError("first route row pointer must be zero")
        if len(self.target_axons) > FPGA_CORE_CAPACITY_V1.max_routes:
            raise ValueError("route count exceeds M11.5 physical capacity")
        if any(
            isinstance(pointer, bool) or not isinstance(pointer, int)
            for pointer in self.row_pointers
        ):
            raise TypeError("route row pointers must be ints")
        if any(
            pointer < 0 or pointer > len(self.target_axons)
            for pointer in self.row_pointers
        ):
            raise ValueError("route row pointer is outside route-target table")
        if any(
            left > right
            for left, right in zip(self.row_pointers, self.row_pointers[1:])
        ):
            raise ValueError("route row pointers must be monotonic")
        if self.row_pointers[-1] != len(self.target_axons):
            raise ValueError("terminal route row pointer must equal route count")
        _validate_events(
            "route target",
            self.target_axons,
            FPGA_CORE_CAPACITY_V1.max_routes,
            FPGA_CORE_CAPACITY_V1.max_axons,
        )

    @property
    def route_count(self) -> int:
        return len(self.target_axons)

    def targets_for_source(self, source_neuron: int) -> tuple[int, ...]:
        _require_count("source_neuron", source_neuron, 0, self.neuron_count - 1)
        start = self.row_pointers[source_neuron]
        stop = self.row_pointers[source_neuron + 1]
        return self.target_axons[start:stop]


@dataclass(frozen=True, slots=True)
class DoubleBufferedRecurrentQueue:
    """Finite recurrent-event banks with an explicit current-bank selector."""

    current_bank: int = 0
    bank0: tuple[int, ...] = ()
    bank1: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.current_bank not in (0, 1):
            raise ValueError("current_bank must be 0 or 1")
        _validate_events(
            "bank0",
            self.bank0,
            FPGA_CORE_CAPACITY_V1.max_recurrent_events_per_tick,
            FPGA_CORE_CAPACITY_V1.max_axons,
        )
        _validate_events(
            "bank1",
            self.bank1,
            FPGA_CORE_CAPACITY_V1.max_recurrent_events_per_tick,
            FPGA_CORE_CAPACITY_V1.max_axons,
        )

    @property
    def current_events(self) -> tuple[int, ...]:
        return self.bank0 if self.current_bank == 0 else self.bank1

    @property
    def inactive_events(self) -> tuple[int, ...]:
        return self.bank1 if self.current_bank == 0 else self.bank0

    @classmethod
    def empty(cls) -> "DoubleBufferedRecurrentQueue":
        return cls(current_bank=0, bank0=(), bank1=())


@dataclass(frozen=True, slots=True)
class RecurrentRoutingResult:
    """One tick's recurrent consumption, generation, and Phase-F commit."""

    consumed_recurrent_axons: tuple[int, ...]
    routed_output_axons: tuple[int, ...]
    queue_after_commit: DoubleBufferedRecurrentQueue


def freeze_spike_routes_v1(
    routes: Iterable[SpikeRoute],
    *,
    neuron_count: int,
    capacity: FpgaCoreCapacity = FPGA_CORE_CAPACITY_V1,
) -> FrozenRouteStorage:
    """Freeze routes into CSR order while preserving declaration order per source."""

    _require_count("neuron_count", neuron_count, 1, capacity.max_neurons)
    source = tuple(routes)
    if len(source) > capacity.max_routes:
        raise ValueError("route count exceeds M11.5 physical capacity")

    rows: list[list[int]] = [[] for _ in range(neuron_count)]
    seen: set[tuple[int, int]] = set()
    for route in source:
        if not isinstance(route, SpikeRoute):
            raise TypeError("routes must contain SpikeRoute objects")
        if route.source_neuron >= neuron_count:
            raise ValueError("route source is outside configured neuron_count")
        if route.target_axon >= capacity.max_axons:
            raise ValueError("route target axon is outside M11.5 physical capacity")
        key = (route.source_neuron, route.target_axon)
        if key in seen:
            raise ValueError("duplicate (source_neuron, target_axon) route")
        seen.add(key)
        rows[route.source_neuron].append(route.target_axon)

    pointers = [0]
    targets: list[int] = []
    for row in rows:
        targets.extend(row)
        pointers.append(len(targets))

    # Construct through the strict storage validator; capacity can be a smaller
    # test profile, so enforce it before using the project-wide default checks.
    if len(targets) > capacity.max_routes:
        raise ValueError("route count exceeds M11.5 physical capacity")
    if any(target >= capacity.max_axons for target in targets):
        raise ValueError("route target axon is outside M11.5 physical capacity")
    return FrozenRouteStorage(
        neuron_count=neuron_count,
        row_pointers=tuple(pointers),
        target_axons=tuple(targets),
    )


def route_and_commit_recurrent_v1(
    queue: DoubleBufferedRecurrentQueue,
    routes: FrozenRouteStorage,
    spike_flags: Sequence[bool],
    *,
    capacity: FpgaCoreCapacity = FPGA_CORE_CAPACITY_V1,
) -> RecurrentRoutingResult:
    """Generate the inactive bank from spikes, then perform the Phase-F swap.

    The returned ``consumed_recurrent_axons`` is captured from the current bank
    *before* routing.  Newly routed events are written only to the inactive bank
    and become ``current_events`` only in ``queue_after_commit``.  Thus no event
    emitted by this call can be consumed by the same tick represented by it.
    """

    if not isinstance(queue, DoubleBufferedRecurrentQueue):
        raise TypeError("queue must be DoubleBufferedRecurrentQueue")
    if not isinstance(routes, FrozenRouteStorage):
        raise TypeError("routes must be FrozenRouteStorage")
    if len(spike_flags) != routes.neuron_count:
        raise ValueError("spike_flags length must equal route neuron_count")
    if any(not isinstance(flag, bool) for flag in spike_flags):
        raise TypeError("spike_flags entries must be bools")

    consumed = queue.current_events
    generated: list[int] = []
    for source_neuron, spiked in enumerate(spike_flags):
        if not spiked:
            continue
        start = routes.row_pointers[source_neuron]
        stop = routes.row_pointers[source_neuron + 1]
        for target_axon in routes.target_axons[start:stop]:
            if target_axon >= capacity.max_axons:
                raise ValueError("route target axon is outside M11.5 physical capacity")
            generated.append(target_axon)
            if len(generated) > capacity.max_recurrent_events_per_tick:
                raise OverflowError("next recurrent queue exceeds M11.5 capacity")

    routed = tuple(generated)
    if queue.current_bank == 0:
        committed = DoubleBufferedRecurrentQueue(
            current_bank=1,
            bank0=queue.bank0,
            bank1=routed,
        )
    else:
        committed = DoubleBufferedRecurrentQueue(
            current_bank=0,
            bank0=routed,
            bank1=queue.bank1,
        )

    return RecurrentRoutingResult(
        consumed_recurrent_axons=consumed,
        routed_output_axons=routed,
        queue_after_commit=committed,
    )


def reset_recurrent_queue_v1() -> DoubleBufferedRecurrentQueue:
    """Return the deterministic architectural-reset queue state."""

    return DoubleBufferedRecurrentQueue.empty()


def _validate_events(
    name: str,
    events: Iterable[int],
    maximum_count: int,
    max_axons: int,
) -> None:
    values = tuple(events)
    if len(values) > maximum_count:
        raise ValueError(f"{name} count exceeds M11.5 capacity")
    for axon_id in values:
        if isinstance(axon_id, bool) or not isinstance(axon_id, int):
            raise TypeError(f"{name} entries must be ints")
        if not 0 <= axon_id < max_axons:
            raise ValueError(f"{name} axon is outside M11.5 physical capacity")


def _require_count(name: str, value: int, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in {minimum}..{maximum}")
