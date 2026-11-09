"""Original AMD 96-pin paged BFM source generation tests; NO IP simulated."""
from __future__ import annotations
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_generate_original_mem_sc_bfm import required_ports, MODULE
from m06_generate_original_paged_vendor_bfm import render_paged


class M06OriginalPagedVendorBenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ports=[{"name":name, "direction":direction,
                    "packed_width":width}
                   for name,(direction,width) in required_ports().items()]
        cls.source=render_paged(cls.ports)

    def test_real_96_port_original_source_direction_contract(self):
        s=self.source
        self.assertIn(MODULE+" dut (.aclk(clk),.aresetn(resetn),",s)
        self.assertIn("wire [255:0] S00_AXI_rdata;",s)
        self.assertIn("wire [255:0] S03_AXI_wdata;",s)
        self.assertIn("reg [31:0] S01_AXI_araddr=0;",s)
        self.assertIn("reg [31:0] S02_AXI_araddr=0;",s)
        self.assertIn(".s00_araddr(S00_AXI_araddr)",s)
        self.assertIn(".s03_awaddr(S03_AXI_awaddr)",s)
        self.assertIn(".s03_wdata(S03_AXI_wdata)",s)
        self.assertIn(".s_axi_rdata(M00_AXI_rdata)",s)
        self.assertIn(".s_axi_wstrb(M00_AXI_wstrb)",s)
        self.assertEqual(s.count(".S03_AXI_wdata(S03_AXI_wdata)"),1)
        self.assertNotIn("module "+MODULE+" (",s)

    def test_real_m06_residency_fsm_and_block_mover_in_scratch_path(self):
        s=self.source
        self.assertIn("m06_residency_control_fsm #(",s)
        self.assertIn("m06_axi256_block_transfer #(",s)
        self.assertIn("m06_axi128_scratch_mem ram (",s)
        self.assertIn("demand(1,1,0)",s)
        self.assertIn("demand(2,0,0)",s)
        self.assertIn("demand(1,0,0)",s)
        self.assertIn("demand(3,0,1)",s)
        self.assertIn("check_page(1)",s)
        self.assertIn("check_page(2)",s)
        self.assertIn("if(edit_mask[j])",s)
        self.assertIn("M06_ORIGINAL_VENDOR_PAGED_RTL_PASS",s)
        self.assertIn("M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS",s)
        self.assertIn("M06_ORIGINAL_PAGED_FAIL GLOBAL_WATCHDOG",s)

    def test_deterministic_and_no_owner_side_effects(self):
        self.assertEqual(self.source,render_paged(self.ports))
        self.assertEqual(self.source.count("M06_ORIGINAL_VENDOR_PAGED_RTL_PASS"),1)
        self.assertNotIn("generate_target",self.source)
        self.assertNotIn("program_hw_devices",self.source)


if __name__=="__main__":
    unittest.main()
