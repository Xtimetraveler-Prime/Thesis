"""Real Icarus source-only AXI4-Lite MMIO manages all 75 LIF commands.

Original M02/M03 512 numerical values are comparison-only. This test
drives 5 real AXI-Lite channels to the work controller for ALL load,
dispatch and dirty-save operations. AXI DDR is a synthetic BFM.
Driver identity, privileged route, and drain remain FAKE testbench pins.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/"rtl/m08"
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as fixture

SOURCES=tuple(RTL/name for name in (
    "m08_host_staged_page_bank.sv",
    "m08_paged_m06_lif_engine.v",
    "m08_m085_ddr_page_admission.v",
    "m08_m085_axi128_page_engine.v",
    "m08_m085_axi128_page_candidate.v",
    "m08_m085_axi_bank_bridge.v",
    "m08_m085_axi_neural_shell.v",
    "m08_m085_kernel_dma_lease_fence.v",
    "m08_m085_trusted_control_abi.v",
    "m08_m085_work_command_sequencer.v",
    "m08_m085_axil_control_candidate.v",
    "m08_m085_axil_managed_neural_candidate.v",
    "tb_m08_m085_axil_managed_neural_candidate.sv",
))
PASS="M08_5_AXIL_MANAGED_75_COMMANDS_512_ORACLE_PASS"


class M085ManagedWorkSourceTests(unittest.TestCase):
    def test_protected_mmio_is_the_only_work_command_source(self):
        work=(RTL/"m08_m085_work_command_sequencer.v").read_text()
        control=(RTL/"m08_m085_axil_control_candidate.v").read_text()
        top=(RTL/"m08_m085_axil_managed_neural_candidate.v").read_text()
        tb=SOURCES[-1].read_text()
        self.assertIn("parameter integer ENABLE_WORK_COMMANDS=0",control)
        self.assertIn(".ENABLE_WORK_COMMANDS(1)",top)
        self.assertIn("m08_m085_work_command_sequencer",control)
        self.assertIn("raw_lease_admit(csr_admit)",control)
        self.assertIn("wire work_selected=ENABLE_WORK_COMMANDS",control)
        self.assertIn("work_fault",top)
        self.assertIn(".work_page_req(request)",top)
        self.assertIn(".work_dispatch_req(dispatch_req)",top)
        self.assertNotIn("input wire request,",top)
        self.assertNotIn("input wire dispatch_req,",top)
        for marker in ("8'h24","8'h28","8'h2c","8'h30","8'h34",
                       "WORK_TIMEOUT_CYCLES","neural_completed_save",
                       "completed_commands","neural_bank_dirty",
                       "assign page_req=phase==PAGE_START",
                       "assign dispatch_req=phase==DISPATCH_START"):
            self.assertIn(marker,work)
        for addr in ("12'h024","12'h028","12'h02c","12'h030"):
            self.assertIn(addr,tb)
        self.assertIn(PASS,tb)
        for banned in ("program_hw_devices","open_hw_manager",
                       "/dev/mem","0x40000000","dma_alloc_coherent("):
            self.assertNotIn(banned,work+top+tb)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "genuine Icarus required, no mock success")
    def test_full_mmio_load_dispatch_dirty_save_75_commands_512_checks(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            exe=path/"managed_neural.vvp"
            comp=subprocess.run(
                ["iverilog","-g2012","-s","tb_m08_m085_axil_managed_neural_candidate",
                 "-o",str(exe),*[str(p) for p in SOURCES]],
                capture_output=True,text=True,timeout=90
            )
            self.assertEqual(comp.returncode,0,comp.stdout+comp.stderr)
            self.assertEqual(comp.stderr.strip(),"","Icarus warnings not accepted")
            _,net,events,_,_,_,_=fixture.source()
            self.assertEqual(len(events),17)
            self.assertEqual(len(net.synapses),5)
            golden=path/"independent_m02_m03_512_check_only.hex"
            edge=path/"original_m6eg_5_edges.hex"
            fixture.write_hex(golden,fixture.golden_words())
            fixture.write_hex(edge,fixture.edge_words())
            plus=[f"+golden={golden}",f"+edge={edge}"]
            for slot in range(6):
                words=fixture.neural_words(slot)
                self.assertTrue(fixture.audit_page(words,slot,0))
                file=path/f"original_m6nf_slot_{slot}.hex"
                fixture.write_hex(file,words)
                plus.append(f"+page{slot}={file}")
            sim=subprocess.run(
                ["vvp",str(exe),"+CASE=0",*plus],
                capture_output=True,text=True,timeout=120
            )
            self.assertEqual(sim.returncode,0,sim.stdout+sim.stderr)
            self.assertEqual(sim.stderr.strip(),"")
            for mark in (
                PASS,
                "M08_5_AXIL_MANAGED_CSR_7_SLOT_NEURAL_GRANT_PASS",
                "M08_5_REAL_LIF_AXI_BANK_M02_M03_512_PARITY_24_DISPATCHES_5_EDGES_PASS",
                "M08_5_M6EG_SEVENTH_SLOT_FIVE_EDGE_BOOTSTRAP_PASS",
            ):
                self.assertEqual(sim.stdout.count(mark),1,sim.stdout)
            self.assertEqual(sim.stdout.count("M08_5_AXIDDR_REAL_SIGNED16_PAGE_PASS tick="),24)
            self.assertEqual(sim.stdout.count("M08_5_AXIDDR_TICK_BARRIER_PASS tick="),4)


if __name__=="__main__":
    unittest.main()
