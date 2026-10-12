"""P03.3b actual C hardware adapter compiled with a host-native AXI bus mock.

The mocked MMIO/DDR hooks are deliberately distinct from the physical
KV260 A53 integration; an offline PASS is NOT FPGA hardware acceptance.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ROOT / "software/p03/include"
SRC = ROOT / "software/p03"
HARNESS = ROOT / "tests/native/p03_3b_hw_adapter_harness.c"


def test_p03_3b_native_axi_hw_adapter(tmp_path: Path):
    cc = shutil.which("cc") or shutil.which("gcc")
    if cc is None:
        pytest.skip("Native C compiler unavailable")
    binary = tmp_path / "p03_3b_native"
    result = subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-O0", "-g", "-I", str(HEADERS),
        str(SRC / "p03_runtime.c"),
        str(SRC / "p03_hw_adapter.c"),
        str(SRC / "p03_hw_runtime_bridge.c"),
        str(HARNESS), "-o", str(binary),
    ], capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(
        [str(binary)], capture_output=True, text=True,
        timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for marker in (
        "PASS: P03.3b native MMIO page/debug/dispatch nonzero core and mutable save",
        "PASS: P03.3b resident/DDR NEXT packet delivery and timestep validation",
        "PASS: P03.3b packet capacity and page MMIO error fail closed",
        "PASS: P03.3b 2-step native policy-to-MMIO bridge",
        "PASS: P03.3b host-native hardware adapter suite",
    ):
        assert marker in result.stdout


def test_p03_3b_hw_contract_preserves_physical_mapping_and_fail_closed_delivery():
    header = (HEADERS / "p03_hw_adapter.h").read_text(encoding="utf-8")
    src = (SRC / "p03_hw_adapter.c").read_text(encoding="utf-8")
    bridge = (SRC / "p03_hw_runtime_bridge.c").read_text(encoding="utf-8")
    xilinx = (SRC / "p03_hw_xilinx_io.c").read_text(encoding="utf-8")
    for value in (
        "#define P03_HW_BACKING_BASE UINT64_C(0x40000000)",
        "#define P03_HW_RECORD_BYTES UINT64_C(0x00080000)",
        "#define P03_HW_EVENT0_DEBUG_BANK 6u",
        "#define P03_HW_EVENT1_DEBUG_BANK 9u",
        "#define P03_HW_PACKET_DEBUG_BANK 8u",
        "#define P03_HW_EVENT0_OFFSET UINT32_C(0x00054000)",
        "#define P03_HW_EVENT1_OFFSET UINT32_C(0x00058000)",
    ):
        assert value in header
    for value in (
        "P03_REG_PAGE_COMMAND",
        "P03_REG_DISPATCH_COMMAND",
        "P03_REG_DEBUG_COMMAND",
        "P03_REG_DISPATCH_PACKET_CNT",
        "P03_REG_DEBUG_RDATA0",
        "P03_HW_MUTABLE_BYTES",
        "source_comp",
        "target_step != timestep + 1u",
        "P03_HW_EVENT1_DEBUG_BANK",
        "P03_HW_EVENT1_OFFSET",
        "hw->event_counts[dest][next_bank] = (uint16_t)(count + 1u)",
        "hw->io.clean_range",
        "hw->io.invalidate_range",
    ):
        assert value in src
    assert "p03_hw_read_packet" in bridge
    assert "p03_hw_route_word" in bridge
    assert "p03_hw_quiescent" in bridge
    assert "Xil_In32(" in xilinx and "Xil_Out32(" in xilinx
    assert "Xil_DCacheFlushRange" in xilinx
    assert "Xil_DCacheInvalidateRange" in xilinx


def test_p03_3b_barrier_callback_receives_opaque_io_context():
    """Prevent omitted cookie args from silently reappearing between native runs."""
    header = (HEADERS / "p03_hw_adapter.h").read_text(encoding="utf-8")
    source = (SRC / "p03_hw_adapter.c").read_text(encoding="utf-8")
    assert "void (*barrier)(void *cookie);" in header
    assert "hw->io.barrier();" not in source
    assert source.count("hw->io.barrier(hw->cookie);") == 6
