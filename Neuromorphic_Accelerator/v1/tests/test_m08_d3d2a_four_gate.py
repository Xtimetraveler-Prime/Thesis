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

    @staticmethod
    def reviewed_report() -> str:
        # Synthetic clone of owner-reviewed warning classes/hierarchy.
        # A positive UNIT test does not substitute for original owner file.
        header = (
            "Vivado v.2025.2\n"
            "Design       : m08_d3d2a_four_lif_jtag_wrapper\n"
            "Device       : xck26-sfvc784-2LV-c\n"
            "Design State : Fully Routed\n"
            "Checks found: 7\n"
        )
        for code, (count, desc) in gate.d3c.VENDOR_DRC_PROFILE.items():
            header += f"| {code} | Warning | {desc} | {count} |\n"
        for idx, (pin, path, conn) in enumerate((
            ("A2", "temp_curid[31]_i_1", "I1"),
            ("A4", "temp_curid[31]_i_1", "I0"),
            ("A5", "id_state[0]_i_1", "I0"),
        ), 1):
            header += (f"PDCN-1569#{idx} Warning\nLUT equation term check\n"
                       f"Used physical LUT pin '{pin}' of cell dbg_hub/inst/"
                       f"xsdb/{path} (pin dbg_hub/inst/xsdb/{path}/{conn}) "
                       "is not included in the LUT equation.\n"
                       "Related violations: <none>\n")
        for code, idx, name, desc in (
            ("REQP-1857", 1, "rx_fifo_i", "RAMB18E2_writefirst_collision_advisory"),
            ("REQP-1858", 1, "rd_cmd_fifo_i", "RAMB36E2_writefirst_collision_advisory"),
            ("REQP-1858", 2, "wr_cmd_fifo_i", "RAMB36E2_writefirst_collision_advisory"),
        ):
            header += (f"{code}#{idx} Warning\n{desc}\n"
                       f"Synchronous clocking for BRAM ({gate.NEW_JTAG_INSTANCE}"
                       f"/jtag_axi/inst/jtag_axi_engine_u/{name}/inst) in SDP "
                       "mode with WRITE_FIRST write-mode; possible address collisions.\n"
                       "Related violations: <none>\n")
        header += ("RTSTAT-10#1 Warning\nNo routable loads\n"
                   "39 net(s) have no routable loads. The problem bus(es) "
                   "and/or net(s) are " + ",\n".join(gate.REVIEWED_15) +
                   "\n (the first 15 of 37 listed).\n"
                   "Related violations: <none>\n")
        return header

    def test_drc_requires_precise_original_debug_paths(self):
        report = self.reviewed_report()
        result = gate.inspect_new_drc(report)
        self.assertEqual(result["drc_checks"], 7)
        self.assertEqual(result["rtstat_sampled_paths"], 15)
        for mutated in (
            report.replace("Checks found: 7", "Checks found: 8"),
            report.replace("| PDCN-1569 | Warning |", "| PDCN-1569 | Error |"),
            report.replace("rx_fifo_i", "user_logic_fifo", 1),
            report.replace("rd_cmd_fifo_i", "user_logic_fifo", 1),
            report.replace("wr_cmd_fifo_i", "user_logic_fifo", 1),
            report.replace(gate.REVIEWED_15[7], "fabric/neuron_bad_signal", 1),
            report.replace("first 15 of 37", "first 15 of 38"),
            report.replace("39 net(s)", "40 net(s)"),
            report.replace("PDCN-1569#3 Warning", "PDCN-1569#3 Error"),
            report.replace("Related violations: <none>", "Related violations: new"),
            report.replace("Design       : m08_d3d2a_four_lif_jtag_wrapper",
                           "Design       : forged_wrapper"),
        ):
            with self.subTest(mutated=mutated[:100]):
                with self.assertRaises(gate.Reject):
                    gate.inspect_new_drc(mutated)

    def test_owner_native_source_hashes_match_checked_in_source(self):
        # Independent provenance: source must be exact bytes accepted in the
        # genuine routed owner build; otherwise NO JTAG program is permitted.
        hashes = gate.source()
        self.assertEqual(hashes["builder_sha256"],gate.OWNER_ORIGINAL_BUILDER_SHA)
        self.assertEqual(hashes["lif_rtl_sha256"],gate.OWNER_ORIGINAL_LIF_SHA)
        self.assertEqual(gate.ORIGINAL_OWNER_BIT_BYTES, 7797843)
        self.assertEqual(
            gate.ORIGINAL_OWNER_BIT_SHA,
            "3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411")

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
