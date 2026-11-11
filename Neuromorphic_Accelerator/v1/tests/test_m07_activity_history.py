"""M07.4 causal completed-evaluation activity history: source-only pilot."""
from __future__ import annotations

from dataclasses import replace
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m03_workloads import WorkloadSpec, build_workload
from neuromorphic_accelerator_v1.m06_block_residency import (
    BlockCache, CanonicalImage, Geometry, NoOwnership, ResidencyError,
)
from neuromorphic_accelerator_v1.m07_activity_cache import ActivityHistoryCache
from neuromorphic_accelerator_v1 import m07_activity_study as pilot
from neuromorphic_accelerator_v1.m07_activity_study import (
    ActivityStudyPlan, run_activity_study,
)
from neuromorphic_accelerator_v1.m07_policy_baseline import run_policy


def geometry():
    return Geometry(
        logical_neurons=8, bytes_per_neuron=16,
        neurons_per_block=2, resident_budget_bytes=64,
        max_model_transfer_bytes=16)


def new_cache():
    g = geometry()
    store = CanonicalImage(g, emulated_owner="M07_TEST")
    return store, ActivityHistoryCache(store, owner="M07_TEST", history_depth=4)


def pair(cache, neuron, value):
    r = cache.read(neuron)
    cache.write(neuron, value.to_bytes(2, "little", signed=True) + r[2:])


def small_plan(**kwargs):
    return replace(
        ActivityStudyPlan(
            neuron_count=32, active_roles=8, fanout_per_active=3,
            events_per_tick=4, ticks=6, seeds=(17,),
            geometries=((2,64), (4,128)),
            history_depths=(2,8), declared_full_onchip_bytes=1024,
        ),
        **kwargs,
    )


