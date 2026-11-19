"""M08 D3.2 live physical stock-only probe: no-board synthetic tests."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
from subprocess import CompletedProcess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/m08_d3_2_stock_live_readonly_pc.py"
spec = importlib.util.spec_from_file_location("stock_live", SOURCE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def sample(*, temp=31500, stock=True, fan=True):
    rows = [
        "M08_D3_2_STOCK_LIVE_BEGIN",
        "BOARD_MODEL=ZynqMP KV260 revB ",
        "FPGA_STATE=operating",
        "DFX_SERVICE=active",
        "FAN_SERVICE=active" if fan else "FAN_SERVICE=inactive",
        "ACTIVE_OVERLAY=/sys/kernel/config/device-tree/overlays/" +
            ("k26-starter-kits_image_1" if stock else "m08-test_image_1"),
        f"TEMP=/sys/class/hwmon/hwmon0/temp1_input:{temp}",
        "M08_D3_2_STOCK_LIVE_END",
    ]
    # Exact model match is deliberately trimmed below in script's expected line.
    rows[1] = rows[1].rstrip()
    return ("\n".join(rows)+"\n").encode()


class LiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.manual = self.root / "manual"
        self.manual.mkdir()
        report = {
            "status": m.MANUAL_STATUS,
            "manual_xmutil_receipt": {
                "operator_observed_stock_app": "k26-starter-kits",
                "operator_observed_active_slot": "0->0",
                "operator_observed_prior_m08_slot": "-1",
            },
            "previous_stock_readonly_evidence": {
                "new_passive_bit_sha256": m.PASSIVE_SHA,
                "stock_bit_sha256": m.STOCK_SHA,
            },
            "hardware_programming_authorized": False,
            "new_passive_bitstream_loaded": False,
            "stock_boot_or_rollback_independently_proven": False,
        }
        files = {
            "00_manual_xmutil_stdout.txt": b"synthetic original\n",
            "01_review.json": (json.dumps(report)+"\n").encode(),
        }
        for name, value in files.items():
            (self.manual/name).write_bytes(value)
        (self.manual/"99_evidence_sha256.txt").write_text(
            "".join(sha256(value).hexdigest()+"  "+name+"\n" for name, value in files.items()))

    def test_source_has_no_mutation_or_root(self):
        m.source_gate()
        for cmd in ("sudo ", "xmutil", "program_hw_devices", "fpgautil", "/dev/mem",
                    "reboot", "poweroff", "systemctl restart"):
            self.assertNotIn(cmd, m.SCRIPT)

    def test_parse_observation(self):
        out = m.parse_observation(sample(), 0)
        self.assertEqual(out["temperatures_millideg_c"], [31500])
        self.assertFalse(out["hardware_programming_authorized"])

    def test_refuse_unexpected_overlay(self):
        with self.assertRaisesRegex(m.Rejected, "stock live"):
            m.parse_observation(sample(stock=False), 0)

    def test_refuse_fan_control_down(self):
        with self.assertRaisesRegex(m.Rejected, "FAN_SERVICE"):
            m.parse_observation(sample(fan=False), 0)

    def test_refuse_overtemperature(self):
        with self.assertRaisesRegex(m.Rejected, "out-of-range"):
            m.parse_observation(sample(temp=90000), 0)

    def test_refuse_failed_ssh(self):
        with self.assertRaisesRegex(m.Rejected, "SSH"):
            m.parse_observation(sample(), 255)

    def test_manual_sha_tamper_rejected(self):
        (self.manual/"01_review.json").write_text("{}\n")
        with self.assertRaisesRegex(m.Rejected, "SHA receipt mismatch"):
            m.review_manual_receipt(self.manual)

    def test_manual_release_claim_rejected(self):
        data = json.loads((self.manual/"01_review.json").read_text())
        data["hardware_programming_authorized"] = True
        value = (json.dumps(data)+"\n").encode()
        (self.manual/"01_review.json").write_bytes(value)
        items = ("00_manual_xmutil_stdout.txt", "01_review.json")
        (self.manual/"99_evidence_sha256.txt").write_text(
            "".join(sha256((self.manual/f).read_bytes()).hexdigest()+"  "+f+"\n"
                    for f in items))
        with self.assertRaisesRegex(m.Rejected, "accepted review-only"):
            m.review_manual_receipt(self.manual)

    def test_mock_capture_three_samples_with_immutable_pc_receipts(self):
        calls = []
        def fake_run(args, **kwargs):
            calls.append(args)
            self.assertEqual(args[-2:], [m.TARGET, "bash -s"])
            self.assertNotIn("sudo", args)
            return CompletedProcess(args, 0, sample(), b"")
        report = m.capture(self.manual, self.root, runner=fake_run)
        self.assertEqual(len(calls), 3)
        self.assertEqual(report["status"], "STOCK_LIVE_READONLY_OBSERVED_NO_RECONFIGURATION")
        output = Path(report["evidence_dir"])
        self.assertNotEqual(output, self.manual)
        self.assertFalse(report["hardware_programming_authorized"])
        review = json.loads((output/"90_review.json").read_text())
        self.assertFalse(review["stock_rollback_proven"])
        for line in (output/"99_evidence_sha256.txt").read_text().splitlines():
            checksum, filename = line.split("  ")
            self.assertEqual(checksum, sha256((output/filename).read_bytes()).hexdigest())

    def test_stop_first_bad_sample(self):
        i = 0
        def fake_run(args, **kwargs):
            nonlocal i
            i += 1
            return CompletedProcess(args, 0, sample(stock=i != 2), b"")
        result = m.capture(self.manual, self.root, runner=fake_run, samples=5)
        self.assertEqual(i, 2)
        self.assertEqual(result["status"], "STOCK_LIVE_READONLY_STOP")

    def test_missing_input_review_rejected(self):
        data = json.loads((self.manual/"01_review.json").read_text())
        data["manual_xmutil_receipt"]["operator_observed_active_slot"] = "-1"
        (self.manual/"01_review.json").write_text(json.dumps(data)+"\n")
        files = ("00_manual_xmutil_stdout.txt", "01_review.json")
        (self.manual/"99_evidence_sha256.txt").write_text(
            "".join(sha256((self.manual/f).read_bytes()).hexdigest()+"  "+f+"\n"
                    for f in files))
        with self.assertRaisesRegex(m.Rejected, "accepted review-only"):
            m.review_manual_receipt(self.manual)


if __name__ == "__main__":
    unittest.main()
