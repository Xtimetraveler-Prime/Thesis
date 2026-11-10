"""Prospective original HLS/AMD M02/M03 32x4 exact parity and AXI evidence.

Fake HLS/vendor stubs used ONLY with iverilog -tnull; no functional vvp.
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
from m06_g3_3_m02_m03_parity_tb import parity_tb
from m06_g3_3_m02_m03_owner_vectors import vectors
from test_m06_g3_3_positive16_axilite_tb import make
from test_m06_g3_3_actual_hls_idle_link import stub
from m06_generate_original_mem_sc_bfm import MODULE,required_ports
from m06_paged_hls_port_audit import TOP

class M06OriginalHLSDenseSparseParityTBTests(unittest.TestCase):
    def test_full_trace_state_and_dirty_eviction_guards(self):
        _,_,_,idle,inv,ctrl=make()
        sv=parity_tb(idle,inv,ctrl)
        self.assertIn("module tb_m06_g3_3_actual_hls_original_amd_parity32;",sv)
        self.assertIn('m06_g3_3_m02_m03_owner_vectors.svh',sv)
        self.assertIn("write_reg(7'h30,32'd32)",sv)
        self.assertIn("write_reg(7'h38,32'd5)",sv)
        self.assertIn("write_reg(7'h40,32'd17)",sv)
        self.assertIn("write_reg(7'h68,32'd4064)",sv)
        self.assertIn("h_trace_TDATA[191:160]!==oracle_trace",sv)
        self.assertIn("h_trace_TDATA[143:136]!==oracle_trace",sv)
        self.assertIn("h_metrics_TDATA!==oracle_metrics",sv)
        self.assertIn("ram.mem[base+b]!==oracle_final_row[i]",sv)
        self.assertIn("read_ar_count",sv)
        self.assertIn("READ_AR_BEFORE_WRITE_B",sv)
        self.assertIn("M06_G3_3_ACTUAL_HLS_AMD_M02_M03_TRACE_STATE_PARITY_XSIM_PASS",sv)
        self.assertNotIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_POSITIVE16_XSIM_PASS",sv)
        self.assertNotIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS",sv)

    def test_original_hls_stream_input_tieoffs_replaced_once_only(self):
        _,_,_,idle,inv,ctrl=make()
        sv=parity_tb(idle,inv,ctrl)
        for name in ("h_neurons_TVALID","h_synapses_TVALID",
                     "h_external_events_TVALID"):
            self.assertIn(f"reg {name}=0;",sv)
            self.assertNotIn(f"assign {name} =",sv)
        bad=idle.replace("wire h_synapses_TVALID;","wire CORRUPT;")
        with self.assertRaisesRegex(ValueError,"ABI/tieoff"):
            parity_tb(bad,inv,ctrl)

    def test_original_control_offsets_are_measured_dynamic(self):
        _,_,_,idle,inv,ctrl=make()
        ctrl["register_offsets"]["CANONICAL_FIRST_NEURON_DATA_0"]=112
        s=parity_tb(idle,inv,ctrl)
        self.assertIn("write_reg(7'h70,32'd4064)",s)
        self.assertNotIn("write_reg(7'h68,32'd4064)",s)
        ctrl["ap_return"]=256
        with self.assertRaisesRegex(ValueError,"register map"):
            parity_tb(idle,inv,ctrl)

    def test_real_guards_ram_and_fake_vendor_syntax_only(self):
        if not shutil.which("iverilog"):
            self.skipTest("requires Icarus; workflow reruns after installing")
        pins,dwc,vendor,idle,inv,ctrl=make()
        sv=parity_tb(idle,inv,ctrl)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            (out/"tb.sv").write_text(sv)
            (out/"m06_g3_3_m02_m03_owner_vectors.svh").write_text(vectors())
            (out/"FAKE_HLS_PORT_DECLARATIONS_ONLY.v").write_text(stub(TOP,pins))
            sc={"aclk":("input",1),"aresetn":("input",1),**required_ports()}
            (out/"FAKE_SMARTCONNECT_DECLARATIONS_ONLY.v").write_text(stub(MODULE,sc))
            d=[]
            for ip,obj in dwc["instances"].items():
                d.append(stub(ip,{n:(x["direction"],x["width_bits"])
                                  for n,x in obj["pins"].items()}))
            (out/"FAKE_DWC_DECLARATIONS_ONLY.v").write_text("\n".join(d))
            p=subprocess.run([
                "iverilog","-g2012","-tnull","-I",str(out),
                "-s","tb_m06_g3_3_actual_hls_original_amd_parity32",
                str(out/"FAKE_HLS_PORT_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_SMARTCONNECT_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_DWC_DECLARATIONS_ONLY.v"),
                str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                str(out/"tb.sv")
            ],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr+p.stdout)
            # Absolutely no vvp against fake generated HLS/vendor modules.

if __name__=="__main__":
    unittest.main()
