"""Exact M32Q first-original DRC/timing owner-image gate: NO physical calls.

Synthetic warning snippets test pin/BRAM/RTSTAT classification ONLY.
No mocked original bitstream, DRC, timing report or SHA receipt can be
accepted as a real image: the overall gate pins immutable owner SHA values.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2e_queue_exact_native_accept as exact

class D3D2EOwnerImageExactBoundary(unittest.TestCase):
    def fake_reviewed_drc(self):
        lines=[
            "Vivado v.2025.2 (lin64)",
            "Date         : Fri Nov 20 16:34:33 2026",
            "Command      : report_drc -file "+exact.DRC_PATH,
            "Design       : "+exact.WRAPPER,
            "Device       : xck26-sfvc784-2LV-c",
            "Design State : Fully Routed",
            "Checks found: 7",
        ]
        for code,(num,desc) in exact.PROFILE.items():
            lines.append(f"| {code} | Warning | {desc} | {num} |")
        for code,(num,desc) in exact.PROFILE.items():
            for i in range(1,num+1):
                lines.extend([f"{code}#{i} Warning",desc])
                if code=="PDCN-1569":
                    pin,suffix,endpoint,equation=exact.LUTS[i]
                    cell=exact.DEBUG_SWITCH+suffix
                    lines.append(
                        f"Used physical LUT pin {pin} of cell {cell} "
                        f"(pin {cell}/{endpoint}) is not included in the LUT equation: {equation}"
                    )
                elif code.startswith("REQP-"):
                    fifo,primitive=exact.RAM_FIFOS[(code,i)]
                    lines.append(
                        "Synchronous clocking is detected for BRAM ("
                        +exact.JTAG_ROOT+fifo+"/testpath/"+primitive+") "
                        "in SDP mode with WRITE_FIRST write-mode. "
                        "Potential address collisions."
                    )
                else:
                    lines.append(
                        "39 net(s) have no routable loads. "
                        "The problem bus(es) and/or net(s) are "
                        +",\n".join(exact.RTSTAT_SAMPLE)
                        +" (the first 15 of 37 listed)."
                    )
                lines.append("Related violations: <none>")
        return "\n".join(lines)+"\n"

    def test_exact_image_review_constants_are_distinct_first_owner(self):
        self.assertEqual(exact.OWNER_NATIVE_DIR,"m08_d3d2e_queue_GFz0SbiC")
        self.assertEqual(exact.OWNER_BIT_BYTES,7797844)
        for value in (exact.OWNER_BIT_SHA,exact.OWNER_DRC_SHA,
                      exact.OWNER_TIMING_SHA,exact.OWNER_CLOCKS_SHA):
            self.assertRegex(value,r"^[0-9a-f]{64}$")
        self.assertNotEqual(exact.OWNER_BIT_SHA,
                            "f50a156342eaf1173a3869b5316e4edc1d59662d9f0d687bcec600f7b0efdeab")
        self.assertEqual(sum(x[0] for x in exact.PROFILE.values()),7)

    def test_exact_seven_vendor_instances_positive_synthetic_parser_only(self):
        data=exact.inspect_drc(self.fake_reviewed_drc())
        self.assertEqual(data["original_drc_checks"],7)
        self.assertEqual(data["reviewed_vendor_warnings"],7)
        self.assertEqual(data["rtstat_no_routable_loads"],39)
        self.assertEqual(data["rtstat_sampled_vendor_paths"],15)

    def test_mutated_warning_pins_equations_and_nonvendor_ram_fails(self):
        base=self.fake_reviewed_drc()
        substitutions=[
            ("physical LUT pin 'A1'","physical LUT pin 'A5'"),
            ("O5=(A5*A3)","O5=(A5*A2)"),
            ("temp_curid[31]_i_1","unexpected_user_cell"),
            (exact.JTAG_ROOT+"rx_fifo_i", "m32q_user_fifo/rx_fifo_i"),
            ("WIDE_PRIM36_NO_ECC.ram","WIDE_PRIM18.ram"),
            ("39 net(s) have no routable loads","40 net(s) have no routable loads"),
            ("(the first 15 of 37 listed)","(the first 15 of 38 listed)"),
            (exact.RTSTAT_SAMPLE[7],"m32q_custom_fifo/unroutable"),
            ("PDCN-1569#1 Warning","PDCN-1569#1 Error"),
            ("PDCN-1569#1 Warning","PDCN-1569#2 Warning"),
            ("Related violations: <none>","Related violations: NEW"),
            ("Design State : Fully Routed","Design State : Synthesized"),
        ]
        for before,after in substitutions:
            with self.subTest(before=before,after=after):
                self.assertIn(before,base)
                with self.assertRaises(exact.Reject):
                    exact.inspect_drc(base.replace(before,after,1))
        with self.assertRaises(exact.Reject):
            exact.inspect_drc(base+"\nNEW-1234#1 Warning\nnew user design hazard\n")

    def test_full_image_gate_rejects_same_named_synthetic_mock(self):
        with TemporaryDirectory() as td:
            home=Path(td)
            path=home/"Thesis_Evidence"/"M08"/exact.OWNER_NATIVE_DIR
            (path/"bitstream_candidate").mkdir(parents=True)
            (path/exact.first.BIT).write_bytes(b"FAKE-BITSTREAM-NOT-OWNER-IMAGE")
            with patch.object(Path,"home",return_value=home), \
                 patch.object(exact.first,"inspect",return_value={
                     "sha_ledger_rows_verified":12,
                     "new_original_candidate_sha256":"0"*64,
                 }), \
                 patch.object(exact.source_gate,"source",return_value={}):
                with self.assertRaisesRegex(exact.Reject,"not the first owner original"):
                    exact.inspect(path)
        with self.assertRaises(exact.Reject):
            exact.inspect(Path(td)/"M08"/"m08_d3d2d_event_DE6kQWvt")

    def test_rehashed_synthetic_cannot_waive_original_DRC_timing_and_SHA(self):
        code=(ROOT/"scripts/m08_d3d2e_queue_exact_native_accept.py").read_text()
        for key in ("OWNER_BIT_SHA","OWNER_DRC_SHA","OWNER_TIMING_SHA",
                    "OWNER_CLOCKS_SHA","first.inspect(run)","vendor.inspect_timing",
                    "source_gate.source()","RTSTAT_SAMPLE","LUTS","RAM_FIFOS",
                    "original_12_sha_entries_verified=True",
                    "image_specific_gate=\"ACCEPTED\""):
            self.assertIn(key,code,key)
        self.assertNotIn("open_hw_manager",code)
        self.assertNotIn("program_hw_devices",code)
        self.assertNotIn("run_hw_axi",code)
        shell=(ROOT/"scripts/run_m08_d3d2e_queue_physical_once.sh").read_text()
        self.assertIn("m08_d3d2e_queue_exact_native_accept.py",shell)
        self.assertLess(shell.index("m08_d3d2e_queue_exact_native_accept.py"),
                        shell.index('HW="$(mktemp -d'))

if __name__=="__main__":
    unittest.main()
