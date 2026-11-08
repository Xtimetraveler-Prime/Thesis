"""M03 paired-case sweep no-board reproducibility and fail-closed proof gates."""
import json
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m03_sweep import csv_ints, run_sweep


class M03SweepTests(unittest.TestCase):
    def test_small_grid_is_deterministic_and_matched(self):
        args = dict(neuron_counts=(64, 128), fanouts=(0, 3),
                    events_per_tick_values=(0, 4), seeds=(17, 23),
                    ticks=6, active_roles=8)
        a = run_sweep(**args)
        b = run_sweep(**args)
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))
        self.assertEqual(a["paired_role_isomorphic_cases"], 16)
        self.assertEqual(a["independent_pc_seed_count"], 2)
        self.assertTrue(a["not_physical_replicates"])
        seen_hashes = set()
        for row in a["grid"]:
            self.assertEqual(row["dense_neuron_updates"],
                             row["neuron_count"] * row["ticks"])
            self.assertLessEqual(row["exact_sparse_neuron_updates"],
                                 row["dense_neuron_updates"])
            self.assertEqual(set(row["cases"]), {"clustered", "dispersed"})
            for locality in row["cases"]:
                self.assertEqual(len(row["cases"][locality]), 4)
                for mode, values in row["cases"][locality].items():
                    self.assertTrue(values["available"])
                    self.assertGreaterEqual(values["total_modeled_transactions"], 0)
            seen_hashes.add(row["canonical_role_workload_sha256"])
        self.assertEqual(len(seen_hashes), 16)

    def test_high_neuron_count_no_onchip_control_instead_of_extrapolation(self):
        r = run_sweep(neuron_counts=(256,), fanouts=(1,),
                      events_per_tick_values=(2,), seeds=(1,),
                      active_roles=8, ticks=3)
        row = r["grid"][0]
        for locality in ("clustered", "dispersed"):
            self.assertFalse(row["cases"][locality]["event/onchip"]["available"])
            self.assertFalse(row["cases"][locality]["timestep/onchip"]["available"])
            self.assertTrue(row["cases"][locality]["event/ddr"]["available"])
            self.assertTrue(row["cases"][locality]["timestep/ddr"]["available"])

    def test_zero_events_and_zero_fanout_still_valid(self):
        r = run_sweep(neuron_counts=(64,), fanouts=(0,),
                      events_per_tick_values=(0,), seeds=(1,),
                      active_roles=8, ticks=4)
        row = r["grid"][0]
        self.assertEqual(row["spikes"], 0)
        self.assertEqual(row["exact_sparse_neuron_updates"], 0)
        for locality in ("clustered", "dispersed"):
            self.assertEqual(row["cases"][locality]["event/ddr"]["total_modeled_bytes"], 0)

    def test_empty_duplicate_invalid_grid_rejected(self):
        bad = [
            dict(neuron_counts=()),
            dict(neuron_counts=(64, 64)),
            dict(neuron_counts=(0,)),
            dict(fanouts=(-1,)),
            dict(fanouts=(17,)),
            dict(events_per_tick_values=(-1,)),
            dict(seeds=(True,)),
            dict(ticks=False),
            dict(active_roles=0),
        ]
        for options in bad:
            with self.subTest(options=options), self.assertRaises(ValueError):
                run_sweep(**options)

    def test_csv_arguments_fail_closed(self):
        self.assertEqual(csv_ints("x", "0,4,8"), (0, 4, 8))
        for v in ("", "4,4", "a,4", "4,", "-1", "1.5"):
            with self.subTest(v=v), self.assertRaises(ValueError):
                csv_ints("x", v)
        with self.assertRaises(ValueError):
            csv_ints("x", "0", minimum=1)

    def test_cli_report_cannot_overwrite_original(self):
        with tempfile.TemporaryDirectory() as path:
            out = Path(path) / "original_sweep.json"
            args = [
                sys.executable, str(ROOT / "scripts" / "m03_sweep.py"),
                "--neuron-counts", "64", "--fanouts", "0",
                "--events-per-tick-values", "1", "--seeds", "1",
                "--ticks", "2", "--out", str(out),
            ]
            a = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(a.returncode, 0, a.stderr)
            original = out.read_bytes()
            b = subprocess.run(args, capture_output=True, text=True)
            self.assertNotEqual(b.returncode, 0)
            self.assertEqual(original, out.read_bytes())
            self.assertEqual(json.loads(original)["paired_role_isomorphic_cases"], 1)


if __name__ == "__main__":
    unittest.main()
