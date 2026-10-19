"""P06-B1.5 three-slot/one-engine paging, NEXT event routing and traffic model.

Host-only MODEL, not firmware, PL trace, DDR write or measured bandwidth.
P05.2i physically measured the page-transfer SIZES, not this scaled workload.
The accepted P03/P02/P05/P08/Track A sources remain read-only.

A slot's LogicalCore state is represented by the logical chip model;
page-in/out transitions are accounting events, NOT a reconstruction of
byte-exact dirty P02 DDR records. That belongs to independently validated
future physical P07-B, not this simulation.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .compiler import NetworkSpec
from .ddr_abi import P02_DDR_CONTEXT_STRIDE_BYTES, ddr_context_offset
from .hardware_p05 import P05_MAX_RESIDENT_CONTEXTS, P05_PHYSICAL_ENGINE_COUNT
from .hardware_p08 import export_paged_hardware_image
from .p06_b12_partition import B12Result
from .p06_b14_monolithic import B14_TICKS, EventSchedule
from .p06_b14_differential import B14Comparison, compare_monolithic_to_traces
from .p06_b1_contract import MAX_EVENTS_PER_BANK, MAX_PACKETS_PER_BANK
from .chip import LogicalChip
from .packet import SpikePacket
from .trace import BarrierSnapshot, ChipTrace

B15_SCHEMA = "p06-b1.5-p05-three-slot-host-scheduling-estimate-v1"
# Historical physical P05.2i read/write page-engine transfers, not theoretical
# complete DDR record sizes or scaled-B physical measurements:
P05_FULL_PAGE_IN_BYTES = 0x6B000        # 438,272
P05_MUTABLE_PAGE_OUT_BYTES = 0x1A000    # 106,496
P05_AXI_BURST_BYTES = 256
P05_OBSERVED_REFERENCE_DISPATCHES = 80
P05_OBSERVED_REFERENCE_BYTES = 43_581_440


class B15ScheduleError(ValueError):
    """Rejected schedule, barrier, event pressure, or attempted drop of traffic."""


def _valid_order(order: tuple[int, ...], ids: tuple[int, ...]) -> tuple[int, ...]:
    if (not isinstance(order, tuple) or len(order) != len(ids)
            or tuple(sorted(order)) != ids):
        raise B15ScheduleError("service order must be a permutation of every logical core ID")
    return order


@dataclass(frozen=True, slots=True)
class PagingOperation:
    tick: int
    ordinal: int
    core_id: int
    slot: int
    hit: bool
    evicted_core: int | None
    page_in_bytes: int
    mutable_page_out_bytes: int
    backing_ddr_offset_bytes: int
    evicted_ddr_offset_bytes: int | None


@dataclass(frozen=True, slots=True)
class FinalFlush:
    slot: int
    core_id: int
    mutable_page_out_bytes: int


class ResidentLRU:
    """Deterministic LRU, at most three concrete P05 slots, only one dispatch.

    Empty slot: smallest available index. Replacement: smallest last-use
    ordinal (tie breaks by physical slot). Every evaluated core becomes dirty.
    Dirty evictions and final flush generate mutable-only P05 out estimates.
    """

    def __init__(self, core_ids: tuple[int, ...]):
        if (not isinstance(core_ids, tuple) or not core_ids
                or len(set(core_ids)) != len(core_ids)
                or tuple(sorted(core_ids)) != core_ids
                or len(core_ids) > 126):
            raise B15ScheduleError("logical core IDs must be unique sorted P05-admissible IDs")
        if any(type(cid) is not int or not 0 <= cid < 126 for cid in core_ids):
            raise B15ScheduleError("logical core IDs must fit P05 diagnostic 0..125")
        if P05_MAX_RESIDENT_CONTEXTS != 3 or P05_PHYSICAL_ENGINE_COUNT != 1:
            raise B15ScheduleError("frozen three-slot one-HLS-engine contract changed")
        if P02_DDR_CONTEXT_STRIDE_BYTES != 0x80000:
            raise B15ScheduleError("frozen 512KiB backing record stride changed")
        self.ids = core_ids
        self.slots: list[int | None] = [None] * min(3, len(core_ids))
        self.last_used: list[int] = [-1] * len(self.slots)
        self.dirty: list[bool] = [False] * len(self.slots)
        self.operations: list[PagingOperation] = []
        self.final_flushes: list[FinalFlush] = []
        self._finalized = False

    def visit(self, tick: int, ordinal: int, core_id: int) -> PagingOperation:
        if self._finalized:
            raise B15ScheduleError("cannot schedule a dispatch after final mutable flush")
        if type(tick) is not int or type(ordinal) is not int or not 0 <= tick < B14_TICKS or ordinal < 0:
            raise B15ScheduleError("invalid global epoch / serial dispatch ordinal")
        if core_id not in self.ids:
            raise B15ScheduleError("unknown logical core")
        if core_id in self.slots:
            slot = self.slots.index(core_id)
            hit, evicted, flushed = True, None, 0
            loaded = 0
        else:
            hit, loaded = False, P05_FULL_PAGE_IN_BYTES
            if None in self.slots:
                slot = self.slots.index(None)
            else:
                slot = min(range(len(self.slots)), key=lambda s: (self.last_used[s], s))
            evicted = self.slots[slot]
            flushed = P05_MUTABLE_PAGE_OUT_BYTES if self.dirty[slot] else 0
            if evicted is not None and not self.dirty[slot]:
                raise B15ScheduleError("resident victim lacks accounted dirty state")
            self.slots[slot] = core_id
        self.last_used[slot] = ordinal
        self.dirty[slot] = True
        op = PagingOperation(
            tick=tick, ordinal=ordinal, core_id=core_id, slot=slot, hit=hit,
            evicted_core=evicted, page_in_bytes=loaded,
            mutable_page_out_bytes=flushed,
            backing_ddr_offset_bytes=ddr_context_offset(core_id),
            evicted_ddr_offset_bytes=(
                ddr_context_offset(evicted) if evicted is not None else None),
        )
        self.operations.append(op)
        return op

    def flush(self) -> tuple[FinalFlush, ...]:
        if self._finalized:
            raise B15ScheduleError("final flush already completed")
        self._finalized = True
        for slot, core in enumerate(self.slots):
            if core is not None and self.dirty[slot]:
                self.final_flushes.append(
                    FinalFlush(slot, core, P05_MUTABLE_PAGE_OUT_BYTES))
                self.dirty[slot] = False
        return tuple(self.final_flushes)

    def report(self) -> dict:
        if not self._finalized:
            raise B15ScheduleError("cannot finalize traffic estimate before dirty-slot flush")
        page_ins = sum(not op.hit for op in self.operations)
        hits = sum(op.hit for op in self.operations)
        replaced = [op for op in self.operations if op.evicted_core is not None]
        outs = len(replaced) + len(self.final_flushes)
        read_bytes = sum(op.page_in_bytes for op in self.operations)
        write_bytes = (sum(op.mutable_page_out_bytes for op in self.operations)
                       + sum(f.mutable_page_out_bytes for f in self.final_flushes))
        if (page_ins != len(self.operations) - hits
                or outs != sum(op.mutable_page_out_bytes > 0 for op in self.operations)
                   + len(self.final_flushes)):
            raise B15ScheduleError("page-load/dirty-flush accounting inconsistency")
        if read_bytes % P05_AXI_BURST_BYTES or write_bytes % P05_AXI_BURST_BYTES:
            raise B15ScheduleError("page-transfer sizes violate P05 observed burst alignment")
        return {
            "dispatches": len(self.operations),
            "global_barriers": max((op.tick for op in self.operations), default=-1) + 1,
            "one_engine_max_in_flight_dispatches": 1,
            "resident_context_slots": len(self.slots),
            "page_hits": hits,
            "full_page_ins": page_ins,
            "initial_empty_slot_page_ins": sum(
                not op.hit and op.evicted_core is None for op in self.operations),
            "replacement_page_ins": len(replaced),
            "dirty_evictions": len(replaced),
            "runtime_mutable_page_outs": len(replaced),
            "final_mutable_page_outs": len(self.final_flushes),
            "all_mutable_page_outs": outs,
            "full_page_in_bytes_each": P05_FULL_PAGE_IN_BYTES,
            "mutable_page_out_bytes_each": P05_MUTABLE_PAGE_OUT_BYTES,
            "full_ddr_backing_record_bytes_each": P02_DDR_CONTEXT_STRIDE_BYTES,
            "estimated_page_engine_read_bytes": read_bytes,
            "estimated_page_engine_write_bytes": write_bytes,
            "estimated_page_engine_total_bytes": read_bytes + write_bytes,
            "estimated_read_bursts_256B": read_bytes // P05_AXI_BURST_BYTES,
            "estimated_write_bursts_256B": write_bytes // P05_AXI_BURST_BYTES,
            "estimated_total_bursts_256B": (read_bytes + write_bytes) // P05_AXI_BURST_BYTES,
            "physical_scaled_page_traffic_measured": False,
            "physical_transfer_sizes_source": "accepted P05.2i 80-dispatch physical AXI proof",
            "physical_P05_reference_80_dispatch_bytes": P05_OBSERVED_REFERENCE_BYTES,
        }


@dataclass(frozen=True, slots=True)
class EpochPaging:
    tick: int
    dispatch_order: tuple[int, ...]
    slot_at_service: tuple[tuple[int, int], ...]
    page_hits: int
    page_ins: int
    dirty_evictions: int
    emitted_packets: int
    resident_at_emission_packets: int
    nonresident_at_emission_packets: int
    current_event_counts: tuple[int, ...]
    next_event_counts: tuple[int, ...]
    finished_barrier: bool
    next_bank: int


@dataclass(frozen=True, slots=True)
class B15Run:
    network_source_sha256: str
    deployment_sha256: str
    capacity_audit_sha256: str
    comparison: B14Comparison
    page_operations: tuple[PagingOperation, ...]
    final_flushes: tuple[FinalFlush, ...]
    epochs: tuple[EpochPaging, ...]
    logical_traces: tuple[ChipTrace, ...]
    initial_ddr_backing: tuple[dict, ...]
    traffic: dict
    operations_sha256: str

    def report(self) -> dict:
        return {
            "schema": B15_SCHEMA,
            "network_source_sha256": self.network_source_sha256,
            "deployment_sha256": self.deployment_sha256,
            "capacity_audit_sha256": self.capacity_audit_sha256,
            "page_schedule_sha256": self.operations_sha256,
            "monolithic_trace_sha256": self.comparison.reference.trace_sha256,
            "partitioned_trace_sha256": self.comparison.output_trace_sha256,
            "algorithmic_neural_parity": True,
            "ticks": len(self.epochs),
            "readout_spike_counts": list(self.comparison.readout_spike_counts),
            "predicted_class": self.comparison.predicted_class,
            "routed_packet_events": sum(e.emitted_packets for e in self.epochs),
            "resident_when_emitted_packets": sum(e.resident_at_emission_packets
                                                 for e in self.epochs),
            "nonresident_when_emitted_packets": sum(e.nonresident_at_emission_packets
                                                    for e in self.epochs),
            "paging": self.traffic,
            "initial_ddr_backing": list(self.initial_ddr_backing),
            "latency_seconds": None,
            "physical_latency_measured": False,
            "physical_kv260_execution": "NOT_TESTED",
            "official_mnist_test_access": "NONE",
            "actual_ddr_mutable_bytes_materialized": False,
        }


def _page_digest(ops: tuple[PagingOperation, ...],
                 flushes: tuple[FinalFlush, ...]) -> str:
    rows = {
        "page_ins_and_dispatches": [
            (op.tick, op.ordinal, op.core_id, op.slot, op.hit,
             op.evicted_core, op.page_in_bytes, op.mutable_page_out_bytes)
            for op in ops
        ],
        "final_flushes": [(f.slot, f.core_id, f.mutable_page_out_bytes)
                          for f in flushes],
    }
    return hashlib.sha256(json.dumps(
        rows, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _scheduled_packets(network: NetworkSpec, schedule: EventSchedule, compiled) -> dict[int, tuple[SpikePacket, ...]]:
    """External input expansion to actual B1.2 destination axons, including duplicates across cores."""
    routes = {(r.input_population, r.input_index) for r in compiled.ingress_routes}
    for population in network.input_populations:
        if population.name not in schedule:
            raise B15ScheduleError("missing external schedule population")
    if set(schedule) != {p.name for p in network.input_populations}:
        raise B15ScheduleError("unexpected external population schedule")
    streams = {}
    for tick in range(B14_TICKS):
        packets: list[SpikePacket] = []
        for pop, rows in sorted(schedule.items()):
            if len(rows) != B14_TICKS:
                raise B15ScheduleError("external event schedule must contain 26 ticks")
            active = tuple(i for i in rows[tick] if (pop, i) in routes)
            if active:
                packets.extend(compiled.external_packets(pop, active, target_timestep=tick))
        streams[tick] = tuple(sorted(packets, key=lambda p: p.logical_key))
    return streams


def run_paged_model(
    network: NetworkSpec,
    result: B12Result,
    schedule: EventSchedule,
    *, readout_population: str,
    service_orders: tuple[tuple[int, ...], ...] | None = None,
    flush_at_end: bool = True,
) -> B15Run:
    """Serial single-engine 26-epoch simulated resident-slot schedule.

    One visit per core per tick, with exact byte accounting and NEXT routing.
    A logical core's Python state survives eviction in the software model,
    while evictions charge P05 measured mutable-out transfer sizes.
    Does not create/verify the actual runtime P02 DDR state images.
    """
    if flush_at_end is not True:
        raise B15ScheduleError("final mutable-slot flush is mandatory")
    if not isinstance(result, B12Result):
        raise B15ScheduleError("B1.5 requires accepted B1.2 mapped deployment")
    compiled = result.compiled
    if compiled.source_fingerprint != network.fingerprint:
        raise B15ScheduleError("source graph does not match B1.2 compiled deployment")
    if result.capacity_audit.get("original_compiled_sha256") != compiled.fingerprint:
        raise B15ScheduleError("B1.1 packed audit mismatch")
    # Source-bound B1.1 record manifests must be genuine, not a substituted
    # source-compiled fingerprint with an unrelated packed DDR occupancy.
    from .p06_b1_contract import audit_compiled_candidate
    if result.capacity_audit != audit_compiled_candidate(compiled):
        raise B15ScheduleError("B1.1 packed/DDR SHA manifest recomputation mismatch")
    ordered = tuple(sorted(c.core_id for c in compiled.logical_deployment.core_configs))
    hardware = export_paged_hardware_image(compiled.logical_deployment.core_configs)
    if (hardware.logical_core_ids != ordered or hardware.resident_context_count != min(3, len(ordered))
            or hardware.physical_engine_count != 1):
        raise B15ScheduleError("P08 backing mapping / physical slots mismatch")
    if service_orders is not None:
        if not isinstance(service_orders, tuple) or len(service_orders) != B14_TICKS:
            raise B15ScheduleError("service_orders must contain exactly 26 explicit core permutations")
        orders = tuple(_valid_order(x, ordered) for x in service_orders)
    else:
        orders = (ordered,) * B14_TICKS
    # Validate full uncompiled input source/schedule constraints *before* altering
    # any logical state. Independently accepted B1.4 oracle performs validation.
    from .p06_b14_monolithic import simulate_monolithic
    oracle = simulate_monolithic(network, schedule, readout_population=readout_population)
    incoming_by_tick = _scheduled_packets(network, schedule, compiled)
    paging = ResidentLRU(ordered)
    chip = LogicalChip(compiled.logical_deployment.core_configs)
    core_rank = {core: index for index, core in enumerate(ordered)}
    staged: tuple[SpikePacket, ...] = ()
    traces: list[ChipTrace] = []
    epoch_rows: list[EpochPaging] = []
    ordinal = 0
    for tick, order in enumerate(orders):
        current = tuple(sorted((*incoming_by_tick[tick], *staged), key=lambda p: p.logical_key))
        current_counts = Counter(p.destination_core for p in current)
        if any(current_counts[c] > MAX_EVENTS_PER_BANK for c in ordered):
            raise B15ScheduleError(f"CURRENT event bank overflow before tick {tick} dispatch")
        if any(packet.target_timestep != tick for packet in current):
            raise B15ScheduleError(f"CURRENT packet target epoch mismatch at tick {tick}")
        # Stage *all* CURRENT events before evaluation, as P05 dual banks
        # and the host backing ledger conceptually require.
        for packet in current:
            chip.cores[packet.destination_core].ingest_packet(packet)
        epoch_ops = []
        trace_by_core = {}
        packets_next = []
        resident_packet_count = nonresident_packet_count = 0
        for core_id in order:
            op = paging.visit(tick, ordinal, core_id)
            ordinal += 1
            epoch_ops.append(op)
            trace = chip.cores[core_id].evaluate(tick)
            trace_by_core[core_id] = trace
            for packet in trace.packets_out:
                # Emission snapshot BEFORE other cores may be paged in/out.
                if packet.destination_core in paging.slots:
                    resident_packet_count += 1
                else:
                    nonresident_packet_count += 1
                packets_next.append(packet)
        packets_next = tuple(sorted(packets_next, key=lambda p: p.logical_key))
        next_counts = Counter(p.destination_core for p in packets_next)
        source_counts = Counter(p.source_core for p in packets_next)
        if any(next_counts[c] > MAX_EVENTS_PER_BANK for c in ordered):
            raise B15ScheduleError(f"NEXT event bank overflow before tick {tick} barrier")
        if any(source_counts[c] > MAX_PACKETS_PER_BANK for c in ordered):
            raise B15ScheduleError(f"output packet RAM overflow before tick {tick} barrier")
        if any(packet.target_timestep != tick + 1 for packet in packets_next):
            raise B15ScheduleError(f"routed packet has incorrect NEXT epoch at tick {tick}")
        if tick == B14_TICKS - 1 and packets_next:
            raise B15ScheduleError("final drain tick emits packets into unsupported epoch 26")
        if len(trace_by_core) != len(ordered):
            raise B15ScheduleError("barrier cannot advance before all cores execute")
        # All outgoing packets must be accounted for at barrier before the
        # next epoch; packets for nonresident cores remain logical backing
        # events in the model. Next timestep must consume exactly once.
        stage_count = sum(next_counts.values())
        if stage_count != len(packets_next):
            raise B15ScheduleError("unacknowledged pending routed packets at barrier")
        staged = packets_next
        trace = ChipTrace(
            algorithmic_timestep=tick,
            cores=tuple(trace_by_core[c] for c in ordered),
            barrier=BarrierSnapshot(
                timestep=tick, completed_cores=ordered,
                in_flight_packets=0, can_advance=True,
            ),
            packet_traffic=(),
        )
        traces.append(trace)
        epoch_rows.append(EpochPaging(
            tick=tick, dispatch_order=order,
            slot_at_service=tuple((op.core_id, op.slot) for op in epoch_ops),
            page_hits=sum(op.hit for op in epoch_ops),
            page_ins=sum(not op.hit for op in epoch_ops),
            dirty_evictions=sum(op.evicted_core is not None for op in epoch_ops),
            emitted_packets=len(packets_next),
            resident_at_emission_packets=resident_packet_count,
            nonresident_at_emission_packets=nonresident_packet_count,
            current_event_counts=tuple(current_counts[c] for c in ordered),
            next_event_counts=tuple(next_counts[c] for c in ordered),
            finished_barrier=True,
            next_bank=(tick + 1) % 2,
        ))
    if staged:
        raise B15ScheduleError("nonempty final next-event queue after inference")
    flushes = paging.flush()
    compare = compare_monolithic_to_traces(
        network, result, schedule, tuple(traces),
        readout_population=readout_population, reference=oracle)
    traffic = paging.report()
    if (traffic["dispatches"] != B14_TICKS * len(ordered)
            or sum(e.emitted_packets for e in epoch_rows) != compare.observed_routed_packets
            or sum(e.current_event_counts[core_rank[c]] for e in epoch_rows
                   for c in ordered) != (
                compare.observed_external_packets + compare.observed_routed_packets)
            ):
        raise B15ScheduleError("total serial-dispatch/packet event accounting drift")
    ops = tuple(paging.operations)
    recorded = {row["core_id"]: row for row in result.capacity_audit["cores"]}
    initial_records = tuple({
        "core_id": core,
        "ddr_offset_bytes": ddr_context_offset(core),
        "full_ddr_record_bytes": P02_DDR_CONTEXT_STRIDE_BYTES,
        "initial_ddr_sha256": recorded[core]["initial_ddr_sha256"],
        "initial_payload_sha256": recorded[core]["initial_ddr_payload_sha256"],
    } for core in ordered)
    return B15Run(
        network_source_sha256=network.fingerprint,
        deployment_sha256=compiled.fingerprint,
        capacity_audit_sha256=result.capacity_audit["audit_sha256"],
        comparison=compare,
        page_operations=ops,
        final_flushes=flushes,
        epochs=tuple(epoch_rows),
        logical_traces=tuple(traces),
        initial_ddr_backing=initial_records,
        traffic=traffic,
        operations_sha256=_page_digest(ops, flushes),
    )
