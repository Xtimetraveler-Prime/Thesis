"""M01 capacity/group-size sweep invariants and no-overwrite CLI tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from m01_sweep import evaluate_grid, parse_ints


class SweepTests(unittest.TestCase):
    def args(self, **overrides):
        values = dict(
            neuron_count=4096, active_neurons=64, requests=512,
            state_bytes=16, pinned_neurons=32, max_transfer_bytes=256,
            seed=1, block_sizes=(4, 8, 16, 32),
            resident_budgets=(1024, 2048, 4096),
        )
        values.update(overrides)
        return values

    def test_full_sweep_is_deterministic_and_matched_within_cell(self):
        x = evaluate_grid(**self.args())
        y = evaluate_grid(**self.args())
        self.assertEqual(json.dumps(x, sort_keys=True), json.dumps(y, sort_keys=True))
        self.assertEqual(len(x["grid"]), 24)
        self.assertEqual(x["status"], "PC_ONLY_ANALYTICAL_TRAFFIC_NOT_REAL_DDR_OR_SNN")
        by_locality = {}
        for row in x["grid"]:
            by_locality.setdefault(row["locality"], set()).add(row["trace_sha256"])
            self.assertEqual(set(row["results"]), {"individual", "block", "hybrid"})
            for stats in row["results"].values():
                self.assertEqual(stats["misses"] + stats["resident_hits"], 512)
                self.assertLessEqual(stats["allocated_resident_bytes"],
                                     row["resident_budget_bytes"])
                self.assertGreaterEqual(stats["total_transactions"], 0)
        self.assertEqual(len(by_locality["clustered"]), 1)
        self.assertEqual(len(by_locality["dispersed"]), 1)
        self.assertNotEqual(next(iter(by_locality["clustered"])),
                            next(iter(by_locality["dispersed"])))

    def test_reference_example_recorded_from_real_no_board_ci(self):
        sweep = evaluate_grid(**self.args(
            block_sizes=(16,), resident_budgets=(2048,)))
        clustered, dispersed = sweep["grid"]
        self.assertEqual((clustered["locality"], dispersed["locality"]),
                         ("clustered", "dispersed"))
        self.assertEqual(clustered["results"]["individual"]["total_transactions"], 128)
        self.assertEqual(clustered["results"]["block"]["total_transactions"], 8)
        self.assertEqual(clustered["results"]["hybrid"]["total_transactions"], 8)
        self.assertEqual(dispersed["results"]["individual"]["total_transactions"], 128)
        self.assertEqual(dispersed["results"]["block"]["total_transactions"], 902)
        self.assertEqual(dispersed["results"]["hybrid"]["total_transactions"], 913)
        self.assertEqual(dispersed["results"]["block"]["misses"], 451)
        self.assertEqual(dispersed["results"]["block"]["total_bytes"], 230912)

    def test_parameter_list_fails_closed(self):
        self.assertEqual(parse_ints("x", "4,8,16"), (4, 8, 16))
        for raw in ("", "0", "-1,2", "1,1", "2,x", "3,"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_ints("x", raw)

    def test_invalid_sweep_cell_is_not_silently_skipped(self):
        with self.assertRaises(ValueError):
            evaluate_grid(**self.args(block_sizes=(3,)))
        with self.assertRaises(ValueError):
            evaluate_grid(**self.args(resident_budgets=(512,)))

    def test_cli_exclusive_create_does_not_overwrite(self):
        script = ROOT / "scripts" / "m01_sweep.py"
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "m01_original.json"
            cmd = [sys.executable, str(script),
                   "--block-sizes", "16", "--resident-budgets", "2048",
                   "--out", str(output)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = output.read_bytes()
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(original, output.read_bytes())
            self.assertEqual(json.loads(original)["schema"],
                             "m01-capacity-granularity-sweep-v1")


if __name__ == "__main__":
    unittest.main()
