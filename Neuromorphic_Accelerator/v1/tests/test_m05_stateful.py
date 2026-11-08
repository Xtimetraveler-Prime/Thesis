"""M05.3 native HLS-oriented local-state memory tests (NO Vitis/board).

Tests run the ACTUAL m05_stateful_service C++ top through a native command
adapter; comparing admitted cases against both independent M02 references.
Static C++ arrays persist across many separate function invocations in the
same subprocess; Python does NOT simulate the candidate hardware's states.
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


class M05StateMemoryNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            raise RuntimeError("M05 state-memory tests REQUIRE a C++17 compiler")
        cls.tmp = tempfile.TemporaryDirectory(prefix="m05_stateful_")
        cls.binary = str(Path(cls.tmp.name) / "m05_stateful_native_cli")
        root = ROOT / "hls"
        outcome = subprocess.run(
            [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
             "-Werror", "-pedantic", "-Wno-unknown-pragmas",
             str(root / "m04_lif_eval/m04_eval.cpp"),
             str(root / "m05_stateful/m05_stateful.cpp"),
             str(root / "m05_stateful/m05_stateful_host_cli.cpp"),
             "-o", cls.binary],
            capture_output=True, text=True,
        )
        if outcome.returncode:
            raise RuntimeError("M05 stateful C++ failed:\n" + outcome.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def command(op, *, neuron=0, count=1, tick=0, old=0, current=0,
                bias=0, threshold=5, reset=0, num=1, den=1):
        return (op, neuron, count, tick, old, current, bias,
                threshold, reset, num, den)

    def run_commands(self, commands):
        data = str(len(commands)) + "\n" + "".join(
            " ".join(str(x) for x in cmd) + "\n" for cmd in commands
        )
        completed = subprocess.run(
            [self.binary], input=data, capture_output=True, text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = completed.stdout.splitlines()
        self.assertEqual(lines[0], str(len(commands)))
        self.assertEqual(len(lines), len(commands) + 1)
        replies = [tuple(map(int, x.split())) for x in lines[1:]]
        self.assertTrue(all(len(x) == 5 for x in replies))
        self.assertEqual([r[:2] for r in replies],
                         [(c[1], c[3]) for c in commands])
        return replies

    def test_init_read_and_clear_invalidate_without_leaking_old_data(self):
        cmds = [self.command(0), self.command(3),
                self.command(1, old=-11), self.command(3),
                self.command(0), self.command(3)]
        result = self.run_commands(cmds)
        self.assertEqual([x[2:] for x in result],
                         [(0, 0, 0), (3, 0, 0), (0, -11, 0),
                          (0, -11, 0), (0, 0, 0), (3, 0, 0)])

    def test_negative_decay_inclusive_spike_and_reset(self):
        cmds = [self.command(0), self.command(1, old=-3, reset=-2),
                self.command(2, tick=0, num=1, den=2),
                self.command(2, tick=1, current=6),
                self.command(3)]
        replies = self.run_commands(cmds)
        self.assertEqual([x[2:] for x in replies],
                         [(0, 0, 0), (0, -3, 0), (0, -1, 0),
                          (0, -2, 1), (0, -2, 0)])

    def test_duplicate_tick_rejected_no_state_write(self):
        cmds = [self.command(0), self.command(1),
                self.command(2, tick=4, current=4),
                self.command(2, tick=4, current=100),
                self.command(3)]
        rows = self.run_commands(cmds)
        self.assertEqual(rows[2][2:], (0, 4, 0))
        self.assertEqual(rows[3][2:], (6, 0, 0))
        self.assertEqual(rows[4][2:], (0, 4, 0))

    def test_stale_tick_rejected_and_gap_is_allowed_if_scheduler_proves_skip(self):
        cmds = [self.command(0), self.command(1),
                self.command(2, tick=9, current=2),
                self.command(2, tick=3, current=40),
                self.command(2, tick=11, current=1), self.command(3)]
        rows = self.run_commands(cmds)
        self.assertEqual(rows[2][2:], (0, 2, 0))
        self.assertEqual(rows[3][2:], (7, 0, 0))
        self.assertEqual(rows[4][2:], (0, 3, 0))
        self.assertEqual(rows[5][2:], (0, 3, 0))

    def test_invalid_init_and_invalid_step_no_state_update(self):
        cmds = [self.command(0),
                self.command(1, old=32768),
                self.command(3),
                self.command(1, threshold=0),
                self.command(3),
                self.command(1, reset=5, threshold=5),
                self.command(3),
                self.command(1, old=4),
                self.command(2, tick=0, den=0),
                self.command(3),
                self.command(2, tick=0, num=3, den=2),
                self.command(3)]
        rows = self.run_commands(cmds)
        self.assertEqual([rows[i][2] for i in (1, 3, 5, 8, 10)],
                         [4, 4, 4, 4, 4])
        self.assertEqual([rows[i][2] for i in (2, 4, 6)],
                         [3, 3, 3])
        self.assertEqual(rows[9][2:], (0, 4, 0))
        self.assertEqual(rows[11][2:], (0, 4, 0))

    def test_duplicate_initialization_rejected_unless_cleared(self):
        cmds = [self.command(0), self.command(1, old=3),
                self.command(1, old=-9), self.command(3),
                self.command(0), self.command(1, old=-9), self.command(3)]
        rows = self.run_commands(cmds)
        self.assertEqual(rows[2][2:], (5, 0, 0))
        self.assertEqual(rows[3][2:], (0, 3, 0))
        self.assertEqual(rows[5][2:], (0, -9, 0))
        self.assertEqual(rows[6][2:], (0, -9, 0))

    def test_invalid_opcode_and_id_fail_closed(self):
        cmds = [self.command(0), self.command(9),
                self.command(1, count=0),
                self.command(1, neuron=1, count=1),
                self.command(1, neuron=0, count=1025),
                self.command(3)]
        rows = self.run_commands(cmds)
        self.assertEqual([row[2:] for row in rows],
                         [(0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 0, 0),
                          (2, 0, 0), (3, 0, 0)])

    def test_two_neurons_can_advance_in_different_dispatch_order(self):
        cmds = [self.command(0), self.command(1, neuron=0, count=2),
                self.command(1, neuron=1, count=2, bias=1),
                self.command(2, neuron=1, count=2, tick=0, current=4),
                self.command(2, neuron=0, count=2, tick=0, current=-7),
                self.command(3, neuron=0, count=2),
                self.command(3, neuron=1, count=2)]
        rows = self.run_commands(cmds)
        self.assertEqual(rows[3][2:], (0, 0, 1))
        self.assertEqual(rows[4][2:], (0, -7, 0))
        self.assertEqual(rows[5][2:], (0, -7, 0))
        self.assertEqual(rows[6][2:], (0, 0, 0))

    def test_1024_neuron_physical_capacity_and_independent_state(self):
        cmds = [self.command(0)]
        cmds += [self.command(1, neuron=i, count=1024, old=i % 31 - 15)
                 for i in range(1024)]
        cmds += [self.command(3, neuron=i, count=1024)
                 for i in (0, 100, 501, 1023)]
        rows = self.run_commands(cmds)
        self.assertEqual([x[3] for x in rows[-4:]],
                         [i % 31 - 15 for i in (0, 100, 501, 1023)])
        self.assertTrue(all(x[2] == 0 for x in rows))

    def test_saturation_must_follow_exact_64bit_aggregate(self):
        cmds = [self.command(0), self.command(1, old=1, threshold=32767),
                self.command(2, tick=0, current=(1 << 63) - 1),
                self.command(3),
                self.command(2, tick=1, current=-(1 << 63)),
                self.command(3)]
        rows = self.run_commands(cmds)
        self.assertEqual(rows[2][2:], (0, 0, 1))
        self.assertEqual(rows[3][2:], (0, 0, 0))
        self.assertEqual(rows[4][2:], (0, -32768, 0))
        self.assertEqual(rows[5][2:], (0, -32768, 0))

    def test_m02_dense_and_event_traces_match_stateful_ram_across_ticks(self):
        for seed in range(8):
            with self.subTest(seed=seed):
                rng = random.Random(51057 + seed)
                cells = tuple(Neuron(
                    initial_v=rng.randint(-4, 3), bias=rng.randint(-2, 2),
                    threshold=rng.randint(2, 10), reset_v=rng.randint(-3, 0))
                    for _ in range(5))
                edges = tuple(Synapse(rng.randrange(5), rng.randrange(5),
                                      rng.randint(-5, 5), rng.randint(1, 3))
                              for _ in range(13))
                net = Network(cells, edges,
                              decay_num=rng.randint(0, 10),
                              decay_den=10, state_bits=16)
                inputs = tuple(InputCurrent(
                    rng.randrange(8), rng.randrange(5), rng.randint(-9, 9))
                    for _ in range(25))
                gold = evaluate_dense(net, inputs, ticks=8)
                self.assertEqual(gold, evaluate_events(net, inputs, ticks=8))
                cmds = [self.command(0)]
                cmds += [self.command(1, neuron=i, count=5,
                                      old=n.initial_v, bias=n.bias,
                                      threshold=n.threshold, reset=n.reset_v)
                         for i, n in enumerate(cells)]
                for t in range(8):
                    for i in range(5):
                        aggregate = sum(
                            event.current for event in inputs
                            if event.tick == t and event.neuron == i
                        ) + sum(
                            edge.weight for edge in edges
                            if edge.post == i and t >= edge.delay
                            and edge.pre in gold.spike_rows[t - edge.delay]
                        )
                        cmds.append(self.command(
                            2, neuron=i, count=5, tick=t, current=aggregate,
                            num=net.decay_num, den=net.decay_den))
                replies = self.run_commands(cmds)[1 + 5:]
                self.assertEqual(len(replies), 40)
                for t in range(8):
                    for i in range(5):
                        reply = replies[t * 5 + i]
                        self.assertEqual(reply,
                                         (i, t, 0, gold.voltage_rows[t][i],
                                          int(i in gold.spike_rows[t])))

    def test_malformed_or_unrepresentable_cli_inputs_rejected(self):
        valid = " ".join(map(str, self.command(0)))
        bad = ["-1\n", "wrong\n", "1\n", "1\n" + valid + " extra\n",
               "1\n" + valid + "\n" + valid + "\n",
               "1\n" + " ".join(valid.split()[:5] + [str(1 << 64)] +
                               valid.split()[6:]) + "\n"]
        for payload in bad:
            with self.subTest(payload=payload[:30]):
                out = subprocess.run([self.binary], input=payload,
                                     text=True, capture_output=True)
                self.assertEqual(out.returncode, 2)
                self.assertEqual(out.stdout, "")


if __name__ == "__main__":
    unittest.main()
