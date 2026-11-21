"""M08.4 source-only real-Icarus negative neural page state invariants.

Runs actual clocked RTL and demands persistent FAIL state after malformed
host memory/tick/barrier/edge/handshake. Never claim native K26 or DDR.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as fixture

RTL=ROOT/"rtl/m08"
RTL_FILES=tuple(RTL/s for s in (
    "m08_paged_m06_lif_shell.v",
    "m08_paged_m06_lif_engine.v",
    "m08_axil_page_control.sv",
    "m08_host_staged_page_bank.sv",
    "tb_m08_paged_m06_lif_fail_closed.sv",
))

class PagedM06LIFNegativeTests(unittest.TestCase):
    def test_source_failure_matrix_no_board_or_golden_injection(self):
        txt=(RTL/"tb_m08_paged_m06_lif_fail_closed.sv").read_text()
        for key in ("Missing setup", "skip expected tick0",
                    "invalid positive threshold","compute_ack",
                    "config[3]=0","stage_words(1,2)",
                    "page_poisoned", "bank_phase!==3'd5"):
            self.assertIn(key,txt)
        self.assertNotIn("program_hw_devices",txt)
        self.assertNotIn("write_bitstream",txt)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "genuine Icarus required for negative page RTL test")
    def test_real_rtl_six_quarantine_scenarios(self):
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td)
            pages=(
                ("edge",fixture.edge_words()),
                ("page0",fixture.neural_words(0)),
                ("page1",fixture.neural_words(1)),
            )
            args=[]
            for name,words in pages:
                path=temp/(name+".hex")
                fixture.write_hex(path,words)
                args.append(f"+{name}={path}")
            target=temp/"negative.vvp"
            build=subprocess.run(["iverilog","-g2012",
                                  "-s","tb_m08_paged_m06_lif_fail_closed",
                                  "-o",str(target),*[str(f) for f in RTL_FILES]],
                                 capture_output=True,text=True,timeout=90)
            self.assertEqual(build.returncode,0,build.stdout+"\n"+build.stderr)
            self.assertEqual(build.stderr.strip(),"",
                             "unexpected first-party RTL compile warning")
            run=subprocess.run(["vvp",str(target),*args],
                               capture_output=True,text=True,timeout=90)
            self.assertEqual(run.returncode,0,run.stdout+"\n"+run.stderr)
            self.assertEqual(run.stderr.strip(),"")
            for case in range(6):
                marker=f"M08_PAGED_LIF_FAIL_CLOSED_REAL_RTL_CASE_PASS|{case}"
                self.assertEqual(run.stdout.count(marker),1,run.stdout)
            final="M08_PAGED_LIF_MISSING_SETUP_PAGE_TICK_THRESHOLD_TIMEOUT_BAD_EDGE_REAL_RTL_POISON_PASS"
            self.assertEqual(run.stdout.count(final),1,run.stdout)
            self.assertNotIn("FATAL:",run.stdout)

if __name__=="__main__":
    unittest.main()
