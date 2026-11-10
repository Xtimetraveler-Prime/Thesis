"""SYNTHETIC_ONLY positive/negative evidence auditor tests, NOT AMD XSim."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m06_original_stage_e_evidence_audit import audit


def hashfile(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root: Path) -> tuple[Path, Path, Path]:
    d3 = root / "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
    d3.mkdir()
    sim = d3 / "m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0.sv"
    sub = d3 / "bd_13bd.v"
    sim.write_text("// SYNTHETIC vendor module shell only\n")
    sub.write_text("// SYNTHETIC vendor submodule shell only\n")
    out = root / "m06_original_vendor_mem_sc_xsim_SYNTHETIC_ONLY"
    out.mkdir()
    (out / "original_directory.txt").write_text(str(d3) + "\n")
    (out / "result.txt").write_text("exit_status=0\n")
    (out / "commit.txt").write_text("a" * 40 + "\n")
    sha = f"{hashfile(sim)}  {sim}\n{hashfile(sub)}  {sub}\n"
    (out / "sha_before.txt").write_text(sha)
    (out / "sha_after.txt").write_text(sha)
    glbl = root / "glbl.v"
    glbl.write_text("// installed SYNTHETIC glbl\n")
    (out / "installed_vivado_glbl_sha256.txt").write_text(f"{hashfile(glbl)}  {glbl}\n")
    (out / "tb_m06_original_vendor_4096.sv").write_text("\n".join((
        "module tb_m06_original_vendor_4096;",
        "m06_axi256_block_transfer #(.MAX_BLOCKS(256),",
        "m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536))",
        "M06_ORIGINAL_VENDOR_4096_RANGE_PASS",
        "M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS",
        "M06_VENDOR_4096_FAIL",
    )))
    (out / "03_xvlog.log").write_text("****** xvlog v2025.2\nAnalyzing tb_m06_original_vendor_4096\n")
    (out / "12_4096_xelab.log").write_text("****** xelab v2025.2\nm06_original_vendor_4096_snapshot\n")
    markers = {
        "05_xsim.log": "M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS writes=4 reads=14",
        "07_paged_xsim.log": "M06_ORIGINAL_VENDOR_PAGED_RTL_PASS fills=3 wb=1\nM06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS",
        "09_neural_paged_xsim.log": "M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS neurons=32 ticks=4\nM06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS",
        "11_lru8_xsim.log": "M06_ORIGINAL_VENDOR_LRU8_RTL_PASS slots=8\nM06_ORIGINAL_VENDOR_LRU8_FAULT_PASS",
        "13_4096_xsim.log": "M06_ORIGINAL_VENDOR_4096_RANGE_PASS highest_page=255 last_neuron=4095 last_byte=65535 dirty_wb=1 M00_write=16 M00_read=48\nM06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS block256_rejected=1 no_physical_DDR=1",
    }
    for name, marker in markers.items():
        (out / name).write_text("****** xsim v2025.2\n" + marker + "\nexit 0\n")
    return out, d3, sim


class M06OriginalStageEEvidenceSyntheticTests(unittest.TestCase):
    def test_positive_complete_run_verified_only_at_scratch_scope(self):
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            verified = audit(out)
            self.assertEqual(verified["legal_last_page"], 255)
            self.assertEqual(verified["illegal_first_page"], 256)
            self.assertEqual(len(verified["stages"]), 5)
            self.assertFalse(verified["hls_engine_instantiated"])
            self.assertFalse(verified["m06_complete"])
            self.assertEqual(verified["physical_ddr"], "NOT_ACCESSED")

    def test_negative_missing_xsim_version_and_duplicate_or_missing_markers(self):
        for old, new, pattern in (
            ("xsim v2025.2", "xsim v2024.1", "version"),
            ("M06_ORIGINAL_VENDOR_4096_RANGE_PASS", "M06_RANGE_UNKNOWN", "marker"),
            ("dirty_wb=1", "dirty_wb=0", "scoreboard"),
            ("block256_rejected=1", "block256_rejected=0", "scoreboard"),
            ("M00_read=48", "M00_read=47", "scoreboard"),
        ):
            with tempfile.TemporaryDirectory() as d, self.subTest(new=new):
                out, _, _ = fixture(Path(d))
                p = out / "13_4096_xsim.log"
                p.write_text(p.read_text().replace(old, new))
                with self.assertRaisesRegex(ValueError, pattern):
                    audit(out)
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            p = out / "13_4096_xsim.log"
            line = p.read_text().splitlines()[1]
            p.write_text(p.read_text() + line + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                audit(out)

    def test_negative_failure_after_positive_marker_or_nonzero_exit(self):
        for addendum in ("M06_VENDOR_4096_FAIL late error\n", "FATAL_ERROR\n", "exit 1\n"):
            with tempfile.TemporaryDirectory() as d, self.subTest(addendum=addendum):
                out, _, _ = fixture(Path(d))
                p = out / "13_4096_xsim.log"
                p.write_text(p.read_text() + addendum)
                with self.assertRaisesRegex(ValueError, "failure|exit"):
                    audit(out)
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            (out / "result.txt").write_text("exit_status=1\n")
            with self.assertRaisesRegex(ValueError, "exit status"):
                audit(out)

    def test_negative_original_sha_mismatch_and_source_modification(self):
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            (out / "sha_after.txt").write_text("CHANGED\n")
            with self.assertRaisesRegex(ValueError, "manifests differ"):
                audit(out)
        with tempfile.TemporaryDirectory() as d:
            out, _, sim = fixture(Path(d))
            sim.write_text("TAMPERED\n")
            with self.assertRaisesRegex(ValueError, "content no longer matches"):
                audit(out)

    def test_negative_mislabeled_generated_bench_and_compilation(self):
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            p = out / "tb_m06_original_vendor_4096.sv"
            p.write_text(p.read_text().replace("SCRATCH_BYTES(65536)", "SCRATCH_BYTES(8192)"))
            with self.assertRaisesRegex(ValueError, "generated bench"):
                audit(out)
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            p = out / "03_xvlog.log"
            p.write_text("SYNTHETIC vendor compile without E testbench\n")
            with self.assertRaisesRegex(ValueError, "compile provenance"):
                audit(out)

    def test_negative_no_commit_or_wrong_glbl_attestation(self):
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            (out / "commit.txt").write_text("not-a-commit\n")
            with self.assertRaisesRegex(ValueError, "commit"):
                audit(out)
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = fixture(Path(d))
            (out / "installed_vivado_glbl_sha256.txt").write_text("INVALID\n")
            with self.assertRaisesRegex(ValueError, "glbl"):
                audit(out)


if __name__ == "__main__":
    unittest.main()
