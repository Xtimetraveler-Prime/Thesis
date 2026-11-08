"""M05.5 native-only end-of-run trace acceptance and toy backpressure tests.

This does NOT drive a real AXIS interface, AXI-Lite register, DMA, interrupt,
RTL simulator or KV260. The single-slot queue tests abstract handshake safety
and atomic consumer acceptance, NOT achieved FPGA flow control.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_trace_commit import (
    MAX_TRACE_ROWS, RollingTraceCommitGate, RollingTraceRow,
)


def row(tick: int, neuron_id: int, *,
        voltage: int = 0, spike: int = 0, evaluated: int = 0,
        deliveries: int = 0) -> RollingTraceRow:
    return RollingTraceRow(tick, neuron_id, voltage, spike, evaluated, deliveries)


class M05TraceCommitTests(unittest.TestCase):
    def test_successful_run_is_invisible_until_final_status(self):
        gate = RollingTraceCommitGate(2, 2)
        for entry in (row(0, 0),
                      row(0, 1), row(1, 0), row(1, 1)):
            gate.offer_row(entry)
        self.assertTrue(gate.has_uncommitted_rows)
        self.assertEqual(gate.received_count, 4)
        result = gate.complete(0)
        self.assertTrue(result.accepted)
        self.assertEqual(len(result.rows), 4)
        self.assertIsNone(result.reason)
        self.assertFalse(gate.has_uncommitted_rows)
        self.assertTrue(gate.is_finished)

    def test_late_overflow_discards_all_earlier_ticks(self):
        gate = RollingTraceCommitGate(1, 64)
        for t in range(50):
            gate.offer_row(row(t, 0, evaluated=1))
        result = gate.complete(5)
        self.assertFalse(result.accepted)
        self.assertEqual(result.rows, ())
        self.assertEqual(result.drained_rows, 50)
        self.assertIn("nonzero", result.reason)
        self.assertFalse(gate.has_uncommitted_rows)

    def test_early_bad_shape_does_not_accept_empty_trace(self):
        gate = RollingTraceCommitGate(1, 1)
        result = gate.complete(1)
        self.assertFalse(result.accepted)
        self.assertEqual(result.rows, ())

    def test_incomplete_success_is_rejected(self):
        gate = RollingTraceCommitGate(2, 2)
        gate.offer_row(row(0, 0))
        gate.offer_row(row(0, 1))
        result = gate.complete(0)
        self.assertFalse(result.accepted)
        self.assertIn("incomplete", result.reason)
        self.assertEqual(result.rows, ())

    def test_duplicate_and_out_of_order_ids_are_rejected(self):
        for bad in (row(0, 0), row(1, 1), row(0, 2)):
            with self.subTest(bad=bad):
                gate = RollingTraceCommitGate(2, 1)
                gate.offer_row(row(0, 0))
                gate.offer_row(bad)
                result = gate.complete(0)
                self.assertFalse(result.accepted)
                self.assertEqual(result.rows, ())

    def test_extra_trace_is_drained_but_not_stored(self):
        gate = RollingTraceCommitGate(1, 1)
        gate.offer_row(row(0, 0))
        gate.offer_row(row(0, 0))
        self.assertFalse(gate.has_uncommitted_rows)
        result = gate.complete(0)
        self.assertFalse(result.accepted)
        self.assertEqual(result.drained_rows, 2)
        self.assertIn("more trace rows", result.reason)

    def test_tick_delivery_counter_must_match_across_neurons(self):
        gate = RollingTraceCommitGate(3, 1)
        gate.offer_row(row(0, 0, deliveries=3))
        gate.offer_row(row(0, 1, deliveries=2))
        gate.offer_row(row(0, 2, deliveries=3))
        result = gate.complete(0)
        self.assertFalse(result.accepted)
        self.assertIn("disagrees", result.reason)

    def test_invalid_widths_and_spike_on_skipped_cell_are_rejected(self):
        invalid = (row(0, 0, voltage=32768),
                   row(0, 0, voltage=-32769),
                   row(0, 0, spike=2),
                   row(0, 0, evaluated=2),
                   row(0, 0, spike=1, evaluated=0),
                   row(0, 0, deliveries=4097),
                   row(0, 0, deliveries=-1),
                   RollingTraceRow(0, 0, 0, True, 1, 0),
                   RollingTraceRow(0, 0, 0, 0, 0, "0"))
        for entry in invalid:
            with self.subTest(entry=entry):
                gate = RollingTraceCommitGate(1, 1)
                gate.offer_row(entry)
                self.assertFalse(gate.complete(0).accepted)

    def test_unknown_or_boolean_final_status_is_fail_closed(self):
        for status in (-1, 7, 12345, True, "0"):
            with self.subTest(status=status):
                gate = RollingTraceCommitGate(1, 1)
                gate.offer_row(row(0, 0))
                result = gate.complete(status)
                self.assertFalse(result.accepted)
                self.assertEqual(result.rows, ())

    def test_abort_on_timeout_discards_partial_trace(self):
        gate = RollingTraceCommitGate(1, 64)
        gate.offer_row(row(0, 0))
        result = gate.abort("DMA timeout while receiving row 2")
        self.assertFalse(result.accepted)
        self.assertIsNone(result.status)
        self.assertIn("DMA timeout", result.reason)
        self.assertEqual(result.rows, ())

    def test_receiver_cannot_be_reused_after_completion(self):
        gate = RollingTraceCommitGate(1, 1)
        gate.offer_row(row(0, 0))
        gate.complete(0)
        with self.assertRaises(RuntimeError):
            gate.offer_row(row(0, 0))
        with self.assertRaises(RuntimeError):
            gate.complete(0)
        with self.assertRaises(RuntimeError):
            gate.abort()

    def test_reject_shape_without_large_allocation(self):
        for args in ((0, 2), (1025, 2), (1, 0), (1, 65),
                     (True, 2), (1, True)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    RollingTraceCommitGate(*args)

    def test_maximum_65536_trace_row_bounded_staging(self):
        gate = RollingTraceCommitGate(1024, 64)
        self.assertEqual(gate.expected_rows, MAX_TRACE_ROWS)
        for tick in range(64):
            for nid in range(1024):
                gate.offer_row(row(tick, nid, evaluated=0,
                                   deliveries=4096 if tick == 63 else 0))
        result = gate.complete(0)
        self.assertTrue(result.accepted)
        self.assertEqual(result.drained_rows, MAX_TRACE_ROWS)
        self.assertEqual(len(result.rows), MAX_TRACE_ROWS)

    def test_single_slot_ready_valid_model_stalls_producer_without_loss(self):
        """Deterministic single-beat FIFO model; no RTL/real AXI signals."""
        gate = RollingTraceCommitGate(2, 5)
        records = [row(t, n) for t in range(5) for n in range(2)]
        fifo = deque()
        produced = consumed = cycles = stalled = 0
        while consumed < len(records):
            cycles += 1
            self.assertLess(cycles, 100)
            consumer_ready = cycles % 4 in (0, 3)
            # Consumer may stall while one beat remains queued; producer
            # must hold its data until the single slot becomes available.
            if fifo and consumer_ready:
                gate.offer_row(fifo.popleft())
                consumed += 1
            if produced < len(records):
                if len(fifo) < 1:
                    fifo.append(records[produced])
                    produced += 1
                else:
                    stalled += 1
            self.assertLessEqual(len(fifo), 1)
        self.assertGreater(stalled, 0)
        self.assertEqual(gate.received_count, 10)
        self.assertTrue(gate.complete(0).accepted)

    def test_single_slot_model_late_abort_cannot_publish_prefix(self):
        gate = RollingTraceCommitGate(1, 4)
        fifo = deque()
        for tick in range(3):
            self.assertFalse(fifo)
            fifo.append(row(tick, 0))
            gate.offer_row(fifo.popleft())
        self.assertEqual(gate.received_count, 3)
        self.assertFalse(gate.complete(4).accepted)

    def test_full_python_receiver_accepts_native_rolling_cli_output(self):
        """Real native C++ kernel stdout parser, not live DMA/AXIS evidence."""
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            raise RuntimeError("native C++ compiler is mandatory")
        with tempfile.TemporaryDirectory(prefix="m05_commit_cli_") as td:
            binary = str(Path(td) / "rolling")
            built = subprocess.run(
                [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                 "-Werror", "-pedantic", "-Wno-unknown-pragmas",
                 str(ROOT / "hls/m04_lif_eval/m04_eval.cpp"),
                 str(ROOT / "hls/m05_rolling/m05_rolling.cpp"),
                 str(ROOT / "hls/m05_rolling/m05_rolling_host_cli.cpp"),
                 "-o", binary], text=True, capture_output=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            proc = subprocess.run(
                [binary], input="1 0 1 3 1 1\n0 0 5 0\n0 0 5\n",
                text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            lines = proc.stdout.splitlines()
            status, count = map(int, lines[0].split())
            self.assertEqual((status, count), (0, 3))
            gate = RollingTraceCommitGate(1, 3)
            for line in lines[1:]:
                gate.offer_row(RollingTraceRow(*map(int, line.split())))
            result = gate.complete(status)
            self.assertTrue(result.accepted)
            self.assertEqual([r.spike for r in result.rows], [1, 0, 0])
            self.assertEqual([r.delivered_count for r in result.rows],
                             [1, 0, 0])


if __name__ == "__main__":
    unittest.main()
