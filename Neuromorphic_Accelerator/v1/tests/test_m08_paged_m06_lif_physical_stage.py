"""M08.4 native evidence triage and STAGED but NOT RELEASED one-shot hardware source.

No tests run Vivado hardware manager, invoke JTAG, or touch owner evidence.
Any real hardware claim must await original first-image DRC/timing/clock
release and an independently captured first physical run.
"""
from __future__ import annotations

from pathlib import Path
import importlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as fixture
import m08_paged_m06_lif_physical_vectors as vectors
import m08_paged_m06_lif_physical_readiness as triage
import m08_paged_m06_lif_physical_audit as auditor

TCL=ROOT/"scripts/m08_paged_m06_lif_physical_once.tcl"
SH=ROOT/"scripts/run_m08_paged_m06_lif_physical_once.sh"

class M084PagedPhysicalStagingTests(unittest.TestCase):
    def test_native_readiness_must_remain_blocked_without_image_review(self):
        source=(ROOT/"scripts/m08_paged_m06_lif_physical_readiness.py").read_text()
        self.assertEqual(triage.OWNER_DIR,"m08_paged_m06_lif_QFKpXlPW")
        self.assertEqual(triage.OWNER_BIT_SHA,auditor.EXPECTED_BIT_SHA)
        self.assertEqual(len(triage.OWNER_BIT_SHA),64)
        self.assertIn('physical_programming_authorized": False',source)
        self.assertIn("BLOCKED_PENDING_EXACT_NEW_IMAGE_DRC_TIMING_CLOCK_REVIEW",source)
        self.assertNotIn("program_hw_devices",source)
        self.assertNotIn("open_hw_manager",source)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((triage.Reject,ValueError,OSError)):
                triage.inspect(Path(d))

    def test_one_shot_physical_tcl_is_source_staged_with_exact_new_bit(self):
        code=TCL.read_text()
        self.assertEqual(len(re.findall(r"(?m)^\s*program_hw_devices\s+\$fpga\s*$",code)),1)
        self.assertIn("M08_4_IMAGE_RELEASE",code)
        self.assertIn("M08_4_PROGRAM_ONCE",code)
        self.assertIn("M08_4_PREFLIGHT_CONFIRMED",code)
        self.assertIn(triage.OWNER_BIT_SHA,code)
        self.assertIn("m08_paged_m06_lif_QFKpXlPW",code)
        self.assertIn("A0001000",code)
        self.assertIn("A0001014",code)
        self.assertIn("A0001100",code)
        self.assertIn("A0000000",code)
        self.assertIn("M08_4_PHYSICAL_256B_LOAD_COMPUTE_FULL_DIRTY_SAVE",code)
        self.assertIn("M08_4_PHYSICAL_ORDERED_TICK_BARRIER",code)
        self.assertIn("20_independent_512_oracle_ONLY.hex",code)
        self.assertIn("external_ingress=HOST_COALESCED_NOT_RAW_EVENT_FIFO",code)
        self.assertNotIn("/dev/mem",code)
        self.assertNotIn("xmutil ",code)
        self.assertNotIn("dma_alloc_coherent",code)
        self.assertNotIn("run_program_twice",code)

    def test_shell_requires_missing_new_image_specific_native_gate_before_jtag(self):
        text=SH.read_text()
        self.assertIn("m08_paged_m06_lif_exact_native_accept.py",text)
        self.assertTrue((ROOT/"scripts/m08_paged_m06_lif_exact_native_accept.py").is_file(),
                        "exact new owner-image release gate must exist before physical runner")
        self.assertLess(text.index('if [[ ! -f "$EXACT_GATE"'),text.index('HW="$(mktemp -d'))
        self.assertLess(text.index('python3 "$EXACT_GATE"'),text.index('HW="$(mktemp -d'))
        self.assertIn("M08_4_PROGRAM_ONCE",text)
        self.assertIn("M08_4_PREFLIGHT_CONFIRMED",text)
        self.assertIn("M08_4_PHYSICAL_STOP_NO_AUTO_RETRY_PRESERVE_ORIGINAL",text)
        self.assertIn('sha256sum -c 99_evidence_sha256.txt',text)
        self.assertIn("m08_paged_m06_lif_physical_audit.py",text)
        p=subprocess.run(["bash","-n",str(SH)],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_original_oracle_is_comparison_only_not_staged_as_neural_state(self):
        with tempfile.TemporaryDirectory() as td:
            home=Path(td)
            evidence=home/"Thesis_Evidence"/"M08"
            evidence.mkdir(parents=True)
            out=evidence/"m08_paged_m06_lif_HW_XY123abc"
            out.mkdir()
            with mock.patch.object(Path,"home",return_value=home):
                result=vectors.generate(out)
                self.assertEqual(result["oracle_comparisons"],512)
                self.assertEqual(result["host_input_current_comparisons"],128)
                self.assertEqual(result["pl_computed_voltage_spike_recurrent_comparisons"],384)
                self.assertFalse(result["hardware_test_executed"])
                for p in range(6):
                    lines=(out/f"11_neural_page_{p}_input.hex").read_text().splitlines()
                    self.assertEqual(lines,[f"{w:08X}" for w in fixture.neural_words(p)])
                golden=(out/"20_independent_512_oracle_ONLY.hex").read_text().splitlines()
                self.assertEqual(golden,[f"{w:08X}" for w in fixture.golden_words()])
                self.assertEqual(len(golden),512)
                self.assertEqual(len((out/"10_edge_config_input.hex").read_text().splitlines()),64)
                with self.assertRaises((fixture.Reject,OSError)):
                    vectors.generate(out)

    def test_auditor_requires_13_real_original_receipts_and_record_grammar(self):
        self.assertEqual(len(auditor.NAMES),13)
        self.assertEqual(len(set(auditor.NAMES)),13)
        self.assertIn("01_jtag_paged_m06.log",auditor.NAMES)
        self.assertIn("80_physical_paged_neural_parity.txt",auditor.NAMES)
        good="tick=0 page=0 neuron=0 input=00000000 voltage=FFFFFFFF mask=00000001 recurrent=00000000"
        self.assertIsNotNone(auditor.OBS.fullmatch(good))
        self.assertIsNone(auditor.OBS.fullmatch(good+" PASS"))
        self.assertIsNone(auditor.OBS.fullmatch(good.replace("recurrent=","ddr=")))
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((auditor.Reject,OSError,ValueError)):
                auditor.inspect(Path(d),Path(d))

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl source grammar parser unavailable")
    def test_physical_tcl_source_is_complete_without_any_vendor_or_jtag_call(self):
        script=(
            "set f [open {"+str(TCL)+"} r]\n"+
            "set t [read $f]\nclose $f\n"+
            "if {![info complete $t]} {exit 7}\n"+
            "puts M08_4_STAGED_TCL_GRAMMAR_ONLY_NO_PROGRAM\n"
        )
        p=subprocess.run(["tclsh"],input=script,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn("M08_4_STAGED_TCL_GRAMMAR_ONLY_NO_PROGRAM",p.stdout)

if __name__=="__main__":
    unittest.main()
