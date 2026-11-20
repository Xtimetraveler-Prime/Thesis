"""M08 D3.D.2E STAGED physical source boundary, never opens Vivado/JTAG.

Full original DRC instance/pin report still missing: original native checker
unconditionally exits 2, so user launch must STOP before creating HW evidence.
These are static/negative mock checks, NOT actual board evidence.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2e_queue_physical_audit as audit
import m08_d3d2e_queue_native_review as native

BIT_SHA="2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc"
NATIVE="m08_d3d2e_queue_GFz0SbiC"

class QueuePhysicalStagedBoundary(unittest.TestCase):
    def test_shell_fails_closed_before_opening_jtag_and_uses_exact_owner_bit(self):
        p=ROOT/"scripts/run_m08_d3d2e_queue_physical_once.sh"
        proc=subprocess.run(["bash","-n",str(p)],capture_output=True,text=True,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr)
        s=p.read_text()
        for req in (BIT_SHA,NATIVE,"EXPECTED_SIZE=7797844",
                    "m08_d3d2e_queue_native_review.py",
                    "m08_d3d2e_queue_readback_once.tcl",
                    "m08_d3d2e_queue_physical_audit.py",
                    "m08_d3d2d_event_vectors.py",
                    "M08_D3D2E_ALLOW_PROGRAM",
                    "M08_D3D2E_PREFLIGHT_CONFIRMED",
                    "M08_D3D2E_HW_STOP_NO_RETRY",
                    "m08_d3d2e_queue_HW_"):
            self.assertIn(req,s,req)
        self.assertLess(s.index("m08_d3d2e_queue_native_review.py"),
                        s.index('HW="$(mktemp -d'))
        active="\\n".join(x for x in s.splitlines()
                         if x.strip() and not x.lstrip().startswith("#"))
        self.assertNotIn("program_hw_devices",active)
        self.assertNotIn("run_hw_axi",active)

    def test_tcl_one_program_only_exact_candidate_then_fifo_service_and_m06(self):
        s=(ROOT/"scripts/m08_d3d2e_queue_readback_once.tcl").read_text()
        self.assertEqual(len(re.findall(r"(?m)^\s*program_hw_devices \$fpga\s*$",s)),1)
        for req in (BIT_SHA,NATIVE,"7797844","4D333251","00060000",
                    "llength $lines] != 630",
                    "M08_D3D2E_ALLOW_PROGRAM","M08_D3D2E_PREFLIGHT_CONFIRMED",
                    "M08_D3D2E_ALL_128_LIVE_BUCKETS_ZERO_BEFORE_SERVICE",
                    "for {set t 0} {$t < 4} {incr t}",
                    "A0001040","A0001044","A0001048","A000104C","A0001050",
                    "A0001054","A0001058",
                    "M08_D3D2E_QUEUE_17_ACCEPTED_17_SERVICED_ALL_FOUR_TICKS_PASS",
                    "M08_D3D2E_PHYSICAL_ALL_128_FPGA_EVENT_BUCKET_SUMS_PASS",
                    "M08_D3D2E_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS",
                    "ONE_ORIGINAL_M06_32X4_QUEUED_EVENT_SERVICE_AND_RECURRENT_HARDWARE_PARITY",
                    "per_tick_serviced_$t"):
            self.assertIn(req,s,req)
        self.assertLess(s.index("    open_hw_manager"),s.index("    program_hw_devices $fpga"))
        self.assertLess(s.index("M08_D3D2E_QUEUE_17_ACCEPTED_17_SERVICED_ALL_FOUR_TICKS_PASS"),
                        s.index("    d2e_write $axi A0001014"))
        for forbidden in ("/dev/mem","/dev/uio","xmutil ","ssh ","D3D2C"):
            self.assertNotIn(forbidden,s)
        if shutil.which("tclsh"):
            with tempfile.TemporaryDirectory() as tmp:
                src=Path(tmp)/"syntax.tcl"
                src.write_text(
                    "set f [open {"+str(ROOT/"scripts/m08_d3d2e_queue_readback_once.tcl")+"}];"
                    "set s [read $f];close $f;"
                    "if {![info complete $s]} {exit 2};puts COMPLETE\n")
                proc=subprocess.run(["tclsh",str(src)],capture_output=True,text=True,timeout=15)
                self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
                self.assertIn("COMPLETE",proc.stdout)

    def test_auditor_cannot_accept_unreviewed_exact_source_candidate(self):
        self.assertEqual(len(audit.FILES),6)
        self.assertEqual(len(audit.expected_lines()),32)
        self.assertTrue(all(" external_currents=" in line and
                            " voltages=" in line and " mask=" in line and
                            " synaptic_currents=" in line
                            for line in audit.expected_lines()))
        with patch.object(native,"inspect",return_value={
            "sha_ledger_rows_verified":12,
            "new_original_candidate_sha256":BIT_SHA,
            "image_specific_gate":"BLOCKED"
        }):
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaisesRegex(audit.Reject,"NOT accepted"):
                    audit.verify(Path(d)/NATIVE,Path(d)/"m08_d3d2e_queue_HW_FAKE")
        s=(ROOT/"scripts/m08_d3d2e_queue_physical_audit.py").read_text()
        self.assertIn('first.get("image_specific_gate") == "ACCEPTED"',s)
        self.assertIn("per_tick_serviced_",s)
        self.assertNotIn("open_hw_manager(",s)
        self.assertNotIn("program_hw_devices(",s)

if __name__=="__main__":
    unittest.main()
