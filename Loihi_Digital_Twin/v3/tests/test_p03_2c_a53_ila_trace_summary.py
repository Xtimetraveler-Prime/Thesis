"""Regression for A53 MMIO ILA CSV handshake summary against a DDR mailbox."""

import csv
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _write_csv(path: Path, names: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Sample in Buffer", "Sample in Window", "TRIGGER", *names])
        writer.writerow(["Radix - UNSIGNED", "UNSIGNED", "UNSIGNED", *(["HEX"] * len(names))])
        for i, values in enumerate(rows):
            writer.writerow([i, i, int(i == 0), *values])


def test_a53_ila_summary_recovers_request_and_correct_data_in_spite_of_bad_mailbox(tmp_path: Path):
    pre = "loihi_twin_v3_p03_mmio_impl_i/"
    up = [
        "system_ila_0/inst/net_slot_0_axi_araddr[39:0]",
        "system_ila_0/inst/net_slot_0_axi_arsize[2:0]",
        "system_ila_0/inst/net_slot_0_axi_arvalid",
        "system_ila_0/inst/net_slot_0_axi_arready",
        "system_ila_0/inst/net_slot_0_axi_rdata[31:0]",
        "system_ila_0/inst/net_slot_0_axi_rresp[1:0]",
        "system_ila_0/inst/net_slot_0_axi_rvalid",
        "system_ila_0/inst/net_slot_0_axi_rready",
    ]
    down = [
        "p03_ps_control_regs_0_p03_diag_araddr[31:0]",
        "p03_ps_control_regs_0_p03_diag_arvalid",
        "p03_ps_control_regs_0_p03_diag_arready",
        "p03_ps_control_regs_0_p03_diag_rdata[31:0]",
        "p03_ps_control_regs_0_p03_diag_rresp[0:0]",
        "p03_ps_control_regs_0_p03_diag_rvalid",
        "p03_ps_control_regs_0_p03_diag_rready",
    ]
    _write_csv(tmp_path / "p03_2c_hpm0_capture.csv", [pre + x for x in up], [
        ["0080000004", "4 bytes", "1", "1", "00000000", "OKAY", "0", "1"],
        ["0080000004", "4 bytes", "0", "1", "00010000", "OKAY", "1", "1"],
    ])
    _write_csv(tmp_path / "p03_2c_mmio_slave_capture.csv",
               [pre + x for x in down], [
        ["80000004", "1", "1", "00000000", "0", "0", "1"],
        ["80000008", "0", "0", "00010000", "0", "1", "1"],
    ])
    actual = (0x4C543302, 0, 0, 0)
    words = (
        0x50335244, 1, 0xDEAD0001, 4, *actual,
        0x4C543302, 0x00010000, 0x0001031F, 0xD1A60018,
        1, 0xC0DEF00D, 0x80000000, 0x43FF0000,
    )
    (tmp_path / "p03_2c_a53_readonly_mailbox.bin").write_bytes(
        struct.pack("<16I", *words)
    )
    cmd = [
        sys.executable, str(ROOT / "scripts/p03_2c_summarize_a53_ila.py"),
        "--capture-dir", str(tmp_path), "--base", "0x80000000",
    ]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "addr=0x80000004" in result.stdout
    assert "data=0x00010000" in result.stdout
    assert "value=0x00000000, expected=0x00010000" in result.stdout
    assert "address not fully observed" in result.stdout


def test_a53_capture_wrapper_requires_matching_built_elf_base():
    s = (ROOT / "scripts/run_p03_2c_a53_ila_capture.sh").read_text(encoding="utf-8")
    assert "existing A53 ELF source was not built for MMIO base" in s
    assert "P03_READONLY_MMIO_BASE" in s
    assert "P03_2C_A53_ILA_EVIDENCE_DIR=" in s
