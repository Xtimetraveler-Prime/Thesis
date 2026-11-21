"""Offline quarantined KV260 PS/PL HPM0/HP0 source preflight & mock CI.

This tests source properties and a FAKE Vivado executable only.
No actual Vivado, synthesis, place-and-route, bitstream, kernel, DT,
SSH, or hardware board is exercised. No fabricated physical PASS marker.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_m085_pspl_quarantine_source_check as check


class M085PSPLQuarantine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tcl=check.TCL.read_text(encoding="utf-8")
        cls.rtl=check.RTL.read_text(encoding="utf-8")
        cls.runner=check.RUN.read_text(encoding="utf-8")

    def test_original_source_pins_are_explicit_and_all_trust_is_hard_low(self):
        record=check.audit(self.tcl,self.rtl,self.runner)
        self.assertEqual(record["status"],
                         "SOURCE_TOPOLOGY_GUARDS_PASS_NATIVE_BD_NOT_YET_VERIFIED")
        self.assertFalse(record["new_k26_bitstream_or_board_authorized"])
        self.assertFalse(record["owner_kernel_dma_allocation_verified"])
        self.assertFalse(record["synthesis_route_timing_verified"])
        self.assertEqual(len(record["quarantine_trust_pins_held_low"]),4)
        self.assertEqual(len(record["sha256"]),3)

    def test_direct_source_only_cli_passes_no_board(self):
        p=subprocess.run([sys.executable,str(check.ROOT/"scripts/m08_m085_pspl_quarantine_source_check.py"),
                          "--source-only"],capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn("NATIVE_BD_NOT_YET_VERIFIED",p.stdout)
        self.assertNotIn("DMA_READY_TRUE",p.stdout)

    def test_missing_required_source_or_interface_is_blocked(self):
        for removed in (
            "m08_m085_axi_neural_shell.v",
            "m08_m085_axil_managed_neural_candidate.v",
            "connect_bd_intf_net $hpm0 [exactly_one_intf control_sc/S00_AXI]",
            "connect_bd_intf_net [exactly_one_intf hp0_sc/M00_AXI] $hp0",
            "ps/saxihp0_fpd_aclk",
            "ps/maxihpm0_fpd_aclk",
            "validate_bd_design -force",
            "set_property PACKAGE_PIN A12",
            "get_bd_addr_segs -quiet ps/SAXIGP2/HP0_DDR_LOW",
        ):
            with self.subTest(removed=removed),self.assertRaises(check.UnsafeTopology):
                check.audit(self.tcl.replace(removed,""),self.rtl,self.runner)

    def test_wrong_k26_part_clock_ps_port_width_and_map_are_blocked(self):
        for old,new in (
            ("xck26-sfvc784-2LV-c","xczu7ev-ffvc1156-2-e"),
            ("CONFIG.PSU__MAXIGP0__DATA_WIDTH {128}",
             "CONFIG.PSU__MAXIGP0__DATA_WIDTH {32}"),
            ("CONFIG.PSU__SAXIGP2__DATA_WIDTH {128}",
             "CONFIG.PSU__SAXIGP2__DATA_WIDTH {64}"),
            ("CONFIG.PSU__USE__M_AXI_GP0 {1}",
             "CONFIG.PSU__USE__M_AXI_GP0 {0}"),
            ("CONFIG.PSU__USE__M_AXI_GP1 {0}",
             "CONFIG.PSU__USE__M_AXI_GP1 {1}"),
            ("CONFIG.PSU__USE__FABRIC__RST {0}",
             "CONFIG.PSU__USE__FABRIC__RST {1}"),
            ("CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}",
             "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {200}"),
            ("-offset 0xA4000000 -range 0x00001000",
             "-offset 0x40000000 -range 0x00001000"),
            ("-offset 0x00000000 -range 0x80000000",
             "-offset 0x40000000 -range 0x40000000"),
        ):
            with self.subTest(old=old),self.assertRaises(check.UnsafeTopology):
                check.audit(self.tcl.replace(old,new),self.rtl,self.runner)

    def test_any_high_or_missing_trust_draining_ack_is_blocked(self):
        for old,new in (
            ("CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {0}",
             "CONFIG.CONST_WIDTH {1} CONFIG.CONST_VAL {1}"),
            ("accel/interconnect_drain_ack","accel/unused_input"),
            ("accel/driver_bound_verified","accel/owner_is_valid"),
            ("connect_bd_net $deny_pin [exactly_one_pin $p]",
             "connect_bd_net [exactly_one_pin accel/drain_request] [exactly_one_pin $p]"),
        ):
            with self.subTest(old=old),self.assertRaises(check.UnsafeTopology):
                check.audit(self.tcl.replace(old,new),self.rtl,self.runner)

    def test_hardware_or_bitgen_commands_cannot_enter_this_offline_builder(self):
        for cmd in ("open_hw_manager","program_hw_devices","launch_runs synth_1",
                    "write_bitstream -file out.bit","connect_hw_server",
                    "write_hw_platform -fixed", "ssh ubuntu@10.42.0.135"):
            with self.subTest(cmd=cmd),self.assertRaises(check.UnsafeTopology):
                check.audit(self.tcl+"\n"+cmd+"\n",self.rtl,self.runner)

    def test_axi_ip_interface_metadata_is_complete_and_not_legacy_32bit(self):
        for old,new in (
            ("ASSOCIATED_BUSIF S_AXI:M_AXI","ASSOCIATED_BUSIF S_AXI"),
            ("PROTOCOL AXI4LITE, DATA_WIDTH 32","PROTOCOL AXI4LITE, DATA_WIDTH 128"),
            ("PROTOCOL AXI4, DATA_WIDTH 128","PROTOCOL AXI4, DATA_WIDTH 32"),
            ("X_INTERFACE_INFO = \"xilinx.com:interface:aximm:1.0 M_AXI RDATA\"",
             "X_INTERFACE_INFO = \"xilinx.com:interface:aximm:1.0 M_AXI BOGUS\""),
        ):
            with self.subTest(old=old),self.assertRaises(check.UnsafeTopology):
                check.audit(self.tcl,self.rtl.replace(old,new),self.runner)

    def test_runner_refuses_unsafe_shell_and_wrong_tool_version(self):
        for old,new in (
            ("mktemp -d","mkdir -p"),
            ("99_evidence_sha256.txt","99_fake.txt"),
            ("vivado -mode batch -source","ssh -T ubuntu@10.42.0.135"),
            ("bitstream_candidate","known_good_bitstream"),
        ):
            with self.subTest(old=old),self.assertRaises(check.UnsafeTopology):
                check.audit(self.tcl,self.rtl,self.runner.replace(old,new))
        self.assertNotIn("StrictHostKeyChecking=no",self.runner)

    @unittest.skipUnless(shutil.which("tclsh"),"Tcl parser needed for syntax-only check")
    def test_actual_tcl_parser_reports_balanced_script_without_running_vivado(self):
        script="""set f [open $::env(M085_TCL_SOURCE) r]
