"""M06 closure MUST NOT merge on a recovery PASS without genuine B watchdog ZIP.

Synthetic archives exercise only evidence policy. They ARE NOT vendor proof.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))

from m06_g4_complete_evidence_gate import (
    MODES, G3_PARITY_MARKER, verify_complete, read_g3
)
from test_m06_g4_owner_zip_audit import valid_files,write_zip

def parity_data()->dict[str,str]:
    original=valid_files("g4_first_r_slverr")
    return {
        "result.txt":"exit_status=0\n",
        "commit.txt":"a"*40+"\n",
        "07_xsim.log":(
            G3_PARITY_MARKER+
            " 32_NEURONS 4_TICKS 1_CACHE_SLOT HIGH_ADDR DIRTY_EVICT "
            "B_BEFORE_AR NO_DDR_NO_BOARD\n"
            "$finish called at time : 496930 ns\nexit 0\n"),
        "original_xci_after_sha_check.txt":
            "/original/read_dwc.xci: OK\n/original/write_dwc.xci: OK\n",
        **{n:original[n] for n in
           ("hls_sources_before_sha256.txt","hls_sources_after_sha256.txt",
            "hls_dat_sources_before_sha256.txt",
            "hls_dat_sources_after_sha256.txt",
            "vendor_sha_before.txt","vendor_sha_after.txt")}
    }

def complete_fixture(folder:Path):
    parity=folder/"accepted_g3_parity_synthetic_only.zip"
    write_zip(parity,parity_data())
    paths={}
    for mode in MODES:
        path=folder/(mode+"_synthetic_only.zip")
        write_zip(path,valid_files(mode))
        paths[mode]=path
    return parity,paths,hashlib.sha256(parity.read_bytes()).hexdigest()

class M06CompleteOriginalOwnerEvidenceGateTests(unittest.TestCase):
    def test_four_mode_original_scope_acceptance_shape_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            parity,paths,digest=complete_fixture(Path(tmp))
            report=verify_complete(parity,paths,expected_g3_sha256=digest)
            self.assertEqual(report["status"],"M06_G4_ALL_ORIGINAL_OWNER_ZIPS_AUDITED")
            self.assertEqual(set(report["g4"]),set(MODES))
            self.assertIn("NO_PS_DDR_NO_BOARD",report["scope"])

    def test_missing_stalled_b_cannot_be_waived_by_later_restoration_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            parity,paths,digest=complete_fixture(Path(tmp))
            paths["g4_stalled_b"]=Path(tmp)/"NOT_UPLOADED.zip"
            with self.assertRaisesRegex(ValueError,"g4_stalled_b.*MISSING"):
                verify_complete(parity,paths,expected_g3_sha256=digest)

    def test_genuine_first_failed_stalled_b_zip_does_not_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            parity,paths,digest=complete_fixture(Path(tmp))
            bad=valid_files("g4_stalled_b")
            bad["result.txt"]="exit_status=1\n"
            bad["07_xsim.log"]="run -all\n"
            write_zip(paths["g4_stalled_b"],bad)
            with self.assertRaisesRegex(ValueError,"exit_status=0"):
                verify_complete(parity,paths,expected_g3_sha256=digest)

    def test_modified_original_vendor_identity_between_modes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            parity,paths,digest=complete_fixture(Path(tmp))
            modified=valid_files("g4_discard_restore")
            original=modified["vendor_sha_before.txt"]
            modified["vendor_sha_before.txt"]=modified["vendor_sha_after.txt"]=(
                "f"+original[1:])
            write_zip(paths["g4_discard_restore"],modified)
            with self.assertRaisesRegex(ValueError,"identity changed"):
                verify_complete(parity,paths,expected_g3_sha256=digest)

    def test_original_g3_parity_digest_attestation_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            parity,paths,digest=complete_fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError,"G3.3 accepted original owner ZIP SHA mismatch"):
                verify_complete(parity,paths,expected_g3_sha256="0"*64)

    def test_no_duplicate_zip_can_masquerade_as_two_distinct_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            parity,paths,digest=complete_fixture(Path(tmp))
            paths["g4_discard_restore"]=paths["g4_stalled_b"]
            with self.assertRaisesRegex(ValueError,"same ZIP path"):
                verify_complete(parity,paths,expected_g3_sha256=digest)

if __name__=="__main__":
    unittest.main()
