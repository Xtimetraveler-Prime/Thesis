"""No-Vivado synthetic tests for the M06 ORIGINAL IP XSim-BFM port probe.

These deliberately forged fixtures only test the auditor/parser safety.
They NEVER claim to be a genuine owner Vivado log or vendor IP simulation.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m06_original_mem_sc_contract_audit import (
    BD, ENDPOINTS, ORIGINAL, inspect,
)

MARKER = "M06_EXACT_ORIGINAL_MEM_SC_PORTS_CAPTURED|READ_ONLY_NO_XSIM_NO_BOARD"


def synthetic_fixture(folder: Path):
    original = folder / ORIGINAL
    original.mkdir()
    report = folder / "ports.txt"
    log = folder / "vivado.log"
    xpr = original / "13_file_backed_project/m05_d3_output_products.xpr"
    bd = original / "13_file_backed_project/m05_d3_output_products.srcs" / "sources_1/bd" / BD / (BD+".bd")
    xpr.parent.mkdir(parents=True)
    bd.parent.mkdir(parents=True)
    xpr.write_text("synthetic ONLY")
    bd.write_text("synthetic ONLY")
    rows = [
        "META|purpose|M06_ORIGINAL_VENDOR_XSIM_BFM_PORT_CONTRACT_NOT_WARNINGS",
        f"SOURCE_XPR|{xpr.resolve()}",
        f"SOURCE_BD|{bd.resolve()}",
        "MEM_IP_VLNV|xilinx.com:ip:smartconnect:1.0",
        "MEM_IP_PROPERTY|CONFIG.NUM_SI|4",
        "MEM_IP_PROPERTY|CONFIG.NUM_MI|1",
    ]
    for name, width in ENDPOINTS.items():
        if name == "ps/S_AXI_HP0_FPD":
            props = dict(READ_WRITE_MODE="READ_WRITE", ADDR_WIDTH="49",
                         ID_WIDTH="6", MAX_BURST_LENGTH="32", HAS_BURST="1",
                         AWUSER_WIDTH="1", ARUSER_WIDTH="1")
        elif name == "mem_sc/M00_AXI":
            props = dict(READ_WRITE_MODE="READ_WRITE", ADDR_WIDTH="49",
                         ID_WIDTH="0", MAX_BURST_LENGTH="32", HAS_BURST="1")
        else:
            props = dict(READ_WRITE_MODE=("WRITE_ONLY" if "S03" in name else "READ_ONLY"),
                         ADDR_WIDTH="32", ID_WIDTH="0",
                         MAX_BURST_LENGTH="16", HAS_BURST="0")
        rows.extend([
            f"ENDPOINT|{name}",
            f"ENDPOINT_PROPERTY|{name}|CONFIG.DATA_WIDTH|{width}",
            f"ENDPOINT_PROPERTY|{name}|CONFIG.PROTOCOL|AXI4",
        ] + [f"ENDPOINT_PROPERTY|{name}|CONFIG.{k}|{v}"
             for k, v in props.items()])
    rows.extend([
        "CLOCK_RESET_PORT|mem_sc/aclk|PRESENT",
        "CLOCK_RESET_PORT|mem_sc/aresetn|PRESENT",
        "SIM_FILESET|PRESENT",
        "SIM_PROPERTY|TOP|testbench_only",
        "SIM_QUERY|OK|2",
        "SIM_SOURCE|/synthetic/sim_0.v",
        "SIM_SOURCE|/synthetic/sim_1.v",
        "PROJECT_FILE_COUNT|382",
        "MEM_PROJECT_SOURCE|/synthetic/rtl/mem_sc_source.v",
        "SIMULATOR_FUNCTIONAL_TRIAL|NOT_EXECUTED",
        "GENERATE_TARGET|NOT_EXECUTED",
        "PHYSICAL_BOARD|NOT_AUTHORIZED",
        "RESULT|ORIGINAL_PORTS_CAPTURED_FOR_ONE_VENDOR_FUNCTIONAL_XSIM_TRIAL",
    ])
    report.write_text("\n".join(rows)+"\n")
    log.write_text(MARKER+"\n")
    return original, report, log


class M06OriginalVivadoProbeTests(unittest.TestCase):
    def test_synthetic_fixture_yields_only_port_contract_never_axi_pass(self):
        with tempfile.TemporaryDirectory() as d:
            result = inspect(*synthetic_fixture(Path(d)))
            self.assertEqual(result["endpoint_count"], 6)
            self.assertEqual(result["memory_si"], 4)
            self.assertEqual(result["source_compile_count"], 2)
            self.assertEqual(result["memory_mi_width_bits"], 128)
            self.assertEqual(result["functional_vendor_axi_result"], "NOT_EXECUTED")
            self.assertEqual(result["axi_transfer_correctness"], "NOT_PROVEN")

    def test_vivado_echo_of_tcl_puts_is_not_counted_as_actual_completion(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            log.write_text(
                '# puts "M06_EXACT_ORIGINAL_MEM_SC_PORTS_CAPTURED|READ_ONLY_NO_XSIM_NO_BOARD"\n'
                + MARKER + "\n")
            result = inspect(orig, report, log)
            self.assertEqual(result["observed_si_modes"]["S03"], "WRITE_ONLY")
            self.assertEqual(result["read_ports"], ["S00", "S01", "S02"])
            self.assertEqual(result["original_si_has_burst_property"], 0)

    def test_wrong_original_read_write_role_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            report.write_text(report.read_text().replace(
                "ENDPOINT_PROPERTY|mem_sc/S03_AXI|CONFIG.READ_WRITE_MODE|WRITE_ONLY",
                "ENDPOINT_PROPERTY|mem_sc/S03_AXI|CONFIG.READ_WRITE_MODE|READ_WRITE"))
            with self.assertRaisesRegex(ValueError, "contradicts actual owner readback"):
                inspect(orig, report, log)

    def test_wrong_original_burst_property_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            report.write_text(report.read_text().replace(
                "ENDPOINT_PROPERTY|mem_sc/S01_AXI|CONFIG.HAS_BURST|0",
                "ENDPOINT_PROPERTY|mem_sc/S01_AXI|CONFIG.HAS_BURST|1"))
            with self.assertRaisesRegex(ValueError, "contradicts actual owner readback"):
                inspect(orig, report, log)

    def test_wrong_mem_sc_data_width_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            text = report.read_text().replace(
                "ENDPOINT_PROPERTY|mem_sc/S00_AXI|CONFIG.DATA_WIDTH|256",
                "ENDPOINT_PROPERTY|mem_sc/S00_AXI|CONFIG.DATA_WIDTH|128")
            report.write_text(text)
            with self.assertRaisesRegex(ValueError, "width contradicts"):
                inspect(orig, report, log)

    def test_wrong_original_topology_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            report.write_text(report.read_text().replace(
                "MEM_IP_PROPERTY|CONFIG.NUM_SI|4",
                "MEM_IP_PROPERTY|CONFIG.NUM_SI|1"))
            with self.assertRaisesRegex(ValueError, "safety marker"):
                inspect(orig, report, log)

    def test_missing_or_repeated_endpoint_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            content = report.read_text()
            report.write_text(content.replace("ENDPOINT|mem_sc/S03_AXI\n", ""))
            with self.assertRaisesRegex(ValueError, "duplicate original"):
                inspect(orig, report, log)
            report.write_text(content.replace(
                "ENDPOINT|mem_sc/S03_AXI\n",
                "ENDPOINT|mem_sc/S03_AXI\nENDPOINT|mem_sc/S03_AXI\n"))
            with self.assertRaisesRegex(ValueError, "duplicate original"):
                inspect(orig, report, log)

    def test_missing_original_owner_vivado_marker_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            log.write_text("Synthetic test, deliberately NO Vivado success marker\n")
            with self.assertRaisesRegex(ValueError, "stdout missing"):
                inspect(orig, report, log)

    def test_malformed_sim_compile_order_not_promoted_to_pass(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            original = report.read_text()
            report.write_text(original.replace(
                "SIM_QUERY|OK|2", "SIM_QUERY|OK|3"))
            with self.assertRaisesRegex(ValueError, "file count"):
                inspect(orig, report, log)
            report.write_text(original.replace(
                "SIM_QUERY|OK|2", "SIM_QUERY|ERROR|not compiled"))
            result = inspect(orig, report, log)
            self.assertEqual(result["source_compile_count"], 2)
            self.assertEqual(result["functional_vendor_axi_result"], "NOT_EXECUTED")

    def test_cli_refuses_overwrite_and_does_not_change_fake_original(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, log = synthetic_fixture(Path(d))
            dest = Path(d)/"new_summary.json"
            script = ROOT/"scripts/m06_original_mem_sc_contract_audit.py"
            argv = [sys.executable, str(script), "--original", str(orig),
                    "--report", str(report), "--vivado-log", str(log),
                    "--output", str(dest)]
            before = report.read_bytes()
            proc = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(dest.read_text())
                             ["functional_vendor_axi_result"], "NOT_EXECUTED")
            proc2 = subprocess.run(argv, capture_output=True, text=True)
            self.assertEqual(proc2.returncode, 2)
            self.assertIn("overwrite", proc2.stderr)
            self.assertEqual(report.read_bytes(), before)

    def test_probe_script_statically_forbids_hardware_and_source_mutation(self):
        tcl = (ROOT/"scripts/m06_original_mem_sc_ports.tcl").read_text()
        runner = (ROOT/"scripts/run_m06_original_mem_sc_port_contract.sh").read_text()
        self.assertIn("open_project -read_only", tcl)
        self.assertIn("RESULT|ORIGINAL_PORTS_CAPTURED", tcl)
        self.assertIn("generate_target", tcl)  # Only NOT_EXECUTED marker and comment
        self.assertNotIn("\nlaunch_simulation ", tcl)
        self.assertNotIn("\ngenerate_target all", tcl)
        self.assertNotIn("\nwrite_bd_tcl ", tcl)
        self.assertNotIn("\nsave_project_as ", tcl)
        self.assertIn("sha256sum", runner)
        self.assertIn("02_original_mem_sc_ports.txt", runner)


if __name__ == "__main__":
    unittest.main()
