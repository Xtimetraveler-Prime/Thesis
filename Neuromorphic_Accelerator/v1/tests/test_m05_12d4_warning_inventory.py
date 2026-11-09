"""M05.12d.4 D4.1 SYNTHETIC host-only warnings; never genuine Vivado proof."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d4_warning_inventory import (
    parse_warnings, inspect_original, strict_parent, ORIGINAL, ORIGINAL_COMMIT,
)

# Shape mirrors published BD 41-2384 formatting. ALL ROWS HERE ARE SYNTHETIC.
LOG = """INFO: [BD 41-1029] Generation completed for some IP
WARNING: [BD 41-2384] Width mismatch when connecting pin: '/m00_nodes/m00_r_node/s_sc_payld'(55) to pin: '/m00_nodes/S_SC_R_payld'(53) - Only lower order bits will be connected.
WARNING: [BD 41-2384] Width mismatch when connecting pin: '/m05_nodes/m05_aw_node/s_sc_payld'(172) to pin: '/m05_nodes/S_SC_AW_payld'(168) - Only lower order bits will be connected.
WARNING: [BD 41-2384] Width mismatch when connecting pin: '/s00_axi2sc/s_sc_b_payld'(7) to pin: '/s00_nodes/M_SC_B_payld'(9) - Only lower order bits will be connected.
WARNING: [BD 41-237] Bus Interface property AWUSER_WIDTH does not match between /ps/S_AXI_HP0_FPD(1) and /mem_sc/M00_AXI(0)
WARNING: [BD 41-3281] Automatic configuration for SmartConnect remains uncertain.
WARNING: [BD 41-1629] Excluded all OCM address paths.
"""


class M05D4WarningInventoryTests(unittest.TestCase):
    def test_extract_exact_two_pin_widths_narrowing_and_line_numbers(self):
        rows = parse_warnings(LOG)
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["line"] for r in rows], list(range(2, 8)))
        self.assertEqual(rows[0]["source_pin"], "/m00_nodes/m00_r_node/s_sc_payld")
        self.assertEqual(rows[0]["destination_pin"], "/m00_nodes/S_SC_R_payld")
        self.assertEqual((rows[0]["source_width"], rows[0]["destination_width"],
                          rows[0]["narrowed_bits"]), (55, 53, 2))
        self.assertEqual((rows[1]["source_width"], rows[1]["destination_width"],
                          rows[1]["narrowed_bits"]), (172, 168, 4))
        self.assertEqual((rows[2]["source_width"], rows[2]["destination_width"],
                          rows[2]["narrowed_bits"]), (7, 9, 0))
        self.assertEqual(rows[0]["channel_hint"], "R")
        self.assertEqual(rows[1]["channel_hint"], "AW")
        self.assertEqual(rows[2]["channel_hint"], "B")

    def test_m00_m05_does_not_prove_parent_smartconnect(self):
        rows = parse_warnings(LOG)
        for r in rows[:3]:
            self.assertEqual(r["parent"], "UNATTRIBUTED")
            self.assertEqual(r["classification"], "UNRESOLVED_BLOCKER")
        # An endpoint named in the interface-property warning IS direct
        # attribution to mem_sc but it does not establish safe USER semantics.
        self.assertEqual(rows[3]["parent"], "mem_sc")
        self.assertEqual(rows[3]["field_hint"], ["AWUSER_WIDTH"])
        self.assertEqual(rows[3]["classification"], "UNRESOLVED_BLOCKER")

    def test_explicit_prefix_and_ambiguous_multi_parent_fail_closed(self):
        msg = "WARNING: [BD 41-2384] Width mismatch when connecting pin: '/ctrl_sc/m00_nodes/a'(9) to pin: '/ctrl_sc/m00_nodes/b'(7) - Only lower order bits will be connected."
        self.assertEqual(parse_warnings(msg)[0]["parent"], "ctrl_sc")
        altered = msg.replace("/ctrl_sc/m00_nodes/b", "/mem_sc/m00_nodes/b")
        self.assertEqual(parse_warnings(altered)[0]["parent"], "AMBIGUOUS")

    def test_unknown_code_and_critical_warning_not_suppressed(self):
        r = parse_warnings(
            "CRITICAL WARNING: [BD 41-9999] new semantic unknown\n"
            "WARNING: [BD 41-2384] WARNING source format changed")
        self.assertEqual([x["id"] for x in r], ["BD 41-9999", "BD 41-2384"])
        self.assertEqual(r[0]["severity"], "CRITICAL WARNING")
        self.assertIn("unrecognized", r[0]["reason"])
        self.assertIsNone(r[1]["narrowed_bits"])
        self.assertEqual(r[1]["classification"], "UNRESOLVED_BLOCKER")

    def test_duplicate_warnings_remain_distinct_occurrences(self):
        row = LOG.splitlines()[1]
        records = parse_warnings(row + "\n" + row + "\n")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["line"], 1)
        self.assertEqual(records[1]["line"], 2)

    def test_no_unreviewed_benign_whitelist_for_auto_config_and_ocm(self):
        records = parse_warnings(LOG)
        self.assertEqual(records[4]["classification"], "UNRESOLVED_BLOCKER")
        self.assertEqual(records[5]["classification"], "UNRESOLVED_BLOCKER")
        self.assertIn("OCM", records[5]["reason"])
        self.assertIn("auto-configuration", records[4]["reason"])

    def test_new_report_path_and_immutability_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            wrong = base / "neuromorphic_v1_m05_12d3_ip_output_old"
            wrong.mkdir()
            with self.assertRaises(ValueError):
                strict_parent(wrong / "02_warning_inventory.json")
            outdir = base / "neuromorphic_v1_m05_12d4_warning_inventory_SYNTHETIC"
            outdir.mkdir()
            report = outdir / "02_warning_inventory.json"
            self.assertEqual(strict_parent(report), outdir.resolve())
            report.write_text("SYNTHETIC DO NOT USE AS OWNER REPORT")
            with self.assertRaises(ValueError):
                strict_parent(report)
            bad_original = base / ORIGINAL
            bad_original.mkdir()
            with self.assertRaises((ValueError, OSError)):
                inspect_original(bad_original)

    def test_runner_is_offline_readonly_and_syntax_valid(self):
        run = ROOT / "scripts/run_m05_12d4_warning_inventory.sh"
        text = run.read_text()
        for required in (ORIGINAL, "03_vivado.log", "16_ip_output_sha256_manifest.txt",
                         "m05_12d4_warning_inventory.py", "02_warning_inventory.json",
                         "result.txt", "source_sha256.txt", "mktemp -d"):
            self.assertIn(required, text)
        for forbidden in ("write_bitstream", "program_hw_devices", "connect_hw_server",
                          "open_hw_target", "xsdb", "synth_design", "launch_runs",
                          "vivado -mode", "vitis", "rm -rf"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(subprocess.run(["bash", "-n", str(run)],
                         capture_output=True).returncode, 0)

    def test_cli_missing_original_must_not_emit_fake_report(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp) / "neuromorphic_v1_m05_12d4_warning_inventory_SYNTHETIC"
            d.mkdir()
            out = d / "02_warning_inventory.json"
            cmd = [sys.executable, str(ROOT / "scripts/m05_12d4_warning_inventory.py"),
                   "--original-d3", str(d / "missing"),
                   "--output", str(out)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(out.exists())
            self.assertIn("FAIL:", result.stderr)


if __name__ == "__main__":
    unittest.main()
