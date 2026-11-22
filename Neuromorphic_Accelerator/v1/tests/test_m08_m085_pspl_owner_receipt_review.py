"""Synthetic mutation tests for the read-only *owner-original* PSPL receipt reviewer.

These fabricate test receipts in temporary PC directories; passing the tests
never means that CI ran Vivado or independently observed the owner PC.
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_m085_pspl_owner_receipt_review as reviewer

MARKER="M08_M085_QUARANTINED_PSPL_BD_COMPLETE_NO_DMA_NO_BITSTREAM"


class OwnerReceiptReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.d=Path(self.temp.name)/"m08_m085_pspl_bd_synthetic_1234"
        self.d.mkdir()
        for name in reviewer.SOURCE_NAMES:
            src=ROOT/"rtl/m08"/name
            dst=self.d/"source_snapshot"/name
            dst.parent.mkdir(exist_ok=True)
            shutil.copyfile(src,dst)
        shutil.copyfile(ROOT/"rtl/m08_d3c_fabric_por.v",
                        self.d/"source_snapshot/m08_d3c_fabric_por.v")
        shutil.copyfile(reviewer.SCRIPT,self.d/"03_builder_source.tcl")
        (self.d/"reports").mkdir()
        (self.d/"00_vivado.log").write_text(
            "# Vivado v2025.2 (64-bit)\n# puts \""+MARKER+"\"\n"+MARKER+"\n")
        (self.d/"01_vivado.jou").write_text("source offline_builder.tcl\n")
        (self.d/"02_vivado_exit_status.txt").write_text("vivado_exit_status=0\n")
        (self.d/"04_stdout.txt").write_text(
            "****** Vivado v2025.2\n# puts \""+MARKER+"\"\n"+MARKER+"\n")
        (self.d/"05_stderr.txt").write_text("offline Vivado no stderr\n")
        (self.d/"06_context.txt").write_text(
            "source_revision=EXAMPLE\nrepository_dir=/synthetic\n"
            "vivado=vivado v2025.2 (64-bit)\n"
            "scope=QUARANTINED_PSPL_BD_ONLY_NO_DMA\n")
        (self.d/"reports/10_fan_a12.xdc").write_text(
            "set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]\n"
            "set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]\n")
        (self.d/"reports/20_quarantined_bd_observation.txt").write_text(
            "".join(f"{key}={value}\n" for key,value in reviewer.STATUS.items()))
        self.rehash()

    def rehash(self):
        self.d.joinpath("99_evidence_sha256.txt").write_text(
            "".join(
                hashlib.sha256((self.d/rel).read_bytes()).hexdigest()
                +"  ./"+rel+"\n" for rel in sorted(reviewer.EXPECTED)
            )
        )

    def change(self,path,text,re_hash=True):
        (self.d/path).write_text(text,encoding="utf-8")
        if re_hash:self.rehash()

    def test_synthetic_receipt_baseline_is_declared_nonphysical(self):
        result=reviewer.verify(self.d)
        self.assertEqual(result["files_sha256_verified"],22)
        self.assertFalse(result["physical_dma_allowed"])
        self.assertFalse(result["independent_vivado_replay_performed"])
        self.assertFalse(result["rtl_synthesis_or_route_performed"])
        self.assertEqual(result["status"],
                         "OWNER_RECEIPT_CONSISTENT_SOURCE_ONLY_NATIVE_BD_NOT_DMA_RELEASE")

    def test_byte_tampering_fails_even_if_no_other_evidence_changed(self):
        for rel in (
            "03_builder_source.tcl",
            "00_vivado.log",
            "source_snapshot/m08_m085_axil_managed_neural_candidate.v",
            "reports/20_quarantined_bd_observation.txt",
        ):
            with self.subTest(path=rel):
                before=(self.d/rel).read_bytes()
                self.change(rel,"tampered\n",re_hash=False)
                with self.assertRaises(reviewer.EvidenceRejected):
                    reviewer.verify(self.d)
                (self.d/rel).write_bytes(before)
                self.rehash()

    def test_rehashed_modified_original_source_is_rejected(self):
        rel="source_snapshot/m08_m085_axil_managed_neural_candidate.v"
        self.change(rel,(self.d/rel).read_text()+"\n// attacker added\n")
        with self.assertRaisesRegex(reviewer.EvidenceRejected,"differs from"):
            reviewer.verify(self.d)

    def test_rehashed_native_status_spoof_fails_closed(self):
        rel="reports/20_quarantined_bd_observation.txt"
        original=(self.d/rel).read_text()
        for bad in (
            original.replace("csr_trusted=HARDWIRED_ZERO","csr_trusted=HIGH"),
            original.replace("interconnect_drain_ack=HARDWIRED_ZERO",
                             "interconnect_drain_ack=HARDWIRED_ONE"),
            original.replace("native_route=NOT_RUN","native_route=ROUTED"),
            original.replace("linux_dma_driver=NOT_PRESENT","linux_dma_driver=PRESENT"),
            original+"status=OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY\n",
            original.replace("ps_hpm0_width=128","ps_hpm0_width=32"),
        ):
            with self.subTest(bad=bad[-65:]):
                self.change(rel,bad)
                with self.assertRaises(reviewer.EvidenceRejected):
                    reviewer.verify(self.d)
        self.change(rel,original)

    def test_rehashed_failed_vivado_and_forged_marker_are_rejected(self):
        original=self.d.joinpath("04_stdout.txt").read_text()
        for rel,bad in (
            ("02_vivado_exit_status.txt","vivado_exit_status=1\n"),
            ("04_stdout.txt","Vivado v2025.2\n"),
            ("00_vivado.log","Vivado v2025.1\n"+MARKER+"\n"),
            ("06_context.txt","vivado=vivado v2025.1\n"),
            ("reports/10_fan_a12.xdc","set_property PACKAGE_PIN B10 [get_ports {M08_FAN_PWM}]\n"),
        ):
            with self.subTest(rel=rel):
                before=(self.d/rel).read_text()
                self.change(rel,bad)
                with self.assertRaises(reviewer.EvidenceRejected):
                    reviewer.verify(self.d)
                self.change(rel,before)
        self.assertEqual((self.d/"04_stdout.txt").read_text(),original)

    def test_missing_extra_and_duplicate_manifest_entries_rejected(self):
        path=self.d/"99_evidence_sha256.txt"
        original=path.read_text()
        for bad in (
            "\n".join(original.splitlines()[1:])+"\n",
            original + "a"*64+"  ./unexpected.txt\n",
            original + original.splitlines()[0]+"\n",
            original.replace("  ./", " *./",1),
        ):
            with self.subTest(bad=bad[-60:]):
                path.write_text(bad)
                with self.assertRaises(reviewer.EvidenceRejected):
                    reviewer.verify(self.d)
        path.write_text(original)

    def test_symlinked_evidence_and_unsafe_unledgered_bitstream_blocked(self):
        path=self.d/"04_stdout.txt"
        real=path.read_bytes()
        path.unlink()
        (self.d/"real_stdout_source.txt").write_bytes(real)
        path.symlink_to("real_stdout_source.txt")
        with self.assertRaises(reviewer.EvidenceRejected):
            reviewer.verify(self.d)
        path.unlink()
        path.write_bytes(real)
        (self.d/"real_stdout_source.txt").unlink()
        path=self.d/"project/synthetic.bit"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"not an actual bitstream")
        with self.assertRaises(reviewer.EvidenceRejected):
            reviewer.verify(self.d)

    def test_requires_exact_named_original_evidence_dir(self):
        self.d.rename(self.d.parent/"unrecognized_dir")
        with self.assertRaises(reviewer.EvidenceRejected):
            reviewer.verify(self.d.parent/"unrecognized_dir")

    def test_cli_requires_real_owner_root_no_access_to_unrelated_dirs(self):
        exe=ROOT/"scripts/m08_m085_pspl_owner_receipt_review.py"
        p=subprocess.run([sys.executable,str(exe),
                          "--original-evidence",str(self.d)],
                         capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,2,p.stdout+p.stderr)
        self.assertIn("outside owner M08 original root",p.stderr)


if __name__=="__main__":
    unittest.main()
