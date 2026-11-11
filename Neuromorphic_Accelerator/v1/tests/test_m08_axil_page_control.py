"""M08.2b.2 native-first AXI4-Lite staging adapter: source and Icarus checks.

Standalone first-party RTL only: NO AMD SmartConnect/PS, Vivado project,
routed bitstream, Linux MMIO/DDR, neural HLS top or real kernel DMA.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
AXIL=ROOT/"rtl/m08/m08_axil_page_control.sv"
BANK=ROOT/"rtl/m08/m08_host_staged_page_bank.sv"
TB=ROOT/"rtl/m08/tb_m08_axil_page_control.sv"
MARKERS=(
    "M08_AXIL_DECODE_AW_W_AND_STALLS_PASS",
    "M08_AXIL_PAGE_STAGE_256B_READBACK_PASS",
    "M08_AXIL_PREMATURE_SAVE_POISONED_PASS",
    "M08_AXIL_DIRTY_READBACK_SAVE_REPLACE_PASS",
    "M08_AXIL_UNVERIFIED_LOAD_POISONED_PASS",
    "M08_AXIL_STANDALONE_NO_K26_NO_DDR_NO_DMA_PASS",
)


class M08AXILPageControlTests(unittest.TestCase):
    def test_first_party_bounded_one_page_boundary(self):
        source=AXIL.read_text(encoding="utf-8")
        bank=BANK.read_text(encoding="utf-8")
        bench=TB.read_text(encoding="utf-8")
        self.assertIn("module m08_axil_page_control",source)
        self.assertIn("m08_host_staged_page_bank bank",source)
        self.assertIn("input wire [11:0] s_axi_awaddr",source)
        self.assertIn("input wire [11:0] s_axi_araddr",source)
        self.assertIn("input wire [31:0] s_axi_wdata",source)
        self.assertIn("input wire [3:0] s_axi_wstrb",source)
        self.assertIn("wire [31:0] status_word",source)
        self.assertIn("aw_pending",source)
        self.assertIn("w_pending",source)
        self.assertIn("ar_pending",source)
        self.assertIn("!s_axi_bvalid && !s_axi_rvalid",source)
        self.assertIn("ST_HOST_WAIT",source)
        self.assertIn("ST_CMD_WAIT",source)
        self.assertIn("bank_host_error",source)
        self.assertIn("bank_poisoned",source)
        self.assertIn("bank_loaded_bytes",source)
        self.assertIn("w_strb_q!=4'hf",source)
        self.assertIn("w_strb_q!=0",source)
        self.assertIn("op_word<=aw_addr_q[7:2]",source)
        self.assertIn("op_word<=ar_addr_q[7:2]",source)
        self.assertIn("32'h4d303850",source)
        self.assertIn("32'h00000001",source)
        self.assertIn("s_axi_bresp<=DECERR",source)
        self.assertIn("s_axi_rresp<=DECERR",source)
        self.assertIn("s_axi_bresp<=SLVERR",source)
        self.assertIn("s_axi_rresp<=SLVERR",source)
        self.assertIn("reg [31:0] words [0:63]",bank)
        self.assertIn("reg [63:0] load_readback_words",bank)
        self.assertIn("reg [63:0] dirty_readback_words",bank)
        for signal in ("compute_req","compute_done","compute_fault",
                       "fault_in","dispatch_accept","page_poisoned"):
            self.assertIn(signal,source)
        for operation in ("send_aw(","send_w(","axi_read(","axi_write(",
                          "run_compute(","stage("):
            self.assertIn(operation,bench)
        for disallowed in ("m_axi_awaddr","m_axi_araddr","/dev/mem",
                           "axi_dma", "dma_alloc", "bitstream_program"):
            self.assertNotIn(disallowed,source)
        self.assertNotIn("$fatal(",source)
        self.assertNotIn("$display(",source)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus Verilog required for genuine AXI-Lite RTL check")
    def test_actual_32bit_axi_lite_backpressure_paging_and_negative_cases(self):
        with tempfile.TemporaryDirectory() as td:
            executable=Path(td)/"m08_axil_page.vvp"
            cmd=["iverilog","-g2012","-s","tb_m08_axil_page_control",
                 "-o",str(executable),str(AXIL),str(BANK),str(TB)]
            compiled=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
            self.assertEqual(compiled.returncode,0,
                             compiled.stdout+"\n"+compiled.stderr)
            self.assertEqual(compiled.stderr.strip(),"",
                             "unreviewed AXI4-Lite RTL compile warning")
            run=subprocess.run(["vvp",str(executable)],capture_output=True,
                               text=True,timeout=60)
            self.assertEqual(run.returncode,0,run.stdout+"\n"+run.stderr)
            self.assertEqual(run.stderr.strip(),"")
            self.assertNotIn("FATAL",run.stdout)
            for marker in MARKERS:
                self.assertEqual(run.stdout.count(marker),1,run.stdout)


if __name__=="__main__":
    unittest.main()
