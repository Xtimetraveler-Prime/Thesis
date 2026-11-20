"""M08 D3.D.1: genuine compute-oriented RTL tests, M02 oracle and offline gate.

All tests are PC/CI only; no Vivado, JTAG, PS, DDR or FPGA programming.
"""
from __future__ import annotations
from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "m08_d3d_neuron_gate_test_module", ROOT / "scripts/m08_d3d_neuron_gate.py")
assert SPEC and SPEC.loader
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)
import m08_d3d_neuron_vectors as vectors
import m08_d3d_neuron_physical_audit as physical_audit


class D3DNeuronTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        base = self.home / "M08"
        base.mkdir()
        self.run = base / "m08_d3d_neuron_TEST01"
        self.run.mkdir()
        self.mock_native()

    def refresh(self):
        (self.run / "99_evidence_sha256.txt").write_text(
            "".join(sha256((self.run / item).read_bytes()).hexdigest() +
                    "  " + item + "\n" for item in g.EXPECTED))

    def mock_native(self):
        data = {
            "schema": g.SCHEMA,
            "wrapper_top": "m08_d3d_lif_jtag_wrapper",
            "builder_sha256": sha256(g.BUILDER.read_bytes()).hexdigest(),
            "lif_rtl_sha256": sha256(g.LIF_RTL.read_bytes()).hexdigest(),
            "fabric_por_rtl_sha256": sha256(g.POR_RTL.read_bytes()).hexdigest(),
            "vivado_version": "2025.2",
            "part": "xck26-sfvc784-2LV-c",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "ps_to_pl_hpm": "DISABLED",
            "jtag_axi": "ENABLED_PL",
            "ps_pl0_clock_request_hz": "100000000",
            "ps_pl0_runtime_clock_proven": "NO",
            "bram_map_base": "0xA0000000",
            "bram_map_range": "0x00001000",
            "lif_base": "0xA0001000",
            "lif_map_range": "0x00001000",
            "neural_mode": "SINGLE_NEURON_FOUR_TICKS_SIGNED16",
            "decay_modes": "ZERO_HALF_ONE",
            "lif_requires_hardware_execution": "YES",
            "reset_mode": "FABRIC_POR_256_CYCLES",
            "ps_reset_dependency": "NO",
            "ps_clock_dependency": "YES",
            "bram_controller_derived_depth": "1024",
            "bram_depth_words": "1024",
            "bram_width_bits": "32",
            "fan_route": "TTC0_WAVEOUT2_TO_A12",
            "linux_management_compatibility": "NOT_PROVEN",
            "hardware_bitstream_programmed": "NO",
            "hardware_jtag_axil_readback_proven": "NO",
            "hardware_neural_execution_proven": "NO",
            "hardware_lif_readback_proven": "NO",
            "bitstream_size_bytes": "131072",
        }
        files = {
            "00_vivado.log": (
                b"M08_D3D_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d_lif_jtag_wrapper\n"
                b"M08_D3D_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED\n"),
            "01_vivado.jou": b"native journal\n",
            "02_vivado_exit.txt": b"vivado_build_exit=0\n",
            "reports/10_fan_a12.xdc": b"set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]\n",
            "reports/11_fabric_por.v": g.POR_RTL.read_bytes(),
            "reports/12_lif_axil.v": g.LIF_RTL.read_bytes(),
            "reports/20_route_drc.rpt": b"Checks found: 0\n",
            "reports/21_route_timing.rpt": (
                b"Design Timing Summary\n"
                b"WNS(ns) TNS(ns) TNS Failing Endpoints WHS(ns) THS(ns)\n"
                b"------- ------- ------- ------- -------\n"
                b"5.242 0.000 0 1000 0.010 0.000 0 900 1.222 0.000 0 100\n"
                b"All user specified timing constraints are met.\n"
                b"clk_pl_0 {0.000 5.000} 10.000 100.000\n"
            ),
            "reports/22_route_utilization.rpt": b"resource utilization\n",
            "reports/23_route_clocks.rpt": b"clock report\n",
            "reports/30_native_result.txt": (
                "\n".join(k + "=" + v for k, v in data.items()) + "\n").encode(),
            g.BIT_REL: b"\xA5\x5A\x3C\xC3" * 32768,
        }
        for name, value in files.items():
            out = self.run / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(value)
        self.refresh()

    def test_source_only_and_no_board_claims(self):
        result = g.source()
        self.assertEqual(result["status"], "M08_D3D_SOURCE_ACCEPTED_PC_ONLY_NOT_BUILT")
        self.assertFalse(result["hardware_neural_inference_proven"])
        self.assertFalse(result["hardware_programmed"])
        self.assertEqual(result["lif_rtl_sha256"],
                         sha256(g.LIF_RTL.read_bytes()).hexdigest())

    def test_synthetic_native_acceptance_remains_no_board(self):
        result = g.native(self.run)
        self.assertEqual(result["status"],
                         "M08_D3D_NATIVE_NEURON_IMAGE_ACCEPTED_OFFLINE_NO_BOARD")
        self.assertFalse(result["neural_execution_proven"])
        self.assertFalse(result["hardware_programmed"])
        self.assertEqual(result["neural_register_base"], "0xA0001000")
        self.assertEqual(result["transport_bram_base"], "0xA0000000")
        self.assertEqual(result["wns_ns"], 5.242)

    def test_native_top_wrapper_is_derived_and_checked_not_guessed(self):
        builder = g.BUILDER.read_text()
        self.assertIn("set wrapper_path [lindex $wrapper 0]", builder)
        self.assertIn("set wrapper_top [file rootname [file tail $wrapper_path]]", builder)
        self.assertIn('if {$wrapper_top ne "m08_d3d_lif_jtag_wrapper"}', builder)
        self.assertIn("set_property top $wrapper_top [current_fileset]", builder)
        self.assertIn("set resolved_top [get_property top [current_fileset]]", builder)
        self.assertIn("M08_D3D_NATIVE_TOP_WRAPPER_VALIDATED|$wrapper_top", builder)
        self.assertNotIn("set_property top m08_d3d_neuron_wrapper", builder)

    def test_source_gate_rejects_historical_wrong_top_and_missing_assertion(self):
        original = g.BUILDER.read_text()
        mutations = (
            ("set_property top $wrapper_top [current_fileset]",
             "set_property top m08_d3d_neuron_wrapper [current_fileset]"),
            ('if {$wrapper_top ne "m08_d3d_lif_jtag_wrapper"}',
             'if {$wrapper_top ne "m08_d3d_neuron_wrapper"}'),
            ("set resolved_top [get_property top [current_fileset]]",
             "set resolved_top $wrapper_top"),
        )
        for old, new in mutations:
            with self.subTest(mutation=old):
                self.assertIn(old, original)
                mutated = self.home / "bad_neural_builder.tcl"
                mutated.write_text(original.replace(old, new))
                with patch.object(g, "BUILDER", mutated):
                    with self.assertRaisesRegex(g.Reject,
                                                "wrapper top|top setting|wrong Vivado top"):
                        g.source()

    def test_native_gate_rejects_missing_wrapper_proof_after_rehash(self):
        path = self.run / "00_vivado.log"
        path.write_text(path.read_text().replace(
            "M08_D3D_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d_lif_jtag_wrapper",
            "M08_D3D_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d_neuron_wrapper"))
        self.refresh()
        with self.assertRaisesRegex(g.Reject, "no native proof generated top"):
            g.native(self.run)

    def test_native_gate_rejects_actual_vivado_filemgmt_critical_after_rehash(self):
        path = self.run / "00_vivado.log"
        path.write_text(path.read_text() +
            'CRITICAL WARNING: [filemgmt 20-742] The top module '
            '"m08_d3d_neuron_wrapper" specified for this project can not '
            'be validated.\n')
        self.refresh()
        with self.assertRaisesRegex(g.Reject, "native fatal diagnostics"):
            g.native(self.run)

    def test_native_rejects_wrong_image_schema_even_with_valid_rehash(self):
        path = self.run / "reports/30_native_result.txt"
        path.write_text(path.read_text().replace(
            g.SCHEMA, "m08-d3c-jtag-bram-offline-build-v2-fabric-por"))
        self.refresh()
        with self.assertRaisesRegex(g.Reject, "schema"):
            g.native(self.run)

    def test_native_rejects_fabric_source_change_even_with_valid_rehash(self):
        path = self.run / "reports/12_lif_axil.v"
        path.write_bytes(path.read_bytes() + b"\n// changed design\n")
        self.refresh()
        with self.assertRaisesRegex(g.Reject, "native evidence RTL differs"):
            g.native(self.run)

    def test_native_rejects_tampered_bit_without_rehash(self):
        path = self.run / g.BIT_REL
        path.write_bytes(path.read_bytes()[:-1] + b"X")
        with self.assertRaisesRegex(g.Reject, "SHA mismatch"):
            g.native(self.run)

    def test_native_rejects_ps_master_or_false_physical_claim(self):
        path = self.run / "reports/30_native_result.txt"
        for needle, new in (
            ("ps_to_pl_hpm=DISABLED", "ps_to_pl_hpm=ENABLED"),
            ("hardware_neural_execution_proven=NO",
             "hardware_neural_execution_proven=YES"),
            ("ps_clock_dependency=YES", "ps_clock_dependency=NO"),
            ("lif_base=0xA0001000", "lif_base=0xA0000000"),
        ):
            with self.subTest(needle=needle):
                self.mock_native()
                path.write_text(path.read_text().replace(needle, new))
                self.refresh()
                with self.assertRaises(g.Reject):
                    g.native(self.run)

    def test_native_rejects_fatal_log_or_negative_timing_with_rehash(self):
        for name, original, changed in (
            ("00_vivado.log", "M08_D3D_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED",
             "CRITICAL WARNING: [BD 41-737] demo\n"
             "M08_D3D_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED"),
            ("reports/21_route_timing.rpt", "5.242 0.000 0", "-0.100 0.200 2"),
        ):
            with self.subTest(path=name):
                self.mock_native()
                path = self.run / name
                path.write_text(path.read_text().replace(original, changed))
                self.refresh()
                with self.assertRaises(g.Reject):
                    g.native(self.run)

    def test_expected_goldens_from_two_real_m02_reference_engines(self):
        expected = (
            ((2, -2, -4, -1), 2),
            ((-5, -32768, -32768, -32768), 1),
            ((3, 0, -3, 0), 2),
            ((-1, -1, -1, -1), 0),
        )
        self.assertEqual(tuple(vectors.expected(f) for f in vectors.FIXTURES),
                         expected)
        for fixture in vectors.FIXTURES:
            line = vectors.format_fixture(fixture)
            self.assertEqual(len(line.split("|")), 16)
            self.assertEqual(line.split("|")[1], vectors.u32(fixture.nonce))

    def test_vector_generator_never_overwrites_existing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "golden.txt"
            runner = [sys.executable,
                      str(ROOT / "scripts/m08_d3d_neuron_vectors.py"),
                      "--out", str(output)]
            first = subprocess.run(runner, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(len(output.read_text().splitlines()), 6)
            second = subprocess.run(runner, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)

    def test_lif_module_top_is_verilog2001_for_vivado_ip_integrator(self):
        # AMD UG994: an SV top is not valid as an IPI module reference.
        self.assertEqual(g.LIF_RTL.suffix, ".v")
        self.assertFalse((ROOT / "rtl/m08/m08_d3d_lif_axil.sv").exists())
        builder = g.BUILDER.read_text()
        self.assertIn("m08 m08_d3d_lif_axil.v", builder)
        self.assertIn("reports 12_lif_axil.v", builder)
        self.assertTrue((ROOT / "rtl/m08/tb_m08_d3d_lif_axil.sv").is_file())
        if not shutil.which("iverilog"):
            self.skipTest("Icarus not installed")
        result = subprocess.run(["iverilog", "-g2005", "-t", "null",
                                 str(g.LIF_RTL)],
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_rtl_four_fixture_axil_protocol_and_m02(self):
        if not shutil.which("iverilog") or not shutil.which("vvp"):
            self.skipTest("Icarus RTL simulation not installed")
        with tempfile.TemporaryDirectory() as tmp:
            executable = str(Path(tmp) / "d3d_neuron_tb")
            compile_cmd = [
                "iverilog", "-g2012", "-s", "tb_m08_d3d_lif_axil",
                "-o", executable,
                str(ROOT / "rtl/m08/m08_d3d_lif_axil.v"),
                str(ROOT / "rtl/m08/tb_m08_d3d_lif_axil.sv"),
            ]
            build = subprocess.run(compile_cmd, capture_output=True, text=True,
                                   timeout=45)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run(["vvp", executable], capture_output=True,
                                 text=True, timeout=45)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("M08_D3D_FOUR_FIXTURE_AXIL_M02_RTL_PASS", run.stdout)

    def build_mock_hardware_evidence(self):
        folder = self.run.parent / "m08_d3d_neuron_HW_SYNTH01"
        folder.mkdir(exist_ok=True)
        sha = g.native(self.run)["candidate_sha256"]
        original_fixture_lines = [vectors.format_fixture(f) for f in vectors.FIXTURES]
        golden = ("# schema=m08-d3d-m02-golden-v1\n"
                  "# independent_dense_vs_event=PASS\n"
                  + "\n".join(original_fixture_lines) + "\n")
        lines = [
            "schema=m08-d3d-hardware-lif4-ticks-v1",
            "result=FOUR_HARDWARE_NEURON_FIXTURES_MATCHED_M02",
            "candidate_sha256=" + sha,
            "target=localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
            "device=xck26_0",
            "debug_axi=hw_axi_1",
            "neural_execution_tested=YES_SINGLE_NEURON_FOUR_TICKS",
            "no_ps_axi_ddr_ssh_used=YES",
            "reset_mode=FABRIC_POR_256_CYCLES",
            "ps_clock_dependency=YES",
            "synapse_routing_tested=NO",
            "full_m06_paging_tested=NO",
        ]
        log = [
            "M08_D3D_PROGRAM_COMPLETED",
            "M08_D3D_BRAM_TRANSPORT_REGRESSION_PASS",
            "M08_D3D_AXI_MASTER|hw_axi_1",
            "M08_D3D_PHYSICAL_NEURAL_RESULT_PC_RECEIPT=" + str(folder),
        ]
        for fixture in vectors.FIXTURES:
            fields = vectors.format_fixture(fixture).split("|")
            lines.append(
                f"fixture={fixture.name} nonce={fields[1]} "
                f"voltages={','.join(fields[11:15])} "
                f"spike_mask={fields[15]} hardware=PASS")
            log.append(
                f"M08_D3D_HW_NEURAL_M02_PARITY_PASS|{fixture.name}|{fields[15]}")
        files = {
            "00_executed_source.tcl": physical_audit.SCRIPT.read_bytes(),
            "01_jtag_neuron.log": ("\n".join(log)+"\n").encode(),
            "02_jtag_neuron.jou": b"synthetic test journal\n",
            "03_exit.txt": b"vivado_physical_exit=0\n",
            "10_m02_golden.txt": golden.encode("ascii"),
            "80_neural_parity_readback.txt": ("\n".join(lines)+"\n").encode(),
        }
        for name, data in files.items():
            (folder/name).write_bytes(data)
        self.rehash_hardware(folder)
        return folder

    @staticmethod
    def rehash_hardware(folder):
        (folder/"99_evidence_sha256.txt").write_text(
            "".join(sha256((folder/name).read_bytes()).hexdigest() + "  " + name + "\n"
                    for name in physical_audit.EXPECTED))

    def test_synthetic_physical_auditor_requires_m02_parity_original_receipts(self):
        hw = self.build_mock_hardware_evidence()
        result = physical_audit.verify(self.run, hw)
        self.assertTrue(result["hardware_execution_verified"])
        self.assertFalse(result["full_m06_neuromorphic_accelerator_verified"])
        self.assertEqual(result["fixtures"], 4)

    def test_physical_auditor_rejects_false_success_even_if_rehashed(self):
        hw = self.build_mock_hardware_evidence()
        receipt = hw / "80_neural_parity_readback.txt"
        receipt.write_text(receipt.read_text().replace(
            "voltages=00000002", "voltages=00000003"))
        self.rehash_hardware(hw)
        with self.assertRaisesRegex(physical_audit.Reject, "trace differs"):
            physical_audit.verify(self.run, hw)

    def test_vivado_tcl_scripts_are_lexically_balanced(self):
        if not shutil.which("tclsh"):
            self.skipTest("tclsh is not installed")
        for filename in ("m08_d3d_neuron_build.tcl",
                         "m08_d3d_neuron_readback_once.tcl"):
            script = ROOT / "scripts" / filename
            command = (
                'set fd [open {' + str(script) + '} r]\n'
                'set source [read $fd]\n'
                'close $fd\n'
                'if {![info complete $source]} {puts stderr "incomplete Tcl"; exit 3}\n'
                'puts TCL_SYNTAX_BALANCED\n'
            )
            run = subprocess.run(["tclsh"], input=command, text=True,
                                 capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, filename + ": " + run.stderr)
            self.assertIn("TCL_SYNTAX_BALANCED", run.stdout)

    def test_physical_programming_remains_an_explicit_separate_action(self):
        path = ROOT / "scripts/run_m08_d3d_neuron_physical_once.sh"
        if not path.exists():
            self.skipTest("D3.D physical runner not yet implemented")
        body = path.read_text()
        self.assertIn("M08_D3D_ALLOW_PROGRAM", body)
        self.assertIn("m08_d3d_lif_jtag_UNRELEASED.bit", body)
        self.assertNotIn("m08_d3c_jtag_bram_r2_UNRELEASED.bit", body)
        self.assertIn("m08_d3d_neuron_gate.py", body)
        self.assertIn("timeout --signal=TERM", body)


if __name__ == "__main__":
    unittest.main()
