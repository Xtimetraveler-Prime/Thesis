"""M05 D4.2/D4.3 SOURCE-ONLY adversarial/positive feasibility unit tests.

All model discovery rows and property traces are SYNTHETIC. No genuine owner
Vivado file is accessible in CI, and tests must not claim vendor simulation.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d4_protocol_risk import review, NEW_PREFIX
from m05_12d4_vendor_sim_readback_audit import inspect, SCOPE, TAIL, SUCCESS


def report(root: Path, sim: bool = True, query: bool = True) -> str:
    base = root.resolve()
    bdname = "m05_12d3_real_signed32_hls_six_control_address_candidate"
    path = base / ("13_file_backed_project/m05_d3_output_products.srcs/"
                   "sources_1/bd/" + bdname + "/" + bdname + ".bd")
    lines = [
        SCOPE,
        "PROJECT|" + str(base / "13_file_backed_project/m05_d3_output_products.xpr"),
        "BD|" + str(path),
    ]
    if sim:
        lines += ["SIMFILESET|PRESENT", "SIMPROP|TOP|original_bd_wrapper",
                  "SIMPROP|TARGET_SIMULATOR|xsim"]
        if query:
            lines += ["SIMCOMPILE|QUERY_OK", "MEM_SIM_FILE|/original/mem_sc_model.v",
                      "SIMCOMPILE_COUNT|12", "MEM_COMPILE_COUNT|1"]
        else:
            lines += ["SIMCOMPILE|QUERY_ERROR", "SIMERROR|no compiled model"]
    else:
        lines += ["SIMFILESET|MISSING", "SIMCOMPILE|UNAVAILABLE"]
    lines += ["MEM_PROJECT_FILE|/original/mem_sc_original.xci",
              "PROJECT_FILE_COUNT|44", "MEM_PROJECT_COUNT|1"]
    lines.extend(TAIL)
    return "\n".join(lines) + "\n"


class OriginalProtocolGateTests(unittest.TestCase):
    def test_sim_readback_present_original_mem_sc_fileset_is_not_sim_pass(self):
        with tempfile.TemporaryDirectory() as d:
            a = inspect(report(Path(d)), Path(d))
            self.assertEqual(a["simulation_fileset"], "PRESENT")
            self.assertEqual(a["compile_order_status"], "QUERY_OK")
            self.assertEqual(a["vivado_fileset"]["mem_compile_objects"], 1)
            self.assertEqual(a["simulation"], "NOT_RUN")
            self.assertEqual(a["vendor_downsize_axi_protocol"], "NOT_PROVEN")

    def test_unavailable_vendor_model_is_captured_not_falsely_successful(self):
        with tempfile.TemporaryDirectory() as d:
            a = inspect(report(Path(d), sim=False), Path(d))
            self.assertEqual(a["simulation_fileset"], "MISSING")
            self.assertEqual(a["compile_order_status"], "UNAVAILABLE")
            self.assertEqual(a["vendor_downsize_axi_protocol"], "NOT_PROVEN")

    def test_vendor_sim_compile_order_query_error_retains_failure_reason(self):
        with tempfile.TemporaryDirectory() as d:
            a = inspect(report(Path(d), query=False), Path(d))
            self.assertEqual(a["compile_order_status"], "QUERY_ERROR")
            self.assertEqual(a["vivado_fileset"]["compile_error"], "no compiled model")

    def test_wrong_model_counts_and_duplicate_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            original = report(Path(d))
            for body in (
                original.replace("MEM_COMPILE_COUNT|1", "MEM_COMPILE_COUNT|0"),
                original.replace("MEM_PROJECT_COUNT|1", "MEM_PROJECT_COUNT|2"),
                original.replace("SIMCOMPILE_COUNT|12", "SIMCOMPILE_COUNT|0"),
                original.replace("MEM_SIM_FILE|/original/mem_sc_model.v",
                                 "MEM_SIM_FILE|/original/other_model.v"),
            ):
                with self.subTest(body=body), self.assertRaises(ValueError):
                    inspect(body, Path(d))

    def test_report_schema_cannot_upgrade_not_run_to_simulation_pass(self):
        with tempfile.TemporaryDirectory() as d:
            original = report(Path(d))
            for altered in (
                original.replace("META|simulation|NOT_RUN", "META|simulation|PASS"),
                original.replace("META|generated_model_compile|NOT_RUN",
                                 "META|generated_model_compile|PASS"),
                original.replace("META|physical_board|NOT_AUTHORIZED",
                                 "META|physical_board|AUTHORIZED"),
                original.replace("SIM_MODEL_DISCOVERY|COMPLETE",
                                 "SIM_MODEL_DISCOVERY|PASS"),
                original[:-1],
                original + "FORGED|PASS\n",
            ):
                with self.subTest(mutated=altered), self.assertRaises(ValueError):
                    inspect(altered, Path(d))

    def test_exact_genuine_saved_project_and_bd_path_required(self):
        with tempfile.TemporaryDirectory() as d:
            good = report(Path(d))
            invalid = good.replace(
                "13_file_backed_project/m05_d3_output_products.xpr",
                "13_file_backed_project/FAKE.xpr")
            with self.assertRaisesRegex(ValueError, "saved project"):
                inspect(invalid, Path(d))
            with self.assertRaisesRegex(ValueError, "saved project"):
                inspect(good, Path(d) / "other")

    def test_original_provenance_required_for_risk_decision(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises((ValueError, OSError)):
                review(root, root, root)
            self.assertTrue(NEW_PREFIX.startswith("neuromorphic_v1_m05_12d4_"))

    def test_vendor_readonly_tcl_only_discovers_simulation_models(self):
        p = ROOT / "scripts/m05_12d4_vendor_sim_feasibility.tcl"
        tcl = p.read_text()
        for required in (
            "open_project -read_only $xpr", "open_bd_design [lindex $exactbd 0]",
            "get_files -compile_order sources -used_in simulation -of_objects $sim",
            "SIMFILESET|PRESENT", "SIMCOMPILE|QUERY_ERROR",
            "SIM_MODEL_DISCOVERY|COMPLETE|SIMULATOR_FUNCTIONAL_PROOF_BLOCKED",
            "META|simulation|NOT_RUN", "close_project",
        ):
            self.assertIn(required, tcl)
        for forbidden in (
            "launch_simulation", "export_simulation", "generate_target", "save_bd_design",
            "create_bd_cell", "synth_design", "write_bitstream",
            "open_hw_target", "program_hw_devices", "connect_hw_server",
        ):
            # Header intentionally mentions disabled commands; only check
            # noncomment executable lines, not explanatory comments.
            executable = "\n".join(line for line in tcl.splitlines()
                                   if not line.lstrip().startswith("#"))
            self.assertNotIn(forbidden, executable)

    def test_single_owner_runner_shell_syntax_and_genuine_before_after_hash_contract(self):
        runner = ROOT / "scripts/run_m05_12d4_protocol_gate.sh"
        body = runner.read_text()
        self.assertEqual(subprocess.run(["bash", "-n", str(runner)],
                         capture_output=True).returncode, 0)
        for required in (
            "source_sha256.txt", "08_source_sha256_after.txt",
            "02_original_axi_risk.json", "07_post_original_axi_risk.json",
            "06_model_discovery_audit.json", "04_vendor_sim_sources.txt",
            "mktemp -d", "cmp -s", "exit 3",
            "m05_12d4_protocol_risk.py",
        ):
            self.assertIn(required, body)
        for bad in ("rm -rf", "program_hw_devices", "write_bitstream",
                    "launch_simulation", "synth_design", "generate_target",
                    "connect_hw_server", "xsdb"):
            self.assertNotIn(bad, body)

    def test_missing_original_or_prior_owner_proof_rejected_by_cli(self):
        with tempfile.TemporaryDirectory() as d:
            temp = Path(d)
            reportfile = temp / "fake.txt"
            reportfile.write_text(report(temp))
            output = temp / "neuromorphic_v1_m05_12d4_protocol_gate_SYNTHETIC"
            output.mkdir()
            result = subprocess.run([
                sys.executable,
                str(ROOT / "scripts/m05_12d4_vendor_sim_readback_audit.py"),
                "--original-d3", str(temp), "--d4-inventory", str(temp),
                "--d4-bd", str(temp), "--model-report", str(reportfile),
                "--vivado-log", str(reportfile),
                "--output", str(output / "06_model_discovery_audit.json"),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((output / "06_model_discovery_audit.json").exists())


if __name__ == "__main__":
    unittest.main()
