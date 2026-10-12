"""P03.3b3 independent model fixture and strict two-core KV260 mailbox gates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "scripts/p03_3b3_verify_probe.py"
BUILD = ROOT / "scripts/build_p03_3b3_probe.sh"
RUN = ROOT / "scripts/run_p03_3b3_probe.sh"
PROBE = ROOT / "software/p03/p03_3b3_probe.c"
VITIS = ROOT / "software/p03/build_p03_3b3_probe.py"
PREPARE = ROOT / "vivado/p03_3b3_xsdb_prepare.tcl"
RUN_TCL = ROOT / "vivado/p03_3b3_xsdb_run.tcl"
FIXTURE = ROOT / "scripts/p03_3b3_packet_fixture.py"

FIELDS = (
    "magic", "version", "result", "error", "ps_width", "runtime_fault",
    "fault_phase", "dispatches", "barriers", "packets",
    "initial_page_ins", "page_ins", "page_outs", "page_operations",
    "last_page_bytes", "last_dispatch_count",
    "packet0_lo", "packet0_hi", "packet1_lo", "packet1_hi",
    "core1_ddr_event1", "core0_ddr_event0", "core1_resident_event1",
    "core1_config0", "timesteps", "last_bank", "core0_event0_count",
    "core1_event1_count", "global_status", "page_pending",
    "page_write_bursts", "page_read_bursts",
)


def fixture(tmp_path: Path) -> tuple[Path, dict]:
    dest = tmp_path / "fixture"
    p = subprocess.run(
        [sys.executable, str(FIXTURE), "--output-dir", str(dest)],
        env=__import__("os").environ | {"PYTHONPATH": str(ROOT / "src")},
        capture_output=True, text=True, check=False, timeout=40,
    )
    assert p.returncode == 0, p.stdout + p.stderr
    data = json.loads((dest / "manifest.json").read_text())
    return dest, data


def valid_words(info: dict) -> list[int]:
    p0 = int(info["first_packet"], 16)
    p1 = int(info["last_packet"], 16)
    return [
        0x50334233, 1, 0x600D600D, 0,
        0x00000A00, 0, 0, 4, 2, 2, 1, 3, 3, 7, 438272, 4,
        p0 & 0xFFFFFFFF, p0 >> 32, p1 & 0xFFFFFFFF, p1 >> 32,
        11, 20, 11, info["core1"]["config0"], 2, 0, 1, 0, 0, 0,
        100, 1712,
    ]


def verify(tmp_path: Path, data: dict, words: list[int]) -> subprocess.CompletedProcess:
    mbox = tmp_path / "test.bin"
    mbox.write_bytes(struct.pack("<32I", *words))
    return subprocess.run(
        [sys.executable, str(VERIFY),
         "--mailbox", str(mbox),
         "--manifest", str(tmp_path / "fixture" / "manifest.json")],
        capture_output=True, text=True, check=False, timeout=10,
    )


def test_two_model_derived_record_headers_and_sparse_axons(tmp_path: Path):
    folder, info = fixture(tmp_path)
    assert info["schema"] == "p03-3b3-directed-packet-page-roundtrip-v1"
    assert info["first_packet"] == "0x2000000020000581"
    assert int(info["last_packet"], 16) == (1 << 61) | (2 << 29) | (20 << 7)
    for core_id in (0, 1):
        record = (folder / f"core{core_id}_initial.bin").read_bytes()
        assert len(record) == 0x80000
        assert hashlib.sha256(record).hexdigest() == info[f"core{core_id}"]["sha256"]
        assert record[:8] == b"LTV3CTX1"
        assert struct.unpack_from("<I", record, 20)[0] == core_id
        assert struct.unpack_from("<I", record, 44)[0] == (1 if core_id == 0 else 0)
    c0 = (folder / "core0_initial.bin").read_bytes()
    assert struct.unpack_from("<I", c0, 0x54000)[0] == 10
    c1 = (folder / "core1_initial.bin").read_bytes()
    assert struct.unpack_from("<I", c1, 0x58000)[0] == 0
    assert len((folder / "mailbox_zero.bin").read_bytes()) == 128


def test_expected_mailbox_pass_and_each_failing_gate(tmp_path: Path):
    _, info = fixture(tmp_path)
    good = valid_words(info)
    assert len(good) == 32
    passed = verify(tmp_path, info, good)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert "PASS: P03.3b3 physical packet/page roundtrip" in passed.stdout
    for idx, invalid in (
        (2, 0xDEAD0008), (5, 7), (7, 3), (8, 1), (9, 1),
        (11, 2), (12, 2), (13, 6), (16, 0), (18, 0),
        (20, 0), (21, 10), (22, 0), (24, 1), (28, 2),
        (30, 0), (31, 0),
    ):
        bad = list(good)
        bad[idx] = invalid
        failed = verify(tmp_path, info, bad)
        assert failed.returncode != 0, (idx, failed.stdout, failed.stderr)
        assert "FAIL: P03.3b3" in failed.stderr


def test_vitis_sources_and_hardware_provisioning_guarded():
    vitis = VITIS.read_text()
    build = BUILD.read_text()
    run = RUN.read_text()
    probe = PROBE.read_text()
    prep = PREPARE.read_text()
    run_tcl = RUN_TCL.read_text()
    for name in (
        "p03_3b3_probe.c", "p03_runtime.c", "p03_hw_adapter.c",
        "p03_hw_runtime_bridge.c", "p03_hw_xilinx_io.c",
        "p03_3b3_fixture.h",
    ):
        assert name in vitis
        assert name in build
    for requirement in (
        "p03_rt_execute(&runtime,&ops,&bridge)",
        "p03_hw_read_packet(&hw,slot,0,&packet)",
        "real_drain(ctx,src,emitted,step,next_bank,committed)",
        "p03_hw_register_axon(&hw,0,20)",
        "P03_REG_PAGE_COMPLETED", "M_CORE1_DDR_EVENT1",
        "M_CORE0_DDR_EVENT0", "B3_ERR_RUNTIME",
    ):
        assert requirement in probe
    for token in (
        "p03_hpm0_data_width_bits=128",
        "p03_hpm0_transport=smartconnect_width_protocol",
        "P03_2C_EXPECTED_XSA_SHA",
        "P03_DIAG_REPORTS",
        "FAIL: ELF overlaps reserved DDR",
    ):
        assert token in build
    assert "p03_3b3_packet_fixture.py" in build
    assert "p03_3b3_xsdb_prepare.tcl" in run
    assert "p03_3b3_xsdb_run.tcl" in run
    assert "p03_3b3_verify_probe.py" in run
    assert "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128" in run
    assert "artifact_identity.txt" in run
    assert "core1_initial.bin" in run and "core0_initial.bin" in run
    assert "mrd -bin -file $verify_record $record_addr 131072" in prep
    assert "mrd -bin -file $mailbox_dump 0x43FF0000 32" in run_tcl
    assert "rm -rf" not in build and "rm -rf" not in run


def test_b3_a53_c_sources_pass_host_syntax_with_xilinx_bsp_shim(tmp_path: Path):
    """Catch A53 C source type/signature errors before expensive Vitis build.

    The shim only supplies header declarations. No FPGA behavior is simulated,
    and the ARM-specific wfe/dsb instructions are not assembled (-fsyntax-only).
    """
    import shutil
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        return  # Vitis still independently compiles on the user's machine
    folder, _ = fixture(tmp_path)
    xil_io = tmp_path / "xil_io.h"
    xil_io.write_text(
        "#ifndef TEST_XIL_IO_H\\n#define TEST_XIL_IO_H\\n"
        "#include <stdint.h>\\n"
        "typedef uintptr_t UINTPTR;\\ntypedef intptr_t INTPTR;\\n"
        "typedef unsigned int u32;\\n"
        "static inline uint32_t Xil_In32(UINTPTR addr)"
        "{(void)addr;return 0;}\\n"
        "static inline void Xil_Out32(UINTPTR addr, uint32_t val)"
        "{(void)addr;(void)val;}\\n"
        "#endif\\n"
    )
    (tmp_path / "xil_cache.h").write_text(
        "#ifndef TEST_XIL_CACHE_H\\n#define TEST_XIL_CACHE_H\\n"
        "#include \"xil_io.h\"\\n"
        "static inline void Xil_DCacheFlushRange(INTPTR addr, u32 size)"
        "{(void)addr;(void)size;}\\n"
        "static inline void Xil_DCacheInvalidateRange(INTPTR addr, u32 size)"
        "{(void)addr;(void)size;}\\n"
        "#endif\\n"
    )
    sources = (
        PROBE,
        ROOT / "software/p03/p03_runtime.c",
        ROOT / "software/p03/p03_hw_adapter.c",
        ROOT / "software/p03/p03_hw_runtime_bridge.c",
        ROOT / "software/p03/p03_hw_xilinx_io.c",
    )
    for source in sources:
        result = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
             "-fsyntax-only", "-I", str(tmp_path),
             "-I", str(ROOT / "software/p03/include"),
             "-I", str(folder), str(source)],
            capture_output=True, text=True, check=False, timeout=20,
        )
        assert result.returncode == 0, (
            str(source) + ": " + result.stdout + result.stderr
        )


def test_b3_build_and_board_scripts_parse_in_bash():
    for shell in (BUILD, RUN):
        result = subprocess.run(
            ["bash", "-n", str(shell)],
            capture_output=True, text=True, check=False, timeout=10,
        )
        assert result.returncode == 0, result.stderr
