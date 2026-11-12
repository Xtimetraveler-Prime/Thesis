"""M08.1 independent source preflight receipt validator negative gates."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))
from neuromorphic_accelerator_v1.m08_receipt_audit import audit_receipt
from neuromorphic_accelerator_v1.m08_entry import sha_file
import m08_capture_readonly as cap


def fake_runner(args,**kwargs):
    return {"argv":list(args),"status":"OK","returncode":0,
            "stdout":"" if args[:2]==("git","status") else "fake", "stderr":""}


def fixture(role="host"):
    def read(p):
        return {"status":"OK","text":"kv260" if "model" in str(p) else "fixture"}
    return cap.capture(role,source_root=ROOT,originals=None,
                       runner=fake_runner,reader=read)


class M08ReceiptAuditTests(unittest.TestCase):
    def test_host_receipt_audits_only_integrity_not_real_board(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"host"
            cap.write_capture(out,fixture())
            result=audit_receipt(out)
            self.assertEqual(result["status"],"RECEIPT_HASH_AND_SCHEMA_OK")
            self.assertEqual(result["mode"],"host")
            self.assertFalse(result["physical_board_identity_authenticated"])
            self.assertFalse(result["ready_for_physical_ddr"])
            self.assertFalse(result["physical_run_verified"])
            self.assertEqual(result["receipt_sha256"],
                             sha_file(out/"m08_readonly_inventory.json"))

    def test_board_local_receipt_never_authenticates_board_or_dma(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"board"
            cap.write_capture(out,fixture("board-local"))
            result=audit_receipt(out)
            self.assertEqual(result["mode"],"board-local")
            self.assertFalse(result["physical_board_identity_authenticated"])
            self.assertFalse(result["ready_for_physical_ddr"])

    def test_modified_receipt_is_rejected_even_with_valid_json(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"host"
            cap.write_capture(out,fixture())
            p=out/"m08_readonly_inventory.json"
            data=json.loads(p.read_text())
            data["platform"]["machine"]="tampered"
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,"SHA256"):
                audit_receipt(out)

    def test_self_consistent_but_false_physical_or_extended_commands_rejected(self):
        changes=(
            lambda r:r.__setitem__("ready_for_physical_ddr",True),
            lambda r:r.__setitem__("kv260_programmed_by_this_tool",True),
            lambda r:r["physical_readiness"].__setitem__("ready_to_dma",True),
            lambda r:r["commands"].__setitem__("sudo devmem",{"status":"OK"}),
            lambda r:r.__setitem__("board_identity_observed",True),
            lambda r:r.__setitem__("source_sha256",{}),
            lambda r:r["accepted_original_archive_inventory"].__setitem__(
                "all_sha256_match",True),
        )
        for fn in changes:
            with self.subTest(fn=fn.__code__.co_firstlineno):
                with tempfile.TemporaryDirectory() as d:
                    report=fixture()
                    fn(report)
                    folder=Path(d)/"evidence"
                    cap.write_capture(folder,report)
                    with self.assertRaises(ValueError):
                        audit_receipt(folder)

    def test_cli_preserves_accepted_receipt_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/"capture"
            cap.write_capture(folder,fixture())
            cmd=[sys.executable,str(ROOT/"scripts/m08_audit_readonly.py"),
                 "--capture-dir",str(folder),"--output",str(Path(d)/"audit.json")]
            run=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT)
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads((Path(d)/"audit.json").read_text())
            self.assertFalse(result["ready_for_physical_ddr"])
            again=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT)
            self.assertNotEqual(again.returncode,0)
            self.assertIn("already exists",again.stderr)


if __name__=="__main__":
    unittest.main()
