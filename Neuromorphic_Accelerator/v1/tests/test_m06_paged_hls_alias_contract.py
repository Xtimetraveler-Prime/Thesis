"""Source-only M06 cosim alias contract: POSITIVE/NEGATIVE, no vendor tools."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from m06_paged_hls_alias_contract import inspect

SOURCE = ROOT/"hls/m06_paged_rolling/m06_paged_rolling.cpp"
CONFIG = ROOT/"hls/m06_paged_rolling/m06_paged_rolling_hls_config.cfg"


class M06HLSAliasContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text()
        cls.config = CONFIG.read_text()

    def test_source_intent_separate_masters_and_same_buffer_pointer(self):
        result = inspect(self.source, self.config)
        self.assertEqual(result["shared_buffer_pointer_distance_words"], 0)
        self.assertEqual(result["canonical_max_words"], 16384)
        self.assertEqual(result["read_bundle"], "gmem_read")
        self.assertEqual(result["write_bundle"], "gmem_write")
        self.assertFalse(result["physical_DDR_or_original_IP_connected"])
        self.assertFalse(result["m06_complete"])

    def test_negative_reject_missing_or_duplicate_alias(self):
        alias="#pragma HLS ALIAS ports=canonical_read_words,canonical_write_words distance=0"
        self.assertEqual(self.source.count(alias), 1)
        for mutated in (
            self.source.replace(alias, ""),
            self.source.replace(alias, alias+"\n"+alias),
            self.source.replace(alias, alias.replace("distance=0", "distance=1")),
            self.source.replace(alias, alias.replace("canonical_read_words,canonical_write_words",
                                                     "canonical_write_words,canonical_read_words")),
        ):
            with self.subTest(mutated=mutated.count(alias)):
                with self.assertRaisesRegex(ValueError, "alias|ALIAS"):
                    inspect(mutated, self.config)

    def test_negative_reject_merged_bundle_or_wrong_depth(self):
        for old, new in (("bundle=gmem_read", "bundle=gmem_write"),
                         ("bundle=gmem_write", "bundle=gmem_read"),
                         ("depth=16384", "depth=8192"),
                         ("offset=slave", "offset=off")):
            with self.subTest(changed=old+"->"+new):
                self.assertIn(old, self.source)
                with self.assertRaisesRegex(ValueError, "memory master"):
                    inspect(self.source.replace(old, new, 1), self.config)

    def test_negative_reject_wrong_top_and_additional_memory_master(self):
        with self.assertRaisesRegex(ValueError, "wrong HLS top"):
            inspect(self.source, self.config.replace(
                "syn.top=m06_paged_rolling_replay", "syn.top=wrong"))
        altered = self.source.replace(
            "#pragma HLS ALIAS ports=canonical_read_words,canonical_write_words distance=0",
            "#pragma HLS INTERFACE m_axi port=other offset=slave bundle=third depth=16384 max_read_burst_length=16\n"
            "#pragma HLS ALIAS ports=canonical_read_words,canonical_write_words distance=0")
        with self.assertRaisesRegex(ValueError, "additional or removed"):
            inspect(altered, self.config)

    def test_cli_source_preflight_no_vivado_or_bitstream(self):
        result = subprocess.run(
            [sys.executable, str(ROOT/"scripts/m06_paged_hls_alias_contract.py"),
             "--root", str(ROOT)], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SOURCE_ONLY_SHARED_BUFFER_ALIAS_DECLARED_NOT_COSIM_VERIFIED",
                      result.stdout)
        self.assertIn('"genuine_cosim": "NOT_EXECUTED_BY_THIS_TOOL"', result.stdout)


if __name__ == "__main__":
    unittest.main()
