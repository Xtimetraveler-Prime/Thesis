"""M05.12d.3 original signed32 HLS PS/PL candidate, host NEGATIVE tests.

Simulated report schema is NOT Vivado evidence. Original owner must execute the
offline Vivado 2025.2 runner with real externally stored Vitis-generated RTL.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d3_hls_connected_candidate_audit import (
    META, DMA, LINKS, CLOCK, RESET, RESET_INT, RESET_PER, RESETFEED,
    RESETDIR, RESETCFG, RESETINV, PSCFG, STREAM, CONTROL, MEMORY,
    NATIVE, audit_connected_candidate,
)
from m05_12d3_hls_connected_preflight import preflight


def fixture() -> str:
    result = [f"META|{key}|{value}" for key, value in META.items()]
    result += [f"DMA|{name}|{role}|256|32|24"
               for name, role in sorted(DMA.items())]
    result += [f"LINK|{src}|{dst}|link_{i}"
               for i, (src, dst) in enumerate(sorted(LINKS))]
    result += [f"HLSWIRE|{src}|{dst}|{bits}|native_{i}"
               for i, ((src, dst), bits) in enumerate(sorted(NATIVE.items()))]
    result += ["HLSINTF|s_axi_control|SLAVE"]
    result += [f"CLK|{name}|single_clock" for name in sorted(CLOCK)]
    result += [f"RESET|{name}|{'interconnect_rst' if name in RESET_INT else 'peripheral_rst'}"
               for name in sorted(RESET)]
    result += [f"RESETFEED|{name}|{'pre_inv' if name in ('ps/pl_resetn0', 'reset_inv/Op1') else 'post_inv'}"
               for name in sorted(RESETFEED)]
    result += [f"RESETDIR|{key}|{value}" for key, value in RESETDIR.items()]
    result += [f"RESETCFG|{key}|{value}" for key, value in RESETCFG.items()]
    result += [f"RESETINV|{key}|{value}" for key, value in RESETINV.items()]
    result += [f"PSCFG|{key}|{value}" for key, value in PSCFG.items()]
    return "\n".join(result) + "\n"


class M0512D3HLSConnectedCandidateTests(unittest.TestCase):
    def test_full_expected_authentic_hls_schema_synthetic(self):
        facts = audit_connected_candidate(fixture())
        self.assertEqual(facts["stream_links"], 4)
        self.assertEqual(facts["control_links"], 7)
        self.assertEqual(facts["independent_control_banks"], 6)
        self.assertEqual(facts["memory_links"], 5)
        self.assertEqual(facts["native_hls_links"], 12)
        self.assertEqual(facts["clock_consumers"], 16)
        self.assertEqual(facts["reset_consumers"], 8)
        self.assertEqual(facts["reset_input_pins"], 4)

    def test_previous_dma_streams_and_control_banks_exact(self):
        old_tcl = (ROOT / "scripts/m05_12d3_connected_candidate.tcl").read_text()
        next_tcl = (ROOT / "scripts/m05_12d3_hls_connected_candidate.tcl").read_text()
        for original in (
            "dma_neurons/M_AXIS_MM2S shell/S_AXIS_NEURONS",
            "dma_synapses/M_AXIS_MM2S shell/S_AXIS_SYNAPSES",
            "dma_external/M_AXIS_MM2S shell/S_AXIS_EXTERNAL",
            "shell/M_AXIS_TRACE dma_trace/S_AXIS_S2MM",
            "4 shell/s_axi",
            "mem_sc/M00_AXI ps/S_AXI_HP0_FPD",
            "reset_inv/Res", "CONFIG.C_EXT_RESET_HIGH",
            'lappend clocks "$name/m_axi_mm2s_aclk"',
        ):
            self.assertIn(original, old_tcl)
            self.assertIn(original, next_tcl)
        self.assertIn("CONFIG.NUM_SI 1 CONFIG.NUM_MI 5", old_tcl)
        self.assertIn("CONFIG.NUM_SI 1 CONFIG.NUM_MI 6", next_tcl)
        self.assertIn("5 hls/s_axi_control", next_tcl)
        self.assertIn("hls/ap_clk", next_tcl)
        self.assertIn("hls/ap_rst_n", next_tcl)
        self.assertEqual(len(STREAM), 4)
        self.assertEqual(len(CONTROL), 7)
        self.assertEqual(len(MEMORY), 5)

    def test_native_data_width_handshake_and_direction_corruption_rejected(self):
        good = fixture()
        for invalid in (
            "HLSWIRE|shell/hls_neuron_tdata|hls/neurons_TDATA|128|",
            "HLSWIRE|shell/hls_synapse_tdata|hls/synapses_TDATA|192|",
            "HLSWIRE|shell/hls_external_tdata|hls/external_events_TDATA|128|",
            "HLSWIRE|hls/trace_TDATA|shell/hls_trace_tdata|192|",
            "HLSWIRE|hls/trace_TVALID|shell/hls_trace_tvalid|1|",
            "HLSWIRE|shell/hls_trace_tready|hls/trace_TREADY|1|",
        ):
            row = next(x for x in good.splitlines(keepends=True) if x.startswith(invalid))
            for broken in (
                good.replace(row, "", 1),
                good.replace(row, row * 2, 1),
                good.replace(row, row.replace("|128|", "|256|").replace("|192|", "|256|").replace("|1|", "|8|"), 1),
                good.replace(row, row.replace("hls/", "wrong/", 1), 1),
            ):
                with self.subTest(row=row, broken=broken[-90:]):
                    with self.assertRaises(ValueError):
                        audit_connected_candidate(broken)

    def test_sixth_control_and_native_axi_slave_must_exist(self):
        good = fixture()
        wanted = next(x for x in good.splitlines(keepends=True)
                      if x.startswith("LINK|ctrl_sc/M05_AXI|hls/s_axi_control|"))
        for bad in (
            good.replace(wanted, "", 1),
            good.replace(wanted, wanted * 2, 1),
            good.replace(wanted, wanted.replace("hls/s_axi_control", "shell/s_axi"), 1),
            good.replace("HLSINTF|s_axi_control|SLAVE\n", "", 1),
            good.replace("HLSINTF|s_axi_control|SLAVE", "HLSINTF|s_axi_control|MASTER", 1),
        ):
            with self.assertRaises(ValueError):
                audit_connected_candidate(bad)

    def test_native_net_alias_and_missing_clock_or_reset_rejected(self):
        good = fixture()
        first = next(x for x in good.splitlines(keepends=True)
                     if x.startswith("HLSWIRE|shell/hls_neuron_tdata"))
        second = next(x for x in good.splitlines(keepends=True)
                      if x.startswith("HLSWIRE|shell/hls_synapse_tdata"))
        net = first.strip().rsplit("|", 1)[1]
        for bad in (
            good.replace(second, second.rsplit("|", 1)[0] + "|" + net + "\n"),
            good.replace(first, first.rsplit("|", 1)[0] + "|single_clock\n"),
            good.replace("CLK|hls/ap_clk|single_clock\n", ""),
            good.replace("RESET|hls/ap_rst_n|peripheral_rst\n", ""),
            good.replace("RESET|hls/ap_rst_n|peripheral_rst",
                         "RESET|hls/ap_rst_n|interconnect_rst"),
        ):
            with self.assertRaises(ValueError):
                audit_connected_candidate(bad)

    def test_no_false_address_conversion_or_full_validation_pass(self):
        good = fixture()
        for before, after in (
            ("META|address_map|NOT_ASSIGNED", "META|address_map|ASSIGNED"),
            ("META|full_bd_validation|NOT_RUN", "META|full_bd_validation|PASS"),
            ("META|data_width_conversion|SMARTCONNECT_CANDIDATE_NOT_GENERATED",
             "META|data_width_conversion|VERIFIED"),
            ("META|hls_control|REAL_GENERATED_MODULE_REF_CANDIDATE",
             "META|hls_control|MOCK_HLS"),
        ):
            with self.assertRaises(ValueError):
                audit_connected_candidate(good.replace(before, after, 1))

    def test_owner_preflight_rejects_missing_or_failed_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "neuromorphic_v1_m05_12d3_real_hls_contract_trial"
            artifact.mkdir()
            cpp = root / "signed32.cpp"
            cpp.write_text("fixture NOT genuine HLS")
            (artifact / "result.txt").write_text("exit_status=1\n")
            with self.assertRaisesRegex(ValueError, "exit_status"):
                preflight(artifact, cpp)
            (artifact / "result.txt").write_text("exit_status=0\n")
            with self.assertRaises(OSError):
                preflight(artifact, cpp)


    def test_preflight_output_allowlist_tracks_every_d3_integration_runner(self):
        from m05_12d3_hls_connected_preflight import require_new_preflight_output
        # Regression for real 2026-11-09 operator exit2 before any Vivado
        # call: new DMA runner introduced mktemp prefix without registering it.
        runner_names = (
            "run_m05_12d3_hls_connected_candidate.sh",
            "run_m05_12d3_native_axis_candidate.sh",
            "run_m05_12d3_address_validate_candidate.sh",
            "run_m05_12d3_dma_memory_candidate.sh",
        )
        with tempfile.TemporaryDirectory() as temp:
            for name in runner_names:
                script = (ROOT / "scripts" / name).read_text()
                import re
                match = re.search(r'(neuromorphic_v1_m05_12d3_[a-z_]+_)\$\(date', script)
                self.assertIsNotNone(match, f"missing standard mktemp prefix in {name}")
                prefix = match.group(1)
                parent = Path(temp) / (prefix + "20261109T063355Z_test")
                parent.mkdir()
                target = parent / "01_hls_preflight.txt"
                require_new_preflight_output(target)
                target.write_text("do not overwrite original evidence")
                with self.assertRaises(ValueError):
                    require_new_preflight_output(target)
                with self.assertRaises(ValueError):
                    require_new_preflight_output(parent / "other_evidence.txt")
            unknown = Path(temp) / "neuromorphic_v1_m05_12d3_unknown_20261109T000000Z_test"
            unknown.mkdir()
            with self.assertRaises(ValueError):
                require_new_preflight_output(unknown / "01_hls_preflight.txt")

    def test_new_runner_unique_evidence_and_no_hardware_actions(self):
        sh = ROOT / "scripts/run_m05_12d3_hls_connected_candidate.sh"
        tcl = ROOT / "scripts/m05_12d3_hls_connected_candidate.tcl"
        source = sh.read_text() + "\n" + tcl.read_text()
        for required in (
            "source_hls_contract_evidence.txt", "working_tree_status.txt",
            "source_sha256.txt", "result.txt", "01_hls_preflight.txt",
            "02_hls_connected_graph.txt", "03_vivado.log",
            "04_independent_audit.log", "m05_rolling_replay hls",
            "create_bd_cell -type module", "hls/s_axi_control",
            "get_bd_nets -of_objects", "HLSWIRE|", "HLSINTF|",
            "CONFIG.NUM_MI 6", "get_property LEFT", "get_property RIGHT",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "program_hw_devices", "open_hw_target", "connect_hw_server",
            "write_bitstream", "launch_runs", "xsdb", "rm -rf",
            "assign_bd_address", "validate_bd_design",
        ):
            self.assertNotIn(forbidden, source)
        self.assertEqual(subprocess.run(["bash", "-n", str(sh)],
                        capture_output=True).returncode, 0)

    def test_original_d3_verification_and_neural_files_unchanged(self):
        for fname in (
            "scripts/m05_12d3_connected_candidate.tcl",
            "scripts/m05_12d3_connected_candidate_audit.py",
            "scripts/run_m05_12d3_connected_candidate.sh",
            "hls/m05_rolling/m05_rolling.cpp",
            "rtl/m05_12/m05_12d_axis_shell_ref.v",
            "rtl/m05_11/m05_11_stream_shell.v",
        ):
            with self.subTest(file=fname):
                path = ROOT / fname
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                audit_connected_candidate(fixture())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_report_cli_fails_closed_and_is_readonly(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "02_hls_connected_graph.txt"
            expected = fixture()
            report.write_text(expected)
            script = ROOT / "scripts/m05_12d3_hls_connected_candidate_audit.py"
            a = subprocess.run([sys.executable, str(script), "--report", str(report)],
                               capture_output=True, text=True)
            self.assertEqual(a.returncode, 0, a.stderr)
            self.assertIn("independent real signed32 HLS PS/PL graph audit", a.stdout)
            self.assertEqual(expected, report.read_text())
            report.unlink()
            b = subprocess.run([sys.executable, str(script), "--report", str(report)],
                               capture_output=True, text=True)
            self.assertNotEqual(b.returncode, 0)


if __name__ == "__main__":
    unittest.main()
