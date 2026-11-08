"""M03 exact idle-elision lemma, adversarial cases and differential tests."""
import random
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m02_types import (
    InputCurrent, Network, Neuron, Synapse,
)
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events
from neuromorphic_accelerator_v1.m03_sparse_reference import evaluate_exact_sparse


class SparseEquivalenceTests(unittest.TestCase):
    def test_exact_idle_zero_skip_and_nonzero_memory(self):
        # Neuron 1 is permanently quiet; neuron 0 must still be evaluated
        # after a subthreshold input because previous voltage remains nonzero.
        net = Network((Neuron(threshold=7), Neuron(threshold=7)),
                      decay_num=1, decay_den=2, state_bits=8)
        events = (InputCurrent(0, 0, 4),)
        s = evaluate_exact_sparse(net, events, ticks=6)
        self.assertEqual(s.trace, evaluate_dense(net, events, ticks=6))
        self.assertEqual(s.trace, evaluate_events(net, events, ticks=6))
        self.assertEqual(s.trace.voltage_rows,
                         ((4, 0), (2, 0), (1, 0), (0, 0), (0, 0), (0, 0)))
        self.assertEqual(s.evaluated_ids_by_tick,
                         ((0,), (0,), (0,), (0,), (), ()))
        self.assertEqual(s.evaluation_count, 4)

    def test_autonomous_bias_never_incorrectly_skipped(self):
        net = Network((Neuron(bias=3, threshold=5), Neuron(threshold=5)),
                      state_bits=8)
        s = evaluate_exact_sparse(net, (), ticks=5)
        self.assertEqual(s.trace, evaluate_dense(net, (), ticks=5))
        self.assertEqual(s.evaluated_ids_by_tick,
                         ((0,), (0,), (0,), (0,), (0,)))
        self.assertEqual(s.trace.emitted_spikes, ((1, 0), (3, 0)))

    def test_negative_bias_reset_and_refractory_not_assumed(self):
        net = Network((Neuron(initial_v=-3, bias=-1, threshold=7, reset_v=-2),
                       Neuron(threshold=2)),
                      (Synapse(1, 0, -3, 1),), state_bits=8,
                      decay_num=1, decay_den=2)
        events = (InputCurrent(0, 1, 2),)
        s = evaluate_exact_sparse(net, events, ticks=5)
        self.assertEqual(s.trace, evaluate_dense(net, events, ticks=5))
        self.assertEqual(s.trace, evaluate_events(net, events, ticks=5))
        self.assertTrue(all(0 in row for row in s.evaluated_ids_by_tick))

    def test_duplicate_signed_currents_can_cancel_and_still_be_visited(self):
        net = Network((Neuron(threshold=7),), state_bits=8)
        inputs = (InputCurrent(0, 0, 10), InputCurrent(0, 0, -10),
                  InputCurrent(1, 0, 0))
        s = evaluate_exact_sparse(net, inputs, ticks=3)
        self.assertEqual(s.trace, evaluate_dense(net, inputs, ticks=3))
        self.assertEqual(s.evaluated_ids_by_tick, ((0,), (0,), ()))
        self.assertEqual(s.trace.emitted_spikes, ())

    def test_delayed_recurrent_loop_and_spike_fanout_accounting(self):
        net = Network(
            (Neuron(threshold=5), Neuron(threshold=4)),
            (Synapse(0, 1, 4, 2), Synapse(1, 0, 5, 1)),
            state_bits=8)
        s = evaluate_exact_sparse(net, (InputCurrent(0, 0, 5),), ticks=4)
        self.assertEqual(s.trace, evaluate_dense(
            net, (InputCurrent(0, 0, 5),), ticks=4))
        self.assertEqual(s.trace.emitted_spikes, ((0, 0), (2, 1), (3, 0)))
        self.assertEqual(s.traversed_synapses_by_tick, (1, 0, 1, 1))
        self.assertEqual(s.fanout_per_firing_by_tick,
                         (((0, 1),), (), ((1, 1),), ((0, 1),)))

    def test_zero_fanout_and_no_input_updates_zero(self):
        net = Network(tuple(Neuron(threshold=8) for _ in range(8)),
                      state_bits=8)
        s = evaluate_exact_sparse(net, (), ticks=12)
        self.assertEqual(s.evaluation_count, 0)
        self.assertEqual(s.trace, evaluate_dense(net, (), ticks=12))
        self.assertEqual(sum(map(len, s.trace.spike_rows)), 0)

    def test_pending_delivery_backlog_is_accounted_not_hardware_fifo(self):
        net = Network((Neuron(threshold=5), Neuron(threshold=5)),
                      (Synapse(0, 1, 5, 2),), state_bits=8)
        external = (InputCurrent(0, 0, 5), InputCurrent(3, 1, 1))
        sparse = evaluate_exact_sparse(net, external, ticks=4)
        self.assertEqual(sparse.trace, evaluate_dense(net, external, ticks=4))
        self.assertEqual(sparse.deliveries_by_tick, (1, 0, 1, 1))
        # Two future external currents initially pending. The tick-0
        # spike creates one tick-2 synaptic delivery, so count stays 2.
        self.assertEqual(sparse.pending_future_deliveries_by_tick, (2, 2, 1, 0))
        self.assertEqual(sparse.peak_pending_deliveries, 2)

    def test_seeded_random_general_m02_contract_differential(self):
        rng = random.Random(19850519)
        for case in range(65):
            n = rng.randint(1, 12)
            neuron_params = tuple(
                Neuron(initial_v=rng.randint(-8, 8),
                       bias=rng.randint(-4, 4),
                       threshold=rng.randint(1, 20),
                       reset_v=rng.randint(-4, 0))
                for _ in range(n)
            )
            edges = tuple(Synapse(rng.randrange(n), rng.randrange(n),
                                  rng.randint(-10, 10), rng.randint(1, 4))
                          for _ in range(rng.randint(0, 22)))
            external = tuple(InputCurrent(rng.randrange(12), rng.randrange(n),
                                          rng.randint(-12, 12))
                             for _ in range(rng.randint(0, 40)))
            net = Network(neuron_params, edges, state_bits=8,
                          decay_num=rng.randint(0, 5), decay_den=5)
            with self.subTest(case=case):
                expected = evaluate_dense(net, external, ticks=12)
                sparse = evaluate_exact_sparse(net, external, ticks=12)
                self.assertEqual(expected, sparse.trace)
                self.assertEqual(expected, evaluate_events(net, external, ticks=12))
                self.assertLessEqual(sparse.evaluation_count, n * 12)
                self.assertEqual(
                    sum(sparse.traversed_synapses_by_tick),
                    sum(len([e for e in edges if e.pre == pre])
                        for fired in sparse.trace.spike_rows for pre in fired)
                )

if __name__ == "__main__":
    unittest.main()
