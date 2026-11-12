"""D2 offline behavioral PS-domain fault contract; NEVER a physical ATB test.

Icarus is REQUIRED to claim simulation pass; without it Python reports SKIP.
Model has an abstract independent PS clock and synchronized observations;
it is NOT AMD ATB hardware, SmartConnect, clock/CDC implementation or safe bitstream.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TB = ROOT / "rtl/m08/tb_m08_d2_ps_domain_timeout_contract.sv"
INCIDENT = ROOT / "docs/M08_2B_3_FIRST_IDENTITY_RCU_STALL_INCIDENT_AND_FIX_PLAN_2026_11_12.md"
IDENTITY = ROOT / "rtl/m08/m08_axil_readonly_identity.v"
BD = ROOT / "scripts/m08_page_ps_bd_candidate.tcl"
OPERATOR = ROOT / "scripts/m08_kv260_physical_uio_operator.py"
MARKERS = (
    "M08_D2_GUARD_NORMAL_READ_AND_BACKPRESSURE_PASS",
    "M08_D2_GUARD_MISSING_ARREADY_TIMEOUT_AND_POISON_PASS",
    "M08_D2_GUARD_MISSING_RVALID_LATE_RESPONSE_QUARANTINE_PASS",
    "M08_D2_GUARD_PL_CLOCK_ABSENT_UPSTREAM_BOUNDED_PASS",
    "M08_D2_GUARD_PL_STOPPED_AFTER_AR_TIMEOUT_PASS",
    "M08_D2_GUARD_PS_CLOCK_ABSENT_IS_UNPROTECTED_NEGATIVE",
    "M08_D2_GUARD_ABSTRACT_PS_DOMAIN_CONTRACT_ALL_PASS_NO_HARDWARE_PROOF",
)


class M08D2PSFaultContainment(unittest.TestCase):
    def test_original_m08_unprotected_path_remains_quarantined(self):
        original = BD.read_text()
        client = OPERATOR.read_text()
        identity = IDENTITY.read_text()
        tb = TB.read_text()
        self.assertIn("CONFIG.PSU__FPGA_PL0_ENABLE 1", original)
        self.assertIn("ps/maxihpm0_fpd_aclk", original)
        self.assertIn("ctrl_sc/aclk", original)
        self.assertIn("identity/aclk", original)
        self.assertIn("always @(posedge aclk)", identity)
        self.assertIn("reject_quarantined_mmio_mode(args.mode)", client)
        self.assertIn("QUARANTINED", INCIDENT.read_text())
        self.assertIn("NOT SYNTHESIZABLE PS ATB", tb)
        self.assertIn("A downstream accepted AR may remain outstanding", tb)
        self.assertIn("NO CDC is implemented", tb)
        self.assertIn("PS_CLOCK_ABSENT_IS_UNPROTECTED_NEGATIVE", tb)
        # This design intentionally never claims a new physical test.
        for forbidden in ("xmutil", "program_hw_devices", "/dev/mem",
                          "/dev/uio", "ssh ", "fpga_manager", "write_bitstream"):
            self.assertNotIn(forbidden, tb)

    def test_fault_model_issues_one_error_then_poison_no_auto_rearm(self):
        source = TB.read_text()
        self.assertIn("TIMEOUT_CYCLES = 6", source)
        self.assertIn("fault_sticky <= 1;", source)
        self.assertIn("s_rresp <= 2'b10", source)
        self.assertIn("fault_phase <= 2'd1", source)
        self.assertIn("fault_phase <= 2'd2", source)
        self.assertIn("state <= fault_sticky ? POISON : IDLE;", source)
        self.assertIn("assign m_rready = ps_resetn && (state == WAIT_R) && !fault_sticky;", source)
        self.assertIn("ps_clock_running=0", source)
        self.assertIn("pl_clock_running=0", source)
        self.assertNotIn("assign m_arvalid = s_arvalid", source)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus unavailable: do not claim PS-domain fault simulation PASS")
    def test_real_icarus_abstract_ps_timeout_and_negative_failures(self):
        with tempfile.TemporaryDirectory() as d:
            compiled = Path(d) / "m08_d2_guard.vvp"
            run = subprocess.run(
                ["iverilog", "-g2012", "-s",
                 "tb_m08_d2_ps_domain_timeout_contract",
                 "-o", str(compiled), str(TB)],
                capture_output=True, text=True, timeout=60, check=False)
            self.assertEqual(run.returncode, 0, run.stderr + "\n" + run.stdout)
            self.assertEqual(run.stderr.strip(), "", "Review Icarus diagnostics")
            execution = subprocess.run(
                ["vvp", str(compiled)], capture_output=True,
                text=True, timeout=30, check=False)
            self.assertEqual(execution.returncode, 0,
                             execution.stdout + "\n" + execution.stderr)
            self.assertEqual(execution.stderr.strip(), "")
            self.assertNotIn("FATAL", execution.stdout)
            for marker in MARKERS:
                self.assertEqual(execution.stdout.splitlines().count(marker), 1,
                                 "missing/repeated marker: " + marker +
                                 "\n" + execution.stdout)


if __name__ == "__main__":
    unittest.main()
