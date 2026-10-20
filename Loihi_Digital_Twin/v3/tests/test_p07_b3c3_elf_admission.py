"""P07-B.3c3 declaration-only LOAD/heap/stack/buffer ownership checks.

No actual A53 ELF, board DDR probe, XSA or B2 official TEST is accessed.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/p07_b3c3_elf_admission.py"
spec = importlib.util.spec_from_file_location("p07_b3c3_elf_guard", SCRIPT)
assert spec is not None and spec.loader is not None
import sys
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _span(label, first, end):
    return module.Span(label, first, end)


def test_realistic_readelf_wide_load_headers_and_disjoint_linker_regions():
    sample = """
  LOAD           0x000000 0x0000000000100000 0x0000000000100000 0x000020 0x001000 R E 0x1000
  LOAD           0x001000 0x0000000000200000 0x0000000000200000 0x000010 0x000400 RW  0x1000
"""
    spans = module.parse_load_segments(sample)
    assert len(spans) == 2
    assert spans[0].first == 0x100000 and spans[0].end == 0x101000
    result = module.inspect(
        spans,
        _span("stack", 0x300000, 0x320000),
        _span("heap", 0x400000, 0x480000),
        (_span("buffer:packet", 0x500000, 0x520000),),
    )
    assert result["load_segments"] == 2
    assert result["physical_ddr_exclusivity"] == "UNVERIFIED"
    assert result["fpd128_live_shell"] == "UNVERIFIED"


@pytest.mark.parametrize("segment", [
    (0x3FFFFFFF, 0x40000001),    # overlaps lower backing byte
    (0x40000000, 0x40001000),    # core 0
    (0x40D00000, 0x40D80000),    # core 26
    (0x43F00000, 0x43FE0000),    # B1.3 staging
    (0x43FE0000, 0x43FE0100),    # descriptor
    (0x43FF0000, 0x44000000),    # result journal
    (0x43FFFFFF, 0x44000001),    # upper edge
    (0xA4000000, 0xA4001000),    # AXI-Lite MMIO
])
def test_frozen_owner_overlap_fails_closed(segment):
    with pytest.raises(ValueError, match="overlaps"):
        module.inspect(
            (_span("ELF LOAD", *segment),),
            _span("stack", 0x300000, 0x320000),
            _span("heap", 0x400000, 0x480000),
        )


def test_unverified_heap_or_stack_and_aliases_rejected():
    elf = (_span("ELF LOAD", 0x100000, 0x110000),)
    with pytest.raises(ValueError, match="mandatory"):
        module.inspect(elf, None, _span("heap", 0x400000, 0x500000))
    with pytest.raises(ValueError, match="mandatory"):
        module.inspect(elf, _span("stack", 0x300000, 0x310000), None)
    with pytest.raises(ValueError, match="overlaps"):
        module.inspect(elf, _span("stack", 0x100080, 0x101000),
                       _span("heap", 0x400000, 0x500000))
    with pytest.raises(ValueError, match="overlaps"):
        module.inspect(elf, _span("stack", 0x300000, 0x310000),
                       _span("heap", 0x400000, 0x500000),
                       (_span("buffer:sample", 0x480000, 0x510000),))


def test_invalid_declared_bounds_and_missing_loads():
    with pytest.raises(ValueError, match="nonempty"):
        _span("bad", 9, 9)
    with pytest.raises(ValueError, match="nonempty"):
        _span("overflow", (1 << 64) - 2, (1 << 64) + 1)
    with pytest.raises(ValueError, match="no nonempty LOAD"):
        module.parse_load_segments("Type Offset VirtAddr PhysAddr FileSiz MemSiz")
    with pytest.raises(ValueError, match="truncated LOAD"):
        module.parse_load_segments("LOAD 0x0 0x100000")