class M07ActivityHistoryPolicyTests(unittest.TestCase):
    def test_history_uses_completed_evaluations_only_and_bounded_metadata(self):
        store, cache = new_cache()
        self.assertEqual(cache.completed_page_history, ())
        data = cache.read(0)
        self.assertEqual(cache.completed_page_history, ())
        self.assertEqual(cache.pending_neuron, 0)
        cache.write(0, b"\x01\x00" + data[2:])
        self.assertIsNone(cache.pending_neuron)
        self.assertEqual(cache.completed_page_history, (0,))
        for n in (2, 0, 4, 0, 6, 0):
            pair(cache, n, 1)
        cache.flush()
        self.assertEqual(len(cache.completed_page_history), 4)
        self.assertEqual(cache.peak_history_page_ids, 4)
        self.assertEqual(cache.completed_page_history[-1], 0)
        self.assertLessEqual(len(cache.resident_pages), 2)
        self.assertFalse(cache.poisoned)
        self.assertEqual(cache.counters.accesses, 14)
        self.assertEqual(cache.counters.hits + cache.counters.misses,
                         cache.counters.accesses)
        o = cache.policy_observer()
        self.assertGreater(o["victim_decisions"], 0)
        self.assertGreater(o["victim_candidates_examined"], 0)
        self.assertFalse(o["history_ids_within_declared_state_budget"])
        self.assertIsNone(o["service_cycles"])
        self.assertIsNone(o["hardware_area_lut_ff_bram"])
        self.assertEqual(o["logical_page_id_bits"], 2)
        self.assertNotEqual(store.snapshot(owner="M07_TEST"), bytes(8*16))

    def test_directed_hot_page_trace_changes_victim_but_not_canonical_bytes(self):
        result = pilot._source_microtrace()
        self.assertTrue(result["identical_final_canonical_bytes"])
        self.assertFalse(result["real_neural_equivalence_claim"])
        self.assertLess(
            result["models"]["activity_history"]["misses"],
            result["models"]["lru"]["misses"])
        self.assertGreater(
            result["models"]["activity_history"]["policy_observer"][
                "non_lru_victim_choices"], 0)
        self.assertEqual(result["cache_slots"], 2)

    def test_strict_pair_guards_fail_closed_with_original_canonical_state(self):
        for kind in ("orphan", "second_read", "wrong_neuron", "incomplete_flush"):
            with self.subTest(kind=kind):
                store, cache = new_cache()
                with self.assertRaises(ResidencyError):
                    if kind == "orphan":
                        cache.write(0, bytes(16))
                    else:
                        cache.read(0)
                        if kind == "second_read":
                            cache.read(2)
                        elif kind == "wrong_neuron":
                            cache.write(2, bytes(16))
                        else:
                            cache.flush()
                self.assertTrue(cache.poisoned)
                self.assertEqual(store.snapshot(owner="M07_TEST"), bytes(128))
                self.assertEqual(cache.completed_page_history, ())
                with self.assertRaises(ResidencyError):
                    cache.read(0)

    def test_read_write_faults_and_external_version_replacement_poison(self):
        for kind in ("read", "write", "stale", "revoke"):
            with self.subTest(kind=kind):
                store, cache = new_cache()
                if kind == "read":
                    store.inject_once("read", chunk=1)
                with self.assertRaises((ResidencyError, NoOwnership)):
                    if kind == "read":
                        cache.read(0)
                    elif kind == "write":
                        pair(cache, 0, 3)
                        pair(cache, 2, 4)
                        store.inject_once("write", chunk=1)
                        cache.read(4)  # eviction of dirty M06 page
                    else:
                        cache.read(0)
                        if kind == "stale":
                            store.external_edit_for_negative_test(0, bytes([9])*32)
                        else:
                            store.revoke()
                        cache.write(0, bytes([1])*16)
                self.assertTrue(cache.poisoned)
                if kind == "write":
                    self.assertEqual(cache.counters.write_bytes, 0)
                    self.assertIn(0, cache.dirty_pages)
                    self.assertEqual(
                        store.snapshot(owner="M07_TEST"), bytes(128))
                    self.assertEqual(cache.completed_page_history, (0, 1))
                if kind == "read":
                    self.assertEqual(cache.completed_page_history, ())
                if kind == "stale":
                    self.assertEqual(cache.completed_page_history, ())
                with self.assertRaises(ResidencyError):
                    cache.flush()

    def test_history_depth_invalid_and_neural_zero_work(self):
        g = geometry()
        store = CanonicalImage(g, emulated_owner="M07_TEST")
        for depth in (0, -1, True, 4097, 1.5):
            with self.subTest(depth=depth), self.assertRaises(ValueError):
                ActivityHistoryCache(store, owner="M07_TEST",
                                     history_depth=depth)
        w = build_workload(WorkloadSpec(
            neuron_count=8, active_roles=2, ticks=4,
            fanout_per_active=0, external_events_per_tick=0))
        r = run_policy(w, g, policy="activity_history", history_depth=4)
        self.assertEqual(r["evaluations"], 0)
        self.assertEqual(r["state_transfer_bytes"], 0)
        self.assertEqual(r["activity_history_observer"]["victim_decisions"], 0)
        self.assertEqual(r["activity_history_observer"]["peak_history_page_ids"], 0)
        with self.assertRaises(ValueError):
            run_policy(w, g, policy="lru", history_depth=4)
        with self.assertRaises(ValueError):
            run_policy(w, g, policy="future_oracle")

    def test_matched_m03_oracle_and_cache_policy_hold_all_neural_work(self):
        cfg = small_plan()
        report = run_activity_study(cfg)
        self.assertEqual(report["geometry_seed_cases"], 2)
        self.assertEqual(report["policy_history_comparisons"], 8)
        self.assertFalse(report["lookahead"])
        self.assertFalse(report["reordered_deliveries"])
        self.assertFalse(report["extra_history_and_scan_metadata_fits_declared_state_budget"])
        self.assertEqual(report["neuron_execution_order"],
                         "unchanged M06 ascending neuron ID per logical tick")
        self.assertEqual(sum(report["witnessed_outcomes"][key]
                             for key in ("history_lower_model_bytes",
                                         "history_equal_model_bytes",
                                         "history_higher_model_bytes")), 8)
        for case in report["rows"]:
            self.assertEqual(case["page_bytes"] * case["resident_slots"],
                             case["resident_budget_bytes"])
            self.assertEqual(case["localities"]["clustered"]["neural_work"],
                             case["localities"]["dispersed"]["neural_work"])
            for locality in case["localities"].values():
                self.assertEqual(set(locality["history"]), {"2","8"})
                self.assertEqual(locality["direct"]["misses"],
                                 locality["neural_work"]["evaluations"])
                for depth, history in locality["history"].items():
                    self.assertEqual(history["state_bytes_saved_vs_lru"],
                                     locality["lru"]["state_bytes"]
                                     - history["state_bytes"])
                    self.assertEqual(history["policy_observer"]["history_depth_evaluations"],
                                     int(depth))
                    self.assertIsNone(history["policy_observer"]["service_cycles"])
                    self.assertIsNone(history["policy_observer"]["physical_ddr_bytes"])

    def test_reject_invalid_geometry_or_unmatched_source_before_report(self):
        bad = (
            {"geometries": ((3,128),)},
            {"geometries": ((2,129),)},
            {"geometries": ((2,16),)},
            {"geometries": ((2,1024),)},
            {"geometries": ((2,64),(2,64))},
            {"geometries": ((4,128),(2,64))},
            {"geometries": ((True,64),)},
            {"geometries": ()},
            {"seeds": ()}, {"seeds": (17,17)},
            {"history_depths": (0,)}, {"history_depths": (True,)},
            {"history_depths": (4097,)},
            {"state_bytes": 2}, {"events_per_tick": -1},
            {"neuron_count": True},
        )
        for kwargs in bad:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_activity_study(small_plan(**kwargs))
        original = pilot.run_policy
        count = 0
        def corrupted(*args, **kwargs):
            nonlocal count
            result = copy.deepcopy(original(*args, **kwargs))
            count += 1
            if count == 2:
                result["spikes"] += 1
            return result
        with mock.patch.object(pilot, "run_policy", side_effect=corrupted):
            with self.assertRaisesRegex(AssertionError, "policy changed"):
                run_activity_study(small_plan(geometries=((2,64),)))

    def test_cli_exclusive_source_hashed_artifacts_and_repeatable_results(self):
        cmd = [sys.executable, str(ROOT/"scripts/m07_activity_pilot.py"),
               "--neurons","32","--active-roles","8","--ticks","6",
               "--seeds","17","--geometries","2:64,4:128",
               "--history-depths","2,8",
               "--onchip-capacity-bytes","1024"]
        with tempfile.TemporaryDirectory() as td:
            a,b = (Path(td)/name for name in ("a.json","b.json"))
            x = subprocess.run(cmd+["--output",str(a)],
                               capture_output=True,text=True)
            self.assertEqual(x.returncode,0,x.stderr)
            y = subprocess.run(cmd+["--output",str(b)],
                               capture_output=True,text=True)
            self.assertEqual(y.returncode,0,y.stderr)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            z = subprocess.run(cmd+["--output",str(a)],
                               capture_output=True,text=True)
            self.assertNotEqual(z.returncode,0)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            report=json.loads(a.read_text())
            self.assertEqual(report["schema"],"m07-activity-history-pilot-v1")
            self.assertFalse(report["actual_yana_implementation"])
            self.assertIsNone(report["service_cycles"])
            self.assertEqual(report["geometry_seed_cases"],2)
            self.assertEqual(report["policy_history_comparisons"],8)
            self.assertEqual(len(report["source_sha256"]),10)
            self.assertTrue(all(len(value)==64 for value in report["source_sha256"].values()))


if __name__=="__main__":
    unittest.main()
