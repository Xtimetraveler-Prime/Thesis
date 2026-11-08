"""M03 four analytical controls: correctness, matching and fail-closed gating."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from neuromorphic_accelerator_v1.m03_workloads import WorkloadSpec, build_workload
from neuromorphic_accelerator_v1.m03_traffic import ComparisonConfig, compare_workload
from m03_explore import build_report


class FourWayAnalyticalTests(unittest.TestCase):
    def spec(self, **kwargs):
        return replace(WorkloadSpec(neuron_count=128, active_roles=16,
                                    fanout_per_active=3,
                                    external_events_per_tick=6,
                                    ticks=8), **kwargs)

    def test_four_controls_are_same_neural_result_and_safe(self):
        out = build_report(self.spec(), ComparisonConfig())
        self.assertTrue(out["isomorphic_pair_verified"])
        c, d = (out["experimental_results"][key]
                for key in ("clustered", "dispersed"))
        self.assertEqual(c["canonical_role_workload_sha256"],
                         d["canonical_role_workload_sha256"])
        self.assertEqual(c["canonical_functional_trace_sha256"],
                         d["canonical_functional_trace_sha256"])
        self.assertNotEqual(c["relabeled_network_input_sha256"],
                            d["relabeled_network_input_sha256"])
        for result in (c, d):
            self.assertTrue(result["neural_equivalence"]["dense_vs_M02_queued"])
            self.assertTrue(result["neural_equivalence"]["dense_vs_M03_sparse_exact"])
            four = result["four_way_models"]
            self.assertEqual(set(four), {"timestep/onchip", "event/onchip",
                                         "timestep/ddr", "event/ddr"})
            for row in four.values():
                self.assertTrue(row["available"])
                self.assertTrue(row["functional_parity_verified"])
            self.assertEqual(four["event/onchip"]["total_modeled_bytes"], 0)
            self.assertEqual(four["timestep/onchip"]["total_modeled_bytes"], 0)
            self.assertEqual(four["timestep/onchip"]["evaluated_neuron_steps"], 128*8)
            self.assertLessEqual(four["event/onchip"]["evaluated_neuron_steps"],
                                 128*8)
            self.assertEqual(four["timestep/onchip"]["synapse_edge_visits"], 16*3*8)
            self.assertEqual(
                four["event/ddr"]["synapse_read_bytes"],
                four["event/onchip"]["synapse_edge_visits"] * 8
            )
            self.assertEqual(
                four["event/ddr"]["total_modeled_bytes"],
                four["event/ddr"]["state_read_bytes"] +
                four["event/ddr"]["state_write_bytes"] +
                four["event/ddr"]["synapse_read_bytes"]
            )
            self.assertLess(
                four["event/onchip"]["evaluated_neuron_steps"],
                four["timestep/onchip"]["evaluated_neuron_steps"]
            )

    def test_locality_can_change_memory_traffic_without_neural_changes(self):
        data = build_report(self.spec(), ComparisonConfig())
        c, d = (data["experimental_results"][key]
                for key in ("clustered", "dispersed"))
        # No claim which one is always better across all configurations;
        # this chosen deterministic example checks that mapping is observable.
        self.assertNotEqual(
            c["four_way_models"]["event/ddr"]["state_transactions"],
            d["four_way_models"]["event/ddr"]["state_transactions"]
        )
        self.assertEqual(
            c["neural_equivalence"]["total_edge_traversals_when_spiking"],
            d["neural_equivalence"]["total_edge_traversals_when_spiking"]
        )

    def test_zero_event_zero_bias_workload_is_exact_safe_skip(self):
        spec = self.spec(external_events_per_tick=0, fanout_per_active=0)
        report = compare_workload(build_workload(spec), ComparisonConfig())
        neural = report["neural_equivalence"]
        self.assertEqual(neural["total_spikes"], 0)
        self.assertEqual(neural["exact_sparse_neuron_updates"], 0)
        self.assertEqual(neural["dense_neuron_updates"], 128 * 8)
        self.assertEqual(report["four_way_models"]["event/ddr"]["total_modeled_bytes"], 0)
        self.assertGreater(
            report["four_way_models"]["timestep/ddr"]["total_modeled_bytes"], 0
        )

    def test_onchip_capacity_failure_is_reported_not_extrapolated(self):
        spec = self.spec(neuron_count=256)
        report = compare_workload(build_workload(spec), ComparisonConfig())
        for mode in ("timestep", "event"):
            control = report["four_way_models"][f"{mode}/onchip"]
            self.assertFalse(control["available"])
            self.assertIn("exceeds", control["reason"])
            self.assertTrue(report["four_way_models"][f"{mode}/ddr"]["available"])
        self.assertFalse(report["control_design"]["onchip_test_possible"])

    def test_preserved_individual_and_hybrid_controls(self):
        spec = self.spec()
        for policy, pins in (("block", 0), ("individual", 0), ("hybrid", 8)):
            cfg = ComparisonConfig(residency_policy=policy,
                                   hybrid_pinned_neurons=pins)
            row = compare_workload(build_workload(spec), cfg)
            self.assertEqual(
                row["four_way_models"]["event/ddr"]["state_policy_detail"]["approach"],
                policy)
            self.assertTrue(row["four_way_models"]["event/ddr"]["available"])

    def test_model_config_rejects_bad_fairness_and_grouping(self):
        spec = self.spec()
        for cfg in (
            ComparisonConfig(ddr_state_cache_bytes=2048),
            ComparisonConfig(ddr_state_cache_bytes=4096),
            ComparisonConfig(block_neurons=3),
            ComparisonConfig(residency_policy="unknown"),
            ComparisonConfig(state_bytes=0),
            ComparisonConfig(hybrid_pinned_neurons=8),
            ComparisonConfig(residency_policy="hybrid", hybrid_pinned_neurons=15),
            ComparisonConfig(state_bytes=True),
        ):
            with self.subTest(cfg=cfg), self.assertRaises(ValueError):
                compare_workload(build_workload(spec), cfg)

    def test_cli_is_reproducible_and_refuses_overwrite(self):
        cmd = [sys.executable, str(ROOT / "scripts" / "m03_explore.py"),
               "--neuron-count", "64", "--active-roles", "8",
               "--ticks", "4", "--fanout-per-active", "2",
               "--resident-budget-bytes", "512", "--onchip-capacity-bytes", "1024"]
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "synthetic_original.json"
            a = subprocess.run(cmd + ["--out", str(original)],
                               capture_output=True, text=True)
            self.assertEqual(a.returncode, 0, a.stderr)
            raw = original.read_bytes()
            b = subprocess.run(cmd + ["--out", str(original)],
                               capture_output=True, text=True)
            self.assertNotEqual(b.returncode, 0)
            self.assertEqual(original.read_bytes(), raw)
            payload = json.loads(raw)
            self.assertTrue(payload["isomorphic_pair_verified"])
            self.assertEqual(payload["measurement_status"],
                             "PC_ONLY_FUNCTIONAL_ORACLE_AND_ANALYTICAL_TRAFFIC")

    def test_same_role_workload_canonical_hash_is_policy_invariant(self):
        spec = self.spec()
        a = build_report(spec, ComparisonConfig(residency_policy="block"))
        b = build_report(spec, ComparisonConfig(residency_policy="individual"))
        for locality in ("clustered", "dispersed"):
            self.assertEqual(
                a["experimental_results"][locality]["canonical_role_workload_sha256"],
                b["experimental_results"][locality]["canonical_role_workload_sha256"]
            )
            self.assertEqual(
                a["experimental_results"][locality]["canonical_functional_trace_sha256"],
                b["experimental_results"][locality]["canonical_functional_trace_sha256"]
            )

if __name__ == "__main__":
    unittest.main()
