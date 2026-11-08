"""M05 direct RTL-stall gate: source-only tests, NOT a real XSim result.

The actual generated-IP AXIS handshake test must be executed on the operator
Vitis/Vivado 2025.2 workstation using the completed `--rolling --impl` run.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_axis_regmap import (
    REQUIRED, find_header, find_generated_register_map, format_svh,
    parse_registers, parse_control_verilog,
)

EXAMPLE = {
    "AP_CTRL": 0,
    "AP_RETURN": 16,
    "NEURON_COUNT_DATA": 24,
    "SYNAPSE_COUNT_DATA": 32,
    "EXTERNAL_COUNT_DATA": 40,
    "TICKS_DATA": 48,
    "DECAY_NUM_DATA": 56,
    "DECAY_DEN_DATA": 64,
}


def test_header(mapping=EXAMPLE):
    return "\n".join(f"#define XM05_ROLLING_REPLAY_CONTROL_ADDR_{k} "
                     f"0x{v:02x}" for k, v in mapping.items()) + "\n"


class M05RTLStallPrepTests(unittest.TestCase):
    def test_register_map_from_realistic_2025_2_header(self):
        self.assertEqual(parse_registers(test_header()), EXAMPLE)
        result = format_svh(EXAMPLE)
        self.assertIn("`define M05_ADDR_NEURON_COUNT_DATA 7'h18", result)
        self.assertIn("`define M05_ADDR_AP_RETURN 7'h10", result)

    def test_missing_required_address_is_fail_closed(self):
        bad = EXAMPLE.copy()
        del bad["DECAY_DEN_DATA"]
        with self.assertRaisesRegex(ValueError, "missing|lacks"):
            parse_registers(test_header(bad))

    def test_colliding_address_is_rejected(self):
        bad = EXAMPLE.copy()
        bad["AP_RETURN"] = bad["AP_CTRL"]
        with self.assertRaisesRegex(ValueError, "collide"):
            parse_registers(test_header(bad))

    def test_out_of_range_or_unaligned_address_rejected(self):
        for addr in (128, 19, -4):
            with self.subTest(addr=addr):
                bad = EXAMPLE.copy()
                bad["DECAY_DEN_DATA"] = addr
                source = test_header(bad) if addr >= 0 else test_header(
                    {**EXAMPLE, "DECAY_DEN_DATA": 0x80})
                with self.assertRaisesRegex(ValueError, "7-bit|collide"):
                    parse_registers(source)

    def test_duplicate_address_macro_fails_closed(self):
        lines = test_header()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_registers(lines + lines.splitlines()[0] + "\n")

    def test_header_discovery_deduplicates_consistent_versions(self):
        with tempfile.TemporaryDirectory(prefix="m05_axi_regmap_") as td:
            root = Path(td)
            for name in ("a", "b"):
                p = root / "work" / name / "xm05_rolling_replay_hw.h"
                p.parent.mkdir(parents=True)
                p.write_text(test_header())
            self.assertEqual(find_header(root).name, "xm05_rolling_replay_hw.h")

    def test_header_discovery_rejects_conflicting_versions(self):
        with tempfile.TemporaryDirectory(prefix="m05_axi_regmap_") as td:
            root = Path(td)
            a = root / "work/a/xm05_rolling_replay_hw.h"
            a.parent.mkdir(parents=True)
            a.write_text(test_header())
            b = root / "work/b/xm05_rolling_replay_hw.h"
            b.parent.mkdir(parents=True)
            new = EXAMPLE.copy()
            new["TICKS_DATA"] = 72
            b.write_text(test_header(new))
            with self.assertRaisesRegex(ValueError, "conflicting"):
                find_header(root)

    def test_cli_refuses_to_overwrite_generated_regmap(self):
        with tempfile.TemporaryDirectory(prefix="m05_axi_regmap_") as td:
            root = Path(td)
            p = root / "work/drivers/xm05_rolling_replay_hw.h"
            p.parent.mkdir(parents=True)
            p.write_text(test_header())
            out = root / "test.svh"
            tool = ROOT / "scripts/m05_axis_regmap.py"
            command = [sys.executable, str(tool),
                       "--impl-evidence", str(root), "--output", str(out)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = out.read_text()
            self.assertIn("PASS: derived", first.stdout)
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(out.read_text(), original)

    def test_stressbench_forces_real_tready_low_and_checks_handshake(self):
        tb = (ROOT / "hls/m05_rolling/rtl_stress/"
              "tb_m05_rolling_axis_stress.sv").read_text()
        for required in ("m05_rolling_replay dut (", "trace_TVALID",
                         "trace_TREADY", "trace_TDATA",
                         "stalled_trace_prior", "prior_trace_word",
                         "RTL_STRESS_FAIL", "PASS: M05 REAL RTL AXIS stall stress",
                         "`M05_ADDR_AP_RETURN", "trace_received == 24"):
            with self.subTest(required=required):
                self.assertIn(required, tb)
        self.assertIn("cycle_count % 11 == 0", tb)
        self.assertNotIn("force dut", tb)  # normal AXIS pins only

    def test_safe_runner_uses_unique_evidence_and_source_identity_check(self):
        runner = (ROOT / "scripts/run_m05_rolling_rtl_stress.sh").read_text()
        for required in ("mkdir \"$OUT\"", "source_sha256.txt",
                         "hls_src_hash", "current_src_hash", "xvlog", "xelab",
                         "xsim", "timeout", "04_xsim.log", "result.txt",
                         "PASS: M05 REAL RTL AXIS stall stress"):
            with self.subTest(required=required):
                self.assertIn(required, runner)
        self.assertNotIn("program_hw_devices", runner)
        self.assertNotIn("rm -rf", runner)

    def test_rtl_only_control_s_axi_parameter_fallback(self):
        # package.output.format=rtl skips packaging a software driver.
        # The generated Verilog itself is the register map authority.
        values = {**EXAMPLE}
        lines = ["module m05_rolling_replay_control_s_axi;", "localparam"]
        for name, val in values.items():
            raw = name if name in ("AP_CTRL", "AP_RETURN") else name + "_0"
            lines.append(f"    ADDR_{raw} = 7'h{val:02x},")
        lines.append("END = 1'b1;")
        self.assertEqual(parse_control_verilog("\\n".join(lines)), EXAMPLE)

    def test_rtl_fallback_is_used_when_no_driver_header(self):
        with tempfile.TemporaryDirectory(prefix="m05_axi_rtl_") as td:
            root = Path(td)
            rtl = (root / "work/hls/syn/verilog/"
                   "m05_rolling_replay_control_s_axi.v")
            rtl.parent.mkdir(parents=True)
            rtl.write_text("localparam\\n" + "\\n".join(
                f"ADDR_{k if k in ('AP_CTRL', 'AP_RETURN') else k + '_0'}"
                f" = 7'h{v:02x},"
                for k, v in EXAMPLE.items()))
            parsed, location = find_generated_register_map(root)
            self.assertEqual(parsed, EXAMPLE)
            self.assertEqual(location, rtl)

    def test_rtl_fallback_refuses_missing_or_conflicting_map(self):
        with self.assertRaisesRegex(ValueError, "unique offset"):
            parse_control_verilog("localparam ADDR_AP_CTRL = 7'h00;")
        with self.assertRaisesRegex(ValueError, "invalid RTL"):
            parse_control_verilog("\\n".join(
                f"ADDR_{k if k in ('AP_CTRL', 'AP_RETURN') else k+'_0'}"
                f" = 7'h{(129 if k == 'TICKS_DATA' else v):02x},"
                for k, v in EXAMPLE.items()))

    def test_native_regmap_does_not_require_vitis_installation(self):
        self.assertEqual(set(parse_registers(test_header())), set(REQUIRED))


if __name__ == "__main__":
    unittest.main()
