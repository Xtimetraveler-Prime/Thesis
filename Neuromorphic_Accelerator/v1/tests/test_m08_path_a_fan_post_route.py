"""M08.2b Path A fan+dual AXI genuine native route SOURCE/ARTIFACT tests.

All report fixtures in this file are ARTIFICIAL. They MUST NOT be described as
native Vivado, physical FPGA timing, real fan continuity or Linux PS AXI.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT / "scripts/m08_path_a_fan_post_route.tcl"
SH = ROOT / "scripts/run_m08_path_a_fan_post_route.sh"
AUDIT = ROOT / "scripts/m08_path_a_fan_post_route_audit.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("m08_path_a_fan_post_route_audit", AUDIT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_fake(folder: Path) -> None:
    expected = "".join(
        f"{sha256((ROOT / name).read_bytes()).hexdigest()}  {name}\n"
        for name in mod.SOURCES
    )
    (folder / "00_source_sha256_before.txt").write_text(expected)
    (folder / "04_source_sha256_after.txt").write_text(expected)
    (folder / "03_route_status.txt").write_text("vivado_exit_status=0\n")
    (folder / "01_vivado_fan_route.log").write_text(
        "# ARTIFICIAL TEST, NOT NATIVE VIVADO\n" + "\n".join(mod.MARKERS) + "\n"
    )
    addresses = (
        "APERTURE_IDENTITY|/ps/Data/SEG_identity_reg0|0x00A0000000|0x0000001000\n"
        "APERTURE_PAGE|/ps/Data/SEG_page_reg0|0x00A0001000|0x0000001000\n"
    )
    (folder / "02_vivado_page_bd_readback.txt").write_text(
        "META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD\n"
        "META|compute_enabled|NO\nMETA|validated_bd|YES\n"
        "META|physical_kv260|NOT_PROGRAMMED\n" + addresses
    )
    (folder / "20_m08_fan_bd_readback.txt").write_text(
        "fan_source=ps/emio_ttc0_wave_o[2]\nfan_pin=A12\n"
        "fan_iostandard=LVCMOS33\nfan_output_width=1\n"
        "fan_ttc0_enable=1\nfan_ttc0_io=EMIO\n"
        "validated_bd=YES\nboard_programmed=NO\n"
        "physical_fan_pwm_verified=NO\n" + addresses
    )
    (folder / "21_m08_fan_pwm_a12.xdc").write_text(
        "\n".join(
            ("# FAKE XDC, NOT NATIVE VIVADO",)
            + mod.EXPECTED_FAN_XDC if hasattr(mod, "EXPECTED_FAN_XDC")
            else ("# FAKE XDC", "set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]",
                  "set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]",
                  "set_property SLEW SLOW [get_ports {M08_FAN_PWM}]",
                  "set_property DRIVE 4 [get_ports {M08_FAN_PWM}]")
        ) + "\n"
    )
    (folder / "22_m08_fan_bd_export.tcl").write_text(
        "# FAKE BD Tcl, NOT native Vivado\n"
        "emio_ttc0_wave_o m08_ttc0_fan_slice M08_FAN_PWM\n"
    )
    (folder / "03_page_bd_export.tcl").write_text("# FAKE baseline Tcl\n")
    metrics = (
        ("scope", "M08_PATH_A_NATIVE_K26_FAN_AND_DUAL_AXI_POST_ROUTE"),
        ("part", "xck26-sfvc784-2LV-c"), ("vivado_version", "2025.2"),
        ("synthesis_status", "synth_design Complete!"),
        ("implementation_status", "route_design Complete!"),
        ("synthesis_progress", "100%"), ("implementation_progress", "100%"),
        ("wns_ns", "5.123"), ("whs_ns", "0.045"),
        ("clock_count", "4"), ("fan_port", "M08_FAN_PWM"),
        ("fan_pin", "A12"), ("fan_iostandard", "LVCMOS33"),
        ("fan_direction", "OUT"), ("fan_slew", "SLOW"), ("fan_drive", "4"),
        ("no_bitstream", "YES"), ("no_board_programming", "YES"),
        ("compute_enabled", "NO"),
        ("physical_fan_continuity", "NOT_VERIFIED"),
        ("linux_overlay", "NOT_INSTALLED"), ("ps_axi", "NOT_ACCESSED"),
        ("physical_ddr", "NOT_ACCESSED"),
    )
    assert {k for k, _ in metrics} == set(mod.METRIC_KEYS)
    (folder / "40_fan_route_metrics.txt").write_text(
        "".join(f"META|{k}|{v}\n" for k, v in metrics)
    )
    for name in mod.NATIVE[7:14]:
        (folder / name).write_text("# ARTIFICIAL TEST REPORT, NOT VIVADO\n" + "#" * 128)
    (folder / mod.NATIVE[14]).write_bytes(b"ARTIFICIAL DCP NOT VIVADO\n" * 100)


class TestM08PathAFanRoute(unittest.TestCase):
    def test_source_orders_genuine_fan_bd_wrapper_route_reports_and_no_board(self):
        t = TCL.read_text()
        sh = SH.read_text()
        active = "\n".join(x for x in t.splitlines()
                           if x.strip() and not x.lstrip().startswith("#"))
        for needed in (
            "source $candidate", "m08_path_a_fan_bd_candidate.tcl",
            "21_m08_fan_pwm_a12.xdc", "get_files -quiet $fan_xdc",
            "generate_target all $bd", "make_wrapper -files $bd -top",
            "set_property top m08_page_ps_wrapper", "update_compile_order",
            "launch_runs impl_1 -to_step route_design -jobs $jobs",
            "wait_on_run impl_1", "open_run impl_1",
            "get_ports -quiet M08_FAN_PWM", "get_property PACKAGE_PIN $pwm",
            "get_property IOSTANDARD $pwm", "get_property DIRECTION $pwm",
            "get_property SLEW $pwm", "get_property DRIVE $pwm",
            "report_timing_summary", "report_utilization", "report_drc",
            "report_methodology", "report_clock_utilization",
            "report_io -file", "report_route_status -file",
            "write_checkpoint $checkpoint",
            "get_timing_paths -quiet -delay_type max",
            "get_timing_paths -quiet -delay_type min",
            "M08_PATH_A_FAN_ROUTE_REPORTS_GENERATED_DRC_UNREVIEWED_NO_BITSTREAM_NO_BOARD",
        ):
            self.assertIn(needed, active)
        self.assertLess(active.index("source $candidate"),
                        active.index("generate_target all $bd"))
        self.assertLess(active.index("make_wrapper -files $bd -top"),
                        active.index("launch_runs impl_1 -to_step route_design"))
        self.assertLess(active.index("wait_on_run impl_1"),
                        active.index("open_run impl_1"))
        self.assertLess(active.index("open_run impl_1"),
                        active.index("report_timing_summary"))
        for forbidden in (
            "write_bitstream ", "program_hw_devices ", "connect_hw_server ",
            "write_cfgmem ", "xmutil unloadapp", "xmutil loadapp",
            "bootgen ", "devmem ", "/dev/mem", "fpgautil ",
        ):
            self.assertNotIn(forbidden, active)
        self.assertIn("mktemp -d", sh)
        self.assertIn("M08_FAN_ROUTE_JOBS:-4", sh)
        self.assertIn("52_evidence_sha256.txt", sh)
        self.assertIn("49_independent_fan_route_audit.json", sh)
        self.assertIn("50_audit_console.log", sh)
        self.assertIn("AUDIT_NOT_RUN", sh)
        self.assertNotIn("program_hw_devices ", "\n".join(
            x for x in sh.splitlines() if not x.lstrip().startswith("#")
        ))
        for file in mod.SOURCES:
            self.assertIn(file, sh)
        for file in mod.NATIVE:
            self.assertIn(file, sh)
        self.assertIn("drc_signoff", AUDIT.read_text())
        self.assertIn("unconstrained_path_signoff", AUDIT.read_text())

    @unittest.skipUnless(shutil.which("bash"), "bash not installed")
    def test_runner_bash_grammar(self):
        p = subprocess.run(["bash", "-n", str(SH)], text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)

    @unittest.skipUnless(shutil.which("tclsh"), "Tcl not installed")
    def test_candidate_Tcl_grammar(self):
        cmd = (f"set f [open {{{TCL}}} r]\n"
               "set code [read $f]\nclose $f\n"
               'if {![info complete $code]} {error "incomplete Tcl"}\n'
               'puts "M08_PATH_A_ROUTE_TCL_PARSE_ONLY"\n')
        p = subprocess.run(["tclsh"], input=cmd, capture_output=True,
                           text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assertIn("M08_PATH_A_ROUTE_TCL_PARSE_ONLY", p.stdout)

    def test_artificial_good_fixture_only_claims_offline_source_audit(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            make_fake(folder)
            r = mod.independent_audit(folder, ROOT)
            self.assertTrue(r["native_vivado_routed"])
            self.assertFalse(r["bitstream_generated"])
            self.assertFalse(r["board_programmed"])
            self.assertFalse(r["fan_continuity_verified"])
            self.assertFalse(r["ps_axi_readback_verified"])
            self.assertEqual(r["post_route_slack_ns"]["whs_ns"], .045)

    def test_artificial_mutation_rejected(self):
        mutations = (
            ("40_fan_route_metrics.txt", "META|wns_ns|5.123", "META|wns_ns|-0.02"),
            ("40_fan_route_metrics.txt", "META|whs_ns|0.045", "META|whs_ns|-0.01"),
            ("40_fan_route_metrics.txt", "META|fan_pin|A12", "META|fan_pin|A13"),
            ("40_fan_route_metrics.txt", "META|no_bitstream|YES", "META|no_bitstream|NO"),
            ("40_fan_route_metrics.txt", "META|clock_count|4", "META|clock_count|0"),
            ("40_fan_route_metrics.txt", "META|compute_enabled|NO", "META|compute_enabled|YES"),
            ("21_m08_fan_pwm_a12.xdc", "PACKAGE_PIN A12", "PACKAGE_PIN B12"),
            ("20_m08_fan_bd_readback.txt", "fan_output_width=1", "fan_output_width=3"),
            ("02_vivado_page_bd_readback.txt", "0x00A0001000", "0x00A0002000"),
            ("01_vivado_fan_route.log",
             "M08_PATH_A_FAN_NATIVE_SYNTH_AND_ROUTE_COMPLETE=1",
             "M08_PATH_A_FAN_NATIVE_SYNTH_ROUTE_NOT_DONE"),
            ("04_source_sha256_after.txt", "  scripts/", "  changed/scripts/"),
        )
        for name, old, new in mutations:
            with self.subTest(file=name, mutation=old), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                make_fake(folder)
                p = folder / name
                text = p.read_text()
                self.assertIn(old, text)
                p.write_text(text.replace(old, new, 1))
                with self.assertRaises(ValueError):
                    mod.independent_audit(folder, ROOT)

    @unittest.skipUnless(shutil.which("bash"), "bash not installed")
    def test_missing_vivado_prevents_any_vendor_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["M08_EVIDENCE_BASE"] = td
            env["M08_FAN_ROUTE_JOBS"] = "0"
            p = subprocess.run(["bash", str(SH)], env=env, capture_output=True,
                               text=True, timeout=10)
            self.assertEqual(p.returncode, 2)
            self.assertIn("must be an integer 1..8", p.stderr)
            self.assertFalse(list(Path(td).iterdir()))


if __name__ == "__main__":
    unittest.main()
