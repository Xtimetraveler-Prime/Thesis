"""M06 paged inference SOURCE-ONLY tests against INDEPENDENT M02/M03 oracles."""
from __future__ import annotations

from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_event_reference import evaluate_events
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron, Synapse
from neuromorphic_accelerator_v1.m03_sparse_reference import evaluate_exact_sparse
from neuromorphic_accelerator_v1.m06_block_residency import (
    BlockCache, CanonicalImage, Geometry, NoOwnership, ResidencyError,
)
from neuromorphic_accelerator_v1.m06_paged_replay import (
    check_bounded_network, new_canonical_neuron_image, replay_with_paging,
)


def geometry(n: int, *, page=2, slots=1):
    return Geometry(logical_neurons=n, bytes_per_neuron=2,
                    neurons_per_block=page, resident_budget_bytes=2*page*slots,
                    max_model_transfer_bytes=2*page)


def run(net, events, ticks, *, slots=1, page=2):
    g = geometry(len(net.neurons), page=page, slots=slots)
    source = new_canonical_neuron_image(net, g, owner="EMULATED")
    cache = BlockCache(source, owner="EMULATED")
    return replay_with_paging(net, events, ticks=ticks, cache=cache), source, cache


def seeded_network(seed: int = 15, n: int = 12, ticks: int = 32):
    rng = random.Random(seed)
    neurons = tuple(
        Neuron(initial_v=rng.randint(-4, 4),
               bias=rng.randint(-2, 2),
               threshold=rng.randint(3, 7), reset_v=-1)
        for _ in range(n)
    )
    synapses = tuple(
        Synapse(pre=rng.randrange(n), post=rng.randrange(n),
                weight=rng.randint(-7, 7), delay=rng.randint(1, 8))
        for _ in range(34)
    )
    external = tuple(sorted((
        InputCurrent(tick=rng.randrange(ticks),
                     neuron=rng.randrange(n), current=rng.randint(-9, 9))
        for _ in range(80)
    ), key=lambda e:e.tick))
    return Network(neurons=neurons, synapses=synapses,
                   state_bits=16, decay_num=2, decay_den=3), external


