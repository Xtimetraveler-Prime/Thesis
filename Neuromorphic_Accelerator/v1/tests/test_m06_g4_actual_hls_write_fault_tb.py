"""Existing G4: original HLS/AMD FIRST-B SLVERR owner candidate SOURCE tests.

Icarus -tnull uses dummy port DECLARATIONS ONLY. It does not simulate a
functional fake HLS, AMD SmartConnect/DWC or physical DDR. Genuine 2025.2
Vivado XSim first-owner test is required for real connected G4 acceptance.
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
from m06_g4_actual_hls_write_fault_tb import generate,NAME,PASS
from test_m06_g3_3_positive16_axilite_tb import make
from test_m06_g3_3_actual_hls_idle_link import stub
from m06_generate_original_mem_sc_bfm import MODULE,required_ports
from m06_paged_hls_port_audit import TOP

class G4OriginalAMDWriteFaultTests(unittest.TestCase):
    def test_fault_is_injected_at_real_bfm_not_synthetic_guard_force(self):
        _,_,_,idle,inv,control=make()
        s=generate(idle,inv,control)
        self.assertIn("module "+NAME+";",s)
        self.assertIn(".inject_next_b_slverr(inject_first_b)",s)
        self.assertIn(".inject_next_r_slverr(1'b0)",s)
        self.assertIn("if(M00_AXI_awvalid && M00_AXI_awready && !first_aw_seen)",s)
        self.assertIn("ram_b_slverr=ram_b_slverr+1;",s)
        self.assertIn("hls_b_slverr=hls_b_slverr+1;",s)
        self.assertIn(".write_guard_fault(write_guard_fault)",s)
        self.assertIn(".poisoned(g4_poison)",s)
        self.assertIn("g4_commit!==1'b0",s)
        self.assertIn("published_trace!==0",s)
        self.assertIn(PASS,s)
        self.assertNotIn("force write_guard_fault",s)
        self.assertNotIn("force M00_AXI_bresp",s)
        self.assertNotIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_POSITIVE16_XSIM_PASS",s)
        self.assertNotIn("M06_G3_3_HLS_LINK_IDLE_FAIL GUARD_FAULT",s)
        self.assertNotIn("program_hw_devices",s)

    def test_original_control_map_is_dynamic_and_all_pins_have_identity(self):
        _,_,_,idle,inv,ctrl=make()
        actual=generate(idle,inv,ctrl)
        self.assertIn("write_reg(7'h30,32'd16)",actual)
        self.assertIn("write_reg(7'h00,32'd1)",actual)
        self.assertIn("m06_g4_epoch_commit_gate #(",actual)
        ctrl["register_offsets"]["NEURON_COUNT_DATA_0"]=112
        changed=generate(idle,inv,ctrl)
        self.assertIn("write_reg(7'h70,32'd16)",changed)
        self.assertNotIn("write_reg(7'h30,32'd16)",changed)
        ctrl["ap_return"]=20
        with self.assertRaisesRegex(ValueError,"identity drift"):
            generate(idle,inv,ctrl)

    def test_missing_injection_hardware_link_rejected(self):
        _,_,_,idle,inv,ctrl=make()
        bad=idle.replace(".inject_next_b_slverr(1'b0)",
                         ".inject_next_b_slverr(1'b1)")
        with self.assertRaisesRegex(ValueError,"injection port"):
            generate(bad,inv,ctrl)
        bad2=idle.replace(
            "if(read_guard_fault || write_guard_fault)",
            "if(read_guard_fault)")
        with self.assertRaisesRegex(ValueError,"guard anchor"):
            generate(bad2,inv,ctrl)

    def test_real_synthesizable_gate_and_only_stub_port_syntax(self):
        if not shutil.which("iverilog"):
            self.skipTest("needs Icarus (workflow reruns after apt install)")
        pins,dwc,vendor,idle,inv,ctrl=make()
        s=generate(idle,inv,ctrl)
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)
            (out/"tb.sv").write_text(s)
            (out/"FAKE_HLS_PORT_DECLARATIONS_ONLY.v").write_text(stub(TOP,pins))
            scpins={"aclk":("input",1),"aresetn":("input",1),**required_ports()}
            (out/"FAKE_SMARTCONNECT_DECLARATIONS_ONLY.v").write_text(stub(MODULE,scpins))
            mods=[]
            for ip,meta in dwc["instances"].items():
                mods.append(stub(ip,{n:(row["direction"],row["width_bits"])
                                     for n,row in meta["pins"].items()}))
            (out/"FAKE_DWC_DECLARATIONS_ONLY.v").write_text("\n".join(mods))
            result=subprocess.run([
                "iverilog","-g2012","-tnull","-s",NAME,
                str(out/"FAKE_HLS_PORT_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_SMARTCONNECT_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_DWC_DECLARATIONS_ONLY.v"),
                str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                str(ROOT/"rtl/m06/m06_g4_epoch_commit_gate.sv"),
                str(out/"tb.sv")
            ],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            # NO vvp: vendor+HLS stub declarations are NOT functional IP.

    def test_runner_requires_genuine_owner_xsim_and_g4_marker(self):
        runner=(ROOT/"scripts/run_m06_g3_3_actual_hls_idle_xsim.py").read_text()
        self.assertIn('"g4_first_b_slverr"',runner)
        self.assertIn("M06_G4_ACTUAL_HLS_AMD_FIRST_B_SLVERR_QUARANTINE_XSIM_PASS",runner)
        self.assertIn('str(ROOT/"rtl/m06/m06_g4_epoch_commit_gate.sv")',runner)
        self.assertIn('str(ROOT/"scripts/m06_g4_actual_hls_write_fault_tb.py")',runner)
        self.assertIn("original_xci_after_sha_check.txt",runner)
        self.assertIn("xsim",runner)

if __name__=="__main__":
    unittest.main()
