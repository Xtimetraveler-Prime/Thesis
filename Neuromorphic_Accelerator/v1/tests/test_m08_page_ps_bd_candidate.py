"""M08.2b.3 source-level safe PS/page Vivado BD handoff regression.

Synthetic receipts and Tcl mocks validate only rejection logic/structure.
They are never original vendor, routed or physical FPGA evidence.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m08_page_bd_audit import FILES, MARKER, DISTINCT_MARKER, audit_evidence

TCL = ROOT / "scripts/m08_page_ps_bd_candidate.tcl"
RUNNER = ROOT / "scripts/run_m08_page_bd.sh"
SHELL = ROOT / "rtl/m08/m08_ps_page_safe_shell.sv"
ADAPTER = ROOT / "rtl/m08/m08_axil_page_control.sv"


def synthetic_evidence(folder: Path):
    """FAKE fixture for unit tests; explicitly NOT a native Vivado artifact."""
    from hashlib import sha256
    manifest = "".join(
        f"{sha256((ROOT / name).read_bytes()).hexdigest()}  {name}\n"
        for name in FILES
    )
    (folder / "source_sha256_before.txt").write_text(manifest)
    (folder / "source_sha256_after.txt").write_text(manifest)
    (folder / "result.txt").write_text("exit_status=0\n")
    (folder / "02_vivado_page_bd_readback.txt").write_text("\n".join((
        "META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD",
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|board_part|xilinx.com:kv260_som:part0:1.4",
        "META|ps_preset|YES",
        "META|requested_clock_hz|100000000",
        "META|actual_clock_hz|99999001",
        "META|page_source|rtl/m08/m08_ps_page_safe_shell.sv",
        "META|compute_enabled|NO",
        "MASTER|M_AXI_HPM0_FPD|/ps/Data",
        "SLAVE_IDENTITY|identity/S_AXI|identity/S_AXI/reg0",
        "SLAVE_PAGE|page/S_AXI|page/S_AXI/reg0",
        "APERTURE_IDENTITY|/ps/Data/SEG_identity_reg0|0xA0000000|0x1000",
        "APERTURE_PAGE|/ps/Data/SEG_page_reg0|0xA0010000|0x1000",
        "META|validated_bd|YES",
        "META|routed_implementation|NOT_RUN",
        "META|bitstream|NOT_GENERATED",
        "META|linux_mmio|NOT_ACCESSED",
        "META|physical_ddr|NOT_ACCESSED",
        "META|physical_kv260|NOT_PROGRAMMED",
    )) + "\n")
    (folder / "01_vivado_page_bd.log").write_text(
        "# SYNTHETIC FIXTURE, NOT A VIVADO RUN\n"
        "# puts \"M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD\"\n"
        "M08_KV260_PS_BOARD_PRESET_APPLIED=1\n"
        "M08_GENUINE_PS_PL0_CLOCK_HZ=99999001\n"
        "M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ=99999001\n"
        + DISTINCT_MARKER + "\n" + MARKER + "\n"
    )
    (folder / "03_page_bd_export.tcl").write_text(
        "# SYNTHETIC FIXTURE, NOT ORIGINAL VIVADO\n"
        + "\n".join((
            "ps/M_AXI_HPM0_FPD", "ctrl_sc/S00_AXI",
            "ctrl_sc/M00_AXI", "ctrl_sc/M01_AXI",
            "identity/S_AXI", "page/S_AXI", "m08_ps_page_safe_shell",
            "assign_bd_address",
        )) + "\n" + ("# DUMMY EXPORTED TEXT ONLY\n" * 35)
    )


class M08PageNativeBDCandidateTests(unittest.TestCase):
    def test_kv260_ps_preset_safe_compute_and_two_distinct_slaves(self):
        tcl = TCL.read_text()
        shell = SHELL.read_text()
        adapter = ADAPTER.read_text()
        runner = RUNNER.read_text()
        for item in (
            "xck26-sfvc784-2LV-c", "2025.2",
            "get_board_parts -quiet xilinx.com:kv260_som:part0:*",
            'apply_board_preset "1"',
            "CONFIG.PSU__USE__M_AXI_GP0 1",
            "CONFIG.PSU__USE__M_AXI_GP1 0",
            "CONFIG.PSU__USE__M_AXI_GP2 0",
            "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100",
            "set maximum_clock_deviation_hz 1000",
            "CONFIG.NUM_SI 1 CONFIG.NUM_MI 2",
            "ctrl_sc/M00_AXI", "ctrl_sc/M01_AXI",
            "identity/S_AXI", "page/S_AXI",
            "identity/aclk", "page/aclk",
            "identity/aresetn", "page/aresetn",
            "assign_bd_address", "validate_bd_design -force",
            "M08_PAGE_BD_DISTINCT_ID_AND_PAGE_4K_ADDRESS_SEGMENTS=1",
            "write_bd_tcl", "M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD",
        ):
            self.assertIn(item, tcl)
        self.assertLess(tcl.index("create_project m08_page_ps"),
                        tcl.index("get_ipdefs -all"))
        self.assertLess(tcl.index("get_board_parts -quiet"),
                        tcl.index("create_bd_design m08_page_ps"))
        self.assertLess(tcl.index("apply_bd_automation -rule"),
                        tcl.index("CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100"))
        self.assertLess(tcl.index("validate_bd_design -force"),
                        tcl.index("M08_PAGE_BD_DISTINCT_ID_AND_PAGE_4K_ADDRESS_SEGMENTS=1"))
        self.assertIn("module m08_ps_page_safe_shell", shell)
        self.assertIn("ENABLE_COMPUTE(1'b0)", shell)
        self.assertIn("parameter ENABLE_COMPUTE = 1'b1", adapter)
        self.assertIn("bank_phase==READY &&", adapter)
        self.assertIn("ENABLE_COMPUTE) ||", adapter)
        self.assertIn("ASSOCIATED_BUSIF S_AXI", shell)
        self.assertIn("PROTOCOL AXI4LITE", shell)
        self.assertNotIn("FREQ_HZ 100000000", shell)
        for port in ("compute_req", "compute_write", "compute_done",
                     "compute_fault", "fault_in"):
            self.assertIn("." + port + "(1'b0)", shell)
        for bad in ("write_bitstream", "open_hw_target", "program_hw_devices",
                    "launch_runs", "connect_hw_server", "create_hw_device"):
            self.assertNotIn(bad, tcl)
        self.assertNotIn("xmutil", runner)
        self.assertIn("source_sha256_before.txt", runner)
        self.assertIn("source_sha256_after.txt", runner)
        self.assertIn("M08_PAGE_BD_EVIDENCE_DIR", runner)
        for name in FILES:
            self.assertIn(f'"{name}"', runner)
        self.assertIn("M08_PAGE_BD_GENUINE_LOCAL_VIVADO_VALIDATED_NOT_A_BITSTREAM_OR_FPGA_TEST", runner)

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_source_runner_bash_syntax(self):
        p = subprocess.run(["bash", "-n", str(RUNNER)], text=True,
                           capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    @unittest.skipUnless(shutil.which("tclsh"), "Tcl parser unavailable")
    def test_candidate_tcl_grammar_complete_without_vendor_execution(self):
        text = (
            "set fd [open {" + str(TCL) + "} r]\n"
            "set script [read $fd]\nclose $fd\n"
            'if {![info complete $script]} {puts stderr BAD_TCL; exit 2}\n'
            "puts M08_PAGE_TCL_PARSE_ONLY_NOT_VIVADO\n"
        )
        p = subprocess.run(["tclsh"], input=text, text=True,
                           capture_output=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("M08_PAGE_TCL_PARSE_ONLY_NOT_VIVADO", p.stdout)

    @unittest.skipUnless(shutil.which("tclsh"), "Tcl unavailable")
    def test_mock_project_created_before_ip_lookup_without_native_ip(self):
        with tempfile.TemporaryDirectory() as td:
            harness = r"""
