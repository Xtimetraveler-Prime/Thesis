"""M08.2b physical bring-up READ-ONLY source contracts.

No actual board, JTAG cable, FPGA programming or Linux MMIO occurs in CI.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
JTAG=ROOT/"scripts/m08_kv260_jtag_readonly_inventory.tcl"
LINUX=ROOT/"scripts/m08_kv260_linux_readonly_inventory.sh"


class M08PhysicalInventorySourceTests(unittest.TestCase):
    def test_jtag_inventory_never_programs_or_changes_board(self):
        t=JTAG.read_text()
        operative="\n".join(
            line for line in t.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        for required in (
            "open_hw", "connect_hw_server -url localhost:3121",
            "get_hw_targets -quiet",
            "current_hw_target $target",
            "open_hw_target", "get_hw_devices -quiet",
            "JTAG_DEVICE|$name|$part",
            "M08_JTAG_ENUMERATED_ONLY_NO_BOARD_CONFIGURATION_CHANGE",
            "if {[llength $targets] != 1}",
        ):
            self.assertIn(required, operative)
        for forbidden in (
            "program_hw_devices", "set_property PROGRAM.FILE",
            "write_bitstream", "write_cfgmem", "mwr ", "mrd ",
            "write_hw_icap", "reset_hw_axi", "bootgen ",
            "load_hw_device", "exec sudo",
        ):
            self.assertNotIn(forbidden, operative)
        self.assertLess(operative.index("get_hw_targets -quiet"),
                        operative.index("open_hw_target"))
        self.assertLess(operative.index("open_hw_target"),
                        operative.index("get_hw_devices -quiet"))

    def test_linux_capture_read_only_and_exclusive(self):
        script=LINUX.read_text()
        operative="\n".join(
            line for line in script.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        self.assertIn("mktemp -d",operative)
        self.assertIn("M08_BOARD_READONLY_EVIDENCE_DIR=",operative)
        self.assertIn("xmutil listapps",operative)
        self.assertIn("/sys/class/fpga_manager/",operative)
        self.assertIn("fancontrol",operative)
        self.assertIn("/proc/device-tree/model",operative)
        self.assertIn("sha256sum -- *.txt",operative)
        for forbidden in (
            "xmutil loadapp", "xmutil unloadapp",
            "program_hw_devices", "sudo ", "/dev/mem", "devmem ",
            "bootfw_update", "mwr ", "fpga load",
            "systemctl restart", "systemctl stop",
            "rm -rf", "mkfs", "flashcp ",
        ):
            self.assertNotIn(forbidden,operative)

    @unittest.skipUnless(shutil.which("bash"),"bash unavailable")
    def test_linux_source_bash_syntax(self):
        p=subprocess.run(["bash","-n",str(LINUX)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl parser unavailable")
    def test_jtag_source_tcl_syntax_without_hardware(self):
        script=(
            "set h [open {" + str(JTAG) + "} r]\n"
            "set s [read $h]\nclose $h\n"
            'if {![info complete $s]} {puts stderr INCOMPLETE; exit 3}\n'
            "puts M08_JTAG_TCL_PARSE_ONLY_NOT_PHYSICAL\n"
        )
        p=subprocess.run(["tclsh"],input=script,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn("M08_JTAG_TCL_PARSE_ONLY_NOT_PHYSICAL",p.stdout)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl parser unavailable")
    def test_jtag_mock_unique_board_cable_or_safe_rejection(self):
        """Pure Tcl mock; no hw_server, board, or physical action."""
        for targets,expect_pass in (
            (["mock_KV260_cable"],True),
            ([],False),
            (["mock_KV260_cable","another_cable"],False),
        ):
            with self.subTest(target_count=len(targets)):
                with tempfile.TemporaryDirectory() as td:
                    report=Path(td)/"fresh_target.txt"
                    harness=(
                        "set argv [list {" + str(report) + "}]\n"
                        "proc version {args} {return 2025.2}\n"
                        "proc open_hw {} {}\n"
                        "proc connect_hw_server {args} {}\n"
                        "proc get_hw_targets {args} {return {" +
                        " ".join(targets) + "}}\n"
                        "proc current_hw_target {args} {}\n"
                        "proc open_hw_target {} {}\n"
                        "proc get_hw_devices {args} {return {xck26_0}}\n"
                        'proc get_property {args} {\n'
                        '  if {[lindex $args 1] eq "NAME"} {return xck26_0}\n'
                        '  if {[lindex $args 1] eq "PART"} {return xck26-sfvc784-2LV-c}\n'
                        '  error "unexpected mock property"\n'
                        '}\n'
                        "proc close_hw_target {} {}\n"
                        "proc disconnect_hw_server {} {}\n"
                        "proc close_hw {} {}\n"
                        "if {[catch {source {" + str(JTAG) + "}} err]} {\n"
                        "  puts MOCK_EXPECTED_STOP:$err\n"
                        "  exit 0\n"
                        "}\n"
                        "puts MOCK_INVENTORY_OK\n"
                    )
                    p=subprocess.run(["tclsh"],input=harness,text=True,
                                     capture_output=True,timeout=30)
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                    if expect_pass:
                        self.assertIn("MOCK_INVENTORY_OK",p.stdout)
                        self.assertIn("JTAG_DEVICE|xck26_0|xck26-sfvc784-2LV-c",
                                      report.read_text())
                    else:
                        self.assertIn("MOCK_EXPECTED_STOP:",p.stdout)
                        self.assertNotIn("MOCK_INVENTORY_OK",p.stdout)


if __name__=="__main__":
    unittest.main()
