"""Source-only gate for prospective genuine HLS + AMD positive-16 TB.

Synthetic declarations are syntax-only; never substitute for Vivado vendor IP.
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
from m06_g3_3_positive16_axilite_tb import positive_tb
from test_m06_g3_3_active_axilite_tb import contract
from test_m06_g3_3_actual_hls_idle_link import stub
from m06_generate_original_mem_sc_bfm import MODULE,required_ports
from m06_paged_hls_port_audit import TOP

# Measured genuine original Vitis 2025.2 register-map offsets from prior
# owner active-control evidence; tests must NOT cause generator to assume them.
MEASURED={
    "AP_CTRL":0,"AP_RETURN_0":16,
    "CANONICAL_READ_WORDS_DATA_0":24,
    "CANONICAL_READ_WORDS_DATA_1":28,
    "CANONICAL_WRITE_WORDS_DATA_0":36,
    "CANONICAL_WRITE_WORDS_DATA_1":40,
    "NEURON_COUNT_DATA_0":48,
    "SYNAPSE_COUNT_DATA_0":56,
    "EXTERNAL_COUNT_DATA_0":64,
    "TICKS_DATA_0":72,
    "DECAY_NUM_DATA_0":80,
    "DECAY_DEN_DATA_0":88,
    "RESIDENT_SLOTS_DATA_0":96,
    "CANONICAL_FIRST_NEURON_DATA_0":104,
}

def make():
    pins,dwc,vendor,idle,inv,ctrl=contract()
    ctrl["register_offsets"]=dict(MEASURED)
    return pins,dwc,vendor,idle,inv,ctrl

class Positive16HLSOriginalAMDSyntaxOnly(unittest.TestCase):
    def test_positive_observability_and_no_false_neural_parity(self):
        _,_,_,idle,inv,ctrl=make()
        sv=positive_tb(idle,inv,ctrl)
        self.assertIn("module tb_m06_g3_3_actual_hls_original_amd_positive16;",sv)
        self.assertIn("write_reg(7'h30,32'd16)",sv)
        self.assertIn("write_reg(7'h68,32'd0)",sv)
        self.assertIn("read_reg(7'h10,observed_status)",sv)
        self.assertIn("trace_count !== 16",sv)
        self.assertIn("metrics_count !== 1",sv)
        self.assertIn("ram.mem[0] !== 8'h01",sv)
        self.assertIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_POSITIVE16_XSIM_PASS",sv)
        self.assertNotIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS",sv)
        self.assertNotIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_AXILITE_BAD_GEOMETRY_XSIM_PASS",sv)
        self.assertNotIn("assign h_neurons_TVALID =",sv)
        self.assertIn("NO_M02_M03_PARITY_NO_BOARD",sv)

    def test_missing_or_ambiguous_original_control_register_fails_closed(self):
        _,_,_,idle,inv,ctrl=make()
        del ctrl["register_offsets"]["CANONICAL_WRITE_WORDS_DATA_0"]
        with self.assertRaisesRegex(ValueError,"missing/invalid"):
            positive_tb(idle,inv,ctrl)
        _,_,_,idle,inv,ctrl=make()
        ctrl["register_offsets"]["TICKS_DATA_0"]=48
        with self.assertRaisesRegex(ValueError,"duplicate"):
            positive_tb(idle,inv,ctrl)
        _,_,_,idle,inv,ctrl=make()
        ctrl["ap_return"]=20
        with self.assertRaisesRegex(ValueError,"identity drift"):
            positive_tb(idle,inv,ctrl)

    def test_original_offsets_are_dynamic_not_guessed(self):
        _,_,_,idle,inv,ctrl=make()
        ctrl["register_offsets"]["NEURON_COUNT_DATA_0"]=112
        sv=positive_tb(idle,inv,ctrl)
        self.assertIn("write_reg(7'h70,32'd16)",sv)
        self.assertNotIn("write_reg(7'h30,32'd16)",sv)

    def test_compile_only_using_fake_hls_vendor_declarations(self):
        if not shutil.which("iverilog"):
            self.skipTest("requires Icarus; CI must install it")
        pins,dwc,vendor,idle,inv,ctrl=make()
        sv=positive_tb(idle,inv,ctrl)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            (out/"tb.sv").write_text(sv)
            (out/"FAKE_HLS_DECLARATIONS_ONLY.v").write_text(stub(TOP,pins))
            scpins={"aclk":("input",1),"aresetn":("input",1),**required_ports()}
            (out/"FAKE_SC_DECLARATIONS_ONLY.v").write_text(stub(MODULE,scpins))
            modules=[]
            for ip,data in dwc["instances"].items():
                portspec={n:(item["direction"],item["width_bits"])
                          for n,item in data["pins"].items()}
                modules.append(stub(ip,portspec))
            (out/"FAKE_DWC_DECLARATIONS_ONLY.v").write_text("\n".join(modules))
            p=subprocess.run([
                "iverilog","-g2012","-tnull","-s",
                "tb_m06_g3_3_actual_hls_original_amd_positive16",
                str(out/"FAKE_HLS_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_SC_DECLARATIONS_ONLY.v"),
                str(out/"FAKE_DWC_DECLARATIONS_ONLY.v"),
                str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                str(out/"tb.sv"),
            ],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            # No vvp against fake AMD/HLS blocks. Functional truth is owner XSim.

if __name__=="__main__":
    unittest.main()
