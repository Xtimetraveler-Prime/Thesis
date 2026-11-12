"""D0/D1/D2 source-only regression for the quarantined M08 PS-to-PL stall.

These checks observe first-party *sources* and execute an Icarus DUT test when
installed. They do not simulate PS HPM0, AMD SmartConnect, physical clock
enable, Linux MMIO, or the original vendor-routed checkpoint. A missing
Icarus executable results in an explicit SKIP (not a verified RTL PASS).
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BD = ROOT / "scripts/m08_page_ps_bd_candidate.tcl"
FAN = ROOT / "scripts/m08_path_a_fan_bd_candidate.tcl"
IDENTITY = ROOT / "rtl/m08/m08_axil_readonly_identity.v"
PAGE = ROOT / "rtl/m08/m08_axil_page_control.sv"
SHELL = ROOT / "rtl/m08/m08_ps_page_safe_shell.v"
TB = ROOT / "rtl/m08/tb_m08_axil_identity_stall_forensics.sv"
INCIDENT = ROOT / "docs/M08_2B_3_FIRST_IDENTITY_RCU_STALL_INCIDENT_AND_FIX_PLAN_2026_11_12.md"
ROUTE = ROOT / "docs/M08_2B_POST_ROUTE_ACCEPTANCE_AND_WARNINGS_2026_11_11.md"
OVERLAY = ROOT / "scripts/m08_path_a_stage_uio_overlay.py"
OPERATOR = ROOT / "scripts/m08_kv260_physical_uio_operator.py"
EXPECTED = (
    "M08_D2_IDENTITY_RESET_SEQUENCE_ICARUS_PASS",
    "M08_D2_IDENTITY_R_BACKPRESSURE_ICARUS_PASS",
    "M08_D2_IDENTITY_MID_RESPONSE_RESET_ICARUS_PASS",
    "M08_D2_IDENTITY_STOPPED_CLOCK_NO_R_RESPONSE_EXPECTED",
    "M08_D2_SILENT_SLAVE_EXPECTED_NO_RESPONSE_NO_PROTECTION",
)


class M08PSPLStallForensics(unittest.TestCase):
    def test_first_party_ps_to_slaves_topology_and_runtime_clock_gap(self):
        bd = BD.read_text()
        fan = FAN.read_text()
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP0 1", bd)
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP1 0", bd)
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP2 0", bd)
        self.assertIn("CONFIG.PSU__FPGA_PL0_ENABLE 1", bd)
        self.assertIn("CONFIG.NUM_SI 1 CONFIG.NUM_MI 2", bd)
        for wire in (
            "ps/M_AXI_HPM0_FPD] [intf_required ctrl_sc/S00_AXI",
            "ctrl_sc/M00_AXI] [intf_required identity/S_AXI",
            "ctrl_sc/M01_AXI] [intf_required page/S_AXI",
        ):
            self.assertIn(wire, bd)
        for clk in ("ps/maxihpm0_fpd_aclk", "ctrl_sc/aclk",
                    "pl_reset/slowest_sync_clk", "identity/aclk", "page/aclk"):
            self.assertIn("[pin_required " + clk + "]", bd)
        self.assertIn("connect_bd_net [pin_required ps/pl_clk0]", bd)
        self.assertIn("connect_bd_net [pin_required ps/pl_resetn0]", bd)
        self.assertIn("connect_bd_net [pin_required reset_inv/Res]", bd)
        self.assertIn("connect_bd_net [pin_required logic_one/dout] [pin_required pl_reset/dcm_locked]", bd)
        self.assertIn("pl_reset/interconnect_aresetn", bd)
        self.assertIn("pl_reset/peripheral_aresetn", bd)
        self.assertIn("CONFIG.C_EXT_RESET_HIGH", bd)
        self.assertIn("source $baseline", fan)
        self.assertIn("fan_pin=A12", fan)
        # SOURCE proof of topology is deliberately NOT proof Linux kept pl_clk0
        # enabled or that the actual reset was deasserted after manager load.

    def test_axi_responses_require_running_clock_and_internal_watchdog_is_narrow(self):
        identity = IDENTITY.read_text()
        page = PAGE.read_text()
        shell = SHELL.read_text()
        self.assertIn("always @(posedge aclk)", identity)
        self.assertIn("if (!aresetn)", identity)
        self.assertIn("assign s_axi_arready = aresetn && !s_axi_rvalid", identity)
        self.assertIn("s_axi_rvalid <= 1'b1", identity)
        self.assertIn("if (s_axi_rready)", identity)
        self.assertIn("always @(posedge aclk)", page)
        self.assertIn("host_wait_count==8'd63", page)
        self.assertIn("bridge_fault<=1", page)
        self.assertIn("ST_HOST_WAIT:", page)
        self.assertIn("ENABLE_COMPUTE(1'b0)", shell)
        # The page bank's synchronous 64-cycle watchdog is behind SmartConnect.
        # It cannot rescue an upstream request if its own aclk never toggles.
        self.assertNotIn("host_wait_count", identity)

    def test_address_and_original_hardware_evidence_are_not_conflated(self):
        overlay = OVERLAY.read_text()
        incident = INCIDENT.read_text()
        route = ROUTE.read_text()
        for name, address in (("m08-identity", "0xa0000000"),
                              ("m08-page", "0xa0001000")):
            self.assertIn('("' + name + '", 0x' + address[2:].upper(), overlay)
            self.assertIn(address.upper().replace("0X", "0x"), incident.lower().replace("0x", "0x"))
        self.assertIn("RTSTAT-10", route)
        self.assertIn("mi_handler_m_sc_areset_pipe", route)
        self.assertIn("99,999,001", route)
        self.assertIn("root cause not proven", incident.lower())
        self.assertIn("ORIGINAL", incident)
        self.assertIn("FAILED/INDETERMINATE", incident)

    def test_quarantine_is_unchanged_by_offline_diagnostics(self):
        op = OPERATOR.read_text()
        bench = TB.read_text()
        self.assertIn("reject_quarantined_mmio_mode(args.mode)", op)
        self.assertIn('demand(mode == "preflight"', op)
        self.assertNotIn("/dev/mem", bench)
        self.assertNotIn("/dev/uio", bench)
        self.assertIn("silent_arready=1'b0", bench)
        self.assertIn("silent_rvalid=1'b0", bench)
        self.assertIn("NO_PROTECTION", bench)
        self.assertNotIn("program_hw_devices", bench)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus required: source-only structural checks do NOT imply RTL simulation PASS")
    def test_actual_identity_rtl_reset_stall_and_silent_negative(self):
        with tempfile.TemporaryDirectory() as d:
            binary = Path(d) / "m08_d2_forensics.vvp"
            compiled = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m08_axil_identity_stall_forensics",
                 "-o", str(binary), str(IDENTITY), str(TB)],
                capture_output=True, text=True, timeout=90, check=False)
            self.assertEqual(compiled.returncode, 0,
                             compiled.stdout + "\n" + compiled.stderr)
            self.assertFalse(compiled.stderr.strip(),
                             "review all Icarus compiler warnings: " + compiled.stderr)
            ran = subprocess.run(["vvp", str(binary)], capture_output=True,
                                 text=True, timeout=30, check=False)
            self.assertEqual(ran.returncode, 0, ran.stdout + "\n" + ran.stderr)
            self.assertEqual(ran.stderr.strip(), "")
            self.assertNotIn("FATAL", ran.stdout)
            for marker in EXPECTED:
                self.assertEqual(ran.stdout.splitlines().count(marker), 1, ran.stdout)


if __name__ == "__main__":
    unittest.main()
