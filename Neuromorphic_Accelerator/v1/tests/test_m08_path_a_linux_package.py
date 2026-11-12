"""M08.2b Path A OFFLINE Linux packaging SOURCE + synthetic refusal tests.

NO real bootgen, dtc, firmware install, FPGA programming or device mmap in CI.
The owner must run native bootgen/dtc on their own PC for real evidence.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts/m08_path_a_stage_linux_package.py"
spec = importlib.util.spec_from_file_location("m08_path_a_stage_linux_package", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestM08PathAOfflinePackage(unittest.TestCase):
    def test_template_has_exact_stock_k26_fpga_full_reset_fixups(self):
        s = mod.DTS
        self.assertIn("/plugin/;", s)
        self.assertIn("&fpga_full", s)
        self.assertIn('firmware-name = "m08-v1-fan-page.bit.bin";', s)
        for name in ("0x74", "0x75", "0x76", "0x77"):
            self.assertIn(name, s)
        self.assertEqual(s.count("&zynqmp_reset"), 4)
        self.assertIn('"shell_type": "PL_FLAT"', json.dumps(mod.SHELL))
        self.assertEqual(mod.SHELL["num_slots"], "1")
        self.assertNotIn("0xffffffff", "\n".join(
            row for row in s.splitlines()
            if row.strip() and not row.lstrip().startswith("*")))
        self.assertNotIn("generic-uio", s)
        self.assertNotIn("m08-identity@", s)
        self.assertNotIn("m08-page@", s)

    def test_decoded_dtbo_must_have_real_symbolic_fixups(self):
        ok = (
            "/dts-v1/;\n"
            "/ { fragment@0 { __overlay__ {\n"
            'firmware-name = "m08-v1-fan-page.bit.bin";\n'
            'resets = <0xffffffff 0x74 0xffffffff 0x75 '
            '0xffffffff 0x76 0xffffffff 0x77>; '
            "}; }; __fixups__ { fpga_full = ...; zynqmp_reset = ...; }; };"
        )
        mod.verify_overlay_text(ok)
        for bad in (
            ok.replace("fpga_full", "fpga_partial"),
            ok.replace("zynqmp_reset", "bad_reset"),
            ok.replace('"m08-v1-fan-page.bit.bin"', '"wrong.bit.bin"'),
            ok.replace("__fixups__", "no_fixups"),
            ok + "\ncompatible = \"generic-uio\";\n",
            ok + "\nm08-identity@a0000000\n",
        ):
            with self.subTest(fragment=bad[-60:]), self.assertRaises(ValueError):
                mod.verify_overlay_text(bad)

    def test_source_never_runs_board_or_install_commands(self):
        s = FILE.read_text()
        active = "\n".join(line for line in s.splitlines()
                           if line.strip() and not line.lstrip().startswith("#"))
        for bad in (
            "xmutil unloadapp", "xmutil loadapp", "program_hw_devices",
            "open_hw_manager", "sudo ", "open(\"/dev/mem\"", "devmem ",
            "systemctl stop", "systemctl restart", "fpgautil",
            "ssh ", "scp ", "rsync ", "flashcp ", "write_cfgmem",
            "fw_setenv", "bootfw_update",
        ):
            self.assertNotIn(bad, active)
        self.assertIn("bootgen", s)
        self.assertIn("dtc", s)
        self.assertIn("PL_FLAT", s)
        self.assertIn("OFFLINE_PACKAGE_STAGED_NO_BOARD_NO_MMIO_ACCESS", s)
        self.assertIn("01_inputs.json", s)
        self.assertIn("99_evidence_sha256.txt", s)
        self.assertIn("ORIGINAL_BIT_SHA", s)
        self.assertNotIn("mkdir('/lib/firmware", s)

    def test_bad_release_sha_or_incomplete_receipt_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            release = Path(d) / "m08_2b_path_a_fan_bitstream_TEST"
            release.mkdir()
            (release / "08_evidence_sha256.txt").write_text(
                sha256(b"test").hexdigest()
                + "  05_m08_path_a_fan_page.bit\n"
            )
            (release / "05_m08_path_a_fan_page.bit").write_bytes(b"test")
            with self.assertRaisesRegex(ValueError, "incomplete ORIGINAL"):
                mod.check_release(release)
            self.assertEqual(len(list(release.iterdir())), 2)

    def test_attestation_does_not_accept_unfanned_or_unvalidated_release(self):
        with tempfile.TemporaryDirectory() as d:
            release = Path(d) / "m08_2b_path_a_fan_bitstream_TEST"
            release.mkdir()
            for name in mod.EXPECTED_RELEASE_FILES:
                (release / name).write_text("NOT_GENUINE_" + name)
            ledger = "\n".join(
                sha256((release / name).read_bytes()).hexdigest() + "  " + name
                for name in mod.EXPECTED_RELEASE_FILES
            )
            (release / "08_evidence_sha256.txt").write_text(ledger + "\n")
            with self.assertRaisesRegex(ValueError, "exact byte count"):
                mod.check_release(release)

    def test_cannot_stage_into_boot_or_kernel_firmware(self):
        with tempfile.TemporaryDirectory() as d:
            release = Path(d) / "m08_2b_path_a_fan_bitstream_TEST"
            release.mkdir()
            # Do not attempt any copy or conversion: original receipt missing.
            with self.assertRaisesRegex(ValueError, "missing original release"):
                mod.stage(release, Path("/lib/firmware"))

    def test_cli_requires_explicit_original_and_existing_pc_evidence_parent(self):
        proc = subprocess.run(
            [sys.executable, str(FILE), "--release-dir", "/bad",
             "--evidence-base", "/bad"],
            capture_output=True, text=True, timeout=15
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("OFFLINE_REJECTED", proc.stderr)

    def test_deterministic_evidence_ledger_excludes_own_checksum(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory / "app").mkdir()
            (directory / "app" / "sample.dtbo").write_bytes(b"FAKE TEST DTBO")
            (directory / "98_status.txt").write_text("TEST_FIXTURE\n")
            mod.write_ledger(directory)
            text = (directory / "99_evidence_sha256.txt").read_text()
            self.assertIn("app/sample.dtbo", text)
            self.assertIn("98_status.txt", text)
            self.assertNotIn("99_evidence_sha256.txt", text)
            self.assertEqual(len(text.splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
