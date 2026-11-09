"""Host-only original 96-pin vendor BFM generator tests; never vendor XSim PASS."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_generate_original_mem_sc_bfm import (
    MODULE, ROOT_NAME, SIM_PATH, BD_PATH, SIM_SHA, BD_SHA, REPORT_SHA,
    required_ports, original_ports, render,
)


def fake_port_metadata():
    return [{"name":k,"direction":v[0],"packed_width":v[1],
             "width_status":"EXACT_LITERAL"}
            for k,v in required_ports().items()]


class OriginalGenuineVendorBFMTests(unittest.TestCase):
    def test_exact_original_96_pin_roles_and_widths(self):
        ports=required_ports()
        self.assertEqual(len(ports),96)
        self.assertEqual(ports["S03_AXI_wdata"],("input",256))
        self.assertEqual(ports["S03_AXI_wstrb"],("input",32))
        self.assertEqual(ports["S03_AXI_awlen"],("input",8))
        self.assertEqual(ports["S00_AXI_rdata"],("output",256))
        self.assertEqual(ports["S02_AXI_arready"],("output",1))
        self.assertEqual(ports["M00_AXI_rdata"],("input",128))
        self.assertEqual(ports["M00_AXI_wdata"],("output",128))
        self.assertEqual(ports["M00_AXI_wstrb"],("output",16))
        self.assertEqual(ports["M00_AXI_awaddr"],("output",49))
        self.assertEqual(ports["M00_AXI_arlen"],("output",8))
        self.assertNotIn("S00_AXI_wdata",ports)
        self.assertNotIn("S03_AXI_rdata",ports)
        self.assertFalse(any(x.lower().endswith(("awid", "arid", "bid", "rid",
                             "awuser", "aruser", "buser", "ruser", "wuser"))
                             for x in ports))

    def test_generated_vendor_bfm_real_signal_bindings_and_scratch(self):
        source=render(fake_port_metadata())
        self.assertIn(MODULE+" dut (",source)
        self.assertEqual(source.count(".S03_AXI_wdata(S03_AXI_wdata)"),1)
        self.assertEqual(source.count(".M00_AXI_wdata(M00_AXI_wdata)"),1)
        self.assertIn("m06_axi128_scratch_mem ram (",source)
        self.assertIn(".s_axi_awaddr(M00_AXI_awaddr)",source)
        self.assertIn(".s_axi_rdata(M00_AXI_rdata)",source)
        self.assertIn(".s_axi_wstrb(M00_AXI_wstrb)",source)
        self.assertIn("write_one('h0fe0,0,32'hffffffff)",source)
        self.assertIn("write_one('h1000,1,32'h80010001)",source)
        self.assertIn("read0('h0fe0)",source)
        self.assertIn("read1('h0fe0)",source)
        self.assertIn("read2('h0fe0)",source)
        self.assertIn("verified_reads !== 14",source)
        self.assertIn("m00_wbeats < 8 || m00_rbeats < 28",source)
        self.assertIn("M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS",source)
        self.assertIn("WATCHDOG_TIMEOUT",source)
        self.assertNotIn("module "+MODULE+"(",source)
        self.assertNotIn("M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS writes=4 reads=14",source)

    def test_original_wrong_evidence_is_rejected_before_generation(self):
        with tempfile.TemporaryDirectory() as d:
            original=Path(d)/ROOT_NAME
            original.mkdir()
            with self.assertRaisesRegex(ValueError,"wrong.*original"):
                original_ports(Path(d),{})
            with self.assertRaisesRegex(ValueError,"wrong original port report"):
                original_ports(original,{})
            report={"status":"MODULE_HEADERS_FOUND_NOT_COMPILED",
                    "vendor_functional_axi":"NOT_EXECUTED",
                    "original_report_sha256":REPORT_SHA,
                    "wrapper_candidates":[]}
            with self.assertRaisesRegex(ValueError,"wrapper identity"):
                original_ports(original,report)
            report["wrapper_candidates"]=[{
                "module":MODULE, "source_relative_to_original":SIM_PATH,
                "source_sha256":SIM_SHA, "ansi_axi_ports":fake_port_metadata(),
                "other_ports":[{"name":"aclk","direction":"input","packed_width":1},
                               {"name":"aresetn","direction":"input","packed_width":1}],
            }]
            with self.assertRaises((OSError,ValueError)):
                original_ports(original,report)
            broken=report["wrapper_candidates"][0]["ansi_axi_ports"]
            broken[0]["packed_width"]=257
            with self.assertRaisesRegex(ValueError,"96-signal AXI"):
                original_ports(original,report)

    def test_original_expected_digests_are_known_and_never_embedded_vendor_ip(self):
        self.assertEqual(len(SIM_SHA),64)
        self.assertEqual(len(BD_SHA),64)
        self.assertEqual(len(REPORT_SHA),64)
        self.assertTrue(SIM_PATH.endswith("/sim/"+MODULE+".sv"))
        self.assertTrue(BD_PATH.endswith("/bd_0/sim/bd_13bd.v"))
        self.assertNotEqual(SIM_SHA,BD_SHA)


if __name__=="__main__":
    unittest.main()
