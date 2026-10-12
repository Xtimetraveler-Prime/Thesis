"""Offline regression for isolated P03.3b2 A53 probe + evidence validation."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts/p03_3b2_verify_probe.py"
BUILD = ROOT / "scripts/build_p03_3b2_probe.sh"
RUN = ROOT / "scripts/run_p03_3b2_probe.sh"
VITIS = ROOT / "software/p03/build_p03_3b2_probe.py"
PROBE = ROOT / "software/p03/p03_3b2_probe.c"


def mailbox_words(**changes: int) -> list[int]:
    record = {
        "magic": 0x50333342,
        "schema": 1,
        "result": 0x600D600D,
        "fail_code": 0,
        "mmio_id": 0x4C543302,
        "mmio_version": 0x00010000,
        "capabilities": 0x0001031F,
        "ps_width_raw": 0x00000A00,
        "resident_config0": 0x14001000,
        "page_bytes": 438272,
        "pages_completed": 1,
        "dispatches_completed": 2,
        "logical_dispatches": 2,
        "barriers": 2,
        "initial_page_ins": 1,
        "runtime_fault": 0,
    }
    record.update(changes)
    return list(record.values())


def check(tmp_path: Path, data: bytes) -> subprocess.CompletedProcess[str]:
    mailbox = tmp_path / "mailbox.bin"
    manifest = tmp_path / "manifest.json"
    mailbox.write_bytes(data)
    manifest.write_text(json.dumps({"expected_config0": "0x14001000"}))
    return subprocess.run(
        [sys.executable, str(VERIFY), "--mailbox", str(mailbox),
         "--manifest", str(manifest)],
        capture_output=True, text=True, check=False,
    )


def test_synthetic_realistic_mailbox_pass(tmp_path: Path):
    result = check(tmp_path, struct.pack("<16I", *mailbox_words()))
    assert result.returncode == 0, result.stderr
    assert "PASS: P03.3b2 physical A53 adapter probe" in result.stdout
    assert "dispatches=2" in result.stdout
    assert "barriers=2" in result.stdout


def test_synthetic_mailbox_wrong_event_barrier_or_width_is_rejected(tmp_path: Path):
    for invalid in (
        {"barriers": 1},
        {"ps_width_raw": 0x00000100},
        {"runtime_fault": 11},
        {"page_bytes": 438271},
        {"resident_config0": 0},
        {"result": 0xDEAD0008, "fail_code": 8},
    ):
        result = check(tmp_path, struct.pack("<16I", *mailbox_words(**invalid)))
        assert result.returncode != 0, invalid
        assert "FAIL: P03.3b2" in result.stderr


def test_invalid_mailbox_length_rejected(tmp_path: Path):
    result = check(tmp_path, b"\x00" * 60)
    assert result.returncode != 0
    assert "size 60 != 64" in result.stderr


def test_probe_links_actual_c_scheduler_adapter_and_records_real_results():
    c = PROBE.read_text()
    required = (
        "p03_rt_execute(&runtime, &runtime_ops, &bridge)",
        "p03_hw_bind_runtime(&bridge, &runtime_ops)",
        "p03_hw_xilinx_fpd128_ready()",
        "p03_hw_register_core(&adapter, 0, P03_SMOKE_DISPATCH_METADATA",
        "p03_hw_debug_word(hw, 0, P03_HW_CONFIG_DEBUG_BANK, 0, 0, data)",
        "P03_SMOKE_EXPECT_CONFIG0",
        "P03_SMOKE_EXPECT_PAGE_BYTES",
        "P03_REG_PAGE_COMPLETED",
        "P03_REG_DISPATCH_COMPLETED",
        "rt->counters.logical_dispatches != 2u",
        "rt->counters.barriers != 2u",
        "P03_SMOKE_MAILBOX_BASE",
        "Xil_DCacheFlushRange",
        "Xil_DCacheInvalidateRange",
    )
    for fragment in required:
        assert fragment in c
    assert "p03_hw_route_word(" not in c  # test targets no-packet baseline


def test_vitis_builder_compiles_every_required_source_in_new_directory():
    builder = VITIS.read_text()
    for file in (
        "p03_3b2_probe.c", "p03_runtime.c", "p03_hw_adapter.c",
        "p03_hw_runtime_bridge.c", "p03_hw_xilinx_io.c",
        "p03_hw_adapter.h", "p03_hw_runtime_bridge.h",
        "p03_hw_xilinx_io.h", "p03_mmio.h",
        "p03_2c_fixture.h",
    ):
        assert f'"{file}"' in builder
    assert 'files=[*source_set, *header_set]' in builder
    assert 'name=app_name' in builder
    assert 'no_boot_bsp=True' in builder


def test_build_and_hardware_runner_guard_accepted_fpd128_and_ddr():
    build = BUILD.read_text()
    run = RUN.read_text()
    for c in (build, run):
        for token in (
            "p03_hpm0_data_width_bits=128",
            "p03_hpm0_transport=smartconnect_width_protocol",
            "p03_mmio_base=0xA4000000",
            "P03_2C_EXPECTED_XSA_SHA",
            "P03_DIAG_REPORTS",
            "sha256sum",
        ):
            assert token in c
    assert 'if [[ -e "$BUILD_DIR" ]]' in build
    assert 'FAIL: ELF overlaps reserved DDR' in build
    assert 'if [[ "$VERIFY_EXIT" != 0 ]]' in run
    assert "p03_2c_xsdb_ps_axi_width_diag.tcl" in run
    assert "p03_2c_xsdb_prepare.tcl" in run
    assert "p03_2c_program_bitstream.tcl" in run
    assert "p03_2c_xsdb_run.tcl" in run
    assert "p03_3b2_verify_probe.py" in run
    assert "artifact_identity.txt" in run
    assert "rm -rf" not in build and "rm -rf" not in run
