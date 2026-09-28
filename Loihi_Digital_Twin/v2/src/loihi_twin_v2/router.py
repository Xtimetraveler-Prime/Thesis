"""Explicit logical packet queue and traffic accounting."""

from __future__ import annotations

from collections import Counter

from .packet import SpikePacket


class PacketRouter:
    def __init__(self) -> None:
        self._queue: list[SpikePacket] = []
        self._traffic: Counter[tuple[int, int, int]] = Counter()

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    def enqueue(self, packet: SpikePacket) -> None:
        self._queue.append(packet)
        source = -1 if packet.source_core is None else packet.source_core
        self._traffic[(packet.target_timestep, source, packet.destination_core)] += 1

    def enqueue_many(self, packets: tuple[SpikePacket, ...]) -> None:
        for packet in packets:
            self.enqueue(packet)

    def drain(self, *, reverse: bool = False, limit: int | None = None) -> tuple[SpikePacket, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")
        count = len(self._queue) if limit is None else min(limit, len(self._queue))
        if reverse:
            selected = tuple(reversed(self._queue[-count:])) if count else ()
            if count:
                del self._queue[-count:]
        else:
            selected = tuple(self._queue[:count])
            if count:
                del self._queue[:count]
        return selected

    def traffic_snapshot(self) -> tuple[tuple[int, int, int, int], ...]:
        return tuple(
            (timestep, source, destination, count)
            for (timestep, source, destination), count in sorted(self._traffic.items())
        )
