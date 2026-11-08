"""M05.2 HLS-oriented physical-accumulator native parity/overflow tests.

Actual bounded C++ stateful tick aggregator runs in its own executable.
Hardware queue routing, future delays, physical synthesis and ready/valid
backpressure are NOT proved. All tests are PC/native, not Vitis.
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
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron, Synapse
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events


class M05AccumulatorNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            raise RuntimeError("M05 accumulator native C++17 compiler is required")
        cls.tmp = tempfile.TemporaryDirectory(prefix="m05_accumulator_")
        cls.binary = str(Path(cls.tmp.name) / "m05_accum_cli")
        hls = ROOT / "hls"
        out = subprocess.run(
            [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
             "-Werror", "-pedantic", "-Wno-unknown-pragmas",
             str(hls / "m05_accumulator/m05_accumulator.cpp"),
             str(hls / "m05_accumulator/m05_accum_host_cli.cpp"),
             "-o", cls.binary], capture_output=True, text=True,
        )
        if out.returncode:
            raise RuntimeError("M05 accumulator compilation failed:\n" + out.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def cmd(op, *, neuron=0, count=2, tick=0, current=0):
        return op, neuron, count, tick, current

    def run_cmds(self, commands):
        payload = str(len(commands)) + "\n" + "".join(
            " ".join(map(str, c)) + "\n" for c in commands
        )
        run = subprocess.run(
            [self.binary], input=payload, text=True, capture_output=True
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [tuple(map(int, line.split()))
                for line in run.stdout.splitlines()]
        self.assertEqual(rows[0], (len(commands),))
        self.assertEqual(len(rows), 1 + len(commands))
        self.assertTrue(all(len(row) == 6 for row in rows[1:]))
        self.assertEqual([r[:2] for r in rows[1:]],
                         [(c[1], c[3]) for c in commands])
        return rows[1:]

    def test_signed_cancellation_sealed_aggregate_matches_exact_sum(self):
        ops = [self.cmd(0), self.cmd(1, tick=3),
               self.cmd(2, neuron=1, tick=3, current=32767),
               self.cmd(2, neuron=1, tick=3, current=-32768),
               self.cmd(2, neuron=1, tick=3, current=6),
               self.cmd(3, tick=3), self.cmd(4, neuron=1, tick=3),
               self.cmd(4, neuron=0, tick=3), self.cmd(5, tick=3)]
        rows = self.run_cmds(ops)
        self.assertEqual([r[2] for r in rows], [0] * len(ops))
        self.assertEqual(rows[6][3:], (5, 1, 3))
        self.assertEqual(rows[7][3:], (0, 0, 3))

    def test_4096_signed_contributions_success_including_zero(self):
        ops = [self.cmd(0), self.cmd(1, tick=0)]
        ops += [self.cmd(2, tick=0, current=32767 if i % 2 else -32768)
                for i in range(4096)]
        ops.extend([self.cmd(3), self.cmd(4), self.cmd(5)])
        rows = self.run_cmds(ops)
        self.assertEqual(rows[-3][2], 0)
        self.assertEqual(rows[-2][2:], (0, -2048, 1, 4096))
        self.assertEqual(rows[-1][2], 0)

    def test_4097th_signed_contribution_fails_closed_without_readout(self):
        ops = [self.cmd(0), self.cmd(1)]
        ops.extend(self.cmd(2, current=0) for _ in range(4096))
        ops.extend([self.cmd(2, current=0), self.cmd(3), self.cmd(4),
                    self.cmd(0), self.cmd(1, tick=1),
                    self.cmd(3, tick=1), self.cmd(4, tick=1)])
        rows = self.run_cmds(ops)
        self.assertEqual(rows[2 + 4096][2:], (5, 0, 0, 4096))
        self.assertEqual(rows[3 + 4096][2], 10)
        self.assertEqual(rows[4 + 4096][2], 10)
        self.assertEqual(rows[-1][2:], (0, 0, 0, 0))

    def test_invalid_w16_current_sticky_failure_and_rearm(self):
        ops = [self.cmd(0), self.cmd(1), self.cmd(2, current=32768),
               self.cmd(2, current=1), self.cmd(3),
               self.cmd(0), self.cmd(1, tick=4),
               self.cmd(2, tick=4, current=-32768),
               self.cmd(3, tick=4), self.cmd(4, tick=4)]
        rows = self.run_cmds(ops)
        self.assertEqual([rows[i][2] for i in (2, 3, 4)], [6, 10, 10])
        self.assertEqual(rows[-1][2:], (0, -32768, 1, 1))

    def test_duplicate_begin_or_unknown_opcode_invalidates_current_tick(self):
        ops = [self.cmd(0), self.cmd(1), self.cmd(1),
               self.cmd(2), self.cmd(0), self.cmd(1),
               self.cmd(99), self.cmd(3)]
        rows = self.run_cmds(ops)
        self.assertEqual(rows[2][2], 8)
        self.assertEqual(rows[3][2], 10)
        self.assertEqual(rows[6][2], 1)
        self.assertEqual(rows[7][2], 10)

    def test_read_before_seal_is_failure_not_partial_current(self):
        ops = [self.cmd(0), self.cmd(1), self.cmd(2, current=4),
               self.cmd(4), self.cmd(3), self.cmd(4)]
        rows = self.run_cmds(ops)
        self.assertEqual(rows[3][2:], (7, 0, 0, 1))
        self.assertEqual(rows[4][2], 10)
        self.assertEqual(rows[5][2], 10)

    def test_sealed_tick_rejects_late_add_and_refuses_earlier_sum(self):
        ops = [self.cmd(0), self.cmd(1, tick=8),
               self.cmd(2, tick=8, current=4),
               self.cmd(3, tick=8),
               self.cmd(4, tick=8),
               self.cmd(2, tick=8, current=1),
               self.cmd(4, tick=8)]
        rows = self.run_cmds(ops)
        self.assertEqual(rows[4][2:], (0, 4, 1, 1))
        self.assertEqual(rows[5][2], 9)
        self.assertEqual(rows[6][2:], (10, 0, 0, 1))

    def test_wrong_tick_or_neuron_id_or_network_size_fail_closed(self):
        cases = [
            self.cmd(2, tick=7, current=1),
            self.cmd(2, neuron=2, count=2, tick=8, current=1),
            self.cmd(2, neuron=0, count=1, tick=8, current=1),
        ]
        for bad in cases:
            with self.subTest(bad=bad):
                rows = self.run_cmds([self.cmd(0), self.cmd(1, tick=8), bad,
                                      self.cmd(3, tick=8)])
                self.assertEqual(rows[2][2], 4 if bad[3] == 7 else 2)
                self.assertEqual(rows[3][2], 10)

    def test_multiple_ticks_reset_touch_without_modifying_old_sum(self):
        ops = [self.cmd(0), self.cmd(1, tick=0),
               self.cmd(2, tick=0, neuron=1, current=3),
               self.cmd(3, tick=0),
               self.cmd(5, tick=0),
               self.cmd(1, tick=1),
               self.cmd(3, tick=1),
               self.cmd(4, tick=1, neuron=1),
               self.cmd(5, tick=1)]
        rows = self.run_cmds(ops)
        self.assertEqual(rows[7][2:], (0, 0, 0, 0))

    def test_m02_recurrent_delivery_aggregate_across_seeded_networks(self):
        for seed in range(6):
            with self.subTest(seed=seed):
                rng = random.Random(52026 + seed)
                n = 5
                net = Network(
                    tuple(Neuron(
                        initial_v=rng.randint(-4, 4),
                        threshold=rng.randint(1, 8),
                        bias=rng.randint(-2, 2),
                        reset_v=rng.randint(-2, 0)) for _ in range(n)),
                    tuple(Synapse(rng.randrange(n), rng.randrange(n),
                                  rng.randint(-7, 7), rng.randint(1, 3))
                          for _ in range(14)),
                    decay_num=rng.randint(0, 10), decay_den=10, state_bits=16,
                )
                inputs = tuple(InputCurrent(
                    rng.randrange(6), rng.randrange(n), rng.randint(-8, 8))
                    for _ in range(30))
                gold = evaluate_dense(net, inputs, ticks=6)
                self.assertEqual(gold, evaluate_events(net, inputs, ticks=6))
                commands = [self.cmd(0)]
                expected = []
                for t in range(6):
                    commands.append(self.cmd(1, count=n, tick=t))
                    event_items = [
                        (e.neuron, e.current) for e in inputs if e.tick == t
                    ]
                    event_items.extend(
                        (edge.post, edge.weight) for edge in net.synapses
                        if t >= edge.delay
                        and edge.pre in gold.spike_rows[t - edge.delay]
                    )
                    for dest, weight in event_items:
                        commands.append(self.cmd(
                            2, neuron=dest, count=n, tick=t, current=weight))
                    commands.append(self.cmd(3, count=n, tick=t))
                    for i in range(n):
                        expected.append(
                            (len(commands), sum(weight for dest, weight
                                                in event_items if dest == i),
                             int(any(dest == i for dest, _ in event_items)),
                             len(event_items))
                        )
                        commands.append(self.cmd(
                            4, neuron=i, count=n, tick=t))
                    commands.append(self.cmd(5, count=n, tick=t))
                rows = self.run_cmds(commands)
                for position, current, touched, count in expected:
                    self.assertEqual(rows[position - 1][2:],
                                     (0, current, touched, count))

    def test_malformed_transport_rejected_without_partial_results(self):
        good = " ".join(map(str, self.cmd(0)))
        bad = ["-1\n", "garbage\n", "1\n",
               "1\n" + good + " trailing\n",
               "1\n" + good + "\n" + good + "\n",
               "1\n" + " ".join(good.split()[:4] + [str(1 << 32)]) + "\n"]
        for data in bad:
            with self.subTest(data=data[:40]):
                proc = subprocess.run([self.binary], input=data,
                                      text=True, capture_output=True)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
