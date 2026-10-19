"""P07-B.1 planning-only scaled-memory/resource admission; not a board driver.

All constants are cross-checked against accepted P02/P03/B1 source at test time.
This module cannot access hardware, datasets, or frozen checkpoint assets.
"""
from __future__ import annotations

from dataclasses import dataclass

BACKING_BASE = 0x40000000
BACKING_BYTES = 0x04000000
RECORD_BYTES = 0x80000
CORE_COUNT = 27
RESIDENT_SLOTS = 3
PHYSICAL_ENGINES = 1
PAGE_IN_BYTES = 0x6B000
PAGE_OUT_BYTES = 0x1A000
BURST_BYTES = 256
MMIO_BASE = 0xA4000000
MMIO_BYTES = 0x1000
MAX_BANK_EVENTS = 4096
MAX_PACKETS = 4096
MAX_ROUTES_PER_CORE = 4096
MAX_SYN_WORDS = 32768
INGRESS_HEADER_BYTES = 128
INGRESS_CHANNELS = 784
INGRESS_ROUTE_BYTES = 6
INGRESS_MAX_ROUTES = 784 * 126
INPUT_TICKS = 25
TOTAL_TICKS = 26


class B1AdmissionError(ValueError):
    """P07-B.1 resource rejection before any transfer or dispatch."""


@dataclass(frozen=True)
class B1OwnerMap:
    backing_base: int = BACKING_BASE
    backing_bytes: int = BACKING_BYTES
    core_count: int = CORE_COUNT
    record_bytes: int = RECORD_BYTES
    resident_slots: int = RESIDENT_SLOTS
    physical_engines: int = PHYSICAL_ENGINES

    def validate(self) -> None:
        vals = (self.backing_base, self.backing_bytes, self.core_count,
                self.record_bytes, self.resident_slots, self.physical_engines)
        if any(type(v) is not int for v in vals):
            raise B1AdmissionError("owner map requires integer resource fields")
        if self.backing_base != BACKING_BASE or self.backing_bytes != BACKING_BYTES:
            raise B1AdmissionError("not the accepted reserved P02 DDR window")
        if not 1 <= self.core_count <= 126:
            raise B1AdmissionError("logical core count exceeds P05-diagnostic capacity")
        if self.record_bytes != RECORD_BYTES or self.resident_slots != 3 or self.physical_engines != 1:
            raise B1AdmissionError("accepted physical resources changed")
        if self.backing_base % self.record_bytes:
            raise B1AdmissionError("misaligned backing base")
        if self.core_count * self.record_bytes > self.backing_bytes:
            raise B1AdmissionError("backing capacity exceeded")

    def address(self, core_id: int) -> int:
        self.validate()
        if type(core_id) is not int or not 0 <= core_id < self.core_count:
            raise B1AdmissionError("logical ID outside provisioned context set")
        start = self.backing_base + self.record_bytes * core_id
        if start + self.record_bytes > self.backing_base + self.backing_bytes:
            raise B1AdmissionError("core record escapes reserved backing window")
        return start


def ingress_length(route_count: int) -> int:
    """Maximum bounds only; B.2 will validate actual bytes against signed mapping."""
    if type(route_count) is not int or not 0 <= route_count <= INGRESS_MAX_ROUTES:
        raise B1AdmissionError("B1.3 route count outside v1 transport bounds")
    return INGRESS_HEADER_BYTES + INGRESS_ROUTE_BYTES * route_count + INGRESS_CHANNELS


def page_burst_counts(page_ins: int, dirty_page_outs: int) -> tuple[int, int]:
    """Model only; NOT a read of physical AXI page-engine counters."""
    if any(type(x) is not int or x < 0 or x > 0xFFFFFFFF for x in (page_ins, dirty_page_outs)):
        raise B1AdmissionError("invalid page operation count")
    return (page_ins * (PAGE_IN_BYTES // BURST_BYTES),
            dirty_page_outs * (PAGE_OUT_BYTES // BURST_BYTES))


def assert_source_contract() -> None:
    """Catch accidental planning/ABI drift against the actual accepted Python code."""
    from .ddr_abi import P02_DDR_CONTEXT_STRIDE_BYTES, P02_DDR_BACKING_REGION_BYTES
    from .hardware_p05 import P05_MAX_RESIDENT_CONTEXTS, P05_PHYSICAL_ENGINE_COUNT
    from .p06_b1_contract import (MAX_EVENTS_PER_BANK, MAX_PACKETS_PER_BANK,
                                  MAX_ROUTES, MAX_SYN_WORDS as SOURCE_MAX_SYN_WORDS,
                                  P05_DIAGNOSTIC_MAX_CORES)
    from .p06_b13_streaming import (B13_HEADER_BYTES, B13_INPUT_PIXELS_BYTES,
                                   B13_ROUTE_ENTRY_BYTES, B13_MAX_ROUTES)
    from .p06_input_contract import INPUT_TICKS as SOURCE_INPUT_TICKS, TOTAL_TICKS as SOURCE_TOTAL_TICKS
    from .p06_b15_paging import (P05_FULL_PAGE_IN_BYTES, P05_MUTABLE_PAGE_OUT_BYTES,
                                 P05_AXI_BURST_BYTES)
    if not (P02_DDR_CONTEXT_STRIDE_BYTES == RECORD_BYTES
            and P02_DDR_BACKING_REGION_BYTES == BACKING_BYTES
            and P05_MAX_RESIDENT_CONTEXTS == RESIDENT_SLOTS
            and P05_PHYSICAL_ENGINE_COUNT == PHYSICAL_ENGINES
            and MAX_EVENTS_PER_BANK == MAX_BANK_EVENTS
            and MAX_PACKETS_PER_BANK == MAX_PACKETS
            and MAX_ROUTES == MAX_ROUTES_PER_CORE
            and SOURCE_MAX_SYN_WORDS == MAX_SYN_WORDS
            and P05_DIAGNOSTIC_MAX_CORES == 126
            and B13_HEADER_BYTES == INGRESS_HEADER_BYTES
            and B13_INPUT_PIXELS_BYTES == INGRESS_CHANNELS
            and B13_ROUTE_ENTRY_BYTES == INGRESS_ROUTE_BYTES
            and B13_MAX_ROUTES == INGRESS_MAX_ROUTES
            and SOURCE_INPUT_TICKS == INPUT_TICKS
            and SOURCE_TOTAL_TICKS == TOTAL_TICKS
            and P05_FULL_PAGE_IN_BYTES == PAGE_IN_BYTES
            and P05_MUTABLE_PAGE_OUT_BYTES == PAGE_OUT_BYTES
            and P05_AXI_BURST_BYTES == BURST_BYTES):
        raise B1AdmissionError("drift from accepted source-level P02/P03/B1 ABI")
