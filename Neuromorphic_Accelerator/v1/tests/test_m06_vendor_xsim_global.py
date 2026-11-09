"""Guard authentic XPM/global XSim setup after owner glbl elaboration failure.

These are source integrity tests only. They DO NOT run Vivado or claim a vendor
simulation PASS. Owner 2026-11-09 xelab failed: VRFC 10-2989 glbl undeclared
inside authentic installed XPM xpm_cdc.sv; previous xvlog completed 56 original
memory interconnect RTL dependencies and both generated testbench tops.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_m06_original_mem_sc_vendor_xsim.sh"


class VivadoGlobalPrimitivesTests(unittest.TestCase):
    def test_owner_runner_is_valid_bash(self):
        p = subprocess.run(["bash", "-n", str(RUNNER)],
                           capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_installed_real_vivado_glbl_compiled_and_dual_elaboration_roots(self):
        code = RUNNER.read_text(encoding="utf-8")
        self.assertIn('$XILINX_VIVADO/data/verilog/src/glbl.v', code)
        self.assertIn('grep -Eq', code)
        self.assertIn('"$GLBL" \\\n  2>&1 | tee "$OUT/03_xvlog.log"', code)
        self.assertEqual(code.count(' work.glbl \\\n  -s '), 2)
        self.assertIn('work.tb_m06_original_mem_sc_vendor work.glbl', code)
        self.assertIn('work.tb_m06_original_vendor_paged work.glbl', code)
        self.assertIn('"$OUT/installed_vivado_glbl_sha256.txt"', code)
        self.assertIn('"$OUT/installed_vivado_glbl_path.txt"', code)
        self.assertIn(' -L xpm -L unisims_ver -L secureip', code)
        self.assertIn('source original Vivado 2025.2 settings64.sh', code)
        self.assertNotIn('module glbl', code)
        self.assertNotIn('generate_target', code)
        self.assertNotIn('program_hw_devices', code)

    def test_prior_compile_includes_and_readonly_identity_still_enforced(self):
        code = RUNNER.read_text(encoding="utf-8")
        self.assertIn('m06_vendor_compile_plan.py', code)
        self.assertIn('"$OUT/02_original_vendor_compile_plan.json"', code)
        self.assertIn('sha256sum "$SIM_TOP" "$BD_SUB"', code)
        self.assertIn('cmp -s "$OUT/sha_before.txt"', code)
        self.assertIn('grep -Fq', code)
        self.assertIn('M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS', code)
        self.assertIn('M06_ORIGINAL_VENDOR_PAGED_RTL_PASS', code)
        self.assertIn('M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS', code)


if __name__ == "__main__":
    unittest.main()
