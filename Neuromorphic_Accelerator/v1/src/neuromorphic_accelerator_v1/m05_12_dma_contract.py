"""M05.12a — conservative DMA *admission and lifecycle model* (NO HARDWARE).

This is deliberately NOT an AXI DMA driver. It neither accesses memory
addresses nor registers, allocates physically contiguous DDR, performs cache
maintenance, configures Vivado IP, nor controls a device. A future verified
backend must supply independent DMA/cache/quiescence evidence; boolean test
fixtures here do not certify a real hardware transfer.

A single MM2S submission per nonempty input is assumed: a second DMA packet
would introduce an early TLAST into the existing M05.11 256-bit input shim.
Actual direct-register versus scatter-gather/IP topology remains a separate
Vivado hardware gate. No automatic splitting, retry, or implicit recovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .m05_execution_controller import RunPlan
from .m05_dma_frame import (
    DMAFrameError, DMAFrameResult, DMA_BEAT_BYTES, build_mm2s_buffers,
    accept_dma_frame,
)

PORTS = ("neurons", "synapses", "external_events")
MAX_U64 = (1 << 64) - 1


class DMAAdmissionError(ValueError):
    """A requested transaction is not supported by the stated IP limits."""


class DMALifecycleError(RuntimeError):
    """Transport evidence/order violated; this session cannot be reused."""


@dataclass(frozen=True)
class DMALimits:
    """Explicit CANDIDATE capability; not detected from any Vivado design.

    PG021 AXI DMA v7.1 limits the configurable length field to 8..26 bits.
    256-bit simple transfers are a proposal, not an assertion that a real
    DMA IP has been configured, connected, or verified.
    """
    length_width: int
    stream_width_bits: int = 256
    scatter_gather: bool = False
    micro_mode: bool = False

    def __post_init__(self) -> None:
        if type(self.length_width) is not int or not 8 <= self.length_width <= 26:
            raise DMAAdmissionError("DMA length field must have 8..26 bits")
        if self.stream_width_bits != 256 or type(self.stream_width_bits) is not int:
            raise DMAAdmissionError("M05.11 shims require 256-bit AXIS")
        if type(self.scatter_gather) is not bool or self.scatter_gather:
            raise DMAAdmissionError("SG needs separately verified packet/BD rules")
        if type(self.micro_mode) is not bool or self.micro_mode:
            raise DMAAdmissionError("micro DMA size/boundary rules not verified")

    @property
    def maximum_bytes(self) -> int:
        return (1 << self.length_width) - 1


@dataclass(frozen=True)
class MM2SSubmission:
    port: str
    payload: bytes

    @property
    def transfer_bytes(self) -> int:
        return len(self.payload)


@dataclass(frozen=True)
class PreparedDMARun:
    """Symbolic transfer plan: no buffer address, physical ownership or DMA."""
    plan: RunPlan
    session_id: int
    limits: DMALimits
    sources: tuple[MM2SSubmission, ...]
    s2mm_capacity_bytes: int

    def source_length(self, port: str) -> int:
        if port not in PORTS:
            raise DMAAdmissionError("unknown MM2S port")
        return next((x.transfer_bytes for x in self.sources
                     if x.port == port), 0)


def prepare_dma_run(plan: RunPlan, *, session_id: int,
                    limits: DMALimits) -> PreparedDMARun:
    """Check complete 32-byte buffers BEFORE any hardware may be armed.

    PG021 S2MM_LENGTH is a capacity, NOT an assertion of actual bytes
    received. Reserve the maximum successful trace plus TLAST footer even if
    a failed HLS run may produce a shorter frame. Never issue zero-byte DMA.
    """
    if type(plan) is not RunPlan:
        raise TypeError("expected accepted immutable RunPlan")
    if type(limits) is not DMALimits:
        raise TypeError("explicit reviewed DMALimits required")
    if type(session_id) is not int or not 0 <= session_id <= MAX_U64:
        raise DMAAdmissionError("session ID must be unsigned64")
    payloads = build_mm2s_buffers(plan)
    sources = []
    for port in PORTS:
        data = payloads[port]
        if len(data) % DMA_BEAT_BYTES:
            raise DMAAdmissionError("input buffer not 32-byte packed")
        if len(data) > limits.maximum_bytes:
            raise DMAAdmissionError(
                f"{port} requires {len(data)} bytes, IP permits "
                f"{limits.maximum_bytes}; no unverified descriptor splitting"
            )
        if data:
            sources.append(MM2SSubmission(port, data))
    capacity = (len(plan.neurons) * plan.ticks + 1) * DMA_BEAT_BYTES
    if capacity > limits.maximum_bytes:
        raise DMAAdmissionError(
            f"S2MM requires {capacity} bytes, IP permits "
            f"{limits.maximum_bytes}; no truncated output allocation"
        )
    return PreparedDMARun(
        plan=plan, session_id=session_id, limits=limits,
        sources=tuple(sources), s2mm_capacity_bytes=capacity,
    )


class DMAStage(Enum):
    PREPARED = "prepared"
    RECEIVE_ARMED = "receive_armed"
    ACTIVE = "active"
    FINALIZING = "finalizing"
    VERIFIED = "verified"
    FAULT = "fault"


@dataclass(frozen=True)
class S2MMEvidence:
    """Fields a REAL future driver must establish independently.

    In unit tests they are synthetic assertions. The caller must not infer
    them solely from the packet itself, from ap_done, or from FIFO emptiness.
    """
    packet: bytes
    actual_bytes: int
    dma_completed: bool
    tlast_seen: bool
    cpu_cache_invalidated: bool
    no_outstanding_writes: bool
    transport_quiescent: bool


class DMASessionLedger:
    """Strict one-use host lifecycle check; no real MMIO or DMA operations.

    Receive must be armed before shell START and any MM2S transfer.
    Completion of all submitted inputs is required on a successful run, but
    a failed HLS run may terminate while MM2S data remains unconsumed.
    A verified successful frame still requires independent bridge COMPLETE,
    ACK, and memory-ownership publication checks by a future real driver.
    """

    def __init__(self, prepared: PreparedDMARun):
        if type(prepared) is not PreparedDMARun:
            raise TypeError("expected pre-admitted DMA plan")
        self.prepared = prepared
        self.stage = DMAStage.PREPARED
        self._completed_inputs: set[str] = set()
        self._status: int | None = None

    def _require(self, stage: DMAStage, ok: bool, message: str) -> None:
        if self.stage is not stage or not ok:
            self.stage = DMAStage.FAULT
            raise DMALifecycleError(message)

    def abort(self, reason: str) -> None:
        """Timeout, DMA error, cache failure: quarantine until full reset."""
        self.stage = DMAStage.FAULT
        raise DMALifecycleError(f"session aborted: {reason}")

    def arm_receive(self, *, device_owns_buffer: bool) -> None:
        self._require(DMAStage.PREPARED, device_owns_buffer is True,
                      "S2MM requires verified buffer ownership before arm")
        self.stage = DMAStage.RECEIVE_ARMED

    def start_session(self) -> None:
        self._require(DMAStage.RECEIVE_ARMED, True,
                      "S2MM must be armed before shell START")
        self.stage = DMAStage.ACTIVE

    def complete_input(self, port: str, *, actual_bytes: int,
                       dma_completed: bool, tlast_seen: bool,
                       device_cache_ready: bool) -> None:
        expected = self.prepared.source_length(port) if port in PORTS else 0
        self._require(
            DMAStage.ACTIVE,
            port in PORTS and expected > 0
            and port not in self._completed_inputs
            and type(actual_bytes) is int and actual_bytes == expected
            and dma_completed is True and tlast_seen is True
            and device_cache_ready is True,
            "MM2S missing/duplicate/zero-length/short transfer or cache/TLAST",
        )
        self._completed_inputs.add(port)

    def record_hls_done(self, status: int) -> None:
        self._require(
            DMAStage.ACTIVE, self._status is None
            and type(status) is int and 0 <= status <= 6,
            "no reliable single HLS ap_done/ap_return",
        )
        self._status = status

    def request_finish(self) -> None:
        self._require(DMAStage.ACTIVE, self._status is not None,
                      "do not FINISH before independently latched ap_done")
        self.stage = DMAStage.FINALIZING

    def complete_receive(self, evidence: S2MMEvidence) -> DMAFrameResult:
        self._require(
            DMAStage.FINALIZING,
            type(evidence) is S2MMEvidence
            and type(evidence.actual_bytes) is int
            and 32 <= evidence.actual_bytes <= self.prepared.s2mm_capacity_bytes
            and type(evidence.packet) is bytes
            and len(evidence.packet) == evidence.actual_bytes
            and evidence.dma_completed is True and evidence.tlast_seen is True
            and evidence.cpu_cache_invalidated is True
            and evidence.no_outstanding_writes is True
            and evidence.transport_quiescent is True
            and (self._status != 0 or
                 self._completed_inputs == set(x.port for x in self.prepared.sources)),
            "unsafe S2MM completion, short buffer, stale cache, or unfinished MM2S",
        )
        try:
            frame = accept_dma_frame(
                evidence.packet, session_id=self.prepared.session_id,
                neuron_count=len(self.prepared.plan.neurons),
                ticks=self.prepared.plan.ticks, hls_status=self._status,
                transferred_bytes=evidence.actual_bytes,
                dma_completed=evidence.dma_completed,
                tlast_certified=evidence.tlast_seen,
                transport_quiescent=evidence.transport_quiescent,
            )
        except (DMAFrameError, ValueError) as exc:
            self.stage = DMAStage.FAULT
            raise DMALifecycleError(f"failed atomic DMA frame validation: {exc}") from exc
        self.stage = DMAStage.VERIFIED if frame.result.accepted else DMAStage.FAULT
        return frame
