"""The exact D3.D.2C 2026-11-20 12:31 original image warning profile.

PC-only synthetic mutation tests: synthetic warning text is NOT a native
bitstream, Vivado build, real hardware receipt or genuine owner 12-file ledger.
Full native inspect independently requires the original SHA256 for each byte.
"""
from __future__ import annotations
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_native_review as gate
import m08_d3c_jtag_bram_gate as parent

def synthetic_original_review():
    header=(
        "Copyright Advanced Micro Devices.\n"
        "| Tool Version : Vivado v.2025.2 (lin64)\n"
        "| Date         : Fri Nov 20 12:31:10 2026\n"
        "| Command      : report_drc -file "+gate.REVIEWED_DRC_PATH+"\n"
        "| Design       : m08_d3d2c_m06_lif_jtag_wrapper\n"
        "| Device       : xck26-sfvc784-2LV-c\n"
        "| Design State : Fully Routed\n"
        "Checks found: 7\n"
    )
    for code,(count,desc) in parent.VENDOR_DRC_PROFILE.items():
        header+=f"| {code} | Warning | {desc} | {count} |\n"
    for ordinal,(pin,suffix,endpoint,equation) in gate.REVIEWED_LUT_PINS.items():
        cell=gate.REVIEWED_DEBUG_PREFIX+suffix
        header+=(
            f"PDCN-1569#{ordinal} Warning\n"
            "LUT equation term check\n"
            f"Used physical LUT pin {pin} of cell {cell} "
            f"(pin {cell}/{endpoint}) is not included in the LUT equation: "
            f"{equation}.\nRelated violations: <none>\n"
        )
    for code,ordinal,fifo,primitive in (
        ("REQP-1857",1,"rx_fifo_i","WIDE_PRIM18.ram"),
        ("REQP-1858",1,"rd_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
        ("REQP-1858",2,"wr_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram")
    ):
        desc=parent.VENDOR_DRC_PROFILE[code][1]
        header+=(
            f"{code}#{ordinal} Warning\n{desc}\n"
            "Synchronous clocking is detected for BRAM ("
            f"{gate.REVIEWED_JTAG_INSTANCE}/jtag_axi/inst/"
            f"jtag_axi_engine_u/{fifo}/inst_fifo_gen/"
            f"DEVICE_8SERIES.NO_BMM_INFO.SDP.{primitive}) "
            "in SDP mode with WRITE_FIRST write-mode. "
            "There may be address collisions.\n"
            "Related violations: <none>\n"
        )
    header+=(
        "RTSTAT-10#1 Warning\nNo routable loads\n"
        "39 net(s) have no routable loads. "
        "The problem bus(es) and/or net(s) are "
        +",\n".join(gate.REVIEWED_RTSTAT_FIRST15)
        +"\n (the first 15 of 37 listed).\nRelated violations: <none>\n"
    )
    return header


class ReviewedD3D2CNativeWarningTests(unittest.TestCase):
    def test_new_owner_image_source_builder_and_bit_sha_are_exact(self):
        self.assertEqual(gate.ORIGINAL_OWNER_NATIVE_DIR,"m08_d3d2c_m06_MN2pwduB")
        self.assertEqual(gate.OWNER_ORIGINAL_BIT_BYTES,7797842)
        self.assertEqual(gate.OWNER_ORIGINAL_BIT_SHA,
                         "244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932")
        self.assertEqual(gate.OWNER_ORIGINAL_DRC_SHA,
                         "7c273c8160811e7242c15418d174ae31fc6ddfee7d4850b7748d2facbe3e9fe3")
        self.assertEqual(gate.OWNER_ORIGINAL_RTL_SHA,
                         "27b40475d75592d06f45bc5d66205e4a93e1684195c2965031ad32eb4c77ad04")
        self.assertEqual(gate.OWNER_ORIGINAL_BUILDER_SHA,
                         "e4c95944c11881b741d92215be161dd00e3ab1b89d96e34c32a14b4acec8ca6d")
        self.assertEqual(gate.OWNER_ORIGINAL_POR_SHA,
                         "56dffdb178772296c7d751d75654aff8be44885939f752a9200ad1f961373fb2")
        # Latest code has NOT changed the first original RTL/builders.
        from hashlib import sha256
        self.assertEqual(sha256(gate.RTL.read_bytes()).hexdigest(),gate.OWNER_ORIGINAL_RTL_SHA)
        self.assertEqual(sha256(gate.BUILDER.read_bytes()).hexdigest(),gate.OWNER_ORIGINAL_BUILDER_SHA)
        self.assertEqual(sha256(gate.POR.read_bytes()).hexdigest(),gate.OWNER_ORIGINAL_POR_SHA)

    def test_exact_synthetic_original_warning_profile(self):
        result=gate.inspect_reviewed_drc(synthetic_original_review())
        self.assertEqual(result["original_drc_checks"],7)
        self.assertEqual(result["rtstat_total_unroutable"],39)
        self.assertEqual(result["rtstat_listed_count"],37)
        self.assertEqual(result["rtstat_sampled_paths"],15)
        self.assertIn("EXACT_OWNER_D3D2C",result["drc_review_status"])
        self.assertEqual(gate.REVIEWED_LUT_PINS[1][0],"'A1'")
        self.assertEqual(gate.REVIEWED_LUT_PINS[2][0],"'A2'")
        self.assertEqual(gate.REVIEWED_LUT_PINS[3][0],"'A5'")
        self.assertEqual(gate.REVIEWED_LUT_PINS[3][1],"id_state[0]_i_1")

    def test_original_warning_mutations_fail_closed(self):
        baseline=synthetic_original_review()
        for name,old,new in (
            ("wrong A2 physical LUT", "physical LUT pin 'A2'", "physical LUT pin 'A3'"),
            ("wrong A5 physical LUT", "physical LUT pin 'A5'", "physical LUT pin 'A4'"),
            ("wrong I1 endpoint", "temp_curid[31]_i_1/I1", "temp_curid[31]_i_1/I2"),
            ("wrong third hierarchy", "SWITCH_N_EXT_BSCAN.id_state[0]_i_1",
             "SWITCH_N_EXT_BSCAN.bscan_switch/id_state[0]_i_1"),
            ("wrong LUT INIT equation", "O6=(A6+~A6)*((A1))",
             "O6=(A6+~A6)*((A2))"),
            ("wrong second LUT equation", "O5=(A3*A4)", "O5=(A1*A4)"),
            ("wrong pin wording", "is not included", "is notincluded"),
            ("new JTAG FIFO", "rd_cmd_fifo_i/inst_fifo_gen",
             "unexpected_fifo_i/inst_fifo_gen"),
            ("new REQP BRAM", "WIDE_PRIM36_NO_ECC.ram", "WIDE_PRIM18.ram"),
            ("wrong RTSTAT count", "39 net(s)", "40 net(s)"),
            ("wrong RTSTAT list size", "first 15 of 37 listed",
             "first 15 of 38 listed"),
            ("wrong RTSTAT path", "ctl_reg_en_2[1]", "ctl_reg_en_2[9]"),
            ("critical", "PDCN-1569#1 Warning", "PDCN-1569#1 Critical Warning"),
            ("extra unknown count", "Checks found: 7", "Checks found: 8"),
            ("zero count", "Checks found: 7", "Checks found: 0"),
            ("wrong date", "Fri Nov 20 12:31:10 2026", "Fri Nov 20 11:36:42 2026"),
            ("wrong owner folder", gate.ORIGINAL_OWNER_NATIVE_DIR,
             "m08_d3d2c_m06_fakeimage"),
        ):
            with self.subTest(name=name):
                self.assertIn(old,baseline)
                bad=baseline.replace(old,new,1)
                with self.assertRaisesRegex(gate.Reject,
                                            "M08_D3D2C_NEW_DRC_REVIEW_REQUIRED"):
                    gate.inspect_reviewed_drc(bad)

    def test_native_acceptance_remains_no_board(self):
        src=(ROOT/"scripts/m08_d3d2c_m06_native_review.py").read_text()
        self.assertIn("original_12_sha_entries_verified",src)
        self.assertIn("OWNER_ORIGINAL_BIT_SHA",src)
        self.assertIn("OWNER_ORIGINAL_DRC_SHA",src)
        self.assertIn('physical_programming_authorized":False',src)
        self.assertIn('physical_32_neuron_m02_parity_verified":False',src)
        self.assertIn('status":"M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD"',src)
        for op in ("program_hw_devices","open_hw_manager","run_hw_axi","/dev/mem","/dev/uio"):
            self.assertNotIn(op,src)


if __name__=="__main__":
    unittest.main()
