"""D3.D.2D owner offline raw-event Vivado and physical no-program gate.

All tests are PC-only. No test calls genuine Vivado or physical programming.
Even if new native bitgen succeeds, the exact first-image DRC gate must STOP.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2d_event_native_review as gate

class RawM06NativeBoundaryTests(unittest.TestCase):
    def test_separate_vendor_builder_preserves_jtag_fan_and_closed_hpm(self):
        s=(ROOT/"scripts/m08_d3d2d_event_build.tcl").read_text()
        active="\n".join(line for line in s.splitlines()
                         if line.strip() and not line.lstrip().startswith("#"))
        for term in (
            "m08_d3d2d_raw_event_lif_axil.v",
            "module -reference m08_d3d2d_raw_event_lif_axil",
            "m08_d3d2d_event_lif_jtag_wrapper",
            "m08_d3d2d_event_lif_jtag_UNRELEASED.bit",
            "THIRTY_TWO_NEURON_M06_RAW_17_EVENT_INGRESS_3_4_SIGNED16",
            "event_mailbox_capacity=64",
            "external_event_coalescing=FPGA_AXI_LITE_EVENT_PUSH",
            "hardware_signed_event_accumulation=YES",
            "physical_event_stream_dma=NO",
            "0xA0000000","0xA0001000",
            "CONFIG.PSU__USE__M_AXI_GP0 0",
            "CONFIG.PSU__USE__M_AXI_GP1 0",
            "CONFIG.PSU__USE__M_AXI_GP2 0",
            "M08_FAN_PWM","TTC0",
            "report_drc -file","report_timing_summary -file",
            "write_bitstream -file $bit",
            "hardware_bitstream_programmed=NO",
        ):
            self.assertIn(term,active,term)
        for forbidden in ("m08_d3d2c_m06_32_lif_axil",
                          "open_hw_manager","program_hw_devices",
                          "connect_hw_server","run_hw_axi",
                          "/dev/mem","/dev/uio","xmutil ","sudo ","ssh "):
            self.assertNotIn(forbidden,active,forbidden)

    def test_shell_syntax_unique_owner_folder_and_no_reprogram(self):
        shell=ROOT/"scripts/run_m08_d3d2d_event_pc.sh"
        x=subprocess.run(["bash","-n",str(shell)],capture_output=True,
                         text=True,timeout=20)
        self.assertEqual(x.returncode,0,x.stdout+x.stderr)
        body=shell.read_text()
        for term in (
            "mktemp -d","m08_d3d2d_event_gate.py",
            "m08_d3d2d_event_native_review.py",
            "sha256sum -c 99_evidence_sha256.txt",
            "M08_D3D2D_NO_BOARD_NO_JTAG_NO_IMAGE_RELEASE",
            "m08_d3d2d_event_lif_jtag_UNRELEASED.bit",
        ):
            self.assertIn(term,body,term)
        self.assertNotIn("m08_d3d2c_m06_MN2pwduB",body)
        self.assertNotIn("program_hw_devices",body)
        self.assertNotIn("open_hw_manager",body)

    def test_missing_forged_native_evidence_is_never_accepted(self):
        with TemporaryDirectory() as d:
            fake=Path(d)/"M08"/"m08_d3d2d_event_FAKE"
            fake.mkdir(parents=True)
            with self.assertRaises(gate.Reject):
                gate.inspect(fake)

    def test_new_first_image_native_gate_never_authorizes_any_board(self):
        src=(ROOT/"scripts/m08_d3d2d_event_native_review.py").read_text()
        self.assertIn("M08_D3D2D_FIRST_NEW_NATIVE_DRC_REVIEW_REQUIRED_NO_BOARD",src)
        self.assertIn("return 2",src)
        self.assertIn("original_drc_sha256",src)
        self.assertIn("physical_authorized=False",src)
        self.assertIn("physical_programmed=False",src)
        self.assertIn("raw_event_ingress_physically_verified=False",src)
        self.assertNotIn("M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD",src)
        for prohibited in ("program_hw_devices","open_hw_manager",
                           "connect_hw_server","/dev/mem","/dev/uio"):
            self.assertNotIn(prohibited,src)

if __name__=="__main__":
    unittest.main()
