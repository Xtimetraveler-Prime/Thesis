"""No-board 256/128 AXI4 software link and paging regression.

Actual AMD SmartConnect vendor RTL is NEVER instantiated. These tests
verify a source-defined expected byte/beat/response/stall model only.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron, Synapse
from neuromorphic_accelerator_v1.m06_axi_transport import (
    AXIBurst, AXIFault, AXIModelError, AXIModelImage,
    join_128_to_256, plan_aligned_incr, split_256_to_128,
)
from neuromorphic_accelerator_v1.m06_block_residency import (
    BlockCache, Geometry, ResidencyError,
)
from neuromorphic_accelerator_v1.m06_paged_replay import replay_with_paging


def geom(*, n=32, page=16, slots=1, maxbytes=32):
    return Geometry(logical_neurons=n, bytes_per_neuron=2,
                    neurons_per_block=page,
                    resident_budget_bytes=page*2*slots,
                    max_model_transfer_bytes=maxbytes)


def simulated(*, n=32, page=16, slots=1, maxbytes=32, base=0,
              watchdog=30, delay=2, initial=None):
    g = geom(n=n, page=page, slots=slots, maxbytes=maxbytes)
    if initial is None:
        initial = bytes([i & 255 for i in range(g.image_bytes)])
    s = AXIModelImage(g, emulated_owner="MODEL", initial=initial,
                      logical_bus_base=base, ready_delay_every=delay,
                      cycle_watchdog=watchdog)
    return s, BlockCache(s, owner="MODEL")


class AXIContractTests(unittest.TestCase):
    def test_default_256_byte_block_plan_256_128_and_len_size(self):
        bursts = plan_aligned_incr(0x4000, 256)
        self.assertEqual(len(bursts), 1)
        b = bursts[0]
        self.assertEqual((b.upstream_beats, b.upstream_len, b.upstream_size),
                         (8, 7, 5))
        self.assertEqual((b.downstream_len, b.downstream_size), (15, 4))
        self.assertEqual(b.nbytes, 256)

    def test_real_4k_boundary_split_is_explicit_and_legal(self):
        bursts = plan_aligned_incr(0xFE0, 96, max_bytes=96)
        self.assertEqual([(b.address, b.nbytes) for b in bursts],
                         [(0xFE0, 32), (0x1000, 64)])
        for b in bursts:
            self.assertEqual(b.address // 4096,
                             (b.address+b.nbytes-1)//4096)

    def test_downstream_max_256_beats_caps_upstream_at_128(self):
        bursts = plan_aligned_incr(0, 8192, max_bytes=8192)
        self.assertEqual([(b.upstream_beats, b.downstream_len)
                          for b in bursts], [(128, 255), (128, 255)])
        self.assertEqual([b.address for b in bursts], [0, 4096])

    def test_bad_alignment_len_boolean_negative_overflow_unsupported(self):
        for args in (
            (1, 32, 256), (0, 33, 256), (0, 32, 40),
            (0, 32, 16), (0, 32, 8193),
            (0xffffffE0, 64, 256),
            (True, 32, 256), (0, True, 256),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                plan_aligned_incr(args[0], args[1], max_bytes=args[2])
        with self.assertRaises(ValueError):
            AXIBurst(0xff0, 2)
        with self.assertRaises(ValueError):
            AXIBurst(0, 0)

    def test_lane_preserving_round_trip_and_noncontiguous_wstrb(self):
        raw = bytes(range(32))
        (low, strobelo), (high, strobehi) = split_256_to_128(raw, 0x80000001)
        self.assertEqual((low, high), (raw[:16], raw[16:]))
        self.assertEqual((strobelo, strobehi), (1, 0x8000))
        self.assertEqual(join_128_to_256(low, high), raw)
        for data, mask in ((raw[:16], 0), (raw, -1),
                           (raw, 1<<32), (bytearray(raw), 1)):
            with self.subTest(data=data,mask=mask), self.assertRaises(ValueError):
                split_256_to_128(data, mask)
        with self.assertRaises(ValueError):
            join_128_to_256(raw, raw)

    def test_simulated_page_load_dirty_evict_restore_via_axi_bursts(self):
        s, c = simulated()
        self.assertEqual(c.read(0), b"\x00\x01")
        c.write(15, b"\xa5\x5a")  # upper half of final 256-bit DMA beat
        self.assertEqual(c.read(15), b"\xa5\x5a")
        self.assertEqual(c.read(16), b"\x20\x21")  # evict dirty page0
        self.assertEqual(c.read(15), b"\xa5\x5a")  # reload page0
        c.flush()
        self.assertEqual(s.snapshot(owner="MODEL")[30:32], b"\xa5\x5a")
        self.assertEqual(c.counters.dirty_evictions, 1)
        self.assertEqual(c.counters.read_transactions, 3)
        self.assertEqual(c.counters.write_transactions, 1)
        self.assertTrue(any(x["direction"] == "WRITE" for x in s.burst_log))

    def test_burst_multi_chunk_partial_page_and_high_lane_preserved(self):
        s, c = simulated(n=128, page=32, slots=1, maxbytes=32)
        self.assertEqual(c.read(31), b"\x3e\x3f")
        c.write(31, b"\xf0\x0d")
        c.flush()
        self.assertEqual(s.snapshot(owner="MODEL")[62:64], b"\xf0\x0d")
        self.assertEqual([x["direction"] for x in s.burst_log],
                         ["READ", "READ", "WRITE", "WRITE"])
        self.assertEqual(c.counters.read_transactions, 2)
        self.assertEqual(c.counters.write_transactions, 2)

    def test_real_4k_boundary_splits_page_load_and_write(self):
        s, c = simulated(n=64, page=32, slots=1, maxbytes=64, base=4064)
        c.write(31, b"\x11\xff")
        c.flush()
        self.assertEqual([x["address"] for x in s.burst_log],
                         [4064, 4096, 4064, 4096])
        self.assertEqual(s.snapshot(owner="MODEL")[62:64], b"\x11\xff")

    def test_ready_valid_each_payload_is_held_stable_through_stalls(self):
        s, c = simulated()
        self.assertEqual(c.read(0), b"\x00\x01")
        self.assertTrue(any(n > 0 for n in s.stalls.values()))
        trace = s.channel_trace
        for i, sample in enumerate(trace):
            self.assertTrue(sample["valid"])
            self.assertEqual(len(sample["payload_sha256"]), 64)
            if not sample["ready"]:
                self.assertLess(i+1, len(trace))
                following = trace[i+1]
                self.assertEqual(following["channel"], sample["channel"])
                self.assertEqual(following["payload_sha256"],
                                 sample["payload_sha256"])
        self.assertEqual(s.handshakes["U_AR"], 1)
        self.assertEqual(s.handshakes["D_AR"], 1)
        self.assertEqual(s.handshakes["D_R"], 2)
        self.assertEqual(s.handshakes["U_R"], 1)

    def test_read_rresp_error_must_poison_page_no_trustworthy_read(self):
        s, c = simulated()
        s.inject_axi_fault_once(AXIFault("READ", "RRESP", 0, 1))
        with self.assertRaisesRegex(AXIModelError, "RRESP"):
            c.read(0)
        self.assertTrue(c.poisoned)
        self.assertEqual(c.resident_pages, ())
        with self.assertRaisesRegex(ResidencyError, "poisoned"):
            c.read(0)
        self.assertEqual(s.snapshot(owner="MODEL"), bytes(range(64)))

    def test_missing_d_r_ready_hits_watchdog_without_fake_success(self):
        s, c = simulated(watchdog=4, delay=0)
        s.inject_axi_fault_once(AXIFault("READ", "READY_TIMEOUT", 0, 0))
        with self.assertRaisesRegex(AXIModelError, "stalled beyond"):
            c.read(0)
        self.assertEqual(s.handshakes.get("D_R", 0), 0)
        self.assertTrue(c.poisoned)
        self.assertEqual(s.snapshot(owner="MODEL"), bytes(range(64)))

    def test_partial_w_timeout_leaves_uncertain_canonical_and_quarantined_cache(self):
        s, c = simulated(watchdog=3, delay=0)
        c.write(0, b"\xfe\xed")
        # Downstream beat0 has committed when downstream beat1 is held.
        s.inject_axi_fault_once(AXIFault("WRITE", "READY_TIMEOUT", 0, 1))
        with self.assertRaisesRegex(AXIModelError, "stalled beyond"):
            c.flush()
        self.assertTrue(c.poisoned)
        self.assertEqual(s.uncertain_pages, {0})
        self.assertFalse(s.diagnostic_after_fault(owner="MODEL")
                         ["full_canonical_snapshot_trustworthy"])
        self.assertEqual(bytes(s._bytes[:2]), b"\xfe\xed")
        with self.assertRaisesRegex(AXIModelError, "snapshot forbidden"):
            s.snapshot(owner="MODEL")
        other = BlockCache(s, owner="MODEL")
        with self.assertRaisesRegex(AXIModelError, "uncertain"):
            other.read(0)
        self.assertTrue(other.poisoned)

    def test_writes_that_get_bresp_error_are_uncertain_not_assumed_atomic(self):
        s, c = simulated(delay=0)
        c.write(0, b"\x7e\x19")
        s.inject_axi_fault_once(AXIFault("WRITE", "BRESP"))
        with self.assertRaisesRegex(AXIModelError, "BRESP"):
            c.flush()
        self.assertTrue(c.poisoned)
        self.assertEqual(s.uncertain_pages, {0})
        self.assertEqual(bytes(s._bytes[:2]), b"\x7e\x19")
        self.assertTrue(c.dirty_pages)

    def test_lost_write_response_cannot_be_safely_retried(self):
        s, c = simulated(watchdog=4, delay=0)
        c.write(0, b"\xf0\x0d")
        s.inject_axi_fault_once(AXIFault("WRITE", "RESPONSE_LOST"))
        with self.assertRaisesRegex(AXIModelError, "stalled beyond"):
            c.flush()
        self.assertEqual(bytes(s._bytes[:2]), b"\xf0\x0d")
        self.assertTrue(c.poisoned)
        self.assertEqual(s.uncertain_pages, {0})
        with self.assertRaises(ResidencyError):
            c.flush()

    def test_axi_image_invalid_alignment_range_and_fault_shape(self):
        with self.assertRaises(ValueError):
            AXIModelImage(geom(page=2), emulated_owner="MODEL")
        with self.assertRaises(ValueError):
            AXIModelImage(geom(), emulated_owner="MODEL", logical_bus_base=16)
        with self.assertRaises(ValueError):
            AXIModelImage(geom(), emulated_owner="MODEL",
                          logical_bus_base=0xffffffe0)
        for args in (("READ", "BRESP"), ("WRITE", "RRESP"),
                     ("WRITE", "NOT_A_FAULT")):
            with self.subTest(args=args), self.assertRaises(ValueError):
                AXIFault(*args)

    def test_model_transcript_is_no_vendor_proof_even_with_zero_errors(self):
        s, c = simulated()
        c.read(0)
        for row in s.burst_log:
            self.assertEqual(row["status"], "MODEL_OK_NOT_VENDOR_VERIFIED")
            self.assertEqual((row["upstream_size"], row["downstream_size"]), (5, 4))
            self.assertEqual(row["downstream_beats"], 2*row["upstream_beats"])
            self.assertEqual(row["downstream_len"], row["downstream_beats"]-1)
        self.assertEqual(s.diagnostic_after_fault(owner="MODEL")
                         ["physical_axi_or_ddr"], "NOT_PROVEN")

    def test_m02_exact_neural_recurrence_through_axi_block_cache_eviction(self):
        n = 32
        neurons = tuple(Neuron(
            initial_v=(i%5)-2, bias=(i%7)-3,
            threshold=5+i%3, reset_v=-1) for i in range(n))
        synapses = (Synapse(0, 31, 4, 1), Synapse(31, 0, -2, 8),
                    Synapse(15, 16, 7, 2), Synapse(16, 0, 3, 1))
        net = Network(neurons=neurons, synapses=synapses,
                      decay_num=1, decay_den=2)
        events = (InputCurrent(0, 0, 9), InputCurrent(3, 15, 8),
                  InputCurrent(15, 31, 8), InputCurrent(31, 16, 12))
        initial = b"".join(
            c.initial_v.to_bytes(2, "little", signed=True) for c in neurons)
        s, cache = simulated(n=n, page=16, slots=1, maxbytes=32,
                             initial=initial)
        a = replay_with_paging(net, events, ticks=32, cache=cache)
        self.assertEqual(a.trace, evaluate_dense(net, events, ticks=32))
        self.assertGreater(cache.counters.dirty_evictions, 10)
        self.assertGreater(cache.counters.read_transactions, 10)
        self.assertGreater(s.stalls.get("D_R", 0), 0)
        for i, voltage in enumerate(a.trace.voltage_rows[-1]):
            self.assertEqual(int.from_bytes(
                s.snapshot(owner="MODEL")[2*i:2*i+2],
                "little", signed=True), voltage)


if __name__ == "__main__":
    unittest.main()
