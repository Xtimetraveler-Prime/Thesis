"""Real RTL host-bank+compute-port integrated AXI-Lite test, NO K26 board.

Small 256-byte scan/write probe verifies synthesizable RTL memory ownership,
NOT 4KiB M06 neural page/DDR or any physical bitstream. Genuine Icarus/vvp
required: never use a mock simulator to create a false positive.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/m08"
TOP = RTL / "m08_page_compute_probe_shell.v"
PROBE = RTL / "m08_page_compute_probe.v"
ADAPTER = RTL / "m08_axil_page_control.sv"
BANK = RTL / "m08_host_staged_page_bank.sv"
TB = RTL / "tb_m08_page_compute_probe_shell.sv"
MARKERS = (
    "M08_PAGE_PROBE_ACTUAL_AXIL_STAGE_FULL_READBACK_PASS",
    "M08_PAGE_PROBE_63_READ_1_WRITE_DIRTY_SAVE_PASS",
    "M08_PAGE_PROBE_TWO_SEPARATE_LOGICAL_CONTEXTS_PASS",
    "M08_PAGE_PROBE_WRONG_LOGICAL_POISON_PASS",
    "M08_PAGE_PROBE_PREMATURE_SAVE_POISON_PASS",
    "M08_PAGE_PROBE_STALLED_COMPUTE_WATCHDOG_POISON_PASS",
    "M08_PAGE_PROBE_REAL_RTL_SOFTWARE_ONLY_NO_DDR_NO_K26_PASS",
)

class PageComputeProbeTests(unittest.TestCase):
    def test_separate_real_compute_engine_and_safe_shell_unchanged(self):
        probe=PROBE.read_text()
        top=TOP.read_text()
        old=(RTL/"m08_ps_page_safe_shell.v").read_text()
        self.assertIn("module m08_page_compute_probe",probe)
        self.assertIn("module m08_page_compute_probe_shell",top)
        self.assertIn("m08_axil_page_control #(.ENABLE_COMPUTE(1'b1))",top)
        self.assertIn("m08_page_compute_probe probe",top)
        self.assertIn("m08_axil_page_control #(.ENABLE_COMPUTE(1'b0))",old)
        self.assertIn("module m08_ps_page_safe_shell",old)
        self.assertIn("X_INTERFACE_INFO",top)
        self.assertIn("ASSOCIATED_BUSIF S_AXI",top)
        for name in ("awaddr","awprot","awvalid","awready",
                     "wdata","wstrb","wvalid","wready",
                     "bresp","bvalid","bready",
                     "araddr","arprot","arvalid","arready",
                     "rdata","rresp","rvalid","rready"):
            self.assertIn(f".s_axi_{name}(s_axi_{name})",top,
                          "AXI-Lite interface signal unconnected: "+name)
        for wire in ("compute_ack","compute_rdata","compute_req",
                     "compute_write","compute_word","compute_wdata",
                     "compute_done","compute_fault","dispatch_accept"):
            self.assertIn(wire,top)
            self.assertIn(wire,probe)
        for excluded in ("program_hw_devices","/dev/mem","axi_dma",
                         "m_axi_awaddr","write_bitstream","vitis_hls"):
            self.assertNotIn(excluded,top+probe)
        self.assertNotIn("$display(",probe)
        self.assertNotIn("$fatal(",probe)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "REAL Icarus/vvp required for integrated RTL")
    def test_integrated_256byte_host_compute_backpressure_and_faults(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"page_probe.vvp"
            build=subprocess.run(
                ["iverilog","-g2012","-s","tb_m08_page_compute_probe_shell",
                 "-o",str(out),*[str(p) for p in
                                  (TOP,PROBE,ADAPTER,BANK,TB)]],
                capture_output=True,text=True,timeout=90)
            self.assertEqual(build.returncode,0,
                             build.stdout+"\n"+build.stderr)
            self.assertEqual(build.stderr.strip(),"",
                             "unexpected first-party RTL compilation warnings")
            run=subprocess.run(["vvp",str(out)],capture_output=True,
                               text=True,timeout=90)
            self.assertEqual(run.returncode,0,
                             run.stdout+"\n"+run.stderr)
            self.assertEqual(run.stderr.strip(),"")
            self.assertNotIn("FATAL",run.stdout)
            for marker in MARKERS:
                self.assertEqual(run.stdout.count(marker),1,
                                 "real RTL marker absent/duplicated: "+marker
                                 +"\n"+run.stdout)

if __name__=="__main__":
    unittest.main()
