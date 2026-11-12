"""First-party M08.2b predeployment PC-only safety and evidence tests."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/run_m08_path_a_physical_preflight_pc.py'
BOARD_SCRIPT = ROOT / 'scripts/m08_path_a_physical_gate_board_readonly.sh'
spec = importlib.util.spec_from_file_location('m08_physical_gate', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class M08PhysicalPreflight(unittest.TestCase):
    def test_source_is_read_only_and_syntax_valid(self):
        subprocess.run(['bash','-n',str(BOARD_SCRIPT)],check=True,timeout=10)
        subprocess.run([sys.executable,'-m','py_compile',str(SCRIPT)],check=True,timeout=10)
        board = BOARD_SCRIPT.read_text()
        runner = SCRIPT.read_text()
        for forbidden in ('xmutil unloadapp','xmutil loadapp','program_hw_devices',
                          'sudo systemctl','systemctl restart','devmem',
                          '/dev/uio','modprobe ', 'fpga_manager/fpga0/firmware',
                          'flashcp', 'sudo apt', 'mmap.'):
            with self.subTest(phrase=forbidden):
                self.assertNotIn(forbidden,board)
        self.assertNotIn('shell=True',runner)
        self.assertIn('StrictHostKeyChecking=ask',runner)
        self.assertIn('candidate_byte_hash_checked_on_pc',runner)

    def test_ledger_hash_and_failure_modes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'a.txt').write_text('genuine\n')
            digest = sha256((root/'a.txt').read_bytes()).hexdigest()
            (root/'99_evidence_sha256.txt').write_text(f'{digest}  a.txt\n')
            self.assertEqual(mod.verify_ledger(root,'99_evidence_sha256.txt'),{'a.txt':digest})
            (root/'a.txt').write_text('tampered\n')
            with self.assertRaisesRegex(mod.PreflightRejected,'mismatch'):
                mod.verify_ledger(root,'99_evidence_sha256.txt')
            (root/'a.txt').write_text('genuine\n')
            (root/'99_evidence_sha256.txt').write_text(f'{digest}  ../escaped\n')
            with self.assertRaises(mod.PreflightRejected):
                mod.verify_ledger(root,'99_evidence_sha256.txt')
            (root/'99_evidence_sha256.txt').write_text(f'{digest}  a.txt\n{digest}  a.txt\n')
            with self.assertRaisesRegex(mod.PreflightRejected,'duplicate'):
                mod.verify_ledger(root,'99_evidence_sha256.txt')
            (root/'99_evidence_sha256.txt').write_text(f'{digest}  a.txt\n')
            alias=root/'alias'
            alias.symlink_to(root/'a.txt')
            (root/'99_evidence_sha256.txt').write_text(f'{digest}  alias\n')
            with self.assertRaises(mod.PreflightRejected):
                mod.verify_ledger(root,'99_evidence_sha256.txt')

    def test_wrong_or_missing_candidate_fails_before_ssh(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            bad=base/'m08_2b_path_a_uio_overlay_REVIEW_ONLY_wrong'
            bad.mkdir()
            with patch.object(mod.subprocess,'run',side_effect=AssertionError('SSH must not run')):
                with self.assertRaises(mod.PreflightRejected):
                    mod.capture(bad,base,BOARD_SCRIPT)
                with self.assertRaisesRegex(mod.PreflightRejected,'board target'):
                    mod.capture(bad,base,BOARD_SCRIPT,target='ubuntu@10.42.0.136')

    def test_capture_success_receipt_and_no_deployment(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            candidate=base/'m08_2b_path_a_uio_overlay_REVIEW_ONLY_fake'
            candidate.mkdir()
            source=base/'board.sh'
            source.write_bytes(BOARD_SCRIPT.read_bytes())
            def fake_run(argv,**opts):
                self.assertEqual(argv[-2:],[mod.TARGET,'bash -s'])
                self.assertEqual(opts['check'],False)
                self.assertIn(b'M08_PHYSICAL_PREFLIGHT_BEGIN_READ_ONLY',opts['stdin'].read())
                opts['stdout'].write(b'M08_PHYSICAL_PREFLIGHT_BEGIN_READ_ONLY\nM08_GATE_PROBE_BEGIN|model\nKV260\nM08_GATE_PROBE_END|model|rc=0\nM08_GATE_PROBE_END|xmutil_listapps|rc=1\nM08_PHYSICAL_PREFLIGHT_END_NO_FPGA_CHANGES\n')
                return subprocess.CompletedProcess(argv,0)
            with patch.object(mod,'validate_candidate',return_value={'fake_fixture':True}),\
                 patch.object(mod.subprocess,'run',side_effect=fake_run):
                out,good=mod.capture(candidate,base,source)
            self.assertTrue(good)
            self.assertTrue(out.is_dir())
            self.assertEqual((out/'03_ssh_exit.txt').read_text(),'exit_status=0\n')
            self.assertEqual(mod.verify_ledger(out,'99_evidence_sha256.txt').keys(),
                             {'00_board_source.sh','00_inputs.json','01_ssh_stdout.log',
                              '02_ssh_stderr.log','03_ssh_exit.txt','04_review.json'})
            review=json.loads((out/'04_review.json').read_text())
            self.assertFalse(review['deployment_authorized'])
            self.assertFalse(review['m08_board_programmed'])
            self.assertEqual(review['status'],
                             'READ_ONLY_BASELINE_CAPTURED_WITH_NONZERO_PROBES_FOR_REVIEW')
            self.assertEqual(review['individual_probe_exit_codes']['xmutil_listapps'], 1)
            self.assertEqual(review['failed_individual_probes'], ['xmutil_listapps'])
            self.assertFalse(review['authenticated_xmutil_inventory_verified'])
            self.assertEqual(review['cooling_safe_during_reconfiguration'],'NOT_VERIFIED')

    def test_failed_ssh_still_preserves_original_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            candidate=base/'m08_2b_path_a_uio_overlay_REVIEW_ONLY_fake'
            candidate.mkdir()
            def fake_run(argv,**opts):
                opts['stderr'].write(b'synthetic SSH transport failure\n')
                return subprocess.CompletedProcess(argv,255)
            with patch.object(mod,'validate_candidate',return_value={'fake_fixture':True}),\
                 patch.object(mod.subprocess,'run',side_effect=fake_run):
                out,good=mod.capture(candidate,base,BOARD_SCRIPT)
            self.assertFalse(good)
            review=json.loads((out/'04_review.json').read_text())
            self.assertEqual(review['status'],'READ_ONLY_CAPTURE_INCOMPLETE_STOP')
            self.assertEqual(review['ssh_exit_status'],255)
            self.assertEqual(len(mod.verify_ledger(out,'99_evidence_sha256.txt')),6)


if __name__ == '__main__':
    unittest.main()
