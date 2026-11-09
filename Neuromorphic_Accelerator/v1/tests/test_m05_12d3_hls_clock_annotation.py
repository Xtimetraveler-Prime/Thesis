"""M05.12d.3 synthetic-only tests for metadata staging of original Vitis HLS.

Genuine 2025.2 owner Vivado BD 41-237/41-967 clock result requires a new
offline run. These tests do not imply genuine HLS or Vivado acceptance.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d3_hls_clock_annotation import BUSIFS, annotate, stage

SCRIPT = ROOT / "scripts/m05_12d3_hls_clock_annotation.py"
TCL = ROOT / "scripts/m05_12d3_address_validate_candidate.tcl"
RUNNER = ROOT / "scripts/run_m05_12d3_address_validate_candidate.sh"


def fixture() -> bytes:
    return (
        b"module m05_rolling_replay(ap_clk, ap_rst_n, neurons_TDATA);\n"
        b"  input ap_clk;\n"
        b"  input ap_rst_n;\n"
        b"  input [127:0] neurons_TDATA;\n"
        b"endmodule\n"
    )


class M0512D3ClockAnnotationTests(unittest.TestCase):
    def test_exact_metadata_only_inserted_and_original_bytes_recoverable(self):
        src = fixture()
        data, annotation = annotate(src, 96968727)
        self.assertEqual(data.count(b"X_INTERFACE_PARAMETER"), 1)
        self.assertIn(b"ASSOCIATED_BUSIF " + BUSIFS.encode(), annotation)
        self.assertIn(b"ASSOCIATED_RESET ap_rst_n", annotation)
        self.assertIn(b"FREQ_HZ 96968727", annotation)
        self.assertIn(b"FREQ_TOLERANCE_HZ 0", annotation)
        self.assertEqual(data.replace(annotation, b"", 1), src)
        self.assertIn(b"input [127:0] neurons_TDATA", data)

    def test_preserve_nonansi_wire_and_crlf_verbatim(self):
        original = fixture().replace(b"input ap_clk;", b"input wire ap_clk;").replace(
            b"\n", b"\r\n")
        data, metadata = annotate(original, 96968727)
        self.assertEqual(data.replace(metadata, b"", 1), original)

    def test_reject_wrong_top_missing_or_duplicate_clock(self):
        bads = (
            fixture().replace(b"m05_rolling_replay", b"fake_neural_top"),
            fixture().replace(b"  input ap_clk;\n", b""),
            fixture().replace(b"  input ap_clk;", b"  input ap_clk;\n  input ap_clk;"),
            fixture().replace(b"endmodule", b"module m05_rolling_replay; endmodule\nendmodule"),
            fixture() + b"(* ASSOCIATED_BUSIF neurons *)",
        )
        for bad in bads:
            with self.subTest(input=bad[:60]):
                with self.assertRaises(ValueError):
                    annotate(bad, 96968727)

    def test_reject_wrong_frequency_and_reannotation(self):
        for frequency in (0, 999999, 500000001, -1):
            with self.assertRaises(ValueError):
                annotate(fixture(), frequency)
        first, _ = annotate(fixture(), 96968727)
        with self.assertRaises(ValueError):
            annotate(first, 96968727)

    def test_stage_is_immutable_records_hashes_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            parent = directory / "hls"
            parent.mkdir()
            origin = parent / "m05_rolling_replay.v"
            origin.write_bytes(fixture())
            derived = directory / "09_hls_clock_annotated_top.v"
            manifest = directory / "09_hls_clock_annotation_manifest.txt"
            before = hashlib.sha256(origin.read_bytes()).hexdigest()
            stage(origin, derived, manifest, 96968727)
            self.assertEqual(before, hashlib.sha256(origin.read_bytes()).hexdigest())
            self.assertIn("ORIGINAL_SHA256|" + before, manifest.read_text())
            self.assertIn("FREQ_HZ|96968727", manifest.read_text())
            self.assertIn("physical_board|NOT_AUTHORIZED", manifest.read_text())
            self.assertIn(b"ASSOCIATED_BUSIF", derived.read_bytes())
            with self.assertRaises(ValueError):
                stage(origin, derived, manifest, 96968727)
            with self.assertRaises(ValueError):
                stage(origin, origin, manifest, 96968727)

    def test_runner_stages_only_original_top_copy_before_vivado(self):
        run = RUNNER.read_text()
        tcl = TCL.read_text()
        for item in (
            "m05_12d3_hls_clock_annotation.py",
            "09_hls_clock_annotated_top.v",
            "09_hls_clock_annotation_manifest.txt",
            "--original-top", "--derived-top", "--frequency-hz 96968727",
        ):
            self.assertIn(item, run)
        self.assertIn("set annotated_top [lindex $argv 7]", tcl)
        self.assertIn("if {[file normalize $source] eq [file normalize [file join $rtl_dir m05_rolling_replay.v]]}", tcl)
        self.assertIn("add_files -norecurse $annotated_top", tcl)
        self.assertIn("M05_D3_HLS_CLK_PS_ACTUAL", tcl)
        self.assertIn("CONFIG.FREQ_HZ [get_bd_pins -quiet ps/pl_clk0]", tcl)
        self.assertIn("CONFIG.ASSOCIATED_BUSIF", tcl)
        self.assertIn("get_bd_intf_pins -quiet hls/s_axi_control", tcl)
        self.assertIn("validate_bd_design -force", tcl)
        self.assertLess(tcl.index("add_files -norecurse $annotated_top"),
                        tcl.index("create_bd_design "))
        for forbidden in ("program_hw_devices", "open_hw_target", "write_bitstream",
                          "connect_hw_server", "xsdb"):
            self.assertNotIn(forbidden, run + tcl)

    def test_cli_rejects_missing_hls_and_does_not_create_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            out = directory / "09_hls_clock_annotated_top.v"
            manifest = directory / "09_hls_clock_annotation_manifest.txt"
            proc = subprocess.run([
                sys.executable, str(SCRIPT),
                "--original-top", str(directory / "missing.v"),
                "--derived-top", str(out),
                "--manifest", str(manifest),
                "--frequency-hz", "96968727",
            ], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(out.exists())
            self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
