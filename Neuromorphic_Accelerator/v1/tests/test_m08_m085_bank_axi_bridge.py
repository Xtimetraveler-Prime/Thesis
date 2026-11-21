"""Real Icarus AXI4 + original M08 one-resident-bank load/save verification.

PC ONLY: model DDR is 6 x 256B Verilog register array, not PS DDR/DMA.
Original M06 signed16 M02/M03 input pages, not the output-oracle bytes.
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
SOURCES=[
    RTL/"m08_host_staged_page_bank.sv",
    RTL/"m08_m085_ddr_page_admission.v",
    RTL/"m08_m085_axi128_page_engine.v",
    RTL/"m08_m085_axi128_page_candidate.v",
    RTL/"m08_m085_axi_bank_bridge.v",
    RTL/"tb_m08_m085_axi_bank_bridge.sv",
]


class IntegratedBankAXITests(unittest.TestCase):
    def test_unmodified_original_bank_and_empty_window_default(self):
        bridge=SOURCES[4].read_text()
        self.assertIn("m08_host_staged_page_bank bank",bridge)
        self.assertIn("m08_m085_axi128_page_candidate",bridge)
        self.assertIn("WINDOW_BEGIN=64'd0",bridge)
        self.assertIn("WINDOW_END=64'd0",bridge)
        self.assertIn("host_readback_verified(host_commit)",bridge)
        self.assertIn("axi_read_page!==expected_save",bridge)
        self.assertIn("host_save_done(host_save)",bridge)
        self.assertIn("word_index==63",bridge)
        self.assertIn("read_page_valid",SOURCES[3].read_text())
        for forbidden in ("program_hw_devices","open_hw_manager",
                          "0x40000000","/dev/mem","dma_alloc_coherent"):
            self.assertNotIn(forbidden,bridge)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "real Icarus simulator mandatory; never fake RTL pass")
    def test_original_six_neural_pages_load_dirty_save_evict_and_reload(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td)
            out=t/"m08_m085_bank_axi.vvp"
            build=subprocess.run(
                ["iverilog","-g2012","-s","tb_m08_m085_axi_bank_bridge",
                 "-o",str(out),*[str(x) for x in SOURCES]],
                capture_output=True,text=True
            )
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            # Six original FIRST-PARTY state inputs, not a neural-output
            # oracle; memory transport saves synthetic compute mutation.
            for page in range(6):
                with self.subTest(original_page=page):
                    words=fixture.neural_words(page)
                    self.assertEqual(len(words),64)
                    self.assertTrue(fixture.audit_page(words,page,0))
                    p=t/f"page_{page}.hex"
                    fixture.write_hex(p,words)
                    r=subprocess.run(
                        ["vvp",str(out),"+CASE=0",
                         f"+PAGE={page}",f"+ORIGINAL_PAGE_HEX={p}"],
                        capture_output=True,text=True,timeout=20
                    )
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                    self.assertIn(
                        "M08_5_REAL_BANK_AXI_256B_LOAD_DIRTY_SAVE_EVICT_RELOAD_PASS",
                        r.stdout
                    )

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "real Icarus simulator mandatory; never fake RTL pass")
    def test_fifteen_integrated_bank_axi_failure_cases(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"m08_m085_bank_axi.vvp"
            build=subprocess.run(
                ["iverilog","-g2012","-s","tb_m08_m085_axi_bank_bridge",
                 "-o",str(out),*[str(x) for x in SOURCES]],
                capture_output=True,text=True
            )
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            for case in range(1,16):
                with self.subTest(case=case):
                    r=subprocess.run(["vvp",str(out),f"+CASE={case}"],
                                     capture_output=True,text=True,timeout=20)
                    self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                    self.assertIn(
                        f"M08_5_REAL_BANK_AXI_NEGATIVE_PASS case={case}",
                        r.stdout
                    )
                    self.assertNotIn("FATAL",r.stdout+r.stderr)


if __name__=="__main__":
    unittest.main()
