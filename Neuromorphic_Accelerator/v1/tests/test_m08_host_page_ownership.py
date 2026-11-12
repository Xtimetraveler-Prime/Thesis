"""M08 host-paged PS-side ownership adapted from accepted Loihi P08.

All tests are deterministic Python-only. They cannot establish a real PL
host-bank command, kernel DMA allocation, PS DDR or physical memory safety.
"""
from __future__ import annotations
from hashlib import sha256
import unittest

from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from neuromorphic_accelerator_v1.m08_host_page_ownership import (
    HostPagedOwnership,HostOwnershipError,HostProtocolPoisoned,
)


class M08LoihiHostPagingTests(unittest.TestCase):
    def make(self,slots:int=2)->HostPagedOwnership:
        return HostPagedOwnership(
            {0:b"0000",1:b"1111",2:b"2222"},
            slots=slots,owner="software-host-only")

    @staticmethod
    def load(p:HostPagedOwnership,logical:int,slot:int)->None:
        p.begin_host(owner="software-host-only")
        image=p.stage_load(logical,slot,owner="software-host-only")
        p.verify_load(slot,observed_sha256=sha256(image).hexdigest(),
                      owner="software-host-only")
        p.end_host(owner="software-host-only")

    def test_two_resident_three_logical_page_replacement_preserves_state(self):
        p=self.make()
        self.load(p,0,0)
        self.load(p,1,1)
        self.assertEqual(p.dispatch(0,0,owner="software-host-only"),b"0000")
        p.finish_compute(0,observed_image=b"aaaa",packets_drained=True,
                         owner="software-host-only")
        # Backing is *not yet* committed by a completed compute dispatch.
        self.assertEqual(p.backing_snapshot(0,owner="software-host-only"),b"0000")
        p.begin_host(owner="software-host-only")
        with self.assertRaisesRegex(HostOwnershipError,"commit dirty"):
            p.stage_load(2,0,owner="software-host-only")
        p.save_dirty(0,observed_image=b"aaaa",owner="software-host-only")
        image=p.stage_load(2,0,owner="software-host-only")
        p.verify_load(0,observed_sha256=sha256(image).hexdigest(),
                      owner="software-host-only")
        p.end_host(owner="software-host-only")
        self.assertEqual(p.dispatch(1,1,owner="software-host-only"),b"1111")
        p.finish_compute(1,observed_image=b"bbbb",packets_drained=True,
                         owner="software-host-only")
        p.begin_host(owner="software-host-only")
        p.save_dirty(1,observed_image=b"bbbb",owner="software-host-only")
        p.end_host(owner="software-host-only")
        self.assertEqual(p.dispatch(2,0,owner="software-host-only"),b"2222")
        p.finish_compute(0,observed_image=b"cccc",packets_drained=True,
                         owner="software-host-only")
        p.begin_host(owner="software-host-only")
        p.save_dirty(0,observed_image=b"cccc",owner="software-host-only")
        p.end_host(owner="software-host-only")
        p.advance_epoch(owner="software-host-only")
        self.assertEqual([p.backing_snapshot(i,owner="software-host-only")
                          for i in range(3)],[b"aaaa",b"bbbb",b"cccc"])
        receipt=p.receipt(owner="software-host-only")
        self.assertEqual(receipt["epoch"],1)
        self.assertEqual(receipt["page_loads"],3)
        self.assertEqual(receipt["page_saves"],3)
        self.assertEqual(receipt["slot_to_logical"],[2,1])
        self.assertFalse(receipt["physical_dma_ready"])
        self.assertFalse(receipt["kernel_dma_buffer_owned"])

    def test_host_compute_exclusion_sticky_load_and_logical_identity(self):
        p=self.make()
        p.begin_host(owner="software-host-only")
        image=p.stage_load(0,0,owner="software-host-only")
        with self.assertRaises(HostOwnershipError):
            p.end_host(owner="software-host-only")
        with self.assertRaises(HostOwnershipError):
            p.dispatch(0,0,owner="software-host-only")
        p.verify_load(0,observed_sha256=sha256(image).hexdigest(),
                      owner="software-host-only")
        p.end_host(owner="software-host-only")
        with self.assertRaises(HostOwnershipError):
            p.dispatch(1,0,owner="software-host-only")
        p.dispatch(0,0,owner="software-host-only")
        with self.assertRaises(HostOwnershipError):
            p.begin_host(owner="software-host-only")
        with self.assertRaises(HostOwnershipError):
            p.dispatch(0,0,owner="software-host-only")
        p.finish_compute(0,observed_image=b"0000",packets_drained=True,
                         owner="software-host-only")
        p.begin_host(owner="software-host-only")
        with self.assertRaisesRegex(HostOwnershipError,"commit dirty"):
            p.stage_load(1,0,owner="software-host-only")

    def test_load_readback_mismatch_poison_is_fail_closed(self):
        p=self.make()
        p.begin_host(owner="software-host-only")
        p.stage_load(0,0,owner="software-host-only")
        with self.assertRaises(HostProtocolPoisoned):
            p.verify_load(0,observed_sha256="0"*64,
                          owner="software-host-only")
        with self.assertRaises(HostProtocolPoisoned):
            p.end_host(owner="software-host-only")
        with self.assertRaises(HostProtocolPoisoned):
            p.advance_epoch(owner="software-host-only")

    def test_dirty_readback_mismatch_cannot_change_canonical_backing(self):
        p=self.make()
        self.load(p,0,0)
        p.dispatch(0,0,owner="software-host-only")
        p.finish_compute(0,observed_image=b"xxxx",packets_drained=True,
                         owner="software-host-only")
        p.begin_host(owner="software-host-only")
        with self.assertRaises(HostProtocolPoisoned):
            p.save_dirty(0,observed_image=b"yyyy",
                         owner="software-host-only")
        # The state machine is poisoned, so direct checking would itself
        # be embargoed rather than expose possibly stale data.
        with self.assertRaises(HostProtocolPoisoned):
            p.backing_snapshot(0,owner="software-host-only")

    def test_packets_must_be_drained_before_commit_and_epoch(self):
        p=self.make()
        self.load(p,0,0)
        p.dispatch(0,0,owner="software-host-only")
        with self.assertRaises(HostProtocolPoisoned):
            p.finish_compute(0,observed_image=b"aaaa",packets_drained=False,
                             owner="software-host-only")
        with self.assertRaises(HostProtocolPoisoned):
            p.begin_host(owner="software-host-only")
        q=self.make()
        self.load(q,0,0)
        q.dispatch(0,0,owner="software-host-only")
        q.finish_compute(0,observed_image=b"aaaa",packets_drained=True,
                         owner="software-host-only")
        with self.assertRaisesRegex(HostOwnershipError,"all logical"):
            q.advance_epoch(owner="software-host-only")

    def test_software_lease_is_not_linux_dma_ownership(self):
        p=self.make()
        with self.assertRaises(PermissionError):
            p.begin_host(owner="another-owner")
        with self.assertRaises(ValueError):
            HostPagedOwnership({0:b"1",1:b"22"},slots=1,owner="x")
        with self.assertRaises(ValueError):
            HostPagedOwnership({0:b"1"},slots=1,owner="x")
        self.load(p,0,0)
        p.begin_host(owner="software-host-only")
        with self.assertRaises(HostOwnershipError):
            p.stage_load(0,1,owner="software-host-only")
        p.end_host(owner="software-host-only")
        receipt=p.receipt(owner="software-host-only")
        self.assertEqual(
            receipt["scope"],
            "M08_SOFTWARE_HOST_PAGED_OWNERSHIP_REFERENCE_NOT_KERNEL_DMA")
        self.assertFalse(receipt["hardware_dispatch_measured"])
        p.mark_uncertain(owner="software-host-only")
        with self.assertRaises(HostProtocolPoisoned):
            p.receipt(owner="software-host-only")


if __name__=="__main__":
    unittest.main()
