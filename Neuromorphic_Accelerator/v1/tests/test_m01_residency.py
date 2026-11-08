"""M01 no-board, standard-library regression and negative tests."""

import json
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neuromorphic_accelerator_v1.m01_residency import (
    APPROACHES, StudyConfig, generate_trace, run_study,
    serial_transfer_estimate_ns, simulate,
)


class ResidencyAccountingTests(unittest.TestCase):
    def config(self, **values):
        params = dict(
            neuron_count=64,
            state_bytes=8,
            resident_budget_bytes=64,
            block_neurons=4,
            hybrid_pinned_neurons=4,
            max_transfer_bytes=16,
        )
        params.update(values)
        return StudyConfig(**params)

    def test_configuration_accepts_matched_budget(self):
        cfg = self.config()
        cfg.validate()
        result = {name: simulate(cfg, (0, 1, 2, 3), approach=name)
                  for name in APPROACHES}
        for row in result.values():
            self.assertLessEqual(row.allocated_resident_bytes,
                                 cfg.resident_budget_bytes)
            self.assertEqual(row.request_count, row.resident_hits + row.misses)

    def test_config_fail_closed(self):
        bad = [
            dict(neuron_count=True),
            dict(state_bytes=0),
            dict(resident_budget_bytes=0),
            dict(block_neurons=0),
            dict(max_transfer_bytes=False),
            dict(neuron_count=65),
            dict(hybrid_pinned_neurons=3),
            dict(hybrid_pinned_neurons=64),
            dict(hybrid_pinned_neurons=-1),
            dict(resident_budget_bytes=31),
            dict(resident_budget_bytes=32, hybrid_pinned_neurons=4),
        ]
        for changed in bad:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.config(**changed).validate()

    def test_trace_is_deterministic_and_work_matched(self):
        kwargs = dict(neuron_count=64, active_neurons=8, requests=80, seed=17)
        a = generate_trace(**kwargs, locality="clustered")
        b = generate_trace(**kwargs, locality="dispersed")
        self.assertEqual(a, generate_trace(**kwargs, locality="clustered"))
        self.assertEqual(b, generate_trace(**kwargs, locality="dispersed"))
        self.assertEqual(len(a), len(b))
        self.assertEqual(len(set(a)), len(set(b)))
        self.assertEqual(len(set(a)), 8)
        self.assertEqual(sorted([a.count(x) for x in set(a)]),
                         sorted([b.count(x) for x in set(b)]))
        # Locality changes where work lands, not how many updates are requested.
        self.assertEqual({x // 4 for x in a}, {0, 1})
        self.assertEqual(len({x // 4 for x in b}), 8)

    def test_trace_validation(self):
        for args in [
            dict(neuron_count=0, active_neurons=1, requests=1),
            dict(neuron_count=4, active_neurons=0, requests=1),
            dict(neuron_count=4, active_neurons=5, requests=5),
            dict(neuron_count=4, active_neurons=4, requests=3),
            dict(neuron_count=4, active_neurons=2, requests=True),
            dict(neuron_count=4, active_neurons=2, requests=2, seed=-1),
            dict(neuron_count=4, active_neurons=2, requests=2, locality="dense"),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                generate_trace(locality="clustered", **{
                    k: v for k, v in args.items() if k != "locality"
                }) if "locality" not in args else generate_trace(**args)

    def test_one_neuron_lru_eviction_dirty_and_end_flush(self):
        cfg = self.config(resident_budget_bytes=32, hybrid_pinned_neurons=0)
        # Per-neuron buffer actually fits four neurons, so force five IDs.
        result = simulate(cfg, (0, 1, 2, 3, 4, 0), approach="individual")
        self.assertEqual(result.request_count, 6)
        self.assertEqual(result.misses, 6)
        self.assertEqual(result.evictions, 2)
        self.assertEqual(result.dirty_evictions, 2)
        self.assertEqual(result.final_dirty_flushes, 4)
        self.assertEqual(result.read_bytes, 6 * 8)
        self.assertEqual(result.write_bytes, 6 * 8)
        self.assertEqual(result.read_transactions, 6)
        self.assertEqual(result.write_transactions, 6)

    def test_one_neuron_lru_hit(self):
        cfg = self.config(hybrid_pinned_neurons=0)
        result = simulate(cfg, (0, 1, 0, 1), approach="individual")
        self.assertEqual((result.resident_hits, result.misses), (2, 2))
        self.assertEqual(result.evictions, 0)
        self.assertEqual((result.read_bytes, result.write_bytes), (16, 16))

    def test_block_burst_and_end_flush(self):
        cfg = self.config(hybrid_pinned_neurons=0)
        result = simulate(cfg, (0, 1, 4), approach="block")
        self.assertEqual((result.resident_hits, result.misses), (1, 2))
        self.assertEqual(result.distinct_residency_units_touched, 2)
        self.assertEqual(result.evictions, 0)
        self.assertEqual(result.final_dirty_flushes, 2)
        self.assertEqual((result.read_bytes, result.write_bytes), (64, 64))
        # Each 4-neuron block is 32 bytes split into two 16-byte transfers.
        self.assertEqual((result.read_transactions, result.write_transactions),
                         (4, 4))

    def test_block_eviction_is_whole_group_and_dirty(self):
        cfg = self.config(resident_budget_bytes=32, hybrid_pinned_neurons=0)
        result = simulate(cfg, (0, 1, 4), approach="block")
        self.assertEqual(result.dynamic_cache_slots, 1)
        self.assertEqual((result.resident_hits, result.misses), (1, 2))
        self.assertEqual(result.evictions, 1)
        self.assertEqual(result.dirty_evictions, 1)
        self.assertEqual(result.final_dirty_flushes, 1)
        self.assertEqual((result.read_bytes, result.write_bytes), (64, 64))

    def test_hybrid_prefetch_cold_start_cost_is_visible(self):
        cfg = self.config()
        result = simulate(cfg, (0, 1, 0), approach="hybrid")
        self.assertEqual(result.pinned_records, 4)
        self.assertEqual(result.prefetch_records, 4)
        self.assertEqual(result.dynamic_cache_slots, 1)
        self.assertEqual((result.read_bytes, result.write_bytes), (32, 16))
        self.assertEqual((result.resident_hits, result.misses), (3, 0))
        self.assertEqual(result.final_dirty_flushes, 2)
        self.assertEqual(result.read_transactions, 2)
        self.assertEqual(result.write_transactions, 1)

    def test_hybrid_pinned_and_unpinned_do_not_double_cache(self):
        cfg = self.config()
        result = simulate(cfg, (0, 1, 4, 5, 8), approach="hybrid")
        self.assertEqual(result.prefetch_records, 4)
        self.assertEqual(result.maximum_used_resident_bytes, 64)
        self.assertEqual(result.dynamic_cache_slots, 1)
        self.assertEqual(result.evictions, 1)
        self.assertEqual(result.distinct_neurons_touched, 5)
        self.assertEqual(result.distinct_residency_units_touched, 4)

    def test_zero_pins_hybrid_equivalent_to_block(self):
        cfg = self.config(hybrid_pinned_neurons=0)
        trace = (0, 1, 4, 0, 8, 4, 12)
        a = simulate(cfg, trace, approach="block").as_dict()
        b = simulate(cfg, trace, approach="hybrid").as_dict()
        a.pop("approach")
        b.pop("approach")
        self.assertEqual(a, b)

    def test_empty_trace_pinned_init_not_inferred_as_work(self):
        cfg = self.config()
        result = simulate(cfg, (), approach="hybrid")
        self.assertEqual((result.request_count, result.prefetch_records), (0, 4))
        self.assertEqual((result.read_bytes, result.write_bytes), (32, 0))
        self.assertEqual(result.as_dict()["hit_rate"], 0.0)

    def test_trace_rejects_invalid_and_boolean_ids(self):
        for trace in [(64,), (-1,), (True,), (0.0,)]:
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                simulate(self.config(), trace, approach="individual")
        with self.assertRaises(ValueError):
            simulate(self.config(), (0,), approach="unknown")

    def test_run_study_reports_only_hypothetical_timing_if_requested(self):
        cfg = self.config()
        k = dict(config=cfg, active_neurons=4, requests=32, seed=20,
                 locality="clustered")
        x = run_study(**k)
        y = run_study(**k)
        self.assertEqual(json.dumps(x, sort_keys=True),
                         json.dumps(y, sort_keys=True))
        self.assertEqual(x["measurement_status"],
                         "PC_ONLY_TRAFFIC_ACCOUNTING_NOT_HARDWARE_MEASURED")
        self.assertEqual(x["illustrative_timing_assumptions"], None)
        self.assertNotIn("hypothetical_serial_memory_ns",
                         x["results"]["block"])
        z = run_study(**k, illustrative_transaction_overhead_ns=250,
                      illustrative_bandwidth_mbps=1000)
        self.assertIn("hypothetical_serial_memory_ns",
                      z["results"]["individual"])
        self.assertEqual(x["trace"]["sha256"], z["trace"]["sha256"])
        with self.assertRaises(ValueError):
            run_study(**k, illustrative_transaction_overhead_ns=300)

    def test_hypothetical_transfer_model_rejects_bad_numbers(self):
        row = simulate(self.config(), (0,), approach="individual")
        for overhead, bw in [(float("nan"), 1000), (-1, 1000),
                             (100, 0), (100, float("inf")),
                             (float("inf"), 1000)]:
            with self.subTest(assumptions=(overhead, bw)), self.assertRaises(ValueError):
                serial_transfer_estimate_ns(row,
                    illustrative_transaction_overhead_ns=overhead,
                    illustrative_bandwidth_mbps=bw)


if __name__ == "__main__":
    unittest.main()
