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


def stub_receipt(folder:Path)->None:
    folder.mkdir()
    rows="".join(
        f"{hashlib.sha256((ROOT/name).read_bytes()).hexdigest()}  {name}\n"
        for name in FILES)
    (folder/"source_sha256_before.txt").write_text(rows)
    (folder/"source_sha256_after.txt").write_text(rows)
    (folder/"result.txt").write_text("exit_status=0\n")
    (folder/"01_vivado_identity_bd.log").write_text(
        "SYNTHETIC TEST FIXTURE NOT ORIGINAL VIVADO\n"+MARKER+"\n")
    (folder/"02_vivado_identity_bd_readback.txt").write_text("\n".join((
        "META|scope|"+SCOPE,
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|requested_clock_hz|100000000",
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

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl parser unavailable")
    def test_tcl_grammar_balanced_without_loading_vendor_ip(self):
        p=ROOT/"scripts/m08_identity_ps_bd_candidate.tcl"
        script="set f [open [lindex $argv 0] r]; set t [read $f]; close $f; if {![info complete $t]} {exit 2}; puts TCL_GRAMMAR_COMPLETE"
        proc=subprocess.run(["tclsh",str(p)],capture_output=True,text=True)
        # Only the preflight argc guard should fire in standalone Tcl.
        self.assertNotEqual(proc.returncode,0)
        self.assertIn("usage:",proc.stderr)
        proc=subprocess.run(
            ["tclsh",str(ROOT/"scripts/m08_identity_ps_bd_candidate.tcl")],
            input="",capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)

    def test_fixture_checks_auditor_only_not_real_vivado(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)/"fake"
            stub_receipt(folder)
            report=audit_evidence(folder,ROOT)
            self.assertEqual(
                report["status"],
                "ORIGINAL_OWNER_VIVADO_BD_VALIDATION_EVIDENCE_CONSISTENT")
            self.assertEqual(report["ps_axi_aperture_offset"],"0xa0000000")
            self.assertFalse(report["physical_mmio_performed"])
            self.assertFalse(report["bitstream_programmed"])
            self.assertFalse(report["neural_inference_verified"])

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
