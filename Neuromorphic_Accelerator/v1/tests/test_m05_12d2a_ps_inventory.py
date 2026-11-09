"""M05.12d.2a synthetic K26 PS-IP discovery audit + read-only runner safety.

The PS catalog remains genuinely UNVERIFIED until owner Vivado 2025.2 run.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d2a_ps_inventory_audit import (
    PART, SCOPE, PORTS, PINS, PROPS, verify_ps_inventory,
)


def inventory():
    lines = [
        f"META|part|{PART}",
        "META|vlnv|xilinx.com:ip:zynq_ultra_ps_e:3.5",
        f"META|scope|{SCOPE}",
        "META|source_mgmt_mode|All",
    ]
    for name, role in PORTS.items():
        lines.append(f"IF|{name}|0|NA")
    for name, role in PINS.items():
        lines.append(f"PIN|{name}|0|NA")
    for name in PROPS:
        lines.append(f"PROP|{name}|UNAVAILABLE")
    return "\n".join(lines) + "\n"


class M0512D2APSInventoryTests(unittest.TestCase):
    def test_fully_disabled_default_catalog_is_discovery_not_integration(self):
        self.assertEqual(verify_ps_inventory(inventory()), {
            "ps_to_pl_master_defaults": 0,
            "pl_to_ps_slave_defaults": 0,
            "pin_defaults": 0,
        })

    def test_enabled_directional_ports_count_not_assumed_from_defaults(self):
        src = inventory()
        src = src.replace("IF|M_AXI_HPM0_FPD|0|NA",
                          "IF|M_AXI_HPM0_FPD|1|MASTER", 1)
        src = src.replace("IF|S_AXI_HP0_FPD|0|NA",
                          "IF|S_AXI_HP0_FPD|1|SLAVE", 1)
        src = src.replace("PIN|pl_clk0|0|NA", "PIN|pl_clk0|1|O", 1)
        self.assertEqual(verify_ps_inventory(src), {
            "ps_to_pl_master_defaults": 1,
            "pl_to_ps_slave_defaults": 1,
            "pin_defaults": 1,
        })

    def test_wrong_direction_or_enabled_field_is_rejected(self):
        src = inventory()
        for bad in (
            src.replace("IF|M_AXI_HPM0_FPD|0|NA",
                        "IF|M_AXI_HPM0_FPD|1|SLAVE", 1),
            src.replace("IF|S_AXI_HP0_FPD|0|NA",
                        "IF|S_AXI_HP0_FPD|1|MASTER", 1),
            src.replace("IF|S_AXI_HP0_FPD|0|NA",
                        "IF|S_AXI_HP0_FPD|false|NA", 1),
            src.replace("PIN|pl_clk0|0|NA",
                        "PIN|pl_clk0|1|I", 1),
        ):
            with self.subTest(bad=bad[:80]):
                with self.assertRaises(ValueError):
                    verify_ps_inventory(bad)

    def test_missing_duplicate_extra_wrong_vlnv_or_preset_is_rejected(self):
        src = inventory()
        row = "IF|M_AXI_HPM0_FPD|0|NA\n"
        for bad in (
            src.replace(row, "", 1),
            src.replace(row, row * 2, 1),
            src + "IF|M_AXI_HP999_FPD|1|MASTER\n",
            src.replace("META|vlnv|xilinx.com:ip:zynq_ultra_ps_e:3.5",
                        "META|vlnv|xilinx.com:ip:ps7:5.5", 1),
            src.replace(f"META|scope|{SCOPE}", "META|scope|PHYSICAL_HARDWARE"),
            src.replace("META|source_mgmt_mode|All",
                        "META|source_mgmt_mode|DisplayOnly"),
            src.replace("PIN|pl_clk0|0|NA\n", "", 1),
            src.replace("PROP|PCW_USE_FABRIC_INTERRUPT|UNAVAILABLE\n", "", 1),
            src[:-1],
        ):
            with self.subTest(bad=bad[:110]):
                with self.assertRaises(ValueError):
                    verify_ps_inventory(bad)

    def test_properties_can_be_observed_but_absence_not_assumed_enabled(self):
        good = inventory().replace(
            "PROP|PCW_USE_M_AXI_GP0|UNAVAILABLE",
            "PROP|PCW_USE_M_AXI_GP0|1",
        ).replace(
            "PROP|PCW_FPGA0_PERIPHERAL_FREQMHZ|UNAVAILABLE",
            "PROP|PCW_FPGA0_PERIPHERAL_FREQMHZ|100.0",
        )
        self.assertEqual(verify_ps_inventory(good)["pin_defaults"], 0)
        duplicate = good.replace(
            "PROP|PCW_USE_M_AXI_GP0|1\n",
            "PROP|PCW_USE_M_AXI_GP0|1\n" * 2, 1,
        )
        with self.assertRaises(ValueError):
            verify_ps_inventory(duplicate)

    def test_cli_is_read_only_and_missing_report_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="m05_12d2a_ps_") as td:
            f = Path(td) / "report.txt"
            contents = inventory()
            f.write_text(contents)
            cmd = [sys.executable,
                   str(ROOT / "scripts/m05_12d2a_ps_inventory_audit.py"),
                   "--report", str(f)]
            good = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("PASS: M05.12d.2a independently audited", good.stdout)
            self.assertEqual(f.read_text(), contents)
            f.unlink()
            bad = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("ERROR: M05.12d.2a", bad.stderr)

    def test_safe_offline_runner_and_no_configuration_side_effects(self):
        runner = ROOT / "scripts/run_m05_12d2a_ps_inventory.sh"
        syntax = subprocess.run(["bash", "-n", str(runner)],
                                capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        good = subprocess.run(["bash", str(runner), "--help"],
                              capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("NO BOARD", good.stdout)
        bad = subprocess.run(["bash", str(runner), "--invalid"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        tcl = (ROOT / "scripts/m05_12d2a_ps_inventory.tcl").read_text()
        runner_src = runner.read_text()
        for required in ("create_project -in_memory", "source_mgmt_mode All",
                         "get_ipdefs -all -quiet xilinx.com:ip:zynq_ultra_ps_e",
                         "create_bd_cell -type ip",
                         "get_bd_intf_pins", "get_bd_pins",
                         "get_property MODE", "get_property DIR",
                         "M_AXI_HPM0_FPD", "S_AXI_HP0_FPD",
                         "pl_clk0", "pl_resetn0"):
            self.assertIn(required, tcl)
        for required in ("source_sha256.txt", "commit.txt", "result.txt",
                         "01_ps_inventory.txt", "03_independent_audit.log",
                         "m05_12d2a_ps_inventory_audit.py"):
            self.assertIn(required, runner_src)
        for forbidden in ("program_hw_devices", "open_hw_target",
                          "connect_hw_server", "open_project",
                          "launch_runs", "write_bitstream", "xsdb",
                          "connect_bd_intf_net", "connect_bd_net",
                          "assign_bd_address", "set_property -dict",
                          "apply_bd_automation", "validate_bd_design",
                          "get_hw_devices", "rm -rf"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, tcl)
                self.assertNotIn(forbidden, runner_src)


if __name__ == "__main__":
    unittest.main()
