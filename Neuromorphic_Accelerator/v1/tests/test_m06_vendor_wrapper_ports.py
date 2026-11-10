"""Original generated IP HDL header scanner tests, SYNTHETIC ONLY."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_vendor_wrapper_ports import D3_NAME, inspect


def fixture(where: Path, *, body: str | None = None):
    orig = where/D3_NAME
    xpr = orig/"13_file_backed_project/m05_d3_output_products.xpr"
    vendor = orig/"13_file_backed_project/m05_d3_output_products.gen/sources_1/bd/sample/ip/sample_mem_sc_0_0/sim/sample_mem_sc_0_0.sv"
    vendor.parent.mkdir(parents=True)
    xpr.parent.mkdir(parents=True,exist_ok=True)
    xpr.write_text("UNTRUSTED SYNTHETIC")
    vendor.write_text(
        body if body is not None else
        "module sample_mem_sc_0_0 (\n"
        "    input wire aclk,\n"
        "    input wire aresetn,\n"
        "    input wire [31:0] S00_AXI_araddr,\n"
        "    output logic [255:0] S00_AXI_rdata,\n"
        "    input wire [255:0] S03_AXI_wdata,\n"
        "    output wire [127:0] M00_AXI_wdata,\n"
        "    input wire [127:0] M00_AXI_rdata\n"
        ");\nendmodule\n")
    report = where/"synthetic_report.txt"
    report.write_text(
        f"SOURCE_XPR|{xpr.resolve()}\n"
        f"SIM_SOURCE|{vendor.resolve()}\n"
        "RESULT|ORIGINAL_PORTS_CAPTURED_FOR_ONE_VENDOR_FUNCTIONAL_XSIM_TRIAL\n")
    return orig,report,vendor


class OriginalVendorHeaderTests(unittest.TestCase):
    def test_actual_style_vendor_ansi_port_widths_from_original_bounded_source(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, vendor = fixture(Path(d))
            value = inspect(orig,report)
            self.assertEqual(value["status"],"MODULE_HEADERS_FOUND_NOT_COMPILED")
            self.assertEqual(value["wrapper_candidate_count"],1)
            self.assertEqual(value["wrappers_with_ansi_axi_ports"],1)
            wrapper=value["wrapper_candidates"][0]
            ports={p["name"]:p for p in wrapper["ansi_axi_ports"]}
            self.assertEqual(ports["S00_AXI_araddr"]["packed_width"],32)
            self.assertEqual(ports["S00_AXI_rdata"]["packed_width"],256)
            self.assertEqual(ports["S03_AXI_wdata"]["packed_width"],256)
            self.assertEqual(ports["M00_AXI_wdata"]["packed_width"],128)
            self.assertEqual(ports["M00_AXI_rdata"]["packed_width"],128)
            self.assertTrue(wrapper["port_header_only_not_elaborated"])
            self.assertEqual(value["vendor_functional_axi"],"NOT_EXECUTED")

    def test_original_verilog1995_non_ansi_declarations_visible_in_module_body(self):
        text = """
// module FAKE (input [999:0] S00_AXI_rdata); inside COMMENT
module sample_mem_sc_0_0 (
    aclk, aresetn, S00_AXI_araddr, S00_AXI_rdata,
    S03_AXI_wdata, M00_AXI_wdata, M00_AXI_rdata
);
  input wire aclk;
  input aresetn;
  input [31:0] S00_AXI_araddr;
  output reg [255:0] S00_AXI_rdata;
  input wire [255:0] S03_AXI_wdata;
  output [127:0] M00_AXI_wdata;
  input [127:0] M00_AXI_rdata;
