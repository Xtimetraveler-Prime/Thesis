"""M08.2 no-board Vivado candidate and independent transcript negative tests.

The positive fixture deliberately fabricates self-consistent text. Its pass
tests the AUDITOR contract, NOT whether Vivado ran on any physical machine.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m08_identity_bd_audit import audit_evidence, FILES, MARKER, SCOPE


def stub_receipt(folder:Path,actual_clock_hz:int=99_999_001)->None:
    folder.mkdir()
    rows="".join(
        f"{hashlib.sha256((ROOT/name).read_bytes()).hexdigest()}  {name}\n"
        for name in FILES)
    (folder/"source_sha256_before.txt").write_text(rows)
    (folder/"source_sha256_after.txt").write_text(rows)
    (folder/"result.txt").write_text("exit_status=0\n")
    (folder/"01_vivado_identity_bd.log").write_text(
        "SYNTHETIC TEST FIXTURE NOT ORIGINAL VIVADO\n"
        f"M08_GENUINE_PS_PL0_CLOCK_HZ={actual_clock_hz}\n"
        f"M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ={actual_clock_hz}\n"
        +MARKER+"\n")
    (folder/"02_vivado_identity_bd_readback.txt").write_text("\n".join((
        "META|scope|"+SCOPE,
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|requested_clock_hz|100000000",
        f"META|actual_clock_hz|{actual_clock_hz}",
        "META|identity_source|rtl/m08/m08_axil_readonly_identity.v",
        "MASTER|ps/M_AXI_HPM0_FPD|/ps/Data",
        "SLAVE|identity/S_AXI|identity/S_AXI/Reg",
        "APERTURE|/ps/Data/SEG_identity_Reg|0xa0000000|0x10000",
        "META|validated_bd|YES",
        "META|routed_implementation|NOT_RUN",
        "META|bitstream|NOT_GENERATED",
        "META|ps_linux_memory_driver|NOT_CONNECTED",
        "META|physical_ddr|NOT_ACCESSED",
        "META|physical_kv260|NOT_PROGRAMMED",
    ))+"\n")
    (folder/"03_identity_bd_export.tcl").write_text(
        "# SYNTHETIC TEST FIXTURE NOT ORIGINAL VIVADO\n"+
        "set example {TCL_ONLY_SOURCE_FIXTURE}\n"*6)


class M08BDCandidateTests(unittest.TestCase):
    def test_tcl_is_ps_to_readonly_id_only_not_software_ddr(self):
        tcl=(ROOT/"scripts/m08_identity_ps_bd_candidate.tcl").read_text()
        runner=(ROOT/"scripts/run_m08_identity_bd.sh").read_text()
        rtl=(ROOT/"rtl/m08/m08_axil_readonly_identity.v").read_text()
        for keyword in (
            "xck26-sfvc784-2LV-c", "2025.2",
            "ps/M_AXI_HPM0_FPD", "ctrl_sc/S00_AXI",
            "ctrl_sc/M00_AXI", "identity/S_AXI", "validate_bd_design",
            "assign_bd_address", "get_bd_addr_segs", "C_EXT_RESET_HIGH",
            "write_bd_tcl",
        ):
            self.assertIn(keyword,tcl)
        self.assertIn("X_INTERFACE_INFO",rtl)
        self.assertIn("PROTOCOL AXI4LITE",rtl)
        # The module consumes an incoming PS-generated clock: it must not
        # hardcode an output-clock frequency on its input pin.
        self.assertNotIn("FREQ_HZ 100000000",rtl)
        self.assertIn("ASSOCIATED_BUSIF S_AXI",rtl)
        self.assertNotIn("program_hw_devices",tcl)
        self.assertNotIn("connect_hw_server",tcl)
        self.assertNotIn("write_bitstream",tcl)
        self.assertNotIn("xmutil unloadapp",runner)
        self.assertNotIn("bootfw_update",runner)
        self.assertIn("source_sha256_after.txt",runner)
        self.assertIn("M08_IDENTITY_BD_GENUINE_LOCAL_VIVADO_VALIDATED_NOT_A_BITSTREAM_OR_FPGA_TEST",runner)

    @unittest.skipUnless(shutil.which("bash"),"bash shell parser unavailable")
    def test_runner_has_valid_bash_syntax_without_running_vivado(self):
        proc=subprocess.run(
            ["bash","-n",str(ROOT/"scripts/run_m08_identity_bd.sh")],
            capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl interpreter unavailable")
    def test_unused_lpd_and_ps_clock_readbacks_before_bd_wiring(self):
        # The owner's genuine Vivado log reported BD 41-2670 and 41-758
        # from M_AXI_HPM0_LPD/maxihpm0_lpd_aclk despite FPD HPM0 wiring.
        # The next genuine run emitted BD 41-237/238, as PS PL0 delivered
        # 96968727 Hz while first-party AXI metadata declared 100000000 Hz.
        # Tcl mocks model only parameter negotiation and rejection, not
        # genuine AMD IP initialization or validate_bd_design.
        script=ROOT/"scripts/m08_identity_ps_bd_candidate.tcl"
        with tempfile.TemporaryDirectory() as td:
            harness=r"""
