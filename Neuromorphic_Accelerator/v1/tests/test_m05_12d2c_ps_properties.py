"""M05.12d.2c genuine-passive PS CONFIG discovery, synthetic host tests ONLY.

Original owner Vivado 2025.2 PS v3.5 D2a had no default HP/HPC ports and
unrecognized PCW__ keys. These tests must NOT be mistaken for real key proof.
"""
from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d2c_ps_properties_audit import (
    SCOPE, PART, TARGETS, verify_ps_property_report,
)


def fixture(values: dict[str, str] | None = None):
    if values is None:
        values = {
            "PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ": "100",
            "PSU__USE__M_AXI_GP0": "0",
            "PSU__USE__M_AXI_GP1": "0",
            "PSU__USE__S_AXI_GP0": "0",
            "PSU__USE__S_AXI_GP2": "1",
            "PSU__USE__IRQ0": "0",
        }
    lines = [
        f"META|part|{PART}",
        "META|vlnv|xilinx.com:ip:zynq_ultra_ps_e:3.5",
        f"META|scope|{SCOPE}",
        "META|source_mgmt_mode|All",
        f"META|property_count|{len(values)}",
    ]
    lines.extend(f"TARGET|{key}|{int(key in values)}" for key in TARGETS)
    lines.extend(
        f"PROP|{key}|{base64.b64encode(value.encode()).decode() if value else '~'}"
        for key, value in sorted(values.items())
    )
    return "\n".join(lines) + "\n"


