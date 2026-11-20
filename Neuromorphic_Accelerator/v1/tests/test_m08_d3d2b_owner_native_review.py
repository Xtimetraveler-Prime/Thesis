"""Owner-original D3.D.2B seven-warning native gate regression (NO BOARD).

Synthetic full DRC positive fixture models exactly the reviewed source lines;
real native approval also requires the ORIGINAL owner file ledger and bit SHA.
All tests are Python-only: no Vivado, JTAG, Linux runtime or FPGA access.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2b_synaptic_gate as gate


class OriginalD3D2BReviewTests(unittest.TestCase):
    @staticmethod
    def reviewed_report():
        s=(
            "| Tool Version : Vivado v.2025.2 (lin64) Build 6299465 Fri Nov 14 12:34:56 MST 2025\n"
            "| Date         : Fri Nov 20 00:49:59 2026\n"
            "| Host         : PC running 64-bit Ubuntu 24.04.5 LTS\n"
            "| Command      : report_drc -file "+gate.REVIEWED_OWNER_DRC_PATH+"\n"
            "| Design       : m08_d3d2b_synaptic_lif_jtag_wrapper\n"
            "| Device       : xck26-sfvc784-2LV-c\n"
            "| Design State : Fully Routed\n"
            "Checks found: 7\n"
        )
        for rule,(quantity,description) in gate.d3c.VENDOR_DRC_PROFILE.items():
            s+=f"| {rule} | Warning  | {description} | {quantity} |\n"
        pin_details=(
            ("A1","bscan_switch/temp_curid[31]_i_1","I0"),
            ("A3","bscan_switch/temp_curid[31]_i_1","I1"),
            ("A4","id_state[0]_i_1","I0"),
        )
        for idx,(pin,suffix,endpoint) in enumerate(pin_details,1):
            full=gate.REVIEWED_DEBUG_PREFIX+suffix
            s+=(f"PDCN-1569#{idx} Warning\nLUT equation term check\n"
                f"Used physical LUT pin '{pin}' of cell {full} "
                f"(pin {full}/{endpoint}) is not included in the LUT equation.\n"
                "Related violations: <none>\n")
        fifo_details=(
            ("REQP-1857",1,"rx_fifo_i","RAMB18E2_writefirst_collision_advisory"),
            ("REQP-1858",1,"rd_cmd_fifo_i","RAMB36E2_writefirst_collision_advisory"),
            ("REQP-1858",2,"wr_cmd_fifo_i","RAMB36E2_writefirst_collision_advisory"),
        )
        for rule,idx,fifo,desc in fifo_details:
            s+=(f"{rule}#{idx} Warning\n{desc}\n"
                f"Synchronous clocking is detected for BRAM "
                f"({gate.REVIEWED_NEW_JTAG_INSTANCE}/jtag_axi/inst/"
                f"jtag_axi_engine_u/{fifo}/inst_fifo_gen/foo) in SDP "
                "mode with WRITE_FIRST write-mode. Possible address collisions.\n"
                "Related violations: <none>\n")
        s+=(
            "RTSTAT-10#1 Warning\nNo routable loads\n"
            "39 net(s) have no routable loads. The problem bus(es) and/or "
            "net(s) are "+",\n".join(gate.REVIEWED_RTSTAT_FIRST15)+
            "\n (the first 15 of 37 listed).\nRelated violations: <none>\n"
        )
        return s

    def test_exact_owner_source_builder_and_image_pins(self):
        hashes=gate.source()
        self.assertEqual(hashes["rtl_sha256"],gate.OWNER_ORIGINAL_RTL_SHA)
        self.assertEqual(hashes["builder_sha256"],gate.OWNER_ORIGINAL_BUILDER_SHA)
        self.assertEqual(gate.ORIGINAL_OWNER_NATIVE_DIR,
                         "m08_d3d2b_synaptic_DakjdpCO")
        self.assertEqual(gate.ORIGINAL_OWNER_BIT_BYTES,7797847)
        self.assertEqual(gate.ORIGINAL_OWNER_BIT_SHA,
                         "dae1c4953826317854acd3c61d013b6fddec410a0450002fa13b3ab1f1650d14")

    def test_exact_vendor_debug_warning_profile_accepted(self):
        data=gate.inspect_new_drc(self.reviewed_report())
        self.assertEqual(data["drc_checks"],7)
        self.assertEqual(data["vendor_drc_warnings"],7)
        self.assertEqual(data["rtstat_total_unroutable"],39)
        self.assertEqual(data["rtstat_listed_count"],37)
        self.assertEqual(data["rtstat_sampled_paths"],15)
        self.assertIn("EXACT_OWNER_D3D2B_VENDOR_DEBUG",data["drc_review_status"])
        # Owner-original A4 pin is directly under SWITCH_N_EXT_BSCAN,
        # and the genuine reporter prints "is not included" with a space.
        self.assertIn(
            "SWITCH_N_EXT_BSCAN.id_state[0]_i_1/I0) "
            "is not included in the LUT equation",
            self.reviewed_report())
        self.assertNotIn("is notincluded in the LUT equation",
                         self.reviewed_report())
        self.assertNotIn(
            "SWITCH_N_EXT_BSCAN.bscan_switch/id_state[0]_i_1",
            self.reviewed_report())

    def test_drc_mutations_fail_closed(self):
        original=self.reviewed_report()
        mutations=(
            ("wrong total count", "Checks found: 7", "Checks found: 8"),
            ("elevated summary severity", "| REQP-1857 | Warning",
             "| REQP-1857 | Critical Warning"),
            ("new rule", "REQP-1858#2 Warning", "REQP-1859#2 Warning"),
            ("wrong vendor fifo", "wr_cmd_fifo_i", "user_synapse_fifo"),
            ("unreviewed source", gate.REVIEWED_RTSTAT_FIRST15[11],
             "fabric/new_synapse_unrouted"),
            ("unseen RTSTAT nets", "39 net(s)", "40 net(s)"),
            ("changed listed count", "first 15 of 37", "first 15 of 39"),
            ("wrong BSCAN physical pin", "pin 'A1'", "pin 'A2'"),
            ("wrong BSCAN LUT endpoint", "temp_curid[31]_i_1/I1",
             "temp_curid[31]_i_1/I2"),
            ("spurious A4 BSCAN subtree",
             "SWITCH_N_EXT_BSCAN.id_state[0]_i_1",
             "SWITCH_N_EXT_BSCAN.bscan_switch/id_state[0]_i_1"),
            ("rewritten A4 warning text", "is not included in the LUT equation",
             "is notincluded in the LUT equation"),
            ("wrong XSDB LUT cell", "SWITCH_N_EXT_BSCAN.bscan_switch/",
             "user_lif_engine/"),
            ("different native run", gate.ORIGINAL_OWNER_NATIVE_DIR,
             "m08_d3d2b_synaptic_OTHER"),
            ("different Vivado version", "Vivado v.2025.2", "Vivado v.2026.1"),
            ("wrong design", "m08_d3d2b_synaptic_lif_jtag_wrapper",
             "unreviewed_wrapper"),
            ("related rule", "Related violations: <none>",
             "Related violations: new"),
        )
        for label,find,replacement in mutations:
            with self.subTest(case=label):
                self.assertIn(find,original)
                modified=original.replace(find,replacement,1)
                self.assertNotEqual(modified,original)
                with self.assertRaises(gate.Reject):
                    gate.inspect_new_drc(modified)

    def test_zero_warning_drc_unit_path_not_original_candidate(self):
        self.assertEqual(gate.inspect_new_drc("Checks found: 0\n")["drc_checks"],0)


if __name__=="__main__":
    unittest.main()