set argv [list {__ROOT__} {__EVIDENCE__}]
set ::project_open 0
set ::refuse_disable __REFUSE_DISABLE__
set ::actual_ps_clock_hz __PS_CLOCK_HZ__
set ::board_found __BOARD_FOUND__
set ::board_part ""
set ::board_preset_applied 0
set ::ip_checks 0
set ::lpd_interface_lookups 0
set ::lpd_clock_lookups 0
array set ::pscfg {CONFIG.PSU__USE__M_AXI_GP0 0 CONFIG.PSU__USE__M_AXI_GP1 1 CONFIG.PSU__USE__M_AXI_GP2 1 CONFIG.PSU__FPGA_PL0_ENABLE 0 CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 96.968727 CONFIG.PSU__MAXIGP0__DATA_WIDTH 128}
proc version {opt} {return 2025.2}
proc create_project {args} {set ::project_open 1}
proc current_project {} {return mocked_project}
proc get_board_parts {args} {
    if {$::board_found} {return [list xilinx.com:kv260_som:part0:1.4]}
    return {}
}
proc set_property {args} {
    if {[lindex $args 0] eq "BOARD_PART"} {
        set ::board_part [lindex $args 1]
    }
    if {[lindex $args 0] eq "-dict"} {
        if {!$::board_preset_applied} {
            error "M08 mock: board preset must be applied before PS overrides"
        }
        foreach {key val} [lindex $args 1] {
            if {$key eq "CONFIG.PSU__USE__M_AXI_GP2" && $::refuse_disable} {
                continue
            }
            set ::pscfg($key) $val
        }
    }
}
proc get_property {name obj} {
    if {$name eq "PART"} {return xck26-sfvc784-2LV-c}
    if {$name eq "BOARD_PART"} {return $::board_part}
    if {$name eq "MODE" && $obj eq "ps/M_AXI_HPM0_FPD"} {return MASTER}
    if {$name eq "CONFIG.FREQ_HZ" && $obj eq "ps/pl_clk0"} {
        return $::actual_ps_clock_hz
    }
    if {[info exists ::pscfg($name)]} {return $::pscfg($name)}
    error "unexpected property $name"
}
proc get_ipdefs {args} {
    if {!$::project_open} {error "No open project"}
    incr ::ip_checks
    return [list mocked_ip]
}
proc add_files {args} {}
proc update_compile_order {args} {}
proc create_bd_design {args} {}
proc apply_bd_automation {args} {
    if {$::board_part eq ""} {error "M08 mock: no board part"}
    if {[lsearch -exact $args "apply_board_preset \"1\""] < 0} {
        error "M08 mock: KV260 PS board preset not requested"
    }
    set ::board_preset_applied 1
}
proc get_bd_intf_pins {args} {
    set name [lindex $args end]
    if {$name eq "ps/M_AXI_HPM0_FPD"} {return [list $name]}
    if {$name eq "ps/M_AXI_HPM1_FPD"} {
        if {$::pscfg(CONFIG.PSU__USE__M_AXI_GP1) eq "1"} {return [list $name]}
    }
    if {$name eq "ps/M_AXI_HPM0_LPD"} {
        incr ::lpd_interface_lookups
        if {$::pscfg(CONFIG.PSU__USE__M_AXI_GP2) eq "1"} {return [list $name]}
    }
    return {}
}
proc get_bd_pins {args} {
    set name [lindex $args end]
    if {$name eq "ps/pl_clk0"} {return [list $name]}
    if {$name eq "ps/maxihpm1_fpd_aclk"} {
        if {$::pscfg(CONFIG.PSU__USE__M_AXI_GP1) eq "1"} {return [list $name]}
    }
    if {$name eq "ps/maxihpm0_lpd_aclk"} {
        incr ::lpd_clock_lookups
        if {$::pscfg(CONFIG.PSU__USE__M_AXI_GP2) eq "1"} {return [list $name]}
    }
    return {}
}
proc create_bd_cell {args} {
    if {[lsearch -exact $args "-reference"] >= 0} {
        if {$::ip_checks != 5 ||
            !$::board_preset_applied ||
            $::board_part ne "xilinx.com:kv260_som:part0:1.4" ||
            $::pscfg(CONFIG.PSU__USE__M_AXI_GP0) ne "1" ||
            $::pscfg(CONFIG.PSU__USE__M_AXI_GP1) ne "0" ||
            $::pscfg(CONFIG.PSU__USE__M_AXI_GP2) ne "0" ||
            $::pscfg(CONFIG.PSU__FPGA_PL0_ENABLE) ne "1" ||
            $::pscfg(CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ) ne "100" ||
            abs($::actual_ps_clock_hz - 100000000) > 1000 ||
            $::lpd_interface_lookups != 1 ||
            $::lpd_clock_lookups != 1} {
            error "missing explicit PS-only-FPD guard or probe"
        }
        puts M08_MOCK_FPD_ONLY_LPD_DISABLED_PASS
        exit 0
    }
    return ps
}
if {[catch {source {__SCRIPT__}} err]} {
    puts stderr "M08_TCL_LPD_BOUNDARY_ERROR: $err"
    exit 9
}
error "Tcl missed identity-cell stop"
"""
            cases=((False,99999001,True), (False,100000000,True),
                   (True,100000000,True), (False,96968727,True),
                   (False,99998999,True), (False,100000000,False))
            for refuse_disable, clock_hz, board_found in cases:
                with self.subTest(refuse_disable=refuse_disable,
                                  actual_ps_clock_hz=clock_hz,
                                  board_found=board_found):
                    t=(harness.replace("__ROOT__",str(ROOT))
                              .replace("__EVIDENCE__",td)
                              .replace("__SCRIPT__",str(script))
                              .replace("__REFUSE_DISABLE__",
                                       "1" if refuse_disable else "0")
                              .replace("__PS_CLOCK_HZ__",str(clock_hz))
                              .replace("__BOARD_FOUND__",
                                       "1" if board_found else "0"))
                    proc=subprocess.run(["tclsh"],input=t,
                                        capture_output=True,text=True)
                    if not board_found:
                        self.assertNotEqual(proc.returncode,0)
                        self.assertIn(
                            "M08 requires installed KV260 SOM board files",
                            proc.stderr)
                    elif refuse_disable:
                        self.assertNotEqual(proc.returncode,0)
                        self.assertIn(
                            "M08 unused PS HPM0 LPD master could not be disabled",
                            proc.stderr)
                    elif abs(clock_hz-100000000)>1000:
                        self.assertNotEqual(proc.returncode,0)
                        self.assertIn(
                            "M08 PS PL0 actual FREQ_HZ outside 1000 Hz budget:",
                            proc.stderr)
                        self.assertIn(str(clock_hz),proc.stderr)
                        self.assertNotIn(
                            "M08_MOCK_FPD_ONLY_LPD_DISABLED_PASS",proc.stdout)
                    else:
                        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
                        self.assertIn(
                            f"M08_GENUINE_PS_PL0_CLOCK_HZ={clock_hz}",proc.stdout)
                        self.assertIn(
                            f"M08_PS_PL0_CLOCK_DEVIATION_HZ={abs(clock_hz-100000000)}",
                            proc.stdout)
                        self.assertIn(
                            "M08_MOCK_FPD_ONLY_LPD_DISABLED_PASS",proc.stdout)

    def test_explicit_ps_pl0_clock_request_preserves_fpd_only_topology(self):
        tcl=(ROOT/"scripts/m08_identity_ps_bd_candidate.tcl").read_text()
        # Based on accepted Loihi v2 P03/P04/P05/P08: select an actual
        # KV260 board part and run the PS preset BEFORE explicit clock and
        # FPD-only AXI selection; do not import the Loihi neural/DDR topology.
        self.assertIn("CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100",tcl)
        self.assertIn("CONFIG.PSU__FPGA_PL0_ENABLE 1",tcl)
        self.assertIn("get_property CONFIG.FREQ_HZ [pin_required ps/pl_clk0]",tcl)
        self.assertIn("M08 PS PL0 actual FREQ_HZ outside 1000 Hz budget:",tcl)
        self.assertIn("set maximum_clock_deviation_hz 1000",tcl)
        self.assertIn("M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ=",tcl)
        self.assertIn("get_property CONFIG.FREQ_HZ $endpoint",tcl)
        self.assertIn('"META|actual_clock_hz|$ps_clock_hz"',tcl)
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP0 1",tcl)
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP2 0",tcl)
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP1 0",tcl)
        self.assertIn("get_board_parts -quiet xilinx.com:kv260_som:part0:*",tcl)
        self.assertIn("set_property BOARD_PART $kv260_board_part [current_project]",tcl)
        self.assertIn('apply_board_preset "1"',tcl)
        self.assertLess(tcl.index("get_board_parts -quiet"),
                        tcl.index("create_bd_design"))
        self.assertLess(tcl.index("apply_bd_automation -rule"),
                        tcl.index("CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100"))
        self.assertNotIn("write_bitstream",tcl)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl interpreter unavailable")
    def test_ip_catalog_query_occurs_only_after_open_project(self):
        # Regression for the owner's actual Vivado 2025.2 Common 17-53
        # failure. Mock only the pre-add_files Tcl boundary: real Vivado IP
        # discovery and BD validation STILL require the separate owner run.
        with tempfile.TemporaryDirectory() as td:
            script=ROOT/"scripts/m08_identity_ps_bd_candidate.tcl"
            harness=r"""
