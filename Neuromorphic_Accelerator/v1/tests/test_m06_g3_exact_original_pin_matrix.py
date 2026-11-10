"""SYNTHETIC_ONLY unit tests of exact generated-HLS/original-vendor pin matrix.

Does not instantiate original AMD RTL, HLS Verilog or Vivado IP.
"""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_exact_original_pin_matrix import NEEDED,matrix
from m06_generate_original_mem_sc_bfm import required_ports


def fake():
    # The real owner tool parses every pin from genuine 2025.2 Verilog.
    p=dict(NEEDED)
    p["m_axi_gmem_read_ARID"]=("output",1)
    p["m_axi_gmem_read_RRESP"]=("input",2)
    p["m_axi_gmem_write_AWID"]=("output",1)
    p["m_axi_gmem_write_WLAST"]=("output",1)
    return p,required_ports()


class M06ExactVendorHLSMatrixSyntheticTests(unittest.TestCase):
    def test_positive_measurement_requires_data_and_address_adapter(self):
        hls,vendor=fake()
        result=matrix(hls,vendor)
        self.assertFalse(result["original_smartconnect_linked"])
        self.assertFalse(result["genuine_connected_RTL_XSim"])
        self.assertFalse(result["m06_complete"])
        self.assertEqual([x["original_si"] for x in result["paths"]],["S00","S03"])
        for p in result["paths"]:
            self.assertEqual(p["data_width_conversion"],
                             "MANDATORY_32_TO_256_VERIFIED_AMD_IP")
            self.assertEqual(p["address_conversion"],
                             "MANDATORY_GUARDED_64_TO_32_BOUNDED_64KiB_OFFSET")
            self.assertFalse(p["original_si_id_wires_present"])

    def test_positive_explicitly_inventory_hls_only_id_signal(self):
        hls,vendor=fake()
        result=matrix(hls,vendor)
        read=result["paths"][0]
        arid=next(p for p in read["sideband_pin_matrix"] if p["signal"]=="ARID")
        self.assertEqual(arid["hls_direction_width"],["output",1])
        self.assertIsNone(arid["original_direction_width"])
        self.assertTrue(arid["requires_adapter_or_explicit_termination"])

    def test_negative_vendor_changed_port_width_rejected(self):
        hls,vendor=fake()
        vendor["S00_AXI_rdata"]=("output",128)
        with self.assertRaisesRegex(ValueError,"original 96-pin"):
            matrix(hls,vendor)
        hls,vendor=fake()
        vendor["S03_AXI_awaddr"]=("input",64)
        with self.assertRaisesRegex(ValueError,"original 96-pin"):
            matrix(hls,vendor)

    def test_negative_hls_incompatible_width_missing_pin_or_wrong_direction(self):
        for name,bad in (
            ("m_axi_gmem_read_RDATA",("input",64)),
            ("m_axi_gmem_read_ARADDR",("output",32)),
            ("m_axi_gmem_write_WSTRB",("output",32)),
            ("m_axi_gmem_write_AWADDR",("input",64)),
            ("m_axi_gmem_write_BRESP",("output",2)),
        ):
            with self.subTest(pin=name):
                hls,vendor=fake()
                hls[name]=bad
                with self.assertRaisesRegex(ValueError,"measured HLS"):
                    matrix(hls,vendor)
        hls,vendor=fake()
        hls.pop("m_axi_gmem_write_WVALID")
        with self.assertRaisesRegex(ValueError,"measured HLS"):
            matrix(hls,vendor)

    def test_negative_same_direction_handshake_refused(self):
        # A pin may be added beyond the mandatory subset, but where a
        # corresponding original pin exists, it must be master->slave.
        hls,vendor=fake()
        hls["m_axi_gmem_read_ARLEN"]=("input",8)
        with self.assertRaisesRegex(ValueError,"same-direction"):
            matrix(hls,vendor)


if __name__=="__main__":
    unittest.main()