endmodule
"""
        with tempfile.TemporaryDirectory() as d:
            original, report, _ = fixture(Path(d), body=text)
            result = inspect(original, report)
            self.assertEqual(result["status"], "MODULE_HEADERS_FOUND_NOT_COMPILED")
            self.assertEqual(result["wrappers_with_ansi_axi_ports"], 1)
            instance = result["wrapper_candidates"][0]
            self.assertEqual(instance["declaration_style"], "NON_ANSI")
            ports = {p["name"]: p for p in instance["ansi_axi_ports"]}
            self.assertEqual(len(ports), 5)
            self.assertEqual(ports["S00_AXI_araddr"]["packed_width"], 32)
            self.assertEqual(ports["S00_AXI_rdata"]["direction"], "output")
            self.assertEqual(ports["S00_AXI_rdata"]["packed_width"], 256)
            self.assertEqual(ports["S03_AXI_wdata"]["packed_width"], 256)
            self.assertEqual(ports["M00_AXI_wdata"]["packed_width"], 128)
            self.assertEqual(ports["M00_AXI_rdata"]["packed_width"], 128)
            self.assertFalse(result["vendor_functional_axi"] == "PASS")

    def test_parameterized_original_header_preserves_unresolved_width(self):
        text = """
module sample_mem_sc_0_0 #(parameter DATA_W=256) (
   input wire [DATA_W-1:0] S00_AXI_rdata,
   output wire [127:0] M00_AXI_wdata,
   input aclk
);
endmodule
"""
        with tempfile.TemporaryDirectory() as d:
            original, report, _ = fixture(Path(d), body=text)
            result = inspect(original, report)
            self.assertEqual(result["wrappers_with_ansi_axi_ports"], 1)
            found = {x["name"]: x for x in result["wrapper_candidates"][0]["ansi_axi_ports"]}
            self.assertIsNone(found["S00_AXI_rdata"]["packed_width"])
            self.assertEqual(found["S00_AXI_rdata"]["width_status"],
                             "UNRESOLVED_PARAMETER_EXPRESSION")
            self.assertEqual(found["M00_AXI_wdata"]["packed_width"], 128)

    def test_original_report_rejects_other_xpr_and_missing_completion(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,vendor=fixture(Path(d))
            txt=report.read_text()
            report.write_text(txt.replace("m05_d3_output_products.xpr","wrong.xpr"))
            with self.assertRaisesRegex(ValueError,"exact original XPR"):
                inspect(orig,report)
            report.write_text(txt.replace("RESULT|ORIGINAL_PORTS_CAPTURED",
                                          "RESULT|NOT_CAPTURED"))
            with self.assertRaisesRegex(ValueError,"capture incomplete"):
                inspect(orig,report)

    def test_rejects_arbitrary_source_path_outside_original_even_if_report_lists_it(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,vendor=fixture(Path(d))
            outside=Path(d)/"not_original_mem_sc_fake.sv"
            outside.write_text(vendor.read_text())
            report.write_text(report.read_text().replace(str(vendor.resolve()),
                                                       str(outside.resolve())))
            value=inspect(orig,report)
            self.assertEqual(value["source_candidates_from_previous_vivado_report"],0)
            self.assertEqual(value["status"],"MODEL_HEADER_UNAVAILABLE_NO_GUESSED_WRAPPER")
            self.assertFalse(value["wrapper_candidates"])

    def test_module_header_unavailable_does_not_invent_compiled_vendor_model(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,vendor=fixture(Path(d),body="module sample_mem_sc_0_0; endmodule\n")
            value=inspect(orig,report)
            self.assertEqual(value["status"],"MODEL_HEADER_UNAVAILABLE_NO_GUESSED_WRAPPER")
            self.assertEqual(value["wrapper_candidate_count"],0)
            self.assertEqual(value["vendor_functional_axi"],"NOT_EXECUTED")

    def test_cli_writes_exclusive_json_and_reports_bounded_header_probe(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,vendor=fixture(Path(d))
            dest=Path(d)/"read_only_header.json"
            args=[sys.executable,str(ROOT/"scripts/m06_vendor_wrapper_ports.py"),
                  "--original",str(orig),"--report",str(report),"--output",str(dest)]
            first=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(json.loads(dest.read_text())["wrappers_with_ansi_axi_ports"],1)
            self.assertIn("REAL VENDOR XSIM NOT RUN",first.stdout)
            again=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(again.returncode,2)
            self.assertIn("exclusive",again.stderr)


if __name__ == "__main__":
    unittest.main()
