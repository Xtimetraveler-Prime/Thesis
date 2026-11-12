"""M08.2b.4a first-party original K26 route candidate and rejection tests.

Synthetic report fixtures are FAKE and never constitute Vivado routing.
Real hardware closure requires owner native Vivado reports/checkpoint.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT / "scripts/m08_page_post_route_candidate.tcl"
RUN = ROOT / "scripts/run_m08_page_post_route.sh"
AUDIT = ROOT / "scripts/m08_page_post_route_audit.py"
sys.path.insert(0, str(ROOT / "scripts"))
from m08_page_post_route_audit import (  # noqa: E402
    FILES, MARKERS, ORIGINALS, audit_evidence
)


def fake_evidence(folder: Path) -> None:
    """Artificial consistency fixture, NOT an original vendor output."""
    manifest = "".join(
        f"{sha256((ROOT / name).read_bytes()).hexdigest()}  {name}\n"
        for name in FILES
    )
    (folder / "result.txt").write_text("exit_status=0\n")
    (folder / "source_sha256_before.txt").write_text(manifest)
    (folder / "source_sha256_after.txt").write_text(manifest)
    (folder / "01_vivado_impl.log").write_text(
        "# ARTIFICIAL TEST FIXTURE, NOT A VIVADO LOG\n"
        + "M08_GENUINE_PS_PL0_CLOCK_HZ=99999001\n"
        + "M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ=99999001\n"
        + "\n".join(MARKERS) + "\n")
    (folder / "02_vivado_page_bd_readback.txt").write_text("\n".join((
        "META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD",
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|board_part|xilinx.com:kv260_som:part0:1.4",
        "META|ps_preset|YES",
        "META|requested_clock_hz|100000000",
        "META|actual_clock_hz|99999001",
        "META|page_source|rtl/m08/m08_ps_page_safe_shell.v",
        "META|compute_enabled|NO",
        "MASTER|M_AXI_HPM0_FPD|/ps/Data",
        "SLAVE_IDENTITY|/identity/S_AXI|/identity/S_AXI/reg0",
        "SLAVE_PAGE|/page/S_AXI|/page/S_AXI/reg0",
        "APERTURE_IDENTITY|/ps/Data/SEG_identity_reg0|0x00A0000000|0x0000001000",
        "APERTURE_PAGE|/ps/Data/SEG_page_reg0|0x00A0001000|0x0000001000",
        "META|validated_bd|YES",
        "META|routed_implementation|NOT_RUN",
        "META|bitstream|NOT_GENERATED",
        "META|linux_mmio|NOT_ACCESSED",
        "META|physical_ddr|NOT_ACCESSED",
        "META|physical_kv260|NOT_PROGRAMMED",
    )) + "\n")
    (folder / "03_page_bd_export.tcl").write_text(
        "# ARTIFICIAL TCL EXPORT, NOT ACTUAL VIVADO\n"
        "connect_bd_intf_net [get_bd_intf_pins ps/M_AXI_HPM0_FPD] [get_bd_intf_pins ctrl_sc/S00_AXI]\n"
        "connect_bd_intf_net [get_bd_intf_pins ctrl_sc/M00_AXI] [get_bd_intf_pins identity/S_AXI]\n"
        "connect_bd_intf_net [get_bd_intf_pins ctrl_sc/M01_AXI] [get_bd_intf_pins page/S_AXI]\n"
        "create_bd_cell -type module -reference m08_ps_page_safe_shell page\n"
    )
    (folder / "04_implementation_metrics.txt").write_text("\n".join((
        "META|scope|M08_GENUINE_LOCAL_KV260_PAGE_SAFE_POST_ROUTE",
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|synthesis_status|synth_design Complete!",
        "META|implementation_status|route_design Complete!",
        "META|synthesis_progress|100%",
        "META|implementation_progress|100%",
        "META|wns_ns|0.123",
        "META|whs_ns|0.045",
        "META|clock_count|4",
        "META|no_bitstream|YES",
        "META|no_board_programming|YES",
        "META|compute_enabled|NO",
        "META|physical_ddr|NOT_ACCESSED",
        "META|linux_mmio|NOT_ACCESSED",
    )) + "\n")
    for name in ORIGINALS[4:9]:
        (folder / name).write_text(
            "# ARTIFICIAL TEST REPORT, NOT VIVADO\n" + "#"*100)
    (folder / "10_m08_page_post_route.dcp").write_bytes(
        b"ARTIFICIAL DCP; NOT VIVADO\n" * 100)


class M08PagePostRouteCandidateTests(unittest.TestCase):
    def test_vendor_workflow_reuses_accepted_bd_but_never_writes_bitstream(self):
        t = TCL.read_text()
        r = RUN.read_text()
        a = AUDIT.read_text()
        self.assertIn("set argv [list $root $evidence]", t)
        self.assertIn("source $candidate", t)
        self.assertIn("scripts m08_page_ps_bd_candidate.tcl", t)
        self.assertLess(t.index("source $candidate"),
                        t.index("generate_target all $bd"))
        self.assertLess(t.index("generate_target all $bd"),
                        t.index("make_wrapper -files $bd -top"))
        self.assertLess(t.index("make_wrapper -files $bd -top"),
                        t.index("launch_runs impl_1 -to_step route_design"))
        self.assertLess(t.index("wait_on_run impl_1"),
                        t.index("open_run impl_1"))
        self.assertLess(t.index("open_run impl_1"),
                        t.index("report_timing_summary"))
        for term in (
            "get_timing_paths -quiet -delay_type max",
            "get_timing_paths -quiet -delay_type min",
            "report_utilization", "report_drc", "report_methodology",
            "report_clock_utilization", "report_timing_summary",
            "write_checkpoint $checkpoint_file",
            "M08_PAGE_GENUINE_NATIVE_WRAPPER_GENERATED=1",
            "M08_PAGE_GENUINE_NATIVE_SYNTH_AND_ROUTE_COMPLETED=1",
            "M08_PAGE_POST_ROUTE_TIMING_NONNEGATIVE_NO_BITSTREAM=1",
            "M08_PAGE_NATIVE_ROUTE_REPORTS_GENERATED_UNREVIEWED_DRC_NO_BOARD",
            "string is double -strict $setup_slack",
            "string is double -strict $hold_slack",
            "double($setup_slack)", "double($hold_slack)",
            "get_clocks -quiet",
        ):
            self.assertIn(term, t)
        for forbidden in (
            "write_bitstream", "write_hw_platform", "launch_hw_server",
            "open_hw_target", "program_hw_devices", "connect_hw_server",
            "write_cfgmem", "bootgen", "xmutil ", "/dev/mem",
        ):
            self.assertNotIn(forbidden, t)
        self.assertNotIn("launch_runs", r)
        self.assertNotIn("sudo ", r)
        self.assertIn('M08_ROUTE_JOBS:-4', r)
        self.assertIn("mktemp -d", r)
        self.assertIn("M08_ROUTE_EVIDENCE_DIR=", r)
        self.assertIn("source_sha256_before.txt", r)
        self.assertIn("source_sha256_after.txt", r)
        self.assertIn("11_m08_route_independent_audit.json", r)
        self.assertIn("12_evidence_sha256.txt", r)
        self.assertEqual(len(FILES), 10)
        for name in FILES:
            self.assertEqual(r.count('"' + name + '"'), 1)
        for name in ORIGINALS:
            self.assertIn(name, r)
        self.assertIn("no_bitstream", a)
        self.assertIn("unconstrained_path_review_required", a)

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_runner_bash_parse(self):
        p = subprocess.run(["bash", "-n", str(RUN)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh unavailable")
    def test_route_tcl_is_syntactically_complete(self):
        script = (
            "set fd [open {" + str(TCL) + "} r]\n"
            "set src [read $fd]\nclose $fd\n"
            'if {![info complete $src]} {puts stderr BAD_ROUTE_TCL; exit 9}\n'
            'puts M08_ROUTE_TCL_PARSE_ONLY_NOT_VIVADO\n'
        )
        p = subprocess.run(["tclsh"], input=script,
                           text=True, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("M08_ROUTE_TCL_PARSE_ONLY_NOT_VIVADO", p.stdout)

    def test_synthetic_original_receipt_and_failure_mutations(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            fake_evidence(folder)
            accepted = audit_evidence(folder, ROOT)
            self.assertEqual(
                accepted["status"],
                "ORIGINAL_OWNER_M08_KV260_ROUTE_EVIDENCE_CONSISTENT_DRC_REVIEW_REQUIRED")
            self.assertFalse(accepted["bitstream_generated"])
            self.assertTrue(accepted["unconstrained_path_review_required"])
            metrics = folder / "04_implementation_metrics.txt"
            original_metrics = metrics.read_text()
            for before, after in (
                ("META|wns_ns|0.123", "META|wns_ns|-0.001"),
                ("META|whs_ns|0.045", "META|whs_ns|-0.300"),
                ("META|clock_count|4", "META|clock_count|0"),
                ("META|no_bitstream|YES", "META|no_bitstream|NO"),
                ("META|compute_enabled|NO", "META|compute_enabled|YES"),
                ("META|implementation_progress|100%",
                 "META|implementation_progress|99%"),
            ):
                with self.subTest(change=after):
                    metrics.write_text(original_metrics.replace(before, after))
                    with self.assertRaises(ValueError):
                        audit_evidence(folder, ROOT)
                    metrics.write_text(original_metrics)
            original_report = (folder / "02_vivado_page_bd_readback.txt")
            report_content = original_report.read_text()
            original_report.write_text(
                report_content.replace("0x00A0001000", "0x00A0000000"))
            with self.assertRaisesRegex(ValueError, "overlap"):
                audit_evidence(folder, ROOT)
            original_report.write_text(report_content)
            log = folder / "01_vivado_impl.log"
            original_log = log.read_text()
            log.write_text(original_log.replace(
                "M08_PAGE_POST_ROUTE_TIMING_NONNEGATIVE_NO_BITSTREAM=1\n", ""))
            with self.assertRaisesRegex(ValueError, "marker missing"):
                audit_evidence(folder, ROOT)
            log.write_text(original_log + MARKERS[-1] + "\n")
            with self.assertRaisesRegex(ValueError, "duplicated"):
                audit_evidence(folder, ROOT)
            log.write_text(original_log)
            manifest = folder / "source_sha256_after.txt"
            old_manifest = manifest.read_text()
            manifest.write_text(old_manifest.replace("  ", " "))
            with self.assertRaisesRegex(ValueError, "source was modified"):
                audit_evidence(folder, ROOT)
            manifest.write_text(old_manifest)
            exp = folder / "03_page_bd_export.tcl"
            old_exp = exp.read_text()
            exp.write_text(old_exp.replace("page/S_AXI", "identity/S_AXI"))
            with self.assertRaisesRegex(ValueError, "native AXI link"):
                audit_evidence(folder, ROOT)
            exp.write_text(old_exp)


if __name__ == "__main__":
    unittest.main()
