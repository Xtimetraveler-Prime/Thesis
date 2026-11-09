"""Host-only synthetic negative tests for M05.12d.3 file-backed IP output trial."""
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m05_12d3_ip_output_trial import derive,stage,PRODUCT_BLOCK
from m05_12d3_ip_output_audit import check,WIDTHS,SCOPE,TAIL,SUCCESS
BASE=ROOT/"scripts/m05_12d3_address_validate_candidate.tcl"
RUN=ROOT/"scripts/run_m05_12d3_ip_output_candidate.sh"

def fixture(tmp):
    evidence=tmp/"neuromorphic_v1_m05_12d3_ip_output_test"
    evidence.mkdir(); prj=evidence/"13_file_backed_project";prj.mkdir()
    xpr=prj/"m05_d3_output_products.xpr";xpr.write_text("SYNTHETIC NOT VIVADO")
    bd=prj/"m05_d3_output_products.srcs/bd/m05_12d3_real_signed32_hls_six_control_address_candidate.bd"
    bd.parent.mkdir(parents=True);bd.write_text("SYNTHETIC NOT VIVADO")
    out=prj/"m05_d3_output_products.gen/sources_1/ip/mem_sc_0/mem_sc_0.v"
    out.parent.mkdir(parents=True);out.write_text("SYNTHETIC NOT VIVADO")
    report="\n".join([SCOPE,"PROJECT|"+str(xpr),"BD|"+str(bd)]+[f"WIDTH|{p}|{v}" for p,v in WIDTHS]+TAIL)+"\n"
    return evidence,out,report,SUCCESS+"\n"

class M05D3IPOutputTrialTests(unittest.TestCase):
    def test_derived_tcl_project_and_widths_real_bd_and_fail_closed(self):
        original=BASE.read_text();t=derive(original)
        for fragment in ("create_project m05_d3_output_products $output_project_dir -part $part",
                         "save_bd_design","generate_target all $actual_bd",
                         "set width_report_path [lindex $argv 9]",
                         "set output_project_dir [lindex $argv 10]",
                         "get_property CONFIG.DATA_WIDTH $iface",
                         "META|converter_internals|NOT_PROVEN_BY_OUTPUT_PRODUCTS"):
            self.assertIn(fragment,t)
        self.assertNotIn("create_project -in_memory -part $part",t)
        self.assertEqual(t.count("validate_bd_design -force"),original.count("validate_bd_design -force"))
        self.assertLess(t.index("save_bd_design"),t.index("generate_target all $actual_bd"))
        with self.assertRaises(ValueError):derive(original.replace("create_project -in_memory -part $part","create_project wrong"))

    def test_staging_preserves_owner_baseline_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);dest=p/"trial.tcl";m=p/"manifest.txt"
            digest=hashlib.sha256(BASE.read_bytes()).hexdigest()
            stage(BASE,dest,m)
            self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),digest)
            self.assertIn("ORIGINAL_SIX_CONTROL_SHA256|"+digest,m.read_text())
            self.assertEqual(dest.read_text(),derive(BASE.read_text()))
            with self.assertRaises(ValueError):stage(BASE,dest,m)

    def test_synthetic_vendor_files_and_widths(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence,out,report,log=fixture(Path(temp))
            result,hashes=check(evidence,report,log)
            self.assertEqual(result["generated"],1)
            self.assertEqual(result["adapter_internals"],0)
            self.assertEqual(len(hashes),1)

    def test_corrupted_widths_missing_vendor_file_and_fake_success_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence,out,report,log=fixture(Path(temp))
            for bad in (report.replace("WIDTH|mem_sc/M00_AXI|128","WIDTH|mem_sc/M00_AXI|256"),
                        report.replace("WIDTH|mem_sc/S00_AXI|256","WIDTH|mem_sc/S00_AXI|128"),
                        report.replace("GENERATE_TARGET|all|PASS","GENERATE_TARGET|all|FAIL"),
                        report.replace("META|synthesis|NOT_RUN","META|synthesis|PASS"),
                        report.replace(SCOPE,"META|scope|FAKE"),report+"FAKE\n"):
                with self.assertRaises(ValueError):check(evidence,bad,log)
            with self.assertRaises(ValueError):check(evidence,report,"ERROR: Vivado real failure")
            out.unlink()
            with self.assertRaises(ValueError):check(evidence,report,log)

    def test_runner_requires_all_audits_and_no_hardware_actions(self):
        sh=RUN.read_text()
        for expected in ("14_ip_output_trial_generated.tcl","15_ip_output_width_readback.txt",
                         "16_ip_output_sha256_manifest.txt","17_independent_ip_output_audit.log",
                         "m05_12d3_dma_memory_audit.py","m05_12d3_address_validate_audit.py",
                         "m05_12d3_native_axis_candidate_audit.py","ip_rc="):
            self.assertIn(expected,sh)
        for forbidden in ("write_bitstream","open_hw_target","program_hw_devices",
                          "connect_hw_server","xsdb","synth_design","synth_ip","launch_runs"):
            self.assertNotIn(forbidden,sh+PRODUCT_BLOCK)
        self.assertEqual(subprocess.run(["bash","-n",str(RUN)],capture_output=True).returncode,0)

    def test_cli_missing_base_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            out=d/"tcl";m=d/"manifest"
            p=subprocess.run([sys.executable,str(ROOT/"scripts/m05_12d3_ip_output_trial.py"),
                "--base-tcl",str(d/"missing"),"--derived-tcl",str(out),"--manifest",str(m)],
                capture_output=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(out.exists())
            self.assertFalse(m.exists())
if __name__=="__main__":unittest.main()
