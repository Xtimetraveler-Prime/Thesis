"""M06 G3 source-only tests: official Vivado IP export + real SIM ABI parser.

No Vivado, no vendor IP model, no HLS neural top and no board is run by
these tests; only the source contract and synthetic Verilog headers.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_capture_dwc_ports import parse_module, verify_role_pins, EXPECTED


def header(role: str) -> str:
    name="m06_g3_read_dwc" if role=="READ_ONLY" else "m06_g3_write_dwc"
    declarations=[]
    for pin,(direction,width) in EXPECTED[role].items():
        bus=f"[{width-1}:0] " if width>1 else ""
        declarations.append(f"    {direction} wire {bus}{pin}")
    return "module "+name+" (\n"+",\n".join(declarations)+"\n);\nendmodule\n"


class M06G3AMDExporterContractTests(unittest.TestCase):
    def test_synthetic_valid_read_write_verilog_headers(self):
        for role in EXPECTED:
            with self.subTest(role=role):
                name="m06_g3_read_dwc" if role=="READ_ONLY" else "m06_g3_write_dwc"
                pins=parse_module(header(role),name)
                verify_role_pins(pins,role)
                self.assertEqual(pins,EXPECTED[role])

    def test_synthetic_rejects_real_width_and_direction_changes(self):
        for role in EXPECTED:
            name="m06_g3_read_dwc" if role=="READ_ONLY" else "m06_g3_write_dwc"
            example=header(role)
            pins=parse_module(example,name)
            entry=next(iter(EXPECTED[role]))
            value=pins[entry]
            pins[entry]=(value[0],value[1]*2)
            with self.assertRaisesRegex(ValueError,"role/pin/width"):
                verify_role_pins(pins,role)

    def test_synthetic_rejects_duplicate_or_missing_headers(self):
        name="m06_g3_read_dwc"
        with self.assertRaisesRegex(ValueError,"exactly one"):
            parse_module(header("READ_ONLY")+header("READ_ONLY"),name)
        with self.assertRaisesRegex(ValueError,"named pins"):
            parse_module(header("READ_ONLY").replace("output wire s_axi_arready", "wire s_axi_arready"),name)
        with self.assertRaisesRegex(ValueError,"top"):
            parse_module(header("READ_ONLY"),"unexpected_name")

    def test_owner_source_only_no_xsim_board_original_d3_mutation(self):
        tcl=(ROOT/"scripts/m06_g3_export_real_dwc_xsim.tcl").read_text()
        runner=(ROOT/"scripts/run_m06_g3_amd_xsim_export.sh").read_text()
        self.assertIn("open_project -read_only",tcl)
        self.assertIn("get_files -compile_order sources -used_in simulation -of_objects $ip",tcl)
        self.assertNotIn("export_simulation -simulator",tcl)
        self.assertIn("M06_G3_REAL_AMD_DWC_SIM_COMPILE_ORDER_RECORDED_NOT_CONNECTED_NOT_SIMULATED",tcl)
        self.assertNotIn("launch_simulation",tcl)
        self.assertNotIn("program_hw_devices",tcl)
        self.assertNotIn("write_bitstream",tcl)
        self.assertIn("sha256sum -c",runner)
        self.assertIn("scripts/m06_g3_capture_dwc_ports.py",runner)
        self.assertIn("scripts/m06_g3_real_amd_compile_order_audit.py",runner)
        self.assertIn("03_real_amd_sim_source_paths.txt",runner)
        self.assertIn("06_amd_sim_compile_order_audit.json",runner)
        self.assertIn("M06_G3_REAL_AMD_DWC_SIM_COMPILE_ORDER_RECORDED_NOT_CONNECTED_NOT_SIMULATED",runner)
        self.assertNotIn("xsim m06_",runner)

    def test_runner_real_bash_and_tcl_syntax_only(self):
        result=subprocess.run(["bash","-n",str(ROOT/"scripts/run_m06_g3_amd_xsim_export.sh")],
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        if shutil.which("tclsh"):
            # This is a syntax COMPLETE check only; vendor commands aren't
            # invoked and no original owner project is opened.
            # Check Tcl brace completeness without executing Vivado commands.
            script=ROOT/"scripts/m06_g3_export_real_dwc_xsim.tcl"
            code='''set f [open {'''+str(script)+'''} r]
set s [read $f]
close $f
if {![info complete $s]} {exit 3}
puts M06_G3_TCL_SYNTAX_COMPLETE
'''
            check=subprocess.run(["tclsh"],input=code,text=True,capture_output=True,
                                 timeout=10)
            self.assertEqual(check.returncode,0,check.stderr)
            self.assertIn("M06_G3_TCL_SYNTAX_COMPLETE",check.stdout)


if __name__=="__main__":
    unittest.main()
