"""D3.D.2E completed owner hardware receipt auditor regression tests.

Entirely synthetic sealed six-file receipt, mocked native original identity.
Tests that fix for literal-backslash-n false negative and guard *all* existing
one-shot provenance, independent M06 numerical, and per-tick marker checks.
NEVER hardware programming or owner-local original evidence mutation.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2e_queue_physical_audit as audit

OWNER_BIT_SHA="2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc"
EXPECTED_COUNTS=[5,5,4,3]

class D3D2EPhysicalReauditTests(unittest.TestCase):
    def make_mock(self,base:Path):
        owner=base/"M08"/"m08_d3d2e_queue_GFz0SbiC"
        owner.mkdir(parents=True)
        hw=owner.parent/"m08_d3d2e_queue_HW_SYNTHETIC"
        hw.mkdir()
        golden=audit.oracle.words()
        counts=[sum(int(golden[580+3*k],16)==t for k in range(17)) for t in range(4)]
        self.assertEqual(counts,EXPECTED_COUNTS)
        data=dict(audit.METADATA)
        data["candidate_sha256"]=OWNER_BIT_SHA
        for t,c in enumerate(counts):
            data[f"per_tick_serviced_{t}"]=str(c)
        result="\n".join([*(k+"="+v for k,v in data.items()),
                          *audit.expected_lines()])+"\n"
        markers=[
            "M08_D3D2E_ACCEPTED_IMAGE_HASH|"+OWNER_BIT_SHA,
            "M08_D3D2E_M06_TRIPLE_ORACLE_630_WORDS_VERIFIED",
            "M08_D3D2E_DEVICE|xck26_0|xck26",
            "M08_D3D2E_PROGRAM_START",
            "M08_D3D2E_PROGRAM_COMPLETED",
            "M08_D3D2E_AXI_MASTER|hw_axi_1",
            "M08_D3D2E_BRAM_TRANSPORT_PASS",
            "M08_D3D2E_M32Q_V6_IDENTITY_PASS",
            "M08_D3D2E_PHYSICAL_RAW_17_EVENT_PUSH_ACCEPTED",
            "M08_D3D2E_ALL_128_LIVE_BUCKETS_ZERO_BEFORE_SERVICE",
        ]
        markers += [f"M08_D3D2E_TICK_SERVICE_PARITY|{i}|{n}"
                    for i,n in enumerate(counts)]
        markers += ["M08_D3D2E_QUEUE_17_ACCEPTED_17_SERVICED_ALL_FOUR_TICKS_PASS"]
        markers += [f"M08_D3D2E_EVENT_BUCKET_PARITY|{n}" for n in range(32)]
        markers += ["M08_D3D2E_PHYSICAL_ALL_128_FPGA_EVENT_BUCKET_SUMS_PASS"]
        markers += [f"M08_D3D2E_M06_REAL_NEURON_PARITY|{n}" for n in range(32)]
        markers += ["M08_D3D2E_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS"]
        (hw/"00_executed_source.tcl").write_bytes(audit.TCL.read_bytes())
        (hw/"01_jtag_m06.log").write_text("\n".join(markers)+"\n")
        (hw/"02_jtag_m06.jou").write_text("SIMULATION ONLY, NOT PHYSICAL VIVADO\n")
        (hw/"03_exit.txt").write_text("vivado_physical_exit=0\n")
        (hw/"10_m06_tickqueue_golden.hex").write_text("\n".join(golden)+"\n")
        (hw/"80_m06_tickqueue_hw_parity.txt").write_text(result)
        self.seal(hw)
        return owner,hw

    def seal(self,hw):
        (hw/"99_evidence_sha256.txt").write_text(
            "".join(sha256((hw/name).read_bytes()).hexdigest()+"  "+name+"\n"
                    for name in audit.FILES))

    def fake_native(self):
        return patch.object(audit.native,"inspect",return_value={
            "status":"M08_D3D2E_EXACT_OWNER_NATIVE_TICKQUEUE_IMAGE_ACCEPTED_NO_BOARD",
            "image_specific_gate":"ACCEPTED",
            "candidate_sha256":OWNER_BIT_SHA,
        })

    def test_four_real_newline_markers_exact_order_and_counts(self):
        expected=[f"M08_D3D2E_TICK_SERVICE_PARITY|{i}|{n}"
                  for i,n in enumerate(EXPECTED_COUNTS)]
        # Vivado puts terminate real lines with newline, not backslash+n text.
        log="Vivado INFO: started\n"+"\n".join(expected)+"\nVivado INFO: end\n"
        audit.verify_tick_service_log(log,EXPECTED_COUNTS)

    def test_bad_tick_receipts_not_accepted(self):
        expected=[f"M08_D3D2E_TICK_SERVICE_PARITY|{i}|{n}"
                  for i,n in enumerate(EXPECTED_COUNTS)]
        variants=[
            expected[:3],expected+expected[-1:],
            list(reversed(expected)),
            [expected[0],expected[1].replace("|5","|4"),*expected[2:]],
            [expected[0],*expected[2:]],
            [expected[0],expected[1],"M08_D3D2E_TICK_SERVICE_PARITY|9|0",*expected[2:]],
            [x+"\\n" for x in expected], # literal backslash+n not a valid real marker
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                with self.assertRaisesRegex(audit.Reject,"physical per-tick SERVICE"):
                    audit.verify_tick_service_log("\n".join(variant)+"\n",EXPECTED_COUNTS)

    def test_mock_full_original_six_receipts_accepts_and_stays_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            owner,hw=self.make_mock(Path(d))
            with self.fake_native():
                out=audit.verify(owner,hw)
            self.assertEqual(out["status"],
                             "M08_D3D2E_PHYSICAL_M06_17_QUEUED_EVENT_128_BUCKET_384_NEURAL_ACCEPTED")
            self.assertEqual(out["hardware_input_buckets_verified"],128)
            self.assertEqual(out["hardware_voltages_verified"],128)
            self.assertEqual(out["hardware_spike_decisions_verified"],128)
            self.assertEqual(out["hardware_recurrent_currents_verified"],128)
            self.assertEqual(out["physical_events_serviced"],17)
            self.assertTrue(out["four_service_tick_barriers"])

    def test_rehashed_tick_corruption_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            owner,hw=self.make_mock(Path(d))
            log=hw/"01_jtag_m06.log"
            data=log.read_text().replace(
                "M08_D3D2E_TICK_SERVICE_PARITY|2|4",
                "M08_D3D2E_TICK_SERVICE_PARITY|2|5",
            )
            log.write_text(data)
            self.seal(hw)
            with self.fake_native():
                with self.assertRaisesRegex(audit.Reject,"physical per-tick SERVICE"):
                    audit.verify(owner,hw)

    def test_six_receipt_corruption_and_mock_native_gate_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            owner,hw=self.make_mock(Path(d))
            with patch.object(audit.native,"inspect",return_value={
                "status":"M08_D3D2E_EXACT_OWNER_NATIVE_TICKQUEUE_IMAGE_ACCEPTED_NO_BOARD",
                "image_specific_gate":"BLOCKED","candidate_sha256":OWNER_BIT_SHA
            }):
                with self.assertRaisesRegex(audit.Reject,"NOT accepted"):
                    audit.verify(owner,hw)
            log=hw/"01_jtag_m06.log"
            log.write_text(log.read_text()+"TAMPER\n") # do not reseal
            with self.fake_native():
                with self.assertRaisesRegex(audit.Reject,"mutated physical evidence"):
                    audit.verify(owner,hw)

    def test_rehashed_neural_output_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            owner,hw=self.make_mock(Path(d))
            path=hw/"80_m06_tickqueue_hw_parity.txt"
            data=path.read_text()
            self.assertIn("neuron=0 external_currents=",data)
            path.write_text(data.replace("neuron=0 external_currents=",
                                         "neuron=0 external_currents=00000099,",1))
            self.seal(hw)
            with self.fake_native():
                with self.assertRaisesRegex(audit.Reject,"trace differs"):
                    audit.verify(owner,hw)

if __name__=="__main__":
    unittest.main()
