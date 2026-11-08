"""M05.9 synthetic-transcript/RTL-source tests; NO native Vitis proof.

Only the operator-run --multi-run generated-Verilog XSim simulator can
establish whether the unmodified HLS core works for two ap_start commands.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_rtl_multi_run_replay import parse_and_replay

FINAL0 = "M05_RTL_MULTI_FINAL run=0 status=4 rows=8 committed=0"
FINAL1 = "M05_RTL_MULTI_FINAL run=1 status=0 rows=20 committed=20"
PASS = ("PASS: M05 REAL RTL AXIS MULTI-RUN fail-then-success "
        "rows=8+20 committed=0+20; output_stalls=260")


def make_synthetic_log():
    lines = []
    for epoch, ticks in ((0, 4), (1, 10)):
        for t in range(ticks):
            for n in range(2):
                spike = int((epoch == 0 and t == 0 and n == 0)
                            or (epoch == 1 and t == 1 and n == 1))
                delivery = int((epoch == 0 and t == 0)
                               or (epoch == 1 and t == 1))
                lines.append(
                    f"M05_RTL_MULTI_ROW run={epoch} tick={t} neuron={n} "
                    f"voltage=0 spike={spike} evaluated={spike} delivered={delivery}"
                )
        lines.append(FINAL0 if epoch == 0 else FINAL1)
    lines.append(PASS)
    return "\n".join(lines) + "\n"


class M05RTLMultiRunTests(unittest.TestCase):
    def test_failed_then_success_replay_has_atomic_commit(self):
        outcome = parse_and_replay(make_synthetic_log())
        self.assertEqual(outcome.final_statuses, (4, 0))
        self.assertEqual((outcome.aborted_rows, outcome.accepted_rows), (8, 20))
        self.assertEqual(outcome.stalls, 260)

    def test_run0_must_have_nonzero_final_status(self):
        with self.assertRaisesRegex(ValueError, "status|completion"):
            parse_and_replay(make_synthetic_log().replace(
                "run=0 status=4", "run=0 status=0"
            ))

    def test_run1_cannot_succeed_with_nonzero_status(self):
        with self.assertRaisesRegex(ValueError, "status|completion"):
            parse_and_replay(make_synthetic_log().replace(
                "run=1 status=0", "run=1 status=4"
            ))

    def test_duplicate_or_out_of_order_session_completion_rejected(self):
        raw = make_synthetic_log()
        for bad in (raw + FINAL1 + "\n",
                    raw.replace(FINAL1, FINAL0 + "\n" + FINAL1),
                    raw.replace(FINAL0 + "\n", ""),
                    raw.replace(FINAL1 + "\n", "")):
            with self.subTest(bad=bad[-90:]):
                with self.assertRaises(ValueError):
                    parse_and_replay(bad)

    def test_run1_row_before_failed_status_rejected(self):
        lines = make_synthetic_log().splitlines()
        lines[8], lines[9] = lines[9], lines[8]
        with self.assertRaisesRegex(ValueError, "boundary|completion"):
            parse_and_replay("\n".join(lines))

    def test_row_missing_duplicate_and_wrong_tick_rejected(self):
        original = make_synthetic_log().splitlines()
        variants = (
            original[1:],
            original[:3] + original[2:],
            original[:10] + original[11:],
            [line.replace("run=1 tick=8 neuron=1", "run=1 tick=9 neuron=1")
             for line in original],
        )
        for lines in variants:
            with self.subTest(length=len(lines)):
                with self.assertRaises(ValueError):
                    parse_and_replay("\n".join(lines))

    def test_stale_recurrent_tick8_activity_is_rejected(self):
        log = make_synthetic_log()
        old = "run=1 tick=8 neuron=1 voltage=0 spike=0 evaluated=0 delivered=0"
        self.assertIn(old, log)
        for replacement in (
            "run=1 tick=8 neuron=1 voltage=0 spike=1 evaluated=1 delivered=1",
            "run=1 tick=8 neuron=1 voltage=0 spike=0 evaluated=1 delivered=0",
            "run=1 tick=8 neuron=1 voltage=0 spike=0 evaluated=0 delivered=1",
        ):
            with self.subTest(value=replacement):
                with self.assertRaisesRegex(ValueError, "oracle"):
                    parse_and_replay(log.replace(old, replacement))

    def test_run1_fresh_tick1_spike_is_required(self):
        raw = make_synthetic_log()
        self.assertIn("run=1 tick=1 neuron=1 voltage=0 spike=1 evaluated=1", raw)
        with self.assertRaisesRegex(ValueError, "oracle"):
            parse_and_replay(raw.replace(
                "run=1 tick=1 neuron=1 voltage=0 spike=1 evaluated=1",
                "run=1 tick=1 neuron=1 voltage=0 spike=0 evaluated=0"
            ))

    def test_truncated_or_overflow_rows_are_rejected(self):
        log = make_synthetic_log()
        for replacement in (
            log.replace("run=0 tick=0 neuron=0 voltage=0",
                        "run=0 tick=0 neuron=0 voltage=32768"),
            log.replace("run=1 tick=9 neuron=1 voltage=0",
                        "run=1 tick=9 neuron=1 voltage=0") +
                        "M05_RTL_MULTI_ROW run=1 tick=9 neuron=1 voltage=0 spike=0 evaluated=0 delivered=0\n",
            log.replace("run=0 tick=0 neuron=0 voltage=0",
                        "run=0 tick=0 neuron=0 voltage=0", 1).replace(
                            "delivered=1", "delivered=4097", 1),
        ):
            with self.assertRaises(ValueError):
                parse_and_replay(replacement)

    def test_fatal_or_premature_or_duplicate_pass_rejected(self):
        good = make_synthetic_log()
        for bad in (
            good + "Fatal: RTL_STRESS_FAIL injected\n",
            good + PASS + "\n",
            good.replace(PASS, ""),
            PASS + "\n" + good,
            good.replace("output_stalls=260", "output_stalls=0"),
        ):
            with self.subTest(sample=bad[-100:]):
                with self.assertRaises(ValueError):
                    parse_and_replay(bad)

    def test_malformed_transaction_marker_is_rejected(self):
        raw = make_synthetic_log()
        with self.assertRaisesRegex(ValueError, "unrecognized"):
            parse_and_replay(raw + "M05_RTL_MULTI_ROW run=BAD\n")

    def test_cli_success_on_synthetic_log_is_read_only(self):
        with tempfile.TemporaryDirectory(prefix="m05_synthetic_multirun_") as td:
            f = Path(td) / "04_xsim.log"
            data = make_synthetic_log()
            f.write_text(data)
            cmd = [sys.executable, str(ROOT / "scripts/m05_rtl_multi_run_replay.py"),
                   "--xsim-log", str(f)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("failed_run_discarded=8", proc.stdout)
            self.assertIn("next_run_accepted=20", proc.stdout)
            self.assertIn("wheel_t8_clean=1", proc.stdout)
            self.assertEqual(f.read_text(), data)

    def test_cli_missing_log_is_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="m05_synthetic_multirun_") as td:
            cmd = [sys.executable, str(ROOT / "scripts/m05_rtl_multi_run_replay.py"),
                   "--xsim-log", str(Path(td) / "no_xsim.log")]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("ERROR: M05 multi-run RTL trace replay", proc.stderr)

    def test_new_rtl_reuses_same_dut_without_reset_after_failure(self):
        s = (ROOT / "hls/m05_rolling/rtl_stress/"
             "tb_m05_rolling_axis_multi_run.sv").read_text()
        for anchor in (
            "module tb_m05_rolling_axis_multi_run;",
            "m05_rolling_replay dut (",
            "run_epoch = 1;",
            "M05_RTL_MULTI_ROW",
            "M05_RTL_MULTI_FINAL run=0 status=4 rows=8 committed=0",
            "M05_RTL_MULTI_FINAL run=1 status=0 rows=20 committed=20",
            "trace_received == 28",
            "observed_second_run_rows != 20",
            "M05 REAL RTL AXIS MULTI-RUN",
            "axi_write(`M05_ADDR_SYNAPSE_COUNT_DATA, 0)",
            "axi_write(`M05_ADDR_TICKS_DATA, 10)",
            "status !== 32'd0",
            "status !== 32'd4",
            "stalled_trace_prior",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, s)
        self.assertEqual(s.count("ap_rst_n = 1;"), 1)
        self.assertNotIn("ap_rst_n = 0;", s)

    def test_runner_includes_third_opt_in_case_and_replay_gate(self):
        s = (ROOT / "scripts/run_m05_rolling_rtl_stress.sh").read_text()
        for term in (
            '--multi-run', 'MODE="multi-run"',
            'tb_m05_rolling_axis_multi_run.sv',
            'm05_rolling_axis_multi_run_snapshot',
            'PASS: M05 REAL RTL AXIS MULTI-RUN',
            'm05_rtl_multi_run_replay.py',
            '05_trace_commit.log',
            'm05_rtl_meminit.py',
            'source_sha256.txt',
        ):
            with self.subTest(term=term):
                self.assertIn(term, s)
        self.assertNotIn("program_hw_devices", s)
        self.assertNotIn("rm -rf", s)


if __name__ == "__main__":
    unittest.main()
