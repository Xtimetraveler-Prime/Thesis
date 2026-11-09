"""Native-only source/evidence tests for generated XSim RAM .dat staging.

Uses synthetic generated RTL and synthetic binary RAM images. Does NOT run
Vitis, Vivado, XSim, or the physical board.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_rtl_meminit import referenced_init_files, stage_meminit


class M05RTLMemoryAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m05_synthetic_raminit_")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.impl = root / "neuromorphic_v1_m05_rolling_impl_SYNTHETIC"
        self.verilog = self.impl / "work/hls/syn/verilog"
        self.verilog.mkdir(parents=True)
        self.dest = root / "neuromorphic_v1_m05_rolling_axis_rtl_SYNTHETIC"
        self.dest.mkdir()
        self.asset = "m05_rolling_replay_current_RAM_2P_BRAM_1R1W.dat"
        self.verilog.joinpath("m05_rolling_replay.v").write_text(
            "module m05_rolling_replay;\n" +
            "parameter INIT_FILE = \"./" + self.asset + "\";\n"
            "endmodule\n"
        )
        self.original = self.verilog / self.asset
        self.original.write_bytes(b"0000\n0001\n")

    def test_parses_actual_named_generated_init_reference(self):
        self.assertEqual(referenced_init_files(self.verilog), {self.asset})

    def test_stage_uses_original_contents_and_writes_provenance(self):
        result = stage_meminit(self.impl, self.dest)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], self.asset)
        self.assertEqual((self.dest / self.asset).read_bytes(),
                         self.original.read_bytes())
        manifest = (self.dest / "ram_init_manifest.txt").read_text()
        self.assertIn(self.asset, manifest)
        self.assertIn("source=", manifest)

    def test_second_attempt_refuses_to_mutate_existing_evidence(self):
        stage_meminit(self.impl, self.dest)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            stage_meminit(self.impl, self.dest)

    def test_missing_generated_init_never_fabricates_zero_data(self):
        self.original.unlink()
        with self.assertRaisesRegex(ValueError, "missing tool-generated"):
            stage_meminit(self.impl, self.dest)
        self.assertFalse((self.dest / self.asset).exists())

    def test_conflicting_copies_are_rejected_before_any_write(self):
        duplicate = self.impl / "work/hls/sim/verilog" / self.asset
        duplicate.parent.mkdir(parents=True)
        duplicate.write_bytes(b"ffff\n")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            stage_meminit(self.impl, self.dest)
        self.assertFalse((self.dest / self.asset).exists())

    def test_identical_duplicate_is_safe(self):
        duplicate = self.impl / "work/hls/sim/verilog" / self.asset
        duplicate.parent.mkdir(parents=True)
        duplicate.write_bytes(self.original.read_bytes())
        self.assertEqual(len(stage_meminit(self.impl, self.dest)), 1)

    def test_refuses_unrelated_and_unsafe_init_filename(self):
        self.verilog.joinpath("m05_rolling_replay.v").write_text(
            'parameter INIT_FILE = "unrelated.dat";\n')
        with self.assertRaisesRegex(ValueError, "unexpected"):
            referenced_init_files(self.verilog)

    def test_cli_fails_closed_on_missing_asset(self):
        self.original.unlink()
        cmd = [
            sys.executable, str(ROOT / "scripts/m05_rtl_meminit.py"),
            "--impl-evidence", str(self.impl),
            "--output-directory", str(self.dest),
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("RAM INIT STAGING FAIL:", proc.stderr)
        self.assertFalse((self.dest / "ram_init_manifest.txt").exists())

    def test_safe_runner_checks_meminit_and_rejects_xsim_warnings(self):
        runner = (ROOT / "scripts/run_m05_rolling_rtl_stress.sh").read_text()
        self.assertIn("scripts/m05_rtl_meminit.py", runner)
        self.assertIn("01_ram_init.log", runner)
        self.assertIn("cannot be opened for reading", runner)
        self.assertIn("mkdir \"$OUT\"", runner)
        self.assertNotIn("rm -rf", runner)


if __name__ == "__main__":
    unittest.main()
