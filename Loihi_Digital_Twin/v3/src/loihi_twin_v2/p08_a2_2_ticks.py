"""Fail-closed decoder for P08-A2.2 per-tick *experimental* A53 captures.

Pairs 3MiB P08TCK02 timing with the 1MiB P08ALAT1 image sidecar.
No hardware run, physical correctness or calibrated PL clock inferred.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct
import zlib
from .p08_a2_timing import TimingRun

MAGIC = b"P08TCK02"
BASE = 0x43100000
CAPACITY = 3 * 1024 * 1024
HEADER = 256
RECORD = 96
TICKS = 26
MAX_FRAMES = 1024
SUCCESS = 0x600D600D


@dataclass(frozen=True)
class Tick:
    frame: int
    tick: int
    external_events: int
    emitted_packets: int
    acknowledged_packets: int
    final_drain: bool
    start: int
    after_encode: int
    after_append: int
    after_dispatch: int
    after_trace: int
    after_route: int
    after_barrier: int
    pl_dispatch_cycles: int

    @property
    def source_ticks(self) -> int:
        return self.after_encode - self.start

    @property
    def bank_ticks(self) -> int:
        return self.after_append - self.after_encode

    @property
    def dispatch_wrapper_ticks(self) -> int:
        return self.after_dispatch - self.after_append

    @property
    def trace_ticks(self) -> int:
        return self.after_trace - self.after_dispatch

    @property
    def route_ticks(self) -> int:
        return self.after_route - self.after_trace

    @property
    def barrier_ticks(self) -> int:
        return self.after_barrier - self.after_route


@dataclass(frozen=True)
class TickRun:
    count: int
    trace_index: int
    descriptor_crc32: int
    hz: int
    start: int
    stop: int
    ticks: tuple[Tick, ...]


def parse_ticks(raw: bytes, image: TimingRun,
                *, expected_descriptor_crc32: int | None = None) -> TickRun:
    if len(raw) != CAPACITY:
        raise ValueError("P08-A2.2: raw tick sidecar must be exactly 3MiB")
    h = raw[:HEADER]
    if h[:8] != MAGIC:
        raise ValueError("P08-A2.2: wrong sidecar magic")
    if (zlib.crc32(h[:252]) & 0xffffffff) != struct.unpack_from("<I", h, 252)[0]:
        raise ValueError("P08-A2.2: header CRC wrong")
    version, header, status, complete, count, ticks_per = struct.unpack_from("<6I", h, 8)
    hz, = struct.unpack_from("<Q", h, 32)
    base, capacity, record_size, descriptor_crc, trace_frame, reserved = struct.unpack_from("<6I", h, 40)
    start, stop = struct.unpack_from("<2Q", h, 64)
    if (version != 2 or header != HEADER or status != SUCCESS or
            not 1 <= count <= MAX_FRAMES or complete != count or
            ticks_per != TICKS or base != BASE or capacity != CAPACITY or
            record_size != RECORD or reserved != 0 or any(h[80:252])):
        raise ValueError("P08-A2.2: header schema/status/reserved invalid")
    if (count != image.count or trace_frame != image.trace_index or
            hz != image.cntfrq_hz or start != image.dataset_start or
            stop < image.dataset_stop or stop <= start or
            expected_descriptor_crc32 is not None and
            descriptor_crc != expected_descriptor_crc32):
        raise ValueError("P08-A2.2: header does not match A2.1 image sidecar")
    used = HEADER + count * TICKS * RECORD
    if used > CAPACITY or any(raw[used:]):
        raise ValueError("P08-A2.2: reserved tail nonzero")
    result: list[Tick] = []
    for frame in range(count):
        row = image.records[frame]
        prev_end = row.after_ingress
        cycles = 0
        for tick in range(TICKS):
            off = HEADER + (frame * TICKS + tick) * RECORD
            block = raw[off:off+RECORD]
            if (zlib.crc32(block[:88]) & 0xffffffff) != struct.unpack_from("<I", block, 88)[0]:
                raise ValueError(f"P08-A2.2: frame={frame} tick={tick} CRC bad")
            row_frame, row_tick, events, emitted, acknowledged, flags = struct.unpack_from("<6I", block)
            timestamps = struct.unpack_from("<7Q", block, 24)
            pl_cycles, = struct.unpack_from("<Q", block, 80)
            padding, = struct.unpack_from("<I", block, 92)
            if (row_frame != frame or row_tick != tick or
                    flags != int(tick == TICKS-1) or
                    events > 784 or (tick == TICKS-1 and events != 0) or
                    acknowledged > emitted or
                    padding != 0):
                raise ValueError(f"P08-A2.2: frame={frame} tick={tick} metadata invalid")
            t0, t1, t2, t3, t4, t5, t6 = timestamps
            if not (prev_end <= t0 <= t1 <= t2 <= t3 <= t4 <= t5 <= t6 <= row.after_neural):
                raise ValueError(f"P08-A2.2: frame={frame} tick={tick} timestamps invalid")
            result.append(Tick(frame, tick, events, emitted, acknowledged,
                               bool(flags), *timestamps, pl_cycles))
            prev_end = t6
            cycles += pl_cycles
        if cycles != row.pl_dispatch_cycles:
            raise ValueError(f"P08-A2.2: frame={frame} PL cycles mismatch against P03")
    return TickRun(count, trace_frame, descriptor_crc, hz, start, stop, tuple(result))
