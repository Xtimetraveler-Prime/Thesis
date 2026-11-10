"""M06 G3 generated combined AMD DWC-to-original-SC BFM tests, FAKE stubs.

The generated TB is destined for real owner XSim with authenticated vendor
RTL. Here CI checks Python contracts and optional Icarus SYNTAX ONLY
against clearly FAKE stub declarations (never executes fake model).
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
from m06_g3_generate_real_dwc_original_sc_bfm import render,exact_dwc_abi,ROLE
from m06_generate_original_mem_sc_bfm import required_ports,MODULE

REQ=required_ports()
VENDOR=[{"name":key,"direction":role,"packed_width":w}
        for key,(role,w) in REQ.items()]
DWC={"instances":{
    ip:{"role":"READ_ONLY" if sc=="S00" else "WRITE_ONLY",
        "pins":exact_dwc_abi(sc,REQ)}
    for ip,sc in ROLE
}}


def stub(name: str, pins: dict[str,dict]) -> str:
    names=", ".join(pins)
    decls=[]
    for pin,meta in pins.items():
        w=meta["width_bits"]
        rng=f"[{w-1}:0] " if w>1 else ""
        decls.append(f'{meta["direction"]} wire {rng}{pin};')
    return "module "+name+"("+names+");\n"+"\n".join(decls)+"\nendmodule\n"


def vendor_stub() -> str:
    declarations=["input wire aclk;","input wire aresetn;"]
    for name,(mode,w) in REQ.items():
        span=f"[{w-1}:0] " if w>1 else ""
        declarations.append(f"{mode} wire {span}{name};")
    return ("module "+MODULE+"(aclk,aresetn,"+
            ",".join(REQ)+");\n"+"\n".join(declarations)+"\nendmodule\n")


class M06ActualMeasuredDWCAndOriginalSmartConnectBFMTests(unittest.TestCase):
    def test_complete_measured_read36_and_write42_pin_contract(self):
        self.assertEqual(len(DWC["instances"]["m06_g3_read_dwc"]["pins"]),36)
        self.assertEqual(len(DWC["instances"]["m06_g3_write_dwc"]["pins"]),42)
        self.assertEqual(DWC["instances"]["m06_g3_read_dwc"]["pins"]
                         ["m_axi_rdata"]["width_bits"],256)
        self.assertEqual(DWC["instances"]["m06_g3_write_dwc"]["pins"]
                         ["s_axi_wstrb"]["width_bits"],4)
        self.assertEqual(DWC["instances"]["m06_g3_read_dwc"]["pins"]
                         ["s_axi_araddr"]["direction"],"input")
        self.assertEqual(DWC["instances"]["m06_g3_read_dwc"]["pins"]
                         ["m_axi_araddr"]["direction"],"output")
        self.assertEqual(DWC["instances"]["m06_g3_write_dwc"]["pins"]
                         ["s_axi_wdata"]["direction"],"input")
        self.assertEqual(DWC["instances"]["m06_g3_write_dwc"]["pins"]
                         ["m_axi_wdata"]["direction"],"output")

    def test_generated_testbench_requires_real_both_vendor_ip_and_shared_memory(self):
        src=render(DWC,VENDOR)
        self.assertIn(MODULE+" sc_dut",src)
        self.assertIn("m06_g3_read_dwc m06_g3_read_dwc_dut",src)
        self.assertIn("m06_g3_write_dwc m06_g3_write_dwc_dut",src)
        self.assertIn("SCRATCH_BYTES(65536)",src)
        self.assertIn("write32('hfffc,32'h01234567,4'b0101)",src)
        self.assertIn("read32('hfffc)",src)
        self.assertIn("M06_G3_REAL_DWC_ORIGINAL_SC_32TO256_XSIM_PASS",src)
        self.assertNotIn("m06_paged_rolling_replay",src)
        self.assertNotIn("program_hw_devices",src)
        self.assertNotIn("export_simulation",src)

    def test_negative_wrong_vendor_sc_or_dwc_pin_cannot_be_accepted(self):
        bad=[dict(x) for x in VENDOR]
        bad[0]={"name":bad[0]["name"],"direction":"output",
                "packed_width":999}
        with self.assertRaisesRegex(ValueError,"96-pin"):
            render(DWC,bad)
        broken={"instances":{k:{"role":v["role"],"pins":dict(v["pins"])}
                             for k,v in DWC["instances"].items()}}
        broken["instances"]["m06_g3_read_dwc"]["pins"].pop("m_axi_rdata")
        with self.assertRaisesRegex(ValueError,"36/42-pin"):
            render(broken,VENDOR)

    def test_negative_swapped_read_write_roles_rejected(self):
        fake={"instances":{k:dict(v) for k,v in DWC["instances"].items()}}
        fake["instances"]["m06_g3_read_dwc"]=dict(
            fake["instances"]["m06_g3_read_dwc"],role="WRITE_ONLY")
        with self.assertRaisesRegex(ValueError,"mode"):
            render(fake,VENDOR)

    def test_connected_owner_runner_bash_and_authentic_source_boundaries(self):
        runner=ROOT/"scripts/run_m06_g3_real_dwc_original_sc_xsim.sh"
        script=runner.read_text()
        self.assertIn("m06_g3_merge_vendor_sources.py",script)
        self.assertIn("m06_g3_generate_real_dwc_original_sc_bfm.py",script)
        self.assertIn("m06_g3_amd_dwc_evidence_audit.py",script)
        self.assertIn("m06_g3_real_amd_compile_order_audit.py",script)
        self.assertIn("m06_vendor_compile_plan.py",script)
        self.assertIn("m06_g3_real_dwc_original_sc_snapshot",script)
        self.assertIn("work.glbl",script)
        self.assertIn("sha256sum",script)
        self.assertIn("M06_G3_REAL_DWC_ORIGINAL_SC_32TO256_XSIM_PASS",script)
        self.assertNotIn("program_hw_devices",script)
        self.assertNotIn("write_bitstream",script)
        self.assertNotIn("vitis-run",script)
        self.assertNotIn("export_simulation",script)
        check=subprocess.run(["bash","-n",str(runner)],capture_output=True,
                             text=True,timeout=15)
        self.assertEqual(check.returncode,0,check.stderr)

    def test_generated_bench_syntax_against_FAKE_stubs_only_no_simulation(self):
        if not shutil.which("iverilog"):
            self.skipTest("Icarus not installed; original AMD test belongs on owner XSim")
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            tb=directory/"tb_m06_g3_real_dwc_original_sc.sv"
            tb.write_text(render(DWC,VENDOR))
            mocks=directory/"FAKE_STUB_SYNTAX_ONLY.sv"
            mocks.write_text(vendor_stub()+"\n"+"\n".join(
                stub(ip,entry["pins"]) for ip,entry in DWC["instances"].items()
            ))
            check=subprocess.run(["iverilog","-g2012","-tnull",
                "-s","tb_m06_g3_real_dwc_original_sc",
                str(tb),str(mocks),
                str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv")],
                capture_output=True,text=True,timeout=30)
            self.assertEqual(check.returncode,0,check.stdout+"\n"+check.stderr)


if __name__=="__main__":
    unittest.main()
