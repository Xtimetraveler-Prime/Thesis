"""Synthetic offline regression for the P03.2c ILA/XSDB evidence parser."""

from __future__ import annotations

import csv
from pathlib import Path
import subprocess
import sys


UP = [
    "net_slot_0_axi_araddr[39:0]", "net_slot_0_axi_arvalid",
    "net_slot_0_axi_arready", "net_slot_0_axi_rdata[31:0]",
    "net_slot_0_axi_rvalid", "net_slot_0_axi_rready",
    "net_slot_0_axi_rresp[1:0]", "net_slot_0_axi_rlast",
    "net_slot_0_axi_arsize[2:0]",
]
DOWN = [
    "p03_ps_control_regs_0_p03_diag_araddr[31:0]",
    "p03_ps_control_regs_0_p03_diag_arvalid",
    "p03_ps_control_regs_0_p03_diag_arready",
    "p03_ps_control_regs_0_p03_diag_rdata[31:0]",
    "p03_ps_control_regs_0_p03_diag_rvalid",
    "p03_ps_control_regs_0_p03_diag_rready",
    "p03_ps_control_regs_0_p03_diag_rresp[0:0]",
]


def _csv(path: Path, columns: list[str], values: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["Sample in Buffer", "Sample in Window", "TRIGGER", *columns])
        writer.writerow(["Radix - UNSIGNED", "UNSIGNED", "UNSIGNED", *(["HEX"] * len(columns))])
        for index, value in enumerate(values):
            writer.writerow([index, index, int(index == 0), *value])


def _run(tmp_path: Path, bad_upstream: bool = False) -> subprocess.CompletedProcess[str]:
    upstream = tmp_path / "up.csv"
    downstream = tmp_path / "down.csv"
    xsdb = tmp_path / "xsdb.log"

    _csv(upstream, ["system_ila/inst/" + n for n in UP], [
        ["00a4000004", "1", "1", "00000000", "0", "1", "OKAY", "0", "4 bytes"],
        ["00a4000004", "0", "1",
         "00000000" if bad_upstream else "00010000", "1", "1", "OKAY", "1", "4 bytes"],
    ])
    _csv(downstream, ["design/" + n for n in DOWN], [
        ["a4000004", "1", "1", "00000000", "0", "1", "0"],
        # Invalid/inactive address changing must NOT count as a second request.
        ["a4000008", "0", "0", "00010000", "1", "1", "0"],
    ])
    xsdb.write_text(
        "P03_2C_ILA_READ_TARGET=PSU\n"
        "P03_2C_ILA_READ_ADDRESS=0xA4000004\n"
        "A4000004: 00000000\n",
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        [
            sys.executable, str(root / "scripts/p03_2c_analyze_ila_capture.py"),
            "--upstream", str(upstream), "--downstream", str(downstream),
            "--xsdb", str(xsdb),
        ],
        capture_output=True, text=True, check=False,
    )


def test_ila_analyzer_localizes_valid_pl_response_with_debugger_disagreement(tmp_path: Path):
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "PASS: PS-facing AXI4 AR sample=0" in result.stdout
    assert "PASS: MMIO-slave AXI4-Lite AR sample=0" in result.stdout
    assert "XSDB reported 0x00000000" in result.stdout
    assert "LOCALIZED:" in result.stdout


def test_ila_analyzer_rejects_wrong_ps_facing_axi_response(tmp_path: Path):
    result = _run(tmp_path, bad_upstream=True)
    assert result.returncode != 0
    assert "AssertionError" in result.stderr
