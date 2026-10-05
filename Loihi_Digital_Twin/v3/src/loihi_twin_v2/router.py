"""Explicit logical packet queue and traffic accounting."""

from __future__ import annotations

from collections import Counter

from .packet import SpikePacket


class PacketRouter:
    def __init__(self) -> None:
        self._queue: list[SpikePacket] = []
        self._traffic: Counter[tuple[int, int, int, str]] = Counter()

    @property
    def pending_count(self) -> int:
        return len(self._queue)

    def enqueue(self, packet: SpikePacket) -> None:
        self._queue.append(packet)
        source = -1 if packet.source_core is None else packet.source_core
        self._traffic[
            (
                packet.target_timestep,
                source,
                packet.destination_core,
                packet.route_scope.value,
            )
        ] += 1

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

    def traffic_snapshot(self) -> tuple[tuple[int, int, int, str, int], ...]:
        """Return deterministic cumulative traffic grouped by route scope.

        Rows are ``(target_timestep, source_core, destination_core, scope, count)``.
        ``source_core`` is ``-1`` only for externally sourced packets should they ever
        pass through this router; core-generated P04 traffic is classified as local
        when source and destination core IDs match and remote otherwise.
        """

        return tuple(
            (timestep, source, destination, scope, count)
            for (timestep, source, destination, scope), count in sorted(self._traffic.items())
        )
