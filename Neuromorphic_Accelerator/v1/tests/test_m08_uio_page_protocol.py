"""Host-only fault-injected first-party M08 UIO page contract (NO MMIO)."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m08_uio_page_protocol import (
    PageProtocolError, stage_and_compare,
)


class Identity:
    def __init__(self, *, bad=False):
        self.regs = {0: 0x4D303831, 4: 0x00010000, 8: 0, 12: 0,
                     16: 0, 20: 0, 24: 0, 28: 0}
        if bad:
            self.regs[0] = 0
        self.reads = []

    def read32(self, offset):
        self.reads.append(offset)
        return self.regs[offset]


class Page:
    def __init__(self, *, bad_word=None, load_override=None, initial_status=0,
                 fail_write_at=None, fail_read_at=None):
        self.status = initial_status
        self.loaded = 0
        self.selected = 0
        self.resident = 0
        self.words = [0]*64
        self.written = set()
        self.read_set = set()
        self.writes = []
        self.bad_word = bad_word
        self.load_override = load_override
        self.fail_write_at = fail_write_at
        self.fail_read_at = fail_read_at

    def read32(self, offset):
        if offset == self.fail_read_at:
            raise OSError("synthetic MMIO read failure")
        if offset == 0: return 0x4D303850
        if offset == 4: return 0x00020002
        if offset == 8: return 1
        if offset == 12: return self.status
        if offset == 16: return self.selected
        if offset == 24: return self.resident
        if offset == 28:
            if self.load_override is not None and self.status != 0:
                return self.load_override
            return self.loaded
        if 0x100 <= offset < 0x200 and offset % 4 == 0:
            n = (offset-0x100)//4
            self.read_set.add(n)
            return self.words[n] ^ (1 if n == self.bad_word else 0)
        raise AssertionError(f"bad read offset 0x{offset:x}")

    def write32(self, offset, value):
        if offset == self.fail_write_at:
            raise OSError("synthetic MMIO write failure")
        self.writes.append((offset,value))
        if offset == 16:
            self.selected = value
        elif offset == 20:
            if value == 1 and self.status == 0:
                self.status = 1 | 0x80
            elif value == 2 and self.status == (1 | 0x80):
                if self.loaded == 256 and len(self.read_set) == 64:
                    self.status = 2 | 0x10
                    self.resident = self.selected
                else:
                    raise AssertionError("bad premature COMMIT")
            else: raise AssertionError("unexpected/unsafe command")
        elif 0x100 <= offset < 0x200 and offset % 4 == 0:
            n = (offset-0x100)//4
            self.words[n] = value
            self.written.add(n)
            self.loaded = len(self.written)*4
        else: raise AssertionError(f"bad write 0x{offset:x}")


class PageContract(unittest.TestCase):
    def setUp(self):
        self.values = [((i * 0x1020304) ^ 0xAB55F012) & 0xffffffff for i in range(64)]

    def test_full_injected_64_word_roundtrip_comparison_before_commit(self):
        page = Page()
        result = stage_and_compare(Identity(), page, self.values, 7,
                                   allow_transport_writes=True)
        self.assertEqual(result['words_compared'], 64)
        self.assertEqual(result['bytes_compared'], 256)
        self.assertFalse(result['physical_ps_axi_verified'])
        self.assertFalse(result['axi_bresp_or_rresp_observed'])
        self.assertFalse(result['dispatch_attempted'])
        self.assertEqual(page.writes[-1], (0x14,2))
        self.assertEqual(page.status, 0x12)
        self.assertEqual(page.read_set, set(range(64)))
        self.assertEqual(len(page.writes), 67)
        self.assertFalse(result['identity']['identity_build_tag_provisioned'])

    def test_no_write_without_explicit_gate(self):
        page = Page()
        with self.assertRaisesRegex(PageProtocolError, "authorization"):
            stage_and_compare(Identity(), page, self.values, 7)
        self.assertEqual(page.writes, [])

    def test_bad_inputs_fail_before_any_write(self):
        for vals, lid in ((self.values[:-1],7), (self.values+[0],7),
                          (self.values[:10]+[-1]+self.values[11:],7),
                          (self.values[:10]+[True]+self.values[11:],7),
                          (self.values, True), (self.values,2**32)):
            with self.subTest(vals=repr(vals[:2]), lid=lid):
                page=Page()
                with self.assertRaises(PageProtocolError):
                    stage_and_compare(Identity(), page, vals, lid,
                                      allow_transport_writes=True)
                self.assertEqual(page.writes, [])

    def test_bad_identity_status_or_loaded_refuses_writes(self):
        loaded_page = Page()
        loaded_page.loaded = 4
        for ident,page in ((Identity(bad=True),Page()),
                           (Identity(),Page(initial_status=2|0x10)),
                           (Identity(),Page(initial_status=0x8)),
                           (Identity(),loaded_page)):
            with self.subTest(status=page.status):
                with self.assertRaises(PageProtocolError):
                    stage_and_compare(ident,page,self.values,2,
                                      allow_transport_writes=True)
                self.assertEqual(page.writes, [])

    def test_bad_readback_must_withhold_commit(self):
        page = Page(bad_word=29)
        with self.assertRaisesRegex(PageProtocolError, r'word\[29\] mismatch'):
            stage_and_compare(Identity(),page,self.values,5,
                              allow_transport_writes=True)
        self.assertNotIn((0x14,2),page.writes)

    def test_incomplete_loaded_bytes_must_withhold_commit(self):
        page = Page(load_override=252)
        with self.assertRaisesRegex(PageProtocolError, 'loaded byte count'):
            stage_and_compare(Identity(),page,self.values,5,
                              allow_transport_writes=True)
        self.assertNotIn((0x14,2),page.writes)

    def test_injected_io_failures_do_not_commit(self):
        for kwargs in ({'fail_write_at':0x14}, {'fail_write_at':0x144},
                       {'fail_read_at':0x144}):
            page=Page(**kwargs)
            with self.subTest(kwargs=kwargs),self.assertRaises(PageProtocolError):
                stage_and_compare(Identity(),page,self.values,5,
                                  allow_transport_writes=True)
            self.assertNotIn((0x14,2),page.writes)

    def test_pure_source_has_no_linux_transport(self):
        src = (Path(__file__).resolve().parents[1] /
               'src/neuromorphic_accelerator_v1/m08_uio_page_protocol.py').read_text()
        for forbidden in ('import mmap','from mmap','os.open','subprocess.run(',
                          'program_hw_devices', 'xmutil unloadapp'):
            self.assertNotIn(forbidden,src)
        self.assertIn('physical_ps_axi_verified": False',src)


if __name__ == '__main__':
    unittest.main()
