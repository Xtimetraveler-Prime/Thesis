"""Host-only ORIGINAL-port-safe independent AXI BFM inputs; NOT XSim PASS."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m06_vendor_axi_directed_vectors import (
    SCHEMA, ORIGINAL_CONTRACT, PORT_ROLES, READERS, WRITER,
    validate_original_report, vector_suite,
)


def synthetic_port_report():
    """Fake fixture to check parsing only, never authenticated as Vivado."""
    lines = []
    for endpoint, props in ORIGINAL_CONTRACT.items():
        lines.append("ENDPOINT|"+endpoint)
        for key, value in props.items():
            lines.append(f"ENDPOINT_PROPERTY|{endpoint}|{key}|{value}")
    lines.append("RESULT|ORIGINAL_PORTS_CAPTURED_FOR_ONE_VENDOR_FUNCTIONAL_XSIM_TRIAL")
    return "\n".join(lines)+"\n"


class OriginalPortSafeVectorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = vector_suite()

    def test_original_read_write_modes_not_four_full_duplex_inputs(self):
        v = self.v
        self.assertEqual(v["schema"], SCHEMA)
        self.assertEqual(v["scenario_count"], 9)
        self.assertEqual(v["original_port_role_contract"], PORT_ROLES)
        self.assertEqual(PORT_ROLES, {"S00": "READ_ONLY", "S01": "READ_ONLY",
                                      "S02": "READ_ONLY", "S03": "WRITE_ONLY"})
        self.assertFalse(v["vendor_smartconnect_executed"])
        self.assertEqual(v["true_vendor_axi_result"], "NOT_EXECUTED")
        self.assertEqual(v["original_si_max_burst_length_property"], 16)
        self.assertEqual(v["original_mi_max_burst_length_property"], 32)

    def test_all_writes_exclusively_on_original_s03_and_1_beat(self):
        write_cases = [c for c in self.v["scenarios"] if c["direction"]=="WRITE"]
        self.assertEqual(len(write_cases), 4)
        offsets = [c["upstream_address_offset"] for c in write_cases]
        self.assertEqual(offsets, [0x0fe0, 0x1000, 0x1020, 0x1040])
        for case in write_cases:
            self.assertEqual(case["source_port"], WRITER)
            self.assertEqual(case["upstream_beat_count"], 1)
            self.assertEqual(case["upstream_awlen"], 0)
            self.assertEqual(case["upstream_awsize"], 5)
            self.assertEqual(len(case["expected_downstream_two_halves"]), 2)
            self.assertEqual(case["expected_write_response"], "OKAY")

    def test_independent_masked_byte_mem_oracle_and_low_high_lane_mapping(self):
        source = bytearray((13*i+17)&255 for i in range(0x2000))
        masks = [0xffffffff, 0x80010001, 0x00ff00ff, 0x0000ffff]
        for idx,case in enumerate(self.v["scenarios"][:4]):
            start = case["upstream_address_offset"]
            original = bytes(source[start:start+32])
            self.assertEqual(case["before_memory_256_le_hex"], original.hex())
            data = bytes.fromhex(case["upstream_wdata_256_le_hex"])
            mask = int(case["upstream_wstrb_32_hex"],16)
            self.assertEqual(mask, masks[idx])
            for half in range(2):
                witness = case["expected_downstream_two_halves"][half]
                self.assertEqual(witness["address_offset"], start+16*half)
                self.assertEqual(
                    bytes.fromhex(witness["downstream_data_128_le_hex"]),
                    data[16*half:16*(half+1)])
                self.assertEqual(
                    int(witness["downstream_wstrb_16_hex"],16),
                    (mask>>(16*half))&0xffff)
                self.assertEqual(witness["expected_downstream_wlast"], half==1)
            for lane in range(32):
                if mask & (1<<lane):
                    source[start+lane] = data[lane]
            self.assertEqual(case["expected_after_memory_256_le_hex"],
                             bytes(source[start:start+32]).hex())
        for case in self.v["scenarios"][4:7]:
            self.assertIn(case["source_port"], READERS)
            self.assertEqual(case["direction"], "READ")
            self.assertEqual(case["upstream_arlen_each"], 0)
            self.assertEqual(
                case["expected_upstream_rdata_256_le_hex"],
                [bytes(source[at:at+32]).hex()
                 for at in case["independent_single_beat_read_address_offsets"]])

    def test_every_read_port_sees_same_s03_canonical_writes(self):
        cases = self.v["scenarios"][4:7]
        self.assertEqual([c["source_port"] for c in cases], list(READERS))
        self.assertTrue(all(c["direction"]=="READ" for c in cases))
        self.assertEqual(cases[0]["expected_upstream_rdata_256_le_hex"],
                         cases[1]["expected_upstream_rdata_256_le_hex"])
        self.assertEqual(cases[1]["expected_upstream_rdata_256_le_hex"],
                         cases[2]["expected_upstream_rdata_256_le_hex"])

    def test_no_crossing_4k_burst_and_max_burst_not_unconditionally_sent(self):
        edge = self.v["scenarios"][7]
        self.assertEqual(edge["source_port"], "S00")
        self.assertEqual(edge["direction"], "READ_SPLIT")
        self.assertEqual(edge["separate_upstream_address_offsets"],
                         [0x0fe0, 0x1000, 0x1020])
        self.assertTrue(edge["never_issue_one_4KiB_crossing_burst"])
        self.assertEqual(len(edge["expected_256b_words_le_hex"]), 3)
        blocked = self.v["scenarios"][8]
        self.assertIn("NOT_EXECUTABLE",blocked["direction"])
        self.assertEqual(blocked["original_si_has_burst"],0)
        self.assertEqual(blocked["original_si_max_burst_beats"],16)
        self.assertEqual(blocked["original_mi_max_burst_beats"],32)
        self.assertTrue(blocked["generic_128_upstream_beat_stress_excluded"])

    def test_report_role_parser_accepts_only_original_observed_contract(self):
        raw = synthetic_port_report()
        value = validate_original_report(raw)
        self.assertTrue(value["real_port_source_attached"])
        self.assertEqual(value["real_vendor_functional_axi"],"NOT_EXECUTED")
        self.assertEqual(value["real_capture_sha256"],
                         hashlib.sha256(raw.encode()).hexdigest())
        for before,after in (
            ("CONFIG.READ_WRITE_MODE|WRITE_ONLY","CONFIG.READ_WRITE_MODE|READ_ONLY"),
            ("CONFIG.MAX_BURST_LENGTH|16","CONFIG.MAX_BURST_LENGTH|128"),
            ("CONFIG.HAS_BURST|0","CONFIG.HAS_BURST|1"),
            ("CONFIG.ID_WIDTH|0","CONFIG.ID_WIDTH|16"),
        ):
            with self.subTest(before=before), self.assertRaises(ValueError):
                validate_original_report(raw.replace(before,after))
        with self.assertRaisesRegex(ValueError,"missing original completed"):
            validate_original_report(raw.replace("RESULT|ORIGINAL_PORTS_CAPTURED", "RESULT|NOT_CAPTURED"))
        self.assertEqual(vector_suite(raw)["source_port_report_provenance"]
                         ["real_capture_sha256"], hashlib.sha256(raw.encode()).hexdigest())

    def test_no_vendor_proof_even_with_attached_original_port_contract(self):
        report = synthetic_port_report()
        v = vector_suite(report)
        self.assertFalse(v["vendor_smartconnect_executed"])
        self.assertEqual(v["true_vendor_axi_result"],"NOT_EXECUTED")
        self.assertEqual(v["actual_burst_pin_semantics"],
                         "NOT_YET_INSPECTED_IN_VENDOR_HDL")
        self.assertEqual(v["rresp_bresp_error_injection"],
                         "PENDING_REAL_VENDOR_BFM")

    def test_reproducible_source_cases_and_exclusive_cli(self):
        self.assertEqual(vector_suite(),self.v)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"role_safe_vectors.json"
            report = Path(d)/"fake_fixture_DO_NOT_TREAT_AS_VIVADO.txt"
            report.write_text(synthetic_port_report())
            cmd = [sys.executable,
                   str(ROOT/"scripts/m06_vendor_axi_directed_vectors.py"),
                   "--output",str(path),"--port-report",str(report)]
            proc = subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn("S03 write, S00/S01/S02 reads",proc.stdout)
            obj = json.loads(path.read_text())
            self.assertEqual(obj["scenario_count"],9)
            self.assertFalse(obj["vendor_smartconnect_executed"])
            self.assertEqual(obj["source_port_report_provenance"]
                             ["real_capture_sha256"],
                             hashlib.sha256(report.read_bytes()).hexdigest())
            prior = path.read_bytes()
            proc = subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(proc.returncode,2)
            self.assertIn("overwrite",proc.stderr)
            self.assertEqual(path.read_bytes(),prior)


if __name__ == "__main__":
    unittest.main()
