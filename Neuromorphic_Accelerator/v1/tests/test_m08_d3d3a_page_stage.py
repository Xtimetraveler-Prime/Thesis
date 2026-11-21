"""M08 D3.D.3A first software page/handoff conformance (NO FPGA/DDR).

Uses the accepted original M02 dense/event + M03 sparse fixture through
the D3.D.2D 630-word independent source oracle. Page images and lease
tests are software-only, not measurement or a memory-safe PS DMA claim.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
import m08_d3d3a_page_stage as page
from neuromorphic_accelerator_v1.m08_host_page_ownership import (
    HostPagedOwnership,HostOwnershipError,HostProtocolPoisoned,
)

class D3D3AOnePageSourceContractTests(unittest.TestCase):
    def test_original_m06_fixed_size_layout_and_exact_word_mapping(self):
        original=[int(x,16) for x in page.fixture.words()]
        self.assertEqual(len(original),630)
        self.assertEqual(page.END,635)
        self.assertEqual(page.BYTES,4096)
        self.assertEqual(page.MAGIC,0x4D335047)
        image=page.pack_page(6,9)
        self.assertEqual(len(image),4096)
        words=struct.unpack("<1024I",image)
        self.assertEqual(words[:8],
                         (page.MAGIC,page.VERSION,6,9,original[0],3,5,17))
        for n in range(32):
            for t in range(4):
                self.assertEqual(words[page.CONFIG+n*4+t],original[3+n*8+t])
                self.assertEqual(words[page.INPUTS+n*4+t],original[3+n*8+4+t])
                self.assertEqual(words[page.VOLTAGES+n*4+t],original[291+n*9+t])
                self.assertEqual(words[page.RECURRENT+n*4+t],original[291+n*9+5+t])
            self.assertEqual(words[page.SPIKES+n],original[291+n*9+4])
        self.assertEqual(words[page.EDGES:page.EDGES+32],tuple(original[259:291]))
        self.assertEqual(words[page.EVENTS:page.END],tuple(original[579:630]))
        self.assertEqual(set(words[page.END:]),{0})
        result=page.audit_page(image,logical_id=6,epoch=9)
        self.assertEqual(result["software_page_sha256"],sha256(image).hexdigest())
        self.assertFalse(result["hardware_page_verified"])

    def test_cross_page_logical_ids_are_never_silently_aliased(self):
        images=[page.pack_page(i) for i in (0,1,2)]
        self.assertEqual(len({sha256(v).hexdigest() for v in images}),3)
        for i,image in enumerate(images):
            page.audit_page(image,logical_id=i,epoch=0)
            for other in (0,1,2):
                if other!=i:
                    with self.assertRaises(page.PageReject):
                        page.audit_page(image,logical_id=other,epoch=0)
        with self.assertRaises(page.PageReject):
            page.audit_page(images[0],logical_id=0,epoch=1)

    def test_single_word_mutation_is_rejected_every_region(self):
        image=page.pack_page(4,0)
        for offset in (0,1,2,3,4,5,6,7,
                       page.CONFIG,page.INPUTS,page.EDGES,
                       page.VOLTAGES,page.SPIKES,page.RECURRENT,
                       page.EVENTS,page.END,page.WORDS-1):
            with self.subTest(offset=offset):
                mutated=bytearray(image)
                mutated[offset*4]^=0x01
                with self.assertRaisesRegex(page.PageReject,
                                            "wrong logical ID, epoch, original neural"):
                    page.audit_page(bytes(mutated),logical_id=4,epoch=0)

    def test_wrong_lengths_types_endianness_epoch_and_identity_reject(self):
        a=page.pack_page(0)
        for value in (-1, 1<<32, True, "4", None):
            with self.subTest(value=value):
                with self.assertRaises(page.PageReject):
                    page.pack_page(value)
        for payload in (a[:-4],a+b"\0"*4,bytearray(a),b""):
            with self.subTest(size=len(payload)):
                with self.assertRaises(page.PageReject):
                    page.audit_page(payload,logical_id=0,epoch=0)
        with self.assertRaises(page.PageReject):
            page.with_epoch(a,logical_id=0,old_epoch=0,new_epoch=2)
        with self.assertRaises(page.PageReject):
            page.with_epoch(a,logical_id=1,old_epoch=0,new_epoch=1)
        updated=page.with_epoch(a,logical_id=0,old_epoch=0,new_epoch=1)
        page.audit_page(updated,logical_id=0,epoch=1)
        with self.assertRaises(page.PageReject):
            page.audit_page(updated,logical_id=0,epoch=0)
        # Only the SOFTWARE epoch header may change in a modeled commit.
        self.assertEqual(a[:12]+a[16:],updated[:12]+updated[16:])

    def test_original_fixture_drift_and_nonmonotonic_ticks_fail_closed(self):
        original=page.fixture.words()
        with patch.object(page.fixture,"words",
                                        return_value=original[:-1]):
            with self.assertRaisesRegex(page.PageReject,"fixture length drift"):
                page.pack_page(0)
        bad=list(original)
        bad[580]="00000003"  # tick 0 -> 3, breaks counts/ordering
        with patch.object(page.fixture,"words",return_value=tuple(bad)):
            with self.assertRaisesRegex(page.PageReject,"event tick ordering drift"):
                page.pack_page(0)

    def test_real_software_ownership_reference_three_logical_two_resident(self):
        result=page.demo()
        self.assertEqual(result["status"],
                         "M08_D3D3A_SOURCE_ONLY_M06_PAGE_GEOMETRY_AND_HOST_LEASE_PASS")
        self.assertEqual(result["modeled_page_loads"],3)
        self.assertEqual(result["modeled_dirty_saves"],3)
        self.assertEqual(result["modeled_epoch"],1)
        self.assertEqual(result["logical_contexts"],3)
        self.assertEqual(result["resident_slots"],2)
        self.assertFalse(result["physical_ddr"])
        self.assertFalse(result["hardware_page_swap_verified"])
        self.assertFalse(result["actual_neural_compute_performed"])

    def test_dirty_eviction_and_dispatch_without_readback_rejected(self):
        owner="m08-page-only"
        p=HostPagedOwnership(
            {n:page.pack_page(n) for n in range(3)}, slots=2,owner=owner)
        p.begin_host(owner=owner)
        p.stage_load(0,0,owner=owner)
        with self.assertRaises(HostOwnershipError):
            p.end_host(owner=owner)
        with self.assertRaises(HostOwnershipError):
            p.dispatch(0,0,owner=owner)
        # Incorrect readback POISONS the entire session.
        with self.assertRaises(HostProtocolPoisoned):
            p.verify_load(0,observed_sha256="0"*64,owner=owner)
        with self.assertRaises(HostProtocolPoisoned):
            p.begin_host(owner=owner)

    def test_software_only_has_no_device_mutating_capabilities(self):
        code=(ROOT/"scripts/m08_d3d3a_page_stage.py").read_text()
        for forbidden in ("open_hw_manager","program_hw_devices","run_hw_axi",
                          "subprocess.run","/dev/mem","/dev/uio","xmutil ",
                          "dma_alloc_coherent","mmap.mmap","socket.socket"):
            self.assertNotIn(forbidden,code)
        self.assertIn('hardware_page_swap_verified":False',code)
        self.assertIn('physical_ddr":False',code)

if __name__=="__main__":
    unittest.main()
