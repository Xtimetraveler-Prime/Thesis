"""Offline G4 original-owner ZIP evidence acceptance / mutation regression.

Synthetic log fixtures exercise the auditor only; NEVER represent actual
Vivado / original AMD proof and are not used by owner XSim runner.
"""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g4_owner_zip_audit import GATES, INTEGRITY, check_zip, REQUIRED_LOGS

def valid_files(mode: str) -> dict[str,str]:
    marker,tb,gen,local_count=GATES[mode]
    def digest_rows(count):
        return "".join("a"*64+"  /real/owner/file_"+str(i)+".sv\n"
                       for i in range(count))
    evidence={
        "result.txt":"exit_status=0\n",
        "commit.txt":"b"*40+"\n",
        "generated_hls_link_tb_sha256.txt":"c"*64+"  /synthetic/owner/tb.sv\n",
        tb:"// SYNTHETIC PRIVATE TB ONLY\n",
        gen:"M06_G4_GENERATION SOURCE_ONLY_NO_VENDOR_XSIM\n",
        "original_xci_after_sha_check.txt":
            "/owner/m06_g3_read_dwc.xci: OK\n"
            "/owner/m06_g3_write_dwc.xci: OK\n",
        "05_xvlog.log":"INFO: analyzing module ORIGINAL\n",
        "06_xelab.log":(
            "WARNING: [XSIM 43-3431] environment\n"
            "WARNING: [VRFC 10-5021] port 'mb_reset'\n"
            "WARNING: [VRFC 10-5021] port 'aclk2x'\n"
            "WARNING: [VRFC 10-5021] port 'aclk2x'\n"
            "Built simulation snapshot original\n"),
        "07_xsim.log":(
            marker+" NO_DDR_NO_BOARD\n"
            "$finish called at time : 1000 ns\nexit 0\n"
            "INFO: [Common 17-206] Exiting xsim\n"),
    }
    for key in REQUIRED_LOGS:
        evidence.setdefault(key,"INFO: stage\n")
    for (before,after),size in zip(INTEGRITY,(local_count,40,14,67)):
        evidence[before]=evidence[after]=digest_rows(size)
    stage_names=[
        "01_reaudit_dwc_owner.log","02_vendor_plan.log",
        "03_merge_plan.log","03_hls_original_dat_stage.log",
        "03_control_map.log","03_generation.log",gen,
        "04_xvhdl.log","05_xvlog.log","06_xelab.log","07_xsim.log",
    ]
    evidence["08_operator_invocation_console.log"]="".join(
        "M06_G3_3_1_OWNER_STAGE "+key+" rc 0\n" for key in stage_names
    )+"M06_G3_3_1_OWNER_EVIDENCE /fake/owner/path exit=0\n"
    return evidence

def write_zip(path: Path,files:dict[str,str])->None:
    with ZipFile(path,"w") as z:
        for key,value in files.items():
            z.writestr(key,value)

class G4OwnerZipFailClosedAuditTests(unittest.TestCase):
    def test_all_modes_have_synthetic_shape_validation_not_vendor_proof(self):
        for mode in GATES:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/"synthetic_test_only.zip"
                write_zip(path,valid_files(mode))
                got=check_zip(path,mode)
                self.assertEqual(got["owner_result"],"exit_status=0")
                self.assertEqual(got["xelab_warnings"],4)
                self.assertEqual(got["original_xci_count"],2)

    def test_rejects_real_first_failure_rather_than_false_accepting_timeout(self):
        for mode in GATES:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/"synthetic_first_failure.zip"
                data=valid_files(mode)
                data["result.txt"]="exit_status=1\n"
                data["07_xsim.log"]="run -all\n"
                write_zip(path,data)
                with self.assertRaisesRegex(ValueError,"exit_status"):
                    check_zip(path,mode)

    def test_rejects_tampered_manifest_and_missing_vivado_or_xci(self):
        mode="g4_stalled_b"
        for reason,mutate in (
            ("source mutation", lambda f:f.__setitem__(
                "vendor_sha_after.txt","deadbeef\n")),
            ("missing genuine XSim marker",lambda f:f.__setitem__(
                "07_xsim.log","$finish called at time : 200 ns\nexit 0\n")),
            ("missing xci",lambda f:f.__setitem__(
                "original_xci_after_sha_check.txt",
                "/original/read_dwc.xci: OK\n/write_dwc.xci: FAILED\n")),
            ("missing original stage",lambda f:f.__setitem__(
                "08_operator_invocation_console.log","FAKE\n")),
            ("unknown warning",lambda f:f.__setitem__(
                "06_xelab.log","WARNING: [NEW 1-1] mismatch\n"
                "Built simulation snapshot original\n")),
        ):
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as temp:
                files=valid_files(mode)
                mutate(files)
                path=Path(temp)/"mutated.zip"
                write_zip(path,files)
                with self.assertRaises(ValueError):
                    check_zip(path,mode)

    def test_duplicate_and_unsafe_zip_members_are_rejected(self):
        mode="g4_first_r_slverr"
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"unsafe.zip"
            files=valid_files(mode)
            files["../escape.sv"]="BAD\n"
            write_zip(path,files)
            with self.assertRaisesRegex(ValueError,"unsafe ZIP path"):
                check_zip(path,mode)

    def test_source_only_provenance_must_not_be_faked_to_accept_first_error(self):
        mode="g4_discard_restore"
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"badpass.zip"
            files=valid_files(mode)
            files[GATES[mode][2]]="FAKE-GENERATOR WITHOUT IDENTITY\n"
            write_zip(path,files)
            with self.assertRaisesRegex(ValueError,"source-only generator"):
                check_zip(path,mode)

if __name__=="__main__":
    unittest.main()
