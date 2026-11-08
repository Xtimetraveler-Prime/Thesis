"""M05.8 host-only strict log-parser tests using SYNTHETIC XSim transcripts.

These are NOT new RTL/Vivado tests. The genuine RTL gate is the user's
offline --late-error execution against original generated Verilog.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_rtl_transaction_replay import replay_log

PASS = ("PASS: M05 REAL RTL AXIS LATE-ERROR status=4 "
        "provisional=8 committed=0; output_stalls=80; ingress_gaps=20")
FOOTER = "M05_RTL_FINAL status=4 provisional=8 committed=0"


def successful_synthetic_log():
    records = []
    for tick in range(4):
        for neuron in range(2):
            spike = int(tick == 0 and neuron == 0)
            evaluated = spike
            delivery = int(tick == 0)
            records.append(
                f"M05_RTL_PROVISIONAL tick={tick} neuron={neuron} "
                f"voltage=0 spike={spike} evaluated={evaluated} "
                f"delivered={delivery}"
            )
    return "\n".join(records + [FOOTER, PASS]) + "\n"


class M05RTLTransactionReplayTests(unittest.TestCase):
    def test_real_transcript_contract_discards_all_eight_valid_prefix_rows(self):
        result = replay_log(successful_synthetic_log())
        self.assertEqual(result.status, 4)
        self.assertEqual(result.provisional_count, 8)
        self.assertEqual(result.drained_rows, 8)
        self.assertEqual(result.accepted_count, 0)
        self.assertTrue(result.first_spike)

    def test_missing_or_duplicate_terminal_markers_fail_closed(self):
        good = successful_synthetic_log()
        for bad in (
            good.replace(FOOTER + "\n", ""),
            good.replace(PASS + "\n", ""),
            good + FOOTER + "\n",
            good + PASS + "\n",
        ):
            with self.subTest(sample=bad[-100:]):
                with self.assertRaisesRegex(ValueError, "PASS|status"):
                    replay_log(bad)

    def test_bad_return_status_is_never_committable(self):
        with self.assertRaisesRegex(ValueError, "BAD_EXTERNAL"):
            replay_log(successful_synthetic_log().replace(
                "M05_RTL_FINAL status=4", "M05_RTL_FINAL status=0"
            ))

    def test_wrong_final_counts_are_rejected(self):
        good = successful_synthetic_log()
        for bad in (
            good.replace("provisional=8 committed=0\n", "provisional=7 committed=0\n"),
            good.replace("provisional=8 committed=0\n", "provisional=8 committed=2\n"),
        ):
            with self.assertRaises(ValueError):
                replay_log(bad)

    def test_missing_out_of_order_and_duplicate_rows_rejected(self):
        good = successful_synthetic_log()
        lines = good.splitlines()
        for variant in (
            "\n".join(lines[:7] + lines[8:]),
            "\n".join(lines[1:2] + lines[0:1] + lines[2:]),
            "\n".join([lines[0]] + lines),
        ):
            with self.assertRaises(ValueError):
                replay_log(variant)

    def test_no_initial_valid_spike_is_rejected(self):
        bad = successful_synthetic_log().replace(
            "tick=0 neuron=0 voltage=0 spike=1 evaluated=1",
            "tick=0 neuron=0 voltage=0 spike=0 evaluated=0"
        )
        with self.assertRaisesRegex(ValueError, "tick0"):
            replay_log(bad)

    def test_malformed_trace_fields_rejected_fail_closed(self):
        good = successful_synthetic_log()
        for bad in (
            good.replace("voltage=0 spike=1", "voltage=32768 spike=1"),
            good.replace("tick=0 neuron=0", "tick=1 neuron=0"),
            good.replace("delivered=1", "delivered=4097", 1),
        ):
            with self.assertRaises(ValueError):
                replay_log(bad)

    def test_rtl_fatal_wins_over_incorrect_pass_marker(self):
        good = successful_synthetic_log()
        with self.assertRaisesRegex(ValueError, "RTL_STRESS_FAIL"):
            replay_log(good + "Fatal: RTL_STRESS_FAIL invalid packet\n")

    def test_cli_replays_transcript_without_mutating_original(self):
        with tempfile.TemporaryDirectory(prefix="m05_synth_xsim_abort_") as td:
            log = Path(td) / "04_xsim.log"
            original = successful_synthetic_log()
            log.write_text(original)
            tool = ROOT / "scripts/m05_rtl_transaction_replay.py"
            result = subprocess.run(
                [sys.executable, str(tool), "--xsim-log", str(log)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("all failure rows discarded", result.stdout)
            self.assertEqual(log.read_text(), original)

    def test_cli_missing_real_log_does_not_invent_evidence(self):
        with tempfile.TemporaryDirectory(prefix="m05_synth_xsim_abort_") as td:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/m05_rtl_transaction_replay.py"),
                 "--xsim-log", str(Path(td) / "missing")],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: M05 RTL transactional replay:", result.stderr)

    def test_rtl_source_requires_prior_valid_prefix_and_late_bad_order(self):
        tb = (ROOT / "hls/m05_rolling/rtl_stress/"
              "tb_m05_rolling_axis_late_error.sv").read_text()
        for token in (
            "module tb_m05_rolling_axis_late_error",
            "external_sent == 0", "external_sent == 1",
            "{32'd5, 32'd0, 64'd0}", "{32'd5, 32'd0, 64'd4}",
            "{32'd5, 32'd0, 64'd3}",
            "external_sent < 3",
            "wait(trace_received == 8);",
            "status !== 32'd4",
            "M05_RTL_PROVISIONAL",
            "M05_RTL_FINAL status=4",
            "M05 REAL RTL AXIS LATE-ERROR",
            "no meaningful AXIS output backpressure",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tb)

    def test_runner_selects_new_test_and_python_gate_without_hls_resynthesis(self):
        sh = (ROOT / "scripts/run_m05_rolling_rtl_stress.sh").read_text()
        for token in (
            "MODE=\"late-error\"",
            "tb_m05_rolling_axis_late_error.sv",
            "tb_m05_rolling_axis_late_error",
            "m05_rolling_axis_late_error_snapshot",
            "m05_rtl_transaction_replay.py",
            "05_trace_commit.log",
            "Fatal: RTL_STRESS_FAIL",
            "source_sha256.txt",
            "m05_rtl_meminit.py",
        ):
            with self.subTest(token=token):
                self.assertIn(token, sh)
        self.assertNotIn("vitis-run --mode hls", sh)
        self.assertNotIn("program_hw_devices", sh)


if __name__ == "__main__":
    unittest.main()
