"""D3.2 stock read-only physical baseline: synthetic-only PC safety negatives."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "scripts/m08_d3_2_stock_baseline_pc.py"
spec = importlib.util.spec_from_file_location("test_m08_d3_2_stock_baseline", S)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class StockBaselinePcTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name) / "M08"
        self.base.mkdir()
        self.candidate = self.base / "m08_d3_2_passive_synth_gKr8mQe6"
        self.candidate.mkdir()
        self.owner = self.base / "m08_d3_2_manual_readiness.json"
        self.record = {
            "schema": "m08-d3-2-owner-physical-readiness-v1",
            "candidate_bit_sha256": m.EXPECTED_BIT_SHA,
            **{x: True for x in m.READINESS},
            "owner_confirms_no_programming_in_this_step": True,
        }
        self.owner.write_text(json.dumps(self.record))
        self.args = types.SimpleNamespace(
            target=m.BOARD_TARGET, readiness=self.owner,
            evidence_base=self.base, candidate_run=self.candidate,
        )

    def mock_stdout(self, *, bad_rc_label=None):
        lines = ["M08_D3_2_STOCK_READONLY_BEGIN"]
        for label in m.LABELS:
            lines += [
                "M08_D3_2_PROBE_BEGIN|" + label,
                "mock read-only field",
                "M08_D3_2_PROBE_END|" + label +
                ("|rc=3" if label == bad_rc_label else "|rc=0"),
            ]
        lines.append("M08_D3_2_STOCK_READONLY_END_NO_PL_OR_KERNEL_CHANGES")
        return ("\n".join(lines) + "\n").encode()

    def stub_runner(self, cmd, **kwargs):
        self.assertEqual(cmd[0], "ssh")
        self.assertEqual(cmd[-2:], [m.BOARD_TARGET, "bash -s"])
        self.assertIn(b"M08_D3_2_STOCK_READONLY_BEGIN", kwargs["input"])
        self.assertNotIn(b"program_hw_devices", kwargs["input"])
        self.assertNotIn(b"xmutil unloadapp", kwargs["input"])
        self.assertIn("-T", cmd)
        self.assertIn("StrictHostKeyChecking=yes", cmd)
        self.assertNotIn("sudo", cmd)
        self.assertIn(b"sudo -n xmutil listapps", kwargs["input"])
        return CompletedProcess(cmd, 0, self.mock_stdout(), b"")

    def patch_candidate(self):
        original = m.candidate_audit
        self.addCleanup(setattr, m, "candidate_audit", original)
        m.candidate_audit = lambda _: {
            "candidate_sha256": m.EXPECTED_BIT_SHA,
            "candidate_size_bytes": m.EXPECTED_BIT_BYTES,
            "candidate_kind": "MOCK_ONLY",
            "original_sha_99_98_96_verified": False,
            "physical_programming_authorized": False,
        }

    def test_board_source_six_readonly_probes(self):
        sh = m.check_script()
        self.assertIn(b"sudo -n xmutil listapps", sh)
        self.assertEqual(sh.count(b"sudo -n xmutil listapps"), 1)
        self.assertIn(b"cat /sys/class/fpga_manager/fpga0/state", sh)
        self.assertNotIn(b"xmutil loadapp", sh)
        self.assertNotIn(b"program_hw_devices", sh)
        self.assertNotIn(b"/dev/uio", b"\n".join(
            x for x in sh.splitlines() if not x.lstrip().startswith(b"#")))

    def test_expected_new_sha_is_not_failed_hardware_sha(self):
        self.assertEqual(m.EXPECTED_BIT_SHA,
                         "07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547")
        self.assertEqual(m.EXPECTED_BIT_BYTES, 7797839)
        self.assertNotEqual(m.EXPECTED_BIT_SHA, m.OLD_QUARANTINED_SHA)

    def test_owner_manual_controls_must_all_be_explicit(self):
        m.parse_readiness(self.owner, m.EXPECTED_BIT_SHA)
        for key in m.READINESS:
            obj = dict(self.record)
            obj[key] = False
            self.owner.write_text(json.dumps(obj))
            with self.assertRaisesRegex(m.BaselineRejected, key):
                m.parse_readiness(self.owner, m.EXPECTED_BIT_SHA)
        self.owner.write_text(json.dumps(self.record))

    def test_wrong_candidate_sha_or_owner_mode_rejected(self):
        self.record["candidate_bit_sha256"] = "0"*64
        self.owner.write_text(json.dumps(self.record))
        with self.assertRaisesRegex(m.BaselineRejected, "exact"):
            m.parse_readiness(self.owner, m.EXPECTED_BIT_SHA)
        self.record["candidate_bit_sha256"] = m.EXPECTED_BIT_SHA
        self.record["owner_confirms_no_programming_in_this_step"] = False
        self.owner.write_text(json.dumps(self.record))
        with self.assertRaisesRegex(m.BaselineRejected, "read-only"):
            m.parse_readiness(self.owner, m.EXPECTED_BIT_SHA)

    def test_readonly_probe_mock_does_not_approve_programming(self):
        out = m.parse_capture(self.mock_stdout(), 0)
        self.assertEqual(out["status"],
                         "STOCK_BOARD_READONLY_CAPTURE_COMPLETE_HUMAN_REVIEW_REQUIRED")
        self.assertFalse(out["hardware_programming_authorized"])
        self.assertFalse(out["stock_boot_verified"])

    def test_any_single_readonly_probe_error_is_rejected(self):
        with self.assertRaisesRegex(m.BaselineRejected, "installed_apps.*3"):
            m.parse_capture(self.mock_stdout(bad_rc_label="installed_apps"), 0)

    def test_only_narrow_readonly_sudo_is_allowed(self):
        import unittest.mock
        original = m.BOARD_SH
        with tempfile.TemporaryDirectory() as dirname:
            bad = Path(dirname) / "bad.sh"
            body = original.read_text()
            for changed in ("sudo -n xmutil loadapp anything",
                            "sudo -n sh -c 'xmutil listapps'",
                            "sudo -n xmutil listapps\\nsudo -n xmutil listapps"):
                bad.write_text(body.replace("sudo -n xmutil listapps", changed))
                with unittest.mock.patch.object(m, "BOARD_SH", bad):
                    with self.assertRaises(m.BaselineRejected):
                        m.check_script()

    def test_wrong_exit_or_missing_boundary_rejected(self):
        with self.assertRaisesRegex(m.BaselineRejected, "incomplete"):
            m.parse_capture(self.mock_stdout(), 255)
        with self.assertRaisesRegex(m.BaselineRejected, "boundary"):
            m.parse_capture(self.mock_stdout().replace(
                b"STOCK_READONLY_END_NO_PL_OR_KERNEL_CHANGES",
                b"INCORRECT_TERMINATOR"), 0)

    def test_duplicate_probe_or_malformed_rc_rejected(self):
        payload = self.mock_stdout()
        payload = payload.replace(
            b"M08_D3_2_PROBE_END|sensors|rc=0",
            b"M08_D3_2_PROBE_END|sensors|rc=0\nM08_D3_2_PROBE_END|sensors|rc=0")
        with self.assertRaisesRegex(m.BaselineRejected, "duplicate"):
            m.parse_capture(payload, 0)

    def test_mock_pc_capture_creates_new_hash_receipt_no_hardware_claim(self):
        self.patch_candidate()
        result = m.capture(self.args, subprocess_runner=self.stub_runner)
        self.assertEqual(result["status"],
                         "STOCK_BOARD_READONLY_CAPTURE_COMPLETE_HUMAN_REVIEW_REQUIRED")
        self.assertFalse(result["board_programmed"])
        self.assertTrue(result["no_bitstream_copied_to_board"])
        evidence = Path(result["new_pc_evidence_dir"])
        self.assertNotEqual(evidence, self.candidate)
        self.assertTrue((evidence/"99_evidence_sha256.txt").is_file())
        self.assertEqual(json.loads((evidence/"06_readonly_review.json").read_text())
                         ["hardware_programming_authorized"], False)

    def test_mock_incomplete_ssh_capture_preserved_but_refused(self):
        self.patch_candidate()
        def failure(cmd, **kwargs):
            return CompletedProcess(cmd, 255, b"", b"SSH failure")
        result = m.capture(self.args, subprocess_runner=failure)
        self.assertEqual(result["status"], "STOCK_BOARD_READONLY_CAPTURE_INCOMPLETE_STOP")
        self.assertFalse(result["board_programmed"])
        self.assertTrue((Path(result["new_pc_evidence_dir"])/"99_evidence_sha256.txt").exists())

    def test_wrong_target_rejected_before_ssh(self):
        self.patch_candidate()
        self.args.target = "unknown@192.0.2.25"
        with self.assertRaisesRegex(m.BaselineRejected, "target"):
            m.capture(self.args, subprocess_runner=self.stub_runner)

    def test_original_candidate_auditor_required_before_capture(self):
        with self.assertRaisesRegex(m.BaselineRejected, "bitgen"):
            m.candidate_audit(self.candidate)

    def test_original_script_and_pc_wrapper_no_deployment_actions(self):
        active_board = "\n".join(
            ln for ln in m.BOARD_SH.read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#"))
        for forbidden in (
            "program_hw_devices(", "xmutil loadapp", "xmutil unloadapp",
            "write_bitstream(", "fpgautil -b", "fpga_manager/fpga0/firmware",
        ):
            self.assertNotIn(forbidden, active_board)


if __name__ == "__main__":
    unittest.main()
