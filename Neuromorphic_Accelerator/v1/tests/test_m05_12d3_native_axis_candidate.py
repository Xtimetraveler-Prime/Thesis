"""Host-only negative audit of M05.12d.3 genuine native AXIS BD refactor.

This does not fabricate original generated Vitis RTL or claim Vivado validation.
Only original owner's offline tool execution can establish the new interface
net and address-discovery readback. Prior accepted scalar graph is preserved.
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
from m05_12d3_hls_connected_preflight import require_new_preflight_output
from m05_12d3_native_axis_candidate_audit import (
    META, DMA, LINKS, CLOCK, RESET, RESET_INT, RESETFEED, RESETDIR,
    RESETCFG, RESETINV, PSCFG, STREAM, CONTROL, MEMORY, NATIVE_INTF,
    NATIVE_PINS, SLAVE_INTERFACES, audit_connected_candidate,
    audit_address_inventory,
)


def graph_fixture() -> str:
    rows = [f"META|{k}|{v}" for k, v in META.items()]
    rows += [f"DMA|{n}|{role}|256|32|24" for n, role in sorted(DMA.items())]
    rows += [f"LINK|{src}|{dst}|intf_{i}"
             for i, (src, dst) in enumerate(sorted(LINKS))]
    rows += [f"NATIVEINTF|{src}|{dst}|native_intf_{i}"
             for i, (src, dst) in enumerate(sorted(NATIVE_INTF))]
    rows += [f"NATIVEPIN|{n}|{direction}|{width}"
             for n, (direction, width) in sorted(NATIVE_PINS.items())]
    rows += ["HLSINTF|s_axi_control|SLAVE"]
    rows += [f"CLK|{name}|one_clock" for name in sorted(CLOCK)]
    rows += [f"RESET|{name}|{'int_reset' if name in RESET_INT else 'per_reset'}"
             for name in sorted(RESET)]
    rows += [f"RESETFEED|{name}|{'pre_inversion' if name in ('ps/pl_resetn0', 'reset_inv/Op1') else 'post_inversion'}"
             for name in sorted(RESETFEED)]
    rows += [f"RESETDIR|{k}|{v}" for k, v in RESETDIR.items()]
    rows += [f"RESETCFG|{k}|{v}" for k, v in RESETCFG.items()]
    rows += [f"RESETINV|{k}|{v}" for k, v in RESETINV.items()]
    rows += [f"PSCFG|{k}|{v}" for k, v in PSCFG.items()]
    return "\n".join(rows) + "\n"


def address_fixture() -> str:
    rows = ["META|scope|OFFLINE_READ_ONLY_VIVADO_ADDRESS_INVENTORY_NOT_DECODE_PROOF"]
    rows += [f"SLAVE|{bank}|{intf}|NO_BD_SEGMENT_YET"
             for bank, intf in SLAVE_INTERFACES.items()]
    rows += ["SPACE|ps/M_AXI_HPM0_FPD|NO_BD_SPACE_YET",
             "META|address_assignment|NOT_RUN",
             "META|physical_ddr|NOT_AUTHORIZED"]
    return "\n".join(rows) + "\n"


class M0512D3NativeAXISCandidateTests(unittest.TestCase):
    def test_preflight_accepts_only_fresh_original_integration_and_native_axis_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            accepted = root / "neuromorphic_v1_m05_12d3_real_hls_contract_accepted"
            accepted.mkdir()
            previous = root / "neuromorphic_v1_m05_12d3_hls_connected_accepted"
            previous.mkdir()
            native = root / "neuromorphic_v1_m05_12d3_native_axis_new"
            native.mkdir()
            path = native / "01_hls_preflight.txt"
            require_new_preflight_output(path)
            require_new_preflight_output(previous / "01_hls_preflight.txt")
            for bad in (
                accepted / "01_hls_preflight.txt",
                root / "01_hls_preflight.txt",
                native / "result.txt",
                native / "source_sha256.txt",
            ):
                with self.subTest(path=bad):
                    with self.assertRaises(ValueError):
                        require_new_preflight_output(bad)
            path.write_text("original owner trial - never overwrite")
            with self.assertRaises(ValueError):
                require_new_preflight_output(path)
            self.assertEqual(path.read_text(), "original owner trial - never overwrite")

    def test_grouped_real_axis_expected_contract(self):
        facts = audit_connected_candidate(graph_fixture())
        self.assertEqual(facts["stream_links"], 4)
        self.assertEqual(facts["control_links"], 7)
        self.assertEqual(facts["independent_control_banks"], 6)
        self.assertEqual(facts["memory_links"], 5)
        self.assertEqual(facts["native_axis_interface_links"], 4)
        self.assertEqual(facts["native_scalar_pin_contracts"], 24)
        self.assertEqual(facts["clock_consumers"], 16)
        self.assertEqual(facts["reset_consumers"], 8)

    def test_reject_missing_duplicate_and_wrong_native_interface(self):
        good = graph_fixture()
        row = next(line for line in good.splitlines(keepends=True)
                   if line.startswith("NATIVEINTF|shell/hls_neuron|"))
        for bad in (
            good.replace(row, "", 1),
            good.replace(row, row * 2, 1),
            good.replace(row, row.replace("hls/neurons|", "hls/trace|"), 1),
            good.replace(row, row.replace("native_intf_", "intf_"), 1),
        ):
            with self.subTest(mutation=bad[:120]):
                with self.assertRaises(ValueError):
                    audit_connected_candidate(bad)

    def test_reject_native_pin_corruption_and_missing_handshake(self):
        good = graph_fixture()
        for pin in ("shell/hls_neuron_tdata", "hls/synapses_TDATA",
                    "hls/trace_TVALID", "shell/hls_trace_tready"):
            row = next(line for line in good.splitlines(keepends=True)
                       if line.startswith(f"NATIVEPIN|{pin}|"))
            for bad in (
                good.replace(row, "", 1),
                good.replace(row, row * 2, 1),
                good.replace(row, row.replace("|O|", "|I|").replace("|I|", "|X|"), 1),
                good.replace(row, row.replace("|128", "|256").replace("|192", "|256").replace("|1\n", "|8\n"), 1),
            ):
                with self.subTest(pin=pin):
                    with self.assertRaises(ValueError):
                        audit_connected_candidate(bad)

    def test_reject_alias_native_axi_and_old_dma_interface(self):
        good = graph_fixture()
        native_row = next(x for x in good.splitlines(keepends=True)
                          if x.startswith("NATIVEINTF|shell/hls_neuron|"))
        old_row = next(x for x in good.splitlines(keepends=True)
                       if x.startswith("LINK|dma_neurons/M_AXIS_MM2S|"))
        old_net = old_row.rstrip("\n").split("|")[-1]
        bad = good.replace(native_row,
                           native_row.rsplit("|", 1)[0] + "|" + old_net + "\n", 1)
        with self.assertRaisesRegex(ValueError, "alias"):
            audit_connected_candidate(bad)

    def test_reject_sixth_bank_missing_clock_reset_or_false_validation(self):
        good = graph_fixture()
        for bad in (
            good.replace("LINK|ctrl_sc/M05_AXI|hls/s_axi_control|", 
                         "LINK|ctrl_sc/M05_AXI|shell/s_axi|", 1),
            good.replace("CLK|hls/ap_clk|one_clock\n", "", 1),
            good.replace("RESET|hls/ap_rst_n|per_reset\n", "", 1),
            good.replace("META|full_bd_validation|NOT_RUN", 
                         "META|full_bd_validation|PASS", 1),
            good.replace("META|address_map|NOT_ASSIGNED",
                         "META|address_map|VIVADO_ASSIGNED", 1),
        ):
            with self.assertRaises(ValueError):
                audit_connected_candidate(bad)

    def test_readonly_address_inventory_accepts_only_six_real_roles(self):
        status = audit_address_inventory(address_fixture())
        self.assertEqual(status["control_slave_banks_inventoried"], 6)
        self.assertEqual(status["slave_segments_exposed"], 0)
        self.assertEqual(status["assigned"], 0)
        example = address_fixture().replace(
            "SLAVE|hls|hls/s_axi_control|NO_BD_SEGMENT_YET",
            "SLAVE|hls|hls/s_axi_control|/hls/s_axi_control/Reg")
        status = audit_address_inventory(example)
        self.assertEqual(status["slave_segments_exposed"], 1)

    def test_owner_six_segment_empty_path_property_regression(self):
        # Actual owner Vivado 2025.2 found six segment objects but
        # get_property PATH recorded six empty strings, not missing objects.
        # The old inventory must FAIL; using actual object path handles is
        # required to pass a schema with all six independent slave regions.
        original = address_fixture()
        failed_inventory = original.replace("NO_BD_SEGMENT_YET", "")
        with self.assertRaisesRegex(ValueError, "invalid address slave segment path"):
            audit_address_inventory(failed_inventory)
        # Only synthetic strings for host tests; ORIGINAL Vivado evidence
        # must supply its own object identities in a fresh rerun.
        mapped = original
        for bank, intf in SLAVE_INTERFACES.items():
            mapped = mapped.replace(
                f"SLAVE|{bank}|{intf}|NO_BD_SEGMENT_YET",
                f"SLAVE|{bank}|{intf}|/{intf}/Reg"
            )
        audit = audit_address_inventory(mapped)
        self.assertEqual(audit["control_slave_banks_inventoried"], 6)
        self.assertEqual(audit["slave_segments_exposed"], 6)
        self.assertEqual(audit["assigned"], 0)

    def test_vivado_tcl_records_real_segment_object_not_empty_path_property(self):
        tcl = (ROOT / "scripts/m05_12d3_native_axis_candidate.tcl").read_text()
        self.assertIn("set candidates [get_bd_addr_segs -quiet -of_objects", tcl)
        self.assertIn("set observed [string trim $segment]", tcl)
        self.assertIn('puts $addrfile "SLAVE|$bank|$interface|$observed"', tcl)
        self.assertNotIn("[get_property PATH $segment]", tcl)
        self.assertIn('![string match "/$bank/*" $observed]', tcl)
        # The existing, immutable failed owner report still records exit 1.
        # This next-stage parser source NEVER changes original HLS/Vivado.
        old = (ROOT / "scripts/m05_12d3_hls_connected_candidate.tcl").read_text()
        self.assertIn("link_hls_native", old)

    def test_readonly_address_inventory_rejects_fabricated_mappings(self):
        good = address_fixture()
        row = "SLAVE|hls|hls/s_axi_control|NO_BD_SEGMENT_YET\n"
        for bad in (
            good.replace(row, "", 1),
            good.replace(row, row * 2, 1),
            good.replace(row, "SLAVE|hls|shell/s_axi|NO_BD_SEGMENT_YET\n", 1),
            good.replace(row, "SLAVE|hls|hls/s_axi_control|/dma_trace/S_AXI_LITE/Reg\n", 1),
            good.replace(row, "SLAVE|hls|hls/s_axi_control|/hls/s_axi_fake/Reg\n", 1),
            good.replace(row, "SLAVE|hls|hls/s_axi_control|/hls/s_axi_control/Reg bad\n", 1),
            good.replace("META|address_assignment|NOT_RUN",
                         "META|address_assignment|ASSIGNED", 1),
            good.replace("META|physical_ddr|NOT_AUTHORIZED",
                         "META|physical_ddr|PASSED", 1),
            good.replace("SPACE|ps/M_AXI_HPM0_FPD|NO_BD_SPACE_YET\n", "", 1),
        ):
            with self.subTest(mutation=bad[:100]):
                with self.assertRaises(ValueError):
                    audit_address_inventory(bad)

    def test_tcl_intf_grouping_not_scalar_overrides_and_runner_guard(self):
        tcl = (ROOT / "scripts/m05_12d3_native_axis_candidate.tcl").read_text()
        runner = ROOT / "scripts/run_m05_12d3_native_axis_candidate.sh"
        run_source = runner.read_text()
        for required in (
            "connect_bd_intf_net $master $slave",
            "foreach {master slave}", "shell/hls_neuron hls/neurons",
            "shell/hls_synapse hls/synapses",
            "shell/hls_external hls/external_events",
            "hls/trace shell/hls_trace",
            "assert_native_pin", "NATIVEPIN|", "NATIVEINTF|",
            "get_bd_addr_segs -quiet -of_objects", "get_bd_addr_spaces -quiet -of_objects",
        ):
            self.assertIn(required, tcl)
        self.assertNotIn("link_hls_native", tcl)
        self.assertNotIn('connect_bd_net $a $b', tcl)
        self.assertIn("grep -Fq 'WARNING: [BD 41-1306]'", run_source)
        self.assertIn("01_hls_preflight.txt", run_source)
        self.assertIn("02_native_axis_graph.txt", run_source)
        self.assertIn("05_read_only_address_inventory.txt", run_source)
        self.assertIn("04_independent_audit.log", run_source)
        for forbidden in ("program_hw_devices", "connect_hw_server",
                          "write_bitstream", "xsdb", "assign_bd_address",
                          "validate_bd_design", "launch_runs", "rm -rf"):
            self.assertNotIn(forbidden, tcl + run_source)
        self.assertEqual(subprocess.run(["bash", "-n", str(runner)],
                         capture_output=True).returncode, 0)

    def test_original_real_hls_scalar_candidate_and_accepted_sources_preserved(self):
        original = (ROOT / "scripts/m05_12d3_hls_connected_candidate.tcl").read_text()
        next_tcl = (ROOT / "scripts/m05_12d3_native_axis_candidate.tcl").read_text()
        self.assertIn("link_hls_native", original)
        self.assertIn("connect_bd_net $a $b", original)
        self.assertIn("CONFIG.NUM_SI 1 CONFIG.NUM_MI 6", next_tcl)
        self.assertIn("mem_sc/M00_AXI ps/S_AXI_HP0_FPD", next_tcl)
        self.assertIn("CONFIG.C_EXT_RESET_HIGH", next_tcl)
        for file in ("hls/m05_rolling/m05_rolling.cpp",
                     "rtl/m05_11/m05_11_stream_shell.v",
                     "rtl/m05_12/m05_12d_axis_shell_ref.v",
                     "scripts/m05_12d3_connected_candidate.tcl"):
            path = ROOT / file
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            audit_connected_candidate(graph_fixture())
            self.assertEqual(sha, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_independent_cli_accepts_good_and_rejects_missing_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            graph, inv = p / "02_native_axis_graph.txt", p / "05_read_only_address_inventory.txt"
            graph.write_text(graph_fixture())
            inv.write_text(address_fixture())
            cli = ROOT / "scripts/m05_12d3_native_axis_candidate_audit.py"
            cmd = [sys.executable, str(cli), "--report", str(graph),
                   "--inventory", str(inv)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("independent grouped native AXIS", result.stdout)
            inv.unlink()
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
