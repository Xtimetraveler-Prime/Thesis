"""Synthetic compile-only source regression of ORIGINAL vendor 4096-range BFM.

No fake HDL compilation/sim pass counts as actual original AMD XSim.
"""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_generate_original_mem_sc_bfm import required_ports, MODULE
from m06_generate_original_vendor_4096_bfm import render_full_canonical


class OriginalVendor4096ScratchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ports=[{"name":key,"direction":role,
                    "packed_width":width}
                   for key,(role,width) in required_ports().items()]
        cls.code=render_full_canonical(cls.ports)

    def test_genuine_vendor_roles_unchanged_and_full_canonical_range_enabled(self):
        code=self.code
        self.assertIn("module tb_m06_original_vendor_4096;",code)
        self.assertIn(MODULE+" dut (.aclk(clk),.aresetn(resetn),",code)
        self.assertIn(".S00_AXI_araddr(S00_AXI_araddr)",code)
        self.assertIn(".S03_AXI_awaddr(S03_AXI_awaddr)",code)
        self.assertIn("m06_axi256_block_transfer #(.MAX_BLOCKS(256),",code)
        self.assertIn("m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536)) ram (",code)
        self.assertIn("expected [0:2047]",code)
        self.assertNotIn("module "+MODULE+" (",code)

    def test_high_page_byte_exact_and_outside_region_quarantined(self):
        code=self.code
        self.assertIn("demand(255,1,0)",code)
        self.assertIn("check_page(255)",code)
        self.assertIn("demand(254,0,0)",code)
        self.assertIn("demand(256,0,1)",code)
        self.assertIn("m00_wbeats!==16 || m00_rbeats!==48",code)
        self.assertIn("M06_ORIGINAL_VENDOR_4096_RANGE_PASS",code)
        self.assertIn("M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS",code)
        self.assertIn("M06_VENDOR_4096_FAIL GLOBAL_WATCHDOG",code)
        self.assertEqual(render_full_canonical(self.ports),code)

    def test_fifth_xsim_stage_requires_real_owner_verification(self):
        script=(ROOT/"scripts/run_m06_original_mem_sc_vendor_xsim.sh").read_text()
        self.assertIn("m06_generate_original_vendor_4096_bfm.py",script)
        self.assertIn("work.tb_m06_original_vendor_4096 work.glbl",script)
        self.assertIn("13_4096_xsim.log",script)
        self.assertIn("M06_ORIGINAL_VENDOR_4096_RANGE_PASS",script)
        self.assertIn("M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS",script)
        self.assertNotIn("program_hw_devices",script)
        ram=(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv").read_text()
        self.assertIn("parameter integer SCRATCH_BYTES = 8192",ram)
        self.assertIn("mem[address[15:0]+n]",ram)
        self.assertIn("mem[wr_address[15:0]+lane]",ram)


if __name__=="__main__":
    unittest.main()
