"""FPGA-v3 P03 PS-visible MMIO register contract."""

from __future__ import annotations
from dataclasses import dataclass

P03_MMIO_BASE = 0xA4000000
P03_MMIO_RANGE_BYTES = 0x1000
P03_MMIO_ID = 0x4C543302
P03_MMIO_VERSION = 0x00010000

REG_ID = 0x000
REG_VERSION = 0x004
REG_CAPABILITIES = 0x008
REG_GLOBAL_STATUS = 0x00C

REG_PAGE_CONFIG = 0x020
REG_PAGE_BASE_LO = 0x024
REG_PAGE_BASE_HI = 0x028
REG_PAGE_COMMAND = 0x02C
REG_PAGE_STATUS = 0x030
REG_PAGE_BYTES = 0x034
REG_PAGE_COMPLETED = 0x038
REG_PAGE_CYCLES_LO = 0x03C
REG_PAGE_CYCLES_HI = 0x040
REG_PAGE_READ_BURSTS = 0x044
REG_PAGE_WRITE_BURSTS = 0x048
REG_PAGE_AXI_BYTES_LO = 0x04C
REG_PAGE_AXI_BYTES_HI = 0x050
REG_PAGE_PENDING_BYTES = 0x054

REG_DISPATCH_CONFIG = 0x080
REG_DISPATCH_META_LO = 0x084
REG_DISPATCH_META_HI = 0x088
REG_DISPATCH_TIMESTEP = 0x08C
REG_DISPATCH_COMMAND = 0x090
REG_DISPATCH_STATUS = 0x094
REG_DISPATCH_PACKET_CNT = 0x098
REG_DISPATCH_CORE_STATUS = 0x09C
REG_DISPATCH_COMPLETED = 0x0A0
REG_DISPATCH_CYCLES_LO = 0x0A4
REG_DISPATCH_CYCLES_HI = 0x0A8
REG_DISPATCH_ACTIVE = 0x0AC

REG_DEBUG_CONFIG = 0x100
REG_DEBUG_ADDR = 0x104
REG_DEBUG_COMMAND = 0x108
REG_DEBUG_STATUS = 0x10C
REG_DEBUG_WDATA0 = 0x110
REG_DEBUG_RDATA0 = 0x130

CMD_START = 1 << 0
CMD_CLEAR_DONE = 1 << 1


@dataclass(frozen=True, slots=True)
class PageCommand:
    page_out: bool
    mutable_only: bool
    resident_slot: int
    record_base: int

    def config_word(self) -> int:
        if not 0 <= self.resident_slot < 3:
            raise ValueError("resident_slot must be in [0, 2]")
        if self.record_base & 0x7FFFF:
            raise ValueError("record_base must be 512-KiB aligned")
        return (
            int(self.page_out)
            | (int(self.mutable_only) << 1)
            | (self.resident_slot << 8)
        )


@dataclass(frozen=True, slots=True)
class DispatchCommand:
    resident_slot: int
    metadata: int
    timestep: int
    event_read_bank: int

    def config_word(self) -> int:
        if not 0 <= self.resident_slot < 3:
            raise ValueError("resident_slot must be in [0, 2]")
        if self.event_read_bank not in (0, 1):
            raise ValueError("event_read_bank must be 0 or 1")
        if not 0 <= self.metadata < (1 << 64):
            raise ValueError("metadata must fit 64 bits")
        if not 0 <= self.timestep < (1 << 32):
            raise ValueError("timestep must fit 32 bits")
        return self.resident_slot | (self.event_read_bank << 8)


@dataclass(frozen=True, slots=True)
class ResidentMemoryCommand:
    write: bool
    resident_slot: int
    bank: int
    address: int

    def config_word(self) -> int:
        if not 0 <= self.resident_slot < 3:
            raise ValueError("resident_slot must be in [0, 2]")
        if not 0 <= self.bank < 16:
            raise ValueError("bank must fit 4 bits")
        if not 0 <= self.address < (1 << 15):
            raise ValueError("address must fit 15 bits")
        return (
            int(self.write)
            | (self.resident_slot << 8)
            | (self.bank << 12)
        )
