"""Source-only active actual-HLS AXI-Lite start/control TB + compile-only stub test.

FAKE AMD/HLS declarations are used ONLY with iverilog -tnull (NEVER vvp).
Functional acceptance MUST come from actual owner Vivado 2025.2 XSim.
"""
from __future__ import annotations
from pathlib import Path
import sys
import shutil
import hashlib
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))
from m06_g3_3_active_axilite_tb import active_tb
from m06_g3_3_hls_control_map import control_map,CONTROL
from m06_g3_3_generate_actual_hls_idle_tb import render,TOP
from m06_generate_original_mem_sc_bfm import MODULE, required_ports
from test_m06_g3_3_actual_hls_idle_link import fixtures,stub

def contract():
    pins,dwc,vendor=fixtures()
    idle=render(pins,dwc,vendor)
    inv={"status":"REAL_HLS_RTL_AND_AMD_ABI_INVENTORIED_NOT_CONNECTED",
         "hls_port_count":125,"g3_3_complete":False,
         "hls_complete_top_ports":{
             key:{"direction":role,"width_bits":width}
             for key,(role,width) in pins.items()}}
    ctrl={"schema":"m06-g3-3-genuine-generated-hls-control-map-v1",
          "status":"REAL_HLS_AXILITE_CONTROL_OFFSETS_SHA_ATTESTED",
          "ap_ctrl":0,"ap_return":16}
    return pins,dwc,vendor,idle,inv,ctrl

class M06RealHLSActiveAXILiteTests(unittest.TestCase):
    def test_positive_hls_original_amd_control_connected_but_no_neural(self):
        *_,idle,inv,ctrl=contract()
        s=active_tb(idle,inv,ctrl)
        self.assertIn("task automatic write_start;",s)
        self.assertIn("task automatic read_reg(",s)
        self.assertIn("h_s_axi_control_BRESP !== 2'b00",s)
        self.assertIn("read_reg(7'h10,observed_status)",s)
        self.assertIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_AXILITE_BAD_GEOMETRY_XSIM_PASS",s)
        self.assertIn("NO_CANONICAL_AXI_NO_NEURAL_PARITY_NO_BOARD",s)
        self.assertIn("module tb_m06_g3_3_actual_hls_original_amd_active;",s)
        self.assertNotIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS",s)
        self.assertNotIn("assign h_s_axi_control_AWVALID =",s)
        self.assertIn("reg h_s_axi_control_AWVALID=0;",s)
    def test_negative_control_map_and_port_mutations(self):
        *_,idle,inv,ctrl=contract()
        ctrl["ap_return"]=256
        with self.assertRaisesRegex(ValueError,"control register map"):active_tb(idle,inv,ctrl)
        *_,idle,inv,ctrl=contract()
        inv["hls_complete_top_ports"]["s_axi_control_AWADDR"]["width_bits"]=32
        with self.assertRaisesRegex(ValueError,"role drift"):active_tb(idle,inv,ctrl)
        *_,idle,inv,ctrl=contract()
        idle=idle.replace("wire h_s_axi_control_AWVALID;","wire wrong;")
        with self.assertRaisesRegex(ValueError,"declaration changed"):active_tb(idle,inv,ctrl)
    def test_grouped_generated_control_map_feeds_actual_hls_active_tb(self):
        # Regression for the exact G3.3 original-owner failure:
        # control_s_axi.v uses ONE comma-separated localparam statement.
        pins,dwc,vendor,idle,inv,_=contract()
        with tempfile.TemporaryDirectory() as tmp:
            rtl=Path(tmp)/"work/hls/syn/verilog"
            rtl.mkdir(parents=True)
            file=rtl/CONTROL
            names=[
                "AP_CTRL","GIE","IER","ISR","AP_RETURN",
                "CANONICAL_READ_WORDS_DATA_0","CANONICAL_READ_WORDS_DATA_1",
                "NEURON_COUNT_DATA_0","SYNAPSE_COUNT_DATA_0","TICKS_DATA_0",
                "DECAY_NUM_DATA_0","DECAY_DEN_DATA_0",
            ]
            offsets=[0,4,8,12,16,24,28,32,36,40,44,48]
            lines=["module original_style_fixture;","localparam"]
            lines.extend(
                " ADDR_"+name+" = 7'h"+format(addr,"02x")+
                ("," if i!=len(names)-1 else ";")
                for i,(name,addr) in enumerate(zip(names,offsets))
            )
            file.write_text("\n".join(lines+["endmodule"])+"\n")
            inventory={"hls_rtl_file_inventory":[
                {"name":CONTROL,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()}
            ]}
            parsed=control_map(inventory,rtl)
            self.assertEqual(parsed["ap_return"],16)
            actual=active_tb(idle,inv,parsed)
            self.assertIn("read_reg(7'h10,observed_status)",actual)
            self.assertIn("write_start();",actual)
            self.assertNotIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS",actual)
            # A different *measured* AP_RETURN offset must flow through,
            # never be hardcoded to 0x10 in the generated testbench.
            changed=file.read_text().replace("ADDR_AP_RETURN = 7'h10",
                                              "ADDR_AP_RETURN = 7'h14")
            file.write_text(changed)
            inventory["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(file.read_bytes()).hexdigest()
            parsed=control_map(inventory,rtl)
            self.assertEqual(parsed["ap_return"],20)
            self.assertIn("read_reg(7'h14,observed_status)",
                          active_tb(idle,inv,parsed))

    def test_compile_only_with_real_guard_and_ram_and_fake_ip_stubs(self):
        if not shutil.which("iverilog"):
            self.skipTest("requires Icarus, explicitly rerun after apt in M06 CI")
        pins,dwc,vendor,idle,inv,ctrl=contract()
        code=active_tb(idle,inv,ctrl)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            (out/"tb.sv").write_text(code)
            (out/"FAKE_HLS_DECLARATIONS_ONLY.v").write_text(stub(TOP,pins))
            scpins={"aclk":("input",1),"aresetn":("input",1),**required_ports()}
            (out/"FAKE_SC_DECLARATIONS_ONLY.v").write_text(stub(MODULE,scpins))
            modules=[]
            for ip,data in dwc["instances"].items():
                portspec={n:(item["direction"],item["width_bits"])
                          for n,item in data["pins"].items()}
                modules.append(stub(ip,portspec))
            (out/"FAKE_DWC_DECLARATIONS_ONLY.v").write_text("\n".join(modules))
            p=subprocess.run(
                ["iverilog","-g2012","-tnull","-s",
                 "tb_m06_g3_3_actual_hls_original_amd_active",
                 str(out/"FAKE_HLS_DECLARATIONS_ONLY.v"),
                 str(out/"FAKE_SC_DECLARATIONS_ONLY.v"),
                 str(out/"FAKE_DWC_DECLARATIONS_ONLY.v"),
                 str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                 str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                 str(out/"tb.sv")],
                capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            # Never execute an Icarus vvp against fake/vendor placeholder RTL.

if __name__=="__main__":
    unittest.main()
