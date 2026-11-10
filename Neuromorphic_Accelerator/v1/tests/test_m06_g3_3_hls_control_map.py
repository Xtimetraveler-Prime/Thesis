"""Synthetic tests for SHA-attested generated HLS AXI-Lite control offsets."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_3_hls_control_map import control_map,CONTROL


class RealHLSControlMapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"work/hls/syn/verilog"
        self.root.mkdir(parents=True)
        self.path=self.root/CONTROL
        self.source="""
module fixture;
parameter ADDR_AP_CTRL = 7'h00;
parameter ADDR_GIE = 7'h04;
parameter ADDR_IER = 7'h08;
parameter ADDR_ISR = 7'h0c;
parameter ADDR_AP_RETURN = 7'h10;
parameter ADDR_CANONICAL_READ_WORDS_DATA_0 = 7'h18;
parameter ADDR_CANONICAL_READ_WORDS_DATA_1 = 7'h1c;
parameter ADDR_NEURON_COUNT_DATA_0 = 7'h20;
parameter ADDR_SYNAPSE_COUNT_DATA_0 = 7'h24;
parameter ADDR_TICKS_DATA_0 = 7'h28;
parameter ADDR_DECAY_NUM_DATA_0 = 7'h2c;
parameter ADDR_DECAY_DEN_DATA_0 = 7'h30;
endmodule
"""
        self.path.write_text(self.source)
        self.inv={"hls_rtl_file_inventory":[{
            "name":CONTROL,"sha256":hashlib.sha256(self.path.read_bytes()).hexdigest()}]}
    def test_positive_real_control_map_bytes(self):
        got=control_map(self.inv,self.root)
        self.assertEqual(got["ap_ctrl"],0)
        self.assertEqual(got["ap_return"],16)
        self.assertEqual(len(got["register_offsets"]),12)
        self.assertFalse(got["generated_hls_xsim_functional"])
    def test_grouped_real_vitis_localparam_list_and_comments(self):
        # AMD/Vitis generated AXI-Lite control modules commonly declare all
        # ADDR_* constants in ONE localparam group, comma separated.
        self.path.write_text("""
module fixture;
localparam
    ADDR_AP_CTRL = 7'h00,
    ADDR_GIE = 7'h04,
    ADDR_IER = 7'h08,
    ADDR_ISR = 7'h0c,
    ADDR_AP_RETURN = 7'h10,
    ADDR_CANONICAL_READ_WORDS_DATA_0 = 7'h18,
    ADDR_CANONICAL_READ_WORDS_DATA_1 = 7'h1c,
    ADDR_NEURON_COUNT_DATA_0 = 7'h20,
    ADDR_SYNAPSE_COUNT_DATA_0 = 7'h24,
    ADDR_TICKS_DATA_0 = 7'h28,
    ADDR_DECAY_NUM_DATA_0 = 7'h2c,
    ADDR_DECAY_DEN_DATA_0 = 7'h30,
    WRIDLE = 2'd0;
// parameter ADDR_AP_RETURN = 7'h7c;  // comment must be ignored
/* localparam ADDR_AP_CTRL = 7'h20; */
endmodule
""")
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        got=control_map(self.inv,self.root)
        self.assertEqual(got["ap_ctrl"],0)
        self.assertEqual(got["ap_return"],16)
        self.assertEqual(len(got["register_offsets"]),12)
        self.assertEqual(got["register_offsets"]["DECAY_DEN_DATA_0"],48)

    def test_grouped_negative_duplicate_missing_and_bad_literal(self):
        source=self.source.replace("parameter ADDR_GIE = 7'h04;","parameter ADDR_GIE = 7'h04,\n ADDR_GIE = 7'h04;")
        self.path.write_text(source)
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"duplicated"):
            control_map(self.inv,self.root)
        source=self.source.replace("parameter ADDR_GIE = 7'h04;","parameter ADDR_GIE = 7'd04;")
        self.path.write_text(source)
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"unrecognized HLS address"):
            control_map(self.inv,self.root)
        source=self.source.replace("parameter ADDR_GIE = 7'h04;","parameter ADDR_GIE = 7'h84;")
        self.path.write_text(source)
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"constant width"):
            control_map(self.inv,self.root)
        source=self.source.replace("parameter ADDR_GIE = 7'h04;","parameter ADDR_GIE = ADDR_AP_CTRL+4;")
        self.path.write_text(source)
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"unrecognized HLS address"):
            control_map(self.inv,self.root)

    def test_negative_genuine_control_sha_drift(self):
        self.path.write_text(self.source.replace("7'h10","7'h14"))
        with self.assertRaisesRegex(ValueError,"SHA drift"):
            control_map(self.inv,self.root)
    def test_negative_missing_return_or_bad_ctrl(self):
        self.path.write_text(self.source.replace("ADDR_AP_RETURN","ADDR_UNKNOWN"))
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"return register"):
            control_map(self.inv,self.root)
        self.path.write_text(self.source.replace("ADDR_AP_CTRL = 7'h00","ADDR_AP_CTRL = 7'h04"))
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"ap_ctrl offset"):
            control_map(self.inv,self.root)
    def test_negative_duplicate_or_invalid_register(self):
        self.path.write_text(self.source.replace("ADDR_IER = 7'h08","ADDR_IER = 7'h08;\nparameter ADDR_IER = 7'h08"))
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"duplicated"):
            control_map(self.inv,self.root)
        self.path.write_text(self.source.replace("ADDR_IER = 7'h08","ADDR_IER = 7'h07"))
        self.inv["hls_rtl_file_inventory"][0]["sha256"]=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,"nonaligned"):
            control_map(self.inv,self.root)


if __name__=="__main__":
    unittest.main()
