"""M08 D3.2 full AR/R + AW/W/B abstract fault scoreboard (NO BOARD)."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "rtl/m08/tb_m08_d3b_axi_fault_scoreboard.sv"
BD = ROOT / "scripts/m08_d3a_passive_fan_bd_candidate.tcl"
ORIGINAL = ROOT / "scripts/m08_page_ps_bd_candidate.tcl"
OPERATOR = ROOT / "scripts/m08_kv260_physical_uio_operator.py"
MARKERS = (
    "M08_D3_2_AXI_READ_WRITE_SPLIT_CHANNEL_DRAIN_PASS",
    "M08_D3_2_AXI_SYNTHETIC_SLVERR_WITH_ORPHAN_AR_REJECTED_NEGATIVE",
    "M08_D3_2_AXI_LATE_R_DRAIN_NO_AUTO_RECOVERY_PASS",
    "M08_D3_2_AXI_AW_W_B_PARTIAL_AND_LATE_B_CONTAINMENT_PASS",
    "M08_D3_2_AXI_UNSOLICITED_R_B_REJECTED_NEGATIVE",
    "M08_D3_2_AXI_CONCURRENT_OUTSTANDING_NOT_SAFE_TO_ISOLATE_PASS",
    "M08_D3_2_AXI_TRACKING_CAPACITY_EXCEEDED_NEGATIVE_PASS",
    "M08_D3_2_AXI_R_B_BACKPRESSURE_INSTABILITY_REJECTED_NEGATIVE",
    "M08_D3_2_AXI_STOPPED_PL_CLOCK_OUTSTANDING_REMAINS_NEGATIVE",
    "M08_D3_2_AXI_STOPPED_PS_CLOCK_UNPROTECTED_NEGATIVE",
    "M08_D3_2_AXI_ABSTRACT_BFM_ALL_PASS_NOT_VENDOR_ATB_AIB_OR_BOARD",
)


class AXIFaultScoreboard(unittest.TestCase):
    def test_no_new_axi_path_or_quarantine_regression(self):
        source = TB.read_text()
        self.assertIn("ABSTRACT PS-clock AXI-Lite AR/R + AW/W/B", source)
        self.assertIn("NOT SYNTHESIZABLE PS ATB", source)
        self.assertIn("A synthetic upstream error DOES NOT cancel", source)
        self.assertIn("simulated full platform restart", source)
        self.assertIn("wire locally_drained", source)
        self.assertIn("if (isolation_request && (!locally_drained", source)
        self.assertIn("if (pending_aw == 0 || pending_w == 0)", source)
        self.assertIn("ps_clock_running=0", source)
        self.assertIn("pl_clock_running=0", source)
        self.assertIn("reject_quarantined_mmio_mode(args.mode)", OPERATOR.read_text())
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP0 0", BD.read_text())
        self.assertNotIn("m08_d3b_abstract_axi_scoreboard", ORIGINAL.read_text())
        for disallowed in ("/dev/uio", "/dev/mem", "program_hw_devices",
                           "write_bitstream", "xmutil ", "ssh "):
            self.assertNotIn(disallowed, source)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus unavailable: HDL scoreboard cannot be claimed PASS")
    def test_real_icarus_protocol_scenarios_and_negatives(self):
        with tempfile.TemporaryDirectory() as d:
            vvp = Path(d) / "m08_d3b_axi_scoreboard.vvp"
            compile_run = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m08_d3b_axi_fault_scoreboard",
                 "-o", str(vvp), str(TB)],
                capture_output=True, text=True, timeout=60, check=False)
            self.assertEqual(compile_run.returncode, 0,
                             compile_run.stdout + "\n" + compile_run.stderr)
            self.assertEqual(compile_run.stderr.strip(), "", "Icarus warning requires review")
            actual = subprocess.run(["vvp", str(vvp)], capture_output=True,
                                    text=True, timeout=45, check=False)
            self.assertEqual(actual.returncode, 0,
                             actual.stdout + "\n" + actual.stderr)
            self.assertEqual(actual.stderr.strip(), "")
            self.assertNotIn("FATAL", actual.stdout)
            lines = actual.stdout.splitlines()
            for marker in MARKERS:
                self.assertEqual(lines.count(marker), 1,
                                 "missing/duplicate real Icarus marker: " + marker
                                 + "\n" + actual.stdout)


if __name__ == "__main__":
    unittest.main()
