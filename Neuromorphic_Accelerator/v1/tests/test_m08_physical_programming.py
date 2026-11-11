"""M08.2b guarded physical programming source regression.

All Vivado/JTAG calls below are Tcl MOCKS. NO actual physical action.
The real original SHA-pinned .bit is not present in CI.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT / "scripts/m08_kv260_program_oneshot.tcl"
SH = ROOT / "scripts/run_m08_kv260_program_oneshot.sh"
EXPECTED = "170da137f315a6f53c345c416808c5203e866b8772acb6b7e69265fe38d31bbf"
REVIEW = """mode=ISOLATED_JTAG
linux_pl_ownership=NONE_CONFIRMED
fan_cooling=INDEPENDENT_VERIFIED
active_pl_replacement=APPROVED
operator_authorization=YES
"""


class PhysicalProgrammingSourceTests(unittest.TestCase):
    def test_source_is_explicitly_M08_not_Loihi_VIO_or_firmware(self):
        t = TCL.read_text()
        s = SH.read_text()
        t_active = "\n".join(
            x for x in t.splitlines() if x.strip() and not x.lstrip().startswith("#")
        )
        for must in (
            "open_hw_manager",
            "connect_hw_server -url localhost:3121",
            "get_hw_targets -quiet",
            "current_hw_target [lindex $targets 0]",
            "open_hw_target",
            "get_hw_devices -quiet",
            'set_property PROGRAM.FILE $bit_file $fpga',
            "program_hw_devices $fpga",
            "refresh_hw_device $fpga",
            "M08_JTAG_PROGRAMMED_BITSTREAM_NO_PS_AXI_READBACK",
            "M08_BOARD_REVIEW_FILE",
            "ISOLATED_JTAG",
            EXPECTED,
        ):
            self.assertIn(must, t_active)
        self.assertEqual(t_active.count("program_hw_devices $fpga"), 1)
        self.assertLess(t_active.index("set expected_sha"),
                        t_active.index("open_hw_manager"))
        self.assertLess(t_active.index("get_hw_targets -quiet"),
                        t_active.index("get_hw_devices -quiet"))
        self.assertLess(t_active.index("get_hw_devices -quiet"),
                        t_active.index("program_hw_devices $fpga"))
        self.assertIn("sha256sum --", s)
        self.assertIn("mktemp -d", s)
        self.assertIn("05_evidence_sha256.txt", s)
        self.assertIn("M08_ALLOW_PROGRAM", s)
        self.assertIn("M08_BOARD_REVIEW_FILE", s)
        for bad in ("get_hw_vios", "get_hw_probes", "PROBES.FILE",
                    "FULL_PROBES.FILE", "write_cfgmem", "mwr ", "mrd ",
                    "xmutil unloadapp", "xmutil loadapp", "/dev/mem",
                    "bootfw_update", "flashcp ", "reset_hw_axi"):
            self.assertNotIn(bad, t_active)
        for bad in ("xmutil unloadapp", "xmutil loadapp", "/dev/mem",
                    "bootfw_update", "flashcp ", "sudo ", "rm -rf"):
            self.assertNotIn(bad, "\n".join(
                x for x in s.splitlines() if not x.lstrip().startswith("#")
            ))

    @unittest.skipUnless(shutil.which("bash"), "bash absent")
    def test_bash_parses_and_cannot_program_without_approval(self):
        p = subprocess.run(["bash", "-n", str(SH)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        with tempfile.TemporaryDirectory() as td:
            bit = Path(td) / "05_m08_safe_page.bit"
            with bit.open("wb") as f:
                f.truncate(7797831)
            env = os.environ.copy()
            for name in ("M08_ALLOW_PROGRAM", "M08_APPROVED_MODE",
                         "M08_BOARD_REVIEW_FILE"):
                env.pop(name, None)
            p = subprocess.run(["bash", str(SH), str(bit)], env=env,
                               capture_output=True, text=True, timeout=10)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("approvals missing", p.stderr)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh absent")
    def test_tcl_mock_only_programs_unique_exact_K26_after_all_gates(self):
        cases = (
            ("approved_mock_only", "exact", "both", "good", True, 1),
            ("wrong_sha", "exact", "both", "bad", True, 0),
            ("wrong_cable", "changed", "both", "good", True, 0),
            ("two_targets", "multiple", "both", "good", True, 0),
            ("dap_only", "exact", "dap", "good", True, 0),
            ("duplicate_fpga", "exact", "duplicate", "good", True, 0),
            ("no_approval", "exact", "both", "good", False, 0),
        )
        for label, target, devices, digest, approval, expected_calls in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                path = Path(td)
                bit = path / "05_m08_safe_page.bit"
                with bit.open("wb") as f:
                    f.truncate(7797831)
                result = path / "result.txt"
                review = path / "review.txt"
                review.write_text(REVIEW)
                targs = {
                    "exact": "localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
                    "changed": "different_cable",
                    "multiple": "different_cable other_cable",
                }[target]
                devs = {
                    "both": "xck26_0 arm_dap_1",
                    "dap": "arm_dap_1",
                    "duplicate": "xck26_0 xck26_0 arm_dap_1",
                }[devices]
                mock_sha = EXPECTED if digest == "good" else "0" * 64
                script = (
                    "set argv [list {" + str(bit) + "} {" + str(result) + "}]\n"
                    "set ::env(M08_ALLOW_PROGRAM) " +
                    ("YES" if approval else "NO") + "\n"
                    "set ::env(M08_APPROVED_MODE) ISOLATED_JTAG\n"
                    "set ::env(M08_BOARD_REVIEW_FILE) {" + str(review) + "}\n"
                    "set ::calls 0\n"
                    "proc version {args} {return 2025.2}\n"
                    "proc exec {args} {return {" + mock_sha + "  sample.bit}}\n"
                    "proc open_hw_manager {} {}\n"
                    "proc connect_hw_server {args} {}\n"
                    "proc get_hw_targets {args} {return {" + targs + "}}\n"
                    "proc current_hw_target {args} {}\n"
                    "proc open_hw_target {} {}\n"
                    "proc get_hw_devices {args} {return {" + devs + "}}\n"
                    "proc get_property {prop obj} {\n"
                    " if {$prop eq \"NAME\"} {return $obj}\n"
                    " if {$prop eq \"PART\"} {\n"
                    "   if {$obj eq \"xck26_0\"} {return xck26}\n"
                    "   return arm_dap\n"
                    " }\n"
                    " error \"unexpected property\"\n"
                    "}\n"
                    "proc current_hw_device {args} {}\n"
                    "proc refresh_hw_device {args} {}\n"
                    "proc set_property {args} {}\n"
                    "proc program_hw_devices {d} {\n"
                    " if {$d ne \"xck26_0\"} {error \"mock selected DAP\"}\n"
                    " incr ::calls\n"
                    "}\n"
                    "proc close_hw_target {} {}\n"
                    "proc disconnect_hw_server {} {}\n"
                    "proc close_hw_manager {} {}\n"
                    "set failed [catch {source {" + str(TCL) + "}} detail]\n"
                    "puts \"MOCK_RESULT|$failed|$::calls|$detail\"\n"
                )
                p = subprocess.run(["tclsh"], input=script, capture_output=True,
                                   text=True, timeout=15)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn("MOCK_RESULT|", p.stdout)
                self.assertIn(f"|{expected_calls}|", p.stdout)
                self.assertEqual(result.is_file(), expected_calls == 1)
                if expected_calls:
                    self.assertIn("result=PROGRAMMED_ONLY_NO_PS_AXI_PROOF",
                                  result.read_text())
                else:
                    self.assertIn("MOCK_RESULT|1|0|", p.stdout)


if __name__ == "__main__":
    unittest.main()
