"""Adversarial genuine Icarus MMIO work-command sequencer protocol tests.

This unit TB supplies synthetic neural-status signals. The separate
full managed-neural test uses real signed16 LIF/bank/AXI4 RTL with 512 golden.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

RTL=Path(__file__).resolve().parents[1]/"rtl/m08"
SOURCES=(
    RTL/"m08_m085_work_command_sequencer.v",
    RTL/"tb_m08_m085_work_command_sequencer.sv"
)


class M085WorkCommandSequencerTests(unittest.TestCase):
    def test_source_is_bounded_and_explicitly_external_owner(self):
        rtl=SOURCES[0].read_text()
        for needle in (
            "module m08_m085_work_command_sequencer",
            "WORK_TIMEOUT_CYCLES=8192", "trusted_owner",
            "raw_lease_admit","source_admit","stop_new_requests",
            "write_strb==4'hf", "write_addr[1:0]==0",
            "neural_bank_logical==expected_logical",
            "completed_commands<=completed_commands+1",
            "phase<=FAULT",
            "assign page_req=phase==PAGE_START",
            "assign dispatch_req=phase==DISPATCH_START",
        ):
            self.assertIn(needle,rtl)
        for banned in ("program_hw_devices","open_hw_manager", "/dev/mem",
                       "dma_alloc_coherent(", "0x40000000"):
            self.assertNotIn(banned,rtl+SOURCES[1].read_text())

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "genuine real Icarus; no mock RTL success")
    def test_19_adverse_and_one_three_operation_lifecycle(self):
        with tempfile.TemporaryDirectory() as root:
            exe=Path(root)/"work_mmio.vvp"
            comp=subprocess.run(
                ["iverilog","-g2012","-s","tb_m08_m085_work_command_sequencer",
                 "-o",str(exe),*[str(p) for p in SOURCES]],
                capture_output=True,text=True,timeout=60
            )
            self.assertEqual(comp.returncode,0,comp.stdout+comp.stderr)
            self.assertEqual(comp.stderr.strip(),"")
            for case in range(20):
                with self.subTest(case=case):
                    run=subprocess.run(
                        ["vvp",str(exe),f"+CASE={case}"],
                        capture_output=True,text=True,timeout=25
                    )
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                    self.assertEqual(run.stderr.strip(),"")
                    expected=("M08_5_MMIO_WORK_LOAD_DISPATCH_SAVE_POSITIVE_PASS"
                              if case==0 else f"M08_5_MMIO_WORK_ADVERSE_PASS case={case}")
                    self.assertEqual(run.stdout.count(expected),1,run.stdout)


if __name__=="__main__":
    unittest.main()
