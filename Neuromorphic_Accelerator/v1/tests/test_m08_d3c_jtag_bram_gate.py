"""M08 D3C: JTAG AXI -> BRAM offline design source/native negative tests."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
from pathlib import Path
import tempfile
import unittest
import subprocess
import re
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "test_m08_d3c_gate", ROOT / "scripts/m08_d3c_jtag_bram_gate.py")
assert SPEC and SPEC.loader
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)


class D3CJtagBramTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        (self.root / "M08").mkdir()
        self.run = self.root / "M08" / "m08_d3c_jtag_link_TEST001"
        self.run.mkdir()
        self.candidate = self.run / g.BIT_REL
        self.make_mock_native()

    def make_mock_native(self):
        report = {
            "schema": "m08-d3c-jtag-bram-offline-build-v1",
            "vivado_version": "2025.2",
            "part": "xck26-sfvc784-2LV-c",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "ps_to_pl_hpm": "DISABLED",
            "jtag_axi": "ENABLED_PL",
            "ps_pl0_clock_request_hz": "100000000",
            "ps_pl0_runtime_clock_proven": "NO",
            "bram_map_base": "0xA0000000",
            "bram_map_range": "0x00001000",
            "test_window_bytes": "4096",
            "fan_route": "TTC0_WAVEOUT2_TO_A12",
            "linux_management_compatibility": "NOT_PROVEN",
            "hardware_bitstream_programmed": "NO",
            "hardware_jtag_axil_readback_proven": "NO",
            "hardware_neural_execution_proven": "NO",
            "bitstream_size_bytes": "131072",
        }
        self.report = report
        values = {
            "00_vivado.log": b"M08_D3C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED\n",
            "01_vivado.jou": b"source test\n",
            "02_vivado_exit.txt": b"vivado_build_exit=0\n",
            "reports/10_fan_a12.xdc": b"set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]\n",
            "reports/20_route_drc.rpt": b"DRC Checks found: 0\n",
            "reports/21_route_timing.rpt": b"timing report\n",
            "reports/22_route_utilization.rpt": b"utilization\n",
            "reports/23_route_clocks.rpt": b"clock report\n",
            "reports/30_native_result.txt": (
                "\n".join(k+"="+v for k, v in report.items())+"\n").encode(),
            g.BIT_REL: b"\x01\x02\x03\x04" * 32768,
        }
        for name, data in values.items():
            output = self.run / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
        self.refresh_ledger()

    def refresh_ledger(self):
        self.run.joinpath("99_evidence_sha256.txt").write_text(
            "".join(sha256((self.run/name).read_bytes()).hexdigest()+"  "+name+"\n"
                    for name in g.EXPECTED))

    def test_vivado_version_banner_gate_matches_real_2025_2_and_rejects_other_versions(self):
        # Vivado 2025.2 on Linux prints lowercase "vivado", not "Vivado".
        # Test both scripts without invoking native Vivado or accessing JTAG.
        good = ("vivado v2025.2 (64-bit)", "Vivado v2025.2 (64-bit)")
        bad = ("vivado v2025.1 (64-bit)", "vivado v2025.20 (64-bit)",
               "vivado v2026.1 (64-bit)", "not-vivado v2025.2 (64-bit)")
        scripts = ("run_m08_d3c_jtag_bram_pc.sh",
                   "run_m08_d3c_jtag_bram_physical_once.sh")
        for script in scripts:
            body = (ROOT / "scripts" / script).read_text()
            patterns = re.findall(r"grep -Eq '([^']+)'", body)
            self.assertEqual(len(patterns), 1, script)
            for banner in good:
                with self.subTest(script=script, banner=banner, expected="accept"):
                    result = subprocess.run(("grep", "-Eq", patterns[0]),
                                            input=banner + "\n", text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
            for banner in bad:
                with self.subTest(script=script, banner=banner, expected="reject"):
                    result = subprocess.run(("grep", "-Eq", patterns[0]),
                                            input=banner + "\n", text=True, capture_output=True)
                    self.assertEqual(result.returncode, 1, result.stderr)

    def test_actual_tcl_preflight_accepts_vivado_log_journal_and_rejects_extra(self):
        # Tclsh executes exactly the startup contract with a stub for Vivado's
        # version command. This never compiles an FPGA design or accesses hardware.
        if not shutil.which("tclsh"):
            self.skipTest("tclsh not installed")
        builder = (ROOT / "scripts/m08_d3c_jtag_bram_build.tcl").read_text()
        prefix, separator, _ = builder.partition("set part xck26-sfvc784-2LV-c")
        self.assertTrue(separator, "missing protected native preflight boundary")
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            run = home / "Thesis_Evidence" / "M08" / "m08_d3c_jtag_link_TEST01"
            run.mkdir(parents=True)
            (run / "00_vivado.log").write_text("Vivado begins logging before Tcl\n")
            (run / "01_vivado.jou").write_text("journal\n")
            harness = home / "preflight_only.tcl"
            harness.write_text(
                "proc version {args} { return 2025.2 }\n"
                + prefix + "\nputs PREFLIGHT_PASSED\n")
            env = os.environ.copy()
            env["HOME"] = str(home)
            def check(*args):
                return subprocess.run(("tclsh", str(harness), *args),
                                      env=env, text=True, capture_output=True)
            ok = check(str(run))
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("PREFLIGHT_PASSED", ok.stdout)
            extra_arg = check(str(run), "unexpected-extra-argv")
            self.assertNotEqual(extra_arg.returncode, 0)
            self.assertIn("usage:", extra_arg.stderr)
            (run / "unexpected-file.txt").write_text("must reject\n")
            unsafe = check(str(run))
            self.assertNotEqual(unsafe.returncode, 0)
            self.assertIn("unexpected/unsafe content", unsafe.stderr)

    def test_native_launch_flags_before_tclargs(self):
        runner = (ROOT / "scripts/run_m08_d3c_jtag_bram_pc.sh").read_text()
        args = runner.index('-tclargs "$RUN"')
        self.assertLess(runner.index('-log "$RUN/00_vivado.log"'), args)
        self.assertLess(runner.index('-journal "$RUN/01_vivado.jou"'), args)
        self.assertLess(runner.index('-source "$ROOT/scripts/m08_d3c_jtag_bram_build.tcl"'), args)
        self.assertEqual(runner.count('-tclargs "$RUN"'), 1)
        self.assertEqual(g.source()["status"],
                         "M08_D3C_JTAG_BRAM_PC_SOURCE_ACCEPTED_NOT_BUILT")

    def test_source_parent_contract_and_source_no_board(self):
        result = g.source()
        self.assertEqual(result["status"],
                         "M08_D3C_JTAG_BRAM_PC_SOURCE_ACCEPTED_NOT_BUILT")
        self.assertFalse(result["hardware_programmed"])
        self.assertFalse(result["pl_clock_independence_proven"])

    def test_synthetic_native_accepted_but_no_hardware(self):
        result = g.native(self.run)
        self.assertEqual(result["status"],
                         "M08_D3C_NATIVE_OFFLINE_JTAG_BRAM_IMAGE_HASH_ACCEPTED_NO_BOARD")
        self.assertFalse(result["readback_proven"])
        self.assertEqual(result["jtag_axi_bram_base"], "0xA0000000")
        self.assertEqual(result["candidate_bytes"], 131072)

    def test_tampered_bit_without_receipt_rejected(self):
        self.candidate.write_bytes(self.candidate.read_bytes()[:-4] + b"FAIL")
        with self.assertRaisesRegex(g.Reject, "hash differs"):
            g.native(self.run)

    def test_tampered_report_with_rehashed_receipt_rejected(self):
        p = self.run/"reports/30_native_result.txt"
        p.write_text(p.read_text().replace("ps_to_pl_hpm=DISABLED",
                                          "ps_to_pl_hpm=ENABLED"))
        self.refresh_ledger()
        with self.assertRaisesRegex(g.Reject, "native field: ps_to_pl_hpm"):
            g.native(self.run)

    def test_existing_original_passive_sha_always_different(self):
        self.assertNotEqual(g.OLD_FAILED, g.PREV_PASSIVE)
        self.assertEqual(g.PREV_PASSIVE,
                         "07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547")

    def test_bad_native_file_order_rejected(self):
        ledger = self.run/"99_evidence_sha256.txt"
        lines = ledger.read_text().splitlines()
        ledger.write_text("\n".join(lines[::-1])+"\n")
        with self.assertRaisesRegex(g.Reject, "receipt file mismatch"):
            g.native(self.run)

    def test_old_status_not_released(self):
        p = self.run/"reports/30_native_result.txt"
        p.write_text(p.read_text().replace("hardware_bitstream_programmed=NO",
                                          "hardware_bitstream_programmed=YES"))
        self.refresh_ledger()
        with self.assertRaisesRegex(g.Reject, "hardware_bitstream_programmed"):
            g.native(self.run)

    def test_nonzero_drc_refused_even_with_valid_receipt(self):
        p = self.run/"reports/20_route_drc.rpt"
        p.write_text("DRC Checks found: 2\n")
        self.refresh_ledger()
        with self.assertRaisesRegex(g.Reject, "native DRC"):
            g.native(self.run)

    def test_error_log_refused_even_with_valid_receipt(self):
        p = self.run/"00_vivado.log"
        p.write_text(p.read_text()+"ERROR: invalid PS clock\n")
        self.refresh_ledger()
        with self.assertRaisesRegex(g.Reject, "Vivado logs report"):
            g.native(self.run)

    def test_native_log_diagnostic_prints_exact_line_but_never_accepts(self):
        # Earlier critical warnings must block acceptance even if bitgen later
        # prints zero warnings. Report a log line without modifying original data.
        p = self.run / "00_vivado.log"
        p.write_text(
            "INFO: opening Vivado 2025.2\\n"
            "CRITICAL WARNING: [BD 41-999] synthetic test-only clock issue\\n"
            "8 Infos, 0 Warnings, 0 Critical Warnings and 0 Errors encountered.\\n"
            "M08_D3C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED\\n"
        )
        self.refresh_ledger()
        with self.assertRaisesRegex(g.Reject, r"00_vivado\\.log:2: CRITICAL WARNING"):
            g.native(self.run)

    def test_native_log_error_line_still_rejected_with_location(self):
        p = self.run / "00_vivado.log"
        p.write_text(
            "M08_D3C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED\\n"
            "ERROR: [Common 17-999] synthetic test-only implementation error\\n"
        )
        self.refresh_ledger()
        with self.assertRaisesRegex(g.Reject, r"00_vivado\\.log:2: ERROR:"):
            g.native(self.run)

    def test_nonzero_vivado_exit_rejected(self):
        p = self.run/"02_vivado_exit.txt"
        p.write_text("vivado_build_exit=1\n")
        self.refresh_ledger()
        with self.assertRaisesRegex(g.Reject, "nonzero exit"):
            g.native(self.run)

    def test_source_mutation_rejected(self):
        source = ROOT/"scripts/m08_d3c_jtag_bram_build.tcl"
        runner = ROOT/"scripts/run_m08_d3c_jtag_bram_pc.sh"
        (self.root/"scripts").mkdir()
        (self.root/"scripts/m08_d3c_jtag_bram_build.tcl").write_text(
            source.read_text()+"\nprogram_hw_devices $fpga\n")
        (self.root/"scripts/run_m08_d3c_jtag_bram_pc.sh").write_text(runner.read_text())
        with self.assertRaisesRegex(g.Reject, "forbidden action"):
            g.source(self.root)

    def test_script_readback_is_separate_and_exactly_one_program_call(self):
        script = (ROOT/"scripts/m08_d3c_jtag_bram_readback_once.tcl").read_text()
        active = [line.strip() for line in script.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(sum(line.startswith("program_hw_devices ") for line in active), 1)
        self.assertIn("reset_hw_axi $axi", script)
        self.assertIn("M08_D3C_FOUR_WORDS_READBACK_PASS_PC_RECEIPT", script)
        self.assertIn("M08_D3C_EXPECTED_SHA", script)
        self.assertIn("M08_D3C_ALLOW_PROGRAM", script)
        self.assertIn("A0000000", script)
        for forbidden in ("xmutil loadapp", "xmutil unloadapp", "/dev/mem",
                          "M_AXI_HPM0_FPD", "write_cfgmem"):
            self.assertNotIn(forbidden, "\n".join(active))

    def test_script_jtag_exact_32bit_pattern(self):
        script = (ROOT/"scripts/m08_d3c_jtag_bram_readback_once.tcl").read_text()
        self.assertIn("set values {A5A55A5A 12345678 DEADBEEF 0BADF00D}", script)
        self.assertIn("set i 0} {$i < 4} {incr i}", script)
        self.assertIn("get_property DATA $rt", script)

    def test_bad_native_run_folder_rejected(self):
        with self.assertRaisesRegex(g.Reject, "dedicated M08 D3C"):
            g.native(self.root)


if __name__ == "__main__":
    unittest.main()
