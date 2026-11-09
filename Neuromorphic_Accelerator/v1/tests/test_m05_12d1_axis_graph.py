"""M05.12d.1 host-only PL AXIS graph boundary tests (NOT Vivado/PS/DMA).

Optional Icarus compile checks wrapper-to-existing-shell HDL structure.
The genuine IP Integrator netlist must still run under operator Vivado.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12_dma_candidate_audit import ROLES, PART, VLNV, expected_config
from m05_12d1_axis_graph_audit import (
    SCOPE, SHELL_MODULE, LINKS, verify_axis_graph_report,
)


def synthetic_report():
    lines = [f"META|part|{PART}", f"META|vlnv|{VLNV}",
             f"META|scope|{SCOPE}", "META|source_mgmt_mode|All",
             f"CELL|shell|{SHELL_MODULE}"]
    for name, role in ROLES.items():
        lines.append(f"CELL|{name}|{role}")
        lines.extend(f"CFG|{name}|{key}|{value}"
                     for key, value in expected_config(role).items())
    lines.extend(f"LINK|{source}|{dest}|net_{i}"
                 for i, (source, dest) in enumerate(LINKS.items()))
    return "\n".join(lines) + "\n"


class M0512D1AxisGraphTests(unittest.TestCase):
    def test_four_connected_point_to_point_links_synthetic(self):
        self.assertEqual(verify_axis_graph_report(synthetic_report()), 4)

    def test_wrong_link_or_missing_trace_link_fail_closed(self):
        src = synthetic_report()
        target = next(x for x in src.splitlines() if x.startswith("LINK|dma_trace"))
        for bad in (
            src.replace(target + "\n", "", 1),
            src.replace(target, target + "\n" + target, 1),
            src.replace(target, target.replace("shell/M_AXIS_TRACE",
                                               "shell/S_AXIS_EXTERNAL"), 1),
            src.replace(target, target.rsplit("|", 1)[0] + "|net_0", 1),
        ):
            with self.subTest(bad=bad[-110:]):
                with self.assertRaises(ValueError):
                    verify_axis_graph_report(bad)

    def test_config_provenance_duplicate_unknown_and_partial_rejected(self):
        src = synthetic_report()
        marker = "CFG|dma_neurons|c_sg_length_width|24\n"
        for bad in (
            src.replace(marker, marker.replace("24", "14"), 1),
            src.replace(marker, "", 1),
            src.replace(marker, marker * 2, 1),
            src.replace("META|part|", "META|other|", 1),
            src.replace(f"META|vlnv|{VLNV}", "META|vlnv|DMA:6.0", 1),
            src.replace(f"META|scope|{SCOPE}", "META|scope|ON_BOARD", 1),
            src.replace("META|source_mgmt_mode|All",
                        "META|source_mgmt_mode|DisplayOnly", 1),
            src.replace("META|source_mgmt_mode|All\n", "", 1),
            src.replace("CELL|shell|m05_12d_axis_shell_ref\n", "", 1),
            src + "LINK|rogue|shell/S_AXIS_NEURONS|net_5\n",
            src[:-1],
        ):
            with self.subTest(bad=bad[:105]):
                with self.assertRaises(ValueError):
                    verify_axis_graph_report(bad)

    def test_wrapper_exactly_maps_existing_shell_ports(self):
        original = (ROOT / "rtl/m05_11/m05_11_stream_shell.v").read_text()
        new = (ROOT / "rtl/m05_12/m05_12d_axis_shell_ref.v").read_text()
        hdr = original.split("module m05_11_stream_shell(", 1)[1].split(");", 1)[0]
        original_ports = re.findall(
            r"\b(?:input|output)\s+wire\s*(?:\[[^\]]+\])?\s*(\w+)\b",
            hdr,
        )
        self.assertEqual(len(original_ports), 54)
        self.assertEqual(new.count("m05_11_stream_shell shell_core("), 1)
        for port in original_ports:
            with self.subTest(port=port):
                self.assertEqual(len(re.findall(
                    r"^\s*\." + re.escape(port) + r"\(" + re.escape(port) + r"\)",
                    new, re.MULTILINE,
                )), 1)
        self.assertNotIn("m05_rolling_replay", new)

    def test_wrapper_has_all_axi_stream_byte_qualifiers(self):
        content = (ROOT / "rtl/m05_12/m05_12d_axis_shell_ref.v").read_text()
        for prefix, interface in (
            ("n_dma", "S_AXIS_NEURONS"),
            ("s_dma", "S_AXIS_SYNAPSES"),
            ("e_dma", "S_AXIS_EXTERNAL"),
            ("trace_dma", "M_AXIS_TRACE"),
        ):
            for signal in ("TDATA", "TKEEP", "TLAST", "TVALID", "TREADY"):
                with self.subTest(interface=interface, signal=signal):
                    expected = (
                        f"X_INTERFACE_INFO = "
                        f"\"xilinx.com:interface:axis:1.0 {interface} {signal}\""
                    )
                    self.assertIn(expected, content)
            self.assertIn(f"XIL_INTERFACENAME {interface}, TDATA_NUM_BYTES 32", content)
            self.assertRegex(content, rf"\b(?:input|output) wire \[255:0\] {prefix}_tdata\b")
            self.assertRegex(content, rf"\b(?:input|output) wire \[31:0\] {prefix}_tkeep\b")

    @unittest.skipUnless(shutil.which("iverilog"), "Icarus not installed locally")
    def test_wrapper_native_icarus_elaboration_without_hls(self):
        files = (
            ROOT / "rtl/m05_11/m05_11_axil_session_controller.v",
            ROOT / "rtl/m05_11/m05_trace_dma_packetizer.v",
            ROOT / "rtl/m05_11/m05_ingress_dma_unpad.v",
            ROOT / "rtl/m05_11/m05_11_stream_shell.v",
            ROOT / "rtl/m05_12/m05_12d_axis_shell_ref.v",
        )
        with tempfile.TemporaryDirectory(prefix="m05_12d1_icarus_") as td:
            proc = subprocess.run(
                ["iverilog", "-g2012", "-s", "m05_12d_axis_shell_ref",
                 "-o", str(Path(td) / "module_ref.out"),
                 *(str(f) for f in files)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_audit_cli_is_read_only_and_fails_if_missing(self):
        with tempfile.TemporaryDirectory(prefix="m05_12d1_audit_") as td:
            target = Path(td) / "report.txt"
            original = synthetic_report()
            target.write_text(original)
            cmd = [sys.executable,
                   str(ROOT / "scripts/m05_12d1_axis_graph_audit.py"),
                   "--report", str(target)]
            ok = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("PASS: M05.12d.1 independent", ok.stdout)
            self.assertEqual(target.read_text(), original)
            target.unlink()
            err = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(err.returncode, 0)
            self.assertIn("ERROR: M05.12d.1", err.stderr)

    def test_auto_source_management_before_module_reference_regression(self):
        # Real owner Vivado 2025.2 failure eea1a56: filemgmt 56-176,
        # 56-587 and BD 41-1690. UG994 requires source_mgmt_mode All.
        tcl = (ROOT / "scripts/m05_12d1_axis_graph.tcl").read_text()
        required = "set_property source_mgmt_mode All [current_project]"
        self.assertEqual(tcl.count(required), 1)
        self.assertLess(tcl.index("create_project -in_memory"), tcl.index(required))
        self.assertLess(tcl.index(required), tcl.index("add_files -norecurse"))
        self.assertLess(tcl.index(required), tcl.index("update_compile_order -fileset sources_1"))
        self.assertLess(tcl.index("update_compile_order -fileset sources_1"),
                        tcl.index("create_bd_cell -type module -reference"))
        self.assertEqual(
            tcl.count('get_property source_mgmt_mode [current_project]'), 2
        )
        self.assertIn(
            'error "M05.12d.1 RTL module reference requires automatic compile order"',
            tcl
        )
        self.assertIn('META|source_mgmt_mode|$source_mode', tcl)
        self.assertIn('M05_12D1_SOURCE_MGMT_MODE=$source_mode', tcl)
        for manual in ("source_mgmt_mode DisplayOnly",
                       "source_mgmt_mode None",
                       "reorder_files", "set_property source_mgmt_mode Manual"):
            self.assertNotIn(manual, tcl)

    def test_no_board_runner_and_actual_bd_net_proof_requirements(self):
        bash = ROOT / "scripts/run_m05_12d1_axis_graph.sh"
        check = subprocess.run(["bash", "-n", str(bash)],
                               capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        help_run = subprocess.run(["bash", str(bash), "--help"],
                                  capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("NO BOARD", help_run.stdout)
        bad = subprocess.run(["bash", str(bash), "--invalid"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        tcl = (ROOT / "scripts/m05_12d1_axis_graph.tcl").read_text()
        run = bash.read_text()
        for phrase in ("create_project -in_memory",
                       "create_bd_cell -type module -reference",
                       "connect_bd_intf_net", "get_bd_intf_nets -of_objects",
                       "get_bd_intf_pins -of_objects", "add_files -norecurse",
                       "XILINX_NO_HARDWARE_NEVER"):  # intentionally excluded
            if phrase == "XILINX_NO_HARDWARE_NEVER":
                self.assertNotIn(phrase, tcl)
            else:
                self.assertIn(phrase, tcl)
        self.assertIn("m05_12d1_axis_graph_audit.py", run)
        self.assertIn("source_sha256.txt", run)
        self.assertIn("result.txt", run)
        for forbidden in (
            "program_hw_devices", "connect_hw_server",
            "open_hw_target", "write_bitstream", "launch_runs", "xsdb",
            "open_project", "open_bd_design", "assign_bd_address",
            "connect_bd_net", "write_hw_platform", "write_bd_tcl",
            "rm -rf", "validate_bd_design",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, tcl)
                self.assertNotIn(forbidden, run)


if __name__ == "__main__":
    unittest.main()
