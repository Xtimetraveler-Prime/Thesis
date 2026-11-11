"""M07.2 four-way policy controls: host-model correctness and fairness gates."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m03_workloads import (
    WorkloadSpec, build_workload,
)
from neuromorphic_accelerator_v1.m03_traffic import ComparisonConfig, compare_workload
from neuromorphic_accelerator_v1.m07_matched_controls import (
    FourWayPolicyConfig, build_matched_locality_report,
    compare_four_way, replay_timestep_oracle_state, _check_accounting,
)
from neuromorphic_accelerator_v1.m06_block_residency import Geometry


def spec(**kwargs):
    return replace(WorkloadSpec(
        neuron_count=32, active_roles=8, fanout_per_active=3,
        external_events_per_tick=4, ticks=8, seed=20261110), **kwargs)


def cfg(**kwargs):
    return replace(FourWayPolicyConfig(
        block_neurons=4, resident_slots=2,
        onchip_state_capacity_bytes=1024, max_model_transfer_bytes=32),
        **kwargs)


class M07MatchedControlsTests(unittest.TestCase):
    def test_all_four_controls_per_policy_neural_role_parity_and_units(self):
        result = build_matched_locality_report(spec(), cfg())
        self.assertTrue(result["matched_neural_work_confirmed"])
        c = result["results_by_locality"]["clustered"]
        d = result["results_by_locality"]["dispersed"]
        self.assertEqual(c["canonical_role_workload_sha256"],
                         d["canonical_role_workload_sha256"])
        self.assertEqual(c["canonical_functional_trace_sha256"],
                         d["canonical_functional_trace_sha256"])
        self.assertNotEqual(c["relabeled_network_input_sha256"],
                            d["relabeled_network_input_sha256"])
        for locality_result in (c, d):
            controls = locality_result["controls_by_policy"]
            self.assertEqual(set(controls), {"direct", "lru"})
            for policy in ("direct", "lru"):
                rows = controls[policy]
                self.assertEqual(set(rows), {"timestep/onchip", "event/onchip",
                                             "timestep/ddr", "event/ddr"})
                for mode, item in rows.items():
                    self.assertTrue(item["available"], mode)
                    self.assertTrue(item["functional_parity_verified"])
                    self.assertEqual(item["canonical_functional_trace_sha256"],
                                     c["canonical_functional_trace_sha256"])
                    self.assertIsNone(item["physical_ddr_bytes"])
                    self.assertIsNone(item["model_timing_cycles"])
                    self.assertIsNone(item["queue_stall_cycles"])
                    self.assertIsNone(item["outstanding_axi_requests"])
                    self.assertIsNone(item["b_before_ar_fence_cycles"])
                    self.assertIsNone(item["hardware_resource_utilization"])
                    self.assertEqual(
                        item["combined_idealized_bytes"],
                        item["state_read_bytes"] + item["state_write_bytes"] +
                        item["synapse_read_bytes_m03_estimate"])
                    self.assertEqual(
                        item["combined_idealized_transactions"],
                        item["state_transactions"] +
                        item["synapse_transactions_m03_estimate"])
                for mode in ("timestep", "event"):
                    self.assertEqual(rows[f"{mode}/onchip"]["state_read_bytes"], 0)
                    self.assertEqual(rows[f"{mode}/onchip"]["state_write_bytes"], 0)
                    self.assertEqual(rows[f"{mode}/onchip"]["synapse_read_bytes_m03_estimate"], 0)
                    self.assertEqual(rows[f"{mode}/onchip"]["state_transactions"], 0)
                for mode in ("timestep", "event"):
                    on, ddr = rows[f"{mode}/onchip"], rows[f"{mode}/ddr"]
                    self.assertEqual(on["evaluated_neuron_steps"],
                                     ddr["evaluated_neuron_steps"])
                    self.assertEqual(on["synapse_edge_visits"],
                                     ddr["synapse_edge_visits"])
                    self.assertEqual(ddr["synapse_read_bytes_m03_estimate"],
                                     ddr["synapse_edge_visits"] * cfg().synapse_record_bytes)
                self.assertEqual(rows["timestep/ddr"]["evaluated_neuron_steps"], 32*8)
                self.assertEqual(rows["event/ddr"]["state_execution_source"],
                                 "M06_PAGED_EXACT_LIF")
                self.assertEqual(rows["timestep/ddr"]["state_execution_source"],
                                 "M02_ORACLE_GUIDED_STATE_MOVEMENT")
                self.assertLessEqual(rows["event/ddr"]["evaluated_neuron_steps"], 32*8)
                for mode in ("timestep/ddr", "event/ddr"):
                    counters = rows[mode]["state_cache_counters_m06_method_level"]
                    self.assertEqual(counters["accesses"],
                                     2*rows[mode]["evaluated_neuron_steps"])
                    self.assertEqual(counters["hits"] + counters["misses"],
                                     counters["accesses"])
                    self.assertEqual(counters["read_bytes"], rows[mode]["state_read_bytes"])
                    self.assertEqual(counters["write_bytes"], rows[mode]["state_write_bytes"])
            for mode in ("timestep/ddr", "event/ddr"):
                direct, lru = controls["direct"][mode], controls["lru"][mode]
                self.assertGreaterEqual(direct["state_read_bytes"] +
                                        direct["state_write_bytes"],
                                        lru["state_read_bytes"] + lru["state_write_bytes"])
                self.assertEqual(direct["state_cache_counters_m06_method_level"]["misses"],
                                 direct["evaluated_neuron_steps"])
                self.assertEqual(direct["direct_invalidations_not_capacity_evictions"],
                                 direct["evaluated_neuron_steps"])
                self.assertEqual(lru["direct_invalidations_not_capacity_evictions"], 0)

    def test_baseline_matches_m03_synapse_estimate_but_not_m01_state_counters(self):
        w = build_workload(spec())
        config = cfg()
        _, m03config = config.validate(len(w.network.neurons))
        old = compare_workload(w, m03config)["four_way_models"]
        new = compare_four_way(w, config)["controls_by_policy"]
        for policy in ("direct", "lru"):
            for mode in ("timestep/ddr", "event/ddr"):
                fresh = new[policy][mode]
                prior = old[mode]
                self.assertEqual(fresh["evaluated_neuron_steps"],
                                 prior["evaluated_neuron_steps"])
                self.assertEqual(fresh["synapse_read_bytes_m03_estimate"],
                                 prior["synapse_read_bytes"])
                self.assertEqual(fresh["synapse_transactions_m03_estimate"],
                                 prior["synapse_transactions"])
                self.assertEqual(fresh["synapse_edge_visits"],
                                 prior["synapse_edge_visits"])
                self.assertEqual(
                    fresh["state_cache_counters_m06_method_level"]["accesses"],
                    2*fresh["evaluated_neuron_steps"])
        # Accepted M03's one-access-per-update, write-on-first-touch traffic
        # is intentionally NOT re-used as M06 method-level state access data.
        self.assertIn("not substituted",
                      compare_four_way(w, config)["m03_original_analytical_state_policy"])

    def test_capacity_unavailable_for_both_policies_without_fake_zero_control(self):
        w = build_workload(spec(neuron_count=128))
        result = compare_four_way(w, cfg(onchip_state_capacity_bytes=1024))
        self.assertEqual(result["full_comparator_state_bytes"], 2048)
        for policy in ("direct", "lru"):
            for mode in ("timestep/onchip", "event/onchip"):
                unavailable = result["controls_by_policy"][policy][mode]
                self.assertFalse(unavailable["available"])
                self.assertIn("exceeds", unavailable["reason"])
                self.assertNotIn("state_read_bytes", unavailable)
                self.assertIsNone(unavailable["model_timing_cycles"])
            for mode in ("timestep/ddr", "event/ddr"):
                self.assertTrue(result["controls_by_policy"][policy][mode]["available"])

    def test_zero_work_event_and_full_timestep_oracle_dense_state_access(self):
        w = build_workload(spec(external_events_per_tick=0,
                                fanout_per_active=0))
        out = compare_four_way(w, cfg())
        for policy in ("direct", "lru"):
            rows = out["controls_by_policy"][policy]
            event = rows["event/ddr"]
            dense = rows["timestep/ddr"]
            self.assertEqual(event["evaluated_neuron_steps"], 0)
            self.assertEqual(event["state_read_bytes"] + event["state_write_bytes"], 0)
            self.assertEqual(event["synapse_read_bytes_m03_estimate"], 0)
            self.assertEqual(dense["evaluated_neuron_steps"], 32*8)
            self.assertGreater(dense["state_read_bytes"], 0)
            self.assertTrue(dense["functional_parity_verified"])

    def test_multiple_fixed_event_locality_pairs_and_budget_knobs(self):
        # Each case holds all role-level spike/delivery/edge counts fixed
        # between clustered and dispersed; different budgets/groups are
        # separate experiments rather than one resource-matched RTL design.
        for slots, group, seed in ((1, 2, 17), (2, 4, 23), (4, 8, 29)):
            with self.subTest(slots=slots, group=group):
                result = build_matched_locality_report(
                    spec(seed=seed),
                    cfg(resident_slots=slots, block_neurons=group,
                        onchip_state_capacity_bytes=2048))
                a = result["results_by_locality"]["clustered"]
                b = result["results_by_locality"]["dispersed"]
                for policy in ("direct", "lru"):
                    for mode in ("timestep/ddr", "event/ddr"):
                        left = a["controls_by_policy"][policy][mode]
                        right = b["controls_by_policy"][policy][mode]
                        for field in ("evaluated_neuron_steps",
                                      "synapse_edge_visits",
                                      "synapse_read_bytes_m03_estimate"):
                            self.assertEqual(left[field], right[field])
                        self.assertEqual(left["canonical_functional_trace_sha256"],
                                         right["canonical_functional_trace_sha256"])

    def test_invalid_resource_budget_record_width_and_wrong_precision_fail_closed(self):
        for config in (
            cfg(state_bytes=2), cfg(block_neurons=3), cfg(resident_slots=0),
            cfg(resident_slots=True), cfg(block_neurons=True),
            cfg(onchip_state_capacity_bytes=128),
            cfg(max_model_transfer_bytes=0),
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                compare_four_way(build_workload(spec()), config)
        with self.assertRaises(ValueError):
            compare_four_way(build_workload(spec(state_bits=8)), cfg())
        w = build_workload(spec())
        with self.assertRaises(ValueError):
            replay_timestep_oracle_state(
                w, Geometry(logical_neurons=8, bytes_per_neuron=16,
                            neurons_per_block=2, resident_budget_bytes=32,
                            max_model_transfer_bytes=16), policy="direct")
        with self.assertRaises(ValueError):
            replay_timestep_oracle_state(w, cfg().validate(32)[0], policy="fifo")

    def test_invalid_accounting_cannot_pass_fairness_gate(self):
        counts = {"accesses": 2, "hits": 1, "misses": 1,
                  "read_bytes": 64, "read_transactions": 2,
                  "write_bytes": 64, "write_transactions": 2}
        geom = cfg().validate(32)[0]
        _check_accounting(counts, geom, 1)
        for key, wrong in (("accesses", 3), ("misses", 2),
                           ("read_bytes", 32), ("read_transactions", 1),
                           ("write_bytes", 65), ("write_transactions", 1)):
            broken = dict(counts, **{key: wrong})
            with self.subTest(key=key), self.assertRaises(AssertionError):
                _check_accounting(broken, geom, 1)

    def test_cli_exclusive_artifact_and_capacity_flag(self):
        cmd = [sys.executable, str(ROOT / "scripts/m07_four_way.py"),
               "--neurons", "32", "--active-roles", "8", "--ticks", "4",
               "--block-neurons", "4", "--resident-slots", "2",
               "--onchip-capacity-bytes", "1024", "--max-transfer-bytes", "32"]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "matched_model.json"
            first = subprocess.run(cmd + ["--output", str(output)],
                                   capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            initial = output.read_bytes()
            again = subprocess.run(cmd + ["--output", str(output)],
                                   capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(output.read_bytes(), initial)
            data = json.loads(initial)
            self.assertTrue(data["matched_neural_work_confirmed"])
            self.assertFalse(data["physical_hardware_measured"])
            self.assertEqual(set(data["results_by_locality"]),
                             {"clustered", "dispersed"})
            for locality in data["results_by_locality"].values():
                self.assertFalse(locality["vendor_hls_amd_executed"])
                self.assertFalse(locality["physical_board_accessed"])


if __name__ == "__main__":
    unittest.main()