class PagedReplaySourceTests(unittest.TestCase):
    def test_recurrent_32_tick_dense_event_sparse_exact_under_single_slot_churn(self):
        net, events = seeded_network()
        actual, store, cache = run(net, events, 32)
        dense = evaluate_dense(net, events, ticks=32)
        event = evaluate_events(net, events, ticks=32)
        sparse = evaluate_exact_sparse(net, events, ticks=32)
        self.assertEqual(actual.trace, dense)
        self.assertEqual(actual.trace, event)
        self.assertEqual(actual.trace, sparse.trace)
        self.assertEqual(actual.evaluated_ids_by_tick, sparse.evaluated_ids_by_tick)
        self.assertEqual(actual.touched_ids_by_tick, sparse.destinations_by_tick)
        self.assertEqual(actual.deliveries_by_tick, sparse.deliveries_by_tick)
        self.assertEqual(actual.fanout_edges_by_tick, sparse.traversed_synapses_by_tick)
        self.assertGreater(cache.counters.evictions, 25)
        self.assertGreater(cache.counters.dirty_evictions, 25)
        self.assertEqual(cache.counters.accesses,
                         cache.counters.hits + cache.counters.misses)
        self.assertLessEqual(len(cache.resident_pages), 1)
        self.assertFalse(cache.poisoned)
        for i, voltage in enumerate(dense.voltage_rows[-1]):
            offset = i * 2
            self.assertEqual(
                int.from_bytes(store.snapshot(owner="EMULATED")[offset:offset+2],
                               "little", signed=True), voltage)

    def test_64_tick_delay8_wheel_wrap_extremes_and_all_oracles(self):
        net = Network(
            neurons=(Neuron(initial_v=-3, bias=1, threshold=6, reset_v=-2),
                     Neuron(initial_v=0, bias=0, threshold=4, reset_v=0),
                     Neuron(initial_v=0, bias=-1, threshold=8, reset_v=0),
                     Neuron(initial_v=0, bias=0, threshold=9, reset_v=0)),
            synapses=(Synapse(0, 0, 2, 8), Synapse(0, 1, 5, 1),
                      Synapse(0, 1, -3, 1), Synapse(1, 0, -4, 3),
                      Synapse(1, 1, 4, 8), Synapse(3, 2, 7, 8)),
            decay_num=1, decay_den=2)
        events = (
            InputCurrent(0, 0, 7), InputCurrent(0, 0, -2),
            InputCurrent(0, 1, 4), InputCurrent(8, 1, -1),
            InputCurrent(15, 0, 12), InputCurrent(16, 1, 4),
            InputCurrent(32, 0, 7), InputCurrent(55, 1, 4),
            InputCurrent(63, 0, 0),
        )
        a, _, cache = run(net, events, 64)
        self.assertEqual(a.trace, evaluate_dense(net, events, ticks=64))
        self.assertEqual(a.trace, evaluate_events(net, events, ticks=64))
        self.assertEqual(a.trace, evaluate_exact_sparse(net, events, ticks=64).trace)
        self.assertIn(0, a.touched_ids_by_tick[-1])  # zero external wakes 0
        self.assertEqual(a.touched_ids_by_tick, evaluate_exact_sparse(net, events, ticks=64).destinations_by_tick)
        self.assertEqual(a.storage_model, "SOFTWARE_BLOCK_CACHE_NO_HARDWARE")
        self.assertGreater(cache.counters.write_bytes, 100)

    def test_silent_neurons_do_not_load_from_canonical_until_touched(self):
        net = Network(neurons=(Neuron(),)*16, synapses=())
        events = (InputCurrent(0, 0, 0), InputCurrent(2, 0, 0))
        result, _, cache = run(net, events, 8)
        self.assertEqual(result.trace, evaluate_dense(net, events, ticks=8))
        self.assertEqual(result.evaluated_ids_by_tick, ((0,), (), (0,), (), (), (), (), ()))
        self.assertEqual(result.emitted_spikes, 0)
        self.assertEqual(cache.counters.misses, 1)
        self.assertEqual(cache.counters.accesses, 4)
        self.assertEqual(cache.counters.write_bytes, 4)

    def test_zero_cancellation_and_signed_saturation_in_paged_records(self):
        net = Network(neurons=(Neuron(threshold=30000), Neuron(threshold=30000)),
                      synapses=(), decay_num=1, decay_den=1)
        evs = tuple([InputCurrent(0, 0, 32767)]*5
                    + [InputCurrent(1, 1, -32768)]*5
                    + [InputCurrent(2, 1, 10), InputCurrent(2, 1, -10)])
        actual, _, _ = run(net, evs, 3)
        self.assertEqual(actual.trace, evaluate_dense(net, evs, ticks=3))
        self.assertEqual(actual.deliveries_by_tick, (5, 5, 2))
        self.assertEqual(actual.touched_ids_by_tick[2], (1,))

    def test_persistent_last_tick_watermarks_survive_dirty_eviction_restore(self):
        net = Network(neurons=tuple(
            Neuron(bias=1 if i in (0, 31) else 0,
                   threshold=100, reset_v=0) for i in range(32)))
        g = Geometry(logical_neurons=32, bytes_per_neuron=16,
                     neurons_per_block=16, resident_budget_bytes=256,
                     max_model_transfer_bytes=256)
        store = new_canonical_neuron_image(net, g, owner="EMULATED")
        cache = BlockCache(store, owner="EMULATED")
        result = replay_with_paging(net, (), ticks=8, cache=cache)
        self.assertEqual(result.trace, evaluate_dense(net, (), ticks=8))
        self.assertGreater(cache.counters.dirty_evictions, 8)
        final = store.snapshot(owner="EMULATED")
        for idx in range(32):
            row = final[idx*16:(idx+1)*16]
            self.assertEqual(int.from_bytes(row[:2], "little", signed=True),
                             8 if idx in (0, 31) else 0)
            self.assertEqual(int.from_bytes(row[2:6], "little"),
                             8 if idx in (0, 31) else 0)
            self.assertEqual(row[6:], bytes(10))

    def test_future_timestamp_from_faulty_page_rejected_and_poisoned(self):
        net = Network(neurons=tuple(
            Neuron(bias=1 if i == 0 else 0) for i in range(16)))
        g = Geometry(logical_neurons=16, bytes_per_neuron=16,
                     neurons_per_block=16, resident_budget_bytes=256,
                     max_model_transfer_bytes=256)
        class BadTimestampImage(CanonicalImage):
            def read_block(self, page, *, owner):
                data, version, tx = super().read_block(page, owner=owner)
                bad = bytearray(data)
                bad[2:6] = (9).to_bytes(4, "little")
                return bytes(bad), version, tx
        store = BadTimestampImage(g, emulated_owner="EMULATED")
        cache = BlockCache(store, owner="EMULATED")
        with self.assertRaisesRegex(ResidencyError, "future last-update"):
            replay_with_paging(net, (), ticks=1, cache=cache)
        self.assertTrue(cache.poisoned)
        self.assertEqual(store.snapshot(owner="EMULATED"), bytes(256))

    def test_repeat_seeded_hybrid_locality_churn_but_same_neural_trace(self):
        net, evs = seeded_network(seed=107, n=16, ticks=24)
        a, _, ca = run(net, evs, 24, slots=1)
        b, _, cb = run(net, evs, 24, slots=8)  # entire 8-page image resident
        self.assertEqual(a.trace, b.trace)
        self.assertEqual(a.trace, evaluate_dense(net, evs, ticks=24))
        self.assertGreater(ca.counters.misses, cb.counters.misses)
        self.assertGreater(ca.counters.read_bytes, cb.counters.read_bytes)
        self.assertLessEqual(len(cb.resident_pages), cb.geometry.slots)

    def test_external_unsorted_or_beyond_bounds_is_rejected_before_any_paging(self):
        net = Network(neurons=(Neuron(), Neuron()))
        for bad in (
            (InputCurrent(1, 0, 1), InputCurrent(0, 0, 1)),
            (InputCurrent(0, 2, 1),),
        ):
            with self.subTest(evs=bad), self.assertRaises(ValueError):
                check_bounded_network(net, bad, 4)
        with self.assertRaises(ValueError):
            check_bounded_network(net, (), 65)
        with self.assertRaises(ValueError):
            check_bounded_network(Network(net.neurons,
                                          (Synapse(0, 1, 1, 9),)), (), 4)
        with self.assertRaises(ValueError):
            check_bounded_network(Network(net.neurons, state_bits=32), (), 4)

    def test_initial_image_and_geometry_validation(self):
        net = Network(neurons=(Neuron(initial_v=-1), Neuron(initial_v=2)))
        with self.assertRaises(ValueError):
            new_canonical_neuron_image(net, geometry(2, page=1), owner="")
        with self.assertRaises(ValueError):
            new_canonical_neuron_image(net, geometry(4), owner="EMULATED")
        good = new_canonical_neuron_image(net, geometry(2), owner="EMULATED")
        self.assertEqual(good.snapshot(owner="EMULATED"), b"\xff\xff\x02\x00")
        good.external_edit_for_negative_test(0, b"FAIL")
        cache = BlockCache(good, owner="EMULATED")
        with self.assertRaisesRegex(ValueError, "not initialized"):
            replay_with_paging(net, (), ticks=1, cache=cache)

    def test_read_fault_poison_requires_new_cache_and_explicit_recovery(self):
        net = Network(neurons=(Neuron(initial_v=1), Neuron()))
        store = new_canonical_neuron_image(net, geometry(2), owner="EMULATED")
        cache = BlockCache(store, owner="EMULATED")
        store.inject_once("read", chunk=0)
        with self.assertRaisesRegex(ResidencyError, "interrupted"):
            replay_with_paging(net, (), ticks=1, cache=cache)
        self.assertTrue(cache.poisoned)
        with self.assertRaisesRegex(ResidencyError, "poisoned"):
            cache.flush()

    def test_emulated_owner_revocation_does_not_prove_linux_memory_ownership(self):
        net = Network(neurons=(Neuron(initial_v=1), Neuron()))
        store = new_canonical_neuron_image(net, geometry(2), owner="EMULATED")
        cache = BlockCache(store, owner="EMULATED")
        store.revoke()
        with self.assertRaises(NoOwnership):
            replay_with_paging(net, (), ticks=2, cache=cache)
        self.assertEqual(store.geometry.page_bytes, 4)

    def test_4097_external_same_tick_rejected_and_quarantined(self):
        net = Network(neurons=(Neuron(threshold=5), Neuron()))
        store = new_canonical_neuron_image(net, geometry(2), owner="EMULATED")
        cache = BlockCache(store, owner="EMULATED")
        events = (InputCurrent(0, 0, 0),)*4097
        with self.assertRaisesRegex(ResidencyError, "4096"):
            replay_with_paging(net, events, ticks=1, cache=cache)
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.counters.accesses, 0)

    def test_future_recurrent_4097_delivery_capacity_overflow_is_fail_closed(self):
        net = Network(neurons=(Neuron(threshold=5), Neuron()),
                      synapses=(Synapse(0, 1, 0, 1),)*4096)
        events = (InputCurrent(0, 0, 5), InputCurrent(1, 1, 0))
        store = new_canonical_neuron_image(net, geometry(2), owner="EMULATED")
        cache = BlockCache(store, owner="EMULATED")
        with self.assertRaisesRegex(ResidencyError, "recurrent arrival capacity"):
            replay_with_paging(net, events, ticks=2, cache=cache)
        self.assertTrue(cache.poisoned)
        self.assertTrue(cache.dirty_pages)
        self.assertEqual(cache.abandon_after_fault()["physical_board"], "NOT_AUTHORIZED")

    def test_reuse_cache_is_not_a_free_second_epoch(self):
        net = Network(neurons=(Neuron(initial_v=1), Neuron()))
        store = new_canonical_neuron_image(net, geometry(2), owner="EMULATED")
        cache = BlockCache(store, owner="EMULATED")
        replay_with_paging(net, (), ticks=1, cache=cache)
        with self.assertRaisesRegex(ValueError, "fresh dedicated"):
            replay_with_paging(net, (), ticks=1, cache=cache)


if __name__ == "__main__":
    unittest.main()
