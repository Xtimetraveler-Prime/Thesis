"""The ONE-ZIP original-owner packager must preserve first PASS or FAIL."""
from __future__ import annotations
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from package_m06_g3_3_positive16_evidence import NAMES,package

class Positive16OwnerZipTests(unittest.TestCase):
    def test_first_pass_and_proprietary_content_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"m06_g3_3_actual_hls_positive16_xsim_first"
            folder.mkdir()
            (folder/"result.txt").write_text("exit_status=0\n")
            (folder/"07_xsim.log").write_text("genuine original vendor log\n")
            (folder/"m06_g3_3_proprietary_generated_hls.v").write_text("DO_NOT_PACKAGE")
            (folder/"m06_g3_amd_original.xci").write_text("DO_NOT_PACKAGE")
            invocation=root/"console.log"
            invocation.write_text("FIRST OWNER INVOCATION\n")
            output=root/"positive.zip"
            package(folder,invocation,output)
            with ZipFile(output) as z:
                self.assertEqual(set(z.namelist()),{
                    "result.txt","07_xsim.log",
                    "08_operator_invocation_console.log","operator_evidence_path.txt"})
                self.assertEqual(z.read("result.txt"),b"exit_status=0\n")
                self.assertEqual(z.read("operator_evidence_path.txt"),
                                 (str(folder)+"\n").encode())
            with self.assertRaisesRegex(ValueError,"overwrite"):
                package(folder,invocation,output)

    def test_first_fail_after_parser_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"m06_g3_3_actual_hls_positive16_xsim_first"
            folder.mkdir()
            (folder/"result.txt").write_text("exit_status=1\n")
            (folder/"03_control_map.log").write_text("FIRST ERROR\n")
            output=root/"failure.zip"
            package(folder,None,output)
            with ZipFile(output) as z:
                self.assertEqual(z.read("03_control_map.log"),b"FIRST ERROR\n")
                self.assertEqual(z.read("result.txt"),b"exit_status=1\n")
                self.assertNotIn("07_xsim.log",z.namelist())

    def test_pre_evidence_failure_still_uploadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            invocation=root/"inv.log"
            invocation.write_text("cannot find accepted HLS folder\n")
            output=root/"failure.zip"
            package(None,invocation,output)
            with ZipFile(output) as z:
                self.assertEqual(set(z.namelist()),{
                    "08_operator_invocation_console.log","operator_evidence_path.txt"})
                self.assertEqual(z.read("operator_evidence_path.txt"),b"NOT_CREATED\n")

    def test_parity_mode_preserves_new_owner_vector_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"m06_g3_3_actual_hls_m02_m03_parity_xsim_first"
            folder.mkdir()
            (folder/"result.txt").write_text("exit_status=1\n")
            (folder/"03_independent_m02_m03_vectors.log").write_text("ORACLE READY\n")
            (folder/"m06_g3_3_m02_m03_owner_vectors.svh").write_text("// GENERATED VECTOR\n")
            output=root/"parity.zip"
            p=subprocess.run([
                sys.executable,str(ROOT/"scripts/package_m06_g3_3_positive16_evidence.py"),
                "--mode","m02_m03_parity","--link",str(folder),
                "--output",str(output)
            ],capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("UPLOAD EXACTLY THIS ZIP:",p.stdout)
            with ZipFile(output) as z:
                self.assertEqual(z.read("result.txt"),b"exit_status=1\n")
                self.assertEqual(z.read("m06_g3_3_m02_m03_owner_vectors.svh"),
                                 b"// GENERATED VECTOR\n")

    def test_g4_first_b_slverr_zip_preserves_error_and_generated_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/"m06_g3_3_actual_hls_g4_first_b_slverr_xsim_first"
            folder.mkdir()
            (folder/"result.txt").write_text("exit_status=1\n")
            (folder/"03_g4_first_b_fault_generation.log").write_text(
                "FIRST FAULT-GENERATOR ERROR\n")
            (folder/"tb_m06_g4_actual_hls_original_amd_first_b_slverr.sv").write_text(
                "LOCAL TB ONLY\n")
            (folder/"private_vendor_ip.v").write_text("NEVER PACKAGE\n")
            output=root/"G4_FIRST.zip"
            p=subprocess.run([
                sys.executable,str(ROOT/"scripts/package_m06_g3_3_positive16_evidence.py"),
                "--mode","g4_first_b_slverr","--link",str(folder),
                "--output",str(output)
            ],capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            with ZipFile(output) as z:
                self.assertEqual(z.read("result.txt"),b"exit_status=1\n")
                self.assertEqual(
                    z.read("03_g4_first_b_fault_generation.log"),
                    b"FIRST FAULT-GENERATOR ERROR\n")
                self.assertIn("tb_m06_g4_actual_hls_original_amd_first_b_slverr.sv",
                              z.namelist())
                self.assertNotIn("private_vendor_ip.v",z.namelist())

    def test_g4_remaining_read_and_stall_immutable_first_owner_zips(self):
        for mode in ("g4_first_r_slverr","g4_stalled_b"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                folder=root/("m06_g3_3_actual_hls_"+mode+"_xsim_FIRST")
                folder.mkdir()
                (folder/"result.txt").write_text("exit_status=1\n")
                filename="tb_m06_g4_actual_hls_original_amd_"+(
                    "first_r_slverr" if mode=="g4_first_r_slverr"
                    else "stalled_b")+".sv"
                (folder/filename).write_text("SOURCE-ONLY TESTBENCH\n")
                (folder/("03_"+mode+"_generation.log")).write_text("FIRST ERROR\n")
                (folder/"ORIGINAL_AMD_PROPRIETARY.v").write_text("NO ZIP\n")
                inv=root/"console.log"
                inv.write_text("FIRST OWNER ERROR\n")
                output=root/"evidence.zip"
                p=subprocess.run([
                    sys.executable,
                    str(ROOT/"scripts/package_m06_g3_3_positive16_evidence.py"),
                    "--mode",mode,"--link",str(folder),
                    "--invocation-log",str(inv),"--output",str(output)],
                    capture_output=True,text=True,timeout=15)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                with ZipFile(output) as z:
                    self.assertEqual(z.read("result.txt"),b"exit_status=1\n")
                    self.assertIn(filename,z.namelist())
                    self.assertIn("03_"+mode+"_generation.log",z.namelist())
                    self.assertEqual(z.read("08_operator_invocation_console.log"),
                                     b"FIRST OWNER ERROR\n")
                    self.assertNotIn("ORIGINAL_AMD_PROPRIETARY.v",z.namelist())
                again=subprocess.run([
                    sys.executable,
                    str(ROOT/"scripts/package_m06_g3_3_positive16_evidence.py"),
                    "--mode",mode,"--link",str(folder),"--output",str(output)],
                    capture_output=True,text=True,timeout=15)
                self.assertEqual(again.returncode,2)
                self.assertIn("overwrite",again.stderr)

    def test_allowlist_rejects_source_payload_extensions(self):
        self.assertIn("03_positive16_generation.log",NAMES)
        self.assertIn("tb_m06_g3_3_actual_hls_original_amd_positive16.sv",NAMES)
        self.assertTrue(all(not n.endswith((".v",".xci",".dat",".vh"))
                            for n in NAMES))

if __name__=="__main__":
    unittest.main()
