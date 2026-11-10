"""M07.1 direct-fetch versus M06 LRU, source-only contract regressions."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron, Synapse
from neuromorphic_accelerator_v1.m03_sparse_reference import evaluate_exact_sparse
from neuromorphic_accelerator_v1.m03_workloads import WorkloadSpec, build_workload
from neuromorphic_accelerator_v1.m06_block_residency import (
    BlockCache, CanonicalImage, Geometry, NoOwnership, ResidencyError,
)
from neuromorphic_accelerator_v1.m06_paged_replay import (
    new_canonical_neuron_image, replay_with_paging,
)
from neuromorphic_accelerator_v1.m07_policy_baseline import (
    DirectFetchCache, run_policy,
)


def geometry(n=32, *, block=4, slots=2, transfer=16):
    return Geometry(logical_neurons=n, bytes_per_neuron=16,
                    neurons_per_block=block,
                    resident_budget_bytes=16*block*slots,
                    max_model_transfer_bytes=transfer)


def store_and_cache(cache_type=DirectFetchCache):
    g = geometry(n=8, block=2, slots=2)
    store = CanonicalImage(g, emulated_owner="TEST")
    return store, cache_type(store, owner="TEST")


class M07DirectFetchPolicyTests(unittest.TestCase):
    def test_direct_no_reuse_and_lru_reuse_exact_bytes_transactions(self):
        for cls, expected in (
            (DirectFetchCache, (3, 3, 96, 96, 6, 6, 3)),
            (BlockCache, (1, 5, 32, 32, 2, 2, 0)),
        ):
            with self.subTest(cls=cls):
                store, cache = store_and_cache(cls)
                for n, value in ((0, 5), (1, -3), (0, 7)):
                    original = cache.read(n)
                    self.assertEqual(len(original), 16)
                    cache.write(n, value.to_bytes(2, "little", signed=True)
                                + bytes(14))
                cache.flush()
                c = cache.counters
                self.assertEqual(
                    (c.misses, c.hits, c.read_bytes, c.write_bytes,
                     c.read_transactions, c.write_transactions,
                     getattr(cache, "direct_invalidations", 0)),
                    expected)
                self.assertEqual(c.accesses, 6)
                self.assertEqual(c.evictions, 0)
                self.assertFalse(cache.dirty_pages)
                self.assertFalse(cache.poisoned)
                final = store.snapshot(owner="TEST")
                self.assertEqual(int.from_bytes(final[:2], "little", signed=True), 7)
                self.assertEqual(int.from_bytes(final[16:18], "little", signed=True), -3)
                self.assertLessEqual(len(cache.resident_pages), g_slots := 2)
                self.assertEqual(g_slots, cache.geometry.slots)

    def test_matched_m03_recurrent_workload_independent_M02_oracles_and_locality(self):
        pairs = {}
        for locality in ("clustered", "dispersed"):
            workload = build_workload(WorkloadSpec(
                neuron_count=32, active_roles=8, fanout_per_active=3,
                external_events_per_tick=4, ticks=12, seed=20261110,
                locality=locality))
            modes = {
                policy: run_policy(workload, geometry(), policy=policy)
                for policy in ("direct", "lru")
            }
            pairs[locality] = modes
            direct, lru = modes["direct"], modes["lru"]
            for result in (direct, lru):
                self.assertTrue(result["m02_dense_queued_m03_sparse_m06_paged_parity"])
                self.assertTrue(result["canonical_image_and_last_tick_parity"])
                self.assertIsNone(result["physical_ddr_bytes"])
                self.assertIsNone(result["simulated_service_cycles"])
                self.assertIsNone(result["queue_stall_cycles"])
                self.assertIsNone(result["outstanding_axi_requests"])
                counts = result["state_cache_counters"]
                self.assertEqual(counts["hits"] + counts["misses"], counts["accesses"])
                self.assertEqual(counts["accesses"], 2 * result["evaluations"])
                self.assertEqual(result["role_workload_sha256"],
                                 direct["role_workload_sha256"])
            for field in ("canonical_trace_sha256", "evaluations", "spikes",
                          "delivered_events", "fanout_edge_visits",
                          "role_workload_sha256"):
                self.assertEqual(direct[field], lru[field], field)
            self.assertEqual(direct["state_cache_counters"]["misses"],
                             direct["evaluations"])
            self.assertEqual(direct["direct_invalidations_not_evictions"],
                             direct["evaluations"])
            self.assertEqual(lru["direct_invalidations_not_evictions"], 0)
            self.assertLessEqual(lru["state_transfer_bytes"],
                                 direct["state_transfer_bytes"])
            self.assertEqual(direct["state_cache_counters"]["evictions"], 0)
        for field in ("canonical_trace_sha256", "evaluations", "spikes",
                      "delivered_events", "fanout_edge_visits",
                      "role_workload_sha256"):
            self.assertEqual(pairs["clustered"]["direct"][field],
                             pairs["dispersed"]["lru"][field], field)
        self.assertNotEqual(
            pairs["clustered"]["lru"]["relabeled_input_sha256"],
            pairs["dispersed"]["lru"]["relabeled_input_sha256"])

    def test_explicit_signed_delayed_recurrent_zero_and_quiet_neurons(self):
        net = Network(neurons=(
            Neuron(initial_v=-3, bias=1, threshold=6, reset_v=-2),
            Neuron(initial_v=0, bias=0, threshold=4, reset_v=0),
            Neuron(initial_v=0, bias=-1, threshold=8, reset_v=0),
            Neuron(), Neuron(), Neuron(), Neuron(), Neuron()),
            synapses=(Synapse(0, 0, 2, 8), Synapse(0, 1, 5, 1),
                      Synapse(0, 1, -3, 1), Synapse(1, 0, -4, 3),
                      Synapse(1, 1, 4, 8), Synapse(3, 2, 7, 8)),
            decay_num=1, decay_den=2)
        inputs = (InputCurrent(0, 0, 7), InputCurrent(0, 0, -2),
                  InputCurrent(0, 1, 4), InputCurrent(8, 1, -1),
                  InputCurrent(15, 0, 12), InputCurrent(16, 1, 4),
                  InputCurrent(31, 0, 0))
        dense = evaluate_dense(net, inputs, ticks=32)
        self.assertEqual(dense, evaluate_events(net, inputs, ticks=32))
        self.assertEqual(dense, evaluate_exact_sparse(net, inputs, ticks=32).trace)
        for cls in (BlockCache, DirectFetchCache):
            with self.subTest(cls=cls):
                g = geometry(n=8, block=2, slots=1)
                store = new_canonical_neuron_image(net, g, owner="TEST")
                cache = cls(store, owner="TEST")
                run = replay_with_paging(net, inputs, ticks=32, cache=cache)
                self.assertEqual(run.trace, dense)
                self.assertIn(0, run.touched_ids_by_tick[31])
                self.assertTrue(all(v == 0 for row in dense.voltage_rows
                                    for v in row[4:]))
                for i, voltage in enumerate(dense.voltage_rows[-1]):
                    b = store.snapshot(owner="TEST")[16*i:16*i+2]
                    self.assertEqual(int.from_bytes(b, "little", signed=True),
                                     voltage)
                self.assertFalse(cache.dirty_pages)
                self.assertFalse(cache.poisoned)

    def test_zero_event_quiet_workload_never_fetches_a_page(self):
        workload = build_workload(WorkloadSpec(
            neuron_count=32, active_roles=8, fanout_per_active=0,
            external_events_per_tick=0, ticks=8))
        for policy in ("direct", "lru"):
            r = run_policy(workload, geometry(), policy=policy)
            self.assertEqual(r["evaluations"], 0)
            self.assertEqual(r["state_transfer_bytes"], 0)
            self.assertEqual(r["state_transfer_transactions"], 0)
            self.assertEqual(r["state_cache_counters"]["accesses"], 0)

    def test_incomplete_or_wrong_pair_quarantines_without_committing(self):
        for mode in ("orphan_write", "double_read", "wrong_target", "incomplete_flush"):
            with self.subTest(mode=mode):
                store, cache = store_and_cache()
                with self.assertRaises(ResidencyError):
                    if mode == "orphan_write":
                        cache.write(0, bytes(16))
                    else:
                        cache.read(0)
                        if mode == "double_read":
                            cache.read(1)
                        elif mode == "wrong_target":
                            cache.write(1, bytes(16))
                        else:
                            cache.flush()
                self.assertTrue(cache.poisoned)
                self.assertEqual(store.snapshot(owner="TEST"), bytes(8*16))
                with self.assertRaises(ResidencyError):
                    cache.read(0)

    def test_faults_version_change_and_revoke_fail_closed(self):
        for fault in ("read", "write", "version", "revoke"):
            with self.subTest(fault=fault):
                store, cache = store_and_cache()
                if fault == "read":
                    store.inject_once("read", chunk=1)
                with self.assertRaises((ResidencyError, NoOwnership)):
                    if fault == "read":
                        cache.read(0)
                    else:
                        cache.read(0)
                        if fault == "write":
                            store.inject_once("write", chunk=1)
                        elif fault == "version":
                            store.external_edit_for_negative_test(0, bytes([9])*32)
                        elif fault == "revoke":
                            store.revoke()
                        cache.write(0, bytes([3])*16)
                self.assertTrue(cache.poisoned)
                self.assertEqual(cache.direct_invalidations, 0)
                self.assertEqual(cache.counters.write_bytes, 0)
                if fault not in ("version", "revoke"):
                    self.assertEqual(store.snapshot(owner="TEST"), bytes(8*16))
                if fault == "write":
                    self.assertEqual(cache.dirty_pages, (0,))
                    with self.assertRaises(ResidencyError):
                        cache.flush()

    def test_reject_unsupported_policy_bad_geometry_and_incomplete_image(self):
        workload = build_workload(WorkloadSpec(neuron_count=32, active_roles=8,
                                               fanout_per_active=0, ticks=2))
        for policy, geom in (
            ("fifo", geometry()),
            ("direct", geometry(n=8, block=2)),
            ("direct", geometry(n=32, block=3)),
            ("lru", Geometry(logical_neurons=32, bytes_per_neuron=2,
                             neurons_per_block=4, resident_budget_bytes=8,
                             max_model_transfer_bytes=8)),
        ):
            with self.subTest(policy=policy, geom=geom), self.assertRaises(ValueError):
                run_policy(workload, geom, policy=policy)

    def test_cli_exclusive_create_and_source_only_evidence_label(self):
        cmd = [sys.executable, str(ROOT / "scripts" / "m07_cache_baseline.py"),
               "--neurons", "32", "--active-roles", "8",
               "--ticks", "4", "--block-neurons", "4", "--slots", "2"]
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "source_only.json"
            once = subprocess.run(cmd + ["--output", str(out)],
                                  capture_output=True, text=True)
            self.assertEqual(once.returncode, 0, once.stderr)
            original = out.read_bytes()
            twice = subprocess.run(cmd + ["--output", str(out)],
                                   capture_output=True, text=True)
            self.assertNotEqual(twice.returncode, 0)
            self.assertEqual(original, out.read_bytes())
            data = json.loads(original)
            self.assertEqual(data["schema"], "m07-cache-policy-comparison-v1")
            self.assertTrue(data["role_isomorphic_checked"])
            self.assertFalse(data["physical_hardware_measured"])
            self.assertEqual(len(data["results"]), 4)


if __name__ == "__main__":
    unittest.main()
