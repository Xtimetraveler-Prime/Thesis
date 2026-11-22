"""Genuine AXI4-Lite protocol + M08.5 trusted CSR + real DMA lease fence.

Both owner verification and interconnect drain are synthetic TB pins. A PASS
establishes 5-channel source RTL behavior only; NOT privileged HPM0 path,
DDR, Linux DMA, FPGA placement/timing, or safe physical buffer release.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/m08"
FILES = tuple(RTL / name for name in (
    "m08_m085_kernel_dma_lease_fence.v",
    "m08_m085_trusted_control_abi.v",
    "m08_m085_axil_control_candidate.v",
    "tb_m08_m085_axil_control_candidate.sv",
))


class M085AXILControlCandidateTests(unittest.TestCase):
    def test_source_uses_independent_axil_handshakes_no_auto_trust(self):
        src = FILES[2].read_text(encoding="utf-8")
        tb = FILES[-1].read_text(encoding="utf-8")
        for expected in (
            "module m08_m085_axil_control_candidate",
            "m08_m085_trusted_control_abi",
            "s_axi_awready", "s_axi_wready", "s_axi_bvalid",
            "s_axi_arready", "s_axi_rvalid", "s_axi_rready",
            "aw_pending", "w_pending", "write_commit",
            "write_embargo", "admit_work=csr_admit && !write_embargo",
            "selected_addr[11:8]!=0 ? 8'hfc",
            "csr_trusted", "driver_bound_verified", "control_route_verified",
            "interconnect_drain_ack", "2'b10",
        ):
            self.assertIn(expected, src)
        self.assertIn("M08_5_AXIL_CONTROL_POSITIVE_PASS", tb)
        self.assertIn("M08_5_AXIL_CONTROL_NEGATIVE_PASS", tb)
        for forbidden in (
            "program_hw_devices", "open_hw_manager", "dma_alloc_coherent(",
            "/dev/mem", "0x40000000", "s_axi_awprot==",
            "s_axi_arprot==",
        ):
            self.assertNotIn(forbidden, src + tb)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "genuine iverilog/vvp required, no simulated fallback")
    def test_clocked_real_axil_csr_fence_positive_and_19_adverse_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "m085_axil.vvp"
            compile_result = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m08_m085_axil_control_candidate",
                 "-o", str(binary), *[str(p) for p in FILES]],
                text=True, capture_output=True, timeout=90
            )
            self.assertEqual(compile_result.returncode, 0,
                             compile_result.stdout + compile_result.stderr)
            self.assertEqual(compile_result.stderr.strip(), "",
                             "no RTL Icarus warnings accepted")
            for case in range(20):
                with self.subTest(case=case):
                    result = subprocess.run(
                        ["vvp", str(binary), f"+CASE={case}"],
                        text=True, capture_output=True, timeout=30
                    )
                    self.assertEqual(result.returncode, 0,
                                     f"case={case}\n{result.stdout}\n{result.stderr}")
                    self.assertEqual(result.stderr.strip(), "")
                    self.assertNotIn("FATAL", result.stdout)
                    marker = ("M08_5_AXIL_CONTROL_POSITIVE_PASS"
                              if case == 0 else
                              f"M08_5_AXIL_CONTROL_NEGATIVE_PASS case={case}")
                    self.assertEqual(result.stdout.count(marker), 1, result.stdout)


if __name__ == "__main__":
    unittest.main()