set body [read $f]
close $f
if {![info complete $body]} {
    puts stderr "UNBALANCED_M085_TCL"
    exit 3
}
puts "M085_TCL_SYNTAX_COMPLETE_NOT_NATIVE_VIVADO"
"""
        env=os.environ.copy()
        env["M085_TCL_SOURCE"]=str(check.TCL)
        p=subprocess.run(["tclsh"],input=script,env=env,
                         capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("M085_TCL_SYNTAX_COMPLETE",p.stdout)

    def _mock_offline_runner(self,version: str):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"Thesis_Evidence/M08").mkdir(parents=True)
            bindir=root/"bin"
            bindir.mkdir()
            fake=bindir/"vivado"
            fake.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"-version\" ]; then "
                f"echo 'Vivado v{version}'; exit 0; fi\n"
                "echo 'M08_M085_QUARANTINED_PSPL_BD_COMPLETE_NO_DMA_NO_BITSTREAM'\n"
                "exit 0\n"
            )
            fake.chmod(0o755)
            env=os.environ.copy()
            env["HOME"]=str(root)
            env["PATH"]=str(bindir)+os.pathsep+env.get("PATH","")
            p=subprocess.run(["bash",str(check.RUN)],env=env,
                             capture_output=True,text=True,timeout=20)
            dirs=list((root/"Thesis_Evidence/M08").glob("m08_m085_pspl_bd_*"))
            if version=="2025.1":
                self.assertEqual(dirs,[])
                return p
            self.assertEqual(len(dirs),1,p.stdout+p.stderr)
            out=dirs[0]
            hashes=subprocess.run(
                ["sha256sum","-c","99_evidence_sha256.txt"],
                cwd=out,capture_output=True,text=True,timeout=15
            )
            self.assertEqual(hashes.returncode,0,hashes.stdout+hashes.stderr)
            self.assertIn("vivado_exit_status=0",(out/"02_vivado_exit_status.txt").read_text())
            self.assertIn("QUARANTINED_PSPL_BD_ONLY_NO_DMA",
                          (out/"06_context.txt").read_text())
            self.assertTrue((out/"03_builder_source.tcl").is_file())
            self.assertFalse((out/"reports/20_quarantined_bd_observation.txt").exists())
            return p

    def test_mock_vivado_forged_success_cannot_claim_bd_pass(self):
        p=self._mock_offline_runner("2025.2")
        self.assertEqual(p.returncode,3,p.stdout+p.stderr)
        self.assertIn("INCOMPLETE_OR_REJECTED_NO_PHYSICAL_RELEASE",p.stderr)
        self.assertNotIn("TOPOLOGY_ONLY_PASS_NOT_DMA_READY",p.stdout)

    def test_wrong_vivado_version_refused_before_evidence_creation(self):
        p=self._mock_offline_runner("2025.1")
        self.assertEqual(p.returncode,2,p.stdout+p.stderr)
        self.assertIn("refusing non-Vivado-2025.2",p.stderr)


if __name__=="__main__":
    unittest.main()
