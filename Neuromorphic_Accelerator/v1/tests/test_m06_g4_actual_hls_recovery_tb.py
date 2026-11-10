"""G4 original generated-HLS/AMD read fault, explicit owner discard and clean replay.

Icarus -tnull fake PORT DECLARATIONS ONLY; no functional fake vendor IP.
Owner genuine Vivado 2025.2 result required before actual G4 acceptance.
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
from m06_g4_actual_hls_recovery_tb import recovery_tb, TOP, PASS
from m06_generate_original_mem_sc_bfm import MODULE,required_ports
from m06_paged_hls_port_audit import TOP as HLS_TOP
from test_m06_g3_3_actual_hls_idle_link import stub
from test_m06_g3_3_positive16_axilite_tb import make

class G4OriginalHLSImageRestoreTests(unittest.TestCase):
    def test_first_failure_is_real_original_mem_rresp_and_no_failed_release(self):
        _,_,_,idle,inv,control=make()
        s=recovery_tb(idle,inv,control)
        self.assertIn("module "+TOP+";",s)
        self.assertIn(".inject_next_r_slverr(inject_first_r)",s)
        self.assertIn("M00_AXI_rresp===2'b10",s)
        self.assertIn("h_m_axi_gmem_read_RRESP===2'b10",s)
        self.assertIn("read_guard_fault!==1'b1",s)
        self.assertIn("q_quarantined!==1'b1",s)
        self.assertIn("FIRST_FAULT_NOT_QUARANTINED",s)
        self.assertIn("FAILED_EPOCH_COMMITTED",s)
        self.assertIn("published_trace!==0",s)
        self.assertIn("published_metrics!==0",s)
        self.assertNotIn("force read_guard_fault",s)
        self.assertNotIn("force M00_AXI_rresp",s)

    def test_second_run_requires_explicit_full_image_restore_and_real_hls_done(self):
        _,_,_,idle,inv,control=make()
        s=recovery_tb(idle,inv,control)
        self.assertIn("ram.mem[image_byte]=(13*image_byte+17)&8'hff;",s)
        self.assertIn("image_byte<65536",s)
        self.assertIn("ram.mem[65535]!==8'h04",s)
        self.assertIn("read_reg(7'h00,observed_ctrl)",s)
        self.assertIn("read_reg(7'h10,observed_status)",s)
        self.assertIn("g4_done=1",s)
        self.assertIn("CLEAN_AP_DONE_TIMEOUT",s)
        self.assertIn("CLEAN_HLS_STATUS",s)
        self.assertIn("q_published_count!==32'd16",s)
        self.assertIn("published_metrics!==1",s)
        self.assertIn("DIRTY_OR_UNEXPECTED_TRACE",s)
        self.assertIn("m06_g4_output_quarantine #(.MAX_TRACE(16))",s)
        self.assertIn(PASS,s)
        self.assertNotIn("M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS",s)

    def test_actual_original_control_map_cannot_drift_silently(self):
        _,_,_,idle,inv,ctrl=make()
        ctrl["register_offsets"]["NEURON_COUNT_DATA_0"]=112
        s=recovery_tb(idle,inv,ctrl)
        self.assertIn("write_reg(7'h70,32'd16)",s)
        self.assertNotIn("write_reg(7'h30,32'd16)",s)
        ctrl["ap_return"]=20
        with self.assertRaisesRegex(ValueError,"identity drift"):
            recovery_tb(idle,inv,ctrl)

    def test_real_local_guard_fifo_and_genuine_hls_vendor_declaration_syntax(self):
        if not shutil.which("iverilog"):
            self.skipTest("requires Icarus, post-install workflow retest")
        pins,dwc,_,idle,inv,control=make()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            tb=out/"tb_g4_recovery.sv"
            tb.write_text(recovery_tb(idle,inv,control))
            (out/"FAKE_HLS_DECLARATIONS_ONLY.v").write_text(stub(HLS_TOP,pins))
            sc={"aclk":("input",1),"aresetn":("input",1),**required_ports()}
            (out/"FAKE_SC_DECLARATIONS_ONLY.v").write_text(stub(MODULE,sc))
            items=[]
            for ip,meta in dwc["instances"].items():
                items.append(stub(ip,{n:(x["direction"],x["width_bits"])
                                       for n,x in meta["pins"].items()}))
            (out/"FAKE_DWC_DECLARATIONS_ONLY.v").write_text("\n".join(items))
            p=subprocess.run([
                "iverilog","-g2012","-tnull","-s",TOP,
                str(out/"FAKE_HLS_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_SC_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_DWC_DECLARATIONS_ONLY.v"),
                str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                str(ROOT/"rtl/m06/m06_g4_epoch_commit_gate.sv"),
                str(ROOT/"rtl/m06/m06_g4_output_quarantine.sv"),
                str(tb)
            ],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            # No functional fake HLS/AMD, no vvp on declarations.

    def test_runner_provenance_and_g4_restore_packager(self):
        runner=(ROOT/"scripts/run_m06_g3_3_actual_hls_idle_xsim.py").read_text()
        pack=(ROOT/"scripts/package_m06_g3_3_positive16_evidence.py").read_text()
        self.assertIn('"g4_discard_restore"',runner)
        self.assertIn('"g4_discard_restore"',pack)
        self.assertIn(PASS,runner)
        self.assertIn("m06_g4_actual_hls_recovery_tb.py",runner)
        self.assertIn("m06_g4_output_quarantine.sv",runner)
        self.assertIn("original_xci_after_sha_check.txt",runner)
        self.assertIn("M06_G4_DISCARD_RESTORE_HLS_AMD_REVIEW_",pack)

if __name__=="__main__":
    unittest.main()
