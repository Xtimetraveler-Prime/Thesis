"""M06 initial SYNTHETIC source-only canonical DDR-block cache tests.

DDR is a Python bytearray with an EMULATED lease; NOT real PS, FPGA, AXI,
DMA or DDR memory. Passing these is NOT physical transfer approval.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m06_block_residency import (
    BlockCache, CanonicalImage, Geometry, NoOwnership, ResidencyError,
)
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron, Synapse


def geometry(**kwargs) -> Geometry:
    config = dict(logical_neurons=8, bytes_per_neuron=2,
                  neurons_per_block=2, resident_budget_bytes=4,
                  max_model_transfer_bytes=4)
    config.update(kwargs)
    return Geometry(**config)


def model(**kwargs) -> tuple[CanonicalImage, BlockCache]:
    g = geometry(**kwargs)
    store = CanonicalImage(g, emulated_owner="TEST_ONLY",
                           initial=bytes(range(g.image_bytes)))
    return store, BlockCache(store, owner="TEST_ONLY")


class M06BlockResidencyTests(unittest.TestCase):
    def test_m01_configurable_block_baseline_and_32bit_logical_bounds(self):
        cfg = Geometry()
        cfg.validate()
        self.assertEqual((cfg.logical_neurons, cfg.bytes_per_neuron,
                          cfg.neurons_per_block, cfg.resident_budget_bytes,
                          cfg.max_model_transfer_bytes), (4096, 16, 16, 2048, 256))
        self.assertEqual((cfg.image_bytes, cfg.page_bytes, cfg.pages, cfg.slots),
                         (65536, 256, 256, 8))
        self.assertEqual(cfg.page_for_neuron(16), 1)
        self.assertEqual(cfg.offset_for_page(1), 256)

    def test_invalid_geometry_ownership_and_overflow_fail_closed(self):
        for bad in (
            {"logical_neurons": True},
            {"logical_neurons": 0},
            {"logical_neurons": 9},
            {"neurons_per_block": 0},
            {"bytes_per_neuron": -1},
            {"resident_budget_bytes": 3},
            {"max_model_transfer_bytes": 5},
            {"max_model_transfer_bytes": False},
            {"logical_neurons": 2**30, "bytes_per_neuron": 4},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                geometry(**bad).validate()
        with self.assertRaises(ValueError):
            CanonicalImage(geometry(), emulated_owner="")
        with self.assertRaises(ValueError):
            CanonicalImage(geometry(), emulated_owner="TEST_ONLY", initial=b"x")
        store = CanonicalImage(geometry(), emulated_owner="TEST_ONLY")
        with self.assertRaises(NoOwnership):
            BlockCache(store, owner="not the owner")

    def test_hit_miss_dirty_writeback_no_state_loss(self):
        store, cache = model()
        self.assertEqual(cache.read(0), bytes([0, 1]))
        self.assertEqual(cache.read(1), bytes([2, 3]))
        cache.write(1, b"\xaa\xbb")
        self.assertEqual(cache.dirty_pages, (0,))
        self.assertEqual(cache.read(2), bytes([4, 5]))
        self.assertEqual(cache.resident_pages, (1,))
        self.assertEqual(store.snapshot(owner="TEST_ONLY")[2:4], b"\xaa\xbb")
        self.assertEqual((cache.counters.misses, cache.counters.hits,
                          cache.counters.evictions, cache.counters.dirty_evictions),
                         (2, 2, 1, 1))
        self.assertEqual((cache.counters.read_bytes, cache.counters.write_bytes),
                         (8, 4))
        cache.counters.validate()

    def test_two_slot_lru_evicts_oldest_and_keeps_budget(self):
        _, cache = model(resident_budget_bytes=8)
        cache.read(0)
        cache.read(2)
        cache.read(0)  # page0 newer than page1
        cache.read(4)  # must evict page1
        self.assertEqual(cache.resident_pages, (0, 2))
        self.assertEqual(cache.counters.evictions, 1)
        self.assertEqual(cache.counters.dirty_evictions, 0)
        self.assertEqual((cache.counters.hits, cache.counters.misses), (1, 3))
        self.assertLessEqual(len(cache.resident_pages), cache.geometry.slots)

    def test_flush_is_idempotent_preserves_all_records_and_updates_versions(self):
        store, cache = model(resident_budget_bytes=8)
        cache.write(0, b"\x7f\x80")
        cache.write(3, b"\xff\x10")
        cache.flush()
        self.assertEqual(cache.dirty_pages, ())
        self.assertEqual((store.version(0, owner="TEST_ONLY"),
                          store.version(1, owner="TEST_ONLY")), (1, 1))
        self.assertEqual((cache.read(0), cache.read(3)), (b"\x7f\x80", b"\xff\x10"))
        before = bytes(store.snapshot(owner="TEST_ONLY"))
        cache.flush()
        self.assertEqual(store.snapshot(owner="TEST_ONLY"), before)
        self.assertEqual(cache.counters.write_bytes, 8)

    def test_illegal_neuron_page_ids_and_record_width_block(self):
        store, cache = model()
        for bad in (-1, True, 8, "0", 1.0):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cache.read(bad)
        for bad in (b"", b"x", b"abc", bytearray(b"ab")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cache.write(0, bad)
        for bad in (-1, 4, True, "1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                store.read_block(bad, owner="TEST_ONLY")
        self.assertEqual(store.snapshot(owner="TEST_ONLY"), bytes(range(16)))

    def test_read_fault_second_chunk_no_half_resident_page(self):
        cfg = geometry(bytes_per_neuron=4, neurons_per_block=4,
                       logical_neurons=8, resident_budget_bytes=16,
                       max_model_transfer_bytes=4)
        store = CanonicalImage(cfg, emulated_owner="TEST_ONLY",
                               initial=bytes(range(cfg.image_bytes)))
        cache = BlockCache(store, owner="TEST_ONLY")
        store.inject_once("read", chunk=2)
        with self.assertRaisesRegex(ResidencyError, "interrupted"):
            cache.read(0)
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.resident_pages, ())
        self.assertEqual(store.snapshot(owner="TEST_ONLY"), bytes(range(32)))
        with self.assertRaisesRegex(ResidencyError, "poisoned"):
            cache.read(0)

    def test_write_fault_mid_transfer_never_commits_half_page(self):
        cfg = geometry(bytes_per_neuron=4, neurons_per_block=4,
                       logical_neurons=8, resident_budget_bytes=16,
                       max_model_transfer_bytes=4)
        store = CanonicalImage(cfg, emulated_owner="TEST_ONLY",
                               initial=bytes(range(cfg.image_bytes)))
        cache = BlockCache(store, owner="TEST_ONLY")
        cache.write(0, b"ABCD")
        store.inject_once("write", chunk=1)
        with self.assertRaisesRegex(ResidencyError, "interrupted"):
            cache.flush()
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.dirty_pages, (0,))
        self.assertEqual(store.snapshot(owner="TEST_ONLY"), bytes(range(32)))
        self.assertTrue(cache.abandon_after_fault()["canonical_image_not_guaranteed_current"])
        with self.assertRaisesRegex(ResidencyError, "poisoned"):
            cache.flush()

    def test_write_fault_during_dirty_eviction_retains_volatile_dirty_state(self):
        store, cache = model()
        cache.write(0, b"\x11\x22")
        store.inject_once("write", chunk=0)
        with self.assertRaisesRegex(ResidencyError, "interrupted"):
            cache.read(2)
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.resident_pages, (0,))
        self.assertEqual(cache.dirty_pages, (0,))
        self.assertEqual(store.snapshot(owner="TEST_ONLY"), bytes(range(16)))

    def test_external_canonical_replacement_rejects_stale_dirty_flush(self):
        store, cache = model()
        cache.write(0, b"\x11\x22")
        store.external_edit_for_negative_test(0, b"STAL")
        with self.assertRaisesRegex(ResidencyError, "stale"):
            cache.flush()
        self.assertTrue(cache.poisoned)
        self.assertEqual(store.snapshot(owner="TEST_ONLY")[:4], b"STAL")
        self.assertEqual(cache.dirty_pages, (0,))

    def test_stale_cache_hit_is_never_served(self):
        store, cache = model()
        cache.read(0)
        store.external_edit_for_negative_test(0, b"NEWW")
        with self.assertRaisesRegex(ResidencyError, "stale"):
            cache.read(0)
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.counters.hits, 0)

    def test_owner_revoke_is_sticky_and_does_not_authorize_physical_ddr(self):
        store, cache = model()
        cache.write(0, b"\x11\x22")
        store.revoke()
        with self.assertRaises(NoOwnership):
            cache.flush()
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.dirty_pages, (0,))
        with self.assertRaises(ResidencyError):
            cache.read(0)
        with self.assertRaises(NoOwnership):
            store.snapshot(owner="TEST_ONLY")
        self.assertEqual(cache.abandon_after_fault()["physical_board"], "NOT_AUTHORIZED")

    def test_duplicate_transfer_service_fails_closed_without_double_read(self):
        store, cache = model()
        # Deliberately simulate unexpected second service while a transfer
        # is outstanding; no actual threads/AXI traffic are involved.
        cache._transfer_active = True
        try:
            with self.assertRaisesRegex(ResidencyError, "overlapping"):
                cache.read(0)
        finally:
            cache._transfer_active = False
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.counters.misses, 0)
        self.assertEqual(store.snapshot(owner="TEST_ONLY"), bytes(range(16)))

    def test_chunk_count_bytes_are_model_only_not_axi_facts(self):
        cfg = geometry(bytes_per_neuron=4, neurons_per_block=4,
                       logical_neurons=8, resident_budget_bytes=16,
                       max_model_transfer_bytes=4)
        store = CanonicalImage(cfg, emulated_owner="TEST_ONLY")
        cache = BlockCache(store, owner="TEST_ONLY")
        self.assertEqual(cache.read(0), bytes(4))
        self.assertEqual((cache.counters.read_bytes, cache.counters.read_transactions),
                         (16, 4))
        cache.write(0, b"\x01\x02\x03\x04")
        cache.flush()
        self.assertEqual((cache.counters.write_bytes, cache.counters.write_transactions),
                         (16, 4))
        self.assertEqual(store.snapshot(owner="TEST_ONLY")[:4], b"\x01\x02\x03\x04")

    def test_backing_short_page_malformed_version_tx_and_tuple_poison(self):
        cfg = geometry()
        for shape in ("short", "bad_version", "bad_tx", "bad_tuple"):
            class BrokenRead(CanonicalImage):
                def read_block(self, page, *, owner):
                    result = super().read_block(page, owner=owner)
                    if shape == "short":
                        return result[0][:-1], result[1], result[2]
                    if shape == "bad_version":
                        return result[0], True, result[2]
                    if shape == "bad_tx":
                        return result[0], result[1], 0
                    return (result[0],)
            store = BrokenRead(cfg, emulated_owner="TEST_ONLY")
            cache = BlockCache(store, owner="TEST_ONLY")
            with self.subTest(shape=shape), self.assertRaises(ResidencyError):
                cache.read(0)
            self.assertTrue(cache.poisoned)
            self.assertEqual(cache.resident_pages, ())
            self.assertEqual(cache.counters.accesses, 0)

    def test_bad_backing_flush_ack_can_never_mark_dirty_page_clean(self):
        cfg = geometry()
        for mode in ("wrong_version", "zero_tx", "short_tuple"):
            class BrokenAck(CanonicalImage):
                def write_block(self, page, data, *, expected_version, owner):
                    version, tx = super().write_block(
                        page, data, expected_version=expected_version, owner=owner)
                    if mode == "wrong_version":
                        return expected_version, tx
                    if mode == "zero_tx":
                        return version, 0
                    return (version,)
            store = BrokenAck(cfg, emulated_owner="TEST_ONLY")
            cache = BlockCache(store, owner="TEST_ONLY")
            cache.write(0, b"\xfa\xce")
            with self.subTest(mode=mode), self.assertRaises(ResidencyError):
                cache.flush()
            self.assertTrue(cache.poisoned)
            self.assertEqual(cache.dirty_pages, (0,))

    def test_bad_eviction_ack_retains_resident_dirty_page(self):
        class BrokenAck(CanonicalImage):
            def write_block(self, page, data, *, expected_version, owner):
                ver, tx = super().write_block(
                    page, data, expected_version=expected_version, owner=owner)
                return ver, True
        cfg = geometry(resident_budget_bytes=4)
        store = BrokenAck(cfg, emulated_owner="TEST_ONLY")
        cache = BlockCache(store, owner="TEST_ONLY")
        cache.write(0, b"\x11\x22")
        with self.assertRaisesRegex(ResidencyError, "dirty-eviction acknowledgment"):
            cache.read(2)
        self.assertTrue(cache.poisoned)
        self.assertEqual(cache.dirty_pages, (0,))
        self.assertEqual(cache.resident_pages, (0,))

    def test_malformed_store_value_error_converted_to_poisoned_contract_error(self):
        class BrokenRead(CanonicalImage):
            def read_block(self, page, *, owner):
                raise ValueError("corrupt bus length")
        store = BrokenRead(geometry(), emulated_owner="TEST_ONLY")
        cache = BlockCache(store, owner="TEST_ONLY")
        with self.assertRaisesRegex(ResidencyError, "malformed backing transfer"):
            cache.read(0)
        self.assertTrue(cache.poisoned)

    def test_exact_m02_dense_oracle_state_preserved_across_repeated_page_churn(self):
        network = Network(
            neurons=tuple(
                Neuron(initial_v=(i % 3) - 1, bias=(i % 4) - 2,
                       threshold=5 + (i % 3), reset_v=0)
                for i in range(8)),
            synapses=(Synapse(0, 7, 4, delay=1),
                      Synapse(7, 1, -3, delay=2)),
            decay_num=1, decay_den=2, state_bits=16)
        events = (InputCurrent(0, 0, 8), InputCurrent(3, 7, 9),
                  InputCurrent(5, 1, -7), InputCurrent(9, 0, 5))
        trace = evaluate_dense(network, events, ticks=12)
        initial = b"".join(n.initial_v.to_bytes(2, "little", signed=True)
                           for n in network.neurons)
        cfg = geometry()
        store = CanonicalImage(cfg, emulated_owner="TEST_ONLY", initial=initial)
        cache = BlockCache(store, owner="TEST_ONLY")
        # This replays the INDEPENDENT M02 voltage trace through the M06
        # storage service, rather than claiming M06 itself computes the LIF.
        for tick, expected_row in enumerate(trace.voltage_rows):
            for i, voltage in enumerate(expected_row):
                prev = (network.neurons[i].initial_v if tick == 0
                        else trace.voltage_rows[tick - 1][i])
                self.assertEqual(int.from_bytes(cache.read(i), "little", signed=True), prev)
                cache.write(i, voltage.to_bytes(2, "little", signed=True))
        cache.flush()
        final = b"".join(v.to_bytes(2, "little", signed=True)
                         for v in trace.voltage_rows[-1])
        self.assertEqual(store.snapshot(owner="TEST_ONLY"), final)
        self.assertGreater(cache.counters.dirty_evictions, 10)
        self.assertGreater(cache.counters.write_transactions, 10)


if __name__ == "__main__":
    unittest.main()
