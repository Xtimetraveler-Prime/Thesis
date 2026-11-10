"""Source-only G4 safety interlock: no hardware, no vendor substitution."""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
GATE=ROOT/"rtl/m06/m06_g4_epoch_commit_gate.sv"
TB=ROOT/"rtl/m06/tb_m06_g4_epoch_commit_gate.sv"
MARKER="M06_G4_EPOCH_COMMIT_FAULT_QUARANTINE_RTL_PASS"

class M06G4EpochAcceptanceGateTests(unittest.TestCase):
    def test_fault_and_completion_signal_contract_source_only(self):
        rtl=GATE.read_text()
        self.assertIn("module m06_g4_epoch_commit_gate",rtl)
        self.assertIn("read_guard_fault",rtl)
        self.assertIn("write_guard_fault",rtl)
        self.assertIn("write_aw_fire",rtl)
        self.assertIn("write_b_fire",rtl)
        self.assertIn("read_ar_fire",rtl)
        self.assertIn("ap_return!=32'd0",rtl)
        self.assertIn("next_outstanding!=16'd0",rtl)
        self.assertIn("MAX_EPOCH_CYCLES",rtl)
        self.assertIn("timed_out",rtl)
        self.assertIn("settling_commit",rtl)
        self.assertIn("commit_valid<=1'b0",rtl)
        self.assertIn("poisoned<=1'b1",rtl)
        self.assertNotIn("program_hw_devices",rtl)
        self.assertIn("Does NOT implement hardware-atomic physical DDR",rtl)

    def test_every_negative_case_in_independent_rtl_bench(self):
        bench=TB.read_text()
        for scenario in ("CLEAN_COMMIT","BAD_RETURN","POISON_REUSE",
                         "READ_FAULT_QUARANTINE","UNACKED_WRITE",
                         "READ_BEFORE_B","SAME_CYCLE_WRITE_FAULT_DONE",
                         "B_UNDERFLOW","SPURIOUS_DONE","LOST_ACK_WATCHDOG",
                         "EARLY_COMMIT_ON_AP_DONE","EARLY_FAULT_COMMIT",
                         "LATE_REGISTERED_GUARD_FAULT","WATCHDOG"):
            self.assertIn("M06_G4_GATE_FAIL "+scenario,bench)
        self.assertIn(MARKER,bench)
        self.assertIn("NO_DDR_NO_BOARD NO_VENDOR_XSIM",bench)

    def test_real_candidate_iverilog_functional_gate(self):
        if not shutil.which("iverilog") or not shutil.which("vvp"):
            self.skipTest("requires real Icarus; M06 CI reruns after apt")
        with tempfile.TemporaryDirectory() as temp:
            exe=Path(temp)/"g4_commit_gate"
            build=subprocess.run([
                "iverilog","-g2012","-s","tb_m06_g4_epoch_commit_gate",
                "-o",str(exe),str(GATE),str(TB)
            ],capture_output=True,text=True,timeout=20)
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            actual=subprocess.run(
                ["vvp",str(exe)],capture_output=True,text=True,timeout=20)
            self.assertEqual(actual.returncode,0,actual.stdout+actual.stderr)
            self.assertEqual(actual.stdout.count(MARKER),1)
            self.assertNotIn("M06_G4_GATE_FAIL",actual.stdout)
            self.assertIn("NO_VENDOR_XSIM",actual.stdout)

if __name__=="__main__":
    unittest.main()
