"""M08 D3.2 passive unreleased bitstream: synthetic negative tests (NO Vivado)."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d3_2_passive_bitstream_gate.py"
spec = importlib.util.spec_from_file_location("m08_passive_bitgen_gate_test", SCRIPT)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PassiveUnreleasedBitgenTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.run = self.base / "M08" / "m08_d3_2_passive_synth_SYNTHETIC"
        (self.run / "bitstream_candidate").mkdir(parents=True)
        self.stub = types.SimpleNamespace(
            ReviewRejected=ValueError,
            review_run=lambda _: {
                "status": "PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED",
                "physical_programming_authorized": False,
            },
        )

    def fixture(self):
        sample = b"\x00\x09synthetic_NOT_A_VIVADO_IMAGE\x00\x01" * 7500
        (self.run / m.BIT).write_bytes(sample)
        readback = dict(m.FIELDS)
        readback.update({
            "vivado_version": "2025.2",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "source_route_status": "route_design Complete!",
            "bitstream_size_bytes": str(len(sample)),
        })
        (self.run / m.REPORT).write_text(
            "".join(f"{key}={value}\n" for key, value in readback.items()))
        (self.run / "07_passive_bitgen_vivado.log").write_text(
            "M08_D3_2_PASSIVE_BITSTREAM_CANDIDATE_CREATED_OFFLINE_UNRELEASED_NO_BOARD\n")
        (self.run / "08_passive_bitgen_vivado.jou").write_text("# SYNTHETIC\n")
        (self.run / "65_prebit_pc_review.json").write_text(json.dumps({
            "status": "PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED",
            "physical_programming_authorized": False,
        }))
        (self.run / "66_pc_unreleased_bitstream_gate.json").write_text(
            json.dumps({"status": "SYNTHETIC_PRE_LEDGER_NO_HARDWARE"}))
        self.resign()

    def resign(self):
        text = "".join(
            sha256((self.run / f).read_bytes()).hexdigest() + "  " + f + "\n"
            for f in sorted(m.EVIDENCE)
        )
        (self.run / m.LEDGER).write_text(text)

    def mutate(self, relative: str, find: str, replace: str, resign=True):
        f = self.run / relative
        data = f.read_text()
        self.assertIn(find, data)
        f.write_text(data.replace(find, replace))
        if resign:
            self.resign()

    def test_parent_source_accepted_only_for_offline_unreleased_image(self):
        result = m.source_gate()
        self.assertEqual(
            result["status"], "M08_D3_2_OFFLINE_UNRELEASED_PASSIVE_BITGEN_SOURCE_ACCEPTED")
        self.assertFalse(result["native_candidate_generated"])
        self.assertFalse(result["physical_programming_authorized"])
        self.assertTrue(result["original_bad_bitstream_quarantined"])

    def test_synthetic_candidate_sha_accepted_no_board(self):
        self.fixture()
        result = m.native_candidate(self.run, parent=self.stub)
        self.assertTrue(result["new_candidate_ledger_verified"])
        self.assertEqual(result["bitstream_path"], m.BIT)
        self.assertFalse(result["physical_programming_authorized"])
        self.assertFalse(result["fan_cooling_and_stock_rollback_proven"])

    def test_pre_ledger_status_never_claims_receipt_accepted(self):
        self.fixture()
        (self.run / m.LEDGER).unlink()
        result = m.native_candidate(self.run, pre_ledger=True, parent=self.stub)
        self.assertFalse(result["new_candidate_ledger_verified"])
        self.assertIn("PRE_LEDGER", result["status"])

    def test_binary_bytes_tamper_rejected(self):
        self.fixture()
        (self.run / m.BIT).write_bytes(b"X" * 240000)
        with self.assertRaisesRegex(m.Rejected, "candidate receipt digest mismatch"):
            m.native_candidate(self.run, parent=self.stub)

    def test_forged_hardware_authorization_rejected_even_if_resigned(self):
        self.fixture()
        self.mutate(m.REPORT, "physical_programming_authorized=NO",
                    "physical_programming_authorized=YES")
        with self.assertRaisesRegex(m.Rejected, "physical_programming_authorized"):
            m.native_candidate(self.run, parent=self.stub)

    def test_false_deployment_and_overlay_claim_rejected(self):
        self.fixture()
        self.mutate(m.REPORT, "bit_bin=NOT_CREATED", "bit_bin=CREATED")
        with self.assertRaisesRegex(m.Rejected, "bit_bin"):
            m.native_candidate(self.run, parent=self.stub)

    def test_additional_bit_bin_output_rejected(self):
        self.fixture()
        (self.run / "bitstream_candidate" / "other.bit.bin").write_bytes(b"\x00" * 10)
        with self.assertRaisesRegex(m.Rejected, "unexpected extra image"):
            m.native_candidate(self.run, parent=self.stub)

    def test_wrong_size_or_missing_success_marker_rejected(self):
        self.fixture()
        self.mutate(m.REPORT, "bitstream_size_bytes=240000",
                    "bitstream_size_bytes=1")
        with self.assertRaisesRegex(m.Rejected, "byte"):
            m.native_candidate(self.run, parent=self.stub)
        self.fixture()
        self.mutate("07_passive_bitgen_vivado.log",
                    "M08_D3_2_PASSIVE_BITSTREAM_CANDIDATE_CREATED_OFFLINE_UNRELEASED_NO_BOARD",
                    "BITSTREAM_GENERATION_FAILED")
        with self.assertRaisesRegex(m.Rejected, "marker"):
            m.native_candidate(self.run, parent=self.stub)

    def test_sha_ledger_duplicate_and_path_traversal_rejected(self):
        self.fixture()
        receipt = self.run / m.LEDGER
        s = receipt.read_text().splitlines()
        receipt.write_text("\n".join(s[:-1] + [s[0]]) + "\n")
        with self.assertRaisesRegex(m.Rejected, "duplicated"):
            m.native_candidate(self.run, parent=self.stub)

    def test_symlink_candidate_file_rejected(self):
        self.fixture()
        f = self.run / m.BIT
        moved = f.parent / "moved"
        f.rename(moved)
        f.symlink_to(moved)
        with self.assertRaisesRegex(m.Rejected, "symlinked"):
            m.native_candidate(self.run, parent=self.stub)

    def test_bitstream_source_rejects_programming_and_second_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for rel in (
                "scripts/m08_d3_2_passive_bitstream_candidate.tcl",
                "scripts/run_m08_d3_2_passive_bitstream_pc.sh",
            ):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, path)
            current = m.ROOT
            current_import_parent = m.import_parent
            try:
                m.ROOT = root
                m.import_parent = lambda *args: types.SimpleNamespace(
                    RouteRejected=ValueError,
                    source_gate=lambda: {
                        "status": "MOCK_PASSIVE_PARENT_SOURCE_NOT_VENDOR",
                        "bitstream_created": False,
                        "hardware_mmio_authorized": False,
                    },
                )
                file = root / "scripts/m08_d3_2_passive_bitstream_candidate.tcl"
                file.write_text(file.read_text() + "\nprogram_hw_devices\n")
                with self.assertRaisesRegex(m.Rejected, "unsafe active"):
                    m.source_gate()
                shutil.copy2(ROOT / "scripts/m08_d3_2_passive_bitstream_candidate.tcl", file)
                file.write_text(file.read_text() + "\nwrite_bitstream -force bogus.bit\n")
                with self.assertRaisesRegex(m.Rejected, "exactly one"):
                    m.source_gate()
            finally:
                m.ROOT = current
                m.import_parent = current_import_parent

    @unittest.skipUnless(shutil.which("bash") and shutil.which("tclsh"),
                         "bash or tclsh missing")
    def test_owner_runner_and_vivado_tcl_syntax_only(self):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / "scripts/run_m08_d3_2_passive_bitstream_pc.sh")],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = ROOT / "scripts/m08_d3_2_passive_bitstream_candidate.tcl"
        code = ("set f [open {" + str(path) + "} r]\n"
                "set contents [read $f]\nclose $f\n"
                "puts [info complete $contents]\n")
        parse = subprocess.run(["tclsh"], input=code, text=True,
                               capture_output=True, timeout=10)
        self.assertEqual(parse.returncode, 0, parse.stderr)
        self.assertEqual(parse.stdout.strip(), "1")

    def test_readonly_auditor_has_no_hardware_or_vendor_subprocess(self):
        source = SCRIPT.read_text()
        for forbidden in (
            "subprocess.run(", "os.system(", "program_hw_devices(",
            "open_hw_manager(", "write_bitstream(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
