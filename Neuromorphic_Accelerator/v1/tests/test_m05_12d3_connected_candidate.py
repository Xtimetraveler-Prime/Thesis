"""M05.12d.3 single integrated OFFLINE graph candidate, synthetic host tests.

No HLS generated RTL is in Git; report truthfully marks sixth AXI-Lite
control bank, addresses, full BD validation, and DDR as NOT done.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d3_connected_candidate_audit import (
    META, DMA, STREAM, CONTROL, MEMORY, CLOCK, RESET, RESET_INT,
    RESET_PER, RESETFEED, RESETCFG, PSCFG, audit_connected_candidate,
)


def transcript() -> str:
    rows = [f"META|{k}|{v}" for k, v in META.items()]
    for name, role in sorted(DMA.items()):
        rows.append(f"DMA|{name}|{role}|256|32|24")
    for n, (src, dst) in enumerate(sorted(STREAM | CONTROL | MEMORY)):
        rows.append(f"LINK|{src}|{dst}|net_{n:02d}")
    for pin in sorted(CLOCK):
        rows.append(f"CLK|{pin}|pl_clk_net")
    for pin in sorted(RESET):
        net = "int_reset_net" if pin in RESET_INT else "per_reset_net"
        rows.append(f"RESET|{pin}|{net}")
    for pin in sorted(RESETFEED):
        rows.append(f"RESETFEED|{pin}|ps_resetn_net")
    for key, value in RESETCFG.items():
        rows.append(f"RESETCFG|{key}|{value}")
    for key, value in PSCFG.items():
        rows.append(f"PSCFG|{key}|{value}")
    return "\n".join(rows) + "\n"


class M0512D3ConnectedCandidateTests(unittest.TestCase):
    def test_exact_stream_control_memory_and_clock_reset_graph(self):
        facts = audit_connected_candidate(transcript())
        self.assertEqual(facts, {
            "stream_links": 4, "control_links": 6, "memory_links": 5,
            "clock_consumers": 15, "reset_consumers": 7,
            "reset_input_pins": 2,
        })

    def test_sixth_hls_control_is_not_faked_and_addresses_unassigned(self):
        src = transcript()
        for marker in (
            "META|hls_control|MISSING_GENERATED_RTL",
            "META|address_map|NOT_ASSIGNED",
            "META|full_bd_validation|NOT_RUN",
            "META|data_width_conversion|SMARTCONNECT_CANDIDATE_NOT_GENERATED",
        ):
            self.assertIn(marker, src)
        for marker in (
            ("MISSING_GENERATED_RTL", "READY"),
            ("NOT_ASSIGNED", "ASSIGNED"),
            ("NOT_RUN", "PASS"),
            ("SMARTCONNECT_CANDIDATE_NOT_GENERATED", "VERIFIED"),
        ):
            with self.subTest(marker=marker):
                with self.assertRaises(ValueError):
                    audit_connected_candidate(src.replace(*marker))

    def test_wrong_or_missing_axilite_and_memory_fabric_links_rejected(self):
        src = transcript()
        for wrong in (
            "LINK|ctrl_sc/M04_AXI|shell/s_axi|",
            "LINK|ps/M_AXI_HPM0_FPD|ctrl_sc/S00_AXI|",
            "LINK|dma_neurons/M_AXI_MM2S|mem_sc/S00_AXI|",
            "LINK|mem_sc/M00_AXI|ps/S_AXI_HP0_FPD|",
            "LINK|shell/M_AXIS_TRACE|dma_trace/S_AXIS_S2MM|",
        ):
            row = next(row for row in src.splitlines(keepends=True)
                       if row.startswith(wrong))
            for mutated in (
                src.replace(row, "", 1),
                src.replace(row, row * 2, 1),
                src.replace(row, row.replace("|" + wrong.split("|")[2] + "|",
                                            "|wrong_destination|", 1), 1),
            ):
                with self.subTest(row=wrong, mutated=mutated[-100:]):
                    with self.assertRaises(ValueError):
                        audit_connected_candidate(mutated)

    def test_wrong_net_uniqueness_and_clock_reset_grouping_rejected(self):
        src = transcript()
        lines = src.splitlines(keepends=True)
        links = [i for i, line in enumerate(lines) if line.startswith("LINK|")]
        lines[links[0]] = lines[links[0]].rsplit("|", 1)[0] + "|" + lines[links[1]].rsplit("|", 1)[1]
        with self.assertRaises(ValueError):
            audit_connected_candidate("".join(lines))
        original_clock = "CLK|ps/maxihpm0_fpd_aclk|pl_clk_net"
        with self.assertRaises(ValueError):
            audit_connected_candidate(src.replace(original_clock,
                                                 original_clock.replace("pl_clk_net", "other_clock")))
        original_reset = "RESET|shell/rst_n|per_reset_net"
        with self.assertRaises(ValueError):
            audit_connected_candidate(src.replace(original_reset,
                                                 original_reset.replace("per_reset_net", "int_reset_net")))
        with self.assertRaises(ValueError):
            audit_connected_candidate(src.replace("RESET|ctrl_sc/aresetn|int_reset_net",
                                                 "RESET|ctrl_sc/aresetn|per_reset_net"))

    def test_owner_d3_missing_axis_clock_regression_and_reset_polarity(self):
        # Original Vivado source failed on absent DMA scalar pin
        # dma_neurons/m_axis_mm2s_aclk. PG021 uses m_axi_mm2s_aclk
        # for both memory and stream; separate AXIS clocks are AXI VDMA.
        src = (ROOT / "scripts/m05_12d3_connected_candidate.tcl").read_text()
        auditor = (ROOT / "scripts/m05_12d3_connected_candidate_audit.py").read_text()
        self.assertIn('lappend clocks "$name/m_axi_mm2s_aclk"', src)
        self.assertIn('lappend clocks "dma_trace/m_axi_s2mm_aclk"', src)
        self.assertNotIn('lappend clocks "$name/m_axis_mm2s_aclk"', src)
        self.assertNotIn('lappend clocks "dma_trace/s_axis_s2mm_aclk"', src)
        self.assertNotIn('CLOCK.add(f"{dma}/m_axis_mm2s_aclk")', auditor)
        self.assertNotIn('CLOCK.add("dma_trace/s_axis_s2mm_aclk")', auditor)
        self.assertNotIn("dma_neurons/m_axis_mm2s_aclk", CLOCK)
        self.assertNotIn("dma_trace/s_axis_s2mm_aclk", CLOCK)
        self.assertEqual(len(CLOCK), 15)
        self.assertIn("set_property CONFIG.C_EXT_RESET_HIGH 0 $reset", src)
        self.assertIn("get_property CONFIG.C_EXT_RESET_HIGH $reset", src)
        self.assertIn('lappend report "RESETCFG|C_EXT_RESET_HIGH|', src)
        self.assertEqual(audit_connected_candidate(transcript())["reset_input_pins"], 2)
        for invalid in (
            transcript().replace("RESETCFG|C_EXT_RESET_HIGH|0",
                                 "RESETCFG|C_EXT_RESET_HIGH|1", 1),
            transcript().replace("RESETFEED|pl_reset/ext_reset_in|ps_resetn_net",
                                 "RESETFEED|pl_reset/ext_reset_in|wrong_reset_net", 1),
            transcript().replace("RESETFEED|ps/pl_resetn0|ps_resetn_net",
                                 "RESETFEED|ps/pl_resetn0|pl_clk_net", 1),
            transcript().replace("RESETFEED|ps/pl_resetn0|ps_resetn_net\\n", "", 1),
        ):
            with self.subTest(invalid=invalid[-100:]):
                with self.assertRaises(ValueError):
                    audit_connected_candidate(invalid)

    def test_proven_owner_dma_width_part_and_vlnv_values_enforced(self):
        src = transcript()
        for bad in (
            src.replace("META|part|xck26-sfvc784-2LV-c", "META|part|xczu9eg", 1),
            src.replace("META|ps_vlnv|xilinx.com:ip:zynq_ultra_ps_e:3.5",
                        "META|ps_vlnv|xilinx.com:ip:ps7:5.0", 1),
            src.replace("DMA|dma_trace|S2MM|256|32|24",
                        "DMA|dma_trace|MM2S|256|32|24", 1),
            src.replace("DMA|dma_neurons|MM2S|256|32|24",
                        "DMA|dma_neurons|MM2S|128|32|24", 1),
            src.replace("PSCFG|PSU__SAXIGP2__DATA_WIDTH|128",
                        "PSCFG|PSU__SAXIGP2__DATA_WIDTH|256", 1),
            src.replace("META|scope|OFFLINE_PS_DMA_SHELL_INTERCONNECT_CANDIDATE_NO_HLS_OR_ADDRESSES",
                        "META|scope|PHYSICAL_DDR_PASS", 1),
        ):
            with self.subTest(bad=bad[:80]):
                with self.assertRaises(ValueError):
                    audit_connected_candidate(bad)

    def test_missing_truncated_unknown_duplicate_records_fail_closed(self):
        src = transcript()
        for bad in (
            src[:-1],
            src + "VALIDATE|PASS|physical\n",
            src + "CLK|shell/clk|pl_clk_net\n",
            src.replace("RESET|shell/rst_n|per_reset_net\n", "", 1),
            src.replace("PSCFG|PSU__MAXIGP0__DATA_WIDTH|128\n", "", 1),
            src.replace("META|address_map|NOT_ASSIGNED\n", "", 1),
        ):
            with self.subTest(bad=bad[-100:]):
                with self.assertRaises(ValueError):
                    audit_connected_candidate(bad)

    def test_python_cli_is_read_only_and_rejects_missing_evidence(self):
        with tempfile.TemporaryDirectory(prefix="m05_12d3_") as temp:
            report = Path(temp) / "01_connected_graph.txt"
            contents = transcript()
            report.write_text(contents)
            cmd = [sys.executable, str(ROOT / "scripts/m05_12d3_connected_candidate_audit.py"),
                   "--report", str(report)]
            good = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("PASS: M05.12d.3 independent", good.stdout)
            self.assertEqual(report.read_text(), contents)
            report.unlink()
            bad = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("ERROR: M05.12d.3", bad.stderr)

    def test_offline_shell_dma_ps_smartconnect_real_link_readback_and_safety(self):
        tcl = (ROOT / "scripts/m05_12d3_connected_candidate.tcl").read_text()
        shpath = ROOT / "scripts/run_m05_12d3_connected_candidate.sh"
        sh = shpath.read_text()
        for required in (
            "create_project -in_memory", "source_mgmt_mode All",
            "xilinx.com:ip:smartconnect:1.0",
            "xilinx.com:ip:proc_sys_reset:5.0",
            "xilinx.com:ip:axi_dma:7.1",
            "m05_12d_axis_shell_ref", "CONFIG.PSU__USE__M_AXI_GP0 1",
            "CONFIG.PSU__USE__S_AXI_GP2 1", "CONFIG.NUM_SI 4 CONFIG.NUM_MI 1",
            "CONFIG.NUM_SI 1 CONFIG.NUM_MI 5",
            "get_bd_intf_nets -of_objects", "get_bd_intf_pins -of_objects",
            "connect_bd_intf_net", "connect_bd_net",
            "ps/M_AXI_HPM0_FPD ctrl_sc/S00_AXI",
            "mem_sc/M00_AXI ps/S_AXI_HP0_FPD",
            'format "ctrl_sc/M%02d_AXI" $index', "4 shell/s_axi",
            "pl_reset/peripheral_aresetn", "pl_reset/interconnect_aresetn",
            "get_bd_nets -of_objects",
            "META|hls_control|MISSING_GENERATED_RTL",
        ):
            self.assertIn(required, tcl)
        for required in (
            "commit.txt", "source_sha256.txt", "result.txt",
            "01_connected_graph.txt", "02_vivado.log",
            "03_independent_audit.log", "working_tree_status.txt",
        ):
            self.assertIn(required, sh)
        for forbidden in (
            "open_hw_target", "connect_hw_server", "program_hw_devices",
            "launch_runs", "write_bitstream", "open_project",
            "apply_bd_automation", "assign_bd_address", "validate_bd_design",
            "xsdb", "rm -rf", "connect_bd_intf_net ps/S_AXI_HP0_FPD ps/M_AXI_HPM0_FPD",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, tcl)
                self.assertNotIn(forbidden, sh)
        syntax = subprocess.run(["bash", "-n", str(shpath)],
                                capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        help_run = subprocess.run(["bash", str(shpath), "--help"],
                                  capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("NO BOARD", help_run.stdout)
        bad = subprocess.run(["bash", str(shpath), "--physical"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
