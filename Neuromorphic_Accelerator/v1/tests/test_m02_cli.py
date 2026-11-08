"""M02 reproducible original dense/event oracle report and no-overwrite tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m02_reference_check import run_original_reference_check


class M02ReferenceReportTests(unittest.TestCase):
    def test_original_fixture_output_is_deterministic(self):
        a = run_original_reference_check(seed=20261107, random_cases=7)
        b = run_original_reference_check(seed=20261107, random_cases=7)
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))
        self.assertEqual(a["status"], "PC_ONLY_PROVISIONAL_M02_REFERENCE_NO_HARDWARE")
        self.assertEqual(a["total_cases"], 11)
        self.assertTrue(all(p["equal_dense_vs_event_queue"] for p in a["cases"]))
        self.assertEqual(a["cases"][0]["voltage_rows"], [[3], [0], [2], [1]])
        self.assertEqual(a["cases"][0]["emitted_spikes"], [[1, 0]])
        self.assertEqual(a["cases"][1]["emitted_spikes"], [[1, 0], [3, 0]])
        self.assertEqual(a["cases"][2]["emitted_spikes"], [[0, 0], [2, 1], [3, 0]])
        self.assertNotEqual(a["cases"][0]["network_and_input_sha256"],
                            a["cases"][1]["network_and_input_sha256"])

    def test_bad_reference_report_arguments_fail_closed(self):
        for x in (-1, True, 1001, 3.0):
            with self.subTest(x=x), self.assertRaises(ValueError):
                run_original_reference_check(random_cases=x)
        for x in (-1, True, 0.2):
            with self.subTest(seed=x), self.assertRaises(ValueError):
                run_original_reference_check(seed=x, random_cases=0)

    def test_random_zero_keeps_all_four_hand_fixtures(self):
        p = run_original_reference_check(seed=0, random_cases=0)
        self.assertEqual(p["total_cases"], 4)
        self.assertEqual([c["case"] for c in p["cases"]],
                         ["threshold_equality", "autonomous_bias_no_input",
                          "positive_delay_recurrent_loop",
                          "negative_current_and_parallel_edges"])

    def test_original_report_exclusive_creation_and_stable_bytes(self):
        cli = ROOT / "scripts" / "m02_reference_check.py"
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "original_m02_reference.json"
            args = [sys.executable, str(cli), "--seed", "11",
                    "--random-cases", "3", "--out", str(dest)]
            first = subprocess.run(args, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            data = dest.read_bytes()
            self.assertEqual(json.loads(data)["total_cases"], 7)
            second = subprocess.run(args, text=True, capture_output=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(dest.read_bytes(), data)

    def test_report_source_never_claims_device_or_virtualization(self):
        p = run_original_reference_check(random_cases=0)
        self.assertIn("NO_HARDWARE", p["status"])
        self.assertIn("No hardware event scheduling", " ".join(p["limits"]))
        self.assertIn("Every neuron updated every timestep", " ".join(p["limits"]))


if __name__ == "__main__":
    unittest.main()
