"""D3.D.2B one-shot physical harness + independent evidence mutation tests.

NO hardware. Tests source and synthetic receipts; no native/FPGA claim.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2b_synaptic_physical_audit as audit


class PhysicalSynapticTests(unittest.TestCase):
    def test_one_shot_protocol_only_after_new_native_gate(self):
        script=audit.TCL.read_text()
        runner=(ROOT/"scripts/run_m08_d3d2b_synaptic_physical_once.sh").read_text()
        self.assertEqual(len(re.findall(
            r"(?m)^\s*program_hw_devices \$fpga\s*$",script)),1)
        self.assertIn("M08_D3D2B_ALLOW_PROGRAM",runner)
        self.assertIn("M08_D3D2B_ALLOW_PROGRAM",script)
        self.assertIn('m08_d3d2b_synaptic_gate.py" --run-dir',runner)
        self.assertEqual(runner.count("vivado -mode batch"),1)
        self.assertIn("M08_D3D2B_HW_STOP_NO_RETRY",runner)
        self.assertIn("4D34534E",script)
        self.assertIn("00030000",script)
        self.assertIn("M08_D3D2B_BRAM_TRANSPORT_PASS",script)
        self.assertIn("M08_D3D2B_ROUTED_SYNAPSE_IDENTITY_PASS",script)
        for word in ("35+$n", "0xA0001200", "0xA0001300"):
            if word=="35+$n":
                continue  # D2B has different 104-field reference frame.
            self.assertIn(word,script)
        self.assertIn("68+$n*9",script)
        self.assertIn("offset+5+$j",script)
        self.assertIn("M08_D3D2B_PHYSICAL_ROUTED_RESULT_PC_RECEIPT",script)
        for forbidden in ("xmutil loadapp", "/dev/mem",
                          "M_AXI_HPM0_FPD", "write_cfgmem", "program_flash"):
            self.assertNotIn(forbidden,script)
        result=subprocess.run(
            ["bash","-n",str(ROOT/"scripts/run_m08_d3d2b_synaptic_physical_once.sh")],
            capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_mock_auditor_accepts_only_unmodified_all_trace_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            base=Path(root)/"M08"
            base.mkdir()
            native=base/"m08_d3d2b_synaptic_native123"
            hw=base/"m08_d3d2b_synaptic_HW_synthetic123"
            native.mkdir();hw.mkdir()
            digest="a"*64
            markers=[
                "M08_D3D2B_IMAGE_HASH_VERIFIED|"+digest,
                "M08_D3D2B_M02_ROUTING_FIXTURES_VERIFIED|2",
                "M08_D3D2B_DEVICE|xck26_0|xck26",
                "M08_D3D2B_PROGRAM_COMPLETED",
                "M08_D3D2B_AXI_MASTER|hw_axi_1",
                "M08_D3D2B_BRAM_TRANSPORT_PASS",
                "M08_D3D2B_ROUTED_SYNAPSE_IDENTITY_PASS",
                *(("M08_D3D2B_HW_M02_RECURRENT_SYNAPSE_PARITY_PASS|"
                   +f.name+"|00000001,00000002,00000004,00000008")
                  for f in audit.FIXTURES),
                "M08_D3D2B_PHYSICAL_ROUTED_RESULT_PC_RECEIPT=/original",
            ]
            data=dict(audit.METADATA)
            data["candidate_sha256"]=digest
            original={
                "00_executed_source.tcl":audit.TCL.read_bytes(),
                "01_jtag_synaptic.log":("\n".join(markers)+"\n").encode(),
                "02_jtag_synaptic.jou":b"synthetic Tcl journal\n",
                "03_exit.txt":b"vivado_physical_exit=0\n",
                "10_m02_golden.txt":audit.expected_golden().encode(),
                "80_synaptic_parity_readback.txt":(
                    "\n".join(k+"="+v for k,v in data.items())+"\n"
                    +"\n".join(audit.expected_lines())+"\n").encode(),
            }
            for name,content in original.items():
                (hw/name).write_bytes(content)
            def ledger():
                (hw/"99_evidence_sha256.txt").write_text(
                    "".join(sha256((hw/name).read_bytes()).hexdigest()
                            +"  "+name+"\n" for name in audit.FILES))
            ledger()
            with patch.object(audit.gate,"native",
                              return_value={"candidate_sha256":digest}):
                got=audit.verify(native,hw)
                self.assertTrue(got["recurrent_synapse_routing_physically_verified"])
                self.assertEqual(got["hardware_membrane_voltages_verified"],32)
                self.assertEqual(got["hardware_delivered_synapse_current_words_verified"],32)
                file=hw/"80_synaptic_parity_readback.txt"
                file.write_bytes(original[file.name].replace(
                    b"hardware=PASS",b"hardware=FAIL",1))
                with self.assertRaisesRegex(audit.Reject,"SHA changed"):
                    audit.verify(native,hw)
                ledger()
                with self.assertRaisesRegex(audit.Reject,"trace"):
                    audit.verify(native,hw)
                file.write_bytes(original[file.name]);ledger()
                log=hw/"01_jtag_synaptic.log"
                log.write_bytes(original[log.name].replace(
                    b"M08_D3D2B_PROGRAM_COMPLETED",b"PROGRAM_NOT_DONE"))
                ledger()
                with self.assertRaisesRegex(audit.Reject,"log missing"):
                    audit.verify(native,hw)


if __name__=="__main__":
    unittest.main()
