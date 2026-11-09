"""M06 matched ACTUAL neural work but software-only DDR traffic comparisons."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m06_matched_experiment import (
    matched_network, source_only_sweep, SOURCE_SCOPE,
)


class M06MatchedExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sweep = source_only_sweep()

    def test_12_cases_all_pass_independent_m02_and_no_vendor_claims(self):
        r = self.sweep
        self.assertEqual(r["scope"], SOURCE_SCOPE)
        self.assertEqual(r["schema_rows"], 12)
        self.assertEqual(len(r["rows"]), 12)
        self.assertTrue(r["model_only"])
        self.assertIsNone(r["calibrated_physical_latency"])
        self.assertIsNone(r["calibrated_bandwidth"])
        self.assertEqual(r["physical_board"], "NOT_AUTHORIZED")
        for row in r["rows"]:
            self.assertEqual(row["independent_m02_neural_oracle"], "PASS_SOURCE_ONLY")
            self.assertEqual(row["vendor_smartconnect"], "NOT_SIMULATED")
            self.assertEqual(row["physical_ddr"], "NOT_ACCESSED")
            self.assertEqual(row["neural_spikes"], 64)
            self.assertEqual(row["neuron_evaluations"], 64)
            self.assertGreater(row["axi_downstream_128bit_handshakes"], 0)

    def test_same_role_event_work_and_relocated_id_mappings(self):
        cluster_net, clustered, cids = matched_network("clustered")
        other_net, dispersed, dids = matched_network("dispersed")
        self.assertEqual(cluster_net, other_net)
        self.assertEqual(cids, tuple(range(8)))
        self.assertEqual(dids, tuple(range(0, 64, 8)))
        self.assertEqual(tuple((x.tick, cids.index(x.neuron), x.current)
                               for x in clustered),
                         tuple((x.tick, dids.index(x.neuron), x.current)
                               for x in dispersed))
        with self.assertRaises(ValueError):
            matched_network("hypothetical")

    def test_clustered_neurons_need_fewer_bytes_than_dispersed_for_4and8_blocks(self):
        rows = {(r["group_neurons"], r["resident_budget_bytes"], r["locality"]):r
                for r in self.sweep["rows"]}
        for group in (4, 8):
            for budget in (256, 512):
                c = rows[(group,budget,"clustered")]
                d = rows[(group,budget,"dispersed")]
                self.assertLess(c["source_only_model_transfer_bytes"],
                                d["source_only_model_transfer_bytes"])
                self.assertLess(c["cache_counters"]["misses"],
                                d["cache_counters"]["misses"])
        for r in rows.values():
            cc = r["cache_counters"]
            self.assertEqual(cc["accesses"], cc["hits"]+cc["misses"])
            self.assertEqual(cc["accesses"], 128)  # one read+write per evaluation
            self.assertEqual(cc["read_bytes"]+cc["write_bytes"],
                             r["source_only_model_transfer_bytes"])
            self.assertEqual(cc["read_transactions"]+cc["write_transactions"],
                             r["source_only_model_transactions"])

    def test_cache_capacity_is_real_control_of_model_not_a_speed_claim(self):
        rows = {(r["group_neurons"], r["resident_budget_bytes"], r["locality"]):r
                for r in self.sweep["rows"]}
        for group in (4, 8, 16):
            smaller = rows[(group,256,"dispersed")]
            larger = rows[(group,512,"dispersed")]
            self.assertLessEqual(larger["cache_counters"]["misses"],
                                 smaller["cache_counters"]["misses"])
        self.assertIsNone(self.sweep["calibrated_physical_latency"])

    def test_deterministic_same_inputs_same_full_model_report(self):
        self.assertEqual(source_only_sweep(), self.sweep)
        self.assertEqual(len(self.sweep["neural_role_signature_sha256"]), 64)

    def test_cli_exclusive_output_and_valid_json(self):
        cli = ROOT / "scripts/m06_matched_source_study.py"
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "m06_source.json"
            argv = [sys.executable, str(cli), "--output", str(out)]
            r = subprocess.run(argv, capture_output=True, text=True, check=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("actual vendor/DDR NOT RUN", r.stdout)
            self.assertEqual(json.loads(out.read_text()), self.sweep)
            r2 = subprocess.run(argv, capture_output=True, text=True, check=False)
            self.assertEqual(r2.returncode, 2)
            self.assertIn("no overwrite", r2.stderr)
            self.assertEqual(json.loads(out.read_text()), self.sweep)


if __name__ == "__main__":
    unittest.main()
