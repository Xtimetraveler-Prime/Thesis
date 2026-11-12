"""M08 D2 PC-only PS/HPM0/PL0/AFI ownership contract regression tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/m08_d2_offline_ps_pl_contract_audit.py"
spec = importlib.util.spec_from_file_location("m08_d2_ps_pl_contract_audit", PATH)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class M08D2PSPLStaticContractTests(unittest.TestCase):
    def test_actual_original_sources_show_a_configuration_ownership_gap(self):
        result = audit.audit()
        self.assertEqual(result["original_bd_source"]["hpm_interface"], "M_AXI_HPM0_FPD")
        self.assertEqual(result["original_bd_source"]["master_width_bits_configured_in_vivado"], 128)
        self.assertIn("NOT_PLL_LOCK", result["original_bd_source"]["dcm_locked_source"])
        self.assertEqual(result["m08_deployed_overlay_source"]["ps_pl_clock_and_afi_ownership"],
                         "NOT_DECLARED_IN_THIS_OVERLAY")
        self.assertFalse(any(result["m08_deployed_overlay_source"]["features"].values()))
        self.assertFalse(result["m08_deployed_overlay_source"]["absence_proves_clock_stopped"])
        self.assertFalse(result["m08_deployed_overlay_source"]["absence_proves_afi_wrong"])
        self.assertEqual(result["offline_comparators"]["stock"]["status"], "NOT_SUPPLIED")
        self.assertFalse(result["physical"]["hardware_retest_authorized"])
        self.assertTrue(result["physical"]["original_m08_mmio_quarantined"])

    def test_offline_dts_comparison_counts_properties_but_not_live_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stock = root / "stock_original_saved.dts"
            m08 = root / "m08_original_saved.dts"
            stock.write_text(
                "/dts-v1/; / { node { assigned-clocks = <0x1>; "
                "assigned-clock-rates = <0x5f5e100>; "
                'compatible = "xlnx,afi-fpga"; config-afi = <0 0>; '
                "clock-names = \"s_axi_aclk\"; clocks = <0x1>; }; };"
                "\n" * 8)
            m08.write_text("/dts-v1/; / { fragment@0 { firmware-name = \"m08\"; "
                           "reg = <0x0 0xa0000000 0x0 0x1000>; }; };\n" * 3)
            result = audit.audit(stock_dts=stock, deployed_dts=m08)
            features = result["offline_comparators"]["stock"]["features"]
            self.assertTrue(features["assigned_clocks"])
            self.assertTrue(features["assigned_clock_rates"])
            self.assertTrue(features["afi_fabric_config_node"])
            self.assertTrue(features["afi_programming_properties"])
            self.assertEqual(result["offline_comparators"]["original_deployed_m08"]
                             ["status"], "OFFLINE_DTS_BYTES_READ_NOT_LIVE_PROOF")
            self.assertFalse(result["offline_comparators"]["stock"]["runtime_proof"])
            self.assertFalse(result["physical"]["hardware_retest_authorized"])

    def test_untrusted_symlink_comparator_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            a = p / "input.dts"
            a.write_text("original stock source " * 20)
            link = p / "symlink.dts"
            link.symlink_to(a)
            with self.assertRaisesRegex(audit.ContractRejected, "symlinked"):
                audit.audit(stock_dts=link)

    def test_broken_bd_clock_contract_is_not_accepted_as_current_original(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in audit.SOURCE_PATHS:
                target = p / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            bd = p / audit.BD
            bd.write_text(bd.read_text().replace(
                "CONFIG.PSU__FPGA_PL0_ENABLE 1", "CONFIG.PSU__FPGA_PL0_ENABLE 0"))
            with self.assertRaisesRegex(audit.ContractRejected, "FPGA_PL0_ENABLE"):
                audit.audit(root=p)

    def test_m08_overlay_clock_property_change_requires_new_review(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in audit.SOURCE_PATHS:
                target = p / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            source = p / audit.UIO
            source.write_text(source.read_text().replace(
                'status = "okay";', 'assigned-clock-rates = <100000000>;\n        status = "okay";', 1))
            with self.assertRaisesRegex(audit.ContractRejected, "fresh review"):
                audit.audit(root=p)

    def test_static_dts_ast_never_executes_python_code(self):
        with self.assertRaisesRegex(audit.ContractRejected, "static"):
            audit.extract_literal_dts("DTS = __import__('os').system('false')\n")
        with self.assertRaisesRegex(audit.ContractRejected, "exactly one"):
            audit.extract_literal_dts("DTS = '/dts-v1/;'\nDTS = '/plugin/;'\n")

    def test_source_audit_contains_no_device_or_ssh_access(self):
        src = PATH.read_text()
        for forbidden in ("subprocess.run", "os.system", "mmap.mmap", "/dev/mem",
                          "/dev/uio", "xmutil ", "ssh ", "write_bitstream",
                          "open_checkpoint", "write_text(", "program_hw_devices"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
