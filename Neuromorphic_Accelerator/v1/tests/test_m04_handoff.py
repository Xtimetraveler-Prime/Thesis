"""M04.5 host-only numeric admission envelope / M05 handoff tests.

No HLS tools, board, JTAG, bus protocol, queue, RTL or physical timing used.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m02_types import Network, Neuron, Synapse, InputCurrent
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m04_profile import (
    MAX_U32, MAX_U64, MAX_ARRIVALS_PER_TICK, M04AdmissionError,
    preflight_known_m04_workload, prove_fixed_width_envelope,
)


class M045RequirementsTests(unittest.TestCase):
    def test_integer_bound_proof_all_supported_widths(self):
        for bits in range(4, 33):
            with self.subTest(state_bits=bits):
                self.assertTrue(prove_fixed_width_envelope(bits, 4096))
                self.assertTrue(prove_fixed_width_envelope(bits, 0))
        self.assertFalse(prove_fixed_width_envelope(33, 4096))
        self.assertFalse(prove_fixed_width_envelope(16, 4097))
        self.assertFalse(prove_fixed_width_envelope(True, 1))
        self.assertFalse(prove_fixed_width_envelope(16, -1))
        # Independent numerical extremal proof at W32/u32 max.
        self.assertGreaterEqual(-(1 << 31) * MAX_U32, -(1 << 63))
        self.assertLess((1 << 31) * 4096 + (1 << 32), 1 << 63)

    def test_4096_cancelling_events_count_before_sum(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        inputs = tuple(
            event for _ in range(2048)
            for event in (InputCurrent(0, 0, 32767), InputCurrent(0, 0, -32768))
        )
        report = preflight_known_m04_workload(net, inputs, ticks=1)
        self.assertEqual(report.max_arrivals_per_tick, 4096)
        self.assertEqual(report.max_abs_aggregate, 2048)
        self.assertEqual(report.full_m02_trace, evaluate_dense(net, inputs, ticks=1))
        self.assertEqual(report.full_m02_trace.voltage_rows, ((-2048,),))
        self.assertEqual(report.full_m02_trace.spike_rows, ((),))

    def test_4096_positive_events_single_clamp_and_spike(self):
        net = Network((Neuron(threshold=5, reset_v=-2),), state_bits=16)
        inputs = tuple(InputCurrent(0, 0, 32767) for _ in range(4096))
        report = preflight_known_m04_workload(net, inputs, ticks=1)
        self.assertEqual(report.max_arrivals_per_tick, 4096)
        self.assertEqual(report.max_abs_aggregate, 4096 * 32767)
        self.assertEqual(report.full_m02_trace, evaluate_dense(net, inputs, ticks=1))
        self.assertEqual(report.full_m02_trace.voltage_rows, ((-2,),))
        self.assertEqual(report.full_m02_trace.spike_rows, ((0,),))

    def test_4097_external_arrivals_explicitly_rejected(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        inputs = (InputCurrent(0, 0, 0) for _ in range(4097))
        with self.assertRaisesRegex(M04AdmissionError, "more than 4096"):
            preflight_known_m04_workload(net, inputs, ticks=1)

    def test_4097_parallel_delayed_arrivals_rejected(self):
        # External count is only 1 at t0. All 4097 delayed edges arrive at t1.
        net = Network(
            (Neuron(threshold=5),),
            tuple(Synapse(0, 0, 1, 1) for _ in range(4097)),
            state_bits=16,
        )
        with self.assertRaisesRegex(M04AdmissionError, "tick 1"):
            preflight_known_m04_workload(net, (InputCurrent(0, 0, 5),), ticks=2)

    def test_positive_delay_recurrence_and_finite_horizon(self):
        net = Network(
            (Neuron(threshold=5, reset_v=0),),
            (Synapse(0, 0, 5, 2), Synapse(0, 0, 3, 7)),
            state_bits=16,
        )
        inputs = (InputCurrent(0, 0, 5),)
        report = preflight_known_m04_workload(net, inputs, ticks=3)
        self.assertEqual(report.full_m02_trace, evaluate_dense(net, inputs, ticks=3))
        self.assertEqual(report.full_m02_trace.emitted_spikes, ((0, 0), (2, 0)))
        self.assertEqual(report.max_arrivals_per_tick, 1)

    def test_m02_legal_unbounded_decay_denominator_rejected_by_profile(self):
        net = Network(
            (Neuron(threshold=5),), decay_num=0, decay_den=1 << 32, state_bits=16
        )
        self.assertEqual(evaluate_dense(net, (), ticks=1).voltage_rows, ((0,),))
        with self.assertRaisesRegex(M04AdmissionError, "unsigned 32-bit"):
            preflight_known_m04_workload(net, (), ticks=1)

    def test_other_m02_widths_require_separate_compiled_profile(self):
        for bits in (4, 8, 32):
            with self.subTest(state_bits=bits):
                net = Network((Neuron(threshold=1),), state_bits=bits)
                self.assertEqual(evaluate_dense(net, (), ticks=1).voltage_rows, ((0,),))
                with self.assertRaisesRegex(M04AdmissionError, "state_bits=16"):
                    preflight_known_m04_workload(net, (), ticks=1)

    def test_timestamp_64bit_profile_overflow_rejected_before_replay(self):
        net = Network((Neuron(threshold=1),), state_bits=16)
        with self.assertRaisesRegex(M04AdmissionError, "tick exceeds"):
            preflight_known_m04_workload(net, (), ticks=MAX_U64 + 2)


if __name__ == "__main__":
    unittest.main()
