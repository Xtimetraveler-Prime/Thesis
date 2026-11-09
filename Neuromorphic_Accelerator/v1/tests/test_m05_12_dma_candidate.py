"""M05.12c native synthetic audit tests and no-board runner checks.

DOES NOT invoke Vivado, instantiate real configured AXI DMA or use DDR/PS.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12_dma_candidate_audit import (
    PART, VLNV, SCOPE, ROLES, expected_config, expected_pins,
    verify_candidate_report,
)


def transcript():
    rows = [f"META|part|{PART}", f"META|vlnv|{VLNV}",
            f"META|scope|{SCOPE}"]
    for name, role in ROLES.items():
        rows.append(f"CELL|{name}|{role}")
        rows += [f"CFG|{name}|{k}|{v}"
                 for k, v in expected_config(role).items()]
        rows += [f"PIN|{name}|{k}|{v}"
                 for k, v in expected_pins(role).items()]
    return "\n".join(rows) + "\n"


class M0512DMACandidateTests(unittest.TestCase):
    def test_complete_four_direction_256b_24bit_direct_candidate(self):
        self.assertEqual(verify_candidate_report(transcript()), (3, 1))

    def test_wrong_width_length_mode_or_address_rejected(self):
        good = transcript()
        for field, correct, wrong in (
            ("c_m_axis_mm2s_tdata_width", "256", "32"),
            ("c_s_axis_s2mm_tdata_width", "256", "128"),
            ("c_m_axi_mm2s_data_width", "256", "32"),
            ("c_sg_length_width", "24", "14"),
            ("c_include_sg", "0", "1"),
            ("c_include_mm2s", "1", "0"),
            ("c_addr_width", "32", "64"),
            ("c_micro_dma", "0", "1"),
            ("c_include_mm2s_dre", "0", "1"),
            ("c_prmry_is_aclk_async", "0", "1"),
        ):
            with self.subTest(field=field):
                match = f"|{field}|{correct}\n"
                self.assertIn(match, good)
                with self.assertRaises(ValueError):
                    verify_candidate_report(good.replace(
                        match, f"|{field}|{wrong}\n", 1))

    def test_direction_pins_missing_wrong_or_duplicate_rejected(self):
        src = transcript()
        target = "PIN|dma_trace|S_AXIS_S2MM|1\n"
        for bad in (
            src.replace(target, "", 1),
            src.replace(target, target + target, 1),
            src.replace(target, "PIN|dma_trace|S_AXIS_S2MM|0\n", 1),
            src.replace(target, "PIN|dma_trace|M_AXIS_MM2S|1\n", 1),
        ):
            with self.subTest(bad=bad[-150:]):
                with self.assertRaises(ValueError):
                    verify_candidate_report(bad)

    def test_provenance_missing_extra_duplicate_or_reordered_rejected(self):
        good = transcript()
        first_cell = "CELL|dma_neurons|MM2S\n"
        for bad in (
            good.replace("META|part|", "META|device|", 1),
            good.replace(f"META|vlnv|{VLNV}", "META|vlnv|axi_dma:6.3"),
            good.replace(f"META|scope|{SCOPE}", "META|scope|PHYSICAL"),
            good.replace(first_cell, first_cell * 2, 1),
            good.replace(first_cell, "", 1),
            good + "CELL|dma_extra|MM2S\n",
            good.replace(first_cell, "CELL|dma_neurons|S2MM\n", 1),
            good[:-1],
            good.replace("CFG|dma_neurons|c_include_sg|0\n",
                         "CFG|dma_neurons|c_include_sg|0\n" * 2, 1),
        ):
            with self.subTest(bad=bad[:140]):
                with self.assertRaises(ValueError):
                    verify_candidate_report(bad)

    def test_cli_read_only_valid_and_missing_report_failure(self):
        with tempfile.TemporaryDirectory(prefix="m05_12c_") as td:
            report = Path(td) / "candidate.txt"
            original = transcript()
            report.write_text(original)
            cmd = [sys.executable,
                   str(ROOT / "scripts/m05_12_dma_candidate_audit.py"),
                   "--report", str(report)]
            ok = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("PASS: M05.12c independent", ok.stdout)
            self.assertEqual(report.read_text(), original)
            report.unlink()
            bad = subprocess.run(cmd, text=True, capture_output=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("ERROR:", bad.stderr)

    def test_runner_syntax_help_bad_arg_and_evidence_contract(self):
        shell = ROOT / "scripts/run_m05_12_dma_candidate.sh"
        syntax = subprocess.run(["bash", "-n", str(shell)],
                                text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        help_result = subprocess.run(["bash", str(shell), "--help"],
                                     text=True, capture_output=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("NO BOARD", help_result.stdout)
        bad = subprocess.run(["bash", str(shell), "--invalid"],
                             text=True, capture_output=True)
        self.assertEqual(bad.returncode, 2)
        src = shell.read_text()
        for term in ("mktemp -d", "source_sha256.txt", "result.txt",
                     "01_candidate.txt", "02_vivado.log",
                     "03_independent_audit.log", "-in_memory",
                     "vivado -mode batch", "xck26"):
            if term in ("-in_memory", "xck26"):
                continue  # These are in Tcl, not runner.
            self.assertIn(term, src)

    def test_read_only_clock_property_is_checked_not_written(self):
        # Original real Vivado 2025.2 run returned BD 41-737 (read-only).
        # A successful readback=0 remains a strict requirement.
        tcl = (ROOT / "scripts/m05_12_dma_candidate.tcl").read_text()
        cfg_line = next(line for line in tcl.splitlines()
                        if line.strip().startswith("set cfg [list "))
        self.assertNotIn("CONFIG.c_prmry_is_aclk_async", cfg_line)
        self.assertIn(
            "foreach {key wanted} [concat $cfg [list CONFIG.c_prmry_is_aclk_async 0]]",
            tcl,
        )
        self.assertIn("readback $key", tcl)

    def test_offline_tcl_has_strict_readback_and_no_hardware_actions(self):
        shell = (ROOT / "scripts/run_m05_12_dma_candidate.sh").read_text()
        tcl = (ROOT / "scripts/m05_12_dma_candidate.tcl").read_text()
        for term in ("create_project -in_memory", "create_bd_cell -type ip",
                     "set_property -dict $cfg $cell",
                     "get_property $key $cell",
                     "get_bd_intf_pins",
                     "xck26-sfvc784-2LV-c",
                     "xilinx.com:ip:axi_dma:7.1"):
            self.assertIn(term, tcl)
        for forbidden in (
            "program_hw_devices", "open_hw_target", "connect_hw_server",
            "launch_runs", "write_bitstream", "xsdb", "open_project",
            "open_bd_design", "assign_bd_address", "connect_bd_intf_net",
            "connect_bd_net", "write_hw_platform", "write_bd_tcl",
            "m05_rolling.cpp", "rm -rf",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, shell)
                self.assertNotIn(forbidden, tcl)


if __name__ == "__main__":
    unittest.main()
