"""Source-only M08.2b.3/.4 physical UIO operator tests. NO BOARD."""
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SCRIPT = ROOT / "scripts/m08_kv260_physical_uio_operator.py"
spec = importlib.util.spec_from_file_location("m08_physical_operator", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestM08PhysicalUIOOperator(unittest.TestCase):
    def test_64_word_pattern_unique_and_valid(self):
        values = mod.page_words()
        self.assertEqual(len(values), 64)
        self.assertEqual(len(set(values)), 64)
        self.assertTrue(all(0 <= v <= 0xFFFFFFFF for v in values))
        self.assertEqual(mod.LOGICAL_ID, 0x4D080201)

    def test_synthetic_file_backed_32bit_mmio_no_byte_write(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "SYNTHETIC_FILE_NOT_UIO.bin"
            path.write_bytes(bytes(4096))
            with mod.Window(str(path), True) as w:
                w.write32(0x100, 0xFEDCBA98)
                self.assertEqual(w.read32(0x100), 0xFEDCBA98)
                w.write32(0x104, 0x01234567)
                with self.assertRaises(mod.StopPhysicalTest):
                    w.write32(0x102, 0)
                with self.assertRaises(mod.StopPhysicalTest):
                    w.write32(4096, 0)
                with self.assertRaises(mod.StopPhysicalTest):
                    w.write32(0x100, -1)
            self.assertEqual(path.read_bytes()[0x100:0x108], bytes.fromhex("98badcfe67452301"))
            with mod.Window(str(path), False) as r:
                self.assertEqual(r.read32(0x104), 0x01234567)
                with self.assertRaises(mod.StopPhysicalTest):
                    r.write32(0x100, 0)

    def test_original_identity_record_sha_and_semantics(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "identity.json"
            original = {
                "schema": "m08-first-physical-identity-read-v1",
                "status": "PHYSICAL_UIO_READ32_IDENTITY_AND_EMPTY_PAGE_MATCHED",
                "identity_words": ["0x4d303831", "0x00010000", "0x00000000", "0x00000000"],
                "page_words": ["0x4d303850", "0x00020002", "0x00000001", "0x00000000"],
                "physical_register_reads_attempted": True,
                "physical_256byte_page_written": False,
            }
            path.write_text(json.dumps(original))
            pinned = sha256(path.read_bytes()).hexdigest()
            self.assertEqual(mod.verify_identity_evidence(path, pinned), original)
            path.write_text(json.dumps({**original, "status": "NOT_A_REAL_READ"}))
            with self.assertRaises(mod.StopPhysicalTest):
                mod.verify_identity_evidence(path, pinned)
            with self.assertRaises(mod.StopPhysicalTest):
                mod.verify_identity_evidence(path, sha256(path.read_bytes()).hexdigest())

    def test_page_uses_first_party_full_64_compare_protocol(self):
        class DummyWindow:
            def __init__(self, node, writable): self.node, self.writable = node, writable
            def __enter__(self): return self
            def __exit__(self, *_): pass
        payload = b"".join(v.to_bytes(4, "little") for v in mod.page_words())
        response = {"words_compared": 64, "bytes_compared": 256,
                    "readback_sha256_little_endian": sha256(payload).hexdigest()}
        with patch.object(mod, "Window", DummyWindow), \
             patch.object(mod, "verify_identity_evidence",
                          return_value={"status": "PHYSICAL_UIO_READ32_IDENTITY_AND_EMPTY_PAGE_MATCHED"}), \
             patch.object(mod, "inspect_identity", return_value=None), \
             patch.object(mod, "stage_and_compare", return_value=response) as protocol:
            result = mod.physical_page(
                {"m08-identity": "/fake/identity", "m08-page": "/fake/page"},
                Path("/fake/identity.json"), "f" * 64)
        args, kwargs = protocol.call_args
        self.assertEqual(args[2], mod.page_words())
        self.assertEqual(args[3], mod.LOGICAL_ID)
        self.assertEqual(kwargs, {"allow_transport_writes": True})
        self.assertEqual(result["transaction"]["words_compared"], 64)
        self.assertFalse(result["axi_rresp_bresp_directly_observed"])
        self.assertFalse(result["dispatch_attempted"])
        self.assertFalse(result["neural_inference_tested"])
        self.assertTrue(result["physical_uio_transport_exercised"])

    def test_page_mismatch_propagates_with_no_false_pass(self):
        class DummyWindow:
            def __init__(self, node, writable): pass
            def __enter__(self): return self
            def __exit__(self, *_): pass
        with patch.object(mod, "Window", DummyWindow), \
             patch.object(mod, "verify_identity_evidence",
                          return_value={"status": "PHYSICAL_UIO_READ32_IDENTITY_AND_EMPTY_PAGE_MATCHED"}), \
             patch.object(mod, "inspect_identity", return_value=None), \
             patch.object(mod, "stage_and_compare", return_value={
                 "words_compared": 64, "bytes_compared": 256,
                 "readback_sha256_little_endian": "0"*64
             }):
            with self.assertRaisesRegex(mod.StopPhysicalTest, "independent expected digest"):
                mod.physical_page({"m08-identity":"fake","m08-page":"fake"},Path("fake"),"f"*64)

    def test_host_cli_denies_nonboard(self):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        p = subprocess.run(
            [sys.executable, str(SCRIPT), "--mode", "identity",
             "--acknowledge-axi-read-risk"], capture_output=True,
            text=True, timeout=10, cwd=ROOT, env=env)
        self.assertEqual(p.returncode, 2)
        self.assertIn("M08_PHYSICAL_UIO_STOP_NO_RETRY", p.stderr)

    def test_source_has_no_reconfiguration_or_compute_ops(self):
        source = SCRIPT.read_text()
        for banned in ("xmutil unloadapp", "xmutil loadapp", "program_hw_devices",
                       "sudo reboot", "mmap.flush()", "shell=True",
                       "Path('/dev/mem')", 'open("/dev/mem"'):
            self.assertNotIn(banned, source)
        self.assertIn("acknowledge-rollback-not-yet-exercised", source)
        self.assertIn("allow_transport_writes=True", source)
        self.assertIn("O_NOFOLLOW", source)
        self.assertIn("mmap.MAP_SHARED", source)
        self.assertIn("c_uint32.from_buffer", source)


if __name__ == "__main__":
    unittest.main()
