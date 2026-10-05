"""Manycore logical chip orchestration for the v2 Python golden model."""

from __future__ import annotations

from .barrier import BarrierCoordinator
from .core import LogicalCore, LogicalCoreConfig
from .packet import SpikePacket
from .resources import MAX_LOGICAL_CORES
from .router import PacketRouter
from .trace import ChipTrace, CoreTrace


class LogicalChip:
    def __init__(self, core_configs: tuple[LogicalCoreConfig, ...]) -> None:
        if not core_configs:
            raise ValueError("a logical chip must contain at least one configured core")
        if len(core_configs) > MAX_LOGICAL_CORES:
            raise ValueError("configured logical core count exceeds Loihi-1 chip limit")
        ids = [config.core_id for config in core_configs]
        if len(ids) != len(set(ids)):
            raise ValueError("logical core IDs must be unique")
        self.cores = {config.core_id: LogicalCore(config) for config in core_configs}
        self.router = PacketRouter()
        self.barrier = BarrierCoordinator()
        self.current_timestep = 0
        self._core_traces: tuple[CoreTrace, ...] = ()
        self._validate_routes()

    def _validate_routes(self) -> None:
        for core in self.cores.values():
            for route_entry in core.config.output_routes:
                for route in route_entry.routes:
                    destination = self.cores.get(route.destination_core)
                    if destination is None:
                        raise ValueError(
                            f"route targets unconfigured core {route.destination_core}"
                        )
                    if route.destination_axon not in destination._axons:
                        raise ValueError(
                            f"route targets missing axon {route.destination_axon} on core {route.destination_core}"
                        )

    def inject_external(self, packet: SpikePacket) -> None:
        if self.barrier.active:
            raise RuntimeError("external packets may only be injected before core evaluation")
        if packet.target_timestep != self.current_timestep:
            raise ValueError("external packet target_timestep must equal current chip timestep")
        destination = self.cores.get(packet.destination_core)
        if destination is None:
            raise ValueError("external packet targets an unconfigured core")
        destination.ingest_packet(packet)

    def evaluate(
        self,
        external_packets: tuple[SpikePacket, ...] = (),
        service_order: tuple[int, ...] | None = None,
    ) -> tuple[CoreTrace, ...]:
        if self.barrier.active:
            raise RuntimeError("current timestep is already awaiting packet drain")
        for packet in external_packets:
            self.inject_external(packet)

        core_ids = tuple(sorted(self.cores))
        order = core_ids if service_order is None else service_order
        if tuple(sorted(order)) != core_ids or len(order) != len(core_ids):
            raise ValueError("service_order must be a permutation of configured core IDs")

        self.barrier.begin(self.current_timestep, core_ids)
        traces: list[CoreTrace] = []
        for core_id in order:
            trace = self.cores[core_id].evaluate(self.current_timestep)
            traces.append(trace)
            self.barrier.mark_core_complete(core_id)
            self.router.enqueue_many(trace.packets_out)
            self.barrier.packet_enqueued(len(trace.packets_out))
        self._core_traces = tuple(sorted(traces, key=lambda t: t.logical_core_id))
        return self._core_traces

    def drain_packets(
        self,
        *,
        reverse: bool = False,
        limit: int | None = None,
    ) -> tuple[SpikePacket, ...]:
        if not self.barrier.active:
            raise RuntimeError("no active timestep is awaiting packet drain")
        packets = self.router.drain(reverse=reverse, limit=limit)
        for packet in packets:
            destination = self.cores.get(packet.destination_core)
            if destination is None:
                raise ValueError("routed packet targets an unconfigured core")
            destination.ingest_packet(packet)
            self.barrier.packet_delivered()
        return tuple(sorted(packets, key=lambda p: p.logical_key))

    @property
    def can_advance(self) -> bool:
        return self.barrier.can_advance and self.router.pending_count == 0

    def advance(self) -> ChipTrace:
        if not self.can_advance:
            raise RuntimeError("cannot advance until all current-timestep traffic drains")
        barrier_snapshot = self.barrier.snapshot()
        trace = ChipTrace(
            algorithmic_timestep=self.current_timestep,
            cores=self._core_traces,
            barrier=barrier_snapshot,
            packet_traffic=self.router.traffic_snapshot(),
        )
        next_timestep = self.barrier.advance()
        self.current_timestep = next_timestep
        self._core_traces = ()
        return trace

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
