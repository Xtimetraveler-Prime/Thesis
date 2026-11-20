"""Mock-only D3.D.2C 32x4 physical receipt auditor regression.

No I/O to FPGA/Vivado. A synthetic positive tests the auditor parser, NOT
physical parity; only the owner can produce original JTAG hardware evidence.
Mutation tests rehash tampered six-file receipts and MUST still be rejected.
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
import m08_d3d2c_m06_physical_audit as audit
import m08_d3d2c_m06_native_review as native_gate
import m08_d3d2c_m06_vectors as oracle


class SyntheticPhysicalReadbackAuditTests(unittest.TestCase):
    def make_mock(self,root:Path):
        base=root/"M08"
        base.mkdir()
        native=base/native_gate.ORIGINAL_OWNER_NATIVE_DIR
        native.mkdir()
        hw=base/"m08_d3d2c_m06_HW_FAKE0000"
        hw.mkdir()
        receipt=dict(audit.METADATA)
        receipt["candidate_sha256"]=native_gate.OWNER_ORIGINAL_BIT_SHA
        header="\n".join(f"{k}={v}" for k,v in receipt.items())+"\n"
        content={
            "00_executed_source.tcl":audit.TCL.read_bytes(),
            "01_jtag_m06.log":(
                "M08_D3D2C_ACCEPTED_IMAGE_HASH|"+native_gate.OWNER_ORIGINAL_BIT_SHA+"\n"
                "M08_D3D2C_M06_TRIPLE_ORACLE_579_WORDS_VERIFIED\n"
                "M08_D3D2C_DEVICE|xck26_0|xck26\n"
                "M08_D3D2C_PROGRAM_START\n"
                "M08_D3D2C_PROGRAM_COMPLETED\n"
                "M08_D3D2C_AXI_MASTER|hw_axi_1\n"
                "M08_D3D2C_BRAM_TRANSPORT_PASS\n"
                "M08_D3D2C_M32N_V4_IDENTITY_PASS\n"
                + "".join(f"M08_D3D2C_M06_REAL_NEURON_PARITY|{n}\n" for n in range(32))
                + "M08_D3D2C_PHYSICAL_M06_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS\n"
            ).encode(),
            "02_jtag_m06.jou":b"MOCK-NOT-VIVADO\n",
            "03_exit.txt":b"vivado_physical_exit=0\n",
            "10_m06_32x4_golden.hex":("\n".join(oracle.words())+"\n").encode(),
            "80_m06_32x4_hw_parity.txt":(
                header+"\n".join(audit.expected_lines())+"\n").encode(),
        }
        self.assertEqual(set(content),set(audit.FILES))
        for name,value in content.items():
            (hw/name).write_bytes(value)
        self.rehash(hw)
        return native,hw

    @staticmethod
    def rehash(hw):
        (hw/"99_evidence_sha256.txt").write_text(
            "".join(sha256((hw/name).read_bytes()).hexdigest()+"  "+name+"\n"
                    for name in audit.FILES),encoding="ascii")

    def accepted(self):
        return patch.object(audit.native_gate,"inspect",return_value={
            "status":"M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD",
            "candidate_sha256":native_gate.OWNER_ORIGINAL_BIT_SHA,
        })

    def test_synthetic_complete_384_neural_quantities_auditor_parser(self):
        with TemporaryDirectory() as tmp:
            native,hw=self.make_mock(Path(tmp))
            with self.accepted():
                result=audit.verify(native,hw)
                self.assertEqual(result["hardware_voltages_verified"],128)
                self.assertEqual(result["hardware_spike_decisions_verified"],128)
                self.assertEqual(result["hardware_synaptic_currents_verified"],128)
                self.assertEqual(result["candidate_sha256"],
                                 native_gate.OWNER_ORIGINAL_BIT_SHA)
                self.assertFalse(result["m06_hls_physical"])
                self.assertFalse(result["physical_ddr"])

    def test_rehashed_changed_voltage_result_still_rejects(self):
        with TemporaryDirectory() as tmp:
            native,hw=self.make_mock(Path(tmp))
            name=hw/"80_m06_32x4_hw_parity.txt"
            txt=name.read_text()
            self.assertIn("neuron=0 voltages=",txt)
            txt=txt.replace("neuron=0 voltages=","neuron=0 voltages=DEADBEEF,",1)
            name.write_text(txt)
            self.rehash(hw)
            with self.accepted(),self.assertRaisesRegex(
                    audit.Reject,"hardware 128 voltage/mask/synaptic"):
                audit.verify(native,hw)

    def test_rehashed_changed_program_log_fails(self):
        with TemporaryDirectory() as tmp:
            native,hw=self.make_mock(Path(tmp))
            name=hw/"01_jtag_m06.log"
            txt=name.read_text().replace("M08_D3D2C_PROGRAM_COMPLETED\n","")
            name.write_text(txt)
            self.rehash(hw)
            with self.accepted(),self.assertRaisesRegex(
                    audit.Reject,"actual board log missing"):
                audit.verify(native,hw)

    def test_rehashed_fake_second_program_fails(self):
        with TemporaryDirectory() as tmp:
            native,hw=self.make_mock(Path(tmp))
            name=hw/"01_jtag_m06.log"
            txt=name.read_text().replace(
                "M08_D3D2C_PROGRAM_COMPLETED\n",
                "M08_D3D2C_PROGRAM_COMPLETED\nM08_D3D2C_PROGRAM_START\n")
            name.write_text(txt)
            self.rehash(hw)
            with self.accepted(),self.assertRaisesRegex(
                    audit.Reject,"ambiguous/multiple program markers"):
                audit.verify(native,hw)

    def test_changed_executed_source_rejected_even_after_ledger_rehash(self):
        with TemporaryDirectory() as tmp:
            native,hw=self.make_mock(Path(tmp))
            name=hw/"00_executed_source.tcl"
            name.write_bytes(name.read_bytes()+b"\n# MUTATION\n")
            self.rehash(hw)
            with self.accepted(),self.assertRaisesRegex(
                    audit.Reject,"executed Tcl source changed"):
                audit.verify(native,hw)

    def test_native_exact_image_is_always_required(self):
        with TemporaryDirectory() as tmp:
            native,hw=self.make_mock(Path(tmp))
            with self.assertRaises(audit.Reject):
                audit.verify(native,hw)

if __name__=="__main__":
    unittest.main()
