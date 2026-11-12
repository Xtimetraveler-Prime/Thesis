"""M08.3.1: fail-closed read-only DMA readiness observation, not hardware tests."""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m08_dma_readiness import (
    BLOCKERS,DIRECTORIES,FILES,SCHEMA,collect,read_allowlisted,
    list_allowlisted,write_fresh,audit,
)


class M08DMAReadinessTests(unittest.TestCase):
    def make_os(self,base:Path)->Path:
        osroot=base/"fake_os"
        for name in FILES:
            path=osroot/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes({
                "proc/device-tree/model":b"Xilinx Kria KV260\x00",
                "proc/version":b"Linux version 6.x test only\n",
                "etc/os-release":b"NAME=TEST_ONLY\n",
            }[name])
        for name in DIRECTORIES:
            (osroot/name).mkdir(parents=True,exist_ok=True)
        (osroot/"sys/class/dma_heap/system").mkdir()
        (osroot/"sys/bus/platform/devices/axi_dma_mock_0").mkdir()
        return osroot

    def test_fake_os_observation_never_claims_dma_ownership(self):
        with tempfile.TemporaryDirectory() as td:
            root=self.make_os(Path(td))
            r=collect(root)
            self.assertEqual(r["schema"],SCHEMA)
            self.assertFalse(r["tested_root_is_real_os"])
            self.assertEqual(
                r["sysfs_names"]["sys/class/dma_heap"]["names"],["system"])
            self.assertIn("axi_dma_mock_0",
                          r["sysfs_names"]["sys/bus/platform/devices"]["names"])
            for key in ("verified_kernel_bound_pl_axi_device",
                        "verified_device_dma_mask","verified_device_dma_mapping",
                        "verified_cache_coherency",
                        "verified_quiesce_before_release",
                        "allocated_or_mapped_dma_buffer",
                        "opened_device_or_programmed_pl",
                        "physical_dma_ready"):
                self.assertIs(r[key],False)
            self.assertEqual(r["blockers"],list(BLOCKERS))

    def test_original_fresh_capture_and_independent_sha(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            root=self.make_os(base)
            folder=base/"evidence"
            output=write_fresh(folder,collect(root))
            self.assertTrue(output.is_file())
            a=audit(folder)
            self.assertEqual(
                a["status"],
                "M08_3_READONLY_OBSERVATION_INTEGRITY_PASS_NOT_DMA_READY")
            self.assertEqual(
                a["report_sha256"],sha256(output.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                write_fresh(folder,collect(root))
            # Mutating original evidence is explicitly detected.
            output.write_text(output.read_text().replace(
                "REVIEW_READ_ONLY_EVIDENCE_ONLY",
                "PHYSICAL_DMA_ALLOWED"))
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                audit(folder)

    def test_rehashed_unsafe_claims_still_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            folder=base/"evidence"
            write_fresh(folder,collect(self.make_os(base)))
            p=folder/"m08_3_dma_readiness.json"
            data=json.loads(p.read_text())
            data["physical_dma_ready"]=True
            data["verified_device_dma_mask"]=True
            p.write_text(json.dumps(data,sort_keys=True)+"\n")
            (folder/"m08_3_dma_readiness.sha256").write_text(
                sha256(p.read_bytes()).hexdigest()+
                "  m08_3_dma_readiness.json\n")
            with self.assertRaisesRegex(ValueError,"unsafe or unverified"):
                audit(folder)

    def test_allowlist_bounds_and_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            root=self.make_os(base)
            with self.assertRaisesRegex(ValueError,"not allowlisted"):
                read_allowlisted(root,"dev/mem")
            with self.assertRaisesRegex(ValueError,"not allowlisted"):
                list_allowlisted(root,"sys/kernel/debug")
            target=base/"outside.txt"
            target.write_text("must not read")
            p=root/"proc/version"
            p.unlink()
            p.symlink_to(target)
            self.assertEqual(
                read_allowlisted(root,"proc/version")["status"],"SYMLINK_REFUSED")
            p=root/"etc/os-release"
            p.write_bytes(b"a"*4097)
            self.assertEqual(
                read_allowlisted(root,"etc/os-release")["status"],"TOO_LARGE")
            dma=root/"sys/class/dma_heap"
            for idx in range(130):
                (dma/f"fake_{idx}").mkdir()
            self.assertEqual(list_allowlisted(root,"sys/class/dma_heap")["status"],
                             "TOO_MANY_ENTRIES")

    def test_cli_is_readonly_and_audit_only_mode(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            folder=base/"evidence"
            write_fresh(folder,collect(self.make_os(base)))
            script=ROOT/"scripts/m08_3_dma_readonly.py"
            result=subprocess.run(
                [sys.executable,str(script),"--audit-only","--output-dir",
                 str(folder)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn("NOT_DMA_READY",result.stdout)
            bad=subprocess.run(
                [sys.executable,str(script),"--root","/tmp","--output-dir",
                 str(folder)],capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            self.assertIn("unrecognized arguments",bad.stderr)
            source=script.read_text()
            self.assertNotIn("subprocess.",source)
            self.assertNotIn("mmap(",source)
            self.assertNotIn("ioctl(",source)
            self.assertNotIn("sudo ",source.split("def main()",1)[-1])


if __name__=="__main__":
    unittest.main()
