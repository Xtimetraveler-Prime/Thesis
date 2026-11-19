"""M08 D3.2 passive route-only source and report negatives; no board/Vivado."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts/m08_d3_2_passive_route_gate.py"
TCL = ROOT / "scripts/m08_d3_2_passive_route_only.tcl"
RUNNER = ROOT / "scripts/run_m08_d3_2_passive_route_pc.sh"


def import_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = import_file(GATE_PATH, "route_gate")
synth = import_file(ROOT / "scripts/m08_d3_2_passive_synth_gate.py",
                    "synth_mock_gate")
d3a = import_file(ROOT / "scripts/m08_d3a_passive_candidate_source_gate.py",
                  "d3a_mock_gate")


class PassiveRouteGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "v1"
        files = (
            d3a.ORIGINAL_BD, d3a.ORIGINAL_FAN, d3a.CANDIDATE_TCL,
            d3a.MANIFEST,
            "scripts/m08_d3a_passive_candidate_source_gate.py",
            "scripts/m08_d3_2_passive_synth_gate.py",
            "scripts/m08_d3_2_passive_synth_only.tcl",
            "scripts/m08_d3_2_passive_route_only.tcl",
            "scripts/run_m08_d3_2_passive_route_pc.sh",
            "scripts/run_m08_d3_2_passive_synth_pc.sh",
        )
        for f in files:
            out = self.root / f
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / f, out)
        self.run = Path(temp.name) / "M08" / "m08_d3_2_passive_synth_SYNTHETIC"
        self.out = self.run / "output"
        self.out.mkdir(parents=True)

    def test_route_source_stays_offline_and_no_image(self):
        status = g.source_gate()
        self.assertEqual(status["status"],
                         "M08_D3_2_PASSIVE_ROUTE_SOURCE_ACCEPTED_FOR_PC_ONLY")
        for key in ("genuine_route_proven", "routed_timing_and_drc_accepted",
                    "physical_fan_proven", "bitstream_created",
                    "hardware_mmio_authorized"):
            self.assertFalse(status[key])

    def test_route_rejects_unauthorized_image_creation(self):
        p = self.root / "scripts/m08_d3_2_passive_route_only.tcl"
        p.write_text(p.read_text() + "\nwrite_bitstream -force bad.bit\n")
        with self.assertRaisesRegex(g.RouteRejected, "forbidden"):
            g.source_gate(self.root)

    def test_route_rejects_implementation_write_bitstream_stage(self):
        p = self.root / "scripts/m08_d3_2_passive_route_only.tcl"
        p.write_text(p.read_text().replace(
            "launch_runs impl_1 -to_step route_design -jobs 2",
            "launch_runs impl_1 -to_step write_bitstream -jobs 2"))
        with self.assertRaisesRegex(g.RouteRejected, "forbidden|only route_design"):
            g.source_gate(self.root)

    def test_route_rejects_parent_enabled_hpm_master(self):
        p = self.root / d3a.CANDIDATE_TCL
        p.write_text(p.read_text().replace("CONFIG.PSU__USE__M_AXI_GP0 0",
                                           "CONFIG.PSU__USE__M_AXI_GP0 1"))
        with self.assertRaisesRegex(g.RouteRejected, "passive source gate rejected"):
            g.source_gate(self.root)

    def test_route_rejects_removed_a12_assurance(self):
        p = self.root / "scripts/m08_d3_2_passive_route_only.tcl"
        p.write_text(p.read_text().replace(
            "get_property PACKAGE_PIN [get_ports M08_FAN_PWM]",
            "get_property PACKAGE_PIN [get_ports M08_BAD_FAN]"))
        with self.assertRaisesRegex(g.RouteRejected, "missing safety"):
            g.source_gate(self.root)

    def fixture(self):
        (self.out / "d3a_project").mkdir()
        old = dict(d3a.KNOWN_NATIVE)
        old.update({
            "vivado_version": "2025.2",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "ps_pl0_nominal_request_mhz": "100",
            "ps_pl0_native_frequency_hz": "99999001",
        })
        (self.out / "10_d3a_passive_bd_readback.txt").write_text(
            "".join(f"{k}={v}\n" for k, v in old.items()))
        (self.out / "12_d3a_fan_a12.xdc").write_text(
            "\n".join(d3a.EXPECTED_XDC) + "\n")
        (self.out / "11_d3a_passive_bd_export.tcl").write_text(
            "create_bd_design m08_d3a_passive_fan\n" * 3)
        st = dict(synth.KNOWN)
        st.update({
            "vivado_version": "2025.2",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "synth_run_status": "synth_design Complete!",
        })
        (self.out / "20_passive_synth_readback.txt").write_text(
            "".join(f"{k}={v}\n" for k, v in st.items()))
        (self.out / "21_passive_synth_utilization.rpt").write_text(
            "synthetic utilization report\n")
        (self.out / "22_passive_synth_timing.rpt").write_text(
            "synthetic timing report\n")
        obj = dict(g.EXPECT)
        obj.update({
            "vivado_version": "2025.2",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "route_run_status": "route_design Complete!",
        })
        (self.out / "40_passive_route_readback.txt").write_text(
            "".join(f"{k}={v}\n" for k, v in obj.items()))
        for n, key in (("41_passive_route_timing.rpt", "timing"),
                       ("42_passive_route_drc.rpt", "drc"),
                       ("43_passive_route_utilization.rpt", "utilization"),
                       ("44_passive_route_clocks.rpt", "clock")):
            (self.out / n).write_text("synthetic " + key + " report\n")
        return self.run

    def test_synthetic_route_report_never_proves_drc_or_physical_safety(self):
        record = g.audit_native(self.fixture())
        self.assertTrue(record["genuine_route_reported_complete"])
        self.assertFalse(record["drc_violations_independently_cleared"])
        self.assertFalse(record["routed_timing_independently_accepted"])
        self.assertFalse(record["cooling_and_boot_rollback_proven"])
        self.assertFalse(record["hardware_mmio_authorized"])

    def test_reject_forged_bitstream_or_failed_route(self):
        self.fixture()
        report = self.out / "40_passive_route_readback.txt"
        report.write_text(report.read_text().replace(
            "bitstream=NOT_GENERATED", "bitstream=GENERATED"))
        with self.assertRaisesRegex(g.RouteRejected, "bitstream"):
            g.audit_native(self.run)
        report.write_text(report.read_text().replace(
            "bitstream=GENERATED", "bitstream=NOT_GENERATED").replace(
            "route_design Complete!", "route_design Failed!"))
        with self.assertRaisesRegex(g.RouteRejected, "not recorded complete"):
            g.audit_native(self.run)

    def test_reject_symlink_or_missing_timing_report(self):
        self.fixture()
        report = self.out / "41_passive_route_timing.rpt"
        moved = self.out / "saved.rpt"
        report.rename(moved)
        report.symlink_to(moved)
        with self.assertRaisesRegex(g.RouteRejected, "linked"):
            g.audit_native(self.run)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("tclsh"),
                         "bash/tclsh unavailable")
    def test_shell_and_tcl_parse_without_vivado_or_board(self):
        checked = subprocess.run(["bash", "-n", str(RUNNER)],
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        text = ("set f [open {" + str(TCL) + "} r]\n"
                "set c [read $f]\nclose $f\nputs [info complete $c]\n")
        result = subprocess.run(["tclsh"], input=text, capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "1")


if __name__ == "__main__":
    unittest.main()
