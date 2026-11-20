"""D3.D.2D exact first owner XSDB/JTAG DRC review regression (synthetic only).

These fabricated warning strings test the parser, NOT a genuine native image.
Full native acceptance ALSO pins entire owner-original DRC SHA, exact image
SHA+size, 12 original evidence rows, original RTL/build and routed timing.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2d_event_native_review as gate
import m08_d3c_jtag_bram_gate as parent


def synthetic_owner_drc():
    text=(
        "Copyright Advanced Micro Devices.\n"
        "| Tool Version : Vivado v.2025.2 (lin64)\n"
        "| Date         : Fri Nov 20 15:32:35 2026\n"
        "| Command      : report_drc -file "+gate.REVIEWED_DRC_PATH+"\n"
        "| Design       : m08_d3d2d_event_lif_jtag_wrapper\n"
        "| Device       : xck26-sfvc784-2LV-c\n"
        "| Design State : Fully Routed\n"
        "Checks found: 7\n"
    )
    for code,(count,desc) in parent.VENDOR_DRC_PROFILE.items():
        text+=f"| {code} | Warning | {desc} | {count} |\n"
    for ordinal,(pin,suffix,endpoint,equation) in gate.REVIEWED_LUT_PINS.items():
        cell=gate.REVIEWED_DEBUG_PREFIX+suffix
        text+=(
            f"PDCN-1569#{ordinal} Warning\nLUT equation term check\n"
            f"Used physical LUT pin {pin} of cell {cell} "
            f"(pin {cell}/{endpoint}) is not included in the LUT equation: "
            f"{equation}.\nRelated violations: <none>\n"
        )
    for code,ordinal,fifo,primitive in (
        ("REQP-1857",1,"rx_fifo_i","WIDE_PRIM18.ram"),
        ("REQP-1858",1,"rd_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram"),
        ("REQP-1858",2,"wr_cmd_fifo_i","WIDE_PRIM36_NO_ECC.ram")
    ):
        text+=(
            f"{code}#{ordinal} Warning\n"
            + parent.VENDOR_DRC_PROFILE[code][1] + "\n"
            "Synchronous clocking is detected for BRAM ("
            + gate.REVIEWED_JTAG_INSTANCE
            + "/jtag_axi/inst/jtag_axi_engine_u/"
            + fifo + "/inst_fifo_gen/"
            + f"DEVICE_8SERIES.NO_BMM_INFO.SDP.{primitive}) "
            "in SDP mode with WRITE_FIRST write-mode. "
            "There may be address collisions.\n"
            "Related violations: <none>\n"
        )
    text+=(
        "RTSTAT-10#1 Warning\nNo routable loads\n"
        "39 net(s) have no routable loads. "
        "The problem bus(es) and/or net(s) are "
        +",\n".join(gate.REVIEWED_RTSTAT_FIRST15)
        +"\n (the first 15 of 37 listed).\nRelated violations: <none>\n"
    )
    return text


class D3D2DOwnerNativeReviewTests(unittest.TestCase):
    def test_first_image_exact_sha_and_physical_constraints(self):
        self.assertEqual(gate.ORIGINAL_OWNER_NATIVE_DIR,"m08_d3d2d_event_DE6kQWvt")
        self.assertEqual(gate.OWNER_ORIGINAL_BIT_BYTES,7797844)
        self.assertEqual(
            gate.OWNER_ORIGINAL_BIT_SHA,
            "f50a156342eaf1173a3869b5316e4edc1d59662d9f0d687bcec600f7b0efdeab")
        self.assertEqual(
            gate.OWNER_ORIGINAL_DRC_SHA,
            "f1cc7a7b72b7eeee85828a6c5f7cb75d56894a55a2143cfe4e0f1f6c8098ebee")
        self.assertEqual(gate.REVIEWED_LUT_PINS[1][0],"'A2'")
        self.assertEqual(gate.REVIEWED_LUT_PINS[1][2],"I1")
        self.assertEqual(gate.REVIEWED_LUT_PINS[2][0],"'A3'")
        self.assertEqual(gate.REVIEWED_LUT_PINS[2][2],"I0")
        self.assertEqual(gate.REVIEWED_LUT_PINS[3][0],"'A5'")
        self.assertEqual(gate.REVIEWED_LUT_PINS[3][3],"'O6=(A6+~A6)*((A4))'")

    def test_synthetic_seven_warning_parser(self):
        data=gate.inspect_reviewed_drc(synthetic_owner_drc())
        self.assertEqual(data["vendor_drc_warnings"],7)
        self.assertEqual(data["original_drc_checks"],7)
        self.assertEqual(data["rtstat_total_unroutable"],39)
        self.assertEqual(data["rtstat_listed_count"],37)
        self.assertEqual(data["rtstat_sampled_paths"],15)

    def test_drc_mutations_all_rejected(self):
        src=synthetic_owner_drc()
        for name,bad,bad_repl in (
            ("pin-1", "physical LUT pin 'A2'","physical LUT pin 'A3'"),
            ("pin-2", "physical LUT pin 'A3'","physical LUT pin 'A1'"),
            ("pin-3", "physical LUT pin 'A5'","physical LUT pin 'A4'"),
            ("I1", "temp_curid[31]_i_1/I1", "temp_curid[31]_i_1/I0"),
            ("I0", "temp_curid[31]_i_1/I0", "temp_curid[31]_i_1/I1"),
            ("equation", "O6=(A6+~A6)*((A4))", "O6=(A6+~A6)*((A1))"),
            ("eq-two", "O5=(A5*A1)", "O5=(A5*A2)"),
            ("spacing", "is not included", "is notincluded"),
            ("FIFO", "rx_fifo_i/inst_fifo_gen", "wrong_fifo_i/inst_fifo_gen"),
            ("BRAM", "WIDE_PRIM36_NO_ECC.ram", "WIDE_PRIM18.ram"),
            ("RTSTAT", "39 net(s)", "38 net(s)"),
            ("RTSTAT paths", "ctl_reg_en_2[1]", "ctl_reg_en_2[9]"),
            ("unreviewed", "Checks found: 7", "Checks found: 8"),
            ("critical", "PDCN-1569#1 Warning", "PDCN-1569#1 Critical Warning"),
            ("wrong design", "m08_d3d2d_event_lif_jtag_wrapper",
             "m08_d3d2c_m06_lif_jtag_wrapper"),
            ("wrong date", "15:32:35", "15:32:36"),
        ):
            with self.subTest(name=name):
                self.assertIn(bad,src)
                altered=src.replace(bad,bad_repl,1)
                with self.assertRaisesRegex(gate.Reject,"M08_D3D2D_NEW_DRC_REVIEW_REQUIRED"):
                    gate.inspect_reviewed_drc(altered)

    def test_native_gate_never_executes_jtag(self):
        text=(ROOT/"scripts/m08_d3d2d_event_native_review.py").read_text()
        self.assertIn("M08_D3D2D_EXACT_OWNER_NATIVE_RAW17_IMAGE_ACCEPTED_NO_BOARD",text)
        self.assertIn('raw_event_ingress_physically_verified=False',text)
        self.assertIn("OWNER_ORIGINAL_BIT_SHA",text)
        for token in ("open_hw_manager", "program_hw_devices",
                      "run_hw_axi", "/dev/mem", "/dev/uio"):
            self.assertNotIn(token,text)


if __name__=="__main__":
    unittest.main()
