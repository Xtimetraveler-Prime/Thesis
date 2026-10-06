from __future__ import annotations

import pytest

from loihi_twin_v2.p03_mmio import (
    CMD_CLEAR_DONE,
    CMD_START,
    P03_MMIO_BASE,
    P03_MMIO_ID,
    P03_MMIO_RANGE_BYTES,
    P03_MMIO_VERSION,
    DispatchCommand,
    PageCommand,
    ResidentMemoryCommand,
)


def test_p03_2_mmio_identity_and_window_are_frozen():
    assert P03_MMIO_BASE == 0xA0000000
    assert P03_MMIO_RANGE_BYTES == 0x1000
    assert P03_MMIO_ID == 0x4C543302
    assert P03_MMIO_VERSION == 0x00010000
    assert CMD_START == 0x1
    assert CMD_CLEAR_DONE == 0x2


def test_p03_2_page_command_packing():
    command = PageCommand(
        page_out=True,
        mutable_only=True,
        resident_slot=2,
        record_base=0x40180000,
    )
    assert command.config_word() == 0x00000203


def test_p03_2_page_command_rejects_bad_slot_or_alignment():
    with pytest.raises(ValueError):
        PageCommand(False, False, 3, 0x40000000).config_word()
    with pytest.raises(ValueError):
        PageCommand(False, False, 0, 0x40001000).config_word()


def test_p03_2_dispatch_command_packing():
    command = DispatchCommand(
        resident_slot=1,
        metadata=0x0123456789ABCDEF,
        timestep=42,
        event_read_bank=1,
    )
    assert command.config_word() == 0x00000101


def test_p03_2_resident_memory_command_packing():
    read = ResidentMemoryCommand(
        write=False,
        resident_slot=2,
        bank=5,
        address=17,
    )
    write = ResidentMemoryCommand(
        write=True,
        resident_slot=1,
        bank=3,
        address=21,
    )
    assert read.config_word() == 0x00005200
    assert write.config_word() == 0x00003101
