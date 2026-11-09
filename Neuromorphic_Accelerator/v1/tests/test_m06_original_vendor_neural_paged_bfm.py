"""Source-only third genuine-original AMD XSim neural-paging bench checks."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_generate_original_mem_sc_bfm import required_ports, MODULE
from m06_generate_original_vendor_neural_paged_bfm import (
    render_neural_paged,
)


class OriginalVendorNeuralPagedGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources=[{"name":k,"direction":v[0],"packed_width":v[1]}
                     for k,v in required_ports().items()]
        cls.out=render_neural_paged(cls.sources)

    def test_real_original_amd_96pin_contract_reused_with_no_fabrication(self):
        v=self.out
        self.assertIn("module tb_m06_original_vendor_neural_paged;",v)
        self.assertIn(MODULE+" dut (.aclk(clk),.aresetn(resetn),",v)
        self.assertIn(".S00_AXI_araddr(S00_AXI_araddr)",v)
        self.assertIn(".S03_AXI_wdata(S03_AXI_wdata)",v)
        self.assertIn(".M00_AXI_wdata(M00_AXI_wdata)",v)
        self.assertIn(".s_axi_rdata(M00_AXI_rdata)",v)
        self.assertNotIn("module "+MODULE+" (",v)
        self.assertIn(chr(96)+'include "m06_lif16_vectors.vh"',v)
        self.assertEqual(v.count(".S03_AXI_wdata(S03_AXI_wdata)"),1)

    def test_every_numeric_and_transfer_integrity_gate_required(self):
        s=self.out
        self.assertIn("m06_lif16_neuron_step neural_lane (",s)
        self.assertIn("m06_residency_control_fsm #(",s)
        self.assertIn("m06_axi256_block_transfer #(",s)
        self.assertIn("m06_axi128_scratch_mem ram (",s)
        self.assertIn("ram.mem[init_word*32+byte_lane]",s)
        self.assertIn("lif_next !== oracle_v[tick_no*32+neuron]",s)
        self.assertIn("lif_spike !== oracle_spike[tick_no*32+neuron]",s)
        self.assertIn("word_data[8*(byte_off+2)+:32] !== tick_no",s)
        self.assertIn("demand(neuron/16,1,0)",s)
        self.assertIn("demand(0,0,0)",s)
        self.assertIn("demand(1,0,0)",s)
        self.assertIn("demand(2,0,1)",s)
        self.assertIn("neural_updates !== 128 || neural_spikes !== 8",s)
        self.assertIn("m00_rbeats < 160 || m00_wbeats < 128",s)
        self.assertIn("M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS",s)
        self.assertIn("M06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS",s)
        self.assertIn("M06_VENDOR_NEURAL_FAIL WATCHDOG",s)

    def test_no_original_m05_hls_engine_fabrication_or_board_claim(self):
        v=self.out
        self.assertIn("ORIGINAL_M05_HLS_NOT_INSTANTIATED",v)
        self.assertIn("NO_REAL_DDR_NO_BOARD",v)
        self.assertNotIn("program_hw_devices",v)
        self.assertNotIn("generate_target",v)
        self.assertEqual(render_neural_paged(self.sources),v)

    def test_runner_requires_third_real_xsim_pass_not_just_stub(self):
        runner=(ROOT/"scripts/run_m06_original_mem_sc_vendor_xsim.sh").read_text()
        self.assertIn("m06_generate_original_vendor_neural_paged_bfm.py",runner)
        self.assertIn("m06_generate_paged_lif16_vectors.py",runner)
        self.assertIn('work.tb_m06_original_vendor_neural_paged work.glbl',runner)
        self.assertIn("09_neural_paged_xsim.log",runner)
        self.assertIn("M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS",runner)
        self.assertIn("M06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS",runner)
        p=subprocess.run(["bash","-n",
                          str(ROOT/"scripts/run_m06_original_mem_sc_vendor_xsim.sh")],
                         capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)


if __name__=="__main__":
    unittest.main()
