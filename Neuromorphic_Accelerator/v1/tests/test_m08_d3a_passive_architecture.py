"""D3.1 passive KV260 candidate source and synthetic native readback negatives.

No Vivado, board, kernel, FPGA manager, JTAG, MMIO or hardware evidence
is simulated by these tests. Owner alone can run genuine Vivado offline.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/m08_d3a_passive_candidate_source_gate.py"
spec = importlib.util.spec_from_file_location("m08_d3a_source_gate", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class D3APassiveArchitecture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (m.ORIGINAL_BD, m.ORIGINAL_FAN,
                     m.CANDIDATE_TCL, m.MANIFEST):
            dst = self.root / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dst)

    def test_first_party_passive_candidate_source_is_not_hardware_release(self):
        record = m.verify_source()
        self.assertEqual(
            record["status"], "D3A_PASSIVE_NO_PS_PL_AXI_SOURCE_CANDIDATE_ONLY")
        self.assertEqual(record["ps_to_pl_master_ports_exposed"], 0)
        self.assertFalse(record["physical_programming_allowed"])
        self.assertFalse(record["physical_fan_or_clock_proof"])
        self.assertEqual(record["D3_2_protected_mmio_gate"], "BLOCKED")
        self.assertTrue(record["original_m08_bitstream_quarantined"])

    def test_bad_ps_gp0_enable_rejected(self):
        path = self.root / m.CANDIDATE_TCL
        path.write_text(path.read_text().replace(
            "CONFIG.PSU__USE__M_AXI_GP0 0", "CONFIG.PSU__USE__M_AXI_GP0 1"))
        with self.assertRaisesRegex(m.D3Rejected, "disable"):
            m.verify_source(self.root)

    def test_original_fan_immutable_and_pin_drift_rejected(self):
        path = self.root / m.ORIGINAL_FAN
        path.write_text(path.read_text().replace(
            "PACKAGE_PIN A12", "PACKAGE_PIN B11"))
        with self.assertRaisesRegex(m.D3Rejected, "original M08 TTC fan route changed"):
            m.verify_source(self.root)
        shutil.copy2(ROOT / m.ORIGINAL_FAN, path)
        candidate = self.root / m.CANDIDATE_TCL
        candidate.write_text(candidate.read_text().replace(
            "PACKAGE_PIN A12", "PACKAGE_PIN B11"))
        with self.assertRaisesRegex(m.D3Rejected, "fan|contract"):
            m.verify_source(self.root)

    def test_bad_manifest_approval_and_missing_atb_gate_rejected(self):
        path = self.root / m.MANIFEST
        obj = json.loads(path.read_text())
        obj["hardware_safety"]["owner_mmio_authorized"] = True
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(m.D3Rejected, "hardware approval"):
            m.verify_source(self.root)
        obj["hardware_safety"]["owner_mmio_authorized"] = False
        obj["D3_2_blocking_dependencies"]["ps_atb4_fpd_boot_configuration"] = "PASS"
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(m.D3Rejected, "remain open"):
            m.verify_source(self.root)

    def test_live_programming_or_inherited_hpm_source_command_rejected(self):
        path = self.root / m.CANDIDATE_TCL
        original = path.read_text()
        path.write_text(original + "\nprogram_hw_devices\n")
        with self.assertRaisesRegex(m.D3Rejected, "dangerous"):
            m.verify_source(self.root)
        path.write_text(original + "\nsource $baseline\n")
        with self.assertRaisesRegex(m.D3Rejected, "dangerous"):
            m.verify_source(self.root)
        path.write_text(original + "\nconnect_bd_intf_net ps/M_AXI_HPM0_FPD sc/S00_AXI\n")
        with self.assertRaisesRegex(m.D3Rejected, "must not generate"):
            m.verify_source(self.root)

    def test_untrusted_source_symlink_rejected(self):
        file = self.root / m.CANDIDATE_TCL
        moved = self.root / "other.tcl"
        file.rename(moved)
        file.symlink_to(moved)
        with self.assertRaisesRegex(m.D3Rejected, "symlinked"):
            m.verify_source(self.root)

    def synth_native_report(self):
        folder = self.root / "native"
        folder.mkdir()
        (folder / "d3a_project").mkdir()
        report = dict(m.KNOWN_NATIVE)
        report.update({
            "vivado_version": "2025.2",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "ps_pl0_nominal_request_mhz": "100",
            "ps_pl0_native_frequency_hz": "99999001",
        })
        (folder / "10_d3a_passive_bd_readback.txt").write_text(
            "".join(k + "=" + v + "\n" for k, v in report.items()))
        (folder / "12_d3a_fan_a12.xdc").write_text(
            "\n".join(m.EXPECTED_XDC) + "\n")
        (folder / "11_d3a_passive_bd_export.tcl").write_text(
            "# SYNTHETIC: not genuine owner Vivado\n"
            "create_bd_design m08_d3a_passive_fan\n" * 3)
        return folder

    def test_synthetic_native_readback_accepted_but_no_board_proof(self):
        folder = self.synth_native_report()
        result = m.verify_native(folder)
        self.assertFalse(result["hardware_bitstream_or_mmio_allowed"])
        self.assertEqual(result["ps_pl0_hz_native_reported"], 99999001)
        self.assertFalse(result["native_clock_in_linux_proven"])
        self.assertFalse(result["physical_fan_continuity_proven"])
        self.assertFalse(result["PS_ATB4_timeout_proven"])

    def test_native_report_cannot_claim_hpm_or_physical_fan(self):
        folder = self.synth_native_report()
        report = folder / "10_d3a_passive_bd_readback.txt"
        report.write_text(report.read_text().replace(
            "ps_hpm0_fpd=DISABLED", "ps_hpm0_fpd=ENABLED"))
        with self.assertRaisesRegex(m.D3Rejected, "ps_hpm0_fpd"):
            m.verify_native(folder)
        report.write_text(report.read_text().replace(
            "ps_hpm0_fpd=ENABLED", "ps_hpm0_fpd=DISABLED").replace(
            "physical_fan_cooling=NOT_PROVEN", "physical_fan_cooling=PROVEN"))
        with self.assertRaisesRegex(m.D3Rejected, "physical_fan_cooling"):
            m.verify_native(folder)

    def test_corrupt_native_fan_constraint_rejected(self):
        folder = self.synth_native_report()
        xdc = folder / "12_d3a_fan_a12.xdc"
        xdc.write_text(xdc.read_text().replace("PACKAGE_PIN A12", "PACKAGE_PIN B11"))
        with self.assertRaisesRegex(m.D3Rejected, "fan A12"):
            m.verify_native(folder)

    def test_no_native_evidence_is_not_native_pass(self):
        result = m.verify_source(self.root)
        self.assertEqual(result["native_vivado_run"], "NOT_CLAIMED")
        self.assertNotIn("native", result)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh not present; Tcl syntax cannot be claimed")
    def test_passive_vivado_script_is_syntactically_complete_without_executing_it(self):
        # Tcl info complete parses brace/quote nesting, not vendor Tcl semantics.
        # Never source/eval the untrusted code or run any Vivado/hardware tools.
        path = ROOT / m.CANDIDATE_TCL
        probe = (
            "set handle [open {" + str(path) + "} r]\n"
            "set contents [read $handle]\n"
            "close $handle\n"
            "puts [info complete $contents]\n"
        )
        p = subprocess.run(["tclsh"], input=probe, capture_output=True,
                           text=True, timeout=10, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "1")

    def test_gate_script_itself_never_runs_hardware(self):
        source = PATH.read_text()
        for bad in ("subprocess.run(", "os.system(", "open_hw_manager(",
                    "program_hw_devices(", "write_bitstream(", "xmutil "):
            self.assertNotIn(bad, source)


if __name__ == "__main__":
    unittest.main()
