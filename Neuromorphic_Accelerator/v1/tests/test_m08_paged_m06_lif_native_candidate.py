"""M08.4 PC-only new Vivado source/build safety, never hardware release."""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_source_gate as source_gate
import m08_paged_m06_lif_native_review as reviewer

BUILDER=ROOT/"scripts/m08_paged_m06_lif_build.tcl"
RUNNER=ROOT/"scripts/run_m08_paged_m06_lif_pc.sh"
REVIEW=ROOT/"scripts/m08_paged_m06_lif_native_review.py"
ENGINE=ROOT/"rtl/m08/m08_paged_m06_lif_engine.v"

class M084NativeFirstImageTests(unittest.TestCase):
    def test_source_gate_remains_explicitly_not_physical(self):
        data=source_gate.inspect()
        self.assertEqual(data["status"],
                         "M08_4_PAGED_SIGNED16_32x4_M06_SOURCE_CANDIDATE_NO_BOARD")
        self.assertEqual(data["independently_required_numerical_results"],512)
        self.assertEqual((data["logical_neural_pages"],data["resident_neural_pages"]),(6,1))
        self.assertFalse(data["owner_bitstream_release_allowed"])
        self.assertFalse(data["physical_KV260_page_neural_execution"])

    def test_new_vivado_builder_reuses_safe_accepted_topology_but_no_board(self):
        code=BUILDER.read_text()
        for key in (
            "2025.2", "xck26-sfvc784-2LV-c", "get_board_parts",
            "m08_paged_m06_lif_shell","m08_paged_m06_lif_engine",
            "m08_axil_page_control.sv","m08_host_staged_page_bank.sv",
            "m08_d3c_fabric_por.v","fabric_por/aresetn",
            "get_bd_intf_pins -quiet lif/S_AXI","CONFIG.NUM_MI 2",
            "CONFIG.NUM_SI 1","jtag_axi/M_AXI","bram_ctrl/BRAM_PORTA",
            "CONFIG.PSU__TTC0__WAVEOUT__ENABLE 1",
            "CONFIG.PSU__USE__M_AXI_GP0 0",
            "M08_FAN_PWM","PACKAGE_PIN A12","validate_bd_design",
            "route_design","report_drc","report_timing_summary",
            "report_utilization","report_clocks","write_bitstream",
            "source_receipts", "new_image_owner_drc_review=REQUIRED",
            "physical_jtag_test_authorized=NO",
            "hardware_bitstream_programmed=NO",
            "external_input_ingress=HOST_COALESCED_NO_RAW_EVENT_FIFO_IN_THIS_IMAGE",
            "m08_paged_m06_lif_jtag_UNRELEASED.bit",
        ):
            with self.subTest(key=key):
                self.assertIn(key,code)
        for forbidden in ("program_hw_devices","open_hw_manager","run_hw_axi",
                          "connect_hw_server","/dev/mem","dma_alloc_coherent"):
            self.assertNotIn(forbidden,code)

    def test_owner_runner_is_offline_source_gated_and_15_original_sha_entries(self):
        shell=RUNNER.read_text()
        p=subprocess.run(["bash","-n",str(RUNNER)],
                         capture_output=True,text=True,timeout=8)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        for key in ("set -euo pipefail","mktemp -d",
                    "m08_paged_m06_lif_XXXXXXXX",
                    "test_m08_paged_m06_lif_fail_closed.py",
                    "test_m08_paged_m06_lif.py",
                    "m08_paged_m06_lif_source_gate.py",
                    "m08_paged_m06_lif_build.tcl",
                    "m08_paged_m06_lif_native_review.py",
                    "sha256sum -c 99_evidence_sha256.txt",
                    "M08_4_NO_BOARD_NO_JTAG_NO_DDR_NO_RELEASE"):
            self.assertIn(key,shell)
        for forbidden in ("program_hw_devices","open_hw_manager","run_hw_axi",
                          "sudo ","/dev/mem"):
            self.assertNotIn(forbidden,shell)
        self.assertEqual(len(reviewer.NAMES),15)
        for name in reviewer.NAMES:
            self.assertIn(name,shell)
        self.assertEqual(len(reviewer.SOURCE_MAP),5)

    def test_vivado_decimal_literal_ternary_lexer_boundary(self):
        """Vivado parses 3'd5? as an invalid decimal token, not a ternary."""
        code=ENGINE.read_text()
        bad_literal=r"\b\d+'[sS]?[dD][0-9_]+\?"
        # Mutation control: the actual first owner-native synthesis error.
        self.assertIsNotNone(re.search(bad_literal,"(expected_page==3'd5?32'd2:32'd6)"))
        self.assertIsNone(re.search(bad_literal,code),
                          "Sized decimal literal touches ternary ?: Vivado Synth 8-10871")
        self.assertIn("(expected_page == 3'd5 ?",code)
        self.assertIn("32'd2 : 32'd6)",code)

    @unittest.skipUnless(shutil.which("iverilog"),"Icarus needed for strict Verilog-2001 grammar")
    def test_engine_parses_as_verilog_2001_not_only_systemverilog(self):
        p=subprocess.run(
            ["iverilog","-g2001","-tnull","-s","m08_paged_m06_lif_engine",str(ENGINE)],
            capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stdout+"\n"+p.stderr)
        self.assertEqual(p.stderr.strip(),"", "Verilog-2001 parse warnings require review")

    def test_first_new_owner_image_cannot_be_source_approved(self):
        text=REVIEW.read_text()
        self.assertIn("return 2",text)
        self.assertIn('"image_specific_gate":"BLOCKED"',text)
        self.assertIn('"physical_programming_authorized":False',text)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(reviewer.Reject):
                reviewer.inspect(Path(temp))

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl parser unavailable")
    def test_builder_is_syntactically_complete_without_routing(self):
        text=(
            "set f [open {"+str(BUILDER)+"} r]\n"
            "set contents [read $f]\n"
            "close $f\n"
            "if {![info complete $contents]} {exit 7}\n"
            "puts M08_4_TCL_GRAMMAR_COMPLETE_NO_VIVADO\n"
        )
        out=subprocess.run(["tclsh"],input=text,capture_output=True,
                           text=True,timeout=8)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
        self.assertIn("M08_4_TCL_GRAMMAR_COMPLETE_NO_VIVADO",out.stdout)

if __name__=="__main__":
    unittest.main()
