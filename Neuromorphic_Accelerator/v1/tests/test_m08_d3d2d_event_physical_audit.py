"""D3.D.2D 17 raw-event hardware auditor MOCK parser/mutation tests ONLY.

No actual Vivado, board, JTAG or image is used. A fake accepted-native result
tests read-only audit logic, never a source of new physical evidence.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2d_event_physical_audit as audit
import m08_d3d2d_event_vectors as vec

class SyntheticEventIngressAudit(unittest.TestCase):
    def make_mock(self,root:Path):
        base=root/"M08"
        native=base/"m08_d3d2d_event_SYNTHETIC"
        hw=base/"m08_d3d2d_event_HW_SYNTHETIC"
        native.mkdir(parents=True)
        hw.mkdir()
        fake_sha="a"*64  # NEVER a real bitstream
        meta=dict(audit.METADATA)
        meta["candidate_sha256"]=fake_sha
        text="\n".join(k+"="+v for k,v in meta.items())+"\n"
        log=(
            "M08_D3D2D_ACCEPTED_IMAGE_HASH|"+fake_sha+"\n"
            "M08_D3D2D_M06_TRIPLE_ORACLE_630_WORDS_VERIFIED\n"
            "M08_D3D2D_DEVICE|xck26_0|xck26\n"
            "M08_D3D2D_PROGRAM_START\n"
            "M08_D3D2D_PROGRAM_COMPLETED\n"
            "M08_D3D2D_AXI_MASTER|hw_axi_1\n"
            "M08_D3D2D_BRAM_TRANSPORT_PASS\n"
            "M08_D3D2D_M32E_V5_IDENTITY_PASS\n"
            "M08_D3D2D_PHYSICAL_RAW_17_EVENT_PUSH_ACCEPTED\n"
            "M08_D3D2D_PHYSICAL_ALL_128_FPGA_EVENT_BUCKET_SUMS_PASS\n"
            + "".join(f"M08_D3D2D_EVENT_BUCKET_PARITY|{n}\n" for n in range(32))
            + "".join(f"M08_D3D2D_M06_REAL_NEURON_PARITY|{n}\n" for n in range(32))
            + "M08_D3D2D_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS\n"
        )
        files={
            "00_executed_source.tcl":audit.TCL.read_bytes(),
            "01_jtag_m06.log":log.encode(),
            "02_jtag_m06.jou":b"SYNTHETIC-NOT-VIVADO\n",
            "03_exit.txt":b"vivado_physical_exit=0\n",
            "10_m06_raw17_golden.hex":("\n".join(vec.words())+"\n").encode(),
            "80_m06_raw17_hw_parity.txt":(
                text+"\n".join(audit.expected_lines())+"\n").encode(),
        }
        self.assertEqual(set(files),set(audit.FILES))
        for name,content in files.items():
            (hw/name).write_bytes(content)
        self.rehash(hw)
        return native,hw,fake_sha

    @staticmethod
    def rehash(hw):
        (hw/"99_evidence_sha256.txt").write_text(
            "".join(sha256((hw/n).read_bytes()).hexdigest()+"  "+n+"\n"
                    for n in audit.FILES),encoding="ascii")

    @staticmethod
    def accepted(sha):
        return patch.object(audit.native,"inspect",return_value={
            "status":"M08_D3D2D_EXACT_OWNER_NATIVE_RAW17_IMAGE_ACCEPTED_NO_BOARD",
            "candidate_sha256":sha,
        })

    def test_synthetic_parser_requires_128_raw_event_sums_and_384_neural(self):
        with TemporaryDirectory() as temp:
            owner,hw,sha=self.make_mock(Path(temp))
            with self.accepted(sha):
                result=audit.verify(owner,hw)
                self.assertEqual(result["hardware_input_buckets_verified"],128)
                self.assertEqual(result["hardware_voltages_verified"],128)
                self.assertEqual(result["hardware_spike_decisions_verified"],128)
                self.assertEqual(result["hardware_recurrent_currents_verified"],128)
                self.assertTrue(result["external_event_ingestion_in_fabric"])
                self.assertFalse(result["streaming_or_asynchronous_ingress_proven"])
                self.assertFalse(result["physical_ddr"])

    def test_mutated_event_bucket_rehashed_ledger_still_rejected(self):
        with TemporaryDirectory() as temp:
            owner,hw,sha=self.make_mock(Path(temp))
            file=hw/"80_m06_raw17_hw_parity.txt"
            content=file.read_text()
            file.write_text(content.replace("neuron=0 external_currents=",
                                            "neuron=0 external_currents=DEADBEEF,",1))
            self.rehash(hw)
            with self.accepted(sha),self.assertRaisesRegex(
                    audit.Reject,"raw-event 128 bucket/384 neural physical trace differs"):
                audit.verify(owner,hw)

    def test_second_program_rehashed_log_rejected(self):
        with TemporaryDirectory() as temp:
            owner,hw,sha=self.make_mock(Path(temp))
            file=hw/"01_jtag_m06.log"
            content=file.read_text()
            file.write_text(content.replace(
                "M08_D3D2D_PROGRAM_COMPLETED\n",
                "M08_D3D2D_PROGRAM_COMPLETED\nM08_D3D2D_PROGRAM_START\n"))
            self.rehash(hw)
            with self.accepted(sha),self.assertRaisesRegex(
                    audit.Reject,"ambiguous or duplicated JTAG program marker"):
                audit.verify(owner,hw)

    def test_forged_event_count_metadata_rehashed_receipt_rejected(self):
        with TemporaryDirectory() as temp:
            owner,hw,sha=self.make_mock(Path(temp))
            file=hw/"80_m06_raw17_hw_parity.txt"
            file.write_text(file.read_text().replace("event_push_count=17","event_push_count=18"))
            self.rehash(hw)
            with self.accepted(sha),self.assertRaisesRegex(
                    audit.Reject,"physical target, image, event-ingress claims wrong"):
                audit.verify(owner,hw)

    def test_altered_executed_tcl_rehashed_receipt_rejected(self):
        with TemporaryDirectory() as temp:
            owner,hw,sha=self.make_mock(Path(temp))
            file=hw/"00_executed_source.tcl"
            file.write_bytes(file.read_bytes()+b"\n# MUTATION\n")
            self.rehash(hw)
            with self.accepted(sha),self.assertRaisesRegex(
                    audit.Reject,"executed JTAG source altered"):
                audit.verify(owner,hw)

    def test_real_first_image_gate_not_yet_released(self):
        with TemporaryDirectory() as temp:
            owner,hw,sha=self.make_mock(Path(temp))
            with self.assertRaises(audit.Reject):
                audit.verify(owner,hw)

if __name__=="__main__":
    unittest.main()
