"""No-board regression: M08 first identity hang quarantines BOTH MMIO CLI entry points."""
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
NEW = ROOT / "scripts/m08_kv260_physical_uio_operator.py"
OLD = ROOT / "scripts/m08_path_a_uio_identity_guard.py"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("m08_quarantine_operator", NEW)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PostIncidentSafetyQuarantine(unittest.TestCase):
    def test_identity_and_page_unconditionally_quarantined(self):
        for mode in ("identity", "page"):
            with self.subTest(mode=mode), self.assertRaisesRegex(
                    m.StopPhysicalTest, "QUARANTINED_AFTER_KV260_RCU_STALL"):
                m.reject_quarantined_mmio_mode(mode)
        m.reject_quarantined_mmio_mode("preflight")

    def test_all_physical_cli_flags_cannot_bypass_quarantine(self):
        for mode in ("identity", "page"):
            with self.subTest(mode=mode), patch.object(m, "check_live_platform") as live:
                argv = ["program", "--mode", mode, "--acknowledge-axi-read-risk",
                        "--acknowledge-axi-write-risk",
                        "--acknowledge-rollback-not-yet-exercised",
                        "--output-file", "/home/ubuntu/m08_2b_tests_TEST/"
                                         +mode+".json"]
                env = {"M08_EXPLICIT_PHYSICAL_TEST_APPROVED": "YES",
                       "M08_EXPLICIT_PAGE_WRITE_APPROVED": "YES"}
                with patch.object(sys, "argv", argv), patch.dict(os.environ, env):
                    self.assertEqual(m.main(), 2)
                live.assert_not_called()

    def test_old_entry_point_rejected_with_full_consent(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run(
                [sys.executable, str(OLD), "--mode", "identity",
                 "--expected", "present", "--explicit-identity-read",
                 "--sysfs-root", "/sys/class/uio",
                 "--review-file", str(Path(d) / "fake-approved.json"),
                 "--review-sha256", "f" * 64],
                cwd=ROOT, env={**os.environ, "M08_UIO_IDENTITY_READ_AUTHORIZED": "YES"},
                capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 2)
        self.assertIn("MMIO_QUARANTINED_AFTER_PHYSICAL_RCU_STALL", p.stderr)

    def test_source_interlocks_and_no_force_bypass(self):
        new_src = NEW.read_text()
        old_src = OLD.read_text()
        self.assertIn("reject_quarantined_mmio_mode(args.mode)", new_src)
        self.assertIn('mode == "preflight"', new_src)
        self.assertIn('raise GuardRejected("M08_MMIO_QUARANTINED', old_src)
        self.assertNotIn("--force-retry", new_src + old_src)


if __name__ == "__main__":
    unittest.main()
