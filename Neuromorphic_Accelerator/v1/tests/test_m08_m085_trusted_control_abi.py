"""M08.5 versioned source-only trusted-control ABI + genuine Icarus lease fence.

The TB supplies FAKE kernel-binding, trust and interconnect drain signals.
Passing is NOT Linux DMA ownership, PS AXI-Lite, real drain, or KV260 evidence.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "m08"
FILES = [
    RTL / "m08_m085_kernel_dma_lease_fence.v",
    RTL / "m08_m085_trusted_control_abi.v",
    RTL / "tb_m08_m085_trusted_control_abi.sv",
]


class M085TrustedControlAbiTests(unittest.TestCase):
    def test_source_abi_retains_unbound_external_trust_and_drain(self):
        src = FILES[1].read_text()
        self.assertIn("ABI_VERSION=32'h00010000", src)
        self.assertIn("CAP_MAGIC=32'h4d303835", src)
        self.assertIn("m08_m085_kernel_dma_lease_fence fence", src)
        self.assertIn("written_mask==4'hf", src)
        self.assertIn("DRAIN_ACK_LOW", src)
        self.assertIn("DRAIN_ACK_HIGH", src)
        self.assertIn("interconnect_drain_ack", src)
        self.assertIn("csr_trusted", src)
        self.assertIn("stop_new_requests", src)
        self.assertIn("admitted_begin=admit_work ? fence_begin : 64'd0", src)
        for banned in ("open_hw_manager", "program_hw_devices", "dma_alloc_coherent",
                       "/dev/mem", "0x40000000"):
            self.assertNotIn(banned, src)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "genuine Icarus required; no mock RTL pass")
    def test_real_fence_and_versioned_control_drain_faults(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "trusted_control_abi.vvp"
            comp = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m08_m085_trusted_control_abi",
                 "-o", str(exe), *map(str, FILES)],
                text=True, capture_output=True, timeout=90
            )
            self.assertEqual(comp.returncode, 0, comp.stdout + comp.stderr)
            self.assertEqual(comp.stderr.strip(), "", "Icarus warnings prohibited")
            for case in range(20):
                with self.subTest(case=case):
                    run = subprocess.run(
                        ["vvp", str(exe), f"+CASE={case}"],
                        text=True, capture_output=True, timeout=30
                    )
                    self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                    self.assertEqual(run.stderr.strip(), "", run.stderr)
                    self.assertNotIn("FATAL", run.stdout)
                    if case == 0:
                        self.assertEqual(
                            run.stdout.count("M08_5_TRUSTED_CONTROL_ABI_FRESH_DRAIN_PASS"),
                            1, run.stdout
                        )
                    else:
                        self.assertIn(
                            f"M08_5_TRUSTED_CONTROL_NEGATIVE_PASS case={case}",
                            run.stdout
                        )


if __name__ == "__main__":
    unittest.main()
