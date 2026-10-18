"""Strict host decoder for P08-A2.1 *experimental* KV260 latency sidecar.

All A53 times are raw CNTVCT ticks. PL counters are separate clock-domain
cycles. This module deliberately does NOT claim physical correctness or
convert PL cycles to seconds without an independently verified PL clock.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct
import zlib

MAGIC = b"P08ALAT1"
BASE = 0x43000000
CAPACITY = 1048576
HEADER_BYTES = 256
RECORD_BYTES = 96
MAX_FRAMES = 10000
SUCCESS = 0x600D600D
FAILURE = 0xDEAD0001


@dataclass(frozen=True)
class TimingRecord:
    index: int
    selected_trace: bool
    service_start: int
    after_ingress: int
    after_neural: int
    after_commit: int
    pl_dispatch_cycles: int
    pl_page_cycles: int
    ps_inference_ticks: int
    ps_control_ticks: int
    ps_route_ticks: int
    ps_barrier_ticks: int

    @property
    def service_ticks(self) -> int:
        return self.after_commit - self.service_start


@dataclass(frozen=True)
class TimingRun:
    count: int
    trace_index: int
    cntfrq_hz: int
    dataset_start: int
    dataset_stop: int
    records: tuple[TimingRecord, ...]

    @property
    def throughput_frames_per_second(self) -> float:
        """Whole autonomous window INCLUDING sidecar/header writes per frame."""
        return self.count * self.cntfrq_hz / (self.dataset_stop - self.dataset_start)


def _check_crc(block: bytes, end: int, label: str) -> None:
    stored, = struct.unpack_from("<I", block, end)
    actual = zlib.crc32(block[:end]) & 0xFFFFFFFF
    if actual != stored:
        raise ValueError(f"{label}: CRC mismatch")


def parse_timing(raw: bytes, *, expected_count: int | None = None) -> TimingRun:
    """Decode only complete/terminal-success raw 1MiB sidecars, fail closed.

    Physical evidence and independently validated P07A4R01 neural results
    must also be supplied before any P08 latency numbers can be accepted.
    """
    if len(raw) != CAPACITY:
        raise ValueError("P08: sidecar must be exactly 1MiB")
    head = raw[:HEADER_BYTES]
    if head[:8] != MAGIC:
        raise ValueError("P08: incorrect firmware sidecar magic")
    _check_crc(head, 252, "P08 header")
    version, header_bytes, status, completed, count, trace = struct.unpack_from(
        "<6I", head, 8)
    frequency, start, stop = struct.unpack_from("<3Q", head, 32)
    record_size, base, capacity = struct.unpack_from("<3I", head, 56)
    if (version != 1 or header_bytes != HEADER_BYTES or
            record_size != RECORD_BYTES or base != BASE or
            capacity != CAPACITY or any(head[68:252])):
        raise ValueError("P08: header schema or reserved bytes invalid")
    if (not 1 <= count <= MAX_FRAMES or trace >= count or
            expected_count is not None and expected_count != count):
        raise ValueError("P08: count or trace selection invalid")
    if (status != SUCCESS or completed != count or not frequency or
            start <= 0 or stop <= start):
        raise ValueError("P08: missing successful complete timing terminal")
    used = HEADER_BYTES + count * RECORD_BYTES
    if used > CAPACITY or any(raw[used:]):
        raise ValueError("P08: sidecar tail is not zero")
    rows: list[TimingRecord] = []
    previous_stop = start
    for index in range(count):
        offset = HEADER_BYTES + index * RECORD_BYTES
        block = raw[offset:offset + RECORD_BYTES]
        _check_crc(block, 88, f"P08 record {index}")
        frame, flags = struct.unpack_from("<2I", block)
        vals = struct.unpack_from("<10Q", block, 8)
        reserved, = struct.unpack_from("<I", block, 92)
        if (reserved or frame != index or flags not in (0, 1) or
                flags != int(index == trace)):
            raise ValueError(f"P08: record {index} index/trace/reserved invalid")
        service_start, after_ingress, after_neural, after_commit = vals[:4]
        pl_dispatch, pl_page, inference, control, route, barrier = vals[4:]
        if not (previous_stop <= service_start <= after_ingress <=
                after_neural <= after_commit <= stop):
            raise ValueError(f"P08: record {index} timer order invalid")
        if inference > after_neural - service_start or control > after_neural - service_start:
            raise ValueError(f"P08: record {index} P03 timing exceeds service")
        rows.append(TimingRecord(
            index, bool(flags), service_start, after_ingress, after_neural,
            after_commit, pl_dispatch, pl_page, inference, control, route, barrier
        ))
        previous_stop = after_commit
    return TimingRun(count, trace, frequency, start, stop, tuple(rows))
