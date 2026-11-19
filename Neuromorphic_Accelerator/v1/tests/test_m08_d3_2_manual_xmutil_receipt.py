"""M08 D3.2 manual sudo xmutil evidence supplement, offline synthetic tests only."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/m08_d3_2_manual_xmutil_receipt.py"
sp = importlib.util.spec_from_file_location("m08_d3_2_manual_xmutil_synthetic", SOURCE)
assert sp and sp.loader
m = importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)

MANUAL = b"""[sudo] password for ubuntu:
                   Accelerator  Accel_type                    Base    Pid   Base_type  #slots(RPU+PL+AIE)    slot->handle
    m08-v1-fan-page-uio-review     PL_FLATm08-v1-fan-page-uio-review  id_ok     PL_FLAT (0+0+0)              -1
              k24-starter-kits    XRT_FLAT        k24-starter-kits  id_ok    XRT_FLAT             (0+0+0)              -1
              k26-starter-kits    XRT_FLAT        k26-starter-kits  id_ok    XRT_FLAT             (0+0+0)           0->0,
Connection to 10.42.0.135 closed.
"""


class ManualXmutilTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.dir = Path(t.name)
        self.original = self.dir / "original"
        self.original.mkdir()
        self.manual = self.dir / "manual_xmutil.txt"
        self.manual.write_bytes(MANUAL)
        self.mock_original()

    def mock_original(self):
        original_stdout = (
            "M08_D3_2_STOCK_READONLY_BEGIN\n"
            "M08_D3_2_PROBE_BEGIN|board_identity\n"
            "MODEL=ZynqMP KV260 revB\n"
            "M08_D3_2_PROBE_END|board_identity|rc=0\n"
            "M08_D3_2_PROBE_BEGIN|stock_pl_manager\n"
            "FPGA_STATE=operating\nDFX_SERVICE=active\nFAN_SERVICE=active\n"
            "M08_D3_2_PROBE_END|stock_pl_manager|rc=0\n"
            "M08_D3_2_PROBE_BEGIN|installed_apps\n"
            "xmutil should be called with root privileges. Please try again using 'sudo'.\n"
            "M08_D3_2_PROBE_END|installed_apps|rc=1\n"
            "M08_D3_2_PROBE_BEGIN|stock_firmware_files\n"
            +m.EXPECTED_STOCK_BIT_SHA+"\n"+m.EXPECTED_STOCK_DTBO_SHA+"\n"
            "M08_D3_2_PROBE_END|stock_firmware_files|rc=0\n"
            "M08_D3_2_PROBE_BEGIN|sensors\n"
            "M08_D3_2_PROBE_END|sensors|rc=0\n"
            "M08_D3_2_PROBE_BEGIN|overlay_and_uio_names\n"
            "ACTIVE_OVERLAY=/sys/kernel/config/device-tree/overlays/k26-starter-kits_image_1\n"
            "M08_D3_2_PROBE_END|overlay_and_uio_names|rc=0\n"
            "M08_D3_2_STOCK_READONLY_END_NO_PL_OR_KERNEL_CHANGES\n")
        texts = {
            "00_stock_board_readonly.sh": "mock source\n",
            "01_inputs.json": json.dumps({
                "candidate_sha256": m.EXPECTED_PASSIVE_SHA,
                "physical_programming_authorized": False,
                "original_sha_99_98_96_verified": True,
            })+"\n",
            "02_manual_operator_record.json": "{}\n",
            "03_board_stdout.log": original_stdout,
            "04_board_stderr.log": "\n",
            "05_ssh_exit_status.txt": "exit_status=0\n",
            "06_readonly_review.json": json.dumps({
                "status": "STOCK_BOARD_READONLY_CAPTURE_INCOMPLETE_STOP",
                "ssh_exit_status": 0, "hardware_programming_authorized": False,
            })+"\n",
        }
        for name, content in texts.items():
            (self.original/name).write_text(content)
        self.update_receipt()

    def update_receipt(self):
        self.original.joinpath("99_evidence_sha256.txt").write_text(
            "\n".join(sha256((self.original/name).read_bytes()).hexdigest()+"  "+name
                      for name in m.ORIGINAL_FILES)+"\n"
        )

    def test_manual_realistic_owner_inventory(self):
        result = m.audit_manual_xmutil(MANUAL, 0)
        self.assertEqual(result["operator_observed_active_slot"], "0->0")
        self.assertEqual(result["operator_observed_prior_m08_slot"], "-1")

    def test_original_five_of_six_review(self):
        result = m.audit_original(self.original)
        self.assertEqual(result["original_probe_rc"]["installed_apps"], 1)
        self.assertEqual(result["original_probe_rc"]["stock_pl_manager"], 0)

    def test_new_evidence_is_pc_only_preserves_original(self):
        old = (self.original / "99_evidence_sha256.txt").read_bytes()
        data = m.create_receipt(self.original, self.manual, 0, self.dir)
        new = Path(data["evidence_dir"])
        self.assertEqual(data["status"],
                         "STOCK_READONLY_FIVE_PROBES_PLUS_MANUAL_XMUTIL_REVIEW_ONLY")
        self.assertEqual((self.original/"99_evidence_sha256.txt").read_bytes(), old)
        self.assertFalse(data["hardware_programming_authorized"])
        review = json.loads((new/"01_review.json").read_text())
        self.assertFalse(review["automatic_six_probe_baseline_accepted"])
        self.assertFalse(review["hardware_programming_authorized"])
        self.assertFalse(review["stock_boot_or_rollback_independently_proven"])
        lines = (new/"99_evidence_sha256.txt").read_text().splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            sha, path = line.split("  ", 1)
            self.assertEqual(sha, sha256((new/path).read_bytes()).hexdigest())

    def test_original_modified_bytes_rejected(self):
        self.original.joinpath("03_board_stdout.log").write_text("TAMPER\n")
        with self.assertRaisesRegex(m.ManualReviewRejected, "hash mismatch"):
            m.audit_original(self.original)

    def test_nonzero_manual_ssh_exit_rejected(self):
        with self.assertRaisesRegex(m.ManualReviewRejected, "not 0"):
            m.audit_manual_xmutil(MANUAL, 255)

    def test_manual_stock_inactive_rejected(self):
        with self.assertRaisesRegex(m.ManualReviewRejected, "not active"):
            m.audit_manual_xmutil(MANUAL.replace(b"0->0,", b"-1  "), 0)

    def test_manual_historical_m08_active_rejected(self):
        bad = MANUAL.replace(b"(0+0+0)              -1", b"(0+0+0)              0->0,", 1)
        with self.assertRaisesRegex(m.ManualReviewRejected, "not confirmed inactive"):
            m.audit_manual_xmutil(bad, 0)

    def test_manual_two_active_rejected(self):
        bad = MANUAL.replace(b"PL_FLAT (0+0+0)              -1",
                             b"PL_FLAT (0+0+0)              0->1,")
        with self.assertRaises(m.ManualReviewRejected):
            m.audit_manual_xmutil(bad, 0)

    def test_manual_empty_header_rejected(self):
        with self.assertRaisesRegex(m.ManualReviewRejected, "header"):
            m.audit_manual_xmutil(MANUAL.replace(b"slot->handle", b"deleted"), 0)

    def test_wrong_new_bit_hash_rejected(self):
        i = self.original/"01_inputs.json"
        i.write_text(i.read_text().replace(m.EXPECTED_PASSIVE_SHA, "1"*64))
        self.update_receipt()
        with self.assertRaisesRegex(m.ManualReviewRejected, "candidate pin"):
            m.audit_original(self.original)

    def test_original_other_failed_probe_rejected(self):
        i = self.original/"03_board_stdout.log"
        i.write_text(i.read_text().replace(
            "M08_D3_2_PROBE_END|sensors|rc=0",
            "M08_D3_2_PROBE_END|sensors|rc=1"))
        self.update_receipt()
        with self.assertRaisesRegex(m.ManualReviewRejected, "only unprivileged"):
            m.audit_original(self.original)

    def test_original_hardware_claim_rejected(self):
        i = self.original/"06_readonly_review.json"
        i.write_text(i.read_text().replace('"hardware_programming_authorized": false',
                                           '"hardware_programming_authorized": true'))
        self.update_receipt()
        with self.assertRaisesRegex(m.ManualReviewRejected, "nonprogramming"):
            m.audit_original(self.original)

    def test_manual_missing_old_image_rejected(self):
        with self.assertRaisesRegex(m.ManualReviewRejected, "missing stock"):
            m.audit_manual_xmutil(MANUAL.replace(b"m08-v1-fan-page-uio-review",
                                                 b"not-the-original-m08-app"), 0)

    def test_no_direct_board_or_programming_calls_in_reviewer(self):
        s = SOURCE.read_text()
        for forbidden in ("subprocess.run(", "ssh ", "program_hw_devices(",
                          "xmutil loadapp", "xmutil unloadapp", "/dev/uio", "sudo -n"):
            self.assertNotIn(forbidden, s)


if __name__ == "__main__":
    unittest.main()
