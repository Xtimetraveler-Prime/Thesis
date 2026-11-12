"""M08.2b Path A offline fan-bitstream release source and negative tests.

All sample reports and SHA receipts are SYNTHETIC. No vendor or hardware
success may be claimed from these tests.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from m08_path_a_fan_release_preflight import (  # noqa: E402
    LEDGER_NAMES, check_drc, check_io, check_ledger,
    check_methodology, check_route, check_timing,
)

TCL = SCRIPTS / "m08_path_a_fan_bitstream.tcl"
RUN = SCRIPTS / "run_m08_path_a_fan_bitstream.sh"
PRE = SCRIPTS / "m08_path_a_fan_release_preflight.py"
AUDIT = SCRIPTS / "m08_path_a_fan_bitstream_audit.py"


def example_drc() -> str:
    names = ",".join(
        "m08_page_ps_i/ctrl_sc/inst/n%d/mi_handler_m_sc_areset_pipe" % i
        for i in range(14)
    )
    return (
        "Design State : Fully Routed\nChecks found: 1\n"
        "| RTSTAT-10 | Warning | No routable loads | 1 |\n"
        "RTSTAT-10#1 Warning\n15 net(s) have no routable loads. "
        "The problem net(s) are " + names + ".\nRelated violations: <none>\n"
    )


def example_timing() -> str:
    return (
        "Design State      : Routed\n"
        "checking no_clock (0)\n"
        "checking unconstrained_internal_endpoints (0)\n"
        "checking no_input_delay (0)\n"
        "checking no_output_delay (0)\n"
        "There are 0 pins that are not constrained for maximum delay.\n"
        "All user specified timing constraints are met.\n"
        "   5.355 0.000 0 4515 0.029 0.000 0 4515\n"
        "0  Failing Endpoints\n"
        "| Unconstrained Path Table\n"
        "From Clock    To Clock\n"
        "----------    --------\n"
        "| Timing Details\n"
    )


class TestPathAFanRelease(unittest.TestCase):
    def test_source_uses_original_route_only_with_no_hardware_calls(self):
        t = TCL.read_text()
        r = RUN.read_text()
        p = PRE.read_text()
        a = AUDIT.read_text()
        for phrase in (
            "open_checkpoint $dcp", "get_ports -quiet M08_FAN_PWM",
            "get_property PACKAGE_PIN $pwm", "get_property IOSTANDARD $pwm",
            "get_timing_paths -quiet -delay_type max",
            "get_timing_paths -quiet -delay_type min",
            "report_drc -file $drc_file", "report_timing_summary",
            "write_bitstream $bit_file", "RTSTAT-10",
            "M08_ACCEPT_FAN_RTSTAT10", "m08_page_ps_wrapper",
        ):
            self.assertIn(phrase, t)
        self.assertLess(t.index("sha256sum -- $dcp"),
                        t.index("open_checkpoint $dcp"))
        self.assertLess(t.index("report_drc -file $drc_file"),
                        t.index("write_bitstream $bit_file"))
        self.assertEqual(t.count("write_bitstream $bit_file"), 1)
        for forbidden in (
            "program_hw_devices", "open_hw_manager", "xmutil unloadapp",
            "xmutil loadapp", "/dev/mem", "devmem ", "write_cfgmem",
            "reset_hw_axi", "flashcp ", "bootgen ",
        ):
            self.assertNotIn(forbidden, "\n".join(
                x for x in t.splitlines()
                if x.strip() and not x.lstrip().startswith("#")
            ))
            self.assertNotIn(forbidden, "\n".join(
                x for x in r.splitlines()
                if x.strip() and not x.lstrip().startswith("#")
            ))
        self.assertIn("m08_path_a_fan_release_preflight.py", r)
        self.assertIn("m08_path_a_fan_bitstream_audit.py", r)
        self.assertIn("08_evidence_sha256.txt", r)
        self.assertIn("M08_FAN_ROUTE_EVIDENCE_DIR", r)
        self.assertIn("M08_ACCEPT_FAN_RTSTAT10", r)
        self.assertIn("K26_FAN_ROUTED_EVIDENCE_REVIEWED_RTSTAT10", p)
        self.assertIn("ps_axi_readback_verified", a)

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_bash_parse_and_approval_fails_without_evidence(self):
        p = subprocess.run(["bash", "-n", str(RUN)],
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        env = os.environ.copy()
        env.pop("M08_ACCEPT_FAN_RTSTAT10", None)
        env.pop("M08_FAN_ROUTE_EVIDENCE_DIR", None)
        with tempfile.TemporaryDirectory() as d:
            env["M08_EVIDENCE_BASE"] = d
            p = subprocess.run(["bash", str(RUN)], env=env,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn("explicitly review", p.stderr)
            self.assertEqual(list(Path(d).iterdir()), [])

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh unavailable")
    def test_native_release_tcl_grammar(self):
        cmd = (f"set f [open {{{TCL}}} r]\n"
               "set t [read $f]\nclose $f\n"
               'if {![info complete $t]} {error "Tcl incomplete"}\n'
               'puts "M08_FAN_RELEASE_TCL_SOURCE_ONLY_OK"\n')
        p = subprocess.run(["tclsh"], input=cmd, text=True,
                           capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assertIn("M08_FAN_RELEASE_TCL_SOURCE_ONLY_OK", p.stdout)

    def test_synthetic_drc_unchanged_rtstat_and_denied_new_warning(self):
        d = example_drc()
        good = check_drc(d)
        self.assertEqual(good["reported_nets"], 15)
        self.assertFalse(good["warning_waived"])
        for bad in (
            d.replace("Checks found: 1", "Checks found: 2"),
            d.replace("15 net(s)", "16 net(s)"),
            d.replace("RTSTAT-10", "NSTD-1"),
            d.replace("m08_page_ps_i/ctrl_sc/", "untrusted/"),
            d.replace("Design State : Fully Routed", "Design State : Placed"),
            d + "\n| NSTD-1 | Error | Invalid I/O | 1 |\n",
        ):
            with self.subTest(bad=bad[-80:]):
                with self.assertRaises(ValueError):
                    check_drc(bad)

    def test_synthetic_timing_not_unconstrained_or_negative(self):
        good = example_timing()
        self.assertEqual(check_timing(good, 5.355, .029)["wns_ns"], 5.355)
        for bad, setup, hold in (
            (good.replace("no_clock (0)", "no_clock (1)"), 5.355, .029),
            (good.replace("0 pins that are not constrained",
                          "1 pins that are not constrained"), 5.355, .029),
            (good, -0.001, .029),
            (good, 5.355, -0.01),
            (good.replace("5.355 0.000", "5.355 -1.000"), 5.355, .029),
            (good.replace("From Clock    To Clock",
                          "From Clock    To Clock\nclk_pl_0 clk_pl_1"),
             5.355, .029),
        ):
            with self.subTest(setup=setup, hold=hold, text=bad[-80:]):
                with self.assertRaises(ValueError):
                    check_timing(bad, setup, hold)

    def test_synthetic_route_io_and_methodology_rejection(self):
        route = (
            "# of routable nets.......................... : 3367 :\n"
            "# of fully routed nets..................... : 3367 :\n"
            "# of nets with routing errors.......... : 0 :\n"
        )
        self.assertEqual(check_route(route)["routing_errors"], 0)
        with self.assertRaises(ValueError):
            check_route(route.replace("3367", "3366", 1))
        with self.assertRaises(ValueError):
            check_route(route.replace("errors.......... : 0", "errors.......... : 1"))
        self.assertEqual(check_methodology(
            "Design State : Fully Routed\nChecks found: 0\n")["violations"], 0)
        with self.assertRaises(ValueError):
            check_methodology("Design State : Fully Routed\nChecks found: 1\n")
        io = (
            "| A12 | M08_FAN_PWM[0] | High Density | IO_L11P_AD9P_45 | "
            "OUTPUT | LVCMOS33 | 45 | 4 | | SLOW | | NONE |\n"
        )
        self.assertEqual(check_io(io)["pin"], "A12")
        for bad in ("B12", "LVCMOS18", "INPUT"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                check_io(io.replace({
                    "B12": "A12", "LVCMOS18": "LVCMOS33", "INPUT": "OUTPUT"
                }[bad], bad, 1))

    def test_receipt_detects_drift_and_rejects_missing_origin(self):
        # A tiny ARTIFICIAL receipt containing all expected names, not real
        # vendor outputs; the check validates SHA coverage ONLY.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ledger = []
            for name in LEDGER_NAMES:
                p = root / name
                p.write_text("TEST FAKE " + name + "\n")
                ledger.append(sha256(p.read_bytes()).hexdigest() + "  " + name)
            (root / "52_evidence_sha256.txt").write_text("\n".join(ledger)+"\n")
            self.assertEqual(len(check_ledger(root)), len(LEDGER_NAMES))
            (root / LEDGER_NAMES[-1]).write_text("TAMPERED")
            with self.assertRaises(ValueError):
                check_ledger(root)


if __name__ == "__main__":
    unittest.main()
