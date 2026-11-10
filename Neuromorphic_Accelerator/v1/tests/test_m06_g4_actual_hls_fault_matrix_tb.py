"""M06 EXISTING G4 new original-HLS/AMD read fault and missing-B modes.

Source-only HLS/AMD stub declarations used exclusively with Icarus -tnull.
No fake vendor functional simulation, board or DDR.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))
from m06_g4_actual_hls_fault_matrix_tb import g4_fault_tb,MODES
from m06_generate_original_mem_sc_bfm import MODULE,required_ports
from m06_paged_hls_port_audit import TOP
from test_m06_g3_3_actual_hls_idle_link import stub
from test_m06_g3_3_positive16_axilite_tb import make

class G4ReadErrorAndWithheldBOriginalAMDSyntaxTests(unittest.TestCase):
    def test_read_error_flows_from_memory_endpoint_not_forced_fault_pin(self):
        _,_,_,idle,inv,ctrl=make()
        s=g4_fault_tb(idle,inv,ctrl,"g4_first_r_slverr")
        self.assertIn("module "+MODES["g4_first_r_slverr"][0]+";",s)
        self.assertIn(".inject_next_r_slverr(inject_first_r)",s)
        self.assertIn(".inject_next_b_slverr(1'b0)",s)
        self.assertIn("if(M00_AXI_arvalid && M00_AXI_arready && !first_ar_seen)",s)
        self.assertIn("M00_AXI_rresp===2'b10",s)
        self.assertIn("h_m_axi_gmem_read_RRESP===2'b10",s)
        self.assertIn("read_guard_fault!==1'b1",s)
        self.assertIn("g4_poison!==1'b1",s)
        self.assertIn("g4_commit!==1'b0",s)
        self.assertIn("M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS",s)
        self.assertNotIn("force read_guard_fault",s)
        self.assertNotIn("force M00_AXI_rresp",s)
        self.assertNotIn("M06_G4_ACTUAL_HLS_AMD_FIRST_B_SLVERR_QUARANTINE_XSIM_PASS",s)

    def test_missing_b_is_a_real_memory_channel_interposition(self):
        _,_,_,idle,inv,ctrl=make()
        s=g4_fault_tb(idle,inv,ctrl,"g4_stalled_b")
        self.assertIn("module "+MODES["g4_stalled_b"][0]+";",s)
        self.assertIn("wire raw_ram_bvalid, raw_ram_bready;",s)
        self.assertIn("assign M00_AXI_bvalid = raw_ram_bvalid && !hold_first_b;",s)
        self.assertIn("assign raw_ram_bready = M00_AXI_bready && !hold_first_b;",s)
        self.assertIn(".s_axi_bvalid(raw_ram_bvalid)",s)
        self.assertIn(".s_axi_bready(raw_ram_bready)",s)
        self.assertIn(".s_axi_bresp(raw_ram_bresp)",s)
        self.assertIn("epoch_gate.epoch_cycles<TEST_EPOCH_TIMEOUT",s)
        self.assertIn("hls_b_seen!==0",s)
        self.assertIn("M06_G4_ACTUAL_HLS_AMD_STALLED_B_WATCHDOG_QUARANTINE_XSIM_PASS",s)
        self.assertNotIn("force write_guard_fault",s)
        self.assertNotIn("force h_m_axi_gmem_write_BRESP",s)

    def test_original_hls_pin_map_identity_and_independent_modes(self):
        _,_,_,idle,inv,ctrl=make()
        for mode in MODES:
            actual=g4_fault_tb(idle,inv,ctrl,mode)
            self.assertIn("write_reg(7'h30,32'd16)",actual)
            self.assertIn("write_reg(7'h00,32'd1)",actual)
            self.assertIn("m06_g4_epoch_commit_gate #(",actual)
            ctrl["register_offsets"]["NEURON_COUNT_DATA_0"]=112
            moved=g4_fault_tb(idle,inv,ctrl,mode)
            self.assertIn("write_reg(7'h70,32'd16)",moved)
            self.assertNotIn("write_reg(7'h30,32'd16)",moved)
            ctrl["register_offsets"]["NEURON_COUNT_DATA_0"]=48
        with self.assertRaisesRegex(ValueError,"unsupported"):
            g4_fault_tb(idle,inv,ctrl,"g4_unlisted")
        ctrl["ap_return"]=20
        with self.assertRaisesRegex(ValueError,"identity drift"):
            g4_fault_tb(idle,inv,ctrl,"g4_first_r_slverr")

    def test_missing_genuine_mem_fault_port_rejected(self):
        _,_,_,idle,inv,ctrl=make()
        bad=idle.replace(".inject_next_b_slverr(1'b0)",
                         ".inject_next_b_slverr(1'b1)")
        for mode in MODES:
            with self.assertRaisesRegex(ValueError,"injection port"):
                g4_fault_tb(bad,inv,ctrl,mode)

    def test_both_compiled_real_guards_gate_scratch_with_stub_declarations(self):
        if not shutil.which("iverilog"):
            self.skipTest("requires Icarus; CI reruns AFTER installation")
        pins,dwc,_,idle,inv,ctrl=make()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            (out/"FAKE_HLS_DECLARATIONS_ONLY.v").write_text(stub(TOP,pins))
            sc={"aclk":("input",1),"aresetn":("input",1),**required_ports()}
            (out/"FAKE_SC_DECLARATIONS_ONLY.v").write_text(stub(MODULE,sc))
            all_modules=[]
            for ip,meta in dwc["instances"].items():
                all_modules.append(stub(ip,{n:(x["direction"],x["width_bits"])
                                            for n,x in meta["pins"].items()}))
            (out/"FAKE_DWC_DECLARATIONS_ONLY.v").write_text("\n".join(all_modules))
            for mode,(top,_) in MODES.items():
                tb=out/(mode+".sv")
                tb.write_text(g4_fault_tb(idle,inv,ctrl,mode))
                p=subprocess.run(
                    ["iverilog","-g2012","-tnull","-s",top,
                     str(out/"FAKE_HLS_DECLARATIONS_ONLY.v"),
                     str(out/"FAKE_SC_DECLARATIONS_ONLY.v"),
                     str(out/"FAKE_DWC_DECLARATIONS_ONLY.v"),
                     str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                     str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                     str(ROOT/"rtl/m06/m06_g4_epoch_commit_gate.sv"),
                     str(tb)],
                    capture_output=True,text=True,timeout=30)
                self.assertEqual(p.returncode,0,
                                 mode+"\n"+p.stderr+p.stdout)
            # NO vvp: original HLS/AMD declaration stubs have no function.

    def test_runner_and_packager_modes_require_real_vivado_evidence(self):
        runner=(ROOT/"scripts/run_m06_g3_3_actual_hls_idle_xsim.py").read_text()
        pack=(ROOT/"scripts/package_m06_g3_3_positive16_evidence.py").read_text()
        for mode in MODES:
            self.assertIn('"'+mode+'"',runner)
            self.assertIn('"'+mode+'"',pack)
        self.assertIn("M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS",
                      runner)
        self.assertIn("M06_G4_ACTUAL_HLS_AMD_STALLED_B_WATCHDOG_QUARANTINE_XSIM_PASS",
                      runner)
        self.assertIn("m06_g4_actual_hls_fault_matrix_tb.py",runner)
        self.assertIn("source_before_sha256.txt",runner)
        self.assertIn("hls_dat_sources_after_sha256.txt",runner)
        self.assertIn("original_xci_after_sha_check.txt",runner)

if __name__=="__main__":
    unittest.main()
