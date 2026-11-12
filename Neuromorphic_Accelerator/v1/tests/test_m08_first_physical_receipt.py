"""M08 first physical deployment original evidence audit: all fixtures synthetic."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_verify_first_physical_receipt.py"
spec = importlib.util.spec_from_file_location("m08_first_physical_audit", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_files() -> dict[str, bytes]:
    records = {
        "schema": "m08-kv260-uio-sysfs-discovery-v1",
        "status": "UIO_SYSFS_METADATA_INSPECTED_NO_MMIO",
        "expected": "present", "register_readback": "NOT_PERFORMED",
        "driver_behavior": "NOT_VERIFIED",
        "m08_bindings": {"m08-identity": "uio4", "m08-page": "uio5"},
        "existing_devices": [
            {"name": "m08-identity", "uio": "uio4",
             "maps": [{"map_index": 0, "physical_base": "0x00000000a0000000", "bytes": 4096}]},
            {"name": "m08-page", "uio": "uio5",
             "maps": [{"map_index": 0, "physical_base": "0x00000000a0001000", "bytes": 4096}]},
        ],
    }
    iomem = "".join(f"{0xff000000+i*0x10000:08x}-{0xff000fff+i*0x10000:08x} : device\n"
                    for i in range(20))
    log = (
        "STAGE_A_PASS_M08_REGISTERED_STOCK_STILL_RUNNING\n"
        "sudo cat /proc/iomem\n" + iomem +
        "Confirm independent fan is spinning\n"
        "remove from slot 0 returns: 0 (Ok)\n"
        "m08-v1-fan-page-uio-review: Loaded with slot_handle 0\n"
        "operating\n"
        "k26-starter-kits  XRT_FLAT  -1\n"
        "m08-v1-fan-page-uio-review  PL_FLAT  0->0,\n"
        "active\nactive\n"
        "/sys/class/hwmon/hwmon0/temp1_input=37085\n"
        "/sys/class/hwmon/hwmon0/temp2_input=34194\n"
        "/sys/class/hwmon/hwmon0/temp3_input=32718\n"
        "ACTIVE_OVERLAY=/sys/kernel/config/device-tree/overlays/"
        "m08-v1-fan-page-uio-review_image_1\n"
    )
    files = {
        "00_context.txt": (mod.ORIGINAL_CONTEXT + "\n").encode(),
        "01_operator_ssh.log": log.encode(),
        "02_uio_sysfs_stdout.json": (json.dumps(records) + "\n").encode(),
        "03_uio_sysfs_stderr.log": b"",
        "04_uio_exit.txt": b"exit_status=0\n",
    }
    files["99_evidence_sha256.txt"] = "".join(
        f"{sha256(files[name]).hexdigest()}  {name}\n"
        for name in sorted(mod.EXPECTED_FILES)).encode()
    return files


def archive_at(where: Path, files: dict[str, bytes], extra=None) -> Path:
    with tarfile.open(where, "w:gz") as tar:
        for name, data in files.items():
            member = tarfile.TarInfo("./" + name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
        if extra is not None:
            tar.addfile(extra, io.BytesIO(b"\x00" * extra.size) if extra.isfile() else None)
    return where


class FirstPhysicalReceiptTests(unittest.TestCase):
    def test_synthetic_manager_and_uio_evidence_accepted_narrowly(self):
        with tempfile.TemporaryDirectory() as d:
            result = mod.review(archive_at(Path(d) / "owner.tar.gz", synthetic_files()))
        self.assertEqual(result["ledger_covered_files_verified"], 5)
        self.assertEqual(result["status"], "FIRST_PL_IMAGE_DEPLOYMENT_METADATA_ACCEPTED_NOT_PS_AXI")
        self.assertEqual(result["m08_bindings"], {"m08-identity": "uio4", "m08-page": "uio5"})
        self.assertTrue(result["m08_load_reported_success"])
        self.assertFalse(result["register_mmio_read_performed"])
        self.assertFalse(result["rollback_to_stock_physically_exercised"])
        self.assertFalse(result["neural_inference_verified"])
        self.assertFalse(result["cooling_during_reconfiguration_instrumented"])

    def test_sha_tampering_and_incomplete_ledger_fail(self):
        with tempfile.TemporaryDirectory() as d:
            files = synthetic_files()
            files["01_operator_ssh.log"] += b"TAMPER"
            with self.assertRaisesRegex(mod.EvidenceRejected, "SHA mismatch"):
                mod.review(archive_at(Path(d) / "bad1.tar.gz", files))
            files = synthetic_files()
            files["99_evidence_sha256.txt"] = files["99_evidence_sha256.txt"].replace(
                b"  03_uio_sysfs_stderr.log\n", b"  03_uio_sysfs_stderr.log_BAD\n")
            with self.assertRaises(mod.EvidenceRejected):
                mod.review(archive_at(Path(d) / "bad2.tar.gz", files))

    def test_false_success_requires_genuine_signals_not_hashes_only(self):
        with tempfile.TemporaryDirectory() as d:
            files = synthetic_files()
            files["01_operator_ssh.log"] = files["01_operator_ssh.log"].replace(
                b"Loaded with slot_handle 0", b"Load FAILED")
            files["99_evidence_sha256.txt"] = b"".join(
                (f"{sha256(files[n]).hexdigest()}  {n}\n").encode()
                for n in sorted(mod.EXPECTED_FILES))
            with self.assertRaisesRegex(mod.EvidenceRejected, "load success"):
                mod.review(archive_at(Path(d) / "bad3.tar.gz", files))

    def test_wrong_or_unread_uio_rejected(self):
        good = json.loads(synthetic_files()["02_uio_sysfs_stdout.json"])
        for change in ("wrong_address", "missing_page", "claimed_readback", "wrong_size"):
            data = json.loads(json.dumps(good))
            if change == "wrong_address":
                data["existing_devices"][1]["maps"][0]["physical_base"] = "0x00000000a0002000"
            elif change == "missing_page":
                del data["m08_bindings"]["m08-page"]
            elif change == "claimed_readback":
                data["register_readback"] = "PERFORMED"
            else:
                data["existing_devices"][0]["maps"][0]["bytes"] = 8192
            with self.subTest(change=change), self.assertRaises(mod.EvidenceRejected):
                mod.verify_uio(data)

    def test_malicious_extra_file_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaisesRegex(mod.EvidenceRejected, "unexpected archive"):
                mod.review(archive_at(root / "evil.tar.gz", synthetic_files(),
                                      tarfile.TarInfo("../../escape")))
            link = tarfile.TarInfo("./01_operator_ssh.log")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/shadow"
            with self.assertRaises(mod.EvidenceRejected):
                mod.review(archive_at(root / "link.tar.gz", synthetic_files(), link))

    def test_bad_cli_and_no_board_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, str(SCRIPT),
                                "--archive", str(Path(d) / "not_uploaded.tar.gz")],
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 2)
        self.assertIn("M08_FIRST_PHYSICAL_RECEIPT_REJECTED", p.stderr)
        source = SCRIPT.read_text()
        for banned in ("os.open(", "mmap.mmap(", "xmutil unloadapp", "xmutil loadapp",
                       "subprocess.run(", "ssh -T", "fpga_manager/fpga"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main()
