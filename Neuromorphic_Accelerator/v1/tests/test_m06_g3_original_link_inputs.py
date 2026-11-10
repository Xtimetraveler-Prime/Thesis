"""Synthetic G3 intake tests. External HLS and AMD vendor attestations MOCKED.

These tests validate fail-closed gating only. They do NOT run original tools
or claim real generated HLS plus original SmartConnect connected RTL PASS.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from m06_g3_original_link_inputs import CANONICAL_SOURCES, PASS, verify


def fixture(root: Path):
    repo=root/"repo";repo.mkdir()
    hls=root/"m06_paged_rolling_hls_cosim_SYNTHETIC";hls.mkdir()
    vendor=root/"m06_original_vendor_mem_sc_xsim_SYNTHETIC";vendor.mkdir()
    manifest=[]
    for src in CANONICAL_SOURCES:
        path=repo/src;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("synthetic "+src+"\n")
        manifest.append(hashlib.sha256(path.read_bytes()).hexdigest()+"  "+src)
    text="\n".join(manifest)+"\n"
    (hls/"source_before_sha256.txt").write_text(text)
    (hls/"source_after_sha256.txt").write_text(text)
    (hls/"result.txt").write_text("exit_status=0\n")
    (hls/"mode.txt").write_text("cosim\n")
    (hls/"commit.txt").write_text("a"*40+"\n")
    (hls/"01_csim.log").write_text(
        "vitis-run v2025.2\nM06_PAGED_ROLLING_HLS_CSIM_PASS\nCSim done with 0 errors\n")
    (hls/"02_csynth.log").write_text("v++ v2025.2\nGenerating Verilog RTL\n")
    (hls/"03_cosim.log").write_text(
        "Using XSIM for RTL simulation\nStarting C TB testing\n"
        "Starting verilog simulation\nStarting C post checking\n"+PASS+"\n")
    return repo,hls,vendor


def stages(vendor:Path):
    return {
        "status": "ORIGINAL_VENDOR_A_E_XSIM_VERIFIED_OFFLINE_SCRATCH_ONLY",
        "m06_complete": False, "evidence_folder": str(vendor),
        "owner_commit": "b"*40,"stage_e_log_sha256":"d"*64,
    }


def lanes():
    return {"paths":[
        {"generated_hls_data_width":32,"generated_hls_address_width":64,
         "original_smartconnect_data_width":256,"required_width_adapter":True,
         "original_smartconnect_slave":"S00"},
        {"generated_hls_data_width":32,"generated_hls_address_width":64,
         "original_smartconnect_data_width":256,"required_width_adapter":True,
         "original_smartconnect_slave":"S03"},
    ]}


class M06G3InputGateSyntheticTests(unittest.TestCase):
    def run_gate(self,root:Path,portplan=None,stage=None):
        repo,hls,vendor=fixture(root)
        def do():
            with patch("m06_g3_original_link_inputs.hls_ports",return_value={
                "generated_top_sha256":"a"*64,"generated_rtl_count":37}), \
                 patch("m06_g3_original_link_inputs.width_plan",
                       return_value=lanes() if portplan is None else portplan), \
                 patch("m06_g3_original_link_inputs.vendor_stages",
                       return_value=stages(vendor) if stage is None else stage):
                return verify(hls,vendor,repo)
        return repo,hls,vendor,do

    def test_positive_valid_synthetic_metadata_not_an_integration_claim(self):
        with tempfile.TemporaryDirectory() as d:
            repo,hls,vendor,do=self.run_gate(Path(d))
            report=do()
            self.assertEqual(report["status"],
                             "REAL_HLS_COSIM_AND_ORIGINAL_AMD_A_E_READY_FOR_UNPROVEN_LINK_TRIAL")
            self.assertEqual(report["required_adapters"][0]["width_in"],32)
            self.assertEqual(report["required_adapters"][1]["original_si"],"S03")
            self.assertFalse(report["original_smartconnect_bound_to_hls"])
            self.assertFalse(report["genuine_connected_RTL_XSim"])
            self.assertFalse(report["m06_complete"])

    def test_negative_reject_prior_failed_or_only_synthesis_folder(self):
        with tempfile.TemporaryDirectory() as d:
            repo,hls,vendor,do=self.run_gate(Path(d))
            (hls/"result.txt").write_text("exit_status=1\n")
            with self.assertRaisesRegex(ValueError, "not successful"):
                do()
        with tempfile.TemporaryDirectory() as d:
            repo,hls,vendor,do=self.run_gate(Path(d))
            (hls/"mode.txt").write_text("synth\n")
            with self.assertRaisesRegex(ValueError, "not successful"):
                do()

    def test_negative_reject_source_mutation_and_hash_manifest_changes(self):
        with tempfile.TemporaryDirectory() as d:
            repo,hls,vendor,do=self.run_gate(Path(d))
            (repo/CANONICAL_SOURCES[2]).write_text("mutated HLS engine\n")
            with self.assertRaisesRegex(ValueError, "differs"):
                do()
        with tempfile.TemporaryDirectory() as d:
            repo,hls,vendor,do=self.run_gate(Path(d))
            (hls/"source_after_sha256.txt").write_text("TAMPERED\n")
            with self.assertRaisesRegex(ValueError, "changed"):
                do()

    def test_negative_reject_absent_rtl_pass_and_late_fail(self):
        for marker, replacement in (
            (PASS,"INFO: [COSIM 212-1000] *** C/RTL co-simulation finished: FAIL ***"),
            ("Starting verilog simulation","DID_NOT_RUN_VERILOG"),
            ("Starting C post checking","POSTCHECK_MISSING"),
        ):
            with tempfile.TemporaryDirectory() as d, self.subTest(marker=marker):
                repo,hls,vendor,do=self.run_gate(Path(d))
                p=hls/"03_cosim.log"
                p.write_text(p.read_text().replace(marker,replacement))
                with self.assertRaisesRegex(ValueError, "missing/duplicated"):
                    do()
        with tempfile.TemporaryDirectory() as d:
            repo,hls,vendor,do=self.run_gate(Path(d))
            p=hls/"03_cosim.log"
            p.write_text(p.read_text()+"M06_HLS_CSIM_FAIL late failure\n")
            with self.assertRaisesRegex(ValueError, "diagnostic"):
                do()

    def test_negative_reject_width_or_original_vendor_role_error(self):
        with tempfile.TemporaryDirectory() as d:
            bad=lanes();bad["paths"][0]["generated_hls_data_width"]=64
            repo,hls,vendor,do=self.run_gate(Path(d),portplan=bad)
            with self.assertRaisesRegex(ValueError, "pins changed"):
                do()
        with tempfile.TemporaryDirectory() as d:
            bad=lanes();bad["paths"][1]["original_smartconnect_slave"]="S00"
            repo,hls,vendor,do=self.run_gate(Path(d),portplan=bad)
            with self.assertRaisesRegex(ValueError, "role"):
                do()
        with tempfile.TemporaryDirectory() as d:
            repo,hls,vendor,do=self.run_gate(Path(d),stage={
                "status":"ORIGINAL_VENDOR_NOT_RUN","m06_complete":False})
            with self.assertRaisesRegex(ValueError,"Stage A-E"):
                do()

    def test_negative_cli_rejects_missing_owner_directories_without_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"SHOULD_NOT_EXIST.json"
            cmd=[sys.executable,str(ROOT/"scripts/m06_g3_original_link_inputs.py"),
                 "--hls-cosim",str(Path(d)/"missing1"),
                 "--vendor-a-e",str(Path(d)/"missing2"),
                 "--repo",str(ROOT),"--output",str(out)]
            run=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
