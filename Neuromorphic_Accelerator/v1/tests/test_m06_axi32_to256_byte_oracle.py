"""SYNTHETIC_ONLY M06 32-to-256 AXI byte lane and write-B fence oracle tests.

No AMD Data Width Converter IP and no physical RTL are instantiated.
"""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_axi32_to256_byte_oracle import (
    AXI32CanonicalImage, AXIWidthError, WordWrite,
)


class M06AXI32To256OracleTests(unittest.TestCase):
    def test_32bit_words_cover_all_eight_wide_lanes_without_swapping(self):
        m=AXI32CanonicalImage()
        data=[WordWrite(0xdead0000+i) for i in range(8)]
        plan=m.issue_write(0x120,data,ident=13)
        self.assertEqual([p["lane_index"] for p in plan],list(range(8)))
        self.assertTrue(all(p["wide_base_byte_address"]==0x120 for p in plan))
        self.assertEqual([p["byte_mask_32"] for p in plan],
                         [0xF<<(i*4) for i in range(8)])
        with self.assertRaisesRegex(AXIWidthError,"before write B"):
            m.read(0x120,beats=8)
        m.complete_write(ident=13,bresp=0)
        self.assertEqual(m.read(0x120,beats=8),
                         [0xdead0000+i for i in range(8)])

    def test_partial_strobes_preserve_other_bytes_and_canonical_neighbor(self):
        m=AXI32CanonicalImage(fill=0xA5)
        p=m.issue_write(0x11C,[WordWrite(0x01234567,0b0101)],ident=2)
        self.assertEqual(p[0]["lane_index"],7)
        self.assertEqual(p[0]["byte_mask_32"],0b0101<<28)
        m.complete_write(ident=2)
        self.assertEqual(m.read(0x11C),[0xA523A567])
        self.assertEqual(m.read(0x118),[0xA5A5A5A5])
        self.assertEqual(m.read(0x120),[0xA5A5A5A5])

    def test_last_legal_neuron_address_65535_and_reload(self):
        m=AXI32CanonicalImage()
        base=0xFF00
        for ofs in (0,64,128,192):
            words=[WordWrite(((base+ofs+4*i) ^ 0xA54B6C03)&0xFFFFFFFF)
                   for i in range(16)]
            p=m.issue_write(base+ofs,words,ident=1)
            self.assertEqual(len(p),16)
            m.complete_write(ident=1)
        for ofs in (0,64,128,192):
            read=m.read(base+ofs,beats=16)
            self.assertEqual(read,
              [((base+ofs+4*i)^0xA54B6C03)&0xFFFFFFFF for i in range(16)])
        self.assertEqual(m.written_word_count,64)
        self.assertEqual(m.read(0xFFFC),[0xFFFC ^ 0xA54B6C03])
        self.assertEqual(m.read(0xFEFC),[0xA5A5A5A5])
        self.assertEqual(len(m.digest()),64)

    def test_negative_out_of_range_4kb_crossing_unaligned_and_bad_shape(self):
        m=AXI32CanonicalImage()
        bad=[
            (0x10000,[WordWrite(0)],"out of 64KiB"),
            (0xFFFC,[WordWrite(0),WordWrite(0)],"out of 64KiB"),
            (0xFFE,[WordWrite(0)],"unaligned"),
            (0xFFC,[WordWrite(0),WordWrite(0)],"4KiB"),
            (0x0,[],"AXI beats"),
            (0x0,[WordWrite(0)]*17,"AXI beats"),
            (0,[WordWrite(0,0x10)],"WSTRB"),
        ]
        for address,words,pattern in bad:
            with self.subTest(address=address,pattern=pattern):
                with self.assertRaisesRegex(AXIWidthError,pattern):
                    m.issue_write(address,words)
                self.assertIsNone(m.pending)
        with self.assertRaisesRegex(AXIWidthError,"SIZE=2"):
            m.issue_write(0,[WordWrite(0)],size=5)
        with self.assertRaisesRegex(AXIWidthError,"SIZE=2"):
            m.read(0,size=1)

    def test_error_bresp_poison_and_failed_epoch_cannot_be_accepted(self):
        m=AXI32CanonicalImage()
        m.issue_write(0,[WordWrite(0x87654321)],ident=7)
        with self.assertRaisesRegex(AXIWidthError,"BID mismatch"):
            m.complete_write(ident=8)
        self.assertTrue(m.poisoned)
        with self.assertRaisesRegex(AXIWidthError,"quarantined"):
            m.read(0)
        with self.assertRaisesRegex(AXIWidthError,"incomplete/poisoned"):
            m.digest()
        another=AXI32CanonicalImage()
        another.issue_write(0,[WordWrite(0)],ident=7)
        with self.assertRaisesRegex(AXIWidthError,"BRESP failure"):
            another.complete_write(ident=7,bresp=2)
        self.assertTrue(another.poisoned)

    def test_read_rresp_error_and_missing_write_ack_never_publish(self):
        m=AXI32CanonicalImage()
        m.issue_write(0,[WordWrite(0xabcde001)])
        with self.assertRaisesRegex(AXIWidthError,"incomplete/poisoned"):
            m.digest()
        with self.assertRaisesRegex(AXIWidthError,"prior write"):
            m.issue_write(4,[WordWrite(0xabcde002)])
        m.complete_write()
        with self.assertRaisesRegex(AXIWidthError,"RRESP failure"):
            m.read(0,rresp=2)
        with self.assertRaisesRegex(AXIWidthError,"quarantined"):
            m.read(0)

    def test_two_independent_4kb_bursts_no_implicit_crossing(self):
        m=AXI32CanonicalImage()
        m.issue_write(0xFFC,[WordWrite(0x11111111)],ident=4)
        m.complete_write(ident=4)
        m.issue_write(0x1000,[WordWrite(0x22222222)],ident=4)
        m.complete_write(ident=4)
        self.assertEqual(m.read(0xFFC),[0x11111111])
        self.assertEqual(m.read(0x1000),[0x22222222])


if __name__=="__main__":
    unittest.main()
