"""M05 D4.1b SYNTHETIC positive/negative read-only owner-BD property tests.

NO fake Vivado execution. Genuine D3/.gen material exists only with owner.
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
from m05_12d4_readonly_bd_audit import (
    CELLS, ENDPOINTS, PAIRS, PROPS, SCOPE, SUCCESS, TAIL, WIDTHS,
    parse, verify_original_and_inventory, witnessed_ocm_exclusion,
)
from m05_12d4_generated_hierarchy_index import token_hints


def fixture(root: Path) -> str:
    original = root.resolve()
    xpr = original / "13_file_backed_project/m05_d3_output_products.xpr"
    bdname = "m05_12d3_real_signed32_hls_six_control_address_candidate"
    bd = original / ("13_file_backed_project/m05_d3_output_products.srcs/"
                     "sources_1/bd/" + bdname + "/" + bdname + ".bd")
    lines = [SCOPE, "PROJECT|" + str(xpr), "BD|" + str(bd)]
    lines.extend(f"CELL|{c}|{p}|{v}" for c, p, v in CELLS)
    wires = {name: f"unique_{idx}" for idx, pair in enumerate(PAIRS) for name in pair}
    for endpoint in ENDPOINTS:
        lines.append(f"NET|{endpoint}|{wires.get(endpoint, 'ctrl_input_only')}")
        for prop in PROPS:
            value = "32" if prop == "CONFIG.DATA_WIDTH" else "0"
            if prop == "CONFIG.PROTOCOL":
                value = "AXI4"
            if prop == "CONFIG.DATA_WIDTH" and endpoint in WIDTHS:
                value = str(WIDTHS[endpoint])
            lines.append(f"IFACE|{endpoint}|{prop}|{value}")
    lines.extend(TAIL)
    return "\n".join(lines) + "\n"


class D4ReadonlyBDTests(unittest.TestCase):
    def test_exact_23_interface_readback_and_11_unique_bidirectional_connections(self):
        with tempfile.TemporaryDirectory() as d:
            result = parse(fixture(Path(d)), Path(d))
            self.assertEqual(result["endpoints"], 23)
            self.assertEqual(len(result["interface_nets"]), 23)
            self.assertEqual(result["memory_readback_widths"], WIDTHS)
            self.assertEqual(result["smartconnect"]["ctrl_sc"], {"si": 1, "mi": 6})
            self.assertEqual(result["smartconnect"]["mem_sc"], {"si": 4, "mi": 1})
            self.assertEqual(result["protocol_integrity"],
                             "BLOCKED_UNTIL_GENERATED_ADAPTER_FUNCTIONAL_EVIDENCE")
            self.assertEqual(result["sideband_property_disagreements"], [])

    def test_reject_missing_duplicate_or_corrupted_required_endpoint_properties(self):
        with tempfile.TemporaryDirectory() as d:
            good = fixture(Path(d))
            bad_rows = [
                good.replace("IFACE|mem_sc/M00_AXI|CONFIG.DATA_WIDTH|128",
                             "IFACE|mem_sc/M00_AXI|CONFIG.DATA_WIDTH|256"),
                good.replace("IFACE|mem_sc/S02_AXI|CONFIG.ID_WIDTH|0",
                             "IFACE|mem_sc/S02_AXI|CONFIG.FREQ_HZ|0"),
                good.replace("IFACE|ps/S_AXI_HP0_FPD|CONFIG.ARUSER_WIDTH|0\n", ""),
                good.replace("NET|ctrl_sc/M05_AXI|", "NET|unknown/FIFO|"),
                good.replace(SCOPE, "META|scope|FAKE"),
                good + "FORGED|PASS\n",
                good[:-1],
                good.replace("META|physical_board|NOT_AUTHORIZED",
                             "META|physical_board|PASS"),
            ]
            for i, bad in enumerate(bad_rows):
                with self.subTest(case=i), self.assertRaises(ValueError):
                    parse(bad, Path(d))

    def test_net_pair_splits_and_aliases_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            good = fixture(Path(d))
            broken = good.replace("NET|mem_sc/S00_AXI|unique_0",
                                  "NET|mem_sc/S00_AXI|different")
            with self.assertRaisesRegex(ValueError, "split"):
                parse(broken, Path(d))
            merged = good.replace("NET|mem_sc/M00_AXI|unique_4",
                                  "NET|mem_sc/M00_AXI|unique_0").replace(
                                  "NET|ps/S_AXI_HP0_FPD|unique_4",
                                  "NET|ps/S_AXI_HP0_FPD|unique_0")
            with self.assertRaisesRegex(ValueError, "share"):
                parse(merged, Path(d))

    def test_axi_user_id_disagreement_is_explicit_blocker_not_waiver(self):
        with tempfile.TemporaryDirectory() as d:
            good = fixture(Path(d))
            mutated = good.replace(
                "IFACE|ps/S_AXI_HP0_FPD|CONFIG.AWUSER_WIDTH|0",
                "IFACE|ps/S_AXI_HP0_FPD|CONFIG.AWUSER_WIDTH|1",
            )
            parsed = parse(mutated, Path(d))
            diff = parsed["sideband_property_disagreements"]
            self.assertEqual(len(diff), 1)
            self.assertEqual(diff[0]["a"], "mem_sc/M00_AXI")
            self.assertEqual(diff[0]["b"], "ps/S_AXI_HP0_FPD")
            self.assertEqual(diff[0]["property"], "CONFIG.AWUSER_WIDTH")
            self.assertEqual(diff[0]["classification"],
                             "UNRESOLVED_NEEDS_AXI_FIELD_PROOF")
            self.assertIn("BLOCKED", parsed["protocol_integrity"])

    def test_ocm_1629_only_classifies_with_original_four_exclusions(self):
        synthetic = [{
            "id": "BD 41-1629", "line": 774,
            "message": "Slave segment </ps/SAXIGP2/HP0_LPS_OCM> is excluded from all addressing paths.",
        }]
        dma = {"dma_ocm_excluded": 4, "dma_ddr_low_mapped": 4}
        genuine_marker_shape = (
            "PASS: M05.12d.3 four authentic DDR_LOW address mappings and "
            "four excluded OCM segments independently audited "
            "{'dma_ddr_low_mapped': 4, 'dma_ocm_excluded': 4} SYNTHETIC ONLY")
        observed = witnessed_ocm_exclusion(synthetic, dma, genuine_marker_shape)
        self.assertEqual(observed["original_log_line"], 774)
        self.assertEqual(observed["classification"],
                         "DOCUMENTED_INTENTIONAL_OCM_EXCLUSION_ONLY")
        self.assertEqual(observed["axi_payload_semantics"],
                         "NOT_IMPLIED_BY_OCM_EXCLUSION")
        for warnings, summary, log in (
            (synthetic + synthetic, dma, genuine_marker_shape),
            (synthetic, {"dma_ocm_excluded": 3, "dma_ddr_low_mapped": 4}, genuine_marker_shape),
            (synthetic, dma, "SYNTHETIC but no original independent PASS"),
            ([dict(synthetic[0], message="OCM unrelated warning")], dma, genuine_marker_shape),
        ):
            with self.subTest(warnings=warnings, summary=summary), self.assertRaises(ValueError):
                witnessed_ocm_exclusion(warnings, summary, log)


    def test_missing_original_d3_or_d4_attestation_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((ValueError, OSError)):
                verify_original_and_inventory(Path(d), Path(d) / "02_warning_inventory.json")

    def test_generated_file_token_hints_never_prove_ip_parent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ctrl = root / "ctrl_sc_unit.v"
            mem = root / "mem_sc_unit.v"
            ctrl.write_text("module dummy; m05_aw_node S_SC_AW_payld; endmodule")
            mem.write_text("module dummy; m05_aw_node S_SC_AW_payld; endmodule")
            paths = [(p.name, p, hashlib.sha256(p.read_bytes()).hexdigest())
                     for p in (ctrl, mem)]
            warn = dict(id="BD 41-2384", line=10,
                        source_pin="/m05_nodes/m05_aw_node/s_sc_payld",
                        destination_pin="/m05_nodes/S_SC_AW_payld",
                        source_width=172, destination_width=168,
                        narrowed_bits=4)
            hints = token_hints([warn], paths)
            self.assertEqual(len(hints), 1)
            self.assertEqual(hints[0]["generated_parent_attribution"], "NOT_ESTABLISHED")
            parents = {w["file_parent_hint"] for w in hints[0]["candidate_vendor_files"]}
            self.assertEqual(parents, {"ctrl_sc", "mem_sc"})
            self.assertEqual(hints[0]["packed_axi_payload_fields"], "NOT_ESTABLISHED")
            self.assertEqual(token_hints([dict(warn, source_pin=None,
                                               destination_pin=None)], paths)[0]["tokens_searched"], [])

    def test_readonly_vivado_tcl_reports_actual_interfaces_not_requested_values(self):
        path = ROOT / "scripts/m05_12d4_readonly_bd_properties.tcl"
        script = path.read_text()
        for expected in (
            "open_project -read_only $xpr", "open_bd_design [lindex $actual_bd 0]",
            "get_bd_intf_pins -quiet $endpoint", "get_bd_intf_nets -quiet -of_objects $pin",
            "CONFIG.AWUSER_WIDTH", "CONFIG.ARUSER_WIDTH", "CONFIG.BUSER_WIDTH",
            "CONFIG.RUSER_WIDTH", "CONFIG.ID_WIDTH", "CONFIG.MAX_BURST_LENGTH",
            "CONFIG.HAS_WSTRB", "CONFIG.DATA_WIDTH",
            "M05_D4_READ_ONLY_BD_PROPERTIES_PASS",
            "get_property $prop $pin", "CONFIG.NUM_SI", "CONFIG.NUM_MI"):
            self.assertIn(expected, script)
        self.assertEqual(script.count("generate_target"), 0)  # no IP regeneration
        for forbidden in ("save_bd_design", "create_bd_cell", "connect_bd_intf_net",
                          "assign_bd_address", "launch_runs", "synth_design",
                          "write_bitstream", "open_hw_target", "program_hw_devices",
                          "connect_hw_server", "xsdb", "system", "exec"):
            self.assertNotIn(forbidden, script)

    def test_runner_immutable_provenance_and_readonly_safety(self):
        runner = ROOT / "scripts/run_m05_12d4_readonly_bd_probe.sh"
        data = runner.read_text()
        for marker in ("mktemp -d", "source_sha256.txt",
                       "07_source_sha256_after.txt", "cmp -s",
                       "05_generated_hierarchy_hints.json",
                       "06_independent_bd_audit.json",
                       "04_vivado_readonly.log", "exit 3", "result.txt"):
            self.assertIn(marker, data)
        for forbidden in ("write_bitstream", "open_hw_target", "program_hw_devices",
                          "connect_hw_server", "xsdb", "rm -rf", "synth_design",
                          "generate_target all", "save_bd_design"):
            self.assertNotIn(forbidden, data)
        self.assertEqual(subprocess.run(["bash", "-n", str(runner)],
                         capture_output=True).returncode, 0)

    def test_replay_parser_cli_refuses_fake_owner_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outdir = root / "neuromorphic_v1_m05_12d4_readonly_bd_SYNTHETIC"
            outdir.mkdir()
            report = outdir / "03_bd_interface_properties.txt"
            report.write_text(fixture(root))
            log = outdir / "04_vivado_readonly.log"
            log.write_text(SUCCESS + "\nSYNTHETIC NOT VIVADO\n")
            output = outdir / "06_independent_bd_audit.json"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/m05_12d4_readonly_bd_audit.py"),
                "--original-d3", str(root),
                "--previous-d4", str(root / "missing"),
                "--bd-report", str(report), "--vivado-log", str(log),
                "--output", str(output),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("FAIL:", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
