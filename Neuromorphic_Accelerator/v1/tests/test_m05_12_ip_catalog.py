"""M05.12b source-only safety checks for offline IP catalog probe.

Native CI does not invoke Vivado or any physical hardware.
"""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class M0512IPCatalogSafetyTests(unittest.TestCase):
    def test_bash_syntax_help_and_invalid_argument_do_not_need_vivado(self):
        script = ROOT / "scripts/run_m05_12_ip_catalog.sh"
        self.assertEqual(subprocess.run(["bash", "-n", str(script)],
                                        capture_output=True).returncode, 0)
        help_run = subprocess.run(["bash", str(script), "--help"],
                                  capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0)
        self.assertIn("NO BOARD", help_run.stdout)
        invalid = subprocess.run(["bash", str(script), "--bad"],
                                 capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)

    def test_probe_is_catalog_only_with_no_hw_or_persistent_bd_actions(self):
        script = (ROOT / "scripts/run_m05_12_ip_catalog.sh").read_text()
        tcl = (ROOT / "scripts/m05_12_ip_catalog.tcl").read_text()
        self.assertIn("create_project -in_memory", tcl)
        self.assertIn("get_ipdefs", tcl)
        self.assertIn("create_bd_cell -type ip", tcl)
        self.assertIn("close_project", tcl)
        self.assertIn("mktemp -d", script)
        self.assertIn("source_sha256.txt", script)
        self.assertIn("result.txt", script)
        for forbidden in (
            "connect_hw_server", "open_hw_target", "program_hw_devices",
            "launch_runs", "write_bitstream", "write_bd_tcl",
            "write_hw_platform", "export_hardware", "write_device_image",
            "xsdb", "open_project", "open_bd_design",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, tcl)
                self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
