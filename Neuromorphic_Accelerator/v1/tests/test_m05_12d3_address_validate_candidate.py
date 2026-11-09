"""M05.12d.3 offline explicit real-PS six-bank addressing NEGATIVE host tests.

Synthetic fixtures exercise ONLY the independent auditor. Actual assignment,
segment roundtrips and full validation require new owner Vivado 2025.2 logs.
Do not broaden M05.12d.3, modify signed32 RTL or touch the physical board.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d3_address_validate_audit import (
    PLAN_HEADER, MAP_HEADER, MASTER_SPACE, HLS_NATIVE_OFFSETS,
    parse_plan, audit_six_assignments, audit_original_hls_registers,
    audit_validation, SLAVE_INTERFACES,
)
from m05_12d3_hls_connected_preflight import require_new_preflight_output

PLAN = ROOT / "scripts/m05_12d3_control_apertures_candidate.txt"
AUDITOR = ROOT / "scripts/m05_12d3_address_validate_audit.py"
RUNNER = ROOT / "scripts/run_m05_12d3_address_validate_candidate.sh"
TCL = ROOT / "scripts/m05_12d3_address_validate_candidate.tcl"


def good_plan() -> str:
    return PLAN.read_text(encoding="utf-8")


def mapped_fixture(plan_text: str | None = None) -> str:
    plan = parse_plan(plan_text or good_plan())
    rows = [MAP_HEADER, "SPACE|ps/M_AXI_HPM0_FPD|/ps/Data"]
    for bank in SLAVE_INTERFACES:
        intf = SLAVE_INTERFACES[bank]
        leaf = "reg0" if bank in ("shell", "hls") else "Reg"
        aperture = plan.aperture(bank)
        rows.append(
            f"READBACK|{bank}|/{intf}/{leaf}|"
            f"/ps/Data/SEG_{bank}_{leaf}|"
            f"0x{aperture.base:08X}|0x{aperture.length_bytes:08X}"
        )
    rows += ["META|address_assignment|SIX_EXPLICIT_VIVADO_ASSIGNMENTS_READ_BACK",
             "META|physical_board|NOT_AUTHORIZED"]
    return "\n".join(rows) + "\n"


def hls_contract_fixture() -> str:
    rows = ["META|scope|ORIGINAL_SIGNED32_GENERATED_RTL_ATTESTATION_NO_BD"]
    for name, offset in HLS_NATIVE_OFFSETS.items():
        rows.append(f"REG|{name}|0x{offset:02X}")
    return "\n".join(rows) + "\n"


class M0512D3AddressValidateTests(unittest.TestCase):
    def test_explicit_proposed_six_bank_plan_not_default_or_overlap(self):
        plan = parse_plan(good_plan())
        self.assertEqual(len(plan.apertures), 6)
        self.assertEqual([x.base for x in plan.apertures], [
            0xA0000000, 0xA0010000, 0xA0020000,
            0xA0030000, 0xA0040000, 0xA0050000,
        ])
        self.assertEqual(set(x.length_bytes for x in plan.apertures), {0x10000})

    def test_plan_rejects_duplicate_bank_missing_or_reordered(self):
        good = good_plan()
        for bad in (
            good.replace("BANK|hls|", "BANK|shell|"),
            good.replace("BANK|dma_trace|", "BANK|dma_synapses|"),
            good.replace("BANK|dma_trace|0xA0030000|0x10000\n", ""),
            good.replace(PLAN_HEADER, "META|scope|REAL_OS_PHYSICAL_APPROVED"),
            good + "BANK|extra|0xA1000000|0x10000\n",
            good.rstrip("\n"),
        ):
            with self.subTest(bad=bad[:80]):
                with self.assertRaises(ValueError):
                    parse_plan(bad)

    def test_plan_rejects_overlaps_misalignment_bounds_or_nonpowers(self):
        good = good_plan()
        for old, replacement in (
            ("0xA0050000", "0xA0040000"),
            ("0xA0050000", "0xA0041000"),
            ("0xA0050000", "0x00000000"),
            ("0xA0050000", "0x10000000000"),
            ("0x10000\n", "0x3000\n"),
            ("0x10000\n", "0x0000\n"),
            ("0xA0020000", "0xNOTHEX"),
        ):
            with self.subTest(replacement=replacement):
                with self.assertRaises(ValueError):
                    parse_plan(good.replace(old, replacement, 1))

    def test_synthetic_six_actual_readbacks_against_explicit_map(self):
        plan = parse_plan(good_plan())
        status = audit_six_assignments(mapped_fixture(), plan)
        self.assertEqual(status["independent_ps_axi_lite_banks"], 6)
        self.assertEqual(status["master_mappings"], 6)
        self.assertEqual(status["plan_nonoverlap_verified"], 1)
        self.assertEqual(status["physical_board"], 0)

    def test_reject_missing_or_duplicate_master_or_slave_readback(self):
        report = mapped_fixture()
        row = next(x for x in report.splitlines(keepends=True)
                   if x.startswith("READBACK|hls|"))
        first = next(x for x in report.splitlines(keepends=True)
                     if x.startswith("READBACK|dma_neurons|"))
        master = first.rstrip("\n").split("|")[3]
        for bad in (
            report.replace(row, "", 1),
            report.replace(row, row * 2, 1),
            report.replace(row, row.replace("/ps/Data/SEG_hls_reg0", master), 1),
            report.replace(row, row.replace("/hls/s_axi_control/reg0",
                                            "/shell/s_axi/reg0"), 1),
            report.replace(row, row.replace("/ps/Data/", "/ps/DDR/", 1), 1),
        ):
            with self.assertRaises(ValueError):
                audit_six_assignments(bad, parse_plan(good_plan()))

    def test_reject_wrong_vivado_offset_range_or_unassigned(self):
        report = mapped_fixture()
        row = next(x for x in report.splitlines(keepends=True)
                   if x.startswith("READBACK|hls|"))
        for bad in (
            report.replace(row, row.replace("|0xA0050000|", "|0xA0060000|"), 1),
            report.replace(row, row.replace("|0x00010000", "|0x00001000"), 1),
            report.replace(row, row.replace("|0xA0050000|", "||"), 1),
            report.replace(row, row.replace("|0xA0050000|", "|NO_READBACK|"), 1),
            report.replace("SIX_EXPLICIT_VIVADO_ASSIGNMENTS_READ_BACK",
                           "ONLY_DISCOVERED_NO_DECODE"),
            report.replace("META|physical_board|NOT_AUTHORIZED",
                           "META|physical_board|PROGRAMMED"),
        ):
            with self.subTest(bad=bad[-110:]):
                with self.assertRaises(ValueError):
                    audit_six_assignments(bad, parse_plan(good_plan()))

    def test_hls_original_generated_register_map_within_real_sixth_bank(self):
        plan = parse_plan(good_plan())
        audit_original_hls_registers(hls_contract_fixture(), plan)
        for bad in (
            hls_contract_fixture().replace("REG|DECAY_DEN_DATA|0x40", 
                                           "REG|DECAY_DEN_DATA|0x44"),
            hls_contract_fixture().replace("REG|AP_CTRL|0x00\n", ""),
            hls_contract_fixture().replace(
                "ORIGINAL_SIGNED32_GENERATED_RTL_ATTESTATION_NO_BD", "FAKE"),
            hls_contract_fixture().replace("REG|AP_CTRL|0x00\n",
                                           "REG|AP_CTRL|0x00\nREG|AP_CTRL|0x00\n"),
        ):
            with self.assertRaises(ValueError):
                audit_original_hls_registers(bad, plan)

    def test_validation_pass_fail_and_unsupported_status_distinct(self):
        self.assertTrue(audit_validation("VALIDATION|PASS|FULL_BD_VALIDATE_FORCE\n"))
        self.assertFalse(audit_validation("VALIDATION|FAIL|FULL_BD_VALIDATE_FORCE\n"))
        for bad in (
            "VALIDATION|SKIPPED|FULL_BD_VALIDATE_FORCE\n",
            "VALIDATION|PASS|ASSIGN_ADDRESS_ONLY\n",
            "VALIDATION|PASS|FULL_BD_VALIDATE_FORCE\nVALIDATION|FAIL|FULL_BD_VALIDATE_FORCE\n",
            "",
        ):
            with self.assertRaises(ValueError):
                audit_validation(bad)

    def test_cli_preflights_explicit_plan_without_vivado_or_evidence_writes(self):
        before = good_plan()
        cmd = [sys.executable, str(AUDITOR), "--plan", str(PLAN), "--plan-only"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NO VIVADO ADDRESS ASSIGNMENT", result.stdout)
        self.assertEqual(before, good_plan())
        wrong = subprocess.run(cmd + ["--mapped", str(PLAN)],
                               capture_output=True, text=True)
        self.assertNotEqual(wrong.returncode, 0)

    def test_cli_real_audit_synthetic_success_and_validation_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapped = root / "06_real_ps_control_address_readback.txt"
            validate = root / "07_full_bd_validation.txt"
            contract = root / "01_original_hls_contract.txt"
            mapped.write_text(mapped_fixture())
            validate.write_text("VALIDATION|PASS|FULL_BD_VALIDATE_FORCE\n")
            contract.write_text(hls_contract_fixture())
            cmd = [sys.executable, str(AUDITOR), "--plan", str(PLAN),
                   "--mapped", str(mapped), "--validation", str(validate),
                   "--hls-original-contract", str(contract)]
            success = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertIn("six ORIGINAL actual Vivado PS AXI-Lite", success.stdout)
            validate.write_text("VALIDATION|FAIL|FULL_BD_VALIDATE_FORCE\n")
            fail = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(fail.returncode, 1)
            self.assertIn("six ORIGINAL actual Vivado PS AXI-Lite", fail.stdout)
            self.assertIn("full Vivado validate_bd_design -force failed", fail.stderr)

    def test_runner_provenance_no_physical_hardware_and_no_auto_address(self):
        script = RUNNER.read_text()
        tcl = TCL.read_text()
        for required in (
            "assign_bd_address -target_address_space $control_space",
            "-offset $base_text -range $length_text $slave",
            "get_bd_addr_segs -addressing -quiet -of_objects $slave",
            "get_bd_addr_segs -quiet -of_objects $master",
            "get_property OFFSET $master", "get_property RANGE $master",
            "validate_bd_design -force",
            "FULL_BD_VALIDATE_FORCE", "SIX_EXPLICIT_VIVADO_ASSIGNMENTS_READ_BACK",
        ):
            self.assertIn(required, tcl)
        for required in (
            "source_sha256.txt", "01_hls_preflight.log", "00_offline_plan_admission.log",
            "02_native_axis_graph.txt", "05_read_only_address_inventory.txt",
            "06_real_ps_control_address_readback.txt", "07_full_bd_validation.txt",
            "04_independent_original_graph_audit.log",
            "08_independent_address_validation_audit.log", "vivado_rc=",
            "graph_rc=", "addr_rc=", "source_explicit_control_plan.txt",
        ):
            self.assertIn(required, script)
        for forbidden in (
            "program_hw_devices", "open_hw_target", "connect_hw_server",
            "write_bitstream", "launch_runs", "xsdb", "rm -rf",
        ):
            self.assertNotIn(forbidden, script + tcl)
        self.assertEqual(subprocess.run(["bash", "-n", str(RUNNER)],
                         capture_output=True).returncode, 0)

    def test_owner_2025_2_assign_printed_but_empty_return_must_use_real_readback(self):
        # Owner source e.g. "Slave segment '/dma_neurons/S_AXI_LITE/Reg'
        # is being assigned ..." followed by previous Tcl false-negative
        # from '[llength $created] != 1'. The message alone is NOT proof
        # of successful decoding. Require actual mapped objects/values.
        tcl = TCL.read_text()
        self.assertIn(
            "set created [assign_bd_address -target_address_space $control_space",
            tcl)
        self.assertNotIn("if {[llength $created] != 1}", tcl)
        self.assertIn(
            "set masters [get_bd_addr_segs -addressing -quiet -of_objects $slave]",
            tcl)
        self.assertIn(
            "set ps_mappings [get_bd_addr_segs -quiet -of_objects $control_space]",
            tcl)
        self.assertIn(
            "[lsearch -exact $ps_mappings $master] < 0", tcl)
        self.assertIn(
            "set reverse [get_bd_addr_segs -quiet -of_objects $master]", tcl)
        self.assertIn(
            "if {[llength $masters] != 1}", tcl)
        self.assertIn(
            "if {[llength $created] != 0 && [lsearch -exact $created $master] < 0}",
            tcl)
        self.assertIn(
            'puts $af "READBACK|$bank|$slave|$master|$rb_base|$rb_range"',
            tcl)
        self.assertNotIn(
            'puts $af "READBACK|$bank|$slave|$master|[format {0x%08X} $wanted_base]',
            tcl)
        self.assertLess(
            tcl.index("set rb_base [string trim [get_property OFFSET $master]]"),
            tcl.index('puts $af "READBACK|$bank|$slave|$master|$rb_base|$rb_range"'))
        self.assertLess(
            tcl.index('get_bd_addr_segs -addressing -quiet -of_objects $slave'),
            tcl.index('assign_bd_address -target_address_space $control_space'))
        self.assertIn("if {[llength $mapped_before] != 0}", tcl)

    def test_owner_second_failure_requires_real_ps_master_space_not_filtered_addressed(self):
        # Owner Vivado 2025.2 produced ONE -addressing master for the
        # original dma_neurons slave, but '-addressed -of_objects /ps/Data'
        # did not report that same master object. UG912 BD_ADDR_SEG
        # documents the plain space->master segment relation. This
        # guards against accidentally reintroducing filtered -addressed.
        tcl = TCL.read_text()
        self.assertNotIn(
            "get_bd_addr_segs -addressed -quiet -of_objects $control_space",
            tcl)
        self.assertIn(
            "set masters [get_bd_addr_segs -addressing -quiet -of_objects $slave]",
            tcl)
        self.assertIn(
            "set ps_mappings [get_bd_addr_segs -quiet -of_objects $control_space]",
            tcl)
        self.assertIn(
            "if {[llength $ps_mappings] == 0 ||", tcl)
        self.assertIn(
            "[lsearch -exact $ps_mappings $master] < 0", tcl)
        self.assertIn(
            'puts "ADDR_D3_SPACE_QUERY|$bank|PS_SPACE=$control_space|', tcl)
        self.assertIn(
            'puts "ADDR_D3_REVERSE_QUERY|$bank|PS_MASTER=$master|', tcl)
        self.assertIn(
            'puts "ADDR_D3_PROP_QUERY|$bank|PS_MASTER=$master|', tcl)
        self.assertLess(
            tcl.index("set ps_mappings [get_bd_addr_segs -quiet -of_objects $control_space]"),
            tcl.index("set reverse [get_bd_addr_segs -quiet -of_objects $master]"))
        self.assertLess(
            tcl.index("set reverse [get_bd_addr_segs -quiet -of_objects $master]"),
            tcl.index("set rb_base [string trim [get_property OFFSET $master]]"))

    def test_owner_bd_41_758_unused_lpd_port_is_disabled_not_fake_clocked(self):
        # Genuine original owner run 20261109T052908Z_QSqea3: six authentic
        # mapped control banks + independent audit PASS, but whole BD FAIL
        # due to an enabled, unconnected LPD AXI master clock.
        # This tests only the *source guard*. A new genuine owner Vivado run
        # must still demonstrate the actual IP port disappearance/BD result.
        tcl = TCL.read_text()
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP2 1", tcl)
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP2 0", tcl)
        self.assertIn("get_bd_intf_pins -quiet ps/M_AXI_HPM0_LPD", tcl)
        self.assertIn("get_bd_pins -quiet ps/maxihpm0_lpd_aclk", tcl)
        self.assertIn("M05_D3_UNUSED_LPD_DISABLED|", tcl)
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP0 1", tcl)
        self.assertIn("CONFIG.PSU__USE__S_AXI_GP2 1", tcl)
        self.assertIn("M_AXI_HPM0_FPD MASTER S_AXI_HP0_FPD SLAVE", tcl)
        self.assertNotIn('lappend clocks "ps/maxihpm0_lpd_aclk"', tcl)
        self.assertLess(
            tcl.index("CONFIG.PSU__USE__M_AXI_GP2 0"),
            tcl.index("get_bd_intf_pins -quiet ps/M_AXI_HPM0_LPD"))
        self.assertLess(
            tcl.index("get_bd_pins -quiet ps/maxihpm0_lpd_aclk"),
            tcl.index("validate_bd_design -force"))
        self.assertIn("if {$vrc} {", tcl)
        self.assertIn('puts $vf "VALIDATION|FAIL|FULL_BD_VALIDATE_FORCE"', tcl)

    def test_unverified_requested_offset_does_not_count_as_vivado_readback(self):
        good = mapped_fixture()
        plan = parse_plan(good_plan())
        # The auditor must refuse fabricated output values that disagree with
        # user-supplied plan, regardless of whether the Tcl assignment returned.
        self.assertEqual(audit_six_assignments(good, plan)["master_mappings"], 6)
        for old, replacement in (
            ("|0xA0000000|", "|0xA0001000|"),
            ("|0x00010000\n", "|0x00002000\n"),
            ("/ps/Data/SEG_dma_neurons_Reg", "/ps/DDR/SEG_dma_neurons_Reg"),
        ):
            with self.subTest(mutation=replacement):
                with self.assertRaises(ValueError):
                    audit_six_assignments(good.replace(old, replacement, 1), plan)

    def test_preflight_accepts_new_same_milestone_folder_only_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accepted = root / "neuromorphic_v1_m05_12d3_addr_validate_new"
            accepted.mkdir()
            target = accepted / "01_hls_preflight.txt"
            require_new_preflight_output(target)
            target.write_text("evidence must not be overwritten")
            with self.assertRaises(ValueError):
                require_new_preflight_output(target)
            self.assertEqual(target.read_text(), "evidence must not be overwritten")
            with self.assertRaises(ValueError):
                require_new_preflight_output(root / "01_hls_preflight.txt")

    def test_accepted_native_axis_and_signed32_sources_preserved(self):
        original = (ROOT / "scripts/m05_12d3_native_axis_candidate.tcl").read_text()
        next_source = TCL.read_text()
        for link in (
            "shell/hls_neuron hls/neurons",
            "shell/hls_synapse hls/synapses",
            "shell/hls_external hls/external_events",
            "hls/trace shell/hls_trace",
            "ctrl_sc/M05_AXI",  # present in graph readback in original auditor
            "reset_inv/Res",
        ):
            if link == "ctrl_sc/M05_AXI":
                self.assertIn("5 hls/s_axi_control", original)
                self.assertIn("5 hls/s_axi_control", next_source)
            else:
                self.assertIn(link, original)
                self.assertIn(link, next_source)
        for path in (
            "hls/m05_rolling/m05_rolling.cpp",
            "rtl/m05_11/m05_11_stream_shell.v",
            "rtl/m05_12/m05_12d_axis_shell_ref.v",
            "scripts/m05_12d3_native_axis_candidate.tcl",
        ):
            with self.subTest(path=path):
                p = ROOT / path
                before = hashlib.sha256(p.read_bytes()).hexdigest()
                parse_plan(good_plan())
                self.assertEqual(before, hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
