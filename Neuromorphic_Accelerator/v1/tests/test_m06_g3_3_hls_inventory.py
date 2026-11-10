"""Synthetic G3.3 HLS source-contract tests. NO real AMD vendor models simulated."""
from __future__ import annotations
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_3_hls_inventory import contract,source_inventory,TOP
from m06_g3_exact_original_pin_matrix import NEEDED
from m06_g3_generate_real_dwc_original_sc_bfm import exact_dwc_abi
from m06_generate_original_mem_sc_bfm import required_ports

def fixture():
    sc=required_ports()
    hls=dict(NEEDED)
    hls["ap_clk"]=("input",1)
    hls["ap_rst_n"]=("input",1)
    dwc={"instances":{name:{"role":role,"pins":exact_dwc_abi(port,sc)} for
         name,role,port in (("m06_g3_read_dwc","READ_ONLY","S00"),
                            ("m06_g3_write_dwc","WRITE_ONLY","S03"))}}
    files=[{"name":TOP+".v","sha256":"0"*64,"bytes":128,"language":"verilog"}]
    g32={"status":"PASS_G3_2_BFM_ONLY_ORIGINAL_AMD_XSIM_2025_2",
         "generated_hls_neural_rtl_connected":False,"evidence_zip_sha256":"1"*64}
    return hls,sc,dwc,files,g32

class M06G33InventoryTests(unittest.TestCase):
    def test_positive_measured_width_binding_not_claimed(self):
        report=contract(*fixture())
        self.assertEqual(report["status"],"REAL_HLS_RTL_AND_AMD_ABI_INVENTORIED_NOT_CONNECTED")
        self.assertEqual([x["original_si"] for x in report["hls_pin_matrix"]],["S00","S03"])
        self.assertFalse(report["g3_3_complete"])
        self.assertFalse(report["original_vendor_xsim_with_actual_HLS"])
        self.assertFalse(report["m06_complete"])
    def test_negative_missing_high_address_or_wrong_data_width(self):
        h,s,d,f,a=fixture();h["m_axi_gmem_read_ARADDR"]=("output",32)
        with self.assertRaisesRegex(ValueError,"measured HLS"):contract(h,s,d,f,a)
        h,s,d,f,a=fixture();h["m_axi_gmem_write_WDATA"]=("output",256)
        with self.assertRaisesRegex(ValueError,"measured HLS"):contract(h,s,d,f,a)
    def test_negative_mutated_dwc_or_original_sc_ports(self):
        h,s,d,f,a=fixture();d["instances"]["m06_g3_read_dwc"]["pins"].pop("m_axi_araddr")
        with self.assertRaisesRegex(ValueError,"AMD DWC ABI"):contract(h,s,d,f,a)
        h,s,d,f,a=fixture();s.pop("S00_AXI_araddr")
        with self.assertRaisesRegex(ValueError,"96-pin"):contract(h,s,d,f,a)
    def test_negative_fabricated_g32_hls_proof_and_bad_source_list(self):
        h,s,d,f,a=fixture();a["generated_hls_neural_rtl_connected"]=True
        with self.assertRaisesRegex(ValueError,"BFM-only"):contract(h,s,d,f,a)
        h,s,d,f,a=fixture();f.append(dict(f[0]))
        with self.assertRaisesRegex(ValueError,"duplicate"):contract(h,s,d,f,a)
    def test_positive_and_negative_source_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"syn"/"verilog";root.mkdir(parents=True)
            rtl=root/(TOP+".v")
            rtl.write_text("module "+TOP+"; endmodule\n")
            got=source_inventory(root)
            self.assertEqual(got[0]["sha256"],hashlib.sha256(rtl.read_bytes()).hexdigest())
            (root/"bad.v").symlink_to(rtl)
            with self.assertRaisesRegex(ValueError,"symlink"):source_inventory(root)
            (root/"bad.v").unlink()
            rtl.unlink()
            with self.assertRaisesRegex(ValueError,"top missing"):source_inventory(root)

if __name__=="__main__":
    unittest.main()
