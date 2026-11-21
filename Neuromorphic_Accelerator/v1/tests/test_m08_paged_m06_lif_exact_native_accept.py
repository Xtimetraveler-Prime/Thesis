"""First owner QFKpXlPW native exact-image release tests, NO BOARD/JTAG.

Golden vendor diagnostic sample is reconstructed from the ORIGINAL first
new-image DRC warning instances. Tests use NO actual owner private reports;
the real native checker additionally requires exact original file hashes.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_exact_native_accept as gate

def vendor_sample()->str:
    lines=[
        "Vivado v.2025.2 (lin64)",
        "Command      : report_drc -file /home/dna/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW/reports/20_route_drc.rpt",
        "Design       : m08_paged_m06_lif_jtag_wrapper",
        "Device       : xck26-sfvc784-2LV-c",
        "Design State : Fully Routed",
        "Checks found: 7",
        "| PDCN-1569 | Warning  | LUT equation term check | 3 |",
        "| REQP-1857 | Warning  | RAMB18E2_writefirst_collision_advisory | 1 |",
        "| REQP-1858 | Warning  | RAMB36E2_writefirst_collision_advisory | 2 |",
        "| RTSTAT-10 | Warning  | No routable loads | 1 |",
    ]
    debug=gate.VENDOR_DBG+"SWITCH_N_EXT_BSCAN."
    for number,(pin,cell,leaf,equation) in gate.LUT_PINS.items():
        lines += [
            f"PDCN-1569#{number} Warning",
            "LUT equation term check",
            f"Used physical LUT pin {pin} of cell {debug}bscan_switch/{cell} "
            f"(pin {debug}bscan_switch/{cell}/{leaf}) is not included in the LUT equation: {equation}",
            "Related violations: <none>",
        ] if number in (1,2) else [
            f"PDCN-1569#{number} Warning",
            "LUT equation term check",
            f"Used physical LUT pin {pin} of cell {debug}{cell} "
            f"(pin {debug}{cell}/{leaf}) is not included in the LUT equation: {equation}",
            "Related violations: <none>",
        ]
    for (code,number),(fifo,prim) in gate.RAM_NAMES.items():
        lines += [
            f"{code}#{number} Warning",gate.DRC_PROFILE[code][1],
            f"Synchronous clocking is detected for BRAM ({gate.VENDOR_AXI}{fifo}/"
            f"any/IP/primitive/{prim}) in SDP mode with WRITE_FIRST write-mode. "
            "Both WRITE_FIRST and NO_CHANGE may exhibit address collisions.",
            "Related violations: <none>",
        ]
    lines.extend([
        "RTSTAT-10#1 Warning","No routable loads",
        "39 net(s) have no routable loads. The problem bus(es) and/or net(s) are "+
        ",\n".join(gate.VENDOR_DBG+"CORE_XSDB.UUT_MASTER/U_CMD"+str(j)
                   for j in range(15))+
        "\n (the first 15 of 37 listed).",
        "Related violations: <none>",
    ])
    return "\n".join(lines)+"\n"

class M084ExactNativeGate(unittest.TestCase):
    def test_pin_exact_reviewed_owner_image_and_four_reports(self):
        self.assertEqual(gate.OWNER,"m08_paged_m06_lif_QFKpXlPW")
        self.assertEqual(len(gate.ORIGINAL),5)
        self.assertEqual(gate.ORIGINAL[gate.BIT][0],
                         "6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494")
        self.assertEqual(gate.ORIGINAL[gate.BIT][1],7797842)
        self.assertEqual({v[0] for v in gate.ORIGINAL.values()}.__len__(),5)
        self.assertEqual(sum(n for n,_ in gate.DRC_PROFILE.values()),7)
        self.assertEqual(len(gate.RAM_NAMES),3)
        self.assertEqual(len(gate.LUT_PINS),3)

    def test_exact_seven_vendor_only_sample_drc_parses(self):
        result=gate.inspect_drc(vendor_sample())
        self.assertEqual(result["original_drc_warning_instances"],7)
        self.assertEqual(result["original_drc_critical_warnings"],0)

    def test_adversarial_new_vendor_or_neural_warning_instances_rejected(self):
        text=vendor_sample()
        mutations=[
            text.replace("Checks found: 7","Checks found: 8"),
            text.replace("PDCN-1569#1 Warning","PDCN-1569#1 Critical Warning"),
            text.replace("REQP-1858#2 Warning","REQP-1858#1 Warning"),
            text.replace("BSCANID.u_xsdbm_id","neural_engine",1),
            text.replace("rd_cmd_fifo_i","lif/neural_engine",1),
            text.replace("39 net(s)","40 net(s)"),
            text.replace("of cell ","of cell lif/",1),
            text.replace("RAMB18E2_writefirst_collision_advisory",
                         "RAMB18E2_unknown_collision",1),
        ]
        for index,mutated in enumerate(mutations):
            with self.subTest(mutant=index):
                with self.assertRaises(gate.Reject):
                    gate.inspect_drc(mutated)

    def test_no_owner_native_no_release_no_physical_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(gate.Reject):
                gate.inspect(Path(tmp))
        code=(ROOT/"scripts/m08_paged_m06_lif_exact_native_accept.py").read_text()
        for banned in ("program_hw_devices(","open_hw_manager(","run_hw_axi(","write_bitstream(",
                       "connect_hw_server(","/dev/mem","dma_alloc_coherent"):
            self.assertNotIn(banned,code)
        self.assertIn("methodology_warning_cells_untraced",code)
        self.assertIn("owner_explicitly_accepts_remaining_first_physical_risk",code)
        self.assertIn("native.inspect(run)",code)
        self.assertIn("vendor.inspect_timing(timing_data)",code)
        runner=(ROOT/"scripts/run_m08_paged_m06_lif_physical_once.sh").read_text()
        self.assertLess(runner.index('python3 "$EXACT_GATE"'),
                        runner.index('HW="$(mktemp -d'))

if __name__=="__main__":
    unittest.main()
