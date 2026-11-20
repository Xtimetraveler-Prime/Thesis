"""D3.D.2C first owner-released JTAG harness: PC-only fail-closed regression.

These tests NEVER invoke Vivado, JTAG, hw_server, PS MMIO, or FPGA programming.
Original M06 32x4 physical test is not yet performed; exact accepted-image
and 2 explicit owner arming variables gate a single fresh hardware attempt.
"""
from __future__ import annotations
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_physical_audit as audit
import m08_d3d2c_m06_native_review as native
import m08_d3d2c_m06_vectors as oracle

class M0632PhysicalBoundaryTests(unittest.TestCase):
    def test_shell_syntax_original_owner_image_and_explicit_board_arming(self):
        shell=ROOT/"scripts/run_m08_d3d2c_m06_physical_once.sh"
        check=subprocess.run(["bash","-n",str(shell)],
                             capture_output=True,text=True,timeout=10)
        self.assertEqual(check.returncode,0,check.stderr)
        s=shell.read_text()
        for token in (
            "m08_d3d2c_m06_native_review.py",
            "244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932",
            'M08_D3D2C_PREFLIGHT_CONFIRMED',
            'm08_d3d2c_m06_MN2pwduB',
            'M08_D3D2C_ALLOW_PROGRAM',
            "sha256sum",
            "mktemp -d",
            "m08_d3d2c_m06_physical_audit.py",
            "M08_D3D2C_HW_STOP_NO_RETRY",
        ):
            self.assertIn(token,s)
        # Exact owner-original native gate executes before any NEW
        # evidence folder or Vivado/JTAG program operation.
        self.assertLess(s.index("native_review.py"),
                        s.index("EXPECTED_SHA="))
        self.assertLess(s.index("EXPECTED_SHA="),
                        s.index("HW=\"$(mktemp"))
        self.assertLess(s.index("EXPECTED_SHA="),
                        s.index("-mode batch"))
        self.assertNotIn("/dev/mem",s)
        self.assertNotIn("/dev/uio",s)

    def test_one_program_tcl_is_pinned_and_no_sneaky_ps_access(self):
        t=(ROOT/"scripts/m08_d3d2c_m06_readback_once.tcl").read_text()
        self.assertIn(
            'set RELEASED_SHA "244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932"',t)
        self.assertIn('M08_D3D2C_PREFLIGHT_CONFIRMED',t)
        self.assertIn('m08_d3d2c_m06_MN2pwduB',t)
        self.assertIn('[file size $bit] != 7797842',t)
        self.assertEqual(
            len(re.findall(r"(?m)^\s*program_hw_devices \$fpga\s*$",t)),1)
        self.assertLess(t.index("set RELEASED_SHA "),t.index("open_hw_manager"))
        for token in (
            'error "D3.D.2C HARD STOP: first owner native image NOT RELEASED"',
            "get_hw_targets -quiet","xck26_0","hw_axi_1",
            "M08_D3D2C_ALLOW_PROGRAM", "55AA22DD",
            "4D33324E","00040000",
            "M08_D3D2C_M06_REAL_NEURON_PARITY|",
            "for {set n 0} {$n < 32}",
            "for {set e 0} {$e < 5}",
            "for {set j 0} {$j < 4}",
            "M08_D3D2C_PHYSICAL_M06_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS",
        ):
            self.assertIn(token,t)
        for forbidden in ("/dev/mem","/dev/uio","xmutil ","ssh ","loadapp"):
            self.assertNotIn(forbidden,t)

    def test_auditor_golden_32_rows_and_six_file_ledger(self):
        self.assertEqual(len(audit.FILES),6)
        self.assertEqual(len(oracle.words()),579)
        expected=audit.expected_lines()
        self.assertEqual(len(expected),32)
        self.assertTrue(expected[0].startswith("neuron=0 voltages="))
        self.assertTrue(expected[-1].startswith("neuron=31 voltages="))
        self.assertTrue(all(" mask=" in s and " synaptic_currents=" in s
                            for s in expected))
        src=(ROOT/"scripts/m08_d3d2c_m06_physical_audit.py").read_text()
        self.assertIn("native 32-neuron first-image DRC/image approval is PENDING",
                      src)
        self.assertIn("original M06",src)
        # Auditor inspects the literal Tcl program statement as evidence;
        # the presence of that *string* is not a hardware operation.
        self.assertIn("program_hw_devices",src)
        self.assertNotIn("program_hw_devices(",src)
        self.assertNotIn("open_hw_manager(",src)
        self.assertNotIn("subprocess.run",src)

    def test_first_owner_image_cannot_be_falsely_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            fake=Path(directory)/"m08_d3d2c_m06_synthetic"
            fake.mkdir()
            with self.assertRaises(audit.Reject):
                audit.verify(fake,fake)
        native_source=(ROOT/"scripts/m08_d3d2c_m06_native_review.py").read_text()
        self.assertIn("M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD",
                      native_source)
        self.assertIn("OWNER_ORIGINAL_BIT_SHA",native_source)
        self.assertIn("OWNER_ORIGINAL_DRC_SHA",native_source)
        # Native approval is necessary but INSUFFICIENT. Both shell and
        # Tcl independently insist on exact accepted SHA and OWNER arming.
        shell=(ROOT/"scripts/run_m08_d3d2c_m06_physical_once.sh").read_text()
        tcl=(ROOT/"scripts/m08_d3d2c_m06_readback_once.tcl").read_text()
        self.assertIn('M08_D3D2C_PREFLIGHT_CONFIRMED',shell)
        self.assertIn('M08_D3D2C_PREFLIGHT_CONFIRMED',tcl)
        self.assertIn('M08_D3D2C_ALLOW_PROGRAM',shell)
        self.assertIn('M08_D3D2C_ALLOW_PROGRAM',tcl)
        self.assertIn('m08_d3d2c_m06_MN2pwduB',shell)
        self.assertIn('m08_d3d2c_m06_MN2pwduB',tcl)
        self.assertNotIn('UNREVIEWED_M08_D3D2C_OWNER_IMAGE',shell+tcl)
        self.assertLess(shell.index('native_review.py'),shell.index('HW="$(mktemp'))
        self.assertLess(tcl.index('set RELEASED_SHA'),tcl.index('open_hw_manager'))

if __name__=="__main__":
    unittest.main()
