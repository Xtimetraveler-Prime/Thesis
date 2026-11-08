"""M05 rolling 8-slot temporal wheel: native C++ and independent M02/M03 parity.

This is source/native verification, NOT Vitis synth, RTL, ready-valid, or a
continuous chip. Nonzero final status INVALIDATES the entire streamed prefix.
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
from neuromorphic_accelerator_v1.m03_sparse_reference import evaluate_exact_sparse


class M05RollingNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            raise RuntimeError("Native C++ compiler is mandatory")
        cls.temp = tempfile.TemporaryDirectory(prefix="m05_rolling_")
        cls.binary = str(Path(cls.temp.name) / "rolling_cli")
        cls.bench = str(Path(cls.temp.name) / "rolling_bench")
        flags = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                 "-Werror", "-pedantic", "-Wno-unknown-pragmas"]
        sources = [
            str(ROOT / "hls/m04_lif_eval/m04_eval.cpp"),
            str(ROOT / "hls/m05_rolling/m05_rolling.cpp")
        ]
        for name, output in (
            ("hls/m05_rolling/m05_rolling_host_cli.cpp", cls.binary),
            ("hls/m05_rolling/m05_rolling_csim_tb.cpp", cls.bench),
        ):
            result = subprocess.run(flags + sources + [str(ROOT / name),
                                    "-o", output],
                                    capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError("Rolling C++ compilation failed:\n" + result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, net, events, ticks, status=0):
        header = (len(net.neurons), len(net.synapses), len(events), ticks,
                  net.decay_num, net.decay_den)
        text_lines = [" ".join(str(v) for v in header)]
        text_lines.extend(f"{n.initial_v} {n.bias} {n.threshold} {n.reset_v}"
                          for n in net.neurons)
        text_lines.extend(f"{e.pre} {e.post} {e.weight} {e.delay}"
                          for e in net.synapses)
        text_lines.extend(f"{e.tick} {e.neuron} {e.current}" for e in events)
        proc = subprocess.run([self.binary],
                              input="\n".join(text_lines) + "\n",
                              text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertTrue(lines, proc.stderr)
        actual_status, count = (int(v) for v in lines[0].split())
        self.assertEqual(actual_status, status, proc.stdout[:400])
        self.assertEqual(len(lines) - 1, count)
        if status:
            self.assertEqual(count, 0, "must discard speculative prefix on fault")
        else:
            self.assertEqual(count, len(net.neurons) * ticks)
        return tuple(tuple(int(v) for v in line.split())
                     for line in lines[1:])

    def compare_m02_m03(self, net, events, ticks):
        wanted = evaluate_dense(net, events, ticks=ticks)
        self.assertEqual(wanted, evaluate_events(net, events, ticks=ticks))
        sparse = evaluate_exact_sparse(net, events, ticks=ticks)
        self.assertEqual(wanted, sparse.trace)
        # Rolling hardware contract requires external events sorted by tick.
        ordered = tuple(sorted(events, key=lambda x: x.tick))
        actual = self.run_case(net, ordered, ticks)
        count = len(net.neurons)
        for tick in range(ticks):
            rows = actual[tick*count:(tick+1)*count]
            self.assertEqual([x[2] for x in rows],
                             list(wanted.voltage_rows[tick]))
            self.assertEqual(tuple(x[1] for x in rows if x[3]),
                             wanted.spike_rows[tick])
            self.assertEqual(tuple(x[1] for x in rows if x[4]),
                             sparse.evaluated_ids_by_tick[tick])
            self.assertEqual(tuple(x[5] for x in rows),
                             (sparse.deliveries_by_tick[tick],) * count)
            self.assertEqual([(x[0], x[1]) for x in rows],
                             [(tick, i) for i in range(count)])
        return actual

    def test_native_hls_csim_vectors(self):
        r = subprocess.run([self.bench], text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PASS: M05 rolling 8-slot wheel", r.stdout)

    def test_delay_eight_crosses_multiple_wheel_wraps(self):
        net = Network((Neuron(threshold=5),),
                      (Synapse(0, 0, 5, 8),), state_bits=16)
        rows = self.compare_m02_m03(net, (InputCurrent(0, 0, 5),), 24)
        self.assertEqual([r[0] for r in rows if r[3]], [0, 8, 16])
        self.assertEqual([r[0] for r in rows if r[4]], [0, 8, 16])

    def test_sparse_bias_and_negative_voltage_across_longer_run(self):
        net = Network((Neuron(bias=2, threshold=5),
                       Neuron(initial_v=-7, threshold=10),
                       Neuron(threshold=4)),
                      decay_num=1, decay_den=2, state_bits=16)
        rows = self.compare_m02_m03(net, (), 40)
        self.assertEqual(rows[2][4], 0)

    def test_signed_current_zero_cancellation_and_parallel_recurrence(self):
        net = Network(
            (Neuron(threshold=5, reset_v=-3), Neuron(bias=2, threshold=6)),
            (Synapse(0, 0, -2, 1), Synapse(0, 0, 4, 8),
             Synapse(0, 1, 6, 1), Synapse(1, 0, -3, 3)),
            decay_num=1, decay_den=2, state_bits=16)
        events = (InputCurrent(0, 0, 5), InputCurrent(3, 0, 0),
                  InputCurrent(3, 0, 32767), InputCurrent(3, 0, -32768))
        self.compare_m02_m03(net, events, 27)

    def test_4096_signed_admissions_exact_sum(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        events = tuple(e for _ in range(2048) for e in
                       (InputCurrent(0, 0, 32767), InputCurrent(0, 0, -32768)))
        rows = self.compare_m02_m03(net, events, 9)
        self.assertEqual(rows[0][2], -2048)
        self.assertEqual(rows[0][5], 4096)

    def test_late_external_overflow_discards_entire_run(self):
        net = Network((Neuron(threshold=5),),
                      (Synapse(0, 0, 0, 1),) * 4096, state_bits=16)
        events = (InputCurrent(0, 0, 5), InputCurrent(1, 0, 0))
        self.run_case(net, events, 17, status=5)

    def test_exact_4097_external_overflow(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        self.run_case(net, (InputCurrent(0, 0, 0),)*4097, 12, status=5)

    def test_delay_outside_wheel_rejected(self):
        net = Network((Neuron(),), (Synapse(0, 0, 1, 9),), state_bits=16)
        self.run_case(net, (), 16, status=3)
        net = Network((Neuron(),), (Synapse(0, 0, 1, 0),), state_bits=16)
        self.run_case(net, (), 16, status=3)

    def test_unsorted_external_is_fail_closed(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        events = (InputCurrent(3, 0, 3), InputCurrent(1, 0, 5))
        self.run_case(net, events, 8, status=4)

    def test_malformed_neuron_external_and_shape(self):
        self.run_case(Network((Neuron(threshold=0),), state_bits=16),
                      (), 2, status=2)
        self.run_case(Network((Neuron(),), state_bits=16),
                      (InputCurrent(0, 0, 32768),), 2, status=4)
        self.run_case(Network((Neuron(),), state_bits=16), (), 65, status=1)
        self.run_case(Network((), state_bits=16), (), 1, status=1)

    def test_same_tick_external_order_is_neuron_numerically_invariant(self):
        net = Network((Neuron(threshold=25),), state_bits=16)
        a = (InputCurrent(0, 0, 4), InputCurrent(0, 0, -11),
             InputCurrent(0, 0, 20), InputCurrent(0, 0, 0))
        b = tuple(reversed(a))
        self.assertEqual(self.run_case(net, a, 12), self.run_case(net, b, 12))
        self.compare_m02_m03(net, a, 12)

    def test_64_tick_mixed_signed_recurrence_against_independent_references(self):
        # Same complete-horizon stimulus as the actual HLS CSim/RTL bench.
        # Its 128 trace rows are checked against all accepted M02/M03 oracles.
        net = Network(
            (Neuron(initial_v=-3, bias=1, threshold=6, reset_v=-2),
             Neuron(initial_v=0, bias=0, threshold=4, reset_v=0)),
            (Synapse(0, 0, 2, 8), Synapse(0, 1, 5, 1),
             Synapse(0, 1, -3, 1), Synapse(1, 0, -4, 3),
             Synapse(1, 1, 4, 8)),
            decay_num=1, decay_den=2, state_bits=16)
        events = (
            InputCurrent(0, 0, 7), InputCurrent(0, 0, -2),
            InputCurrent(0, 1, 4), InputCurrent(7, 0, 6),
            InputCurrent(8, 1, -1), InputCurrent(15, 0, 12),
            InputCurrent(16, 1, 4), InputCurrent(32, 0, 7),
            InputCurrent(55, 1, 4), InputCurrent(63, 0, 0),
        )
        actual = self.compare_m02_m03(net, events, 64)
        self.assertEqual(len(actual), 128)
        self.assertEqual(actual[-2][0], 63)
        self.assertEqual(actual[-2][4], 1)  # final-tick ZERO touch
        self.assertEqual(actual[-1][3], 1)  # last-tick recurrent spike

    def test_maximum_1024_resident_ids_and_sparse_edge_boundary(self):
        net = Network(tuple(Neuron(threshold=5) for _ in range(1024)),
                      (Synapse(1023, 0, 5, 1),), state_bits=16)
        rows = self.compare_m02_m03(net,
                                    (InputCurrent(0, 1023, 5),), 2)
        self.assertEqual(len(rows), 2048)
        self.assertEqual(rows[1023][3], 1)
        self.assertEqual(rows[1024][3], 1)  # tick 1, ID 0 recurrence
        self.assertEqual(rows[1024][5], 1)

    def test_seeded_longer_recurrent_network_full_oracle_parity(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                rng = random.Random(2026110809 + seed)
                n = 5
                net = Network(
                    tuple(Neuron(initial_v=rng.randint(-6, 6),
                                 bias=rng.randint(-2, 2),
                                 threshold=rng.randint(1, 12),
                                 reset_v=rng.randint(-4, 0))
                          for _ in range(n)),
                    tuple(Synapse(rng.randrange(n), rng.randrange(n),
                                  rng.randint(-7, 7), rng.randint(1, 8))
                          for _ in range(25)),
                    decay_num=rng.randint(0, 10), decay_den=10,
                    state_bits=16)
                events = tuple(InputCurrent(rng.randrange(30),
                                            rng.randrange(n),
                                            rng.randint(-12, 12))
                               for _ in range(38))
                self.compare_m02_m03(net, events, 30)


if __name__ == "__main__":
    unittest.main()
