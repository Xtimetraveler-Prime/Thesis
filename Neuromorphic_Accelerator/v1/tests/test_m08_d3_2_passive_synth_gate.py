"""M08 D3.2 passive-fan synthesis source gate; all evidence synthetic (NO BOARD)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/m08_d3_2_passive_synth_gate.py"
TCL = ROOT / "scripts/m08_d3_2_passive_synth_only.tcl"
D3A = ROOT / "scripts/m08_d3a_passive_candidate_source_gate.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    return v


gate = load(AUDIT, "m08_d3_2_passive_synth_gate")
d3a = load(D3A, "m08_d3a_passive_synth_parent")


class PassiveSynthGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "v1"
        for name in (d3a.ORIGINAL_BD, d3a.ORIGINAL_FAN,
                     d3a.CANDIDATE_TCL, d3a.MANIFEST,
                     "scripts/m08_d3_2_passive_synth_gate.py",
                     "scripts/m08_d3a_passive_candidate_source_gate.py",
                     "scripts/m08_d3_2_passive_synth_only.tcl"):
            src = ROOT / name
            dst = self.root / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        self.run = Path(tmp.name) / "m08_d3_2_passive_synth_SYNTHETIC" / "output"
        self.run.mkdir(parents=True)

    def test_passive_synth_source_gate_no_bitstream_ever(self):
        outcome = gate.source_gate()
        self.assertEqual(outcome["status"],
                         "M08_D3_2_PASSIVE_SYNTH_SOURCE_APPROVED_FOR_PC_OFFLINE_ONLY")
        self.assertFalse(outcome["native_synth_proven"])
        self.assertFalse(outcome["native_route_proven"])
        self.assertFalse(outcome["physical_programming_authorized"])
        self.assertFalse(outcome["hpm0_interface_present"])
        self.assertFalse(outcome["protected_hpm0_bitstream_authorized"])

    def test_reject_added_impl_run_bitstream_command(self):
        path = self.root / "scripts/m08_d3_2_passive_synth_only.tcl"
        path.write_text(path.read_text() + "\nlaunch_runs impl_1\nwrite_bitstream -force output.bit\n")
        with self.assertRaisesRegex(gate.SynthRejected, "forbidden"):
            gate.source_gate(self.root)

    def test_reject_wrong_synthesis_run(self):
        path = self.root / "scripts/m08_d3_2_passive_synth_only.tcl"
        path.write_text(path.read_text().replace(
            "launch_runs synth_1 -jobs 2", "launch_runs impl_1 -jobs 2"))
        with self.assertRaisesRegex(gate.SynthRejected, "only synth_1|forbidden"):
            gate.source_gate(self.root)

    def test_reject_axi_master_on_original_d3a(self):
        path = self.root / d3a.CANDIDATE_TCL
        path.write_text(path.read_text().replace(
            "CONFIG.PSU__USE__M_AXI_GP0 0", "CONFIG.PSU__USE__M_AXI_GP0 1"))
        with self.assertRaisesRegex(d3a.D3Rejected, "disable"):
            gate.source_gate(self.root)

    def test_reject_removed_fan_pin_constraint(self):
        path = self.root / "scripts/m08_d3_2_passive_synth_only.tcl"
        path.write_text(path.read_text().replace(
            "get_property PACKAGE_PIN [get_ports M08_FAN_PWM]",
            "get_property PACKAGE_PIN [get_ports M08_FAN_NOT_PRESENT]"))
        with self.assertRaisesRegex(gate.SynthRejected, "source assertion"):
            gate.source_gate(self.root)

    def mock_synth_report(self):
        d = self.run
        (d / "d3a_project").mkdir()
        parent = dict(d3a.KNOWN_NATIVE)
        parent.update({
            "vivado_version": "2025.2",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "ps_pl0_nominal_request_mhz": "100",
            "ps_pl0_native_frequency_hz": "99999001",
        })
        (d / "10_d3a_passive_bd_readback.txt").write_text(
            "".join(k + "=" + v + "\n" for k, v in parent.items()))
        (d / "12_d3a_fan_a12.xdc").write_text(
            "\n".join(d3a.EXPECTED_XDC) + "\n")
        (d / "11_d3a_passive_bd_export.tcl").write_text(
            "# SYNTHETIC, NOT VIVADO:\ncreate_bd_design m08_d3a_passive_fan\n" * 3)
        native = dict(gate.KNOWN)
        native.update({
            "vivado_version": "2025.2",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "synth_run_status": "synth_design Complete!",
        })
        (d / "20_passive_synth_readback.txt").write_text(
            "".join(k + "=" + v + "\n" for k, v in native.items()))
        (d / "21_passive_synth_utilization.rpt").write_text(
            "SYNTHETIC utilization summary, not vendor proof\n")
        (d / "22_passive_synth_timing.rpt").write_text(
            "SYNTHETIC timing summary, not routed proof\n")
        return d

    def test_synthetic_native_evidence_is_report_only_not_hardware(self):
        p = self.mock_synth_report()
        result = gate.native_report(p)
        self.assertTrue(result["native_reported_synth_complete"])
        self.assertFalse(result["bitstream_generated"])
        self.assertFalse(result["physical_mmio_authorized"])
        self.assertFalse(result["physical_fan_continuity_proven"])
        self.assertFalse(result["routed_timing_validated"])

    def test_reject_synthetic_changed_ps_axi_or_bitstream_claim(self):
        d = self.mock_synth_report()
        report = d / "20_passive_synth_readback.txt"
        report.write_text(report.read_text().replace(
            "ps_to_pl_axi=DISABLED", "ps_to_pl_axi=ENABLED"))
        with self.assertRaisesRegex(gate.SynthRejected, "ps_to_pl_axi"):
            gate.native_report(d)
        report.write_text(report.read_text().replace(
            "ps_to_pl_axi=ENABLED", "ps_to_pl_axi=DISABLED").replace(
            "bitstream=NOT_GENERATED", "bitstream=GENERATED"))
        with self.assertRaisesRegex(gate.SynthRejected, "bitstream"):
            gate.native_report(d)

    def test_reject_synthetic_incomplete_run_and_missing_reports(self):
        d = self.mock_synth_report()
        report = d / "20_passive_synth_readback.txt"
        report.write_text(report.read_text().replace(
            "synth_design Complete!", "synth_design Failed!"))
        with self.assertRaisesRegex(gate.SynthRejected, "completion"):
            gate.native_report(d)
        report.write_text(report.read_text().replace(
            "synth_design Failed!", "synth_design Complete!"))
        (d / "22_passive_synth_timing.rpt").unlink()
        with self.assertRaisesRegex(gate.SynthRejected, "missing"):
            gate.native_report(d)

    def test_reject_synth_report_symlink(self):
        d = self.mock_synth_report()
        source = d / "20_passive_synth_readback.txt"
        backup = d / "saved.txt"
        source.rename(backup)
        source.symlink_to(backup)
        with self.assertRaisesRegex(gate.SynthRejected, "symlink"):
            gate.native_report(d)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh unavailable: syntax only")
    def test_tcl_is_syntactically_complete_no_vendor_execution(self):
        probe = ("set f [open {" + str(TCL) + "} r]\n"
                 "set text [read $f]\nclose $f\n"
                 "puts [info complete $text]\n")
        output = subprocess.run(["tclsh"], input=probe, text=True,
                                capture_output=True, timeout=10, check=False)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(output.stdout.strip(), "1")

    def test_shell_owner_runner_syntax_and_only_fresh_pc_projects(self):
        runner = ROOT / "scripts/run_m08_d3_2_passive_synth_pc.sh"
        source = runner.read_text()
        self.assertIn("set -euo pipefail", source)
        self.assertIn("m08_d3_2_passive_synth_XXXXXXXX", source)
        self.assertIn("m08_d3a_passive_fan_bd_candidate.tcl", source)
        self.assertIn("m08_d3_2_passive_synth_only.tcl", source)
        self.assertIn("99_evidence_sha256.txt", source)
        self.assertEqual(source.count("vivado -mode batch"), 2)
        for prohibited in ("launch_runs impl_1", "write_bitstream -",
                           "program_hw_devices", "xmutil unloadapp",
                           "/dev/mem", "/dev/uio", "git clean", "rm -rf"):
            self.assertNotIn(prohibited, source)
        if shutil.which("bash"):
            actual = subprocess.run(["bash", "-n", str(runner)],
                                    capture_output=True, text=True, timeout=10,
                                    check=False)
            self.assertEqual(actual.returncode, 0, actual.stderr)

    def test_gate_program_contains_no_hardware_or_vendor_calls(self):
        source = AUDIT.read_text()
        for forbidden in (
            "subprocess.run(", "open_hw_manager(", "program_hw_devices(",
            "write_bitstream(", "os.system(", "vivado -mode",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