set argv [list {__ROOT__} {__TEMP__}]
set ::opened 0
set ::board ""
set ::count 0
proc version {args} {return 2025.2}
proc create_project {args} {set ::opened 1}
proc current_project {} {return MOCK_PROJECT}
proc get_property {p obj} {
    if {$p eq "PART"} {return xck26-sfvc784-2LV-c}
    if {$p eq "BOARD_PART"} {return $::board}
    error "unexpected property $p"
}
proc get_board_parts {args} {
    return [list xilinx.com:kv260_som:part0:1.4]
}
proc set_property {args} {
    if {[lindex $args 0] eq "BOARD_PART"} {set ::board [lindex $args 1]}
}
proc get_ipdefs {args} {
    if {!$::opened} {error "No open project"}
    incr ::count
    return [list MOCK_IP]
}
proc add_files {args} {
    if {$::count!=5 || $::board eq ""} {error "wrong project/catalog order"}
    puts M08_PAGE_MOCK_PRE_ADD_FILES_PASS
    exit 0
}
if {[catch {source {__SCRIPT__}} e]} {
    puts stderr $e
    exit 9
}
error "Tcl did not reach mocked first source add"
""".replace("__ROOT__", str(ROOT)).replace("__TEMP__", td).replace(
                "__SCRIPT__", str(TCL))
            p = subprocess.run(["tclsh"], input=harness, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("M08_PAGE_MOCK_PRE_ADD_FILES_PASS", p.stdout)

    def test_synthetic_audit_consistency_and_tampering_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            synthetic_evidence(folder)
            result = audit_evidence(folder, ROOT)
            self.assertEqual(
                result["status"],
                "ORIGINAL_OWNER_KV260_PS_TO_SAFE_PAGE_BD_EVIDENCE_CONSISTENT")
            self.assertTrue(result["distinct_address_segments"])
            self.assertFalse(result["bitstream_programmed"])
            self.assertFalse(result["linux_mmio_performed"])
            self.assertFalse(result["kernel_dma_ownership"])
            report = folder / "02_vivado_page_bd_readback.txt"
            original = report.read_text()
            cases = (
                ("APERTURE_PAGE|/ps/Data/SEG_page_reg0|0xA0010000|0x1000",
                 "APERTURE_PAGE|/ps/Data/SEG_page_reg0|0xA0000000|0x1000"),
                ("META|compute_enabled|NO", "META|compute_enabled|YES"),
                ("META|actual_clock_hz|99999001", "META|actual_clock_hz|96968727"),
            )
            for before, after in cases:
                with self.subTest(replacement=after):
                    report.write_text(original.replace(before, after))
                    with self.assertRaises(ValueError):
                        audit_evidence(folder, ROOT)
                    report.write_text(original)
            log = folder / "01_vivado_page_bd.log"
            original_log = log.read_text()
            log.write_text(original_log.replace("\n" + MARKER + "\n", "\n"))
            with self.assertRaisesRegex(ValueError, "printed marker"):
                audit_evidence(folder, ROOT)
            log.write_text(original_log + MARKER + "\n")
            with self.assertRaisesRegex(ValueError, "printed marker"):
                audit_evidence(folder, ROOT)
            log.write_text(original_log)
            after = folder / "source_sha256_after.txt"
            after.write_text(after.read_text().replace("  ", " "))
            with self.assertRaisesRegex(ValueError, "SHA manifest"):
                audit_evidence(folder, ROOT)


if __name__ == "__main__":
    unittest.main()
