"""M05.1/M05.2 host-native tests for real C++ batch kernel and software event replay.

Not HLS synthesis/C-RTL co-simulation, not a hardware scheduler or physical
performance claim. Network traces are checked against independently accepted
M02 dense/event and, where relevant, M03 sparse references.
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
from neuromorphic_accelerator_v1.m04_profile import M04AdmissionError, MAX_U64
from neuromorphic_accelerator_v1.m05_host_runtime import replay_exact_sparse_host


class M05NativeStreamingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            raise RuntimeError("Native C++17 compiler required; M05 tests may not skip")
        cls.build = tempfile.TemporaryDirectory(prefix="m05_stream_")
        cls.binary = str(Path(cls.build.name) / "m05_host_stream_cli")
        m04 = ROOT / "hls" / "m04_lif_eval"
        m05 = ROOT / "hls" / "m05_stream_eval"
        result = subprocess.run(
            [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
             "-pedantic", "-Wno-unknown-pragmas", "-I", str(m04),
             str(m04 / "m04_eval.cpp"), str(m05 / "m05_stream.cpp"),
             str(m05 / "m05_stream_host_cli.cpp"), "-o", cls.binary],
            capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError("M05 compiler failed:\n" + result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def batch(self, requests):
        payload = str(len(requests)) + "\n"
        payload += "".join(" ".join(map(str, request)) + "\n" for request in requests)
        result = subprocess.run([self.binary], input=payload, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(tuple(map(int, lines[0].split())), (0, len(requests)))
        self.assertEqual(len(lines), len(requests) + 1)
        return [tuple(map(int, line.split())) for line in lines[1:]]

    @staticmethod
    def req(*, neuron=0, count=1, tick=0, old=0, incoming=0,
            bias=0, threshold=5, reset=0, bits=16, numerator=1, denominator=1):
        return (neuron, count, tick, old, incoming, bias, threshold,
                reset, bits, numerator, denominator)

    def check_network(self, net, inputs, ticks):
        wanted = evaluate_dense(net, inputs, ticks=ticks)
        self.assertEqual(wanted, evaluate_events(net, inputs, ticks=ticks))
        sparse = evaluate_exact_sparse(net, inputs, ticks=ticks)
        self.assertEqual(wanted, sparse.trace)
        actual = replay_exact_sparse_host(
            net, inputs, ticks=ticks, kernel_binary=self.binary
        )
        self.assertEqual(actual.trace, wanted)
        self.assertEqual(actual.evaluated_ids_by_tick, sparse.evaluated_ids_by_tick)
        self.assertEqual(actual.deliveries_by_tick, sparse.deliveries_by_tick)
        return actual

    def test_stream_batch_exact_negative_division_and_threshold_equality(self):
        requests = [self.req(old=-3, numerator=1, denominator=2),
                    self.req(old=0, incoming=5, reset=-2),
                    self.req(old=32767, threshold=32767, reset=0)]
        self.assertEqual([r[2:] for r in self.batch(requests)],
                         [(0, -1, 0), (0, -2, 1), (0, 0, 1)])

    def test_stream_batch_preserves_order_and_per_request_status(self):
        rows = [self.req(neuron=2, count=3, tick=41, old=-3),
                self.req(neuron=1, count=3, tick=41, bits=3),
                self.req(neuron=0, count=3, tick=41, incoming=-32768)]
        out = self.batch(rows)
        self.assertEqual([r[:2] for r in out], [(2, 41), (1, 41), (0, 41)])
        self.assertEqual(out[1][2:], (2, 0, 0))
        self.assertEqual(out[2][2:], (0, -32768, 0))

    def test_stream_zero_requests_returns_empty(self):
        self.assertEqual(self.batch([]), [])

    def test_stream_input_protocol_rejects_malformed_and_overlarge_batches(self):
        valid = " ".join(map(str, self.req()))
        bad = ["1025\n", "-1\n", "1\n", "1\n" + valid + " extra\n",
               "1\n" + valid + "\n" + valid + "\n",
               "1\n" + valid.replace(" 0 1 1", " 0 1 4294967296") + "\n",
               "not_an_integer\n"]
        for payload in bad:
            with self.subTest(payload=payload[:40]):
                result = subprocess.run([self.binary], input=payload,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(result.stdout)

    def test_bias_only_neurons_always_evaluated(self):
        net = Network((Neuron(bias=3, threshold=5),), state_bits=16)
        actual = self.check_network(net, (), ticks=4)
        self.assertEqual(actual.trace.voltage_rows, ((3,), (0,), (3,), (0,)))
        self.assertEqual(actual.trace.emitted_spikes, ((1, 0), (3, 0)))
        self.assertEqual(actual.evaluated_ids_by_tick, ((0,),) * 4)

    def test_only_exact_zero_state_idle_is_skipped(self):
        net = Network(tuple(Neuron(threshold=20) for _ in range(4)),
                      decay_num=1, decay_den=2, state_bits=16)
        actual = self.check_network(net, (InputCurrent(0, 1, 4),), ticks=5)
        self.assertEqual(actual.trace.voltage_rows,
                         ((0, 4, 0, 0), (0, 2, 0, 0), (0, 1, 0, 0),
                          (0, 0, 0, 0), (0, 0, 0, 0)))
        self.assertEqual(actual.evaluated_ids_by_tick,
                         ((1,), (1,), (1,), (1,), ()))

    def test_duplicate_signed_cancellation_before_one_saturation(self):
        net = Network((Neuron(threshold=5, reset_v=-3),), state_bits=16)
        inputs = (InputCurrent(0, 0, 32767), InputCurrent(0, 0, -32768),
                  InputCurrent(0, 0, 6))
        actual = self.check_network(net, inputs, ticks=2)
        self.assertEqual(actual.trace.voltage_rows[0], (-3,))
        self.assertEqual(actual.trace.emitted_spikes, ((0, 0),))

    def test_parallel_recurrent_self_edges_with_strictly_positive_delays(self):
        net = Network((Neuron(threshold=5), Neuron(threshold=6, bias=1)),
                      (Synapse(0, 0, -2, 1), Synapse(0, 0, 4, 2),
                       Synapse(0, 1, 6, 1), Synapse(1, 0, -3, 3)),
                      decay_num=1, decay_den=2, state_bits=16)
        actual = self.check_network(net, (InputCurrent(0, 0, 5),), ticks=9)
        self.assertIn((0, 0), actual.trace.emitted_spikes)
        self.assertEqual(actual.deliveries_by_tick[0], 1)
        self.assertGreater(actual.evaluated_neuron_steps, 0)

    def test_seeded_recurrent_networks_all_tick_state_and_spike_parity(self):
        for seed in range(12):
            with self.subTest(seed=seed):
                rng = random.Random(20261107 + seed)
                n = 6
                net = Network(
                    tuple(Neuron(initial_v=rng.randint(-4, 4),
                                 bias=rng.randint(-2, 2),
                                 threshold=rng.randint(1, 10),
                                 reset_v=rng.randint(-3, 0)) for _ in range(n)),
                    tuple(Synapse(rng.randrange(n), rng.randrange(n),
                                  rng.randint(-7, 7), rng.randint(1, 4))
                          for _ in range(16)),
                    decay_num=rng.randint(0, 10), decay_den=10, state_bits=16,
                )
                inputs = tuple(InputCurrent(rng.randrange(10), rng.randrange(n),
                                            rng.randint(-10, 10))
                               for _ in range(36))
                actual = self.check_network(net, inputs, 10)
                self.assertLessEqual(actual.evaluated_neuron_steps, n * 10)

    def test_4096_admitted_events_exact_without_intermediate_clipping(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        inputs = tuple(event for _ in range(2048) for event in
                       (InputCurrent(0, 0, 32767), InputCurrent(0, 0, -32768)))
        actual = self.check_network(net, inputs, ticks=1)
        self.assertEqual(actual.deliveries_by_tick, (4096,))
        self.assertEqual(actual.trace.voltage_rows, ((-2048,),))
        self.assertEqual(actual.evaluated_neuron_steps, 1)

    def test_4097_external_events_fail_closed(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        inputs = (InputCurrent(0, 0, 0) for _ in range(4097))
        with self.assertRaisesRegex(M04AdmissionError, "4096"):
            replay_exact_sparse_host(net, inputs, ticks=1, kernel_binary=self.binary)

    def test_4097_scheduled_recurrent_events_fail_closed(self):
        net = Network((Neuron(threshold=5),),
                      tuple(Synapse(0, 0, 1, 1) for _ in range(4097)),
                      state_bits=16)
        with self.assertRaisesRegex(M04AdmissionError, "4096"):
            replay_exact_sparse_host(net, (InputCurrent(0, 0, 5),),
                                     ticks=2, kernel_binary=self.binary)

    def test_provisional_resident_capacity_bound(self):
        net = Network(tuple(Neuron(threshold=5) for _ in range(1024)),
                      state_bits=16)
        result = replay_exact_sparse_host(net, (), ticks=1,
                                          kernel_binary=self.binary)
        self.assertEqual(result.evaluated_neuron_steps, 0)
        self.assertEqual(result.kernel_batches, 0)
        too_big = Network(tuple(Neuron(threshold=5) for _ in range(1025)),
                          state_bits=16)
        with self.assertRaisesRegex(M04AdmissionError, "resident working set"):
            replay_exact_sparse_host(too_big, (), ticks=1,
                                     kernel_binary=self.binary)
        with self.assertRaisesRegex(M04AdmissionError, "resident_neurons"):
            replay_exact_sparse_host(net, (), ticks=1, kernel_binary=self.binary,
                                     resident_neurons=0)

    def test_m02_legal_other_width_or_ratio_rejected_by_first_profile(self):
        for bits in (4, 8, 32):
            net = Network((Neuron(threshold=1),), state_bits=bits)
            self.assertEqual(evaluate_dense(net, (), ticks=1).voltage_rows, ((0,),))
            with self.assertRaisesRegex(M04AdmissionError, "W16"):
                replay_exact_sparse_host(net, (), ticks=1,
                                         kernel_binary=self.binary)
        big_decay = Network((Neuron(threshold=1),), decay_num=0,
                            decay_den=1 << 32, state_bits=16)
        self.assertEqual(evaluate_dense(big_decay, (), ticks=1).voltage_rows, ((0,),))
        with self.assertRaisesRegex(M04AdmissionError, "32-bit"):
            replay_exact_sparse_host(big_decay, (), ticks=1,
                                     kernel_binary=self.binary)

    def test_invalid_zero_delay_is_rejected_before_any_engine_call(self):
        net = Network((Neuron(threshold=5),), (Synapse(0, 0, 1, 0),),
                      state_bits=16)
        with self.assertRaisesRegex(ValueError, "zero/negative delay"):
            replay_exact_sparse_host(net, (), ticks=2, kernel_binary=self.binary)

    def test_missing_host_binary_rejected_without_fake_pass(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        with self.assertRaises(FileNotFoundError):
            replay_exact_sparse_host(net, (), ticks=1,
                                     kernel_binary=str(ROOT / "never_exists_m05"))

    def test_tick_exceeding_u64_rejected_before_any_large_replay(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        with self.assertRaisesRegex(M04AdmissionError, "unsigned 64-bit"):
            replay_exact_sparse_host(net, (), ticks=MAX_U64 + 2,
                                     kernel_binary=self.binary)


if __name__ == "__main__":
    unittest.main()
