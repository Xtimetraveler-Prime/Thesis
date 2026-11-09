"""Synthetic-only negative/positive gates for M05.12d.3 owner DMA memory trial."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d3_dma_memory_trial import derive, stage, MEMORY_TCL
from m05_12d3_dma_memory_audit import check, DMA, DDR_SLAVE, OCM_SLAVE, MARKER
BASE = ROOT / "scripts/m05_12d3_address_validate_candidate.tcl"
RUN = ROOT / "scripts/run_m05_12d3_dma_memory_candidate.sh"
CLI = ROOT / "scripts/m05_12d3_dma_memory_trial.py"

def fixture():
    rows = [
        "META|scope|OFFLINE_VIVADO_DMA_HP0_DDR_LOW_MAPPING_OCM_EXCLUDED",
        "SLAVE|DDR_LOW|" + DDR_SLAVE, "SLAVE|OCM|" + OCM_SLAVE,
    ]
    for name, space in DMA.items():
        rows.append(f"DDR|{name}|{DDR_SLAVE}|{space}|{space}/SEG_vendor_ddr|0x00000000|0x40000000")
        rows.append(f"OCM_EXCLUDED|{name}|{OCM_SLAVE}|{space}|{space}/SEG_vendor_ocm")
    rows.extend(["META|dma_address_width|32", "META|physical_ddr|NOT_AUTHORIZED",
                 "META|generated_smartconnect_width_adapter|NOT_YET_PROVEN"])
    return "\n".join(rows) + "\n", "VALIDATION|PASS|FULL_BD_VALIDATE_FORCE\n", MARKER + "\n"

class M0512D3DmaHp0TrialTests(unittest.TestCase):
    def test_derivative_preserves_entire_original_six_bank_candidate(self):
        original = BASE.read_text()
        generated = derive(original)
        self.assertIn('if {[llength $argv] != 9}', generated)
        self.assertIn('set dma_memory_path [lindex $argv 8]', generated)
        for term in ("assign_bd_address -target_address_space $dma_space $hp0_ddr",
                     "exclude_bd_addr_seg -target_address_space $dma_space $hp0_ocm",
                     "get_bd_addr_segs -excluded -quiet -of_objects $dma_space",
                     "get_bd_addr_segs -quiet -of_objects $ddr_master",
                     "4294967296"):
            self.assertIn(term, generated)
        self.assertEqual(generated.count("validate_bd_design -force"),
                         original.count("validate_bd_design -force"))
        self.assertEqual(generated.replace(MEMORY_TCL, "", 1).replace(
            "!= 9", "!= 8", 1).replace("set dma_memory_path [lindex $argv 8]\n", "", 1), original)

    def test_staging_creates_original_derived_sha_and_refuses_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            new, manifest = d/"10_dma_memory_trial_generated.tcl", d/"10_dma_memory_trial_source_manifest.txt"
            before = hashlib.sha256(BASE.read_bytes()).hexdigest()
            stage(BASE, new, manifest)
            self.assertEqual(before, hashlib.sha256(BASE.read_bytes()).hexdigest())
            self.assertIn("ORIGINAL_TCL_SHA256|" + before, manifest.read_text())
            self.assertIn("NOT_YET_PROVEN", manifest.read_text())
            self.assertEqual(new.read_text(), derive(BASE.read_text()))
            with self.assertRaises(ValueError):
                stage(BASE, new, manifest)

    def test_modified_baseline_fails_closed(self):
        original = BASE.read_text()
        for changed in (original.replace("# Full, genuine Vivado block-design validation.", "# altered"),
                        original.replace('if {[llength $argv] != 8}', 'if {[llength $argv] != 7}'),
                        original + '\nset dma_memory_path bogus\n',
                        original + '\nM05_D3_DMA_HP0_OFFLINE_MAPPING_PASS\n'):
            with self.assertRaises(ValueError):
                derive(changed)

    def test_independent_synthetic_report_positive(self):
        self.assertEqual(check(*fixture()), dict(dma_ddr_low_mapped=4, dma_ocm_excluded=4,
                                                  physical_ddr=0, generated_width_adapter=0))

    def test_fake_report_wrong_slave_space_missing_exclusion_and_corrupt_scope(self):
        report, valid, log = fixture()
        cases = [
            report.replace(DDR_SLAVE, "/ps/SAXIGP2/FALSE_DDR", 1),
            report.replace("DDR|dma_neurons", "DDR|dma_trace", 1),
            report.replace("/dma_trace/Data_S2MM", "/dma_trace/Data_MM2S", 1),
            report.replace("OCM_EXCLUDED|dma_external", "OCM_MAPPED|dma_external", 1),
            report.replace("META|physical_ddr|NOT_AUTHORIZED", "META|physical_ddr|AUTHORIZED"),
            report.replace("NOT_YET_PROVEN", "PROVEN"),
            report + "DDR|unexpected|fake\n",
        ]
        for fake in cases:
            with self.assertRaises(ValueError):
                check(fake, valid, log)

    def test_bad_32bit_dma_memory_range_rejected(self):
        report, valid, log = fixture()
        for fake in (report.replace("0x40000000", "0x00000000", 1),
                     report.replace("0x40000000", "0x100000001", 1),
                     report.replace("0x00000000|0x40000000", "0xF0000000|0x40000000", 1),
                     report.replace("0x40000000", "guessed", 1)):
            with self.assertRaises(ValueError):
                check(fake, valid, log)

    def test_pass_requires_vivado_pass_marker_and_memory_drc_free_log(self):
        report, valid, log = fixture()
        for broken_v, broken_log in (
            ("VALIDATION|FAIL|FULL_BD_VALIDATE_FORCE", log), ("", log),
            (valid, ""), (valid, log+"CRITICAL WARNING: [BD 41-1356] unmapped\n"),
            (valid, log+"CRITICAL WARNING: [BD 41-2909] undefined\n"),
        ):
            with self.assertRaises(ValueError):
                check(report, broken_v, broken_log)

    def test_new_runner_is_separate_safe_and_requires_all_three_audits(self):
        run = RUN.read_text()
        for item in ("m05_12d3_dma_memory_trial.py", "m05_12d3_dma_memory_audit.py",
                     "10_dma_memory_trial_generated.tcl", "11_dma_hp0_memory_readback.txt",
                     "12_independent_dma_hp0_memory_audit.log", "m05_12d3_native_axis_candidate_audit.py",
                     "m05_12d3_address_validate_audit.py", '"$DMA_TCL"',
                     "dma_rc", '"$OUT/07_full_bd_validation.txt"'):
            self.assertIn(item, run)
        for bad in ("open_hw_target", "program_hw_devices", "write_bitstream",
                    "connect_hw_server", "xsdb", "/dev/mem", "generate_target all"):
            self.assertNotIn(bad, run + MEMORY_TCL)

    def test_cli_missing_source_never_fakes_derived_tcl(self):
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp)
            output, manifest = d/"new.tcl", d/"manifest.txt"
            p = subprocess.run([sys.executable, str(CLI), "--base-tcl", str(d/"missing.tcl"),
                "--derived-tcl", str(output), "--manifest", str(manifest)],
                capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(output.exists())
            self.assertFalse(manifest.exists())

if __name__ == "__main__":
    unittest.main()
