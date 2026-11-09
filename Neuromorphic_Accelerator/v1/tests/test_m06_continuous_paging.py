"""M06 continuous paged inference across 64-tick window boundaries (NO FPGA)."""
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
from neuromorphic_accelerator_v1.m06_axi_transport import AXIModelImage, AXIFault, AXIModelError
from neuromorphic_accelerator_v1.m06_block_residency import (
    BlockCache, CanonicalImage, Geometry, ResidencyError,
)
from neuromorphic_accelerator_v1.m06_continuous_paging import PagedContinuousSession
from neuromorphic_accelerator_v1.m06_paged_replay import new_canonical_neuron_image
from neuromorphic_accelerator_v1.m06_shadow_epoch import ShadowEpoch, EpochError


def workload(seed=8, *, n=16, ticks=128):
    rng = random.Random(seed)
    neurons = tuple(
        Neuron(initial_v=rng.randint(-3, 3), bias=rng.randint(-2, 2),
               threshold=rng.randint(4, 9), reset_v=-1)
        for _ in range(n))
    edges = tuple(
        Synapse(rng.randrange(n), rng.randrange(n),
                rng.randint(-5, 5), rng.randint(1, 8))
        for _ in range(48))
    events = tuple(sorted(
        (InputCurrent(rng.randrange(ticks), rng.randrange(n),
                      rng.randint(-10, 10))
         for _ in range(160)),
        key=lambda e: e.tick))
    return Network(neurons, edges, decay_num=2, decay_den=3), events


def geometry(n=16, *, page=2, slots=1, record=16):
    return Geometry(logical_neurons=n, bytes_per_neuron=record,
                    neurons_per_block=page,
                    resident_budget_bytes=page*record*slots,
                    max_model_transfer_bytes=page*record)


def canonical(net, *, slots=1, page=2, axi=False):
    g = geometry(len(net.neurons), page=page, slots=slots)
    original = b"".join(
        p.initial_v.to_bytes(2, "little", signed=True)+bytes(g.bytes_per_neuron-2)
        for p in net.neurons)
    if axi:
        return AXIModelImage(g, emulated_owner="MODEL", initial=original)
    return CanonicalImage(g, emulated_owner="MODEL", initial=original)


