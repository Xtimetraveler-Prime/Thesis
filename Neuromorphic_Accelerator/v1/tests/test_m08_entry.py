"""M08.1 independent read-only preflight / no-unowned-DDR source tests."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from neuromorphic_accelerator_v1.m08_entry import (
    ARCHIVES, PhysicalReadiness, archive_inventory, sha_file, verify_dma_window,
)
import m08_capture_readonly as preflight


class M08SourceEntryTests(unittest.TestCase):
    def test_readiness_is_nonclaim_even_when_all_self_reported(self):
        empty=PhysicalReadiness().assess()
        self.assertEqual(empty["status"],"INSUFFICIENT_EXTERNAL_EVIDENCE")
        self.assertEqual(len(empty["missing"]),6)
        self.assertFalse(empty["ready_to_dma"])
        fields={field:"operator-capture-sha256-"+field
                for field in PhysicalReadiness.__dataclass_fields__}
        complete=PhysicalReadiness(**fields).assess()
        self.assertEqual(complete["missing"],[])
        self.assertEqual(complete["status"],"AWAIT_INDEPENDENT_PHYSICAL_AUDIT")
        self.assertFalse(complete["ready_to_dma"])
        for invalid in ("", " ", "bad\nline", 55, True):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                PhysicalReadiness(actual_kv260_identity_evidence=invalid).assess()

    def test_physical_dma_requires_kernel_owned_buffer_and_32bit_bound(self):
        good=dict(dma_addr=0x1000000,length=0x10000,
                  dma_addr_bits=32,buffer_length=0x20000,
                  allocator="kernel_dma_alloc_coherent",buffer_owner="driver:fd7",
                  device_dma_mask_bits=32,cpu_accessible=True,
                  device_bound=True,mappings_coherent=True)
        result=verify_dma_window(**good)
        self.assertTrue(result["shape_validation_only"])
        self.assertFalse(result["physical_allocation_verified"])
        cases=(
            {"allocator":"devmem"},
            {"allocator":"reserved_address"},
            {"allocator":None},
            {"buffer_owner":" "},
            {"cpu_accessible":False},
            {"device_bound":False},
            {"mappings_coherent":False},
            {"length":0x30000},
            {"length":0},
            {"length":True},
            {"dma_addr":0xffffffff-63},
            {"dma_addr":0x1000001},
            {"dma_addr":-1},
            {"device_dma_mask_bits":24},
            {"dma_addr_bits":24},
            {"dma_addr_bits":True},
        )
        for change in cases:
            with self.subTest(change=change),self.assertRaises(ValueError):
                verify_dma_window(**(good|change))
        self.assertEqual(
            verify_dma_window(**(good|{
                "dma_addr_bits":64,"device_dma_mask_bits":64,
                "dma_addr":0x100000000}))["dma_addr_bits"],64)

    def test_archive_inventory_is_sha_strict_no_faked_owner_vivado_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            none=archive_inventory(None)
            self.assertEqual(none["status"],"NOT_SCANNED")
            self.assertFalse(none["all_sha256_match"])
            missing=archive_inventory(p)
            self.assertEqual([x["status"] for x in missing["items"]],
                             ["MISSING"]*5)
            first,expected=ARCHIVES[0]
            (p/first).write_bytes(b"not an original signed artifact")
            mismatch=archive_inventory(p)
            self.assertEqual(mismatch["items"][0]["status"],"SHA256_MISMATCH")
            self.assertNotEqual(mismatch["items"][0]["observed_sha256"],expected)
            self.assertFalse(mismatch["all_sha256_match"])
            (p/"copy").mkdir()
            (p/"copy"/first).write_bytes(b"copy same name")
            ambiguous=archive_inventory(p)
            self.assertEqual(ambiguous["items"][0]["status"],"AMBIGUOUS")
            self.assertEqual(sha_file(p/first),
                             sha256((p/first).read_bytes()).hexdigest())
            (p/"copy"/first).unlink()
            (p/first).unlink()
            (p/first).symlink_to(p/"nowhere")
            symlink=archive_inventory(p)
            self.assertIn(symlink["items"][0]["status"],("INVALID_FILE","MISSING"))
            with self.assertRaises(ValueError):
                archive_inventory(p/"does-not-exist")

    def test_host_capture_fake_safe_tools_does_not_claim_board(self):
        def fake_run(cmd,**kwargs):
            return {"argv":list(cmd),"status":"OK","returncode":0,
                    "stdout":"" if cmd[0]=="git" and cmd[1]=="status"
                    else "synthetic", "stderr":""}
        got=preflight.capture("host",source_root=ROOT,
                             originals=None,runner=fake_run)
        self.assertEqual(got["mode"],"host")
        self.assertFalse(got["board_identity_observed"])
        self.assertTrue(got["git_clean"])
        self.assertTrue(got["vivado_version_observed"])
        self.assertFalse(got["ready_for_physical_ddr"])
        self.assertFalse(got["physical_readiness"]["ready_to_dma"])
        self.assertEqual(len(got["source_sha256"]),2)
        self.assertEqual(got["accepted_original_archive_inventory"]["status"],
                         "NOT_SCANNED")
        self.assertIn("git rev-parse HEAD",got["commands"])

    def test_board_local_observation_is_not_fpga_attestation(self):
        def reader(p):
            return {"status":"OK",
                    "text":"Xilinx KV260\n" if "model" in str(p)
                    else "read-only synthetic data"}
        def runner(cmd,**kwargs):
            return {"argv":list(cmd),"status":"OK","returncode":0,
                    "stdout":"Linux synthetic","stderr":""}
        got=preflight.capture("board-local",source_root=ROOT,
                             originals=None,reader=reader,runner=runner)
        self.assertTrue(got["board_identity_observed"])
        self.assertTrue(got["board_linux_boot_observed"])
        self.assertTrue(got["accelerator_inventory_observed"])
        self.assertIn("xmutil listapps", got["commands"])
        self.assertIn("xmutil boardid", got["commands"])
        self.assertIn("xmutil bootfw_status", got["commands"])
        self.assertFalse(got["kv260_programmed_by_this_tool"])
        self.assertFalse(got["ready_for_physical_ddr"])
        self.assertEqual(got["accepted_original_archive_inventory"]["status"],
                         "NOT_SCANNED_BOARD_LOCAL")
        got2=preflight.capture("board-local",source_root=ROOT,
                              originals=None,runner=runner,
                              reader=lambda p:{"status":"MISSING","text":""})
        self.assertFalse(got2["board_identity_observed"])

    def test_exclusive_evidence_no_overwrite_or_invented_host_pass(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"capture"
            payload={"test_fixture":True,
                     "ready_for_physical_ddr":False}
            path=preflight.write_capture(out,payload)
            self.assertTrue(path.exists())
            digest=(out/"m08_readonly_inventory.sha256").read_text()
            self.assertIn(sha_file(path),digest)
            before=path.read_bytes()
            with self.assertRaises(FileExistsError):
                preflight.write_capture(out,{"test_fixture":False})
            self.assertEqual(path.read_bytes(),before)

    def test_command_allowlist_and_board_device_file_allowlist(self):
        with self.assertRaises(ValueError):
            preflight._run(("sh","-c","touch /dev/mem"))
        with self.assertRaises(ValueError):
            preflight._run(("xmutil","unloadapp"))
        with self.assertRaises(ValueError):
            preflight._run(("xmutil","loadapp","legacy"))
        with self.assertRaises(ValueError):
            preflight._run(("xmutil","bootfw_update"))
        with self.assertRaises(ValueError):
            preflight._run(("vivado","-mode","batch"))
        with self.assertRaises(ValueError):
            preflight._read(Path("/dev/mem"))
        with self.assertRaises(ValueError):
            preflight._read(Path("/proc/kcore"))
        if not Path("/not-real-m08").exists():
            with self.assertRaises(ValueError):
                preflight.capture("future",source_root=ROOT,originals=None)

    def test_real_cli_host_is_explicit_read_only_and_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"m08_host"
            proc=subprocess.run([
                sys.executable,str(ROOT/"scripts/m08_capture_readonly.py"),
                "--mode","host","--output-dir",str(target)],
                cwd=ROOT,text=True,capture_output=True,timeout=75)
            self.assertEqual(proc.returncode,0,proc.stderr)
            data=json.loads((target/"m08_readonly_inventory.json").read_text())
            self.assertEqual(data["schema"],"m08-kv260-readonly-entry-v1")
            self.assertFalse(data["physical_dma_issued_by_this_tool"])
            self.assertFalse(data["ready_for_physical_ddr"])
            self.assertFalse(data["physical_readiness"]["ready_to_dma"])
            duplicate=subprocess.run([
                sys.executable,str(ROOT/"scripts/m08_capture_readonly.py"),
                "--mode","host","--output-dir",str(target)],
                cwd=ROOT,text=True,capture_output=True,timeout=75)
            self.assertNotEqual(duplicate.returncode,0)
            self.assertIn("already exists",duplicate.stderr)
            self.assertEqual(data,json.loads((target/"m08_readonly_inventory.json").read_text()))


if __name__=="__main__":
    unittest.main()
