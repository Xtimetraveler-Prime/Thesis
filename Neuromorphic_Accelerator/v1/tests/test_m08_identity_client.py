"""M08 read-only MMIO client never assumes a physical address/backend."""
from __future__ import annotations
from dataclasses import replace
import sys
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m08_identity_client import (
    CAPABILITY_NO_DMA, MAGIC, VERSION, IdentityProtocolError,
    inspect_identity,
)


class FakeReadOnly:
    def __init__(self, words=None):
        self.words={
            0x00:MAGIC,0x04:VERSION,0x08:CAPABILITY_NO_DMA,0x0c:0,
            0x10:0x89abcdef,0x14:0x12345678,0x18:0x0badf00d,
            0x1c:0xfedcba98,
        }
        self.words.update(words or {})
        self.calls=[]
        self.spurious_change=None

    def read32(self,offset):
        self.calls.append(offset)
        if self.spurious_change is not None and len(self.calls)>8:
            return self.spurious_change
        return self.words[offset]


class M08IdentityClientTests(unittest.TestCase):
    def test_requires_two_stable_passes_and_nonzero_build_tag(self):
        adapter=FakeReadOnly()
        r=inspect_identity(adapter)
        self.assertEqual(len(adapter.calls),16)
        self.assertEqual(adapter.calls[:8],adapter.calls[8:])
        self.assertEqual(r.magic,MAGIC)
        self.assertEqual(r.version,VERSION)
        self.assertEqual(r.capabilities,0)
        self.assertEqual(r.build_tag_hex,
                         "89abcdef123456780badf00dfedcba98")
        self.assertTrue(r.locally_consistent)
        self.assertFalse(r.actual_bitstream_sha_verified)
        self.assertFalse(r.physically_attested)
        self.assertFalse(r.dma_buffer_owner_verified)

    def test_reject_unknown_magic_version_caps_reserved_and_unprovisioned_tag(self):
        cases=(
            {0x00:0},{0x04:0},{0x08:1},{0x0c:1},
            {0x10:0,0x14:0,0x18:0,0x1c:0}
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(IdentityProtocolError):
                inspect_identity(FakeReadOnly(case))
        empty=FakeReadOnly({0x10:0,0x14:0,0x18:0,0x1c:0})
        r=inspect_identity(empty,require_nonzero_build_tag=False)
        self.assertEqual(r.build_tag_hex,"0"*32)
        self.assertFalse(r.actual_bitstream_sha_verified)
        with self.assertRaises(ValueError):
            inspect_identity(FakeReadOnly(),require_nonzero_build_tag=1)

    def test_reject_unstable_response_or_bad_integer_range(self):
        adapter=FakeReadOnly()
        adapter.spurious_change=7
        with self.assertRaisesRegex(IdentityProtocolError,"unstable"):
            inspect_identity(adapter)
        for bad in (-1,2**32,True,1.0,None):
            with self.subTest(bad=bad),self.assertRaises(IdentityProtocolError):
                inspect_identity(FakeReadOnly({0x10:bad}))

    def test_read_failure_has_no_write_operation(self):
        class Broken:
            def read32(self,off):
                raise OSError("unmapped")
            def write32(self,off,value):
                raise AssertionError("not allowed")
        with self.assertRaisesRegex(IdentityProtocolError,"MMIO adapter"):
            inspect_identity(Broken())

    def test_readonly_client_has_no_devmem_backend(self):
        body=(ROOT/"src/neuromorphic_accelerator_v1/m08_identity_client.py").read_text()
        self.assertNotIn("os.open(",body)
        self.assertNotIn("mmap.mmap(",body)
        self.assertNotIn("write32(",body)
        self.assertIn("def read32(",body)


if __name__=="__main__":
    unittest.main()
