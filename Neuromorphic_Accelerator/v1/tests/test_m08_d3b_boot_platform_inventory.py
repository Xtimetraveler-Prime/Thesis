"""D3.2B.1 synthetic ONLY: bounded offline owner-PC provenance inventory."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d3b_boot_platform_inventory.py"
spec = importlib.util.spec_from_file_location("m08_d3b_b1_inventory", SCRIPT)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TestD3B1Inventory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "owner" / "evidence" / "m08"
        self.root.mkdir(parents=True)
        self.output = self.root / "m08_d3b_b1_inventory_TEST"
        self.output.mkdir()

    def run_scan(self, **kwargs):
        return m.inventory([("synthetic_owner", self.root)],
                           exclude_dir=self.output, **kwargs)

    def test_synthetic_inventory_sha_classes_provenance_and_receipt(self):
        (self.root / "original.xsa").write_bytes(b"synthetic XSA, NOT native Vivado")
        (self.root / "psu_init.c").write_text("/* synthetic, not booted */\n")
        (self.root / "BOOT.BIN").write_bytes(b"synthetic binary")
        (self.root / "design.dtb").write_bytes(b"synthetic dtb not applied")
        (self.root / "boot_manifest.json").write_text("{}")
        (self.root / "fake.xsa.bak").write_bytes(b"false suffix")
        (self.root / "psu_init.c.orig").write_bytes(b"false suffix")
        obj = self.run_scan()
        records = {Path(x["path"]).name: x for x in obj["candidates"]}
        self.assertEqual(set(records), {"original.xsa", "psu_init.c", "BOOT.BIN",
                                        "design.dtb", "boot_manifest.json"})
        self.assertEqual(records["original.xsa"]["sha256"],
                         sha256(b"synthetic XSA, NOT native Vivado").hexdigest())
        self.assertEqual(records["BOOT.BIN"]["hash_policy"],
                         "BOOT_PACKAGE_METADATA_ONLY_NO_BYTES_READ")
        self.assertIsNone(records["BOOT.BIN"]["sha256"])
        self.assertEqual(obj["pinned_originals"]["k26_starter_kits.dtbo"]["status"],
                         "NOT_FOUND_IN_BOUNDED_SCAN_UNKNOWN")
        self.assertTrue(obj["original_m08_image_quarantined"])
        self.assertFalse(obj["hardware_mmio_authorized"])
        self.assertFalse(obj["atb4_hardware_proven"])
        self.assertFalse(obj["physical_programming_authorized"])
        self.assertFalse(obj["proceed_to_d3b5_native_hpm0"])
        result, receipt = m.write_receipt(self.output, obj)
        self.assertEqual(json.loads(result.read_text()), obj)
        self.assertEqual(receipt.read_text(),
                         sha256(result.read_bytes()).hexdigest()
                         + "  00_boot_platform_inventory.json\n")
        with self.assertRaisesRegex(m.InventoryRejected, "EMPTY"):
            m.write_receipt(self.output, obj)

    def test_pinned_original_dtb_mismatch_rejected_no_false_authentication(self):
        (self.root / "k26_starter_kits.dtbo").write_bytes(b"impostor")
        with self.assertRaisesRegex(m.InventoryRejected, "pinned original SHA256 mismatch"):
            self.run_scan()

    def test_symlinked_files_and_directories_never_followed(self):
        source = self.root / "original.xsa"
        source.write_bytes(b"candidate")
        (self.root / "symlink.xsa").symlink_to(source)
        nested = self.root / "nested"
        nested.mkdir()
        (nested / "psu_init.tcl").write_text("fake")
        (self.root / "link_dir").symlink_to(nested, target_is_directory=True)
        report = self.run_scan()
        paths = {x["relative_path"] for x in report["candidates"]}
        self.assertEqual(paths, {"original.xsa", "nested/psu_init.tcl"})
        self.assertEqual(report["coverage"]["symlinks_ignored"], 2)
        with self.assertRaisesRegex(m.InventoryRejected, "symlinked path component"):
            m.inventory([("bad", self.root / "link_dir")])
        bad_out = self.root / "bad_output"
        bad_out.symlink_to(self.output, target_is_directory=True)
        with self.assertRaisesRegex(m.InventoryRejected, "symlinked"):
            m.write_receipt(bad_out, report)

    def test_reject_broad_and_missing_roots(self):
        for path in (Path("/"), Path("/tmp"), Path.home()):
            with self.assertRaisesRegex(m.InventoryRejected, "overbroad"):
                m.validate_root(path)
        with self.assertRaisesRegex(m.InventoryRejected, "missing"):
            m.validate_root(self.root / "not-here")
        report = m.inventory([("owner_m08_evidence", self.root / "not-here")])
        self.assertEqual(len(report["optional_roots_missing"]), 1)
        self.assertFalse(report["linux_clock_afi_proven"])

    def test_entry_limit_fails_closed_and_depth_is_reported(self):
        for i in range(5):
            (self.root / ("boot_%02d.log" % i)).write_text("mock")
        with self.assertRaisesRegex(m.InventoryRejected, "entry limit"):
            self.run_scan(max_entries=3)
        nested = self.root / "d1" / "d2"
        nested.mkdir(parents=True)
        (nested / "actual.xsa").write_bytes(b"mock")
        limited = self.run_scan(max_depth=1)
        self.assertGreater(limited["coverage"]["depth_pruned"], 0)
        self.assertNotIn("actual.xsa", {Path(x["path"]).name
                                       for x in limited["candidates"]})

    def test_oversize_candidate_is_not_falsely_hashed_or_accepted(self):
        (self.root / "big.xsa").write_bytes(b"Z" * 2048)
        obj = self.run_scan(max_hash_bytes=1024)
        record = next(x for x in obj["candidates"]
                      if x["relative_path"] == "big.xsa")
        self.assertIsNone(record["sha256"])
        self.assertEqual(record["hash_policy"], "SKIPPED_SIZE_LIMIT")
        self.assertEqual(obj["coverage"]["size_limited_hashes"], 1)
        with self.assertRaisesRegex(m.InventoryRejected, "unbounded"):
            self.run_scan(max_entries=50001)

    def test_extra_scan_root_cannot_read_outside_owner_home(self):
        with self.assertRaisesRegex(m.InventoryRejected, "beneath owner PC HOME"):
            m.validate_owner_extra(self.root)

    def test_output_must_not_touch_existing_evidence(self):
        existing = self.root / "m08_d3a_original.log"
        existing.write_text("immutable original artifact")
        obj = self.run_scan()
        m.write_receipt(self.output, obj)
        self.assertEqual(existing.read_text(), "immutable original artifact")
        self.assertEqual(set(x.name for x in self.output.iterdir()),
                         {"00_boot_platform_inventory.json", "99_evidence_sha256.txt"})

    def test_static_no_board_or_binary_unpack_execution(self):
        text = SCRIPT.read_text()
        for forbidden in (
            "subprocess", "os.system", "os.popen", "zipfile", "tarfile",
            "program_hw_devices", "write_bitstream", "xmutil",
            "/dev/mem", "/dev/uio", "ssh ", "dtc ", "vivado -",
        ):
            self.assertNotIn(forbidden, text)
        self.assertIn("original_m08_image_quarantined", text)
        self.assertIn("hardware_mmio_authorized", text)
        self.assertIn("ATB4_boot_enable_response_timeout_clock", text)


if __name__ == "__main__":
    unittest.main()
