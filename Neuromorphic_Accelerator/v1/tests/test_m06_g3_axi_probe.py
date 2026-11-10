"""M06 G3.2 DECERR passive instrumentation: positive/negative SOURCE-ONLY tests.

No original AMD models are included or run here. Existing fake-stub Icarus
exercise is SYNTAX ONLY, never functional hardware-model verification.
"""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m06_g3_generate_real_dwc_original_sc_bfm import (
    passive_axi_probe, render, DRIVER_DEFAULTS
)
from m06_g3_axi_trace_audit import analyze
from test_m06_g3_generate_real_dwc_original_sc_bfm import DWC, VENDOR


class M06G32PassiveAXIProbeTests(unittest.TestCase):
    def test_positive_passive_read_and_write_boundary_coverage(self):
        tb = passive_axi_probe()
        for item in ("RD_SI32", "RD_MI256_SC_S00", "SC_M00_RAM128",
                     "WR_SI32", "WR_MI256_SC_S03", "R_OBS", "B_OBS",
                     "ram.rd_bad_request", "M06_G3_AXI_FIRST_DECERR",
                     "M06_G3_AXI_PROBE_SUMMARY", "axi_probe_summary",
                     "LOCAL_AXI_INACTIVITY_WATCHDOG"):
            self.assertIn(item, tb)
        for banned in ("force ", "assign M00_AXI", "program_hw_devices",
                       "s_axi_arsize=3'd4"):
            self.assertNotIn(banned, tb)

    def test_positive_original_reproducer_unchanged(self):
        tb = render(DWC, VENDOR)
        self.assertEqual(DRIVER_DEFAULTS["arsize"], "3'd2")
        self.assertIn("read32('h0000)", tb)
        self.assertIn("m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536))", tb)
        self.assertIn("axi_probe_summary();", tb)
        self.assertIn("M06_G3_AXI_TRACE", tb)
        self.assertNotIn("m06_paged_rolling_replay", tb)

    def test_positive_ram_error_observed_without_fabricated_acceptance(self):
        log = "\n".join((
            "M06_G3_AXI_TRACE kind=AR stage=RD_SI32 t=425000 addr=0 len=0 size=2 burst=01 cache=0011 id=0",
            "M06_G3_AXI_TRACE kind=AR stage=RD_MI256_SC_S00 t=435000 addr=0 len=0 size=2 burst=01 cache=0011 id=NA",
            "M06_G3_AXI_TRACE kind=AR stage=SC_M00_RAM128 t=445000 addr=0 len=0 size=2 burst=01 cache=NA id=NA",
            "M06_G3_AXI_TRACE kind=R_OBS stage=SC_M00_RAM128 t=450000 resp=11 ready=0 last=1 data=0 ram_bad=1",
            "M06_G3_AXI_FIRST_DECERR kind=R_OBS stage=SC_M00_RAM128 t=450000 resp=11 ready=0",
            "M06_G3_AXI_TRACE kind=R_OBS stage=RD_SI32 t=470000 resp=11 ready=0 last=1 data=0 ram_bad=NA",
            "M06_G3_AXI_PROBE_SUMMARY axi_RD_SI32_AR=1 printed=5 first_decerr=1",
        ))
        trace, out = analyze(log)
        self.assertEqual(len(trace), 7)
        self.assertEqual(out["location_hypothesis_from_observations"],
                         "RAM_ENDPOINT_REJECTED_OBSERVED_REQUEST")
        self.assertTrue(out["memory_ar_observed"])
        self.assertFalse(out["root_cause_proven"])
        self.assertFalse(out["trace_truncated_or_incomplete"])

    def test_positive_upstream_error_does_not_invent_memory_access(self):
        log = "\n".join((
            "M06_G3_AXI_TRACE kind=AR stage=RD_SI32 t=425 addr=0 len=0 size=2 burst=01 cache=0011 id=0",
            "M06_G3_AXI_TRACE kind=R_OBS stage=RD_SI32 t=450 resp=11 ready=0 last=1 data=0 ram_bad=NA",
            "M06_G3_AXI_FIRST_DECERR kind=R_OBS stage=RD_SI32 t=450 resp=11 ready=0",
        ))
        _, out = analyze(log)
        self.assertFalse(out["memory_ar_observed"])
        self.assertEqual(out["location_hypothesis_from_observations"],
                         "DECERR_AT_DWC_SI_WITHOUT_OBSERVED_MI_DECERR")
        self.assertTrue(out["trace_truncated_or_incomplete"])

    def test_negative_duplicate_or_unsupported_first_decerr_rejected(self):
        row = "M06_G3_AXI_TRACE kind=R_OBS stage=RD_SI32 t=450 resp=11 ready=0"
        mark = "M06_G3_AXI_FIRST_DECERR kind=R_OBS stage=RD_SI32 t=450 resp=11 ready=0"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze("\n".join((row, mark, mark)))
        with self.assertRaisesRegex(ValueError, "lacks"):
            analyze(mark)

    def test_negative_malformed_response_and_missing_ar_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid AXI response"):
            analyze("M06_G3_AXI_TRACE kind=R_OBS stage=RD_SI32 t=10 resp=xx")
        with self.assertRaisesRegex(ValueError, "missing AXI address"):
            analyze("M06_G3_AXI_TRACE kind=AR stage=RD_SI32 t=10 size=2")
        with self.assertRaisesRegex(ValueError, "unknown AXI"):
            analyze("M06_G3_AXI_TRACE kind=AR stage=FAKE t=10 size=2")

    def test_source_runner_keeps_hash_and_failure_gate(self):
        s = (ROOT / "scripts/run_m06_g3_real_dwc_original_sc_xsim.sh").read_text()
        self.assertIn("m06_g3_axi_trace_audit.py", s)
        self.assertIn("08_axi_handshake_trace.log", s)
        self.assertIn("09_axi_probe_summary.json", s)
        self.assertIn("M06_G3_REAL_DWC_SC_FAIL", s)
        self.assertIn("sim_rc", s)
        self.assertIn("source_before_sha256.txt", s)
        self.assertIn("source_after_sha256.txt", s)
        self.assertNotIn("program_hw_devices", s)


if __name__ == "__main__":
    unittest.main()
