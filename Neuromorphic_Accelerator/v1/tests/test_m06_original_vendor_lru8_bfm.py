"""Synthetic compile-only test for fourth ORIGINAL AMD 8-slot LRU XSim gate."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_generate_original_mem_sc_bfm import required_ports,MODULE
from m06_generate_original_vendor_lru8_bfm import render_lru8


class OriginalVendorEightSlotBFMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ports=[{"name":name,"direction":mode,"packed_width":width}
                   for name,(mode,width) in required_ports().items()]
        cls.src=render_lru8(cls.ports)

    def test_exact_original_vendor_wrapper_and_full_eight_slot_rtl_connected(self):
        code=self.src
        self.assertIn("module tb_m06_original_vendor_lru8;",code)
        self.assertIn(MODULE+" dut (.aclk(clk),.aresetn(resetn),",code)
        self.assertIn("m06_residency_lru8 #(",code)
        self.assertIn("m06_axi256_multislot_transfer #(",code)
        self.assertIn("m06_axi128_scratch_mem ram (",code)
        self.assertIn(".dma_slot(dma_slot)",code)
        self.assertIn(".cmd_slot(dma_slot)",code)
        self.assertIn(".client_slot(client_slot)",code)
        self.assertIn(".s03_wdata(S03_AXI_wdata)",code)
        self.assertIn(".s_axi_wdata(M00_AXI_wdata)",code)
        self.assertNotIn("m06_residency_control_fsm #(",code)
        self.assertNotIn("module "+MODULE+" (",code)

    def test_multi_slot_byte_oracle_dirty_eviction_and_sticky_poison(self):
        code=self.src
        self.assertIn("demand(page,(page==0 || page==1),0)",code)
        self.assertIn("demand(8,0,0)",code)
        self.assertIn("demand(0,1,0)",code)
        self.assertIn("demand(0,0,0)",code)
        self.assertIn("demand(18,0,1)",code)
        self.assertIn("expected[3][8*lane+:8]",code)
        self.assertIn("check_cached(0)",code)
        self.assertIn("wb_acks !== 2 || fill_acks !== 19",code)
        self.assertIn("m00_wbeats < 32 || m00_rbeats < 304",code)
        self.assertIn("M06_ORIGINAL_VENDOR_LRU8_RTL_PASS",code)
        self.assertIn("M06_ORIGINAL_VENDOR_LRU8_FAULT_PASS",code)
        self.assertIn("M06_VENDOR_LRU8_FAIL WATCHDOG",code)
        self.assertEqual(render_lru8(self.ports),code)

    def test_fourth_vendor_stage_evidence_only_from_actual_owner_xsim(self):
        runner=(ROOT/"scripts/run_m06_original_mem_sc_vendor_xsim.sh").read_text()
        self.assertIn("m06_generate_original_vendor_lru8_bfm.py",runner)
        self.assertIn("work.tb_m06_original_vendor_lru8 work.glbl",runner)
        self.assertIn("11_lru8_xsim.log",runner)
        self.assertIn("M06_ORIGINAL_VENDOR_LRU8_RTL_PASS",runner)
        self.assertIn("M06_ORIGINAL_VENDOR_LRU8_FAULT_PASS",runner)
        self.assertTrue("NO original M05 HLS RTL instantiated" in runner)
        self.assertNotIn("program_hw_devices",runner)


if __name__=="__main__":
    unittest.main()
