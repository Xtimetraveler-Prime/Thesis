"""G4 real synthesizable-candidate trace+metrics fail-closed release tests.

Functional standalone RTL Icarus, NOT original HLS/AMD, DDR or FPGA.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
FIFO=ROOT/"rtl/m06/m06_g4_output_quarantine.sv"
TB=ROOT/"rtl/m06/tb_m06_g4_output_quarantine.sv"
PASS="M06_G4_TRACE_METRICS_QUARANTINE_RTL_PASS"

class M06G4HardwareOutputQuarantineTests(unittest.TestCase):
    def test_hls_trace_and_metrics_wait_for_clean_external_commit(self):
        source=FIFO.read_text()
        for term in ("module m06_g4_output_quarantine",
                     "MAX_TRACE = 8192","trace_mem",
                     "expected_trace_count","commit_valid","poisoned",
                     "metrics_seen","s_trace_tvalid",
                     "s_metrics_tvalid","m_trace_tvalid",
                     "m_metrics_tvalid","published_done",
                     "protocol_fault","quarantined",
                     "state<=BLOCK","state<=DRAIN"):
            self.assertIn(term,source)
        self.assertIn("physical DDR rollback",source)
        self.assertNotIn("program_hw_devices",source)

    def test_source_directed_cases_cover_no_publication_before_commit(self):
        source=TB.read_text()
        for name in ("PROVISIONAL_OUTPUT_LEAK","CLEAN_RELEASE",
                     "POISON_DISCLOSED_DATA","POISON_REUSE",
                     "TRACE_COUNT_MISMATCH","MISSING_METRICS",
                     "CAPACITY_GUARD","WATCHDOG"):
            self.assertIn("M06_G4_QUARANTINE_FAIL "+name,source)
        self.assertIn(PASS,source)

    def test_genuine_local_rtl_functional_icarus(self):
        if not shutil.which("iverilog") or not shutil.which("vvp"):
            self.skipTest("Icarus and vvp required; CI reruns after installation")
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/"quarantine"
            p=subprocess.run([
                "iverilog","-g2012","-s","tb_m06_g4_output_quarantine",
                "-o",str(output),str(FIFO),str(TB)],
                capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr+p.stdout)
            run=subprocess.run(["vvp",str(output)],
                               capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr+run.stdout)
            self.assertEqual(run.stdout.count(PASS),1)
            self.assertNotIn("M06_G4_QUARANTINE_FAIL",run.stdout)

if __name__=="__main__":
    unittest.main()
