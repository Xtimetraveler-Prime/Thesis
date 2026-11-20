"""D3.D.2A: four-neuron real RTL/M02 PC-only regressions; NO BOARD."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_d3d2a_four_gate as gate
import m08_d3d2a_four_vectors as golden


class FourNeuronGateTests(unittest.TestCase):
    def test_source_gate_safe_and_present(self):
        result = gate.source()
        self.assertEqual(result["status"],
                         "M08_D3D2A_FOUR_NEURON_SOURCE_ACCEPTED_PC_ONLY_NO_NATIVE")
        self.assertFalse(result["hardware_executed"])
        self.assertFalse(result["synaptic_routing_proven"])

    def test_both_independent_m02_oracles_match_frozen_signals(self):
        self.assertEqual(len(golden.FIXTURES), 2)
        for f in golden.FIXTURES:
            result = golden.expected(f)
            self.assertEqual(result, golden.ANCHORS[f.name])
            fields = golden.format_fixture(f).split("|")
            self.assertEqual(len(fields), 55)
            self.assertEqual(fields[0], f.name)
            self.assertEqual(fields[1], golden.u32(f.nonce))
            self.assertEqual(fields[2], golden.u32(f.decay_mode))
            self.assertTrue(all(len(x) == 8 and x == x.upper() for x in fields[1:]))
        self.assertEqual(golden.ANCHORS["independent_half_decay"][1], (2, 1, 0, 0))
        self.assertEqual(golden.ANCHORS["independent_unit_decay"][1], (2, 1, 2, 0))

    def test_unique_pc_golden_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/"golden.txt"
            argv = [sys.executable, str(ROOT/"scripts/m08_d3d2a_four_vectors.py"),
                    "--out", str(out)]
            first = subprocess.run(argv, capture_output=True, text=True, timeout=25)
            self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
            self.assertIn("M08_D3D2A_M02_FOUR_NEURON_GOLDEN_PC_ONLY=",first.stdout)
            self.assertEqual(len(out.read_text().splitlines()), 4)
            before = out.read_bytes()
            second = subprocess.run(argv, capture_output=True, text=True, timeout=25)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(out.read_bytes(), before)

    def test_drc_fails_closed_on_unreviewed_warnings(self):
        with self.assertRaisesRegex(gate.Reject,"REVIEW_REQUIRED"):
            gate.inspect_new_drc("Checks found: 7\n")
        with self.assertRaisesRegex(gate.Reject,"unambiguous"):
            gate.inspect_new_drc("")
        with self.assertRaisesRegex(gate.Reject,"detail despite zero"):
            gate.inspect_new_drc(
                "Checks found: 0\nREQP-1858#1 Warning\n")
        self.assertEqual(gate.inspect_new_drc("Checks found: 0\n")["drc_checks"],0)

    def test_mutated_design_fails_source_gate(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td)/"broken.v"
            file.write_text(gate.RTL.read_text().replace(
                "membrane[neuron] <= next_voltage",
                "membrane[neuron] <= 16'd0"))
            with patch.object(gate, "RTL", file):
                with self.assertRaisesRegex(gate.Reject,"compute RTL missing"):
                    gate.source()

    def test_iverilog_four_neuron_2005_syntax(self):
        if shutil.which("iverilog") is None:
            self.skipTest("Icarus not installed here; owner/CI must run genuine RTL")
        with tempfile.TemporaryDirectory() as td:
            c = subprocess.run([
                "iverilog", "-g2005", "-s", "m08_d3d2a_four_lif_axil",
                "-o", str(Path(td)/"four.vvp"),
                str(ROOT/"rtl/m08/m08_d3d2a_four_lif_axil.v"),
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(c.returncode, 0, c.stdout+c.stderr)

    def test_iverilog_real_four_neuron_axi_and_arithmetic(self):
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            self.skipTest("Icarus not installed here; owner/CI must run genuine RTL")
        with tempfile.TemporaryDirectory() as td:
            binary = Path(td)/"test.vvp"
            c = subprocess.run([
                "iverilog","-g2012","-s","tb_m08_d3d2a_four_lif_axil",
                "-o",str(binary),
                str(ROOT/"rtl/m08/m08_d3d2a_four_lif_axil.v"),
                str(ROOT/"rtl/m08/tb_m08_d3d2a_four_lif_axil.sv"),
            ],capture_output=True,text=True,timeout=40)
            self.assertEqual(c.returncode,0,c.stdout+c.stderr)
            r = subprocess.run(["vvp",str(binary)],
                               capture_output=True,text=True,timeout=40)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            for token in (
                "M08_D3D2A_FOUR_NEURON_HALF_DECAY_PARITY_PASS",
                "M08_D3D2A_FOUR_NEURON_UNIT_DECAY_PARITY_PASS",
                "M08_D3D2A_AXIL_FOUR_NEURON_SOURCE_RTL_PASS",
            ):
                self.assertIn(token,r.stdout)


if __name__ == "__main__":
    unittest.main()
