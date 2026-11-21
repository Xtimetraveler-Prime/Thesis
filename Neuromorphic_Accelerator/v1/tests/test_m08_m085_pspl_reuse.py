"""M08.5 real Icarus 256B page admission and Digital Twin v3 source evidence.

NO board, OS DMA, XSA bitgen, physical DDR or owner original receipt reads.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from neuromorphic_accelerator_v1.m08_m085_pspl_lineage import (
    PRIOR, LineageError, audit_sources,
)
import m08_m085_twin_pspl_audit as source_audit

RTL = ROOT / "rtl/m08/m08_m085_ddr_page_admission.v"
TB = ROOT / "rtl/m08/tb_m08_m085_ddr_page_admission.sv"
AXI_ENGINE = ROOT / "rtl/m08/m08_m085_axi128_page_engine.v"
AXI_COMPOSITION = ROOT / "rtl/m08/m08_m085_axi128_page_candidate.v"
AXI_TB = ROOT / "rtl/m08/tb_m08_m085_axi128_page_candidate.sv"


class TwinPSPLReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = {p: (REPO / p).read_text(encoding="utf-8") for p in PRIOR}

    def test_exact_first_party_prior_ddr_and_current_m08_topologies(self):
        data = audit_sources(self.original)
        self.assertEqual(data, source_audit.collect())
        self.assertEqual(data["status"], "SOURCE_LINEAGE_PASS_M08_DDR_NOT_CONNECTED_OR_OWNED")
        self.assertEqual(len(data["source_sha256"]), 8)
        self.assertTrue(data["v3_p02_physically_accepted_ddr_paging_historical"])
        self.assertEqual(data["v3_p02_transport"],
                         "PL_AXI128_MASTER_SMARTCONNECT_PS_S_AXI_HP0_FPD")
        self.assertEqual(data["v3_p03_control"],
                         "PS_M_AXI_HPM0_FPD_SMARTCONNECT_PL_AXIL")
        self.assertFalse(data["v3_512k_context_format_reusable_for_m08"])
        self.assertFalse(data["v3_0x40000000_window_reusable_for_m08"])
        self.assertFalse(data["m08_ps_pl_hp0_axi_path_connected"])
        self.assertFalse(data["m08_kernel_dma_buffer_owned"])
        self.assertFalse(data["owner_real_ddr_ready"])
        self.assertIsNone(data["physical_ddr_transactions_measured_for_m08"])
        self.assertFalse(data["new_bitstream_or_board_action_authorized"])

    def test_mutated_interface_path_and_boot_safety_fail_closed(self):
        changes = (
            (PRIOR[0], "CONFIG.PSU__SAXIGP2__DATA_WIDTH {128}",
                       "CONFIG.PSU__SAXIGP2__DATA_WIDTH {32}"),
            (PRIOR[0], "p02_axi128_burst_adapter_0/M_AXI",
                       "missing_axi_port"),
            (PRIOR[1], "p03_hpm0_width_smartconnect_0",
                       "protocol_converter_without_width"),
            (PRIOR[2], "(request_end <= allowed_end)", "(request_end >= allowed_end)"),
            (PRIOR[3], "NUM_READ_OUTSTANDING 1", "NUM_READ_OUTSTANDING 8"),
            (PRIOR[4], "K26 DDR, not PC RAM", "PC-only model"),
            (PRIOR[5], "dw_ss0_sel[9:8] = 2", "selector unknown"),
            (PRIOR[6], "all_DDR_port_and_master_permissions_proven=false",
                       "all_DDR_port_and_master_permissions_proven=true"),
            (PRIOR[7], "CONFIG.PSU__USE__M_AXI_GP0 0",
                       "CONFIG.PSU__USE__M_AXI_GP0 1"),
            (PRIOR[7], "kernel_owned_dma_buffer=NO", "kernel_owned_dma_buffer=YES"),
        )
        for path, original, forged in changes:
            with self.subTest(path=path,original=original):
                changed = dict(self.original)
                self.assertIn(original, changed[path])
                changed[path] = changed[path].replace(original, forged)
                with self.assertRaises(LineageError):
                    audit_sources(changed)
        for changed in ({}, {**self.original, "extra": "hello"}):
            with self.assertRaises(LineageError):
                audit_sources(changed)

    def test_cli_readonly_and_rtl_unconnected_identity(self):
        r = subprocess.run(
            [sys.executable, str(ROOT/"scripts/m08_m085_twin_pspl_audit.py"),
             "--source-only"], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["m08_ps_pl_hp0_axi_path_connected"], False)
        src = RTL.read_text(encoding="utf-8")
        self.assertIn("WINDOW_BEGIN = 64'd0", src)
        self.assertIn("WINDOW_END   = 64'd0", src)
        self.assertIn("req_size_bytes == 16'd256", src)
        self.assertIn("owner_lease_active", src)
        self.assertIn("MAX_WAIT_CYCLES", src)
        for forbidden in ("program_hw_devices", "mrd ", "mwr ",
                          "0x40000000", "axi_dma", "dma_alloc_coherent"):
            self.assertNotIn(forbidden, src)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "genuine Icarus only; no synthetic Verilog substitute")
    def test_real_iverilog_guard_positive_and_eighteen_adversarial_paths(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td)/"guard.vvp"
            built = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m08_m085_ddr_page_admission",
                 "-o", str(exe), str(RTL), str(TB)],
                capture_output=True, text=True
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            for case in range(19):
                with self.subTest(case=case):
                    r = subprocess.run(["vvp", str(exe), f"+CASE={case}"],
                                       capture_output=True, text=True, timeout=10)
                    self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
                    marker = ("M08_5_REAL_IVERILOG_256B_GUARD_TWO_TRANSFERS_PASS"
                              if case == 0 else
                              f"M08_5_REAL_IVERILOG_GUARD_NEGATIVE_PASS case={case}")
                    self.assertIn(marker, r.stdout)
                    self.assertNotIn("FATAL", r.stdout+r.stderr)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "real AXI4 handshake test requires genuine iverilog/vvp")
    def test_real_axi128_page_read_write_and_twenty_three_faults(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td)/"axi_page.vvp"
            built = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m08_m085_axi128_page_candidate",
                 "-o", str(exe), str(RTL), str(AXI_ENGINE),
                 str(AXI_COMPOSITION), str(AXI_TB)],
                capture_output=True, text=True
            )
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            for case in range(24):
                with self.subTest(case=case):
                    r = subprocess.run(
                        ["vvp", str(exe), f"+CASE={case}"],
                        capture_output=True, text=True, timeout=10
                    )
                    self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
                    marker = ("M08_5_REAL_AXI128_256B_READ_WRITE_AND_512_BYTES_PASS"
                              if case == 0 else
                              f"M08_5_REAL_AXI128_256B_NEGATIVE_PASS case={case}")
                    self.assertIn(marker, r.stdout)
                    self.assertNotIn("FATAL", r.stdout+r.stderr)

    def test_new_axi_module_defaults_are_not_a_real_ddr_release(self):
        eng = AXI_ENGINE.read_text(encoding="utf-8")
        top = AXI_COMPOSITION.read_text(encoding="utf-8")
        self.assertIn("module m08_m085_axi128_page_engine", eng)
        self.assertIn("m_axi_awlen=8'd15", eng)
        self.assertIn("m_axi_arlen=8'd15", eng)
        self.assertIn("m_axi_wstrb=16'hFFFF", eng)
        self.assertIn("m_axi_bresp!=2'b00", eng)
        self.assertIn("m_axi_rresp!=2'b00", eng)
        self.assertIn("m_axi_rlast!=(beat==4'd15)", eng)
        self.assertIn("m08_m085_ddr_page_admission", top)
        self.assertIn("m08_m085_axi128_page_engine", top)
        self.assertIn("WINDOW_BEGIN=64'd0", top)
        self.assertIn("WINDOW_END=64'd0", top)
        self.assertIn(".downstream_done(engine_done)", top)
        self.assertIn(".downstream_error(engine_error || engine_poisoned)", top)
        self.assertIn(".downstream_rvalid(engine_read_complete)", top)
        self.assertIn("staged_write_page<=req_write_page", top)
        for bad in ("program_hw_devices", "mrd ", "mwr ", "0x40000000",
                    "dma_alloc_coherent", "create_bd_design"):
            self.assertNotIn(bad, eng+top)

    def test_static_source_never_claims_simulated_guard_is_real_ddr(self):
        raw = (ROOT/"src/neuromorphic_accelerator_v1/m08_m085_pspl_lineage.py").read_text()
        self.assertIn("owner_real_ddr_ready", raw)
        self.assertIn('"owner_real_ddr_ready": False', raw)
        self.assertIn('"new_bitstream_or_board_action_authorized": False', raw)


if __name__=="__main__":
    unittest.main()
