"""M05.11a provisional DMA packet format for a future S2MM transport.

This decoder consumes a complete captured 256-bit AXIS packet AFTER a real
DMA adapter has independently certified S2MM completion, TLAST observation,
actual transferred byte count, cache coherency and stream quiescence. Native
tests are host-only, NOT hardware interface tests.

Trace beats: 32 bytes each, first 24 are exact HLS TDATA, last 8 zero.
Terminal beat: 32 bytes, with TLAST emitted by m05_trace_dma_packetizer.
All AXIS TKEEP bits are 1; footer is NOT a neural trace row.
Little-endian footer: reserved_u64, count_u32, status_u32, session_u64,
magic_u64 == ASCII M0511END. Reject malformed frame and mismatched actual
HLS status; do not publish ANY provisional row on failure or corruption.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from .m05_execution_abi import (
    encode_neuron, encode_synapse, encode_external,
    encode_trace_for_native_test, decode_trace,
)
from .m05_execution_controller import RunPlan
from .m05_trace_commit import RollingTraceCommitGate, TraceRunResult, RollingTraceRow

DMA_BEAT_BYTES = 32
FOOTER_MAGIC = 0x4D30353131454E44
MAX_PACKET_BEATS = 1024 * 64 + 1
MAX_DMA_PACKET_BYTES = MAX_PACKET_BEATS * DMA_BEAT_BYTES
_FOOTER = struct.Struct("<QIIQQ")


class DMAFrameError(ValueError):
    """Invalid transport frame. Do not publish any trace."""


@dataclass(frozen=True)
class DMAFrameResult:
    result: TraceRunResult
    session_id: int
    received_trace_beats: int
    actual_dma_bytes: int
    hls_status: int


def _bounded_int(value: object, minimum: int, maximum: int, label: str) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise DMAFrameError(f"invalid {label}")


def build_mm2s_buffers(plan: RunPlan) -> dict[str, bytes]:
    """Return padded input data buffers, NOT a DMA driver/descriptors.

    Each record occupies 32 bytes to match the proposed 256-bit input bridge.
    No hardware MM2S operation is performed. Zero-item streams are empty;
    a live adapter must NOT arm a zero-byte DMA descriptor.
    """
    if type(plan) is not RunPlan:
        raise TypeError("expected validated RunPlan")
    return {
        "neurons": b"".join(encode_neuron(x).ljust(32, b"\0") for x in plan.neurons),
        "synapses": b"".join(encode_synapse(x).ljust(32, b"\0") for x in plan.synapses),
        "external_events": b"".join(
            encode_external(x).ljust(32, b"\0") for x in plan.external_events
        ),
    }


def build_fake_dma_packet_for_test(
    rows: tuple[RollingTraceRow, ...], *, status: int, session_id: int
) -> bytes:
    """Only synthetic host test vectors, NOT provenance of genuine RTL."""
    _bounded_int(status, 0, 6, "hardware status")
    _bounded_int(session_id, 0, (1 << 64) - 1, "session ID")
    if not isinstance(rows, tuple) or len(rows) > MAX_PACKET_BEATS - 1:
        raise ValueError("invalid synthetic rows")
    trace = b"".join(encode_trace_for_native_test(r).ljust(32, b"\0")
                     for r in rows)
    return trace + _FOOTER.pack(0, len(rows), status, session_id, FOOTER_MAGIC)


def accept_dma_frame(
    packet: bytes, *,
    session_id: int,
    neuron_count: int,
    ticks: int,
    hls_status: int,
    transferred_bytes: int,
    dma_completed: bool,
    tlast_certified: bool,
    transport_quiescent: bool,
) -> DMAFrameResult:
    """Fail closed unless DMA and actual HLS status corroborate the footer.

    The caller must supply *independent* real DMA/AXI evidence. Supplying
    booleans in a unit test does not demonstrate a physical transfer.
    """
    _bounded_int(session_id, 0, (1 << 64) - 1, "session ID")
    _bounded_int(hls_status, 0, 6, "AXI-Lite HLS return")
    _bounded_int(transferred_bytes, DMA_BEAT_BYTES, MAX_DMA_PACKET_BYTES,
                 "actual DMA byte count")
    if (dma_completed is not True or tlast_certified is not True
            or transport_quiescent is not True):
        raise DMAFrameError("DMA incomplete, no certified TLAST or no idle fence")
    if type(packet) is not bytes or len(packet) != transferred_bytes:
        raise DMAFrameError("DMA memory bytes differ from hardware transfer count")
    if len(packet) % DMA_BEAT_BYTES:
        raise DMAFrameError("DMA packet is not a sequence of 32-byte beats")
    gate = RollingTraceCommitGate(neuron_count, ticks)
    footer = packet[-DMA_BEAT_BYTES:]
    reserved, count, status, footer_session, magic = _FOOTER.unpack(footer)
    if reserved != 0 or magic != FOOTER_MAGIC or footer_session != session_id:
        raise DMAFrameError("invalid terminal footer magic/reserved/session ID")
    actual_rows = len(packet) // DMA_BEAT_BYTES - 1
    if count != actual_rows:
        raise DMAFrameError("footer output count disagrees with DMA beat count")
    if count > gate.expected_rows:
        raise DMAFrameError("DMA output exceeded allocated neural trace capacity")
    if status != hls_status:
        raise DMAFrameError("footer status differs from independent HLS ap_return")
    if status > 6:
        raise DMAFrameError("unknown/invalid HLS footer status")
    if status == 0 and count != gate.expected_rows:
        raise DMAFrameError("hardware status0 despite truncated trace")
    for i in range(actual_rows):
        word = packet[DMA_BEAT_BYTES * i: DMA_BEAT_BYTES * (i + 1)]
        if word[24:] != b"\0" * 8:
            raise DMAFrameError("nonzero high padding in 256-bit trace transport beat")
        gate.offer_row(decode_trace(word[:24]))
    result = gate.complete(status)
    if status == 0 and not result.accepted:
        raise DMAFrameError("status0 frame fails atomic trace validation: " +
                            str(result.reason))
    if status != 0 and (result.accepted or result.rows):
        raise DMAFrameError("hardware failed but provisional trace was exposed")
    return DMAFrameResult(
        result=result, session_id=session_id,
        received_trace_beats=actual_rows,
        actual_dma_bytes=transferred_bytes, hls_status=hls_status,
    )