set argv [list {__ROOT__} {__EVIDENCE__}]
set ::project_open 0
set ::ip_checks 0
proc version {flag} {return 2025.2}
proc create_project {args} {set ::project_open 1}
proc current_project {} {return mocked_project}
set ::mock_board_part ""
proc get_board_parts {args} {return [list xilinx.com:kv260_som:part0:1.4]}
proc set_property {args} {
    if {[lindex $args 0] eq "BOARD_PART"} {
        set ::mock_board_part [lindex $args 1]
    }
}
proc get_property {name obj} {
    if {$name eq "PART"} {return xck26-sfvc784-2LV-c}
    if {$name eq "BOARD_PART"} {return $::mock_board_part}
    error "unexpected property $name"
}
proc get_ipdefs {args} {
    if {!$::project_open} {
        error "No open project. Please create or open a project before executing this command."
    }
    incr ::ip_checks
    return [list mocked_amd_ip]
}
proc add_files {args} {
    if {$::ip_checks != 5} {
        error "expected all five AMD IP lookups before source addition"
    }
    puts M08_MOCK_PROJECT_BEFORE_CATALOG_PASS
    exit 0
}
if {[catch {source {__SCRIPT__}} err]} {
    puts stderr "M08_TCL_BOUNDARY_ERROR: $err"
    exit 9
}
error "script skipped the add_files guard"
"""
            harness=(harness.replace("__ROOT__",str(ROOT))
                           .replace("__EVIDENCE__",td)
                           .replace("__SCRIPT__",str(script)))
            proc=subprocess.run(["tclsh"],input=harness,
                                capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            self.assertIn("M08_MOCK_PROJECT_BEFORE_CATALOG_PASS",proc.stdout)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl parser unavailable")
    def test_tcl_grammar_balanced_without_loading_vendor_ip(self):
        p=ROOT/"scripts/m08_identity_ps_bd_candidate.tcl"
        # Parse all Tcl braces/quote/command boundaries without executing a
        # single Vivado operation. Running the actual script under tclsh
        # would only test its initial argument guard and miss the body.
        text=(
            "set fd [open {"+str(p)+"} r]\n"
            "set body [read $fd]\n"
            "close $fd\n"
            "if {![info complete $body]} {puts stderr INCOMPLETE_TCL; exit 2}\n"
            "puts TCL_GRAMMAR_COMPLETE\n"
        )
        proc=subprocess.run(["tclsh"],input=text,
                             capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertIn("TCL_GRAMMAR_COMPLETE",proc.stdout)

    def test_fixture_checks_auditor_only_not_real_vivado(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"fake"
            stub_receipt(folder)
            report=audit_evidence(folder,ROOT)
            self.assertEqual(
                report["status"],
                "ORIGINAL_OWNER_VIVADO_BD_VALIDATION_EVIDENCE_CONSISTENT")
            self.assertEqual(report["ps_axi_aperture_offset"],"0xa0000000")
            self.assertEqual(report["actual_clock_hz"],99_999_001)
            self.assertEqual(report["actual_clock_deviation_hz"],999)
            self.assertEqual(report["requested_clock_hz"],100_000_000)
            self.assertFalse(report["physical_mmio_performed"])
            self.assertFalse(report["bitstream_programmed"])
            self.assertFalse(report["neural_inference_verified"])

    def test_reject_outside_clock_budget_or_missing_propagation_evidence(self):
        for bad_clock in (99_998_999,100_001_001,96_968_727,-1,0):
            with self.subTest(actual_clock_hz=bad_clock):
                with tempfile.TemporaryDirectory() as td:
                    folder=Path(td)/"fake"
                    stub_receipt(folder,actual_clock_hz=bad_clock)
                    with self.assertRaisesRegex(ValueError,"clock"):
                        audit_evidence(folder,ROOT)
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"fake"
            stub_receipt(folder)
            proof=folder/"01_vivado_identity_bd.log"
            proof.write_text(proof.read_text().replace(
                "M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ=99999001",""))
            with self.assertRaisesRegex(ValueError,"clock"):
                audit_evidence(folder,ROOT)
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"fake"
            stub_receipt(folder)
            report=folder/"02_vivado_identity_bd_readback.txt"
            report.write_text(report.read_text().replace(
                "META|actual_clock_hz|99999001",
                "META|actual_clock_hz|99999002"))
            with self.assertRaisesRegex(ValueError,"clock"):
                audit_evidence(folder,ROOT)

    def test_reject_bad_source_result_or_log(self):
        mutants=(
            ("result.txt","exit_status=1\n"),
            ("source_sha256_after.txt","bad\n"),
            ("01_vivado_identity_bd.log","ERROR: failed\n"),
            ("02_vivado_identity_bd_readback.txt","fake\n"),
        )
        for name,bad in mutants:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as td:
                    folder=Path(td)/"fake"
                    stub_receipt(folder)
                    (folder/name).write_text(bad)
                    with self.assertRaises(ValueError):
                        audit_evidence(folder,ROOT)

    def test_reject_bad_address_and_false_physical_claims(self):
        edits=(
            ("|0xa0000000|0x10000","|0xffffff00|0x10000"),
            ("|0xa0000000|0x10000","|0xa0000001|0x10000"),
            ("|0xa0000000|0x10000","|0xa0000000|0x0"),
            ("NOT_GENERATED","GENERATED"),
            ("NOT_ACCESSED","DDR_WRITTEN"),
            ("NOT_PROGRAMMED","PROGRAMMED"),
        )
        for old,new in edits:
            with self.subTest(edit=(old,new)):
                with tempfile.TemporaryDirectory() as td:
                    folder=Path(td)/"fake"
                    stub_receipt(folder)
                    path=folder/"02_vivado_identity_bd_readback.txt"
                    self.assertIn(old,path.read_text())
                    path.write_text(path.read_text().replace(old,new))
                    with self.assertRaises(ValueError):
                        audit_evidence(folder,ROOT)

    def test_cli_rejects_failed_evidence_without_creating_pass(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"fake"
            stub_receipt(folder)
            (folder/"result.txt").write_text("exit_status=2\n")
            dest=folder/"04_audit.json"
            cmd=[sys.executable,str(ROOT/"scripts/m08_identity_bd_audit.py"),
                 "--evidence-dir",str(folder),"--source-root",str(ROOT),
                 "--output",str(dest)]
            proc=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertFalse(dest.exists())


if __name__=="__main__":
    unittest.main()
