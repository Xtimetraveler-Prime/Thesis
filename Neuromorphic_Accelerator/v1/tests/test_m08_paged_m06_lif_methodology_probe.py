"""M08.4 source-only checks for first-owner routed DCP reset warning inventory.

Only parsing and source safety. NEVER invoke genuine Vivado or physical JTAG.
"""
from __future__ import annotations
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
TCL=ROOT/"scripts/m08_paged_m06_lif_methodology_probe.tcl"
SH=ROOT/"scripts/run_m08_paged_m06_lif_methodology_pc.sh"
REVIEW=ROOT/"scripts/m08_paged_m06_lif_physical_readiness.py"
PHYS=ROOT/"scripts/run_m08_paged_m06_lif_physical_once.sh"

class M084MethodologyCaptureSafety(unittest.TestCase):
    def test_read_only_original_dcp_with_fresh_out_and_both_reports(self):
        code=TCL.read_text()
        self.assertIn("open_checkpoint $dcp",code)
        self.assertIn("report_methodology -file $method",code)
        self.assertIn("report_cdc -file $cdc",code)
        self.assertIn("close_design",code)
        self.assertIn("file exists $method",code)
        self.assertIn("m08_paged_m06_lif_methodology_",code)
        for forbidden in ("program_hw_devices ","open_hw_manager","connect_hw_server",
                          "run_hw_axi ","write_checkpoint ","write_bitstream "):
            self.assertNotIn(forbidden,code)

    def test_shell_is_offline_exact_original_evidence_and_no_auto_jtag(self):
        text=SH.read_text()
        self.assertIn("set -euo pipefail",text)
        self.assertIn("m08_paged_m06_lif_QFKpXlPW",text)
        self.assertIn("m08_paged_m06_lif_physical_readiness.py",text)
        self.assertIn("m08_paged_m06_lif_methodology_probe.tcl",text)
        self.assertIn("-name '*_routed.dcp'",text)
        self.assertLess(text.index('-journal "$OUT/02_vivado_methodology.jou"'),
                        text.index('-tclargs "${dcp[0]}" "$OUT"'),
                        "Vivado -tclargs last; no -log/-journal forwarded into Tcl argv")
        self.assertIn('"${#dcp[@]}" -ne 1',text)
        self.assertIn("mktemp -d",text)
        self.assertIn("99_evidence_sha256.txt",text)
        self.assertIn("M08_4_NEW_PAGED_IMAGE_JTAG_HARDWARE_RELEASE=BLOCKED_PENDING_REVIEW",text)
        self.assertLess(text.index("m08_paged_m06_lif_physical_readiness.py"),
                        text.index("mktemp -d"))
        for forbidden in ("program_hw_devices ","open_hw_manager","connect_hw_server",
                          "run_hw_axi ","write_bitstream ","sudo ","/dev/mem"):
            self.assertNotIn(forbidden,text)
        p=subprocess.run(["bash","-n",str(SH)],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_one_shot_physical_release_requires_new_exact_owner_gate(self):
        self.assertTrue((ROOT/"scripts/m08_paged_m06_lif_exact_native_accept.py").is_file())
        shell=PHYS.read_text()
        self.assertIn("if [[ ! -f \"$EXACT_GATE\"",shell)
        self.assertIn("m08_paged_m06_lif_exact_native_accept.py",shell)
        self.assertIn("M08_4_PROGRAM_ONCE",shell)
        self.assertIn("M08_4_PREFLIGHT_CONFIRMED",shell)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl parser not installed")
    def test_tcl_grammar_without_opening_vendor_or_board(self):
        program=(
            "set file [open {"+str(TCL)+"} r]\n"
            "set txt [read $file]\nclose $file\n"
            "if {![info complete $txt]} {exit 7}\n"
            "puts M08_4_METHOD_TCL_SOURCE_ONLY_GRAMMAR_PASS\n"
        )
        p=subprocess.run(["tclsh"],input=program,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn("M08_4_METHOD_TCL_SOURCE_ONLY_GRAMMAR_PASS",p.stdout)

if __name__=="__main__":
    unittest.main()
