"""Strict regression for owner-original vendor A+B evidence tar auditor.

Every tar file in this suite is a SYNTHETIC FIXTURE. It is not an AMD
simulator execution and must never be promoted into a genuine RTL result.
"""
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_vendor_evidence_attest import (
    BD_SHA, SIM_SHA, PRIOR_HEAD, verify,
)


def fake_members():
    common_xelab="Vivado Simulator v2025.2\nSimulation completed.\n"
    return {
        "result.txt":"exit_status=0\n",
        "commit.txt":PRIOR_HEAD+"\n",
        "sha_before.txt":SIM_SHA+"  /FAKE/sim.sv\n"+
                         BD_SHA+"  /FAKE/bd.v\n",
        "sha_after.txt":SIM_SHA+"  /FAKE/sim.sv\n"+
                        BD_SHA+"  /FAKE/bd.v\n",
        "installed_vivado_glbl_sha256.txt":"a"*64+"  /FAKE/glbl.v\n",
        "02_original_vendor_compile_plan.json":json.dumps({
            "vivado_original_source_count":186,
            "selected_vendor_compilation_source_count":56,
            "original_include_files":["FAKE_"+str(i) for i in range(5)]}),
        "04_xelab.log":common_xelab,
        "05_xsim.log":("****** xsim v2025.2\n"
                       "M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS "
                       "writes=4 reads=14 M00_wbeats=8 M00_rbeats=28 "
                       "M00_wstalls=6 M00_rstalls=0 NO_BOARD_NO_REAL_DDR\n"
                       "exit 0\n"),
        "06_paged_xelab.log":common_xelab,
        "07_paged_xsim.log":(
            "****** xsim v2025.2\n"
            "M06_ORIGINAL_VENDOR_PAGED_RTL_PASS fills=3 wb=1 "
            "reload_byte_exact=1 M00_write=16 M00_read=48\n"
            "M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS "
            "M00_read=50 stalls=813 NO_BOARD_NO_REAL_DDR\n"
            "exit 0\n"),
    }


def make_tar(destination: Path, members: dict[str,str]) -> None:
    with tarfile.open(destination,"w:gz") as tar:
        for name,content in members.items():
            raw=content.encode()
            info=tarfile.TarInfo(name)
            info.size=len(raw)
            tar.addfile(info,io.BytesIO(raw))


class M06EvidenceAttestationSyntheticTests(unittest.TestCase):
    def test_required_log_roles_and_truthful_unproved_future_gates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"SYNTHETIC_ONLY.tar.gz"
            make_tar(p,fake_members())
            verified=verify(p)
            self.assertTrue(verified["original_sources_unchanged"])
            self.assertFalse(verified["m06_milestone_complete"])
            self.assertEqual(verified["stage_c_neural_over_original_vendor"],
                             "NOT_IN_ARCHIVE_NOT_EXECUTED")
            self.assertEqual(verified["real_physical_ddr"],"NOT_TESTED")
            self.assertEqual(verified["xsim_version"],"2025.2")

    def test_missing_vendor_result_or_bad_original_source_sha_rejected(self):
        base=fake_members()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"SYNTHETIC_ONLY.tar.gz"
            for mutate,match in (
                (("result.txt","exit_status=1\n"),"did not exit"),
                (("sha_after.txt","CHANGED\n"),"SHA changed"),
                (("commit.txt","wrong-commit\n"),"provenance"),
                (("05_xsim.log","****** xsim v2025.2\nexit 0\n"),
                 "scoreboard incomplete"),
                (("07_paged_xsim.log","****** xsim v2025.2\nexit 0\n"),
                 "page/poison checks incomplete"),
            ):
                with self.subTest(mutate=mutate[0]):
                    sample=base.copy()
                    sample[mutate[0]]=mutate[1]
                    make_tar(p,sample)
                    with self.assertRaisesRegex(ValueError,match):
                        verify(p)

    def test_missing_extra_or_directory_member_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"SYNTHETIC_ONLY.tar.gz"
            for name in ("result.txt","04_xelab.log"):
                sample=fake_members()
                sample.pop(name)
                make_tar(p,sample)
                with self.assertRaisesRegex(ValueError,"missing, extra"):
                    verify(p)
            sample=fake_members()
            sample["extra.txt"]="FAKE"
            make_tar(p,sample)
            with self.assertRaisesRegex(ValueError,"missing, extra"):
                verify(p)

    def test_original_vivado_version_and_elaboration_tool_errors_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"SYNTHETIC_ONLY.tar.gz"
            for bad,match in (
                ("ERROR: xelab failed\n","elaboration"),
                ("Vivado Simulator v2022.2\n","elaboration"),
            ):
                sample=fake_members()
                sample["06_paged_xelab.log"]=bad
                make_tar(p,sample)
                with self.assertRaisesRegex(ValueError,match):
                    verify(p)


if __name__=="__main__":
    unittest.main()
