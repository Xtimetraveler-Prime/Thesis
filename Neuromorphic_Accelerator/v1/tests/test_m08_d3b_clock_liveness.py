"""Genuine Icarus regression for D3.2 unintegrated PL0 liveness hardware RTL.

This is first-party RTL, not PS FPD ATB/AIB, board clock proof, XSA
integration or actual KV260 boot. Missing Icarus is SKIP, never PASS.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DUT = ROOT / "rtl/m08/m08_d3b_clock_liveness_probe.v"
TB = ROOT / "rtl/m08/tb_m08_d3b_clock_liveness_probe.sv"
M08_BD = ROOT / "scripts/m08_page_ps_bd_candidate.tcl"
D3A_BD = ROOT / "scripts/m08_d3a_passive_fan_bd_candidate.tcl"
MARKERS = [
    "M08_D3B_LIVENESS_RUNNING_PL_EDGES_OBSERVED_PASS",
    "M08_D3B_LIVENESS_PL0_STOPS_INDEPENDENT_MONITOR_DETECTS_PASS",
    "M08_D3B_LIVENESS_RESUME_DOES_NOT_CLEAR_STICKY_POISON_PASS",
    "M08_D3B_LIVENESS_STOPPED_MONITOR_CLOCK_IS_UNPROTECTED_NEGATIVE_PASS",
    "M08_D3B_LIVENESS_GENUINE_RTL_ALL_PASS_NOT_PS_ATB_OR_PHYSICAL_CLOCK_PROOF",
]


class M08D3BClockLiveness(unittest.TestCase):
    def test_liveness_source_is_unintegrated_independent_clock_diagnostic(self):
        dut = DUT.read_text()
        tb = TB.read_text()
        self.assertIn("monitor_clock", dut)
        self.assertIn("input wire pl_clock", dut)
        self.assertIn('(* ASYNC_REG = "TRUE" *) reg sync_meta;', dut)
        self.assertIn('(* ASYNC_REG = "TRUE" *) reg sync_stage2;', dut)
        self.assertIn("clock_failure_sticky", dut)
        self.assertIn("clock_observed_alive <= 0", dut)
        self.assertIn("NOT INTEGRATED INTO VIVADO OR A BITSTREAM", dut)
        self.assertIn("does NOT supply ATB4 protection", dut)
        self.assertIn("monitor_running=0", tb)
        for unsafe in ("program_hw_devices", "/dev/mem", "/dev/uio",
                       "write_bitstream", "connect_bd_intf_net"):
            self.assertNotIn(unsafe, dut)
            self.assertNotIn(unsafe, tb)
        self.assertNotIn("m08_d3b_clock_liveness_probe",
                         M08_BD.read_text())
        self.assertNotIn("m08_d3b_clock_liveness_probe",
                         D3A_BD.read_text())

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus unavailable: no genuine D3B RTL simulation accepted")
    def test_native_icarus_first_party_pl0_liveness_and_negative(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "d3b_liveness.vvp"
            compiled = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m08_d3b_clock_liveness_probe",
                 "-o", str(output), str(DUT), str(TB)],
                capture_output=True, text=True, timeout=45, check=False)
            self.assertEqual(compiled.returncode, 0,
                             compiled.stdout + "\n" + compiled.stderr)
            self.assertEqual(compiled.stderr.strip(), "")
            ran = subprocess.run(["vvp", str(output)], capture_output=True,
                                 text=True, timeout=30, check=False)
            self.assertEqual(ran.returncode, 0, ran.stdout + "\n" + ran.stderr)
            self.assertEqual(ran.stderr.strip(), "")
            for mark in MARKERS:
                self.assertEqual(ran.stdout.splitlines().count(mark), 1,
                                 mark + "\n" + ran.stdout)


if __name__ == "__main__":
    unittest.main()
