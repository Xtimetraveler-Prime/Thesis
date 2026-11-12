"""Metadata-only/synthetic mmap tests; no KV260, no device node opens."""
import importlib.util
from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SCRIPT = ROOT / 'scripts/m08_path_a_uio_identity_guard.py'
spec = importlib.util.spec_from_file_location('m08_guard', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GuardTests(unittest.TestCase):
    def test_metadata_preflight_absent_has_no_device_access(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = mod.preflight(root, 'absent')
            self.assertEqual(result['uio_metadata']['m08_bindings'], {})
            self.assertFalse(result['linux_mmap_attempted'])
            self.assertFalse(result['device_node_opened'])
            p = subprocess.run([sys.executable, str(SCRIPT), '--sysfs-root',d],
                               text=True, capture_output=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertFalse(json.loads(p.stdout)['physical_ps_axi_verified'])

    def test_denied_without_owner_consent_or_live_sysfs(self):
        with tempfile.TemporaryDirectory() as d:
            record=Path(d)/'review.json'
            record.write_text(json.dumps(mod.APPROVAL_FIELDS))
            digest=sha256(record.read_bytes()).hexdigest()
            opts=dict(sysfs_root=mod.SYSFS_ROOT,approval_file=record,
                      approval_sha256=digest,cli_consent=True,
                      environment={mod.READ_FLAG:'YES'},
                      machine='aarch64',board_model='ZynqMP KV260 revB')
            accepted=mod.approve_identity_mode(**opts)
            self.assertTrue(accepted['review_document_is_operator_assertion_not_physical_attestation'])
            failures=[{'sysfs_root':Path(d)}, {'cli_consent':False},
                      {'environment':{}}, {'machine':'x86_64'},
                      {'board_model':'not an FPGA'}, {'approval_sha256':'0'*64},
                      {'approval_file':None}]
            for change in failures:
                with self.subTest(change=change),self.assertRaises(mod.GuardRejected):
                    mod.approve_identity_mode(**{**opts,**change})
            record.write_text(json.dumps({**mod.APPROVAL_FIELDS,
                                          'linux_kernel_uio_ownership_verified':'NO'}))
            with self.assertRaises(mod.GuardRejected):
                mod.approve_identity_mode(**{**opts,
                                             'approval_sha256':sha256(record.read_bytes()).hexdigest()})

    def test_symlinked_approval_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            real=Path(d)/'review.json'
            real.write_text(json.dumps(mod.APPROVAL_FIELDS))
            alias=Path(d)/'alias.json'
            alias.symlink_to(real)
            with self.assertRaises(mod.GuardRejected):
                mod.approve_identity_mode(sysfs_root=mod.SYSFS_ROOT,
                    approval_file=alias,approval_sha256=sha256(real.read_bytes()).hexdigest(),
                    cli_consent=True,environment={mod.READ_FLAG:'YES'},machine='aarch64',
                    board_model='ZynqMP KV260 revB')

    def test_fake_backed_mmap_reads_only_never_writes(self):
        with tempfile.TemporaryDirectory() as d:
            ident=Path(d)/'id.bin'
            page=Path(d)/'page.bin'
            def payload(words):
                raw=bytearray(4096)
                for offset,value in words.items():
                    raw[offset:offset+4]=value.to_bytes(4,'little')
                return raw
            ident.write_bytes(payload({0:0x4D303831,4:0x10000}))
            page.write_bytes(payload({0:0x4D303850,4:0x20002,8:1}))
            real_open=os.open
            openings=[]
            def fake_open(path,flags):
                self.assertIn(path,('/dev/uio7','/dev/uio8'))
                self.assertEqual(flags & os.O_ACCMODE,os.O_RDONLY)
                openings.append(path)
                return real_open(str(ident if path.endswith('uio7') else page),flags)
            with patch.object(mod.os,'open',side_effect=fake_open):
                read=mod.identity_read_live({'m08-identity':'uio7','m08-page':'uio8'})
            self.assertEqual(openings,['/dev/uio7','/dev/uio8'])
            self.assertTrue(read['attempted_readonly_linux_uio_mmap'])
            self.assertTrue(read['build_tag_unprovisioned'])
            self.assertFalse(read['physical_readback_independently_accepted'])
            self.assertFalse(read['page_write_attempted'])
            self.assertEqual(ident.stat().st_size,4096)
            self.assertEqual(page.stat().st_size,4096)

    def test_fake_mmap_bad_identity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d)/'bad.bin'
            data.write_bytes(bytes(4096))
            real_open=os.open
            with patch.object(mod.os,'open',side_effect=lambda path,flags:real_open(str(data),flags)):
                with self.assertRaisesRegex(mod.GuardRejected,'identity magic'):
                    mod.identity_read_live({'m08-identity':'uio3','m08-page':'uio4'})

    def test_source_no_mutations_or_uiomap_write(self):
        source=SCRIPT.read_text()
        for bad in ('os.O_RDWR','mmap.PROT_WRITE','xmutil unloadapp','xmutil loadapp',
                    'program_hw_devices','/dev/mem','flashcp','subprocess.run('):
            self.assertNotIn(bad,source)
        self.assertIn('approval_sha256',source)
        self.assertIn('READ_IDENTITY_ONLY',source)
        self.assertNotIn('write32(',source)


if __name__ == '__main__':
    unittest.main()