class ContinuousPagedSessionTests(unittest.TestCase):
    def test_128_ticks_64_64_recurrent_windows_exact_m02_event_and_m03(self):
        net, ev = workload()
        store = canonical(net, axi=True)
        cache = BlockCache(store, owner="MODEL")
        session = PagedContinuousSession(net, ev, total_ticks=128, cache=cache)
        rec0 = session.run_window(64)
        self.assertEqual((rec0.first_tick, rec0.end_tick_exclusive,
                          rec0.canonical_flushed), (0, 64, True))
        self.assertEqual(len(session.trace.voltage_rows), 64)
        rec1 = session.run_window(128)
        result = session.finalize()
        dense = evaluate_dense(net, ev, ticks=128)
        sparse = evaluate_exact_sparse(net, ev, ticks=128)
        self.assertEqual(session.trace, dense)
        self.assertEqual(session.trace, evaluate_events(net, ev, ticks=128))
        self.assertEqual(session.trace, sparse.trace)
        self.assertEqual(session.evaluated_ids_by_tick, sparse.evaluated_ids_by_tick)
        self.assertEqual(session.touched_ids_by_tick, sparse.destinations_by_tick)
        self.assertEqual(session.deliveries_by_tick, sparse.deliveries_by_tick)
        self.assertEqual(session.fanout_edges_by_tick, sparse.traversed_synapses_by_tick)
        self.assertEqual(result["ticks"], 128)
        self.assertEqual(result["windows"], 2)
        self.assertEqual(result["vendor_axi"], "NOT_TESTED")
        self.assertGreater(cache.counters.dirty_evictions, 100)
        self.assertGreater(rec0.emitted_spikes+rec1.emitted_spikes, 0)
        self.assertFalse(cache.poisoned)
        final = store.snapshot(owner="MODEL")
        for i, expected_v in enumerate(dense.voltage_rows[-1]):
            row = final[16*i:16*(i+1)]
            self.assertEqual(int.from_bytes(row[:2], "little", signed=True),
                             expected_v)
            stamp = max((t+1 for t, es in
                         enumerate(sparse.evaluated_ids_by_tick) if i in es),
                        default=0)
            self.assertEqual(int.from_bytes(row[2:6], "little"), stamp)

    def test_cross_window_delay8_and_zero_event_touch(self):
        net = Network(
            neurons=(Neuron(threshold=5), Neuron(threshold=5),
                     Neuron(), Neuron()),
            synapses=(Synapse(0, 1, 5, delay=8), Synapse(1, 0, 0, delay=8)))
        ev = (InputCurrent(63, 0, 5), InputCurrent(70, 2, 0))
        store = canonical(net, page=2)
        session = PagedContinuousSession(
            net, ev, total_ticks=80, cache=BlockCache(store, owner="MODEL"))
        session.run_window(64)
        self.assertEqual(session.trace.spike_rows[63], (0,))
        session.run_window(80)
        self.assertEqual(session.trace.spike_rows[71], (1,))
        self.assertEqual(session.touched_ids_by_tick[70], (2,))
        self.assertEqual(session.touched_ids_by_tick[79], (0,))
        self.assertEqual(session.trace, evaluate_dense(net, ev, ticks=80))
        self.assertEqual(session.finalize()["ticks"], 80)

    def test_irregular_1_63_64_127_128_odd_window_boundaries(self):
        net, ev = workload(seed=19, ticks=128)
        s1 = canonical(net)
        seq = PagedContinuousSession(
            net, ev, total_ticks=128, cache=BlockCache(s1, owner="MODEL"))
        for end in (1, 63, 64, 127, 128):
            seq.run_window(end)
        seq.finalize()
        self.assertEqual(seq.trace, evaluate_dense(net, ev, ticks=128))
        self.assertEqual(len(seq.receipts), 5)
        self.assertEqual(seq.counters["hits"]+seq.counters["misses"],
                         seq.counters["accesses"])

    def test_256_tick_four_window_bounded_source_horizon(self):
        net = Network(
            neurons=(Neuron(bias=1, threshold=7, reset_v=0),
                     Neuron(threshold=3), Neuron(), Neuron()),
            synapses=(Synapse(0, 1, 4, 8), Synapse(1, 0, -2, 1)))
        ev = (InputCurrent(0, 0, 7), InputCurrent(192, 0, 9),
              InputCurrent(255, 1, 0))
        source = canonical(net)
        ses = PagedContinuousSession(
            net, ev, total_ticks=256, cache=BlockCache(source, owner="MODEL"))
        for end in (64, 128, 192, 256):
            ses.run_window(end)
        self.assertEqual(ses.trace, evaluate_dense(net, ev, ticks=256))
        self.assertEqual(len(ses.receipts), 4)
        ses.finalize()
        self.assertEqual(ses.status, "COMPLETE_UNCOMMITTED")

    def test_window_must_progress_without_skips_and_cannot_finalize_early(self):
        net = Network(neurons=(Neuron(), Neuron()))
        source = canonical(net)
        s = PagedContinuousSession(
            net, (), total_ticks=128, cache=BlockCache(source, owner="MODEL"))
        for end in (0, -1, True, 65, 129):
            with self.subTest(end=end), self.assertRaises(ValueError):
                s.run_window(end)
        with self.assertRaisesRegex(ResidencyError, "incomplete"):
            s.finalize()
        s.run_window(64)
        with self.assertRaises(ValueError):
            s.run_window(64)
        s.run_window(128)
        s.finalize()
        with self.assertRaises(ResidencyError):
            s.run_window(128)

    def test_invalid_spec_and_sorted_external_rejected_before_dirty_state(self):
        n = Network(neurons=(Neuron(), Neuron()))
        source = canonical(n)
        for ev, ticks in (
            ((InputCurrent(1, 0, 0), InputCurrent(0, 0, 0)), 3),
            ((), 257),
        ):
            with self.subTest(ev=ev,ticks=ticks), self.assertRaises(ValueError):
                PagedContinuousSession(
                    n, ev, total_ticks=ticks,
                    cache=BlockCache(source, owner="MODEL"))
        self.assertEqual(source.snapshot(owner="MODEL"), bytes(source.geometry.image_bytes))

    def test_4097_external_cannot_enter_initial_scheduler(self):
        net = Network(neurons=(Neuron(), Neuron()))
        source = canonical(net)
        cache = BlockCache(source, owner="MODEL")
        events = (InputCurrent(0, 0, 0),)*4097
        with self.assertRaisesRegex(ValueError, "delivery capacity"):
            PagedContinuousSession(net, events, total_ticks=2, cache=cache)
        self.assertEqual(cache.counters.accesses, 0)

    def test_lost_write_ack_on_window_boundary_quarantines_session(self):
        net = Network(neurons=(
            Neuron(bias=1, threshold=8), Neuron(), Neuron(), Neuron()))
        source = canonical(net, axi=True)
        ses = PagedContinuousSession(
            net, (), total_ticks=8,
            cache=BlockCache(source, owner="MODEL"))
        source.inject_axi_fault_once(AXIFault("WRITE", "BRESP"))
        with self.assertRaises(AXIModelError):
            ses.run_window(1)
        self.assertEqual(ses.status, "FAILED_REQUIRES_ABORT")
        self.assertTrue(ses.cache.poisoned)
        with self.assertRaises(ResidencyError):
            ses.run_window(2)
        self.assertEqual(source.diagnostic_after_fault(owner="MODEL")
                         ["full_canonical_snapshot_trustworthy"], False)

    def test_shadow_epoch_two_windows_128tick_no_canonical_early_write(self):
        net, ev = workload(seed=11)
        store = canonical(net, page=2, axi=False)
        initial = store.snapshot(owner="MODEL")
        epoch = ShadowEpoch(store, owner="MODEL", epoch_id="continuous-128")
        result = epoch.run_windowed(net, ev, total_ticks=128,
                                    window_end_ticks=(64,128))
        self.assertEqual(epoch.status, "RAN_UNCOMMITTED")
        self.assertEqual(result.trace, evaluate_dense(net, ev, ticks=128))
        self.assertEqual(store.snapshot(owner="MODEL"), initial)
        epoch.verify_against_independent_m02(net, ev, ticks=128)
        self.assertEqual(epoch.status, "VALIDATED_UNCOMMITTED")
        self.assertEqual(store.snapshot(owner="MODEL"), initial)
        receipt = epoch.commit()
        self.assertEqual(receipt.status, "SOFTWARE_COMMITTED_NOT_PHYSICAL_DDR")
        self.assertNotEqual(store.snapshot(owner="MODEL"), initial)

    def test_shadow_epoch_bad_second_window_aborts_without_canonical_commit(self):
        net, ev = workload(seed=9)
        store = canonical(net)
        baseline = store.snapshot(owner="MODEL")
        epoch = ShadowEpoch(store, owner="MODEL", epoch_id="fault-second-window")
        epoch.shadow.inject_axi_fault_once(
            AXIFault("WRITE", "BRESP", burst=0, beat=0))
        with self.assertRaises(AXIModelError):
            epoch.run_windowed(net, ev, total_ticks=128,
                               window_end_ticks=(1, 64, 128))
        self.assertEqual(epoch.status, "FAILED_REQUIRES_ABORT")
        r = epoch.abort()
        self.assertTrue(r["shadow_discarded"])
        self.assertEqual(store.snapshot(owner="MODEL"), baseline)
        with self.assertRaises(EpochError):
            epoch.commit()

    def test_source_scope_no_physical_abi_claim(self):
        net = Network(neurons=(Neuron(), Neuron()))
        s = PagedContinuousSession(
            net, (), total_ticks=1,
            cache=BlockCache(canonical(net), owner="MODEL"))
        receipt = s.run_window(1)
        self.assertEqual(receipt.source_scope, "M06_SOURCE_ONLY_NOT_RTL")
        self.assertEqual(s.finalize()["canonical_atomic_commit"], "NOT_PROVEN")


if __name__ == "__main__":
    unittest.main()
