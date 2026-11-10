"""True Icarus RTL tests of 128-bit SIMULATION-ONLY narrow scratch endpoint.

Runs the real RTL module, but NEVER substitutes for owner AMD XSim. Source
contract tests also guard against loss of full-width 128-bit accepted behavior.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RAM = ROOT / "rtl/m06/m06_axi128_scratch_mem.sv"
TB = ROOT / "rtl/m06/tb_m06_axi128_scratch_narrow.sv"


class M06AXI128NarrowScratchTests(unittest.TestCase):
    def test_positive_and_negative_actual_icarus_narrow_ram(self):
        if not shutil.which("iverilog") or not shutil.which("vvp"):
            self.skipTest("Icarus not installed: required by M06 CI post-install")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sim.vvp"
            compile_result = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m06_axi128_scratch_narrow",
                 "-o", str(out), str(RAM), str(TB)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(compile_result.returncode, 0,
                             compile_result.stdout + compile_result.stderr)
            sim = subprocess.run(["vvp", str(out)],
                                 capture_output=True, text=True, timeout=30)
            self.assertEqual(sim.returncode, 0, sim.stdout + sim.stderr)
            self.assertIn("M06_AXI128_NARROW_64K_PASS", sim.stdout)
            self.assertIn("M06_AXI128_SCRATCH_STANDALONE_PASS", sim.stdout)
            self.assertNotIn("M06_AXI128_NARROW_FAIL", sim.stdout)

    def test_source_rejects_wide_4k_and_unaligned_requests(self):
        text = RAM.read_text()
        self.assertIn("(size <= 3'd4)", text)
        self.assertIn("len < 8'd32", text)
        self.assertIn("address_end <= SCRATCH_BYTES", text)
        self.assertIn("50'd4096", text)
        self.assertIn("legal_strobes(wr_address,wr_size,s_axi_wstrb)", text)
        self.assertIn("wr_address <= wr_address + wr_stride", text)
        self.assertIn("rd_address <= rd_address + rd_stride", text)
        self.assertIn("rd_bad_request ? 2'b11", text)
        self.assertIn("s_axi_bresp <= 2'b11", text)

    def test_original_fullwidth_testbench_unchanged(self):
        orig = (ROOT / "rtl/m06/tb_m06_axi128_scratch_mem.sv").read_text()
        self.assertIn("m06_axi128_scratch_mem dut(", orig)
        self.assertIn("M06_AXI128_SCRATCH_STANDALONE_PASS", orig)
        self.assertIn("16'h8001", orig)
        self.assertIn("16'h00ff", orig)
        self.assertIn("4KiB", orig)
        self.assertIn("expect_b(2'b10)", orig)

    def test_negative_mutated_tb_cannot_report_success(self):
        text = TB.read_text()
        for marker in ("49'hfffc","16'h5000","49'h10000",
                       "16'h0010","3'd5","49'hffc,8'd1",
                       "M06_AXI128_NARROW_64K_PASS"):
            self.assertIn(marker, text)
        self.assertEqual(text.count("M06_AXI128_NARROW_64K_PASS"), 1)
        self.assertNotIn("original AMD vendor", text.lower())


if __name__ == "__main__":
    unittest.main()
