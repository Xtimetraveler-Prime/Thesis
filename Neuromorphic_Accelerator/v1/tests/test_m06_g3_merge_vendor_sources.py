"""SYNTHETIC ONLY M06 actual AMD DWC + D3 source-merge tests.

These fixtures are NOT vendor RTL and are NEVER executed as real AMD IP.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_merge_vendor_sources import merge


def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fixture(parent:Path):
    d3=parent/"neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    dwc=parent/"m06_g3_real_amd_dwc_SYNTHETIC_ONLY"
    d3.mkdir();dwc.mkdir()
    vlog=[]
    for i in range(40):
        file=d3/f"original_d3_{i:02d}.v"
        file.write_text(f"// SYNTHETIC only\nmodule original_d3_{i:02d}; endmodule\n")
        vlog.append(str(file))
    original={
        "schema":"m06-original-vivado-compile-plan-v2",
        "original_D3":str(d3),
        "vendor_XSim_executed":False,
        "verilog_files":vlog,
        "vhdl_files":[],
        "include_directories":[str(d3)]
    }
    shared=[]
    for name,role in (("m06_g3_read_dwc","READ_ONLY"),
                      ("m06_g3_write_dwc","WRITE_ONLY")):
        sub=dwc/name;sub.mkdir()
        hdl=sub/"generic_baseblocks_v2_1_vl_rfs.v"
        hdl.write_text("// identical original AMD-like SYNTHETIC fixture\n")
        header=sub/"axi_infrastructure_v1_1_0.vh"
        header.write_text("// identical header SYNTHETIC fixture\n")
        wrapper=sub/(name+".v")
        wrapper.write_text("// FAKE wrapper - NEVER VENDOR\n")
        shared.append((name,role,hdl,header,wrapper))
    instances={}
    for name,role,hdl,header,wrapper in shared:
        files=[]
        for path,kind in ((hdl,"Verilog"),(header,"Verilog Header"),
                          (wrapper,"Verilog")):
            files.append({"path":str(path),"language":kind,"sha256":sha(path)})
        instances[name]={"role":role,"real_vendor_wrapper_found":True,
                         "real_vendor_include_found":True,
                         "ordered_simulation_files":files}
    audit={
        "schema":"m06-g3-real-amd-read-only-compile-order-audit-v1",
        "status":"REAL_AMD_XSIM_SOURCES_RECORDED_NOT_EXPORTED_NOT_COMPILED",
        "owner_original_ip_folder":str(dwc),
        "m06_complete":False,
        "instances":instances,
    }
    return original,audit,shared


class M06GenuineAMDSourceMergeSyntheticTests(unittest.TestCase):
    def test_positive_identical_library_collapses_but_both_tops_remain(self):
        with tempfile.TemporaryDirectory() as d:
            original,audit,shared=fixture(Path(d))
            out=merge(original,audit)
            self.assertEqual(len(out["verilog_files"]),43)
            self.assertEqual(len(out["vhdl_files"]),0)
            self.assertEqual(len(out["deduplicated_same_name_same_sha"]),2)
            self.assertEqual(len(out["two_real_dwc_tops"]),2)
            self.assertFalse(out["genuine_combined_xsim"])
            self.assertFalse(out["hls_core_bound"])
            self.assertFalse(out["m06_complete"])

    def test_negative_same_module_basename_different_sha_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            original,audit,shared=fixture(Path(d))
            wrong=shared[1][2]
            wrong.write_text("different AMD lib version, DO NOT SILENTLY CHOOSE\n")
            audit["instances"][shared[1][0]]["ordered_simulation_files"][0]["sha256"]=sha(wrong)
            with self.assertRaisesRegex(ValueError,"DIFFERENT SHA"):
                merge(original,audit)

    def test_negative_modified_vendor_source_fails_live_digest(self):
        with tempfile.TemporaryDirectory() as d:
            original,audit,shared=fixture(Path(d))
            shared[0][2].write_text("TAMPERED ORIGINAL HDL\n")
            with self.assertRaisesRegex(ValueError,"hash"):
                merge(original,audit)

    def test_negative_vendor_file_from_untrusted_location_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            original,audit,shared=fixture(Path(d))
            evil=Path(d)/"wrong_file.v"
            evil.write_text("BAD SOURCE OUTSIDE OWNER PROJECT\n")
            name=shared[1][0]
            audit["instances"][name]["ordered_simulation_files"][2].update(
                path=str(evil),sha256=sha(evil))
            with self.assertRaisesRegex(ValueError,"origin"):
                merge(original,audit)

    def test_negative_missing_second_converter_or_false_vendor_scope(self):
        with tempfile.TemporaryDirectory() as d:
            original,audit,shared=fixture(Path(d))
            audit["instances"].pop("m06_g3_write_dwc")
            with self.assertRaisesRegex(ValueError,"two real"):
                merge(original,audit)
        with tempfile.TemporaryDirectory() as d:
            original,audit,shared=fixture(Path(d))
            original["vendor_XSim_executed"]=True
            with self.assertRaisesRegex(ValueError,"original D3"):
                merge(original,audit)


if __name__=="__main__":
    unittest.main()
