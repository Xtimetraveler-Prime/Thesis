"""Offline D3.2 receipt integrity and false boot-provenance negatives."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "scripts/m08_d3b_boot_platform_inventory.py"
REVIEW = ROOT / "scripts/m08_d3b_boot_platform_receipt_review.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inv = load(INVENTORY, "m08_d3b_inv")
reviewer = load(REVIEW, "m08_d3b_receipt")


class OfflineReceiptTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "pc" / "m08" / "originals"
        base.mkdir(parents=True)
        self.base = base
        self.output = base / "m08_d3b_b1_inventory_SYNTHETIC"
        self.output.mkdir()
        (base / "psu_init.c").write_text("/* synthetic, never used at boot */")
        (base / "review" / "m08-v1-fan-page-uio-review.dtbo").parent.mkdir()
        (base / "review" / "m08-v1-fan-page-uio-review.dtbo").write_bytes(b"different mock")
        obj = inv.inventory([("synthetic_pc", base)], exclude_dir=self.output)
        inv.write_receipt(self.output, obj)

    def mutate(self, operation, *, resign: bool = True):
        p = self.output / "00_boot_platform_inventory.json"
        obj = json.loads(p.read_text())
        operation(obj)
        p.write_text(json.dumps(obj, sort_keys=True) + "\n")
        if resign:
            (self.output / "99_evidence_sha256.txt").write_text(
                sha256(p.read_bytes()).hexdigest() + "  00_boot_platform_inventory.json\n")

    def test_authentic_synthetic_receipt_stays_hardware_blocked(self):
        a = reviewer.review(self.output)
        self.assertEqual(a["status"],
                         "OWNER_PC_INVENTORY_RECEIPT_INTEGRITY_ACCEPTED_BOOT_OWNERSHIP_UNKNOWN")
        self.assertFalse(a["has_original_boot_config_evidence"])
        self.assertFalse(a["physical_access_authorized"])
        self.assertEqual(a["candidate_class_counts"]["GENERATED_PS_INIT_SOURCE_UNATTESTED"], 1)
        name = "m08-v1-fan-page-uio-review.dtbo"
        self.assertEqual(a["historical_reference_matches"][name]["same_name_different_bytes"], 1)
        self.assertEqual(a["historical_reference_matches"][name]["sha256_matches"], 0)

    def test_reject_hash_tamper_without_resigning(self):
        self.mutate(lambda x: x.update(status="FAKE_BOOT_VERIFIED"), resign=False)
        with self.assertRaisesRegex(reviewer.ReviewRejected, "SHA256 receipt mismatch"):
            reviewer.review(self.output)

    def test_reject_even_resigned_forged_hardware_approval(self):
        self.mutate(lambda x: x.update(hardware_mmio_authorized=True))
        with self.assertRaisesRegex(reviewer.ReviewRejected, "hardware proof"):
            reviewer.review(self.output)

    def test_reject_resigned_false_original_byte_match(self):
        def lie(x):
            for c in x["candidates"]:
                if c["historical_reference_filename_match"]:
                    c["pinned_original_digest_match"] = True
                    return
            raise AssertionError("fixture missing historical comparison")
        self.mutate(lie)
        with self.assertRaisesRegex(reviewer.ReviewRejected, "filename promoted"):
            reviewer.review(self.output)

    def test_reject_resigned_false_reference_summary(self):
        def lie(x):
            x["pinned_originals"]["m08-v1-fan-page-uio-review.dtbo"][
                "sha256_matching_paths"
            ] = ["/tmp/fake-original.dtbo"]
        self.mutate(lie)
        with self.assertRaisesRegex(reviewer.ReviewRejected, "reference summary"):
            reviewer.review(self.output)

    def test_reject_missing_and_symlink_receipts(self):
        log = self.output / "99_evidence_sha256.txt"
        renamed = self.output / "99_original_receipt.txt"
        log.rename(renamed)
        log.symlink_to(renamed)
        with self.assertRaisesRegex(reviewer.ReviewRejected, "symlinked"):
            reviewer.review(self.output)

    def test_reject_duplicate_candidate(self):
        self.mutate(lambda x: x["candidates"].append(dict(x["candidates"][0])))
        with self.assertRaisesRegex(reviewer.ReviewRejected, "duplicate"):
            reviewer.review(self.output)

    def test_reject_misleading_ps_init_runtime_claim(self):
        self.mutate(lambda x: x["candidates"][0].update(
            ps_runtime_configuration_proven=True))
        with self.assertRaisesRegex(reviewer.ReviewRejected, "runtime/deployment"):
            reviewer.review(self.output)

    def test_static_read_only_never_board_or_binary_inspection(self):
        source = REVIEW.read_text()
        for disallowed in ("subprocess", "os.system", "os.popen",
                           "program_hw_devices", "write_bitstream",
                           "ssh ", "/dev/mem", "/dev/uio", "xmutil",
                           "fpga_manager", "zipfile", "tarfile"):
            self.assertNotIn(disallowed, source)
        self.assertIn("physical_access_authorized", source)
        self.assertIn("original_m08_image_quarantined", source)


if __name__ == "__main__":
    unittest.main()
