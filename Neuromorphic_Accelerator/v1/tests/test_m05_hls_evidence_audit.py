"""Source-only tests for local HLS evidence audit — uses SYNTHETIC report fragments.

No real Vitis run, no physical device, no original operator evidence is read.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_hls_evidence_audit import audit, markdown


SYNTH = """================================================================
== Vitis HLS Report for 'm05_rolling_replay'
* Version:        2025.2 (Build 6295257 on Nov 14 2025)
|ap_clk  |  10.00 ns|  8.256 ns|     1.20 ns|
* Summary:
|       Name      | BRAM_18K|  DSP |   FF   |   LUT  | URAM|
|Total            |       39|     2|    8346|    9956|    0|
* Memory:
|current_U         |current_RAM_2P_BRAM_1R1W      |       16|   0|   0|    0|  8192|   32|     1|     262144|
|Total             |                              |       39|  13|   2|    0| 40968|  191|    15|     572520|
"""
COSIM = """Report time: Sun 08 Nov 2026 12:52:33 PM MST.
Solution: hls.
Simulation tool: xsim.
|      VHDL|        NA|             NA|             NA|             NA|             NA|             NA|             NA|                    NA|
|   Verilog|      Pass|            265|           6328|          17225|            285|           6869|          17248|                 63463|
"""
LOG = """INFO: [COSIM 212-316] Starting C post checking ...
PASS: M05 rolling 8-slot wheel temporal CSim vectors (native or Vitis)
INFO: [COSIM 212-1000] *** C/RTL co-simulation finished: PASS ***
"""


class HlsEvidenceAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m05_report_audit_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "neuromorphic_v1_m05_rolling_cosim_SYNTHETIC"
        self.root.mkdir()
        (self.root / "work/hls/syn/report").mkdir(parents=True)
        (self.root / "work/hls/sim/report").mkdir(parents=True)
        self.write("result.txt", "exit_status=0\n")
        self.write("commit.txt", "827f719778472da39ffa294b431ee848fe360529\n")
        self.write("top.txt", "m05_rolling_replay\n")
        self.write("part.txt", "xck26-sfvc784-2LV-c\n")
        self.write("source_sha256.txt",
                   "a"*64 + "  hls/m05_rolling/m05_rolling.cpp\n" +
                   "b"*64 + "  hls/m05_rolling/m05_rolling_csim_tb.cpp\n")
        self.write("work/hls/syn/report/m05_rolling_replay_csynth.rpt", SYNTH)
        self.write("work/hls/sim/report/m05_rolling_replay_cosim.rpt", COSIM)
        self.write("03_cosim.log", LOG)

    def write(self, name, value):
        (self.root / name).write_text(value, encoding="utf-8")

    def test_full_cosim_extracts_exact_metric_and_hashes(self):
        s = audit(self.root)
        self.assertEqual(s.source_commit,
                         "827f719778472da39ffa294b431ee848fe360529")
        self.assertEqual(s.source_sha256, "a" * 64)
        self.assertEqual(s.testbench_sha256, "b" * 64)
        self.assertEqual((s.requested_clock_ns, s.estimated_clock_ns), (10, 8.256))
        self.assertEqual((s.bram18k, s.lut, s.ff, s.dsp, s.uram),
                         (39, 9956, 8346, 2, 0))
        self.assertEqual((s.current_bram18k, s.current_word_bits), (16, 32))
        self.assertEqual(s.cosim_latency_cycles, (265, 6328, 17225))
        self.assertEqual(s.cosim_interval_cycles, (285, 6869, 17248))
        self.assertEqual(s.cosim_total_cycles, 63463)
        self.assertTrue(s.cosim_verilog_pass)

    def test_synthesis_only_has_no_fabric_or_cosim_assertion(self):
        (self.root / "work/hls/sim/report/m05_rolling_replay_cosim.rpt").unlink()
        self.write("03_cosim.log", "")
        s = audit(self.root)
        self.assertEqual(s.bram18k, 39)
        self.assertIsNone(s.cosim_verilog_pass)
        self.assertIsNone(s.cosim_latency_cycles)
        self.assertIsNone(s.cosim_total_cycles)

    def test_markdown_warns_when_testbench_versions_differ(self):
        first = audit(self.root)
        self.write("source_sha256.txt",
                   "a"*64 + "  hls/m05_rolling/m05_rolling.cpp\n" +
                   "c"*64 + "  hls/m05_rolling/m05_rolling_csim_tb.cpp\n")
        second = audit(self.root)
        result = markdown([first, second])
        self.assertIn("**Latency/interval comparisons are NOT controlled**", result)
        self.assertIn("39", result)
        self.assertIn("6328", result)

    def test_identical_fixture_hashes_still_warn_about_workloads(self):
        result = markdown([audit(self.root), audit(self.root)])
        self.assertIn("testbench SHA256 values match", result)
        self.assertIn("runtime parameters and workloads", result)

    def test_invalid_exit_status_is_never_treated_as_pass(self):
        self.write("result.txt", "exit_status=1\n")
        with self.assertRaisesRegex(ValueError, "exit_status"):
            audit(self.root)

    def test_missing_original_reports_rejected(self):
        (self.root / "work/hls/syn/report/m05_rolling_replay_csynth.rpt").unlink()
        (self.root / "work/hls/sim/report/m05_rolling_replay_cosim.rpt").unlink()
        with self.assertRaisesRegex(ValueError, "no usable"):
            audit(self.root)

    def test_wrong_top_target_or_sha_rejected(self):
        self.write("top.txt", "m05_integrated_replay\n")
        with self.assertRaisesRegex(ValueError, "top mismatch"):
            audit(self.root)
        self.write("top.txt", "m05_rolling_replay\n")
        self.write("part.txt", "xck26_wrong\n")
        with self.assertRaisesRegex(ValueError, "unexpected FPGA"):
            audit(self.root)
        self.write("part.txt", "xck26-sfvc784-2LV-c\n")
        self.write("commit.txt", "bad sha")
        with self.assertRaisesRegex(ValueError, "invalid commit"):
            audit(self.root)

    def test_missing_cosim_log_not_silently_pass(self):
        self.write("03_cosim.log", "cosim did not complete")
        with self.assertRaisesRegex(ValueError, "confirming cosim log"):
            audit(self.root)

    def test_failed_cosim_row_not_silently_pass(self):
        self.write("work/hls/sim/report/m05_rolling_replay_cosim.rpt",
                   COSIM.replace("Pass", "Fail"))
        with self.assertRaisesRegex(ValueError, "not PASS"):
            audit(self.root)

    def test_wrong_top_and_missing_hls_marker_rejected(self):
        self.write("work/hls/syn/report/m05_rolling_replay_csynth.rpt",
                   SYNTH.replace("m05_rolling_replay", "not_our_top"))
        with self.assertRaisesRegex(ValueError, "does not identify"):
            audit(self.root)

    def test_cli_markdown_and_json_are_pure_stdout(self):
        exe = ROOT / "scripts/m05_hls_evidence_audit.py"
        for output in ("--markdown", "--json"):
            with self.subTest(output=output):
                proc = subprocess.run(
                    [sys.executable, str(exe), output, "--evidence", str(self.root)],
                    capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("39", proc.stdout)
                self.assertIn("8.256", proc.stdout)
                self.assertFalse((self.root / "normalized.json").exists())


if __name__ == "__main__":
    unittest.main()
