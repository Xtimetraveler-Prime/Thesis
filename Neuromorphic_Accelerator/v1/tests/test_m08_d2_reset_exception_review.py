"""Synthetic PC-only regression for owner fan-DCP reset exception review.

All fixtures are source-generated and are NOT actual vendor run evidence.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d2_review_reset_timing_exceptions.py"
spec = importlib.util.spec_from_file_location("m08_d2_reset_exceptions", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def populate(folder: Path) -> None:
    ident = {
        "schema": "m08-d2-native-fan-dcp-readonly-v1",
        "vivado": "2025.2", "dcp_sha256": mod.ORIGINAL_DCP_SHA,
        "part": "xck26-sfvc784-2LV-c", "top": "m08_page_ps_wrapper",
        "fan_pin": "A12", "fan_iostandard": "LVCMOS33",
        "fan_direction": "OUT", "original_routed_dcp": "YES",
        "exception_coverage_report": "GENERATED_REQUIRES_OWNER_REVIEW",
        "ignored_paths_diagnostic": "SAMPLED_NOT_EXHAUSTIVE",
        "ignored_paths_sample_count": "30",
        "timing_exceptions_signed_off": "NO",
        "live_clock_reset_or_atb_verified": "NO",
        "root_cause_proven": "NO", "physical_mmio_performed": "NO",
        "new_bitstream_created": "NO", "board_programmed": "NO",
    }
    (folder / "10_dcp_identity.txt").write_text(
        "".join(f"{k}={v}\n" for k, v in ident.items()))
    (folder / "13_dcp_methodology.rpt").write_text(
        "Tool Version : Vivado v.2025.2\n"
        "Design       : m08_page_ps_wrapper\n"
        "Design State : Fully Routed\n"
        "REPORT SUMMARY\nChecks found: 0\n"
        + "methodology original vendor-like output\n" * 6)
    positions = (4,5,7,8,9,10,11,13,15,16,18,20,22,24,27,29,31,33,
                 35,37,38,40,42,44,46)
    rows = [f"{n} False Path false false 1 pins 3 100.00\n"
            for n in positions]
    rows += [f"{n} False Path false false 1 cells {points} {cov}\n"
             for n, points, cov in ((48,1,"33.33"),(49,0,"0.00"),
                                    (50,0,"0.00"),(51,1,"0.00"))]
    (folder / "18_dcp_exception_coverage.rpt").write_text(
        "Tool Version : Vivado v.2025.2\n"
        "Design State      : Routed\n"
        "Command: report_exceptions -coverage -file owner-path\n"
        "Exceptions Report\n" + "".join(rows))
    patterns = (
        "s00_entry_pipeline/s00_transaction_regulator",
        "m00_nodes/m00_aw_node", "m00_nodes/m00_ar_node",
        "m01_nodes/m01_ar_node", "switchboards/i_nodes/i_ar_node",
        "s00_nodes/s00_r_node", "m00_nodes/m00_r_node",
        "m00_exit_pipeline/m00_exit", "m00_nodes/m00_w_node",
        "switchboards/i_nodes/i_w_node",
    )
    samples = []
    for group in patterns:
        synchronizer = ("xpm_cdc_async_rst_inst"
                        if ("pipeline" in group or "regulator" in group)
                        else "s_sc_xpm_cdc_async_rst_inst")
        for stage in range(3):
            end = (f"m08_page_ps_i/ctrl_sc/inst/{group}/inst/{synchronizer}"
                   f"/arststages_ff_reg[{stage}]/CLR")
            samples.append(f"IGNORED_PATH|{mod.START}|{end}\n")
    (folder / "19_dcp_ignored_paths_inventory.txt").write_text(
        "schema=m08-d2-routed-ignored-timing-paths-sample-v1\n"
        "sample_max_paths=30\nstatus=SAMPLED_NOT_EXHAUSTIVE\n"
        "sample_returned=30\n" + "".join(samples) +
        "all_false_paths_reviewed=NO\n"
        "runtime_clock_reset_proven=NO\n")


class OriginalResetExceptionReviewTests(unittest.TestCase):
    def test_expected_vendor_shaped_evidence_classified_without_hardware_signoff(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            populate(folder)
            result = mod.inspect(folder)
            self.assertEqual(result["exception_coverage"]["false_path_rows"], 29)
            self.assertEqual(result["exception_coverage"]["cell_entries_zero_percent"], 3)
            self.assertEqual(result["ignored_timing_sample"]["unique_reset_synchronizers"], 10)
            self.assertEqual(result["ignored_timing_sample"]["sample_size"], 30)
            self.assertEqual(result["methodology"]["checks_found"], 0)
            self.assertFalse(result["physical_hardware"]["runtime_pl0_verified"])
            self.assertFalse(result["physical_hardware"]["new_image_approved_for_board"])
            self.assertFalse(result["ignored_timing_sample"]["all_paths_checked"])
            self.assertEqual(len(result["input_sha256"]), 4)

    def test_wrong_original_dcp_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            populate(p)
            f = p / "10_dcp_identity.txt"
            f.write_text(f.read_text().replace(mod.ORIGINAL_DCP_SHA, "0"*64))
            with self.assertRaisesRegex(mod.ReviewRejected, "dcp_sha256"):
                mod.inspect(p)

    def test_methodology_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            populate(p)
            f = p / "13_dcp_methodology.rpt"
            f.write_text(f.read_text().replace("Checks found: 0", "Checks found: 1"))
            with self.assertRaisesRegex(mod.ReviewRejected, "methodology violations"):
                mod.inspect(p)

    def test_coverage_zero_changed_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            populate(p)
            f = p / "18_dcp_exception_coverage.rpt"
            f.write_text(f.read_text().replace(
                "49 False Path false false 1 cells 0 0.00",
                "49 False Path false false 1 cells 1 33.33"))
            with self.assertRaisesRegex(mod.ReviewRejected, "coverage drift"):
                mod.inspect(p)

    def test_non_reset_data_path_exclusion_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            populate(p)
            f = p / "19_dcp_ignored_paths_inventory.txt"
            f.write_text(f.read_text().replace(
                "/arststages_ff_reg[2]/CLR", "/axi_reg[2]/D", 1))
            with self.assertRaisesRegex(mod.ReviewRejected, "not at XPM async reset"):
                mod.inspect(p)

    def test_duplicate_stage_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            populate(p)
            f = p / "19_dcp_ignored_paths_inventory.txt"
            rows = f.read_text().splitlines(keepends=True)
            targets = [i for i,line in enumerate(rows) if line.startswith("IGNORED_PATH|")]
            rows[targets[1]] = rows[targets[0]]
            f.write_text("".join(rows))
            with self.assertRaisesRegex(mod.ReviewRejected, "duplicate reset synchronizer"):
                mod.inspect(p)

    def test_missing_or_symlinked_vendor_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            populate(p)
            f = p / "13_dcp_methodology.rpt"
            f.unlink()
            with self.assertRaisesRegex(mod.ReviewRejected, "missing/symlinked"):
                mod.inspect(p)
            f.symlink_to(p / "10_dcp_identity.txt")
            with self.assertRaisesRegex(mod.ReviewRejected, "missing/symlinked"):
                mod.inspect(p)

    def test_script_never_accesses_board_or_modifies_evidence(self):
        text = SCRIPT.read_text()
        self.assertIn("m08_quarantine_active", text)
        for unsafe in ("subprocess.run", "mmap.mmap", "program_hw_devices",
                       "write_bitstream", "open_checkpoint", "devmem", "/dev/uio",
                       "xmutil", "shell=True", "write_text("):
            self.assertNotIn(unsafe, text)


if __name__ == "__main__":
    unittest.main()
