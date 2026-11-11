"""M07.3 fixed-byte-budget residency/locality ablations; HOST ONLY."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest import mock
import copy
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuromorphic_accelerator_v1 import m07_ablation_sweep as ablate
from neuromorphic_accelerator_v1.m07_ablation_sweep import (
    AblationPlan, run_ablation,
)


def plan(**changes):
    return replace(
        AblationPlan(neuron_count=32, active_roles=8, ticks=6,
                    fanout_per_active=3, external_events_per_tick=4,
                    seeds=(17,), block_sizes_neurons=(2, 4),
                    resident_budgets_bytes=(128, 256),
                    onchip_state_capacity_bytes=1024),
        **changes,
    )


class M07AblationTests(unittest.TestCase):
    def test_fixed_byte_budget_controls_blocks_slots_and_parity(self):
        report = run_ablation(plan())
        self.assertEqual(report["schema"], "m07-residency-locality-ablation-v1")
        self.assertTrue(report["physical_hardware_measured"] is False)
        self.assertFalse(report["performance_or_yana_equivalence_claim"])
        self.assertEqual(report["num_parameter_combinations"], 4)
        self.assertEqual(report["num_policy_locality_four_way_rows"], 64)
        per_budget = {}
        for row in report["rows"]:
            b = row["resident_budget_bytes"]
            block = row["block_neurons"]
            self.assertEqual(row["page_bytes"], block * 16)
            self.assertEqual(row["resident_slots"], b // row["page_bytes"])
            self.assertEqual(b, row["resident_slots"] * row["page_bytes"])
            self.assertLess(b, plan().onchip_state_capacity_bytes)
            per_budget.setdefault(b, {})[block] = row["resident_slots"]
            left = row["localities"]["clustered"]
            right = row["localities"]["dispersed"]
            self.assertEqual(left["work"], right["work"])
            self.assertEqual(left["work"]["external_input_events"], 6*4)
            self.assertEqual(left["work"]["event_neuron_evaluations"],
                             right["work"]["event_neuron_evaluations"])
            self.assertEqual(left["work"]["spiking_synapse_edge_visits"],
                             right["work"]["spiking_synapse_edge_visits"])
            self.assertNotEqual(left["relabeled_network_input_sha256"],
                                right["relabeled_network_input_sha256"])
            for locality in ("clustered", "dispersed"):
                controls = row["localities"][locality]["controls"]
                self.assertEqual(set(controls), {"direct", "lru"})
                for policy in ("direct", "lru"):
                    self.assertEqual(
                        set(controls[policy]),
                        {"event/onchip", "timestep/onchip",
                         "event/ddr", "timestep/ddr"})
                    for mode, data in controls[policy].items():
                        self.assertTrue(data["available"])
                        self.assertTrue(data["functional_parity_verified"])
                        self.assertIsNone(data["physical_ddr_bytes"])
                        self.assertIsNone(data["service_cycles"])
                        if mode.endswith("/ddr"):
                            self.assertEqual(
                                data["state_transfer_bytes"],
                                data["state_read_bytes"] + data["state_write_bytes"])
                            self.assertEqual(data["synapse_analytical_bytes"],
                                             data["synapse_edge_visits"]*8)
                        else:
                            self.assertEqual(data["state_transfer_bytes"], 0)
            for locality in ("clustered", "dispersed"):
                self.assertEqual(
                    row["event_state_bytes_saved_by_lru"][locality],
                    left["controls"]["direct"]["event/ddr"]["state_transfer_bytes"]
                    - left["controls"]["lru"]["event/ddr"]["state_transfer_bytes"]
                    if locality == "clustered" else
                    right["controls"]["direct"]["event/ddr"]["state_transfer_bytes"]
                    - right["controls"]["lru"]["event/ddr"]["state_transfer_bytes"])
            self.assertEqual(
                row["lru_event_state_locality_penalty_bytes"],
                right["controls"]["lru"]["event/ddr"]["state_transfer_bytes"]
                - left["controls"]["lru"]["event/ddr"]["state_transfer_bytes"])
        self.assertEqual(set(per_budget), {128, 256})
        self.assertEqual(per_budget[128], {2: 4, 4: 2})
        self.assertEqual(per_budget[256], {2: 8, 4: 4})

    def test_same_seed_traces_are_unchanged_across_geometries_and_seeds_separate(self):
        report = run_ablation(plan(seeds=(17, 23)))
        self.assertEqual(report["num_parameter_combinations"], 8)
        for seed in (17, 23):
            matches = [r for r in report["rows"] if r["seed"] == seed]
            self.assertEqual(len(matches), 4)
            self.assertEqual(len({r["canonical_role_workload_sha256"]
                                  for r in matches}), 1)
            self.assertEqual(len({r["canonical_functional_trace_sha256"]
                                  for r in matches}), 1)
            for loc in ("clustered", "dispersed"):
                self.assertEqual(len({
                    r["localities"][loc]["relabeled_network_input_sha256"]
                    for r in matches
                }), 1)
        self.assertNotEqual(report["rows"][0]["canonical_role_workload_sha256"],
                            report["rows"][4]["canonical_role_workload_sha256"])

    def test_no_event_no_fanout_preserves_real_zero_transfer_control(self):
        result = run_ablation(plan(
            fanout_per_active=0, external_events_per_tick=0,
            resident_budgets_bytes=(128,),
            block_sizes_neurons=(2,),
        ))
        row = result["rows"][0]
        for locality in ("clustered", "dispersed"):
            work = row["localities"][locality]["work"]
            self.assertEqual(work["event_neuron_evaluations"], 0)
            self.assertEqual(work["total_spikes"], 0)
            for policy in ("direct", "lru"):
                event = row["localities"][locality]["controls"][policy]["event/ddr"]
                dense = row["localities"][locality]["controls"][policy]["timestep/ddr"]
                self.assertEqual(event["state_transfer_bytes"], 0)
                self.assertEqual(event["synapse_analytical_bytes"], 0)
                self.assertGreater(dense["state_transfer_bytes"], 0)
        self.assertEqual(row["lru_event_state_locality_penalty_bytes"], 0)

    def test_unavailable_onchip_control_has_null_not_fake_zero_traffic(self):
        result = run_ablation(plan(
            onchip_state_capacity_bytes=256,
            resident_budgets_bytes=(128,), block_sizes_neurons=(2,),
        ))
        row = result["rows"][0]
        for locality in ("clustered", "dispersed"):
            for policy in ("direct", "lru"):
                controls = row["localities"][locality]["controls"][policy]
                for mode in ("timestep/onchip", "event/onchip"):
                    self.assertFalse(controls[mode]["available"])
                    self.assertIsNone(controls[mode]["state_transfer_bytes"])
                    self.assertIn("exceeds", controls[mode]["reason"])
                self.assertTrue(controls["event/ddr"]["available"])

    def test_bad_geometry_seeds_resource_assumptions_are_rejected(self):
        cases = (
            {"block_sizes_neurons": (3,)},
            {"block_sizes_neurons": (4, 2)},
            {"block_sizes_neurons": (2, 2)},
            {"block_sizes_neurons": (True,)},
            {"block_sizes_neurons": ()},
            {"resident_budgets_bytes": (32,)},
            {"resident_budgets_bytes": (129,)},
            {"resident_budgets_bytes": (128, 128)},
            {"resident_budgets_bytes": (512,)},
            {"resident_budgets_bytes": (1024,)},
            {"seeds": (23, 17)},
            {"seeds": (True,)},
            {"seeds": ()},
            {"neuron_count": True},
            {"state_bytes": 2},
            {"fanout_per_active": 9},
            {"external_events_per_tick": -1},
            {"max_model_transfer_bytes": False},
        )
        for change in cases:
            with self.subTest(case=change), self.assertRaises(ValueError):
                run_ablation(plan(**change))

    def test_neural_work_mutation_does_not_pass_locality_equivalence(self):
        genuine = ablate.build_matched_locality_report
        def altered(*args, **kwargs):
            result = copy.deepcopy(genuine(*args, **kwargs))
            result["results_by_locality"]["dispersed"]["neural_equivalence"][
                "total_spikes"] += 1
            return result
        with mock.patch.object(ablate, "build_matched_locality_report",
                               side_effect=altered):
            with self.assertRaisesRegex(AssertionError, "locality changed"):
                run_ablation(plan(resident_budgets_bytes=(128,),
                                  block_sizes_neurons=(2,)))

    def test_input_identity_mutation_is_rejected_across_cache_geometries(self):
        genuine = ablate.build_matched_locality_report
        count = 0
        def altered(*args, **kwargs):
            nonlocal count
            count += 1
            result = copy.deepcopy(genuine(*args, **kwargs))
            if count == 2:
                result["results_by_locality"]["clustered"][
                    "relabeled_network_input_sha256"] = "wrong-workload"
            return result
        with mock.patch.object(ablate, "build_matched_locality_report",
                               side_effect=altered):
            with self.assertRaisesRegex(AssertionError, "input mapping"):
                run_ablation(plan(resident_budgets_bytes=(128,)))

    def test_yana_published_1024_neuron_capacity_overlap_is_not_hardware_equivalence(self):
        # YANA arXiv:2604.03432v1 reports 2^10 neurons per core, but this
        # exercises only the SAME LOGICAL COUNT in our M02/M03/M06 software.
        # 16 KiB canonical state cannot fit our declared 2048 B onchip gate.
        p = AblationPlan(
            neuron_count=1024, active_roles=16, ticks=4,
            fanout_per_active=2, external_events_per_tick=4,
            seeds=(17,), block_sizes_neurons=(8, 16),
            resident_budgets_bytes=(256,),
            onchip_state_capacity_bytes=2048,
        )
        result = run_ablation(p)
        self.assertEqual(result["num_parameter_combinations"], 2)
        self.assertEqual(result["num_policy_locality_four_way_rows"], 32)
        self.assertFalse(result["performance_or_yana_equivalence_claim"])
        self.assertFalse(result["physical_hardware_measured"])
        for row in result["rows"]:
            self.assertEqual(row["resident_budget_bytes"], 256)
            self.assertEqual(row["page_bytes"]*row["resident_slots"], 256)
            self.assertEqual(
                row["localities"]["clustered"]["work"],
                row["localities"]["dispersed"]["work"])
            for loc in ("clustered", "dispersed"):
                for policy in ("direct", "lru"):
                    four = row["localities"][loc]["controls"][policy]
                    self.assertFalse(four["timestep/onchip"]["available"])
                    self.assertFalse(four["event/onchip"]["available"])
                    self.assertIsNone(
                        four["timestep/onchip"]["state_transfer_bytes"])
                    self.assertTrue(four["event/ddr"]["available"])
                    self.assertTrue(four["event/ddr"]["functional_parity_verified"])
                    self.assertIsNone(four["event/ddr"]["service_cycles"])
                    self.assertIsNone(four["event/ddr"]["physical_ddr_bytes"])

    def test_cli_is_byte_reproducible_refuses_overwrite_and_proves_source_identity(self):
        cmd = [sys.executable, str(ROOT / "scripts/m07_ablation.py"),
               "--neurons", "32", "--active-roles", "8", "--ticks", "6",
               "--seeds", "17", "--blocks", "2,4", "--budgets", "128",
               "--onchip-capacity-bytes", "1024"]
        with tempfile.TemporaryDirectory() as temp:
            a, b = (Path(temp) / name for name in ("a.json", "b.json"))
            first = subprocess.run(cmd + ["--output", str(a)],
                                   capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(cmd + ["--output", str(b)],
                                    capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            bad = subprocess.run(cmd + ["--output", str(a)],
                                 capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            data = json.loads(a.read_text())
            self.assertEqual(data["num_parameter_combinations"], 2)
            self.assertEqual(data["num_policy_locality_four_way_rows"], 32)
            self.assertFalse(data["physical_hardware_measured"])
            self.assertIn("M07_PRIOR_ART_CONFIGURATION_COMPARISON.md",
                          data["prior_art_comparison_document"])
            self.assertGreaterEqual(len(data["source_sha256"]), 10)
            self.assertTrue(all(len(digest) == 64
                                for digest in data["source_sha256"].values()))


if __name__ == "__main__":
    unittest.main()
