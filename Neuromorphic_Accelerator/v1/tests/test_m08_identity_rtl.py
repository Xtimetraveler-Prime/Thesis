"""M08.2 standalone side-effect-free AXI4-Lite identity RTL verification.

Icarus simulates only first-party local register RTL, never actual AMD IP,
PS/PL BD, original HLS, programmed FPGA or DDR. CI installs Icarus to make
this a mandatory gate; host systems without Icarus explicitly SKIP it.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/"rtl/m08/m08_axil_readonly_identity.v"
TB=ROOT/"rtl/m08/tb_m08_axil_readonly_identity.sv"
MARKER="M08_AXIL_IDENTITY_STANDALONE_ICARUS_PASS"


class M08IdentityRTLTests(unittest.TestCase):
    def test_identity_module_has_no_dma_or_writable_effects(self):
        rtl=RTL.read_text()
        self.assertIn("module m08_axil_readonly_identity",rtl)
        self.assertIn("s_axi_rdata <= BUILD_ID0",rtl)
        self.assertIn("s_axi_bresp <= 2'b10",rtl)
        self.assertIn("s_axi_rresp <= 2'b11",rtl)
        self.assertIn("assign s_axi_awready",rtl)
        self.assertIn("assign s_axi_wready",rtl)
        self.assertNotIn("m_axi_araddr",rtl)
        self.assertNotIn("m_axi_awaddr",rtl)
        self.assertNotIn("$display(",rtl)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus Verilog must be installed for local RTL functional check")
    def test_real_iverilog_protocol_reset_and_backpressure(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/"m08_identity.vvp"
            compile_cmd=[
                "iverilog","-g2012","-s","tb_m08_axil_readonly_identity",
                "-o",str(binary),str(RTL),str(TB)]
            x=subprocess.run(compile_cmd,capture_output=True,text=True,
                             timeout=90)
            self.assertEqual(x.returncode,0,x.stdout+"\n"+x.stderr)
            self.assertEqual(x.stderr.strip(),"",
                             "unreviewed standalone RTL compile warning")
            y=subprocess.run(["vvp",str(binary)],
                             capture_output=True,text=True,timeout=40)
            self.assertEqual(y.returncode,0,y.stdout+"\n"+y.stderr)
            self.assertEqual(y.stdout.count(MARKER),1)
            self.assertIn("READS=13 REJECTED_WRITES=3 NO_DMA",y.stdout)
            self.assertNotIn("FATAL",y.stdout)
            self.assertEqual(y.stderr.strip(),"")


if __name__=="__main__":
    unittest.main()
