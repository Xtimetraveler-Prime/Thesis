"""SYNTHETIC owner-source layout tests: no Vivado or vendor RTL execution.

Exercises the TRUE format observed in the 2026-11-09 failed Vivado log:
13 ordered read-IP simulation files, including native Verilog/VHDL/header
and the sim/NAME.v AMD wrapper, before export_simulation crashed.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_real_amd_compile_order_audit import IP_ROLES, TAIL, audit

# First user's actual compile-order record from the genuine Vivado log
# established that Verilog Header is a real FILE_TYPE. Data below are
# synthetic files and must not be mistaken for AMD model source.
SOURCES = (
    ("Verilog", "hdl/generic_baseblocks_v2_1_vl_rfs.v"),
    ("Verilog", "simulation/fifo_generator_vlog_beh.v"),
    ("VHDL", "hdl/fifo_generator_v13_2_rfs.vhd"),
    ("Verilog", "hdl/fifo_generator_v13_2_rfs.v"),
    ("Verilog", "hdl/axi_data_fifo_v2_1_vl_rfs.v"),
    ("Verilog Header", "hdl/axi_infrastructure_v1_1_0.vh"),
    ("Verilog", "hdl/axi_infrastructure_v1_1_vl_rfs.v"),
    ("Verilog", "hdl/axi_register_slice_v2_1_vl_rfs.v"),
    ("Verilog", "hdl/axi_protocol_converter_v2_1_vl_rfs.v"),
    ("Verilog", "hdl/axi_clock_converter_v2_1_vl_rfs.v"),
    ("Verilog", "simulation/blk_mem_gen_v8_4.v"),
    ("Verilog", "hdl/axi_dwidth_converter_v2_1_vl_rfs.v"),
    ("Verilog", "sim/{name}.v"),
)


def fixture(root: Path):
    owner=root/"m06_g3_real_amd_dwc_SYNTHETIC"
    owner.mkdir()
    prj=owner/"new_scratch_project"
    prj.mkdir()
    rows=["original_vendor_simulation_files_only\tNOT_HLS_OR_SMARTCONNECT_CONNECTED"]
    paths={}
    for name,role in IP_ROLES.items():
        rows.extend((f"ip_name\t{name}",f"ip_mode\t{role}",
                     f"ip_sim_file_count\t{len(SOURCES)}"))
        paths[name]=[]
        for kind,rel in SOURCES:
            file=prj/"m06_g3_amd_dwc.gen"/"sources_1"/"ip"/name/rel.format(name=name)
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text("SYNTHETIC FIXTURE NOT AMD IP\n")
            paths[name].append(file)
            rows.append(f"{name}\t{kind}\t{file}")
    for key,value in TAIL.items():
        rows.append(f"{key}\t{value}")
    return owner,paths,"\n".join(rows)+"\n"


class M06G3RealCompileOrderSyntheticTests(unittest.TestCase):
    def test_positive_real_style_13files_each_role_no_vendor_claim(self):
        with tempfile.TemporaryDirectory() as d:
            owner,paths,log=fixture(Path(d))
            result=audit(log,owner)
            self.assertEqual(len(result["ordered_paths"]),26)
            self.assertEqual(result["instances"]["m06_g3_read_dwc"]["sim_file_count"],13)
            self.assertTrue(result["instances"]["m06_g3_write_dwc"]["real_vendor_include_found"])
            self.assertEqual(result["status"],
                "REAL_AMD_XSIM_SOURCES_RECORDED_NOT_EXPORTED_NOT_COMPILED")
            self.assertFalse(result["vendor_converter_xsim_run"])
            self.assertFalse(result["m06_complete"])

    def test_negative_missing_source_and_modified_wrapper_path(self):
        with tempfile.TemporaryDirectory() as d:
            owner,paths,log=fixture(Path(d))
            paths["m06_g3_write_dwc"][3].unlink()
            with self.assertRaisesRegex((OSError,ValueError),""):
                audit(log,owner)
        with tempfile.TemporaryDirectory() as d:
            owner,paths,log=fixture(Path(d))
            corrupted=log.replace("/sim/m06_g3_read_dwc.v",
                                  "/sim/something_else.v")
            with self.assertRaises((OSError,ValueError)):
                audit(corrupted,owner)

    def test_negative_wrong_role_and_bad_count(self):
        with tempfile.TemporaryDirectory() as d:
            owner,paths,log=fixture(Path(d))
            with self.assertRaisesRegex(ValueError,"role"):
                audit(log.replace("ip_mode\tWRITE_ONLY",
                                  "ip_mode\tREAD_ONLY"),owner)
            with self.assertRaisesRegex(ValueError,"role, order|file count|corrupt"):
                audit(log.replace("ip_sim_file_count\t13",
                                  "ip_sim_file_count\t14",1),owner)

    def test_negative_missing_header_or_repeated_source(self):
        with tempfile.TemporaryDirectory() as d:
            owner,paths,log=fixture(Path(d))
            replaced=log.replace("Verilog Header", "Verilog",1)
            with self.assertRaisesRegex(ValueError,"path/type mismatch|header"):
                audit(replaced,owner)
            # Same path twice within one IP is a hard rejection.
            first=str(paths["m06_g3_read_dwc"][0])
            second=str(paths["m06_g3_read_dwc"][1])
            with self.assertRaisesRegex(ValueError,"duplicate"):
                audit(log.replace(second,first,1),owner)

    def test_negative_real_vendor_source_outside_original_project(self):
        with tempfile.TemporaryDirectory() as d:
            owner,paths,log=fixture(Path(d))
            escaped=Path(d)/"EXTERNAL_STALE_AMD.v"
            escaped.write_text("wrong original vendor file\n")
            with self.assertRaisesRegex(ValueError,"outside original project"):
                audit(log.replace(str(paths["m06_g3_read_dwc"][0]),str(escaped)),owner)

    def test_negative_false_scope_or_extra_rows(self):
        with tempfile.TemporaryDirectory() as d:
            owner,paths,log=fixture(Path(d))
            with self.assertRaisesRegex(ValueError,"boundary marker"):
                audit(log.replace("vendor_converter_xsim_run\tFALSE",
                                  "vendor_converter_xsim_run\tTRUE"),owner)
            with self.assertRaisesRegex(ValueError,"unexpected extra"):
                audit(log+"extra\tfield\n",owner)

    def test_cli_only_writes_when_real_path_contract_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            owner,paths,log=fixture(root)
            src=root/"02_genuine_dwc_sim_compile_order.tsv"
            src.write_text(log)
            out=root/"06_manifest.json";listing=root/"03_paths.txt"
            script=ROOT/"scripts/m06_g3_real_amd_compile_order_audit.py"
            cmd=[sys.executable,str(script),"--compile-order",str(src),
                 "--owner-dwc",str(owner),"--output",str(out),
                 "--paths-output",str(listing)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue(out.exists())
            self.assertEqual(len(listing.read_text().splitlines()),26)
            again=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
            self.assertEqual(again.returncode,2)
            self.assertIn("new path",again.stderr)


if __name__=="__main__":
    unittest.main()
