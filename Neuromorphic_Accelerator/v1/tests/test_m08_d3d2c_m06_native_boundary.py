"""D3.D.2C owner native build source/immutable evidence gates, NO BOARD."""
from __future__ import annotations
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_native_review as gate

class M0632NativeBoundaryTests(unittest.TestCase):
    def test_new_builder_is_vendor_offline_only_and_separate(self):
        t=(ROOT/"scripts/m08_d3d2c_m06_build.tcl").read_text()
        active="\n".join(x for x in t.splitlines()
                         if x.strip() and not x.lstrip().startswith("#"))
        for key in (
            "m08_d3d2c_m06_32_lif_axil",
            "m08_d3d2c_m06_lif_jtag_UNRELEASED.bit",
            "m08_d3d2c_m06_lif_jtag_wrapper",
            "THIRTY_TWO_NEURON_M06_RECURRENT_3_4_SIGNED16",
            "external_event_coalescing=HOST_PC_ONLY",
            "CONFIG.NUM_SI 1 CONFIG.NUM_MI 2",
            "CONFIG.PSU__USE__M_AXI_GP0 0",
            "CONFIG.PSU__USE__M_AXI_GP1 0",
            "CONFIG.PSU__USE__M_AXI_GP2 0",
            "CONFIG.PSU__TTC0__WAVEOUT__IO EMIO",
            "m08_d3c_fabric_por fabric_por",
            "0xA0000000", "0xA0001000",
            "validate_bd_design -force",
            "report_drc -file", "report_timing_summary -file",
            "write_bitstream -file $bit",
        ):
            self.assertIn(key,active,key)
        for forbidden in ("open_hw_manager","connect_hw_server",
                          "program_hw_devices","run_hw_axi",
                          "xmutil ","sudo ","ssh ","/dev/mem","/dev/uio"):
            self.assertNotIn(forbidden,active)

    def test_owner_pc_shell_and_first_image_stops_on_unreviewed_drc(self):
        script=ROOT/"scripts/run_m08_d3d2c_m06_pc.sh"
        syntax=subprocess.run(["bash","-n",str(script)],
                              capture_output=True,text=True,timeout=10)
        self.assertEqual(syntax.returncode,0,syntax.stderr)
        s=script.read_text()
        self.assertIn("mktemp -d",s)
        self.assertIn("sha256sum -c",s)
        self.assertIn("m08_d3d2c_m06_native_review.py",s)
        self.assertNotIn("M08_D3D2B_ALLOW_PROGRAM",s)
        self.assertNotIn("program_hw_devices",s)
        self.assertNotIn("run_hw_axi",s)
        self.assertIn("M08_D3D2C_NO_BOARD_NO_JTAG_NO_IMAGE_RELEASE",s)

    def test_missing_or_forged_owner_evidence_never_authorizes_bitstream(self):
        with tempfile.TemporaryDirectory() as temp:
            fake=Path(temp)/"m08_d3d2c_m06_synthetic"
            fake.mkdir()
            with self.assertRaises(gate.Reject):
                gate.inspect(fake)
        src=(ROOT/"scripts/m08_d3d2c_m06_native_review.py").read_text()
        self.assertIn("M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD",src)
        self.assertIn("OWNER_ORIGINAL_BIT_SHA",src)
        self.assertIn("OWNER_ORIGINAL_DRC_SHA",src)
        self.assertIn("return 0  # read-only native acceptance",src)
        self.assertIn('"physical_programming_authorized":False',src)
        self.assertIn('"physical_32_neuron_m02_parity_verified":False',src)
        self.assertNotIn("program_hw_devices",src)
        self.assertNotIn("open_hw_manager",src)

if __name__=="__main__":
    unittest.main()
