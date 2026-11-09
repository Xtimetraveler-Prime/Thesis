"""Host-only independently precomputed AXI transaction stimuli, NOT Vivado XSim."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from m06_vendor_axi_directed_vectors import vector_suite, SCHEMA


class M06VendorStimulusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = vector_suite()

    def test_all_ports_and_cases_never_claim_real_vendor_sim(self):
        v=self.v
        self.assertEqual(v["schema"], SCHEMA)
        self.assertEqual(v["source_case_count"], 6)
        self.assertEqual(v["original_mem_sc_SI"], 4)
        self.assertEqual(v["model_si_width_bits"], 256)
        self.assertEqual(v["model_mi_width_bits"], 128)
        self.assertFalse(v["true_vivado_xsim_executed"])
        self.assertEqual({s["si_index"] for s in v["scenarios"][:4]}, set(range(4)))
        self.assertTrue(v["stimulus_generated_without_vendor_ip"])

    def test_each_original_si_lanes_strobes_and_readback_byte_exact(self):
        for case in self.v["scenarios"][:4]:
            memory = bytearray((13*i+17)&255 for i in range(0x6000))
            start=case["address_offset"]
            self.assertEqual(len(case["upstream_write_beats"]), 8)
            self.assertEqual(len(case["expected_downstream_write_beats"]), 16)
            self.assertEqual(case["downstream_len"], 15)
            for beat,row in enumerate(case["upstream_write_beats"]):
                data=bytes.fromhex(row["wdata_256_le_hex"])
                strb=int(row["wstrb_32_hex"],16)
                self.assertEqual(len(data),32)
                self.assertEqual(row["wlast"], beat==7)
                for lane in range(32):
                    if strb & (1<<lane):
                        memory[start+beat*32+lane]=data[lane]
                for half in range(2):
                    exp=case["expected_downstream_write_beats"][beat*2+half]
                    self.assertEqual(bytes.fromhex(exp["wdata_128_le_hex"]),
                                     data[half*16:(half+1)*16])
                    self.assertEqual(int(exp["wstrb_16_hex"],16),
                                     (strb>>(half*16))&0xffff)
                    self.assertEqual(exp["wlast_128"],beat==7 and half==1)
            expected=[memory[start+32*i:start+32*(i+1)].hex()
                      for i in range(8)]
            self.assertEqual(case["expected_upstream_read_beats_le_hex"],expected)
            self.assertEqual(case["expected_response"],"OKAY")

    def test_4k_boundary_is_two_distinct_axi_bursts(self):
        case=self.v["scenarios"][4]
        self.assertEqual(case["planned_address_offsets"],[4064,4096])
        self.assertEqual(case["planned_upstream_beats"],[1,2])
        self.assertEqual(case["planned_downstream_beats"],[2,4])
        self.assertEqual(len(case["expected_read_words_le_hex"]),3)

    def test_max_burst_read_is_128x256_up_and_256x128_down(self):
        case=self.v["scenarios"][5]
        self.assertEqual(case["upstream_len"],127)
        self.assertEqual(case["downstream_len"],255)
        self.assertEqual(case["source_planner_burst_count"],1)
        self.assertEqual(len(case["expected_payload_sha256"]),64)

    def test_reproducible_selfcontained_inputs(self):
        self.assertEqual(self.v,vector_suite())
        self.assertEqual(self.v["address_interpretation"],
                         "LOGICAL_OFFSETS_ONLY_NOT_OS_DDR")
        self.assertTrue(self.v["error_cases_not_fabricated_as_vendor_results"])

    def test_exclusive_json_export_never_overwrites_user_results(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"directed.json"
            argv=[sys.executable,str(ROOT/"scripts/m06_vendor_axi_directed_vectors.py"),
                  "--output",str(path)]
            r=subprocess.run(argv,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads(path.read_text()),self.v)
            self.assertIn("vendor XSim NOT RUN",r.stdout)
            copy=path.read_bytes()
            r2=subprocess.run(argv,capture_output=True,text=True)
            self.assertEqual(r2.returncode,2)
            self.assertIn("overwrite",r2.stderr)
            self.assertEqual(path.read_bytes(),copy)


if __name__=="__main__":
    unittest.main()
