"""M05 D4.4 SYNTHETIC evidence shape/negative tests; no M05 closure claim."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d4_exit_audit import audit


def fixture(root: Path):
    d = root / "neuromorphic_v1_m05_12d4_protocol_gate_SYNTHETIC"
    d.mkdir()
    (d / "source_sha256.txt").write_text("source snapshot\n")
    (d / "08_source_sha256_after.txt").write_text("source snapshot\n")
    risk = {
        "scope": "M05_D4_2_GENUINE_ORIGINAL_READONLY_RISK_AND_NO_AUTOMATIC_CHANGE",
        "warning_counts": {"UNRESOLVED_BLOCKER": 63,
                           "DOCUMENTED_INTENTIONAL_OCM_EXCLUSION_ONLY": 1},
        "decision": "NO_MUTATION_JUSTIFIED_FROM_CONFIGURATION_READBACK_ALONE",
        "original_d3": "/synthetic/D3", "d4_1b_property_evidence": "/synthetic/D4_BD",
        "m05_exit": "OPEN",
    }
    vendor = {
        "scope": "ORIGINAL_D3_READ_ONLY_VENDOR_SIM_SOURCE_DISCOVERY",
        "compile_order_status": "QUERY_OK", "simulation": "NOT_RUN",
        "vendor_downsize_axi_protocol": "NOT_PROVEN",
        "original_d3": "/synthetic/D3", "original_d4_1b": "/synthetic/D4_BD",
    }
    (d / "02_original_axi_risk.json").write_text(json.dumps(risk) + "\n")
    (d / "07_post_original_axi_risk.json").write_text(json.dumps(risk) + "\n")
    (d / "06_model_discovery_audit.json").write_text(json.dumps(vendor) + "\n")
    return d, risk, vendor


class ExitAuditTests(unittest.TestCase):
    def test_d4_exit_audit_success_still_m05_open(self):
        with tempfile.TemporaryDirectory() as t:
            folder, _, _ = fixture(Path(t))
            out = audit(folder)
            self.assertEqual(out["m05_closure"], "OPEN_REQUIRES_EVIDENCE_AND_USER_APPROVAL")
            self.assertEqual(out["m06"], "NOT_STARTED")
            self.assertEqual(out["d4_3_genuine_vendor_simulation"], "NOT_RUN")
            self.assertEqual(out["d4_2_configuration_correction"],
                             "NOT_APPLIED_63_WARNINGS_STILL_BLOCKED")
            self.assertEqual(out["physical_board"], "NOT_AUTHORIZED")

    def test_original_checksum_drift_blocks_m05_audit(self):
        with tempfile.TemporaryDirectory() as t:
            folder, _, _ = fixture(Path(t))
            (folder / "08_source_sha256_after.txt").write_text("BAD\n")
            with self.assertRaisesRegex(ValueError, "immutable"):
                audit(folder)

    def test_original_vendor_model_simulated_pass_forgery_blocks_audit(self):
        with tempfile.TemporaryDirectory() as t:
            folder, _, vendor = fixture(Path(t))
            vendor["simulation"] = "PASS"
            (folder / "06_model_discovery_audit.json").write_text(json.dumps(vendor))
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                audit(folder)

    def test_original_warning_count_drop_and_missing_postaudit_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder, risk, _ = fixture(Path(t))
            risk["warning_counts"]["UNRESOLVED_BLOCKER"] = 0
            for name in ("02_original_axi_risk.json", "07_post_original_axi_risk.json"):
                (folder / name).write_text(json.dumps(risk))
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                audit(folder)
        with tempfile.TemporaryDirectory() as t:
            folder, _, _ = fixture(Path(t))
            (folder / "07_post_original_axi_risk.json").unlink()
            with self.assertRaisesRegex(ValueError, "immutable"):
                audit(folder)

    def test_no_m06_approval_or_physical_run_in_source_runners(self):
        script = (ROOT / "scripts/run_m05_12d4_protocol_gate.sh").read_text()
        self.assertIn("m05_12d4_exit_audit.py", script)
        self.assertIn("09_m05_exit_audit.json", script)
        for forbidden in ("program_hw_devices", "connect_hw_server",
                          "write_bitstream", "launch_simulation", "synth_design"):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
