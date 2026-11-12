"""M08 D2 local-only DTBO discovery and guarded decompilation regression.

Synthetic fake binary DTBOs and fake dtc, NOT original KV260 or native dtc.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest import mock
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d2_locate_and_decompile_owner_dtbos.py"
spec = importlib.util.spec_from_file_location("m08_d2_dtbo_locator", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OwnerPCD2DTBOLocatorTests(unittest.TestCase):
    def setUp(self):
        self.original_expected = m.EXPECTED
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "original"
        self.src.mkdir()
        self.out = self.root / "evidence"
        self.out.mkdir()
        self.bytes = {"stock": b"FAKE stock DTBO " * 24,
                      "m08": b"FAKE M08 DTBO " * 25}
        m.EXPECTED = {
            key: (self.original_expected[key][0], sha256(data).hexdigest())
            for key, data in self.bytes.items()
        }
        self.addCleanup(lambda: setattr(m, "EXPECTED", self.original_expected))

    def stage_fake_originals(self):
        for key, payload in self.bytes.items():
            (self.src / m.EXPECTED[key][0]).write_bytes(payload)

    def test_exact_original_filenames_and_production_shas_pinned(self):
        self.assertEqual(self.original_expected["stock"][1],
                         "1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1")
        self.assertEqual(self.original_expected["m08"][1],
                         "2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed")

    def test_locates_only_exact_sha_matches_with_no_hardware(self):
        self.stage_fake_originals()
        result = m.locate([self.root])
        self.assertTrue(result["all_originals_located"])
        self.assertTrue(result["original_m08_quarantine_active"])
        self.assertFalse(result["physical_hardware_accessed"])
        for key in m.EXPECTED:
            self.assertEqual(len(result["matches"][key]), 1)
            self.assertTrue(result["matches"][key][0]["matches_original_sha256"])

    def test_mutated_original_is_reported_but_never_accepted(self):
        self.stage_fake_originals()
        (self.src / m.EXPECTED["m08"][0]).write_bytes(b"new or mutated M08 dtbo")
        result = m.locate([self.root])
        self.assertFalse(result["all_originals_located"])
        self.assertFalse(result["matches"]["m08"][0]["matches_original_sha256"])
        with self.assertRaisesRegex(m.OfflineReject, "exactly one"):
            m.prepare(result, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_no_stock_on_pc_is_honestly_reported(self):
        (self.src / m.EXPECTED["m08"][0]).write_bytes(self.bytes["m08"])
        result = m.locate([self.root])
        self.assertFalse(result["all_originals_located"])
        self.assertEqual(result["matches"]["stock"], [])
        self.assertTrue(result["matches"]["m08"][0]["matches_original_sha256"])

    def test_symlinked_dtbo_or_search_root_rejected(self):
        self.stage_fake_originals()
        stock = self.src / m.EXPECTED["stock"][0]
        stock.rename(self.src / "original.bin")
        stock.symlink_to(self.src / "original.bin")
        result = m.locate([self.root])
        self.assertEqual(result["matches"]["stock"], [])
        rootlink = self.root / "rootlink"
        rootlink.symlink_to(self.src, target_is_directory=True)
        with self.assertRaisesRegex(m.OfflineReject, "symlinked"):
            m.locate([rootlink])

    def test_preparation_with_mock_dtc_new_folder_receipt_originals_unchanged(self):
        self.stage_fake_originals()
        result = m.locate([self.root])
        def fake_run(argv, **kwargs):
            self.assertEqual(argv[:4], ["dtc", "-I", "dtb", "-O"])
            self.assertEqual(argv[4], "dts")
            target = Path(argv[argv.index("-o") + 1])
            target.write_text("/dts-v1/;\n// synthetic decompiled node\n" * 6)
            class Proc:
                returncode = 0
                stderr = "Warning (synthetic): review separately\n"
            return Proc()
        with mock.patch.object(m.shutil, "which", return_value="/usr/bin/dtc"), \
             mock.patch.object(m.subprocess, "run", side_effect=fake_run):
            folder, ok = m.prepare(result, self.out)
        self.assertTrue(ok)
        self.assertEqual(folder.parent, self.out)
        self.assertEqual(len(list(self.out.iterdir())), 1)
        self.assertTrue((folder / "11_stock.dts").is_file())
        self.assertTrue((folder / "12_m08.dts").is_file())
        receipt = (folder / "99_evidence_sha256.txt").read_text()
        self.assertIn("00_review.json", receipt)
        report = json.loads((folder / "00_review.json").read_text())
        self.assertTrue(report["originals_unchanged"])
        self.assertFalse(report["runtime_clock_reset_hpm0_afi_or_atb_verified"])
        self.assertFalse(report["hardware_retry_authorized"])
        for key, payload in self.bytes.items():
            self.assertEqual((self.src / m.EXPECTED[key][0]).read_bytes(), payload)

    def test_m08_only_decompile_does_not_require_or_imply_stock_dtbo(self):
        (self.src / m.EXPECTED["m08"][0]).write_bytes(self.bytes["m08"])
        result = m.locate([self.root])
        self.assertFalse(result["all_originals_located"])
        def fake_dtc(argv, **kwargs):
            target = Path(argv[argv.index("-o") + 1])
            target.write_text("/dts-v1/;\\n" * 20)
            class Result:
                returncode = 0
                stderr = "unresolved overlay fixups (synthetic)\\n"
            return Result()
        with mock.patch.object(m.shutil, "which", return_value="/usr/bin/dtc"), \
             mock.patch.object(m.subprocess, "run", side_effect=fake_dtc):
            folder, success = m.prepare(result, self.out, m08_only=True)
        self.assertTrue(success)
        self.assertFalse((folder / "11_stock.dts").exists())
        self.assertTrue((folder / "12_m08.dts").exists())
        review = json.loads((folder / "00_review.json").read_text())
        self.assertFalse(review["stock_dtbo_compared"])
        self.assertEqual(review["status"],
                         "ORIGINAL_M08_DTS_COPY_CREATED_STOCK_ABSENT_NO_BOARD")
        self.assertFalse(review["runtime_clock_reset_hpm0_afi_or_atb_verified"])
        self.assertFalse(review["hardware_retry_authorized"])

    def test_duplicate_sha_verified_originals_not_auto_selected(self):
        self.stage_fake_originals()
        nested = self.root / "duplicate"
        nested.mkdir()
        for key, data in self.bytes.items():
            (nested / m.EXPECTED[key][0]).write_bytes(data)
        result = m.locate([self.root])
        self.assertTrue(result["all_originals_located"])
        with mock.patch.object(m.shutil, "which", return_value="/usr/bin/dtc"):
            with self.assertRaisesRegex(m.OfflineReject, "narrow --search-root"):
                m.prepare(result, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_unsafe_on_kv260_fails_closed(self):
        with mock.patch.object(m.platform, "system", return_value="Windows"):
            with self.assertRaisesRegex(m.OfflineReject, "Linux"):
                m.locate([self.src])
        with mock.patch.object(m.platform, "system", return_value="Linux"), \
             mock.patch.object(m.Path, "exists", autospec=True, side_effect=lambda p: (
                 str(p) == "/proc/device-tree/model")):
            # Test logic without touching board: invalid mocked model read safely.
            with mock.patch.object(m.Path, "read_bytes", return_value=b"KV260"):
                with self.assertRaisesRegex(m.OfflineReject, "prohibited on KV260"):
                    m.locate([self.src])

    def test_no_network_or_fpga_device_commands(self):
        source = SCRIPT.read_text()
        for bad in ("/dev/uio", "/dev/mem", "program_hw_devices",
                    "write_bitstream", "fpga_manager", "xmutil", "JTAG session",
                    "subprocess.Popen", "shell=True", "ssh ", "devmem "):
            self.assertNotIn(bad, source)


if __name__ == "__main__":
    unittest.main()
