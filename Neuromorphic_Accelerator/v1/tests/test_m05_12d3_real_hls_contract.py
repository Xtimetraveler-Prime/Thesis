"""M05.12d.3 read-only original generated RTL contract: HOST SYNTHETIC tests.

No mock HLS is accepted by Vivado or substituted for the original module.
The generated top is deliberately NOT in Git. A genuine positive gate needs
the operator's retained Vitis and M05.11c XSim artifact files.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d3_real_hls_contract import (
    PORTS, PART, TOP, parse_top_ports, verify_top_contract,
    verify_original_evidence, attest, require_new_evidence_output,
)


def synthetic_declarations() -> str:
    lines = [f"module {TOP} (\n"]
    lines += [f"  {p},\n" for p in PORTS]
    lines += ["  unused);\n"]
    for name, (direction, width) in PORTS.items():
        bitdecl = "" if width == 1 else f"[{width - 1}:0] "
        lines.append(f"  {direction} wire {bitdecl}{name};\n")
    lines += ["  input wire unused;\n", "endmodule\n"]
    return "".join(lines)



def observed_vitis_2025_2_declarations() -> str:
    """Owner's ORIGINAL HLS top declaration syntax (2026-11-09 failed gate).

    Actual 2025.2 source has non-ANSI port names, plain numeric native
    AXIS ranges, and parameterized AXI4-Lite address/data/strobe widths.
    These lines are a host parser regression fixture, NOT replacement RTL.
    """
    source = synthetic_declarations()
    source = source.replace("  input wire unused;\n", "  input wire unused;\n")
    prefix = (
        "parameter C_S_AXI_CONTROL_DATA_WIDTH = 32;\n"
        "parameter C_S_AXI_CONTROL_ADDR_WIDTH = 7;\n"
        "parameter C_S_AXI_DATA_WIDTH = 32;\n"
        "parameter C_S_AXI_CONTROL_WSTRB_WIDTH = (32 / 8);\n"
        "parameter C_S_AXI_WSTRB_WIDTH = (32 / 8);\n"
    )
    source = source.replace("  input wire ap_clk;", prefix + "input ap_clk;")
    for name, width_param in (
        ("s_axi_control_AWADDR", "C_S_AXI_CONTROL_ADDR_WIDTH"),
        ("s_axi_control_ARADDR", "C_S_AXI_CONTROL_ADDR_WIDTH"),
        ("s_axi_control_WDATA", "C_S_AXI_CONTROL_DATA_WIDTH"),
        ("s_axi_control_RDATA", "C_S_AXI_CONTROL_DATA_WIDTH"),
        ("s_axi_control_WSTRB", "C_S_AXI_CONTROL_WSTRB_WIDTH"),
    ):
        direction = PORTS[name][0]
        width = PORTS[name][1]
        source = source.replace(
            f"  {direction} wire [{width - 1}:0] {name};",
            f"{direction}  [{width_param} - 1:0] {name};"
        )
    return source



class M0512D3RealHLSContractTests(unittest.TestCase):
    def test_synthetic_port_parser_matches_accepted_xsim_wiring(self):
        pins = verify_top_contract(synthetic_declarations())
        self.assertEqual(len(PORTS), 32)
        self.assertEqual(pins["s_axi_control_AWADDR"], ("input", 7))
        self.assertEqual(pins["neurons_TDATA"], ("input", 128))
        self.assertEqual(pins["synapses_TDATA"], ("input", 192))
        self.assertEqual(pins["trace_TDATA"], ("output", 192))
        self.assertEqual(pins["trace_TREADY"], ("input", 1))
        self.assertEqual(pins["interrupt"], ("output", 1))

    def test_reject_wrong_native_data_width_and_direction(self):
        good = synthetic_declarations()
        for bad in (
            good.replace("input wire [191:0] synapses_TDATA;",
                         "input wire [255:0] synapses_TDATA;"),
            good.replace("output wire [191:0] trace_TDATA;",
                         "input wire [191:0] trace_TDATA;"),
            good.replace("input wire [127:0] external_events_TDATA;",
                         "input wire [191:0] external_events_TDATA;"),
            good.replace("output wire neurons_TREADY;",
                         "input wire neurons_TREADY;"),
            good.replace("input wire [6:0] s_axi_control_AWADDR;",
                         "input wire [31:0] s_axi_control_AWADDR;"),
        ):
            with self.subTest(invalid=bad[-110:]):
                with self.assertRaises(ValueError):
                    verify_top_contract(bad)

    def test_reject_missing_duplicate_unterminated_or_altered_top(self):
        good = synthetic_declarations()
        for bad in (
            good.replace("input wire ap_clk;", ""),
            good.replace("input wire ap_clk;", "input wire ap_clk;\ninput wire ap_clk;"),
            good.replace("endmodule", ""),
            good.replace("module m05_rolling_replay", "module forged_top"),
            good + good,
        ):
            with self.subTest(invalid=bad[:100]):
                with self.assertRaises(ValueError):
                    verify_top_contract(bad)

    def test_reject_native_axis_sidebands_not_in_verified_hls(self):
        good = synthetic_declarations()
        for extra in ("neurons_TLAST", "synapses_TKEEP",
                      "external_events_TSTRB", "trace_TLAST"):
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError):
                    verify_top_contract(good.replace(
                        "endmodule", f"output wire {extra};\nendmodule"
                    ))

    def test_parse_tolerates_non_ansi_and_ansi_scalar_ports(self):
        good = synthetic_declarations()
        self.assertEqual(parse_top_ports(good)["s_axi_control_RDATA"],
                         ("output", 32))
        self.assertEqual(parse_top_ports(
            "module m05_rolling_replay (\n"
            "  input wire [191:0] trace_TDATA,\n"
            "  output wire trace_TREADY);\nendmodule\n"
        )["trace_TDATA"], ("input", 192))

    def test_owner_observed_vitis_2025_2_parameterized_axi_lite_pins(self):
        # Real 2025.2 top uses C_S_AXI_CONTROL_*_WIDTH expressions.
        source = observed_vitis_2025_2_declarations()
        ports = verify_top_contract(source)
        self.assertEqual(ports["s_axi_control_AWADDR"], ("input", 7))
        self.assertEqual(ports["s_axi_control_ARADDR"], ("input", 7))
        self.assertEqual(ports["s_axi_control_WDATA"], ("input", 32))
        self.assertEqual(ports["s_axi_control_RDATA"], ("output", 32))
        self.assertEqual(ports["s_axi_control_WSTRB"], ("input", 4))
        self.assertEqual(ports["synapses_TDATA"], ("input", 192))
        self.assertEqual(ports["trace_TDATA"], ("output", 192))

    def test_parameterized_width_mismatch_not_silently_accepted(self):
        source = observed_vitis_2025_2_declarations()
        for original, wrong in (
            ("C_S_AXI_CONTROL_ADDR_WIDTH = 7",
             "C_S_AXI_CONTROL_ADDR_WIDTH = 8"),
            ("C_S_AXI_CONTROL_DATA_WIDTH = 32",
             "C_S_AXI_CONTROL_DATA_WIDTH = 64"),
            ("C_S_AXI_CONTROL_WSTRB_WIDTH = (32 / 8)",
             "C_S_AXI_CONTROL_WSTRB_WIDTH = (64 / 8)"),
            ("C_S_AXI_CONTROL_ADDR_WIDTH = 7",
             "C_S_AXI_CONTROL_ADDR_WIDTH = 0"),
        ):
            with self.subTest(mutation=wrong):
                with self.assertRaises(ValueError):
                    verify_top_contract(source.replace(original, wrong, 1))

    def test_reject_unknown_duplicate_cyclic_and_unsafe_vitis_parameters(self):
        source = observed_vitis_2025_2_declarations()
        for original, wrong in (
            ("C_S_AXI_CONTROL_ADDR_WIDTH = 7",
             "C_S_AXI_CONTROL_ADDR_WIDTH = UNKNOWN_AXI_WIDTH"),
            ("C_S_AXI_CONTROL_ADDR_WIDTH = 7",
             "C_S_AXI_CONTROL_ADDR_WIDTH = C_S_AXI_CONTROL_ADDR_WIDTH"),
            ("C_S_AXI_CONTROL_WSTRB_WIDTH = (32 / 8)",
             "C_S_AXI_CONTROL_WSTRB_WIDTH = (32 / 0)"),
            ("C_S_AXI_CONTROL_WSTRB_WIDTH = (32 / 8)",
             "C_S_AXI_CONTROL_WSTRB_WIDTH = (33 / 8)"),
            ("C_S_AXI_CONTROL_ADDR_WIDTH = 7",
             "C_S_AXI_CONTROL_ADDR_WIDTH = __import__('os').system('true')"),
            ("C_S_AXI_CONTROL_ADDR_WIDTH = 7",
             "C_S_AXI_CONTROL_ADDR_WIDTH = 7;\nparameter C_S_AXI_CONTROL_ADDR_WIDTH = 7"),
        ):
            with self.subTest(wrong=wrong):
                with self.assertRaises(ValueError):
                    verify_top_contract(source.replace(original, wrong, 1))

    def test_reject_missing_or_duplicated_hls_header_port(self):
        source = observed_vitis_2025_2_declarations()
        with self.assertRaises(ValueError):
            verify_top_contract(source.replace("  s_axi_control_AWADDR,\n", "", 1))
        with self.assertRaises(ValueError):
            verify_top_contract(source.replace("  s_axi_control_AWADDR,\n",
                                               "  s_axi_control_AWADDR,\n"
                                               "  s_axi_control_AWADDR,\n", 1))

    def test_refuses_unaccepted_or_missing_real_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xsim = root / "neuromorphic_v1_m05_11c_real_hls_fake"
            xsim.mkdir()
            source = root / "source.cpp"
            source.write_text("unchanged")
            (xsim / "result.txt").write_text("exit_status=1\n")
            (xsim / "source_impl_evidence.txt").write_text(
                "/nonexistent/neuromorphic_v1_m05_rolling_impl_test\n")
            with self.assertRaisesRegex(ValueError, "not accepted"):
                verify_original_evidence(xsim, source)
            (xsim / "result.txt").write_text("exit_status=0\n")
            with self.assertRaisesRegex(ValueError, "raw-frame PASS missing"):
                verify_original_evidence(xsim, source)
            (xsim / "05_dma_frame_replay.log").write_text(
                "PASS: M05.11c raw 256-bit RTL DMA transcript replay\n"
            )
            with self.assertRaises(OSError):
                attest(xsim, source)

    def test_exact_source_hls_hash_and_safe_local_artifact_runner(self):
        path = ROOT / "scripts/run_m05_12d3_real_hls_contract.sh"
        script = path.read_text()
        python = (ROOT / "scripts/m05_12d3_real_hls_contract.py").read_text()
        for required in (
            "source_impl_evidence.txt", "source_sha256.txt",
            'TOP + "_control_s_axi.v"', "find_generated_register_map",
            "parse_control_verilog", "sha256", "ORIGINAL_SIGNED32",
            "NOT_AUTHORIZED", "PORTS",
        ):
            self.assertIn(required, python)
        for marker in ("commit.txt", "working_tree_status.txt",
                       "source_sha256.txt", "result.txt",
                       "01_original_hls_contract.txt", "02_attestation.log",
                       "mktemp -d", "source_xsim_evidence.txt"):
            self.assertIn(marker, script)
        for unsafe in ("open_hw_target", "program_hw_devices",
                       "connect_hw_server", "write_bitstream", "xsdb",
                       "vivado -mode", "vitis_hls", "rm -rf"):
            self.assertNotIn(unsafe, script)
            self.assertNotIn(unsafe, python)
        result = subprocess.run(["bash", "-n", str(path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior = root / "neuromorphic_v1_m05_11c_real_hls_ACCEPTED"
            prior.mkdir()
            new = root / "neuromorphic_v1_m05_12d3_real_hls_contract_UTC_ABC"
            new.mkdir()
            name = "01_original_hls_contract.txt"
            with self.assertRaisesRegex(ValueError, "NEW D3"):
                require_new_evidence_output(prior / name)
            require_new_evidence_output(new / name)
            with self.assertRaisesRegex(ValueError, "NEW D3"):
                require_new_evidence_output(new / "result.txt")
            self.assertEqual(list(new.iterdir()), [])
            self.assertEqual(list(prior.iterdir()), [])

    def test_no_original_engine_or_prior_d3_graph_mutation(self):
        accepted = (
            ROOT / "scripts/m05_12d3_connected_candidate.tcl",
            ROOT / "scripts/m05_12d3_connected_candidate_audit.py",
            ROOT / "hls/m05_rolling/m05_rolling.cpp",
            ROOT / "rtl/m05_11/m05_11_stream_shell.v",
        )
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in accepted]
        verify_top_contract(synthetic_declarations())
        self.assertEqual(hashes,
                         [hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in accepted])
        self.assertEqual(PART, "xck26-sfvc784-2LV-c")


if __name__ == "__main__":
    unittest.main()
