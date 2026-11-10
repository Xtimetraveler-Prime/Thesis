"""G3.3.1 true-HLS linkage generator source tests.

Synthetic HLS/vendor modules exist ONLY to perform an Icarus COMPILE-only
syntax test. NEVER simulate fake IP or claim real AMD/HLS functional proof.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_3_generate_actual_hls_idle_tb import render,validate_inventory,TOP
from m06_g3_generate_real_dwc_original_sc_bfm import exact_dwc_abi
from m06_generate_original_mem_sc_bfm import MODULE,required_ports
from m06_g3_3_hls_inventory import source_inventory

AXIS={
    "AR": {"ADDR":64, "BURST":2, "CACHE":4, "ID":1, "LEN":8,
           "LOCK":2, "PROT":3, "QOS":4, "READY":1,
           "REGION":4, "SIZE":3, "USER":1, "VALID":1},
    "AW": {"ADDR":64, "BURST":2, "CACHE":4, "ID":1, "LEN":8,
           "LOCK":2, "PROT":3, "QOS":4, "READY":1,
           "REGION":4, "SIZE":3, "USER":1, "VALID":1},
    "B": {"ID":1,"READY":1,"RESP":2,"USER":1,"VALID":1},
    "R": {"DATA":32,"ID":1,"LAST":1,"READY":1,
          "RESP":2,"USER":1,"VALID":1},
    "W": {"DATA":32,"ID":1,"LAST":1,"READY":1,
          "STRB":4,"USER":1,"VALID":1},
}
CONTROL={"ARADDR":7,"ARREADY":1,"ARVALID":1,
         "AWADDR":7,"AWREADY":1,"AWVALID":1,
         "BREADY":1,"BRESP":2,"BVALID":1,
         "RDATA":32,"RREADY":1,"RRESP":2,"RVALID":1,
         "WDATA":32,"WREADY":1,"WSTRB":4,"WVALID":1}

def hls_pins():
    pins={"ap_clk":("input",1),"ap_rst_n":("input",1),"interrupt":("output",1)}
    for role in ("gmem_read","gmem_write"):
        for channel,parts in AXIS.items():
            for suffix,width in parts.items():
                port="m_axi_"+role+"_"+channel+suffix
                direction="input" if (
                    (channel in ("AR","AW","W") and suffix=="READY") or
                    (channel in ("R","B") and suffix!="READY")
                ) else "output"
                pins[port]=(direction,width)
    for suffix,width in CONTROL.items():
        # AXI-Lite HLS core is the SLAVE.
        direction="input" if suffix in (
            "ARADDR","ARVALID","AWADDR","AWVALID",
            "BREADY","RREADY","WDATA","WSTRB","WVALID"
        ) else "output"
        pins["s_axi_control_"+suffix]=(direction,width)
    for name,width,source in (("neurons",128,True),("synapses",192,True),
                              ("external_events",128,True),("trace",192,False),
                              ("metrics",256,False)):
        for suffix,w in (("TDATA",width),("TVALID",1),("TREADY",1)):
            pins[name+"_"+suffix]=("input" if source==(suffix!="TREADY")
                                    else "output",w)
    assert len(pins)==125, len(pins)
    return pins

def fixtures():
    sc=required_ports()
    vendor=[{"name":k,"direction":v[0],"packed_width":v[1]}
            for k,v in sc.items()]
    dwc={"instances":{name:{"role":"READ_ONLY" if scname=="S00" else "WRITE_ONLY",
                        "pins":exact_dwc_abi(scname,sc)}
        for name,scname in (("m06_g3_read_dwc","S00"),
                            ("m06_g3_write_dwc","S03"))}}
    return hls_pins(),dwc,vendor

def stub(module,pins):
    rows=[module+" stub (",
          "    "+",\n    ".join("."+name+"("+name+")" for name in pins)+");"]
    # Generate an explicit module header instead: cannot refer to body signals
    # as connection expressions in a module port list.
    rows=["module "+module+" (\n    "+",\n    ".join(pins)+"\n);"]
    for name,(d,w) in pins.items():
        rows.append(d+" "+(f"[{w-1}:0] " if w>1 else "")+name+";")
    rows.append("endmodule")
    return "\n".join(rows)+"\n"

class G33GeneratedHLSIdleTBTests(unittest.TestCase):
    def test_measured_125_pin_roles_and_original_exact_96_pin(self):
        pins,dwc,vendor=fixtures()
        tb=render(pins,dwc,vendor)
        self.assertEqual(tb.count(".ap_clk(clk)"),1)
        self.assertIn(TOP+" hls_dut",tb)
        self.assertEqual(tb.count("    .m_axi_gmem_write_WSTRB("),1)
        self.assertIn("m06_axi64_to32_read_guard rd_guard",tb)
        self.assertIn("m06_axi64_to32_write_guard wr_guard",tb)
        self.assertIn("m06_g3_read_dwc m06_g3_read_dwc_dut",tb)
        self.assertIn("m06_g3_write_dwc m06_g3_write_dwc_dut",tb)
        self.assertIn(MODULE+" sc_dut",tb)
        self.assertIn("m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536))",tb)
        self.assertIn("h_m_axi_gmem_read_ARLOCK!==2'b00",tb)
        self.assertIn("h_m_axi_gmem_write_AWLOCK!==2'b00",tb)
        self.assertIn("h_m_axi_gmem_read_AWVALID ||",tb)
        self.assertIn("h_m_axi_gmem_write_ARVALID)",tb)
        self.assertIn("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS",tb)
        self.assertIn("NO_START_NO_NEURAL_NO_DDR_NO_BOARD",tb)
        self.assertEqual(tb.count("hls_dut ("),1)
        for name in pins:
            self.assertIn("."+name+"(",tb)
        self.assertEqual(tb.count("s_axi_awregion"),1)

    def test_negative_original_dwc_contract_changed(self):
        pins,dwc,vendor=fixtures()
        dwc["instances"]["m06_g3_read_dwc"]["pins"].pop("s_axi_araddr")
        with self.assertRaisesRegex(ValueError,"DWC"):render(pins,dwc,vendor)
        pins,dwc,vendor=fixtures()
        vendor.pop()
        with self.assertRaisesRegex(ValueError,"96-pin"):render(pins,dwc,vendor)

    def test_genuine_hls_file_manifest_attested_and_bad_sha_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"work/hls/syn/verilog"
            root.mkdir(parents=True)
            pins=hls_pins()
            (root/(TOP+".v")).write_text(stub(TOP,pins))
            for n in range(39):
                (root/f"support_{n}.v").write_text(f"module support_{n}; endmodule\n")
            files=source_inventory(root)
            inv={"schema":"m06-g3-3-real-hls-rtl-interface-inventory-v1",
                 "status":"REAL_HLS_RTL_AND_AMD_ABI_INVENTORIED_NOT_CONNECTED",
                 "hls_top":TOP,"g3_2_verified_bfm_only":True,
                 "original_vendor_xsim_with_actual_HLS":False,
                 "g3_3_complete":False,
                 "hls_rtl_file_inventory":files,
                 "hls_complete_top_ports":{k:{"direction":v[0],"width_bits":v[1]}
                                          for k,v in pins.items()},
                 "hls_real_top_sha256":hashlib.sha256((root/(TOP+".v")).read_bytes()).hexdigest()}
            self.assertEqual(validate_inventory(inv,root),pins)
            (root/"support_3.v").write_text("module changed; endmodule\n")
            with self.assertRaisesRegex(ValueError,"hashes changed"):
                validate_inventory(inv,root)
            (root/"support_3.v").write_text("module support_3; endmodule\n")
            inv["hls_complete_top_ports"]["m_axi_gmem_read_ARADDR"]["width_bits"]=32
            with self.assertRaisesRegex(ValueError,"125-pin top changed"):
                validate_inventory(inv,root)

    def test_synthetic_iverilog_compile_only_real_guard_and_fake_stubs(self):
        if not shutil.which("iverilog"):
            self.skipTest("requires Icarus; M06 workflow reruns after install")
        pins,dwc,vendor=fixtures()
        sc=required_ports()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/"synthetic_HLS_NOT_REAL.v").write_text(stub(TOP,pins))
            scpins={"aclk":("input",1),"aresetn":("input",1),**sc}
            (folder/"synthetic_SC_NOT_REAL.v").write_text(stub(MODULE,scpins))
            bits=[]
            for ip in dwc["instances"]:
                d=dwc["instances"][ip]["pins"]
                bits.append(stub(ip,{key:(v["direction"],v["width_bits"])
                                     for key,v in d.items()}))
            (folder/"synthetic_DWC_NOT_REAL.v").write_text("\n".join(bits))
            (folder/"tb.sv").write_text(render(pins,dwc,vendor))
            compile_result=subprocess.run(
                ["iverilog","-g2012","-tnull","-s",
                 "tb_m06_g3_3_actual_hls_original_amd_idle",
                 str(folder/"synthetic_HLS_NOT_REAL.v"),
                 str(folder/"synthetic_SC_NOT_REAL.v"),
                 str(folder/"synthetic_DWC_NOT_REAL.v"),
                 str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                 str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                 str(folder/"tb.sv")],
                capture_output=True,text=True,timeout=30)
            self.assertEqual(compile_result.returncode,0,
                             compile_result.stdout+compile_result.stderr)
            self.assertNotIn("real AMD",compile_result.stdout.lower())
            # ABSOLUTE RULE: NEVER run 'vvp' with synthetic vendor stubs.

if __name__=="__main__":
    unittest.main()
