"""M08.2b combined release-source regressions; NEVER a vendor bitstream test.

Fake post-route reports here are explicitly synthetic. Native Vivado
open_checkpoint/write_bitstream and physical access require original owner.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))
from m08_page_post_route_audit import audit_evidence
from m08_page_release_preflight import release_preflight
from m08_page_bitstream_audit import SOURCES, MARKERS
from test_m08_page_post_route_candidate import fake_evidence

TCL=ROOT/"scripts/m08_page_bitstream_candidate.tcl"
BASH=ROOT/"scripts/run_m08_page_bitstream.sh"
PRE=ROOT/"scripts/m08_page_release_preflight.py"
AUDIT=ROOT/"scripts/m08_page_bitstream_audit.py"


def make_fake_route(folder: Path) -> None:
    """FAKE report fixture. Synthetic PASS does NOT qualify the FPGA."""
    fake_evidence(folder)
    timing=(
        "Design State      : Routed\n"
        "check_timing report\n"
        "1. checking no_clock (0)\n"
        "4. checking unconstrained_internal_endpoints (0)\n"
        "5. checking no_input_delay (0)\n"
        "6. checking no_output_delay (0)\n"
        "There are 0 pins that are not constrained for maximum delay.\n"
        "All user specified timing constraints are met.\n"
        "0  Failing Endpoints\n"
        " 0.123 0.000 0 4515 0.045 0.000 0 4515 3.500 0.000 0 1748\n"
        "| Unconstrained Path Table\n"
        "Path Group   From Clock  To Clock\n"
        "----------   ----------  --------\n"
        "| Timing Details\n"
    )
    (folder/"05_timing_summary_post_route.rpt").write_text(timing)
    # Real owner's Vivado printed 14 net NAMES while the summary says 15.
    names=[
        f"m08_page_ps_i/ctrl_sc/inst/m0{i%2}_nodes/m0{i%2}_b_node/"
        "inst/mi_handler_m_sc_areset_pipe"
        for i in range(14)
    ]
    # Distinct 14 names, preserving the original name suffix.
    names=[
        f"m08_page_ps_i/ctrl_sc/inst/{i:02d}_nodes/b_node/"
        "inst/mi_handler_m_sc_areset_pipe"
        for i in range(14)
    ]
    drc=(
        "Design State : Fully Routed\n"
        "Checks found: 1\n"
        "| Rule | Severity | Description | Checks |\n"
        "| RTSTAT-10 | Warning | No routable loads | 1 |\n"
        "RTSTAT-10#1 Warning\n"
        "15 net(s) have no routable loads. The problem bus(es) and/or net(s) are "
        + ",\n".join(names) + ".\nRelated violations: <none>\n"
    )
    (folder/"07_drc_post_route.rpt").write_text(drc)
    (folder/"08_methodology_post_route.rpt").write_text(
        "Design State : Fully Routed\nChecks found: 0\n"
        "Report Methodology -- ARTIFICIAL FIXTURE NOT VIVADO\n")
    (folder/"06_utilization_post_route.rpt").write_text(
        "| CLB LUTs | 1957 |\n| CLB Registers | 1665 |\n"
        "| Block RAM Tile | 0 |\n| DSPs | 0 |\n"
        "10. Black Boxes\n| Ref Name | Used |\n"
        "11. Instantiated Netlists\n")
    native=audit_evidence(folder,ROOT)
    (folder/"11_m08_route_independent_audit.json").write_text(
        json.dumps(native,indent=2)+"\n")
    names=(
        "01_vivado_impl.log", "02_vivado_page_bd_readback.txt",
        "03_page_bd_export.tcl", "04_implementation_metrics.txt",
        "05_timing_summary_post_route.rpt","06_utilization_post_route.rpt",
        "07_drc_post_route.rpt","08_methodology_post_route.rpt",
        "09_clock_utilization_post_route.rpt",
        "10_m08_page_post_route.dcp","11_m08_route_independent_audit.json",
    )
    (folder/"12_evidence_sha256.txt").write_text("".join(
        f"{sha256((folder/n).read_bytes()).hexdigest()}  {folder/n}\n"
        for n in names
    ))


class M08BitstreamReleaseTests(unittest.TestCase):
    def test_synthesis_route_belongs_to_original_source_only(self):
        t=TCL.read_text()
        sh=BASH.read_text()
        pre=PRE.read_text()
        audit=AUDIT.read_text()
        for required in (
            "open_checkpoint $checkpoint", "write_bitstream $bit_file",
            "report_drc -file $drc_file", "report_timing_summary",
            "get_timing_paths -quiet -delay_type max",
            "get_timing_paths -quiet -delay_type min",
            "get_clocks -quiet", "M08_PAGE_GENUINE_OFFLINE_BITSTREAM_EMITTED_NOT_PROGRAMMED",
            "RTSTAT-10", "15 net",
        ):
            self.assertIn(required,t)
        self.assertLess(t.index("open_checkpoint $checkpoint"),
                        t.index("report_drc -file $drc_file"))
        self.assertLess(t.index("report_drc -file $drc_file"),
                        t.index("write_bitstream $bit_file"))
        for disallowed in (
            "program_hw_devices","open_hw_target","connect_hw_server",
            "launch_runs", "set_property SEVERITY", "write_cfgmem",
            "xmutil ", "/dev/mem", "bootgen",
        ):
            self.assertNotIn(disallowed,t)
        self.assertNotIn("sudo ",sh)
        self.assertIn("M08_ACCEPT_RTSTAT10",sh)
        self.assertIn("M08_ROUTE_EVIDENCE_DIR",sh)
        self.assertIn("mktemp -d",sh)
        self.assertIn("m08_page_release_preflight.py",sh)
        self.assertIn("m08_page_bitstream_audit.py",sh)
        self.assertIn("12_evidence_sha256.txt",pre)
        self.assertIn("drc_clean",pre)
        self.assertIn("unconstrained_internal_endpoints",pre)
        self.assertIn("original_digests",pre)
        self.assertIn("physical_board_programmed",audit)
        for name in SOURCES:
            self.assertEqual(sh.count('"' + name + '"'),1)
        self.assertEqual(len(SOURCES),14)
        self.assertEqual(len(MARKERS),3)
        self.assertIn("M08_PAGE_RELEASE_CHECKPOINT_TOP_VALIDATED=m08_page_ps_wrapper", MARKERS)
        # The original owner native failure opened the routed checkpoint
        # successfully but the script compared current_design NAME to HDL
        # top, falsely rejecting the netlist display name.
        self.assertIn("get_property -quiet TOP [current_design]", t)
        self.assertIn("get_property NAME [current_design]", t)
        self.assertIn("META|top|$top_module", t)
        self.assertIn("META|design_display_name|$design_name", t)
        self.assertNotIn(
            'if {[get_property NAME [current_design]] ne "m08_page_ps_wrapper"}',
            t,
        )
        self.assertIn("verified_routed_hdl_top",audit)
        self.assertIn("design_display_name",audit)

    @unittest.skipUnless(shutil.which("bash"),"bash unavailable")
    def test_runner_syntax(self):
        x=subprocess.run(["bash","-n",str(BASH)],capture_output=True,text=True)
        self.assertEqual(x.returncode,0,x.stderr)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl syntax checker unavailable")
    def test_release_tcl_grammar(self):
        code=(
            "set fd [open {" + str(TCL) + "} r]\n"
            "set src [read $fd]\nclose $fd\n"
            'if {![info complete $src]} {puts stderr BAD_RELEASE_TCL; exit 9}\n'
            "puts M08_RELEASE_TCL_PARSE_ONLY_NOT_VIVADO\n"
        )
        p=subprocess.run(["tclsh"],input=code,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("M08_RELEASE_TCL_PARSE_ONLY_NOT_VIVADO",p.stdout)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh unavailable")
    def test_top_property_not_design_display_name_with_tcl_mock(self):
        """Fake Vivado: NAME=netlist_1 must NOT be mistaken for HDL TOP.

        Tcl-only mock is a regression of the original owner 2026-11-11
        checkpoint-open guard failure, never a native Vivado/bitstream pass.
        """
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            checkpoint=d/"10_m08_page_post_route.dcp"
            checkpoint.write_text("FAKE DCP -- TCL MOCK ONLY")
            # Only allow a mock execution as far as get_clocks. No
            # write_bitstream, timing, DRC, or hardware commands are run.
            for top, accepted in (
                ("m08_page_ps_wrapper",True),
                ("not_the_signed16_page",False),
                ("",False),
            ):
                with self.subTest(HDL_TOP=top):
                    code = (
                        "set argv [list {" + str(checkpoint) + "} {" +
                        str(d) + "}]\\n"
                        "set ::fake_top {" + top + "}\\n"
                        "proc version {args} {return 2025.2}\\n"
                        "proc open_checkpoint {args} {}\\n"
                        "proc current_project {} {return MOCK_K26_PROJECT}\\n"
                        "proc current_design {} {return MOCK_NETLIST_DESIGN}\\n"
                        'proc get_property {args} {\\n'
                        '  if {[llength $args] == 3} {set key [lindex $args 1]} '
                        'else {set key [lindex $args 0]}\\n'
                        '  switch -- $key {\\n'
                        '    PART {return xck26-sfvc784-2LV-c}\\n'
                        '    NAME {return netlist_1}\\n'
                        '    TOP {return $::fake_top}\\n'
                        '    default {error "unexpected property $key"}\\n'
                        '  }\\n'
                        '}\\n'
                        'proc get_clocks {args} {\\n'
                        '  puts "M08_TOP_MOCK_ACCEPTED_AFTER_NAME_NETLIST_1"\\n'
                        '  exit 0\\n'
                        '}\\n'
                        'if {[catch {source {' + str(TCL) + '}} err]} {\\n'
                        '  if {[string match "*unexpected routed PS/page TOP*" $err]} {\\n'
                        '    puts "M08_TOP_MOCK_REJECTED:$err"\\n'
                        '    exit 0\\n'
                        '  }\\n'
                        '  puts stderr $err\\n'
                        '  exit 8\\n'
                        '}\\n'
                        'error "fake Tcl did not reach guarded clock query"\\n'
                    ).replace("\\n", "\n")
                    proc=subprocess.run(["tclsh"],input=code,text=True,
                                        capture_output=True,timeout=30)
                    self.assertEqual(proc.returncode,0,
                                     proc.stdout+"\\n"+proc.stderr)
                    if accepted:
                        self.assertIn(
                            "M08_TOP_MOCK_ACCEPTED_AFTER_NAME_NETLIST_1",
                            proc.stdout,
                        )
                        self.assertIn(
                            "M08_PAGE_RELEASE_CHECKPOINT_TOP_VALIDATED=m08_page_ps_wrapper",
                            proc.stdout,
                        )
                        self.assertNotIn("M08_TOP_MOCK_REJECTED",proc.stdout)
                    else:
                        self.assertIn("M08_TOP_MOCK_REJECTED:",proc.stdout)
                        self.assertNotIn("M08_TOP_MOCK_ACCEPTED",proc.stdout)

    def test_synthetic_route_release_gate_mutation_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            make_fake_route(folder)
            receipt=release_preflight(folder,ROOT)
            self.assertFalse(receipt["drc_clean"])
            self.assertEqual(receipt["drc_warning"],"RTSTAT-10")
            self.assertEqual(receipt["drc_warning_nets"],15)
            self.assertEqual(receipt["drc_named_nets_in_report"],14)
            self.assertEqual(receipt["timing_wns_ns"],0.123)
            for name,old,new in (
                ("07_drc_post_route.rpt","RTSTAT-10","RTSTAT-20"),
                ("05_timing_summary_post_route.rpt",
                 "checking unconstrained_internal_endpoints (0)",
                 "checking unconstrained_internal_endpoints (12)"),
                ("08_methodology_post_route.rpt",
                 "Checks found: 0", "Checks found: 1"),
                ("04_implementation_metrics.txt",
                 "META|wns_ns|0.123", "META|wns_ns|-0.100"),
                ("12_evidence_sha256.txt",
                 "01_vivado_impl.log", "01_other.log"),
            ):
                with self.subTest(name=name):
                    path=folder/name
                    original=path.read_text()
                    path.write_text(original.replace(old,new))
                    with self.assertRaises(ValueError):
                        release_preflight(folder,ROOT)
                    path.write_text(original)
            # Synthetic acceptance is explicitly NOT a source of physical
            # bitstream/board proof. No Vivado or .bit is created here.


if __name__=="__main__":
    unittest.main()
