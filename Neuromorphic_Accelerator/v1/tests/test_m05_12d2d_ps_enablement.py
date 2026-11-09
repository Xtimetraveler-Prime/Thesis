"""M05.12d.2d genuine operator Vivado PS IP trial: synthetic host tests ONLY.

The checked-in Tcl is a controlled *scratch* PS instance configuration.
It neither boots/configures the physical PS nor proves DDR access or full BD.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d2d_ps_enablement_audit import (
    META, DEFAULT, READBACK, BEFORE, AFTER, PIN, WIDTH, CLOCKCFG, audit_trial,
)


def fixture():
    lines = []
    for section, data in (
        ("META", META), ("DEFAULT", DEFAULT), ("READBACK", READBACK),
        ("BEFORE", BEFORE), ("AFTER", AFTER), ("PIN", PIN), ("WIDTH", WIDTH),
    ):
        for name, value in data.items():
            if isinstance(value, tuple):
                lines.append("|".join((section, name, *value)))
            else:
                lines.append("|".join((section, name, value)))
    lines += [
        f"CLOCKCFG|{CLOCKCFG[0]}|100",
        f"CLOCKCFG|{CLOCKCFG[1]}|96.968727",
    ]
    return "\n".join(lines) + "\n"


class M0512D2DPSPortEnablementTests(unittest.TestCase):
    def test_full_synthetic_two_interface_activation_schema(self):
        facts = audit_trial(fixture())
        self.assertEqual(facts["fpm_master_enabled"], "M_AXI_HPM0_FPD")
        self.assertEqual(facts["hp_memory_slave_enabled"], "S_AXI_HP0_FPD")
        self.assertEqual(facts["master_width_bits"], 128)
        self.assertEqual(facts["slave_width_bits"], 128)
        self.assertEqual(facts["pl_clock_request_mhz"], "100")
        self.assertEqual(facts["pl_clock_ip_actual_mhz"], "96.968727")

    def test_wrong_part_vlnv_or_claimed_scope_denied(self):
        valid = fixture()
        for invalid in (
            valid.replace("xck26-sfvc784-2LV-c", "xczu9eg", 1),
            valid.replace("zynq_ultra_ps_e:3.5", "ps7:5.5", 1),
            valid.replace("SCRATCH_PS_PORT_ENABLE_ONLY_NO_PRESET_DDR",
                          "DDR_ENABLED_AND_WORKING", 1),
            valid.replace("META|source_mgmt_mode|All",
                          "META|source_mgmt_mode|None", 1),
        ):
            with self.subTest(invalid=invalid[:90]):
                with self.assertRaises(ValueError):
                    audit_trial(invalid)

    def test_config_default_and_postwrite_require_distinct_truthful_values(self):
        original = fixture()
        for invalid in (
            original.replace("DEFAULT|PSU__USE__M_AXI_GP0|0",
                             "DEFAULT|PSU__USE__M_AXI_GP0|1", 1),
            original.replace("DEFAULT|PSU__USE__S_AXI_GP2|0",
                             "DEFAULT|PSU__USE__S_AXI_GP2|1", 1),
            original.replace("READBACK|PSU__USE__M_AXI_GP0|1",
                             "READBACK|PSU__USE__M_AXI_GP0|0", 1),
            original.replace("READBACK|PSU__USE__S_AXI_GP2|1",
                             "READBACK|PSU__USE__S_AXI_GP2|0", 1),
            original.replace("READBACK|PSU__USE__M_AXI_GP2|1",
                             "READBACK|PSU__USE__M_AXI_GP2|0", 1),
        ):
            with self.subTest(invalid=invalid[:90]):
                with self.assertRaises(ValueError):
                    audit_trial(invalid)

    def test_actual_aximm_interface_pins_and_direction_required(self):
        original = fixture()
        for invalid in (
            original.replace("BEFORE|M_AXI_HPM0_FPD|0|NA",
                             "BEFORE|M_AXI_HPM0_FPD|1|MASTER", 1),
            original.replace("BEFORE|S_AXI_HP0_FPD|0|NA",
                             "BEFORE|S_AXI_HP0_FPD|1|SLAVE", 1),
            original.replace("AFTER|M_AXI_HPM0_FPD|1|MASTER",
                             "AFTER|M_AXI_HPM0_FPD|0|NA", 1),
            original.replace("AFTER|S_AXI_HP0_FPD|1|SLAVE",
                             "AFTER|S_AXI_HP0_FPD|0|NA", 1),
            original.replace("AFTER|S_AXI_HP0_FPD|1|SLAVE",
                             "AFTER|S_AXI_HP0_FPD|1|MASTER", 1),
            original.replace("AFTER|M_AXI_HPM0_LPD|1|MASTER",
                             "AFTER|M_AXI_HPM0_LPD|1|SLAVE", 1),
        ):
            with self.subTest(invalid=invalid[:90]):
                with self.assertRaises(ValueError):
                    audit_trial(invalid)

    def test_pin_clock_reset_width_and_frequency_guards(self):
        original = fixture()
        for invalid in (
            original.replace("PIN|pl_clk0|1|O",
                             "PIN|pl_clk0|0|NA", 1),
            original.replace("PIN|pl_resetn0|1|O",
                             "PIN|pl_resetn0|1|I", 1),
            original.replace("PIN|maxihpm0_fpd_aclk|1|I",
                             "PIN|maxihpm0_fpd_aclk|0|NA", 1),
            original.replace("PIN|saxihp0_fpd_aclk|1|I",
                             "PIN|saxihp0_fpd_aclk|1|O", 1),
            original.replace("WIDTH|PSU__MAXIGP0__DATA_WIDTH|128",
                             "WIDTH|PSU__MAXIGP0__DATA_WIDTH|256", 1),
            original.replace("WIDTH|PSU__SAXIGP2__DATA_WIDTH|128",
                             "WIDTH|PSU__SAXIGP2__DATA_WIDTH|256", 1),
            original.replace("CLOCKCFG|PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ|100",
                             "CLOCKCFG|PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ|0", 1),
            original.replace("CLOCKCFG|PSU__CRL_APB__PL0_REF_CTRL__ACT_FREQMHZ|96.968727",
                             "CLOCKCFG|PSU__CRL_APB__PL0_REF_CTRL__ACT_FREQMHZ|nan", 1),
        ):
            with self.subTest(invalid=invalid[-110:]):
                with self.assertRaises(ValueError):
                    audit_trial(invalid)

    def test_duplicate_partial_extra_and_truncated_report_denied(self):
        original = fixture()
        required = "AFTER|S_AXI_HP0_FPD|1|SLAVE\n"
        for invalid in (
            original.replace(required, "", 1),
            original.replace(required, required * 2, 1),
            original + "PHYSICAL|DDR|YES\n",
            original + "AFTER|UNKNOWN|1|MASTER\n",
            original[:-1],
        ):
            with self.subTest(invalid=invalid[-120:]):
                with self.assertRaises(ValueError):
                    audit_trial(invalid)

    def test_independent_audit_cli_read_only_and_fail_closed(self):
        script = ROOT / "scripts/m05_12d2d_ps_enablement_audit.py"
        with tempfile.TemporaryDirectory(prefix="m05_12d2d_") as d:
            report = Path(d) / "01_ps_enablement.txt"
            original = fixture()
            report.write_text(original)
            run = [sys.executable, str(script), "--report", str(report)]
            r = subprocess.run(run, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("PASS: M05.12d.2d independent K26", r.stdout)
            self.assertEqual(report.read_text(), original)
            report.unlink()
            r = subprocess.run(run, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("ERROR: M05.12d.2d", r.stderr)

    def test_source_is_offline_config_only_and_runner_fails_safe(self):
        tcl = (ROOT / "scripts/m05_12d2d_ps_enablement.tcl").read_text()
        shell = ROOT / "scripts/run_m05_12d2d_ps_enablement.sh"
        runner = shell.read_text()
        for required in (
            "create_project -in_memory -part $part",
            "set_property source_mgmt_mode All",
            "xilinx.com:ip:zynq_ultra_ps_e:3.5",
            "CONFIG.PSU__USE__M_AXI_GP0 1",
            "CONFIG.PSU__USE__S_AXI_GP2 1",
            "get_bd_intf_pins -quiet",
            "get_property MODE", "get_property DIR",
            "M_AXI_HPM0_FPD MASTER", "S_AXI_HP0_FPD SLAVE",
            "M_AXI_HPM0_LPD MASTER",
            "saxihp0_fpd_aclk I",
        ):
            self.assertIn(required, tcl)
        self.assertLess(tcl.index("DEFAULT|$key|$actual"),
                        tcl.index("set_property -dict"))
        self.assertLess(tcl.index("set_property -dict"),
                        tcl.index("AFTER|$name|1|$actual"))
        for requirement in (
            "source_sha256.txt", "working_tree_status.txt", "result.txt",
            "01_ps_enablement.txt", "02_vivado.log",
            "03_independent_audit.log", "m05_12d2d_ps_enablement_audit.py",
        ):
            self.assertIn(requirement, runner)
        for prohibited in (
            "open_hw_target", "connect_hw_server", "program_hw_devices",
            "open_project", "write_bitstream", "launch_runs",
            "assign_bd_address", "connect_bd_intf_net",
            "apply_bd_automation", "validate_bd_design",
            "xsdb", "rm -rf",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, tcl)
                self.assertNotIn(prohibited, runner)
        syntax = subprocess.run(["bash", "-n", str(shell)],
                                capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        ok = subprocess.run(["bash", str(shell), "--help"],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("NO BOARD", ok.stdout)
        bad = subprocess.run(["bash", str(shell), "--physical"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
