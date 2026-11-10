"""Positive/negative SYNTHETIC_ONLY tests of a read-only AXI binding plan.

No generated Vivado/HLS files or vendor functional simulator are executed.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m06_paged_hls_axi_link_plan import plan


def fake_audit(read=32, write=32):
    return {
        "schema": "m06-paged-hls-synthesized-port-readback-v1",
        "status": "GENUINE_GENERATED_RTL_HEADER_ONLY_NOT_PL_CONNECTED",
        "tool_version": "2025.2",
        "original_s00_s03_width": 256,
        "original_mem_sc_axi_connected": "NOT_PROVEN",
        "physical_base_addresses": "NOT_ALLOCATED",
        "actual_board": "NOT_ACCESSED",
        "m06_complete": False,
        "generated_rtl_count": 100,
        "generated_top_sha256": "a" * 64,
        "source_digest_subset": {
            "hls/m04_lif_eval/m04_eval.cpp": "a" * 64,
            "hls/m05_rolling/m05_rolling.cpp": "b" * 64,
            "hls/m06_paged_rolling/m06_paged_rolling.cpp": "c" * 64,
            "hls/m06_paged_rolling/m06_paged_rolling.hpp": "d" * 64,
        },
        "read_axi_master": {
            "prefix": "m_axi_gmem_read_", "role": "READ_ONLY_SOURCE",
            "data_width": read, "addr_width": 64,
        },
        "write_axi_master": {
            "prefix": "m_axi_gmem_write_", "role": "WRITE_ONLY_SOURCE",
            "data_width": write, "addr_width": 64,
        },
        "read_width_converter_needed": read != 256,
        "write_width_converter_needed": write != 256,
    }


class M06HLSPortLinkPlanSyntheticTests(unittest.TestCase):
    def test_positive_mismatched_generated_bus_widths_require_two_adapters(self):
        report = plan(fake_audit(read=32, write=64))
        self.assertFalse(report["m06_complete"])
        self.assertFalse(report["original_SmartConnect_connected"])
        self.assertEqual([x["original_smartconnect_slave"] for x in report["paths"]],
                         ["S00", "S03"])
        self.assertTrue(all(x["required_width_adapter"] for x in report["paths"]))
        self.assertEqual(report["original_smartconnect_upstream_address_width_bits"], 32)
        self.assertTrue(all(p["address_guard_or_translation_required"] for p in report["paths"]))
        self.assertTrue(all(p["address_mapping_status"] ==
            "HLS_HIGH_BITS_MUST_BE_BOUNDED_BEFORE_32BIT_ORIGINAL_SI"
            for p in report["paths"]))
        self.assertEqual(report["canonical_memory_bytes"], 65536)
        self.assertEqual(report["canonical_last_legal_page"], 255)
        self.assertIn("B_response_fence", " ".join(report["hard_gates"]))

    def test_positive_matching_width_is_not_proof_of_connected_ip(self):
        report = plan(fake_audit(read=256, write=256))
        self.assertFalse(any(x["required_width_adapter"] for x in report["paths"]))
        self.assertTrue(all("NOT_CONNECTED" in x["direct_connection_status"]
                            for x in report["paths"]))
        self.assertEqual(report["shared_backing_memory"], "REQUIRED_NOT_PROVEN")

    def test_negative_reject_fake_claim_of_original_ip_connection_or_board(self):
        for field, bad in (
            ("original_mem_sc_axi_connected", "PASSED"),
            ("actual_board", "PROGRAMMED"),
            ("physical_base_addresses", "0x1000"),
            ("m06_complete", True),
            ("status", "Genuine Connected"),
        ):
            with self.subTest(field=field):
                f = fake_audit()
                f[field] = bad
                with self.assertRaisesRegex(ValueError, "unconnected genuine"):
                    plan(f)

    def test_negative_reject_missing_or_corrupted_source_identity(self):
        for bad in ("garbage", "a" * 63, "Z" * 64):
            with self.subTest(bad=bad):
                f = fake_audit()
                f["generated_top_sha256"] = bad
                with self.assertRaisesRegex(ValueError, "digest"):
                    plan(f)
        f = fake_audit()
        f["source_digest_subset"].pop("hls/m05_rolling/m05_rolling.cpp")
        with self.assertRaisesRegex(ValueError, "source identity"):
            plan(f)

    def test_negative_reject_wrong_master_role_address_or_adapter_flag(self):
        for field, value, fragment in (
            ("prefix", "m_axi_gmem_write_", "role"),
            ("role", "WRITE_ONLY_SOURCE", "role"),
            ("data_width", 24, "width"),
            ("addr_width", 8, "width"),
            ("addr_width", 128, "width"),
        ):
            with self.subTest(field=field, value=value):
                f = fake_audit()
                f["read_axi_master"][field] = value
                with self.assertRaisesRegex(ValueError, fragment):
                    plan(f)
        f = fake_audit(read=32, write=256)
        f["read_width_converter_needed"] = False
        with self.assertRaisesRegex(ValueError, "contradicts"):
            plan(f)

    def test_negative_cli_refuses_absent_owner_evidence_without_output(self):
        script = ROOT / "scripts/m06_paged_hls_axi_link_plan.py"
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "SHOULD_NOT_EXIST.json"
            r = subprocess.run([sys.executable, str(script),
                                "--hls-evidence", str(Path(d) / "NO_HLS"),
                                "--port-audit", str(Path(d) / "NO_JSON"),
                                "--output", str(out)], text=True,
                               capture_output=True)
            self.assertEqual(r.returncode, 2)
            self.assertFalse(out.exists())
            self.assertIn("REJECTED", r.stderr)


if __name__ == "__main__":
    unittest.main()
