"""M08.2b Path A fan-preserving K26 BD: source, mock and negative audit.

CI has no Vivado 2025.2 or physical KV260. All fabricated vendor artifacts
in these tests are SYNTHETIC, never accepted as hardware evidence.
"""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT / "scripts/m08_path_a_fan_bd_candidate.tcl"
RUN = ROOT / "scripts/run_m08_path_a_fan_bd.sh"
AUDIT = ROOT / "scripts/m08_path_a_fan_bd_audit.py"

_spec = importlib.util.spec_from_file_location("m08_path_a_fan_bd_audit", AUDIT)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


class M08PathAFanBD(unittest.TestCase):
    def test_source_extends_existing_M08_without_physical_side_effects(self):
        text = TCL.read_text()
        executable = "\n".join(
            line for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        for expected in (
            "source $baseline", "validate_bd_design -force",
            "ps/emio_ttc0_wave_o", "CONFIG.PSU__TTC0__WAVEOUT__ENABLE",
            "CONFIG.PSU__TTC0__WAVEOUT__IO",
            "CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2",
            "CONFIG.DIN_WIDTH 3", "M08_FAN_PWM",
            "PACKAGE_PIN A12", "IOSTANDARD LVCMOS33",
            "M08_PATH_A_K26_FAN_BD_OFFLINE_VALIDATED_NO_BOARD_NO_BITSTREAM",
            "02_vivado_page_bd_readback.txt",
            "APERTURE_IDENTITY", "APERTURE_PAGE",
        ):
            self.assertIn(expected, executable)
        self.assertLess(executable.index("source $baseline"),
                        executable.index("CONFIG.PSU__TTC0__WAVEOUT__ENABLE"))
        for forbidden in (
            "program_hw_devices", "write_bitstream", "bootgen ",
            "write_cfgmem", "xmutil unloadapp", "xmutil loadapp",
            "mrd ", "mwr ", "/dev/mem", "devmem ", "flashcp ",
            "reset_hw_axi", "connect_hw_server", "run impl_1",
            "synth_design", "set_property PROBES.FILE",
        ):
            self.assertNotIn(forbidden, executable)
        wrapper = RUN.read_text()
        self.assertIn("mktemp -d", wrapper)
        self.assertIn("00_source_sha256_before.txt", wrapper)
        self.assertIn("04_source_sha256_after.txt", wrapper)
        self.assertIn("m08_path_a_fan_bd_audit.py", wrapper)
        self.assertIn("30_evidence_sha256.txt", wrapper)
        self.assertNotIn("program_hw_devices", "\n".join(
            line for line in wrapper.splitlines() if not line.lstrip().startswith("#")
        ))
        self.assertIn("active_firmware_metadata",
                      (ROOT / "scripts/m08_kv260_path_a_readonly.sh").read_text())

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_bash_syntax(self):
        p = subprocess.run(["bash", "-n", str(RUN)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    @unittest.skipUnless(shutil.which("tclsh"), "Tcl unavailable")
    def test_tcl_parses_without_vivado(self):
        command = (
            f"set f [open {{{TCL}}} r]\n"
            "set text [read $f]\n"
            "close $f\n"
            'if {![info complete $text]} {error "incomplete Tcl"}\n'
            'puts "M08_FAN_TCL_PARSE_ONLY_NO_HARDWARE"\n'
        )
        p = subprocess.run(["tclsh"], input=command, capture_output=True,
                           text=True, timeout=20)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assertIn("M08_FAN_TCL_PARSE_ONLY_NO_HARDWARE", p.stdout)

    def make_fixture(self, directory: Path) -> None:
        rows = [
            f"{_module.digest(ROOT / name)}  {name}"
            for name in _module.SOURCE_FILES
        ]
        manifest = "\n".join(rows) + "\n"
        for filename in ("00_source_sha256_before.txt",
                         "04_source_sha256_after.txt"):
            (directory / filename).write_text(manifest)
        (directory / "03_run_result.txt").write_text("vivado_exit_status=0\n")
        (directory / "01_vivado_fan_bd.log").write_text(
            "M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD\n"
            "M08_PATH_A_K26_FAN_BD_OFFLINE_VALIDATED_NO_BOARD_NO_BITSTREAM\n"
        )
        addresses = (
            "APERTURE_IDENTITY|/foo/id|0xA0000000|0x1000\n"
            "APERTURE_PAGE|/foo/page|0xA0001000|0x1000\n"
        )
        (directory / "02_vivado_page_bd_readback.txt").write_text(
            "META|validated_bd|YES\nMETA|compute_enabled|NO\n"
            "META|physical_kv260|NOT_PROGRAMMED\n" + addresses
        )
        (directory / "20_m08_fan_bd_readback.txt").write_text(
            "schema=m08-path-a-kv260-fan-bd-offline-v1\n"
            "fan_source=ps/emio_ttc0_wave_o[2]\n"
            "fan_route=ps/emio_ttc0_wave_o->m08_ttc0_fan_slice[2]->M08_FAN_PWM\n"
            "fan_pin=A12\nfan_iostandard=LVCMOS33\n"
            "fan_output_width=1\nfan_ttc0_enable=1\nfan_ttc0_io=EMIO\n"
            "original_compute_enabled=NO\n"
            "validated_bd=YES\nphysical_fan_pwm_verified=NO\nrouted=NO\n"
            "bitstream_generated=NO\nlinux_overlay_installed=NO\n"
            "board_programmed=NO\n" + addresses
        )
        (directory / "21_m08_fan_pwm_a12.xdc").write_text(
            "# fake XDC for pure auditor unit test\n"
            + "\n".join(_module.EXPECTED_FAN_XDC) + "\n"
        )
        (directory / "22_m08_fan_bd_export.tcl").write_text(
            "m08_ttc0_fan_slice M08_FAN_PWM emio_ttc0_wave_o\n"
        )
        (directory / "03_page_bd_export.tcl").write_text(
            "synthetic baseline, NOT Vivado\n"
        )

    def test_fabricated_fixture_auditor_status_is_offline_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_fixture(root)
            status = _module.audit(root, ROOT)
            self.assertEqual(
                status["status"],
                "ORIGINAL_VIVADO_FAN_BD_EVIDENCE_CONSISTENT_NOT_ROUTED_NOT_PROGRAMMED"
            )
            self.assertFalse(status["physical_board_programmed"])
            self.assertEqual(status["physical_fan_control"], "NOT_VERIFIED")
            self.assertFalse(status["bitstream_generated"])
            self.assertEqual(status["source_sha256_verified"],
                             len(_module.SOURCE_FILES))

    def test_auditor_rejects_tampered_fan_pin_axi_aperture_and_vendor_error(self):
        for filename, old, new in (
            ("21_m08_fan_pwm_a12.xdc", "PACKAGE_PIN A12", "PACKAGE_PIN B12"),
            ("02_vivado_page_bd_readback.txt", "0xA0001000", "0xA0002000"),
            ("20_m08_fan_bd_readback.txt",
             "fan_source=ps/emio_ttc0_wave_o[2]",
             "fan_source=ps/emio_ttc0_wave_o[1]"),
            ("20_m08_fan_bd_readback.txt", "fan_output_width=1",
             "fan_output_width=3"),
            ("01_vivado_fan_bd.log", "M08_PATH_A_K26_FAN_BD_OFFLINE",
             "ERROR: M08_PATH_A_K26_FAN_BD_OFFLINE"),
            ("04_source_sha256_after.txt", "  scripts/", "  changed/scripts/"),
        ):
            with self.subTest(filename=filename, old=old):
                with tempfile.TemporaryDirectory() as td:
                    d = Path(td)
                    self.make_fixture(d)
                    file = d / filename
                    content = file.read_text()
                    self.assertIn(old, content)
                    file.write_text(content.replace(old, new, 1))
                    with self.assertRaises(ValueError):
                        _module.audit(d, ROOT)


if __name__ == "__main__":
    unittest.main()
