"""M32Q first-image gate: synthetic provenance tests NEVER authorize hardware."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_d3d2e_queue_native_review as review

class D3D2ENativeAlwaysBlockedTests(unittest.TestCase):
    def make_run(self, home):
        base = home / "Thesis_Evidence/M08"
        base.mkdir(parents=True)
        run = base / "m08_d3d2e_queue_ABCDEFGH"
        run.mkdir()
        (run / "reports").mkdir()
        (run / "bitstream_candidate").mkdir()
        data = {
            name: (b"NEW-M32Q-SYNTHETIC-MOCK" + name.encode())
            for name in review.FILES
        }
        data["02_vivado_exit.txt"] = b"vivado_build_exit=0\n"
        data["reports/11_fabric_por.v"] = review.POR.read_bytes()
        data["reports/12_synaptic_lif_axil.v"] = review.RTL.read_bytes()
        data[review.BIT] = b"MOCK-ONLY-NOT-A-REAL-BIT" * 6000
        fields = {
            "schema": "m08-d3d2e-tick-queue-32-offline-build-v1",
            "wrapper_top": "m08_d3d2e_queue_lif_jtag_wrapper",
            "physical_neurons": "32", "physical_ticks": "4",
            "m06_original_edges": "5", "m06_original_external_events": "17",
            "event_fifo_capacity": "32", "event_mailbox_lifetime_capacity": "64",
            "queue_ingress_accepted_separate_from_service": "YES",
            "queue_service_tick_barriers": "4",
            "ps_to_pl_hpm": "DISABLED", "physical_event_stream_dma": "NO",
            "physical_m06_ddr": "NO", "ps_clock_dependency": "YES",
            "ps_pl0_clock_request_hz": "100000000",
            "ps_pl0_runtime_clock_proven": "NO",
            "new_image_owner_drc_review": "REQUIRED",
            "asynchronous_clock_domain_proven": "NO",
            "hardware_bitstream_programmed": "NO",
            "hardware_neural_execution_proven": "NO",
            "part": "xck26-sfvc784-2LV-c",
            "lif_base": "0xA0001000", "bram_map_base": "0xA0000000",
            "reset_mode": "FABRIC_POR_256_CYCLES",
            "vivado_version": "2025.2",
            "builder_sha256": sha256(review.BUILD.read_bytes()).hexdigest(),
            "lif_rtl_sha256": sha256(review.RTL.read_bytes()).hexdigest(),
            "fabric_por_rtl_sha256": sha256(review.POR.read_bytes()).hexdigest(),
            "bitstream_size_bytes": str(len(data[review.BIT])),
        }
        data["reports/30_native_result.txt"] = (
            "".join(k+"="+v+"\n" for k,v in fields.items()).encode()
        )
        for name,payload in data.items():
            (run / name).write_bytes(payload)
        self.rehash(run)
        return run

    def rehash(self, run):
        (run / "99_evidence_sha256.txt").write_text(
            "".join(sha256((run / n).read_bytes()).hexdigest() + "  " + n + "\n"
                    for n in review.FILES), encoding="ascii")

    def test_valid_12_hash_synthetic_is_still_review_only(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            run = self.make_run(home)
            with patch.object(Path, "home", return_value=home):
                out = review.inspect(run)
            self.assertEqual(out["sha_ledger_rows_verified"], 12)
            self.assertEqual(out["image_specific_gate"], "BLOCKED")
            self.assertEqual(out["physical_programming"], "NOT_AUTHORIZED")
        with patch.object(review, "inspect", return_value={"mock": "ok"}):
            with patch.object(sys, "argv", ["review", "--run-dir", "anything"]):
                self.assertEqual(review.main(), 2)

    def test_receipt_mutation_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            run = self.make_run(home)
            (run / "reports/20_route_drc.rpt").write_text("MUTATED")
            with patch.object(Path, "home", return_value=home):
                with self.assertRaisesRegex(review.Reject, "receipt bytes mismatch"):
                    review.inspect(run)

    def test_source_copy_mutation_even_with_rehashed_ledger_fails(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            run = self.make_run(home)
            (run / "reports/12_synaptic_lif_axil.v").write_text("tampered")
            self.rehash(run)
            with patch.object(Path, "home", return_value=home):
                with self.assertRaisesRegex(review.Reject, "copy identity mismatch"):
                    review.inspect(run)

    def test_symlink_rejected_and_original_owner_folder_never_reused(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            run = self.make_run(home)
            target = run / "reports/20_route_drc.rpt"
            payload = target.read_bytes()
            target.unlink()
            other = run / "reports/NOT_EVIDENCE.txt"
            other.write_bytes(payload)
            target.symlink_to(other)
            self.rehash(run)
            with patch.object(Path, "home", return_value=home):
                with self.assertRaisesRegex(review.Reject, "symlinked"):
                    review.inspect(run)
            with self.assertRaisesRegex(review.Reject, "not a new D3.D.2E"):
                review.inspect(run.with_name("m08_d3d2d_event_DE6kQWvt"))

if __name__ == "__main__":
    unittest.main()
