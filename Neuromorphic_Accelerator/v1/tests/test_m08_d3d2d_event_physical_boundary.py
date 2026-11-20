"""D3.D.2D hard-blocked future M32E JTAG test, read-only PC regressions.

No hardware is invoked, no Vivado run, no socket opened or programming done.
The future exact new image DRC/timing gate ALWAYS returns 2 until reviewed.
"""
from __future__ import annotations
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2d_event_physical_audit as audit

class D3D2DRawEventPhysicalBoundary(unittest.TestCase):
    def test_staged_shell_is_bash_valid_and_safely_blocked(self):
        file=ROOT/"scripts/run_m08_d3d2d_event_physical_once.sh"
        result=subprocess.run(["bash","-n",str(file)],
                              capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        s=file.read_text()
        self.assertIn('EXPECTED_SHA="UNREVIEWED_M08_D3D2D_NEW_IMAGE"',s)
        self.assertIn("m08_d3d2d_event_native_review.py",s)
        self.assertIn("m08_d3d2d_event_vectors.py",s)
        self.assertIn("m08_d3d2d_event_readback_once.tcl",s)
        self.assertIn("m08_d3d2d_event_physical_audit.py",s)
        self.assertIn("M08_D3D2D_HW_STOP_NO_RETRY",s)
        self.assertIn("M08_D3D2D_ALLOW_PROGRAM",s)
        self.assertIn("M08_D3D2D_PREFLIGHT_CONFIRMED",s)
        self.assertIn("m08_d3d2d_event_HW_",s)
        self.assertLess(s.index("m08_d3d2d_event_native_review.py"),
                        s.index('HW="$(mktemp -d'))
        self.assertLess(s.index('EXPECTED_SHA="UNREVIEWED_'),
                        s.index('HW="$(mktemp -d'))
        self.assertNotIn("m08_d3d2c_m06_MN2pwduB",s)
        # A comment may document Tcl's one-program rule. The SHELL must
        # never contain an actual hardware programming statement.
        active="\n".join(x for x in s.splitlines()
                         if x.strip() and not x.lstrip().startswith("#"))
        self.assertNotIn("program_hw_devices",active)

    def test_staged_tcl_single_program_statement_new_identity_and_630_words(self):
        src=(ROOT/"scripts/m08_d3d2d_event_readback_once.tcl").read_text()
        self.assertIn('set RELEASED_SHA "UNREVIEWED_M08_D3D2D_NEW_IMAGE"',src)
        self.assertEqual(len(re.findall(r"(?m)^\s*program_hw_devices \$fpga\s*$",src)),1)
        self.assertLess(src.index('set RELEASED_SHA'),src.index("open_hw_manager"))
        for token in (
            "M08_D3D2D_ALLOW_PROGRAM","M08_D3D2D_PREFLIGHT_CONFIRMED",
            "m08_d3d2d_event_lif_jtag_UNRELEASED.bit",
            "m08_d3d2d_event_HW_", "10_m06_raw17_golden.hex",
            "80_m06_raw17_hw_parity.txt", "llength $lines] != 630",
            "M08_D3D2D_M06_TRIPLE_ORACLE_630_WORDS_VERIFIED",
            "4D333245", "00050000", "A0001024", "A0001028",
            "A000102C", "A0001030", "A0001034",
            "for {set e 0} {$e < 17} {incr e}",
            "M08_D3D2D_PHYSICAL_ALL_128_FPGA_EVENT_BUCKET_SUMS_PASS",
            "M08_D3D2D_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS",
            "M08_D3D2D_PROGRAM_COMPLETED",
        ):
            self.assertIn(token,src,token)
        for forbidden in ("D3D2C","/dev/mem","/dev/uio","xmutil ","ssh "):
            self.assertNotIn(forbidden,src)
        if shutil.which("tclsh"):
            program=(
                'set f [open "'+str(ROOT/"scripts/m08_d3d2d_event_readback_once.tcl")+'"];'
                'set s [read $f];close $f;'
                'if {![info complete $s]} {exit 2};puts "COMPLETE"\n')
            chk=subprocess.run(["tclsh"],input=program,capture_output=True,
                               text=True,timeout=15)
            self.assertEqual(chk.returncode,0,chk.stdout+chk.stderr)
            self.assertIn("COMPLETE",chk.stdout)

    def test_future_audit_raw_event_receipt_32_rows_and_first_native_stop(self):
        self.assertEqual(len(audit.FILES),6)
        rows=audit.expected_lines()
        self.assertEqual(len(rows),32)
        self.assertTrue(rows[0].startswith("neuron=0 external_currents="))
        self.assertTrue(rows[-1].startswith("neuron=31 external_currents="))
        self.assertTrue(all(" voltages=" in x and " mask=" in x and
                            " synaptic_currents=" in x for x in rows))
        with TemporaryDirectory() as temp:
            native=Path(temp)/"M08"/"m08_d3d2d_event_FAKE"
            native.mkdir(parents=True)
            hw=native.parent/"m08_d3d2d_event_HW_FAKE"
            hw.mkdir()
            with self.assertRaises(audit.Reject):
                audit.verify(native,hw)
        code=(ROOT/"scripts/m08_d3d2d_event_physical_audit.py").read_text()
        self.assertIn("M08_D3D2D_EXACT_OWNER_NATIVE_RAW17_IMAGE_ACCEPTED_NO_BOARD",code)
        self.assertIn("new raw-event first image SHA/DRC release still PENDING",code)
        self.assertNotIn("open_hw_manager(",code)
        self.assertNotIn("program_hw_devices(",code)

if __name__=="__main__":
    unittest.main()
