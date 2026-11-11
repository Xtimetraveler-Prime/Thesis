"""M08.2b.1 standalone one-page host/compute hardware staging regression.

Genuine local Icarus exercises source RTL only. Real K26 PS AXI-Lite
connectivity, HLS AXI page service, routed timing and physical DDR remain OPEN.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/"rtl/m08/m08_host_staged_page_bank.sv"
TB=ROOT/"rtl/m08/tb_m08_host_staged_page_bank.sv"
M06=ROOT/"rtl/m06/m06_lif16_neuron_step.sv"
MARKERS=(
    "M08_ONE_SLOT_HOST_PAGE_SIGNED16_STAGING_PASS",
    "M08_ONE_SLOT_DIRTY_EVICTION_DENIED",
    "M08_ONE_SLOT_PARTIAL_FILL_DENIED",
    "M08_ONE_SLOT_FAKE_LOAD_READBACK_DENIED",
    "M08_ONE_SLOT_FAKE_DIRTY_SAVE_DENIED",
    "M08_ONE_SLOT_HOST_COMPUTE_CONFLICT_DENIED",
    "M08_ONE_SLOT_SOURCE_ONLY_NO_AXI_NO_DMA_NO_BITSTREAM_PASS",
)


class M08HostStagedPageRTLTests(unittest.TestCase):
    def test_first_party_physicalizable_narrow_boundary(self):
        source=RTL.read_text()
        self.assertIn("module m08_host_staged_page_bank",source)
        self.assertIn("reg [31:0] words [0:63]",source)
        self.assertIn("reg [255:0] loaded_bytes",source)
        self.assertIn("reg [63:0] load_readback_words",source)
        self.assertIn("reg [63:0] dirty_readback_words",source)
        self.assertIn("(&load_readback_words)",source)
        self.assertIn("if (&dirty_readback_words)",source)
        self.assertIn("host_readback_verified",source)
        self.assertIn("host_save_done",source)
        self.assertIn("compute_fault",source)
        self.assertIn("dispatch_logical==page_logical",source)
        self.assertIn("state <= FAILED",source)
        self.assertIn("state <= DIRTY",source)
        # Prevent regression of the Verilog dangling-else bug that ACKed
        # compute reads without loading compute_rdata (actual=00000000).
        self.assertRegex(
            source, r"if\s*\(compute_write\)\s*begin\s+for\s*\(i=0;"
        )
        self.assertRegex(
            source,
            r"end\s+else\s+begin\s+compute_rdata\s*<=\s*words\[compute_word\];"
        )
        self.assertNotIn("m_axi_awaddr",source)
        self.assertNotIn("m_axi_araddr",source)
        self.assertNotIn("$display(",source)
        self.assertNotIn("$fatal(",source)
        tb=TB.read_text()
        self.assertIn("m06_lif16_neuron_step lane",tb)
        self.assertIn("M08_PAGE_COMPUTE_READ_TIMEOUT",tb)
        self.assertIn("M08_PAGE_COMPUTE_READ_REJECTED",tb)
        self.assertIn("M08_PAGE_COMPUTE_BAD_DATA",tb)
        self.assertIn("M08_PAGE_COMPUTE_WRITE_TIMEOUT",tb)
        self.assertIn("if(compute_ack)",tb)
        self.assertIn("if(compute_rdata!==expected)",tb)
        self.assertIn("dut.words[idx]",tb)
        self.assertIn("compute_read(6'd1,32'h10200001);",tb)
        self.assertIn("compute_read(6'd63,32'h1020003f);",tb)
        self.assertIn("compute_read(6'd0,32'h55550006);",tb)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus needed to execute genuine standalone RTL simulation")
    def test_actual_rtl_signed16_host_staging_faults_and_page_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/"m08_host_page.vvp"
            compile_cmd=[
                "iverilog","-g2012","-s","tb_m08_host_staged_page_bank",
                "-o",str(binary),str(RTL),str(M06),str(TB),
            ]
            x=subprocess.run(compile_cmd,text=True,capture_output=True,timeout=90)
            self.assertEqual(x.returncode,0,x.stdout+"\n"+x.stderr)
            self.assertEqual(x.stderr.strip(),"",
                             "unreviewed RTL compiler warning")
            y=subprocess.run(["vvp",str(binary)],text=True,
                             capture_output=True,timeout=50)
            self.assertEqual(y.returncode,0,y.stdout+"\n"+y.stderr)
            self.assertEqual(y.stderr.strip(),"")
            for marker in MARKERS:
                self.assertEqual(y.stdout.count(marker),1,y.stdout)
            self.assertNotIn("FATAL",y.stdout)


if __name__=="__main__":
    unittest.main()
