"""M08 D3.2 read-only route-report semantic review, synthetic negative cases.

These tests DO NOT replay owner Vivado output or establish hardware safety.
The real CLI additionally calls the existing native report source gate.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d3_2_passive_route_report_review.py"
spec = importlib.util.spec_from_file_location("route_report_review_test", SCRIPT)
assert spec and spec.loader
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

TIMING = """| Design State      : Routed
Timing Summary Report
There are 0 register/latch pins with no clock.
There are 0 pins that are not constrained for maximum delay.
There are 0 combinational loops in the design.
| Design Timing Summary
| ---------------------
------------------------------------------------------------------------------------------------
    WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints      WHS(ns)
    -------      -------  ---------------------  -------------------      -------
         NA           NA                     NA                   NA           NA

All user specified timing constraints are met.
"""
DRC = """| Design State : Fully Routed
Report DRC
           Ruledeck: default
             Checks found: 0
"""
UTIL = """| Design State : Routed
Utilization Design Information
| CLB LUTs | 0 | 0 | 0 |
| CLB Registers | 0 | 0 | 0 |
| CLB Registers | 0 | 0 | 0 |
| DSPs | 0 | 0 | 0 |
| Block RAM Tile | 0 | 0 | 0 |
| Bonded IOB | 1 | 1 | 0 |
| PS8 | 1 | 0 | 0 |
| PS8 | 1 | Advanced |
| OBUF | 1 | I/O |
10. Black Boxes
"""
CLOCKS = """| Design State      : Routed
Clock Report
clk_pl_0  10.000      {0.000 5.000}  P  {m08_d3a_passive_fan_i/ps/inst/PS8_i/PLCLK[0]}
clk_pl_1  10.000      {0.000 5.000}  P  {m08_d3a_passive_fan_i/ps/inst/PS8_i/PLCLK[1]}
"""
LOG = """WARNING: [Board 49-26] unrelated kc705 board part not installed
WARNING: [Place 30-2953] Timing driven mode will be turned off because no critical terminals were found.
"""


class PassiveSemanticReview(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.run = Path(tmp.name) / "M08" / "m08_d3_2_passive_synth_SYNTHETIC"
        self.run.mkdir(parents=True)
        names = set().union(*review.RECEIPTS.values())
        for rel in names:
            p = self.run / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("synthetic original: " + rel + "\n")
        for rel, text in (
            (review.REPORTS["timing"], TIMING),
            (review.REPORTS["drc"], DRC),
            (review.REPORTS["utilization"], UTIL),
            (review.REPORTS["clocks"], CLOCKS),
            ("05_passive_route_vivado.log", LOG),
            ("30_pc_source_and_native_review.json",
             json.dumps({"physical_programming_authorized": False})),
            ("50_pc_route_evidence_review.json",
             json.dumps({"hardware_mmio_authorized": False,
                         "native": {"bitstream_generated": False,
                                    "hardware_mmio_authorized": False}})),
        ):
            (self.run / rel).write_text(text)
        self.resign()
        self.stub = types.SimpleNamespace(
            RouteRejected=ValueError,
            audit_native=lambda _: {"status": "SYNTHETIC_PARENT_NOT_VIVADO"},
        )

    def resign(self):
        for receipt, names in review.RECEIPTS.items():
            lines = []
            for rel in sorted(names):
                lines.append(sha256((self.run / rel).read_bytes()).hexdigest()
                             + "  " + rel)
            (self.run / receipt).write_text("\n".join(lines) + "\n")

    def review(self):
        return review.review_run(self.run, dependency=self.stub)

    def edit(self, rel, replace, replacement, *, resign=True):
        path = self.run / rel
        original = path.read_text()
        self.assertIn(replace, original)
        path.write_text(original.replace(replace, replacement))
        if resign:
            self.resign()

    def test_synthetic_fan_only_drc_zero_is_not_timing_or_hardware_proof(self):
        result = self.review()
        self.assertEqual(result["status"],
                         "PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED")
        self.assertEqual(result["drc"]["default_ruledeck_reported_findings"], 0)
        self.assertEqual(result["timing"]["WNS_ns"], "NA")
        self.assertFalse(result["timing"]["future_neuromorphic_timing_proven"])
        self.assertEqual(result["resources"]["fabric_luts"], 0)
        self.assertEqual(result["resources"]["PS8"], 1)
        self.assertEqual(result["resources"]["OBUF"], 1)
        self.assertEqual(result["route_log_warning_classes"]["other"], 0)
        self.assertEqual(result["verified_ledgers"], {
            "99_evidence_sha256.txt": 11,
            "98_route_evidence_sha256.txt": 8,
        })
        self.assertFalse(result["physical_programming_authorized"])
        self.assertFalse(result["protected_hpm0_hardware_ready"])

    def test_original_hash_tamper_is_rejected(self):
        self.edit(review.REPORTS["drc"], "Checks found: 0", "Checks found: 99",
                  resign=False)
        with self.assertRaisesRegex(review.ReviewRejected, "changed receipt content"):
            self.review()

    def test_even_resigned_nonzero_drc_is_rejected(self):
        self.edit(review.REPORTS["drc"], "Checks found: 0", "Checks found: 1")
        with self.assertRaisesRegex(review.ReviewRejected, "nonzero reported DRC"):
            self.review()

    def test_even_resigned_timing_margin_for_clocked_fabric_requires_new_review(self):
        self.edit(review.REPORTS["timing"],
                  "NA           NA                     NA                   NA",
                  "0.125        0.000                  0                    48")
        with self.assertRaisesRegex(review.ReviewRejected, "unexpected nonempty"):
            self.review()

    def test_even_resigned_fabric_registers_rejected(self):
        self.edit(review.REPORTS["utilization"],
                  "| CLB Registers | 0 |", "| CLB Registers | 10 |")
        with self.assertRaisesRegex(review.ReviewRejected, "passive design unexpectedly"):
            self.review()

    def test_duplicated_resource_rows_must_agree(self):
        self.edit(review.REPORTS["utilization"],
                  "| PS8 | 1 | Advanced", "| PS8 | 2 | Advanced")
        with self.assertRaisesRegex(review.ReviewRejected, "conflicting resource"):
            self.review()

    def test_missing_fan_output_buffer_rejected(self):
        self.edit(review.REPORTS["utilization"], "| OBUF | 1 |", "| OBUF | 0 |")
        with self.assertRaisesRegex(review.ReviewRejected, "PS8\\+fan OBUF"):
            self.review()

    def test_clock_report_missing_expected_ps8_plclk_rejected(self):
        self.edit(review.REPORTS["clocks"], "PLCLK[1]", "PLCLK[2]")
        with self.assertRaisesRegex(review.ReviewRejected, "clock definitions"):
            self.review()

    def test_unreviewed_warning_rejected_even_if_resigned(self):
        self.edit("05_passive_route_vivado.log",
                  "WARNING: [Board 49-26]",
                  "WARNING: [Place 30-9999] unknown error:")
        with self.assertRaisesRegex(review.ReviewRejected, "unreviewed route warning"):
            self.review()

    def test_critical_warning_rejected_even_if_resigned(self):
        self.edit("05_passive_route_vivado.log",
                  "WARNING: [Board 49-26]",
                  "CRITICAL WARNING: [Board 49-26]")
        with self.assertRaisesRegex(review.ReviewRejected, "critical warning"):
            self.review()

    def test_unsigned_earlier_hardware_approval_claim_rejected(self):
        self.edit("50_pc_route_evidence_review.json",
                  '"bitstream_generated": false', '"bitstream_generated": true')
        with self.assertRaisesRegex(review.ReviewRejected, "cannot grant bitstream"):
            self.review()

    def test_missing_ledger_entry_or_duplicate_line_is_rejected(self):
        p = self.run / "98_route_evidence_sha256.txt"
        lines = p.read_text().splitlines()
        p.write_text("\n".join(lines[:-1] + [lines[0]]) + "\n")
        with self.assertRaisesRegex(review.ReviewRejected, "unknown/duplicate"):
            self.review()

    def test_symlinked_report_rejected(self):
        p = self.run / review.REPORTS["clocks"]
        saved = self.run / "saved_clock.rpt"
        p.rename(saved)
        p.symlink_to(saved)
        with self.assertRaisesRegex(review.ReviewRejected, "symlink"):
            self.review()

    def test_read_only_and_no_bitstream_or_board_calls(self):
        source = SCRIPT.read_text()
        for token in (
            "subprocess.run(", "os.system(", "write_bitstream(",
            "program_hw_devices(", "open_hw_manager(", "/dev/uio",
            "/dev/mem", "xmutil ", "create_project ", "launch_runs ",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
