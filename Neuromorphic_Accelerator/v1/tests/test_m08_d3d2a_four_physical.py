"""D3.D.2A physical-programming protocol source/receipt tests: NO BOARD."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_d3d2a_four_gate as gate
import m08_d3d2a_four_physical_audit as audit


class FourNeuronPhysicalTests(unittest.TestCase):
    def test_one_program_call_only_after_identity_hash_and_golden(self):
        script = audit.TCL.read_text()
        runner = (ROOT / "scripts/run_m08_d3d2a_four_physical_once.sh").read_text()
        self.assertEqual(
            len(re.findall(r"(?m)^\s*program_hw_devices \$fpga\s*$",script)),1)
        self.assertIn("M08_D3D2A_ALLOW_PROGRAM",script)
        self.assertIn("M08_D3D2A_ALLOW_PROGRAM",runner)
        self.assertIn("EXPECTED_SHA=\"3c213c1271f48106495203d008d7f46619f8f079549117e404fca11fd3179411\"",runner)
        self.assertIn("m08_d3d2a_four_gate.py\" --run-dir",runner)
        self.assertEqual(runner.count("vivado -mode batch"),1)
        self.assertIn("M08_D3D2A_HW_STOP_NO_RETRY",runner)
        self.assertIn("M08_D3D2A_BRAM_TRANSPORT_REGRESSION_PASS",script)
        self.assertIn("M08_D3D2A_FOUR_NEURON_LIF_IDENTITY_PASS",script)
        self.assertIn("55AA22DD",script)
        self.assertIn("4D344C46",script)
        self.assertIn("00020000",script)
        self.assertIn("35+$n*5+$j",script)
        self.assertIn("35+$n*5+4",script)
        self.assertIn("0xA0001040",script)
        self.assertIn("0xA0001100",script)
        for unsafe in ("write_cfgmem","program_flash","xmutil loadapp","/dev/mem",
                       "M_AXI_HPM0_FPD","ssh "):
            self.assertNotIn(unsafe,script)
        self.assertFalse((ROOT/"scripts/m08_d3d2a_four_build.tcl").read_text().find(
            "program_hw_devices") >= 0)

    def test_physical_runner_shell_valid(self):
        result = subprocess.run(
            ["bash","-n",str(ROOT/"scripts/run_m08_d3d2a_four_physical_once.sh")],
            capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_independent_auditor_mock_receipts_and_mutations(self):
        # Synthetic only: proves auditor does not trust an arbitrary 'PASS'.
        # Actual HW acceptance always requires genuine native original receipts.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)/"M08"
            base.mkdir()
            native = base/"m08_d3d2a_four_native123"
            native.mkdir()
            hw = base/"m08_d3d2a_four_HW_synthetic123"
            hw.mkdir()
            outputs = {
                "00_executed_source.tcl": audit.TCL.read_bytes(),
                "01_jtag_neuron.log": (
                    "M08_D3D2A_IMAGE_HASH_VERIFIED|"+gate.ORIGINAL_OWNER_BIT_SHA+"\n"
                    "M08_D3D2A_GOLDEN_FOUR_NEURON_FIXTURES_VERIFIED|2\n"
                    "M08_D3D2A_DEVICE|xck26_0|xck26\n"
                    "M08_D3D2A_PROGRAM_COMPLETED\n"
                    "M08_D3D2A_AXI_MASTER|hw_axi_1\n"
                    "M08_D3D2A_BRAM_TRANSPORT_REGRESSION_PASS\n"
                    "M08_D3D2A_FOUR_NEURON_LIF_IDENTITY_PASS\n"
                    + "".join("M08_D3D2A_HW_FOUR_NEURON_M02_PARITY_PASS|"+
                              f.name+"|00000002,00000001,00000000,00000000\n"
                              for f in audit.FIXTURES)
                    + "M08_D3D2A_HW_RESULT_PC_RECEIPT=/original/nonprod\n"
                ).encode(),
                "02_jtag_neuron.jou": b"synthetic Tcl journal\n",
                "03_exit.txt": b"vivado_physical_exit=0\n",
                "10_m02_golden.txt": audit.expected_golden().encode(),
            }
            header = dict(audit.HEADER)
            header["candidate_sha256"] = gate.ORIGINAL_OWNER_BIT_SHA
            result = ("\n".join(f"{key}={value}" for key,value in header.items())+
                      "\n"+"\n".join(audit.expected_lines())+"\n")
            outputs["80_neural_parity_readback.txt"] = result.encode()
            for name,content in outputs.items():
                (hw/name).write_bytes(content)
            def refresh_receipt():
                (hw/"99_evidence_sha256.txt").write_text(
                    "".join(sha256((hw/name).read_bytes()).hexdigest()
                            +"  "+name+"\n" for name in audit.FILES))
            refresh_receipt()
            with patch.object(audit.gate, "native",
                              return_value={"candidate_sha256":
                                            gate.ORIGINAL_OWNER_BIT_SHA}):
                ok = audit.verify(native,hw)
                self.assertTrue(ok["hardware_execution_verified"])
                self.assertEqual(ok["neuron_timestep_voltages_verified"],32)
                self.assertEqual(ok["status"],
                    "M08_D3D2A_PHYSICAL_FOUR_NEURON_FOUR_TICK_M02_PARITY_ACCEPTED")
                # The SHA ledger must fail if result mutated without receipt.
                file = hw/"80_neural_parity_readback.txt"
                before = file.read_bytes()
                file.write_bytes(before.replace(b"hardware=PASS",b"hardware=FAIL",1))
                with self.assertRaisesRegex(audit.Reject, "SHA mismatch"):
                    audit.verify(native,hw)
                # Even re-hashing forged data is insufficient.
                refresh_receipt()
                with self.assertRaisesRegex(audit.Reject, "voltages/spikes"):
                    audit.verify(native,hw)
                file.write_bytes(before)
                refresh_receipt()
                log = hw/"01_jtag_neuron.log"
                saved = log.read_bytes()
                log.write_bytes(saved.replace(b"M08_D3D2A_PROGRAM_COMPLETED",
                                               b"not_programmed"))
                refresh_receipt()
                with self.assertRaisesRegex(audit.Reject,"log marker"):
                    audit.verify(native,hw)


if __name__ == "__main__":
    unittest.main()
