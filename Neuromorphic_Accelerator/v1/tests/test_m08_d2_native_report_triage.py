"""No hardware: synthetic fixtures for the D2 original fan report triage."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/m08_d2_triage_native_fan_reports.py"
spec = importlib.util.spec_from_file_location("m08_d2_native_triage", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fake_reports(folder: Path) -> None:
    identity = {
        "schema": "m08-d2-native-fan-dcp-readonly-v1",
        "vivado": "2025.2",
        "dcp_sha256": mod.SHA,
        "part": "xck26-sfvc784-2LV-c",
        "top": "m08_page_ps_wrapper",
        "fan_pin": "A12",
        "fan_iostandard": "LVCMOS33",
        "fan_direction": "OUT",
        "clock_count": "2",
        "wns_ns": "5.355",
        "whs_ns": "0.029",
        "original_routed_dcp": "YES",
        "root_cause_proven": "NO",
        "physical_mmio_performed": "NO",
        "new_bitstream_created": "NO",
        "board_programmed": "NO",
    }
    (folder / "10_dcp_identity.txt").write_text(
        "".join(f"{k}={v}\n" for k, v in identity.items()))
    (folder / "11_dcp_timing.rpt").write_text(
        "Design State      : Routed\nchecking no_clock (0)\n"
        "checking unconstrained_internal_endpoints (0)\n"
        "All user specified timing constraints are met.\n"
        "clk_pl_0 {0.000 5.000} 10.000 100.000\n"
        "clk_pl_1 {0.000 5.000} 10.000 100.000\n"
        "5.355 0.029\n" + "native timing detail " * 12)
    all_names = [
        f"m08_page_ps_i/ctrl_sc/inst/{prefix}/{channel}/inst/mi_handler_m_sc_areset_pipe"
        for prefix in ("m00_nodes", "m01_nodes", "s00_nodes", "switchboards")
        for channel in ("ar_node", "aw_node", "b_node", "r_node", "w_node")
    ]
    drc_names = all_names[:14]
    (folder / "12_dcp_drc.rpt").write_text(
        "Design State : Fully Routed\nChecks found: 1\n"
        "| RTSTAT-10 | Warning | No routable loads | 1 |\n"
        "15 net(s) have no routable loads.\n"
        + ",\n".join(drc_names) + "\n")
    (folder / "14_dcp_clock_utilization.rpt").write_text(
        "BUFG_PS/O  PS8/PLCLK[0]\n"
        "| 1678 | 0 | 10.000 | clk_pl_0 |\n"
        + "Original source clock and fan route " * 5)
    (folder / "15_dcp_clock_interaction.rpt").write_text(
        "Design State : Routed\nClock Interaction Table\n"
        "clk_pl_0 clk_pl_0 rise - rise 5.35 0.00 0 4591 10.00 Clean Partial False Path\n"
        + "Native report footer " * 5)
    (folder / "16_dcp_reset_net_inventory.txt").write_text(
        "schema=m08-d2-native-fan-dcp-reset-net-inventory-v1\n"
        "matching_net_count=20\n"
        + "".join(f"RESET_NET|{net}\n" for net in all_names)
        + "reset_warning_proven_root_cause=NO\n")
    (folder / "17_dcp_cdc.rpt").write_text(
        "Vivado v2025.2  K26 Design State : Routed\n"
        + "Native report header " * 6
        + "\nCDC Report\n")


class TestNativeReportTriage(unittest.TestCase):
    def test_original_routed_reports_are_consistent_but_not_hardware_signoff(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            fake_reports(folder)
            result = mod.assess(folder)
            self.assertEqual(result["original_routed_dcp_sha256"], mod.SHA)
            self.assertEqual(result["smartconnect_reset"]["drc_counted_nets"], 15)
            self.assertEqual(result["smartconnect_reset"]["drc_explicit_named_nets"], 14)
            self.assertEqual(result["smartconnect_reset"]["net_inventory_pattern_matches"], 20)
            self.assertEqual(result["routed_timing"]["pl0_route_loads"], 1678)
            self.assertEqual(result["cdc"], "EMPTY_REPORT_NO_CDC_SIGNOFF")
            self.assertFalse(result["physical_runtime"]["hardware_retry_authorized"])
            self.assertFalse(result["timing_exceptions"]["signed_off"])
            self.assertEqual(len(result["actual_native_report_sha256"]), 7)

    def test_unaccepted_dcp_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            fake_reports(folder)
            path = folder / "10_dcp_identity.txt"
            path.write_text(path.read_text().replace(mod.SHA, "0" * 64))
            with self.assertRaisesRegex(mod.TriageError, "dcp_sha256"):
                mod.assess(folder)

    def test_new_reset_warning_is_not_silently_waived(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            fake_reports(folder)
            path = folder / "12_dcp_drc.rpt"
            path.write_text(path.read_text().replace("15 net(s)", "16 net(s)"))
            with self.assertRaisesRegex(mod.TriageError, "warning changed"):
                mod.assess(folder)

    def test_missing_cdc_or_symlink_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            fake_reports(folder)
            cdc = folder / "17_dcp_cdc.rpt"
            cdc.unlink()
            with self.assertRaisesRegex(mod.TriageError, "missing/unsafe"):
                mod.assess(folder)
            cdc.symlink_to(folder / "11_dcp_timing.rpt")
            with self.assertRaisesRegex(mod.TriageError, "missing/unsafe"):
                mod.assess(folder)

    def test_false_path_diagnostics_are_not_signoff_even_if_present(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            fake_reports(folder)
            (folder / "18_dcp_exception_coverage.rpt").write_text(
                "sample exception output")
            (folder / "19_dcp_ignored_paths_inventory.txt").write_text(
                "status=SAMPLED_NOT_EXHAUSTIVE\nsample_returned=2\n")
            result = mod.assess(folder)
            self.assertEqual(result["timing_exceptions"]["coverage"], "PRESENT_REVIEW_REQUIRED")
            self.assertEqual(result["timing_exceptions"]["ignored_path_sample"],
                             "PRESENT_NOT_EXHAUSTIVE")
            self.assertFalse(result["physical_runtime"]["rcu_stall_root_cause_proven"])

    def test_wrong_timing_or_clock_interaction_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            fake_reports(folder)
            timing = folder / "11_dcp_timing.rpt"
            timing.write_text(timing.read_text().replace("clk_pl_0 {0.000 5.000} 10.000",
                                                        "clk_pl_0 {0.000 5.000} 9.000"))
            with self.assertRaisesRegex(mod.TriageError, "100MHz"):
                mod.assess(folder)
            fake_reports(folder)
            interaction = folder / "15_dcp_clock_interaction.rpt"
            interaction.write_text(interaction.read_text().replace(
                "Partial False Path", "Timed (unsafe)"))
            with self.assertRaisesRegex(mod.TriageError, "partial false path"):
                mod.assess(folder)

    def test_triage_source_readonly_no_kernel_or_vendor_access(self):
        source = SOURCE.read_text()
        self.assertIn("report_contents", source)
        self.assertIn("hardware_retry_authorized", source)
        for forbidden in ("subprocess.run", "mmap.mmap", "/dev/mem",
                          "/dev/uio", "xmutil", "program_hw_devices", "write_bitstream"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
