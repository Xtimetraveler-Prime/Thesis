"""M03 role-preserving sparse workloads, deterministic provenance and validation."""
from dataclasses import replace
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m03_workloads import (
    WorkloadSpec, build_workload, canonicalize_trace,
)
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events


class WorkloadGenerationTests(unittest.TestCase):
    def test_role_isomorphism_is_bit_exact_across_locality(self):
        for fanout in (0, 1, 4, 16):
            for events_per_tick in (0, 1, 6):
                for seed in (0, 1234):
                    spec = WorkloadSpec(
                        neuron_count=128, active_roles=16,
                        fanout_per_active=fanout,
                        external_events_per_tick=events_per_tick,
                        seed=seed, ticks=8)
                    a = build_workload(spec)
                    b = build_workload(replace(spec, locality="dispersed"))
                    with self.subTest(fanout=fanout, events=events_per_tick, seed=seed):
                        self.assertEqual(a.canonical_role_sha256,
                                         b.canonical_role_sha256)
                        self.assertNotEqual(a.role_to_neuron, b.role_to_neuron)
                        x = evaluate_dense(a.network, a.external_currents, ticks=8)
                        y = evaluate_dense(b.network, b.external_currents, ticks=8)
                        self.assertEqual(x, evaluate_events(
                            a.network, a.external_currents, ticks=8))
                        self.assertEqual(y, evaluate_events(
                            b.network, b.external_currents, ticks=8))
                        self.assertEqual(canonicalize_trace(a, x),
                                         canonicalize_trace(b, y))
                        self.assertEqual(len(a.external_currents), 8 * events_per_tick)
                        self.assertEqual(len(a.network.synapses), 16 * fanout)
                        self.assertEqual(len(set(a.role_to_neuron)), 16)
                        self.assertEqual(len(set(b.role_to_neuron)), 16)

    def test_determinism_no_rng_global_state(self):
        spec = WorkloadSpec(seed=11)
        one = build_workload(spec)
        two = build_workload(spec)
        self.assertEqual(one, two)
        modified = build_workload(replace(spec, seed=12))
        self.assertNotEqual(one.canonical_role_sha256,
                            modified.canonical_role_sha256)
        self.assertEqual(one.relabeled_input_sha256,
                         two.relabeled_input_sha256)

    def test_disperse_roles_really_spans_address_range(self):
        spec = WorkloadSpec(neuron_count=128, active_roles=8, ticks=4)
        a = build_workload(spec)
        b = build_workload(replace(spec, locality="dispersed"))
        self.assertEqual(a.role_to_neuron, tuple(range(8)))
        self.assertEqual(b.role_to_neuron, (0, 16, 32, 48, 64, 80, 96, 112))
        self.assertEqual(a.canonical_role_sha256, b.canonical_role_sha256)
        self.assertNotEqual(a.relabeled_input_sha256, b.relabeled_input_sha256)

    def test_all_active_roles_support_identity_mapping(self):
        spec = WorkloadSpec(neuron_count=16, active_roles=16, ticks=2,
                            fanout_per_active=2)
        a = build_workload(spec)
        b = build_workload(replace(spec, locality="dispersed"))
        self.assertEqual(a.role_to_neuron, b.role_to_neuron)
        self.assertEqual(a.relabeled_input_sha256, b.relabeled_input_sha256)

    def test_necessary_parameters_fail_closed(self):
        bad = [
            dict(neuron_count=0), dict(neuron_count=True),
            dict(active_roles=0), dict(active_roles=129),
            dict(active_roles=True), dict(ticks=0), dict(ticks=False),
            dict(seed=-1), dict(seed=True), dict(fanout_per_active=-1),
            dict(fanout_per_active=17), dict(fanout_per_active=1.0),
            dict(external_events_per_tick=-1),
            dict(external_events_per_tick=False),
            dict(state_bits=7), dict(state_bits=33), dict(locality="random")
        ]
        for replace_fields in bad:
            with self.subTest(**replace_fields), self.assertRaises(ValueError):
                build_workload(replace(WorkloadSpec(), **replace_fields))

    def test_canonical_trace_fails_if_quiet_state_corrupted(self):
        from neuromorphic_accelerator_v1.m02_types import ReferenceTrace
        work = build_workload(WorkloadSpec(
            neuron_count=32, active_roles=8, ticks=1, seed=0))
        states = [[0] * 32]
        states[0][31] = 1
        with self.assertRaises(AssertionError):
            canonicalize_trace(
                work, ReferenceTrace((tuple(states[0]),), ((),))
            )
        with self.assertRaises(ValueError):
            canonicalize_trace(work, ReferenceTrace((), ()))

if __name__ == "__main__":
    unittest.main()
