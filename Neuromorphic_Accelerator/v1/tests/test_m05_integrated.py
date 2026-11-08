"""M05 integrated finite-horizon HLS-oriented PL scheduler, host-native tests.

The C++ top does ALL tick scheduling and LIF evaluation without Python
tick loops or M05 subprocess per tick. Native g++ is NOT Vitis or AXIS timing.
Compare its entire output (all neuron/tick voltages and spikes) against
independent M02 dense/event and M03 sparse oracles, not against itself.
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

class M05IntegratedNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("g++") or shutil.which("c++")
        if not compiler:
            raise RuntimeError("native C++ compiler is required, not skipped")
        cls.temp = tempfile.TemporaryDirectory(prefix="m05_integrated_")
        cls.bin = str(Path(cls.temp.name) / "integrated")
        cls.bench = str(Path(cls.temp.name) / "integrated_tb")
        sources = [ROOT / "hls/m04_lif_eval/m04_eval.cpp",
                   ROOT / "hls/m05_integrated/m05_integrated.cpp"]
        flags = [compiler, "-std=c++17", "-O2", "-Wall", "-Wextra",
                 "-Werror", "-pedantic", "-Wno-unknown-pragmas"]
        for source, output in (
            ("hls/m05_integrated/m05_integrated_host_cli.cpp", cls.bin),
            ("hls/m05_integrated/m05_integrated_csim_tb.cpp", cls.bench)
        ):
            proc = subprocess.run(flags + [*(str(s) for s in sources),
                              str(ROOT / source), "-o", output],
                              text=True, capture_output=True)
            if proc.returncode:
                raise RuntimeError("M05 integrated C++ compiler failure:\n" + proc.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_case(self, network, events, ticks, *, expected_status=0):
        lines = [f"{len(network.neurons)} {len(network.synapses)} {len(events)} "
                 f"{ticks} {network.decay_num} {network.decay_den}"]
        lines.extend(f"{n.initial_v} {n.bias} {n.threshold} {n.reset_v}"
                     for n in network.neurons)
        lines.extend(f"{s.pre} {s.post} {s.weight} {s.delay}"
                     for s in network.synapses)
        lines.extend(f"{e.tick} {e.neuron} {e.current}" for e in events)
        raw = "\n".join(lines) + "\n"
        proc = subprocess.run([self.bin], input=raw, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = proc.stdout.strip().splitlines()
        self.assertTrue(rows)
        status, count = map(int, rows[0].split())
        self.assertEqual(status, expected_status, proc.stdout[:600])
        self.assertEqual(count, len(rows) - 1)
        if status:
            self.assertEqual(count, 0, "no partial trace permitted on error")
        else:
            self.assertEqual(count, len(network.neurons) * ticks)
        return tuple(tuple(map(int, row.split())) for row in rows[1:])

    def check_against_m02(self, net, events, ticks):
        expected = evaluate_dense(net, events, ticks=ticks)
        self.assertEqual(expected, evaluate_events(net, events, ticks=ticks))
        sparse = evaluate_exact_sparse(net, events, ticks=ticks)
        self.assertEqual(expected, sparse.trace)
        rows = self.run_case(net, events, ticks)
        n = len(net.neurons)
        for t in range(ticks):
            current_rows = rows[t*n:(t+1)*n]
            self.assertEqual(tuple(r[2] for r in current_rows),
                             expected.voltage_rows[t])
            self.assertEqual(tuple(r[1] for r in current_rows if r[3]),
                             expected.spike_rows[t])
            self.assertEqual(tuple(r[1] for r in current_rows if r[4]),
                             sparse.evaluated_ids_by_tick[t])
            self.assertEqual(tuple(r[5] for r in current_rows),
                             (sparse.deliveries_by_tick[t],) * n)
            for i, r in enumerate(current_rows):
                self.assertEqual(r[:2], (t, i))
                self.assertIn(r[3], (0, 1))
                self.assertIn(r[4], (0, 1))
        return rows

    def test_native_csim_vectors(self):
        proc = subprocess.run([self.bench], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("PASS: M05 integrated temporal CSim", proc.stdout)

    def test_exact_zero_bias_wakeup_with_no_external_events(self):
        net = Network((Neuron(bias=3, threshold=5), Neuron(threshold=9)),
                      decay_num=1, decay_den=1, state_bits=16)
        rows = self.check_against_m02(net, (), 8)
        self.assertEqual(tuple(row[4] for row in rows[1::2]), (0,)*8)

    def test_unsorted_zero_and_canceling_deliveries_remain_touched(self):
        net = Network((Neuron(threshold=7), Neuron(threshold=7)), state_bits=16)
        events = (InputCurrent(3, 1, -32768), InputCurrent(0, 0, 0),
                  InputCurrent(3, 1, 32767), InputCurrent(3, 1, 1))
        rows = self.check_against_m02(net, events, 5)
        self.assertEqual(rows[0][4], 1)  # zero incoming still touched
        self.assertEqual(rows[3 * 2 + 1][4], 1) # cancellation still touched
        self.assertEqual(rows[3 * 2 + 1][5], 3)

    def test_recurrent_self_parallel_edges_and_future_delays(self):
        net = Network(
            (Neuron(threshold=5, reset_v=-3), Neuron(bias=2, threshold=6)),
            (Synapse(0, 0, -2, 1), Synapse(0, 0, 4, 2),
             Synapse(0, 1, 6, 1), Synapse(1, 0, -3, 3),
             Synapse(0, 1, 1, 10**14)),
            decay_num=1, decay_den=2, state_bits=16)
        self.check_against_m02(net, (InputCurrent(0, 0, 5),), 8)

    def test_negative_decay_rounding_and_threshold_equality(self):
        net = Network((Neuron(initial_v=-3, threshold=5),
                       Neuron(threshold=5, reset_v=-3)),
                      decay_num=1, decay_den=2, state_bits=16)
        rows = self.check_against_m02(net, (InputCurrent(0, 1, 5),), 5)
        self.assertEqual(rows[0][2], -1)
        self.assertEqual(rows[1][2], -3)
        self.assertEqual(rows[1][3], 1)

    def test_all_4096_signed_deliveries_are_exact_and_admitted(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        events = tuple(e for _ in range(2048) for e in
                       (InputCurrent(0, 0, 32767), InputCurrent(0, 0, -32768)))
        rows = self.check_against_m02(net, events, 1)
        self.assertEqual(rows[0][2], -2048)
        self.assertEqual(rows[0][5], 4096)

    def test_4097_external_deliveries_fail_before_any_trace(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        events = (InputCurrent(0, 0, 0),) * 4097
        self.run_case(net, events, 1, expected_status=5)

    def test_4097_recurrent_deliveries_fail_before_any_trace(self):
        # Legal number of edges (4096) but one more overlapping external event
        # in next tick triggers over-capacity. Tick-0 result MUST NOT leak.
        net = Network((Neuron(threshold=5),),
                      (Synapse(0, 0, 0, 1),) * 4096,
                      state_bits=16)
        events = (InputCurrent(0, 0, 5), InputCurrent(1, 0, 0))
        self.run_case(net, events, 2, expected_status=5)

    def test_horizon_and_shape_validation_no_publication(self):
        net = Network((Neuron(threshold=5),), state_bits=16)
        self.run_case(net, (), 9, expected_status=1)
        self.run_case(Network((), state_bits=16), (), 2, expected_status=1)
        self.run_case(Network((Neuron(),), decay_num=1, decay_den=0,
                              state_bits=16), (), 2, expected_status=1)
        self.run_case(Network((Neuron(),), decay_num=2, decay_den=1,
                              state_bits=16), (), 2, expected_status=1)

    def test_invalid_neuron_synapse_and_external_fail_closed(self):
        self.run_case(Network((Neuron(threshold=0),), state_bits=16), (),
                      2, expected_status=2)
        net_bad_edge = Network((Neuron(),), (Synapse(0, 0, 1, 0),), state_bits=16)
        self.run_case(net_bad_edge, (), 2, expected_status=3)
        self.run_case(Network((Neuron(),), state_bits=16),
                      (InputCurrent(2, 0, 1),), 2, expected_status=4)
        self.run_case(Network((Neuron(),), state_bits=16),
                      (InputCurrent(0, 0, 32768),), 2, expected_status=4)

    def test_seeded_networks_full_trace_and_sparse_schedule(self):
        for seed in range(16):
            with self.subTest(seed=seed):
                rng = random.Random(20261108 + seed)
                count = 5
                net = Network(
                    tuple(Neuron(initial_v=rng.randint(-5, 5),
                                 bias=rng.randint(-2, 2),
                                 threshold=rng.randint(1, 12),
                                 reset_v=rng.randint(-4, 0)) for _ in range(count)),
                    tuple(Synapse(rng.randrange(count), rng.randrange(count),
                                  rng.randint(-7, 7), rng.randint(1, 6))
                          for _ in range(24)),
                    decay_num=rng.randint(0, 10), decay_den=10,
                    state_bits=16)
                events = tuple(InputCurrent(rng.randrange(8),
                                            rng.randrange(count),
                                            rng.randint(-12, 12))
                               for _ in range(35))
                self.check_against_m02(net, events, 8)

if __name__ == "__main__":
    unittest.main()
