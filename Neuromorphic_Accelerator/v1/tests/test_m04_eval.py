"""M04 host-native neuron datapath proof vs accepted M02 rev1.

C++ is compiled with the host compiler, never Vitis synthesis. Real M02 dense
and independent event evaluator are both used for cross-tick tests.
"""
from __future__ import annotations

import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron, Synapse


class M04NativeEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++") or shutil.which("c++")
        if compiler is None:
            raise RuntimeError("M04 requires a native C++17 compiler; tests cannot silently skip")
        cls._build = tempfile.TemporaryDirectory(prefix="m04_host_eval_")
        cls.binary = str(Path(cls._build.name) / "m04_host_cli")
        src = ROOT / "hls" / "m04_lif_eval"
        subprocess.run(
            [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
             str(src / "m04_eval.cpp"), str(src / "m04_host_cli.cpp"), "-o", cls.binary],
            check=True, capture_output=True, text=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls._build.cleanup()

    def run_requests(self, requests):
        payload = "".join(" ".join(map(str, row)) + "\n" for row in requests)
        proc = subprocess.run([self.binary], input=payload, capture_output=True, text=True, check=True)
        rows = [tuple(map(int, line.split())) for line in proc.stdout.splitlines()]
        self.assertEqual(len(rows), len(requests), proc.stderr)
        for req, out in zip(requests, rows):
            self.assertEqual(out[:2], (req[0], req[2]))  # logical ID and tick echo
        return rows

    @staticmethod
    def req(*, old=0, current=0, bias=0, threshold=7, reset=0,
            bits=16, num=1, den=1, neuron=0, count=1, tick=0):
        return (neuron, count, tick, old, current, bias, threshold, reset, bits, num, den)

    def test_negative_decay_truncates_toward_zero(self):
        rows = [self.req(old=-3, num=1, den=2),
                self.req(old=-7, num=2, den=3),
                self.req(old=7, num=2, den=3)]
        got = self.run_requests(rows)
        self.assertEqual([x[2:] for x in got], [(0, -1, 0), (0, -4, 0), (0, 4, 0)])

    def test_inclusive_threshold_and_reset(self):
        self.assertEqual(self.run_requests([self.req(old=5, threshold=5, reset=-2)])[0][2:], (0, -2, 1))
        self.assertEqual(self.run_requests([self.req(old=4, threshold=5, reset=-2)])[0][2:], (0, 4, 0))

    def test_signed_saturation_and_extreme_aggregate(self):
        rows = [self.req(old=1, current=30, threshold=7, bits=4),
                self.req(old=-1, current=-30, threshold=7, bits=4),
                self.req(old=0, current=9223372036854775807, threshold=7, bits=4),
                self.req(old=0, current=-9223372036854775808, threshold=7, bits=4)]
        self.assertEqual([x[2:] for x in self.run_requests(rows)],
                         [(0, 0, 1), (0, -8, 0), (0, 0, 1), (0, -8, 0)])

    def test_aggregate_before_single_clamp(self):
        # +7,+7,-7 must sum to +7 before ONE clamp. Per-event clamping changes it.
        req = self.req(bits=4, threshold=7, current=sum([7, 7, -7]))
        self.assertEqual(self.run_requests([req])[0][2:], (0, 0, 1))
        self.assertEqual(self.run_requests([self.req(current=0, bias=-4)])[0][2:], (0, -4, 0))

    def test_bias_only_autonomous_spike(self):
        inputs = [self.req(old=0, bias=3, threshold=5, tick=0),
                  self.req(old=3, bias=3, threshold=5, tick=1),
                  self.req(old=0, bias=3, threshold=5, tick=2)]
        self.assertEqual([x[2:] for x in self.run_requests(inputs)],
                         [(0, 3, 0), (0, 0, 1), (0, 3, 0)])

    def test_valid_width_32_and_large_decay_ratio(self):
        req = self.req(old=-(1 << 31), threshold=1, bits=32,
                       num=4294967295, den=4294967295)
        self.assertEqual(self.run_requests([req])[0][2:], (0, -(1 << 31), 0))
        req = self.req(old=(1 << 31) - 1, threshold=(1 << 31) - 1, bits=32,
                       num=4294967295, den=4294967295)
        self.assertEqual(self.run_requests([req])[0][2:], (0, 0, 1))

    def test_invalid_id_and_empty_network_fail_closed(self):
        rows = [self.req(neuron=1, count=1), self.req(neuron=0, count=0)]
        self.assertEqual([x[2:] for x in self.run_requests(rows)], [(1, 0, 0), (1, 0, 0)])

    def test_invalid_width_and_decay_fail_closed(self):
        rows = [self.req(bits=3), self.req(bits=33), self.req(den=0),
                self.req(num=5, den=4), self.req(num=0, den=1)]
        got = self.run_requests(rows)
        self.assertEqual([x[2:] for x in got[:4]],
                         [(2, 0, 0), (2, 0, 0), (4, 0, 0), (4, 0, 0)])
        self.assertEqual(got[4][2:], (0, 0, 0))

    def test_invalid_state_threshold_and_reset_fail_closed(self):
        rows = [self.req(bits=4, old=8), self.req(bits=4, bias=-9),
                self.req(threshold=0), self.req(bits=4, threshold=8),
                self.req(threshold=5, reset=5), self.req(bits=4, reset=-9)]
        self.assertEqual([x[2:] for x in self.run_requests(rows)], [(4, 0, 0)] * len(rows))

    def test_identical_old_state_is_tick_independent(self):
        rows = [self.req(old=4, num=1, den=2, tick=t) for t in (0, 1, 9999999)]
        self.assertEqual([x[2:] for x in self.run_requests(rows)], [(0, 2, 0)] * len(rows))

    def check_network(self, net, inputs, ticks):
        dense = evaluate_dense(net, inputs, ticks=ticks)
        events = evaluate_events(net, inputs, ticks=ticks)
        self.assertEqual(dense, events)
        rows, expected = [], []
        for t in range(ticks):
            for i, neuron in enumerate(net.neurons):
                arriving = sum(e.current for e in inputs if e.tick == t and e.neuron == i)
                for syn in net.synapses:
                    if syn.post == i and t >= syn.delay and syn.pre in dense.spike_rows[t - syn.delay]:
                        arriving += syn.weight
                old = neuron.initial_v if t == 0 else dense.voltage_rows[t-1][i]
                rows.append(self.req(neuron=i, count=len(net.neurons), tick=t, old=old,
                                     current=arriving, bias=neuron.bias, threshold=neuron.threshold,
                                     reset=neuron.reset_v, bits=net.state_bits,
                                     num=net.decay_num, den=net.decay_den))
                expected.append((i, t, 0, dense.voltage_rows[t][i], int(i in dense.spike_rows[t])))
        self.assertEqual(self.run_requests(rows), expected)

    def test_delayed_self_loop_and_parallel_signed_edges(self):
        net = Network((Neuron(threshold=3, reset_v=0),),
                      (Synapse(0, 0, 2, 2), Synapse(0, 0, -1, 1)),
                      decay_num=0, decay_den=1, state_bits=8)
        inputs = (InputCurrent(0, 0, 3), InputCurrent(2, 0, 2))
        self.check_network(net, inputs, 6)
        trace = evaluate_dense(net, inputs, ticks=6)
        self.assertIn((0, 0), trace.emitted_spikes)
        self.assertEqual(trace.voltage_rows[1], (-1,))  # delayed inhibitory arrival

    def test_randomized_networks_match_two_m02_oracles_all_ticks(self):
        for bits in (4, 8, 16, 32):
            for seed in (3, 19, 71, 101):
                with self.subTest(bits=bits, seed=seed):
                    rnd = random.Random(10000 + bits * 100 + seed)
                    lo, hi = -(1 << (bits-1)), (1 << (bits-1)) - 1
                    cells = tuple(Neuron(initial_v=rnd.randint(max(lo, -6), min(hi, 6)),
                                         bias=rnd.randint(max(lo, -2), min(hi, 2)),
                                         threshold=rnd.randint(1, min(hi, 6)),
                                         reset_v=rnd.randint(max(lo, -3), 0)) for _ in range(5))
                    synapses = tuple(Synapse(rnd.randrange(5), rnd.randrange(5),
                                              rnd.randint(max(lo, -5), min(hi, 5)),
                                              rnd.randint(1, 3)) for _ in range(14))
                    inputs = tuple(InputCurrent(rnd.randrange(8), rnd.randrange(5),
                                                rnd.randint(max(lo, -7), min(hi, 7)))
                                   for _ in range(35))
                    net = Network(cells, synapses, decay_num=rnd.randint(0, 10),
                                  decay_den=10, state_bits=bits)
                    self.check_network(net, inputs, 8)


if __name__ == "__main__":
    unittest.main()
