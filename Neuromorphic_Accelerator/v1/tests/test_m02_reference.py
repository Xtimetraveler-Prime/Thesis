"""M02 independent hard-expected LIF fixtures and two-implementation differential tests.

All tests are PC-only, no Vivado, no hardware, no access to sealed MNIST TEST.
"""
import hashlib
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m02_types import (
    InputCurrent, Network, Neuron, Synapse, ReferenceTrace, validate,
)
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events


def assert_both(test, network, events, ticks, *, states, spikes):
    a = evaluate_dense(network, events, ticks=ticks)
    b = evaluate_events(network, events, ticks=ticks)
    test.assertEqual(a, b)
    test.assertEqual(a.voltage_rows, states)
    test.assertEqual(a.spike_rows, spikes)
    return a


class M02LifReferenceTests(unittest.TestCase):
    def test_hand_expected_threshold_equality_reset_and_leak(self):
        net = Network((Neuron(threshold=5),), decay_num=1, decay_den=2, state_bits=8)
        events = (InputCurrent(0, 0, 3),
                  InputCurrent(1, 0, 4),
                  InputCurrent(2, 0, 2))
        out = assert_both(
            self, net, events, 4,
            states=((3,), (0,), (2,), (1,)),
            spikes=((), (0,), (), ()),
        )
        self.assertEqual(out.emitted_spikes, ((1, 0),))

    def test_hand_expected_negative_leak_truncates_toward_zero(self):
        net = Network(
            (Neuron(initial_v=-3, bias=-2, threshold=6),),
            decay_num=1, decay_den=2, state_bits=8)
        assert_both(self, net, (), 3,
                    states=((-3,), (-3,), (-3,)),
                    spikes=((), (), ()))
        # Python // would produce -2 from -3/2, but this contract produces -1.
        net2 = Network((Neuron(initial_v=-3, threshold=5),),
                       decay_num=1, decay_den=2, state_bits=8)
        assert_both(self, net2, (), 3,
                    states=((-1,), (0,), (0,)), spikes=((), (), ()))

    def test_hand_expected_bias_causes_spike_without_events(self):
        net = Network((Neuron(bias=3, threshold=5),),
                      decay_num=1, decay_den=1, state_bits=8)
        trace = assert_both(
            self, net, (), 4,
            states=((3,), (0,), (3,), (0,)),
            spikes=((), (0,), (), (0,)))
        self.assertEqual(trace.emitted_spikes, ((1, 0), (3, 0)))

    def test_saturation_before_threshold_and_negative_range(self):
        net = Network((Neuron(threshold=127), Neuron(initial_v=-120, threshold=6)),
                      state_bits=8)
        assert_both(self, net,
                    (InputCurrent(0, 0, 127), InputCurrent(0, 0, 127),
                     InputCurrent(0, 1, -120)), 1,
                    states=((0, -128),),
                    spikes=((0,),))

    def test_duplicate_currents_are_summed_before_saturation(self):
        net = Network((Neuron(threshold=110),),
                      state_bits=8)
        x = (InputCurrent(0, 0, 100),
             InputCurrent(0, 0, 100),
             InputCurrent(0, 0, -100))
        assert_both(self, net, x, 2, states=((100,), (100,)),
                    spikes=((), ()))
        # Permuting within-tick events cannot alter exact sum.
        for perm in ((x[2], x[1], x[0]), (x[1], x[0], x[2])):
            self.assertEqual(evaluate_dense(net, x, ticks=2),
                             evaluate_events(net, perm, ticks=2))

    def test_negative_weight_and_parallel_edges(self):
        net = Network(
            (Neuron(threshold=3), Neuron(initial_v=1, threshold=30)),
            (Synapse(0, 1, 20, 1), Synapse(0, 1, -7, 1)),
            decay_num=1, decay_den=1, state_bits=8)
        events = (InputCurrent(0, 0, 3),)
        assert_both(self, net, events, 3,
                    states=((0, 1), (0, 14), (0, 14)),
                    spikes=((0,), (), ()))

    def test_hand_expected_positive_delays_and_recurrence(self):
        net = Network(
            (Neuron(threshold=5), Neuron(threshold=4)),
            (Synapse(0, 1, 4, 2), Synapse(1, 0, 5, 1)),
            decay_num=1, decay_den=1, state_bits=8)
        assert_both(self, net, (InputCurrent(0, 0, 5),), 4,
                    states=((0, 0), (0, 0), (0, 0), (0, 0)),
                    spikes=((0,), (), (1,), (0,)))

    def test_self_recurrent_synapse_requires_positive_delay(self):
        net = Network((Neuron(threshold=5),),
                      (Synapse(0, 0, 5, 1),), state_bits=8)
        assert_both(self, net, (InputCurrent(0, 0, 5),), 4,
                    states=((0,), (0,), (0,), (0,)),
                    spikes=((0,), (0,), (0,), (0,)))

    def test_last_tick_event_and_future_delivery_beyond_horizon(self):
        net = Network((Neuron(threshold=5), Neuron(threshold=5)),
                      (Synapse(0, 1, 5, 2),), state_bits=8)
        assert_both(self, net, (InputCurrent(2, 0, 5),), 3,
                    states=((0, 0), (0, 0), (0, 0)),
                    spikes=((), (), (0,)))

    def test_input_order_and_duplicate_spike_emission_never_changes_trace(self):
        net = Network(
            (Neuron(threshold=7), Neuron(threshold=6)),
            (Synapse(0, 1, 2, 1), Synapse(0, 1, 2, 1)), state_bits=8)
        items = (InputCurrent(1, 1, 1), InputCurrent(0, 0, 7),
                 InputCurrent(0, 0, -2), InputCurrent(0, 0, 2))
        a = evaluate_dense(net, items, ticks=4)
        self.assertEqual(a, evaluate_events(net, tuple(reversed(items)), ticks=4))
        self.assertEqual(a, evaluate_dense(net, tuple(reversed(items)), ticks=4))
        self.assertEqual(a.emitted_spikes, ((0, 0),))

    def test_decay_zero_and_one(self):
        net0 = Network((Neuron(initial_v=5, threshold=7),),
                       decay_num=0, decay_den=4, state_bits=8)
        assert_both(self, net0, (), 3,
                    states=((0,), (0,), (0,)), spikes=((), (), ()))
        net1 = Network((Neuron(initial_v=5, threshold=7),),
                       decay_num=4, decay_den=4, state_bits=8)
        assert_both(self, net1, (), 3,
                    states=((5,), (5,), (5,)), spikes=((), (), ()))

    def test_large_simultaneous_inputs_sum_unbounded_before_clamp(self):
        net = Network((Neuron(threshold=100),), state_bits=8)
        events = tuple([InputCurrent(0, 0, 127)] * 20 +
                       [InputCurrent(0, 0, -127)] * 19)
        assert_both(self, net, events, 1,
                    states=((0,),), spikes=((0,),))

    def test_validate_rejects_bad_neural_contract(self):
        good = Network((Neuron(threshold=5),), state_bits=8)
        cases = [
            (Network(()), (), 1),
            (good, (), True),
            (good, (), 0),
            (Network((Neuron(threshold=5),), state_bits=3), (), 1),
            (Network((Neuron(threshold=5),), state_bits=33), (), 1),
            (Network((Neuron(initial_v=128, threshold=5),), state_bits=8), (), 1),
            (Network((Neuron(bias=True, threshold=5),), state_bits=8), (), 1),
            (Network((Neuron(threshold=0),), state_bits=8), (), 1),
            (Network((Neuron(threshold=5, reset_v=5),), state_bits=8), (), 1),
            (Network((Neuron(threshold=5),), decay_num=2, decay_den=1, state_bits=8), (), 1),
            (Network((Neuron(threshold=5),), decay_num=1, decay_den=0, state_bits=8), (), 1),
            (Network((Neuron(threshold=5),), (Synapse(0, 0, 1, 0),), state_bits=8), (), 1),
            (Network((Neuron(threshold=5),), (Synapse(0, 1, 1, 1),), state_bits=8), (), 1),
            (Network((Neuron(threshold=5),), (Synapse(0, 0, True, 1),), state_bits=8), (), 1),
            (good, (InputCurrent(1, 0, 1),), 1),
            (good, (InputCurrent(-1, 0, 1),), 1),
            (good, (InputCurrent(0, True, 1),), 1),
            (good, (InputCurrent(0, 0, 128),), 1),
            (good, (InputCurrent(0, 0, 1.0),), 1),
            (good, ((0, 0, 1),), 1),
        ]
        for network, inputs, ticks in cases:
            with self.subTest(network=network, inputs=inputs, ticks=ticks):
                with self.assertRaises(ValueError):
                    evaluate_dense(network, inputs, ticks=ticks)
                with self.assertRaises(ValueError):
                    evaluate_events(network, inputs, ticks=ticks)

    def test_random_recurrent_and_feedforward_crosscheck(self):
        rng = random.Random(20261107)
        for case in range(50):
            n = rng.randint(1, 7)
            count = rng.randint(0, 22)
            nodes = tuple(
                Neuron(initial_v=rng.randint(-10, 8),
                       bias=rng.randint(-3, 4),
                       threshold=rng.randint(2, 28),
                       reset_v=rng.choice((-4, -1, 0)))
                for _ in range(n)
            )
            edges = tuple(Synapse(rng.randrange(n), rng.randrange(n),
                                  rng.randint(-8, 8), rng.randint(1, 4))
                          for _ in range(count))
            external = tuple(InputCurrent(rng.randrange(15), rng.randrange(n),
                                          rng.randint(-12, 12))
                             for _ in range(rng.randint(0, 70)))
            network = Network(nodes, edges, decay_num=rng.randrange(6),
                              decay_den=5, state_bits=8)
            with self.subTest(case=case):
                x = evaluate_dense(network, external, ticks=15)
                y = evaluate_events(network, external, ticks=15)
                self.assertEqual(x, y)
                self.assertEqual(len(x.voltage_rows), 15)
                self.assertTrue(all(len(row) == n for row in x.voltage_rows))
                self.assertTrue(all(tuple(sorted(row)) == row for row in x.spike_rows))

    def test_reference_output_reproducibility_sha_and_no_mutation(self):
        net = Network((Neuron(threshold=3), Neuron(threshold=3, bias=1)),
                      (Synapse(0, 1, 2, 1),), state_bits=8)
        events = [InputCurrent(0, 0, 3), InputCurrent(1, 1, -1)]
        before = tuple(events)
        a = evaluate_dense(net, events, ticks=7)
        b = evaluate_events(net, events, ticks=7)
        self.assertEqual(a, b)
        self.assertEqual(tuple(events), before)
        raw = json.dumps(asdict(a), separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         hashlib.sha256(raw).hexdigest())
        self.assertEqual(a, evaluate_dense(net, events, ticks=7))

    def test_input_generator_accepted_once_per_evaluator(self):
        net = Network((Neuron(threshold=3),), state_bits=8)
        items = (InputCurrent(0, 0, 2), InputCurrent(1, 0, 1))
        self.assertEqual(evaluate_dense(net, iter(items), ticks=3),
                         evaluate_events(net, iter(items), ticks=3))


if __name__ == "__main__":
    unittest.main()