class M0512D2CPSPropertyTests(unittest.TestCase):
    def test_genuine_output_schema_can_report_available_psu_keys(self):
        facts = verify_ps_property_report(fixture())
        self.assertEqual(facts["property_count"], 6)
        self.assertEqual(facts["targets_present"], 6)
        self.assertEqual(facts["target_values"]["PSU__USE__M_AXI_GP0"], "0")
        self.assertEqual(facts["target_values"]["PSU__USE__M_AXI_GP2"], None)

    def test_empty_config_value_is_an_explicit_default_not_absence(self):
        raw = fixture({"PSU__USE__M_AXI_GP0": ""})
        facts = verify_ps_property_report(raw)
        self.assertEqual(facts["property_count"], 1)
        self.assertEqual(facts["target_values"]["PSU__USE__M_AXI_GP0"], "")
        with self.assertRaises(ValueError):
            verify_ps_property_report(raw.replace(
                "PROP|PSU__USE__M_AXI_GP0|~",
                "PROP|PSU__USE__M_AXI_GP0|", 1))

    def test_wrong_target_presence_missing_duplicate_and_extra_rejected(self):
        src = fixture()
        row = "TARGET|PSU__USE__M_AXI_GP0|1\n"
        for bad in (
            src.replace(row, "", 1),
            src.replace(row, row * 2, 1),
            src.replace(row, "TARGET|PSU__USE__M_AXI_GP0|0\n", 1),
            src.replace(row, "TARGET|PSU__USE__M_AXI_GP0|true\n", 1),
            src + "TARGET|UNKNOWN|1\n",
        ):
            with self.subTest(bad=bad[:130]):
                with self.assertRaises(ValueError):
                    verify_ps_property_report(bad)

    def test_wrong_part_ip_mode_scope_property_count_rejected(self):
        src = fixture()
        for bad in (
            src.replace(f"META|part|{PART}", "META|part|xczu9eg", 1),
            src.replace("zynq_ultra_ps_e:3.5", "ps7:5.0", 1),
            src.replace(f"META|scope|{SCOPE}", "META|scope|BOARD_PRESET_APPLIED", 1),
            src.replace("META|source_mgmt_mode|All", "META|source_mgmt_mode|None", 1),
            src.replace("META|property_count|6", "META|property_count|5", 1),
            src.replace("META|property_count|6\n", "", 1),
            src[:-1],
        ):
            with self.subTest(bad=bad[:110]):
                with self.assertRaises(ValueError):
                    verify_ps_property_report(bad)

    def test_property_format_duplicate_unsorted_noncanonical_and_unknown_rejected(self):
        src = fixture()
        row = "PROP|PSU__USE__M_AXI_GP0|MA==\n"
        for bad in (
            src.replace(row, row * 2, 1),
            src.replace(row, "PROP|PSU__USE__M_AXI_GP0|not_base64!\n", 1),
            src.replace(row, "PROP|PCW_USE_M_AXI_GP0|MA==\n", 1),
            src.replace(row, "PROP|PSU__USE__M_AXI_GP0|MA==AA\n", 1),
            src.replace(row, "PROP|PSU__USE__M_AXI_GP0|MA=\n", 1),
            src.replace(row, "", 1),
            src + "PROP|PSU__USE__S_AXI_GP999|MA==\n",
        ):
            with self.subTest(bad=bad[-130:]):
                with self.assertRaises(ValueError):
                    verify_ps_property_report(bad)

    def test_sorted_property_list_and_raw_escaping_are_strict(self):
        src = fixture()
        first = "PROP|PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ|MTAw\n"
        second = "PROP|PSU__USE__IRQ0|MA==\n"
        with self.assertRaises(ValueError):
            verify_ps_property_report(
                src.replace(first, "SWAP_SENTINEL\n", 1)
                   .replace(second, first, 1)
                   .replace("SWAP_SENTINEL\n", second, 1)
            )
        with self.assertRaises(ValueError):
            verify_ps_property_report(
                src.replace("PROP|PSU__USE__IRQ0|MA==",
                            "PROP|PSU__USE__IRQ0|AAo=", 1))

    def test_owner_d2c_ascii_sort_regression_stm_precedes_s_axi(self):
        # Owner original 2026-11-09 D2c report (57 properties) was valid
        # Tcl 'lsort' but rejected by the old Python sorted(key=str.lower).
        # This smaller fixture includes real observed keys/defaults only;
        # it is NOT a replacement for the original Vivado report.
        observed = {
            "PSU__USE__STM": "0",
            "PSU__USE__S_AXI_ACE": "0",
            "PSU__USE__S_AXI_ACP": "0",
            "PSU__USE__S_AXI_GP0": "0",
            "PSU__USE__M_AXI_GP2": "1",
            "PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ": "100",
            "PSU__FPGA_PL0_ENABLE": "1",
        }
        raw = fixture(observed)
        self.assertLess(raw.index("PROP|PSU__USE__STM|"),
                        raw.index("PROP|PSU__USE__S_AXI_ACE|"))
        self.assertEqual(verify_ps_property_report(raw)["property_count"], 7)
        self.assertEqual(
            verify_ps_property_report(raw)["target_values"]["PSU__USE__M_AXI_GP2"], "1"
        )
        self.assertEqual(
            verify_ps_property_report(raw)["target_values"]["PSU__USE__S_AXI_GP0"], "0"
        )
        lines = raw.splitlines(keepends=True)
        stm = next(i for i, row in enumerate(lines)
                   if row.startswith("PROP|PSU__USE__STM|"))
        s_axi = next(i for i, row in enumerate(lines)
                     if row.startswith("PROP|PSU__USE__S_AXI_ACE|"))
        lines[stm], lines[s_axi] = lines[s_axi], lines[stm]
        with self.assertRaisesRegex(ValueError, "not sorted"):
            verify_ps_property_report("".join(lines))
        code = (ROOT / "scripts/m05_12d2c_ps_properties_audit.py").read_text()
        self.assertIn("sorted(values)", code)
        self.assertNotIn("sorted(values, key=str.lower)", code)
        tcl = (ROOT / "scripts/m05_12d2c_ps_properties.tcl").read_text()
        self.assertIn("foreach prop [lsort [list_property $ps]]", tcl)

    def test_cli_requires_original_report_and_never_modifies_it(self):
        script = ROOT / "scripts/m05_12d2c_ps_properties_audit.py"
        with tempfile.TemporaryDirectory(prefix="m05_12d2c_") as temp:
            original = fixture()
            target = Path(temp) / "01_ps_properties.txt"
            target.write_text(original)
            cmd = [sys.executable, str(script), "--report", str(target)]
            good = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("PASS: M05.12d.2c independent", good.stdout)
            self.assertIn("TARGET_DEFAULT|PSU__USE__M_AXI_GP0|0", good.stdout)
            self.assertEqual(target.read_text(), original)
            target.unlink()
            bad = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("ERROR: M05.12d.2c", bad.stderr)

    def test_no_board_no_ps_changes_and_true_config_property_discovery(self):
        tcl = (ROOT / "scripts/m05_12d2c_ps_properties.tcl").read_text()
        run = ROOT / "scripts/run_m05_12d2c_ps_properties.sh"
        sh = run.read_text()
        for required in (
            "create_project -in_memory", "source_mgmt_mode All",
            "get_ipdefs -all -quiet xilinx.com:ip:zynq_ultra_ps_e",
            "create_bd_cell -type ip", "list_property $ps",
            "get_property \"CONFIG.$key\" $ps", "binary encode base64",
            "PSU__USE__M_AXI_GP0", "PSU__USE__S_AXI_GP0",
            "PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ",
            "META|property_count|", "PROP|$key|$encoded",
        ):
            self.assertIn(required, tcl)
        for expected in (
            "source_sha256.txt", "commit.txt", "result.txt",
            "01_ps_properties.txt", "02_vivado.log",
            "03_independent_audit.log", "m05_12d2c_ps_properties_audit.py",
        ):
            self.assertIn(expected, sh)
        for forbidden in (
            "apply_bd_automation", "program_hw_devices", "connect_hw_server",
            "open_hw_target", "open_project", "write_bitstream",
            "launch_runs", "assign_bd_address", "connect_bd_intf_net",
            "connect_bd_net", "set_property -dict", "validate_bd_design",
            "xsdb", "rm -rf",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, tcl)
                self.assertNotIn(forbidden, sh)
        self.assertEqual(
            tcl.count("set_property source_mgmt_mode All [current_project]"), 1
        )
        syntax = subprocess.run(["bash", "-n", str(run)],
                                capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        help_run = subprocess.run(["bash", str(run), "--help"],
                                  capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("NO BOARD", help_run.stdout)
        rejected = subprocess.run(["bash", str(run), "--run-on-board"],
                                  capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)


if __name__ == "__main__":
    unittest.main()
