"""PC-only D2 negative tests; NEVER connects to a KV260, MMIO, or Vivado.

Validates the original-fan SHA gate, immutable evidence receipt, source
quarantine, and mocked vendor report contracts. Mocked Tcl does NOT prove
genuine native Vivado reports exist.
"""
from __future__ import annotations

import importlib.util
from hashlib import sha256
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d2_run_fan_dcp_readonly_forensics.py"
TCL = ROOT / "scripts/m08_d2_fan_dcp_readonly_forensics.tcl"
spec = importlib.util.spec_from_file_location("m08_d2_dcp", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class M08D2OriginalFanDCPForensics(unittest.TestCase):
    def test_native_tcl_has_only_readonly_reports_no_board_or_bitstream(self):
        script = TCL.read_text()
        active = "\n".join(line for line in script.splitlines()
                           if line.strip() and not line.lstrip().startswith("#"))
        self.assertIn("open_checkpoint $dcp", active)
        self.assertIn("report_drc -file", active)
        self.assertIn("report_methodology -file", active)
        self.assertIn("report_clock_interaction -file", active)
        self.assertIn("report_cdc -file", active)
        self.assertIn("get_nets -hier -quiet", active)
        self.assertIn("mi_handler_m_sc_areset_pipe", active)
        self.assertIn("M08_D2_NATIVE_FAN_DCP_READONLY_INSPECTION_COMPLETED_NO_BOARD", active)
        for disallowed in ("write_bitstream", "write_checkpoint", "create_project",
                           "program_hw_devices", "open_hw_target", "xsct",
                           "xmutil", "devmem", "/dev/uio", "/dev/mem"):
            self.assertNotIn(disallowed, active)
        self.assertIn("runtime_pl_clk0_enabled=UNKNOWN", script)
        self.assertIn("ps_atb_instance4_enabled=UNKNOWN", script)

    def test_runner_references_only_original_fan_route_and_fresh_evidence(self):
        src = SCRIPT.read_text()
        self.assertIn("aea9bb224006907cf7e62c2a135ec36eda4582b15e8cf6575805f7b807b94b0e", src)
        self.assertIn("52_evidence_sha256.txt", src)
        self.assertIn("48_fan_post_route.dcp", src)
        self.assertIn("scripts/m08_path_a_fan_bd_candidate.tcl", src)
        self.assertIn('"-nolog", "-nojournal", "-notrace"', src)
        self.assertIn('cwd=folder', src)
        self.assertIn('tempfile.mkdtemp(prefix="m08_d2_fan_dcp_READONLY_"', src)
        self.assertIn("hardware_safe_to_test\": False", src)
        self.assertNotIn("shell=True", src)

    def fake_original(self, tmp: Path) -> tuple[Path, str]:
        route = tmp / "m08_2b_path_a_fan_route_ORIGINAL_TEST"
        route.mkdir()
        rows = {}
        for name in m.REQUIRED_ORIGINAL_LEDGER_ROWS:
            path = route / name
            path.write_bytes(("fake original " + name + "\n").encode())
            rows[name] = sha256(path.read_bytes()).hexdigest()
        (route / m.EXPECTED_RECEIPT).write_text(
            "".join(f"{digest}  {name}\n" for name, digest in rows.items()))
        return route, rows[m.EXPECTED_INPUT]

    def test_original_ledger_requires_all_sha_and_prohibits_mutated_files(self):
        with tempfile.TemporaryDirectory() as d:
            route, expected_sha = self.fake_original(Path(d))
            with patch.object(m, "EXPECTED_ORIGINAL_DCP_SHA256", expected_sha):
                verified = m.read_original_ledger(route)
                self.assertEqual(len(verified), len(m.REQUIRED_ORIGINAL_LEDGER_ROWS))
                (route / "43_fan_drc_post_route.rpt").write_text("TAMPERED")
                with self.assertRaisesRegex(m.ForensicRejected, "SHA mismatch"):
                    m.read_original_ledger(route)


    def test_linux_overlay_does_not_independently_manage_pl0_or_afi(self):
        """Document an unresolved deployment gap; NOT proof of runtime clock loss."""
        overlay = (ROOT / "scripts/m08_path_a_stage_uio_overlay.py").read_text()
        self.assertIn('DTS = """', overlay)
        dts = overlay.split('DTS = """', 1)[1].split('"""', 1)[0]
        self.assertIn("generic-uio", dts)
        self.assertIn("firmware-name", dts)
        self.assertNotIn("assigned-clocks", dts)
        self.assertNotIn("assigned-clock-rates", dts)
        self.assertNotIn("xlnx,afi-fpga", dts)
        self.assertNotIn("config-afi", dts)
        # The stock live device tree or PS firmware could still configure
        # these elements. Do not infer a stopped clock from absent DTS words.

    def test_wrong_dcp_identity_cannot_be_accepted_with_rehashed_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            route, _ = self.fake_original(Path(d))
            with self.assertRaisesRegex(m.ForensicRejected, "previously accepted"):
                m.read_original_ledger(route)
            # Cannot make a different DCP accepted by rehashing the ledger;
            # the original hard-pinned SHA is an independent known reference.

    def test_output_path_cannot_overwrite_original_archive(self):
        with tempfile.TemporaryDirectory() as d:
            route, _ = self.fake_original(Path(d))
            with self.assertRaisesRegex(m.ForensicRejected, "original route"):
                m.make_evidence(route, route)
            fresh = Path(d) / "fresh"
            fresh.mkdir()
            result = m.make_evidence(fresh, route)
            self.assertTrue(result.is_dir())
            self.assertNotEqual(result, route)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh absent")
    def test_real_tcl_parser_sha_gate_without_any_vivado(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            dcp = base / "48_fan_post_route.dcp"
            dcp.write_bytes(b"fake fan checkpoint for tclsh guards only\n")
            evidence = base / "fresh"
            evidence.mkdir()
            right_sha = sha256(dcp.read_bytes()).hexdigest()
            wrapper = base / "mock.tcl"
            wrapper.write_text(
                "proc version {flag} { return 2025.2 }\n"
                "proc open_checkpoint {path} { error MOCK_REACHED_AFTER_SHA_CHECK }\n"
                "set forensic_source [lindex $argv 0]\n"
                "set argv [lrange $argv 1 end]\n"
                "source $forensic_source\n"
            )
            # Pass through argv where script is first; wrapper strips it.
            wrong = subprocess.run(
                ["tclsh", str(wrapper), str(TCL), str(dcp), str(evidence), "0" * 64],
                capture_output=True, text=True, timeout=10)
            # The native Tcl fails closed on the wrong SHA BEFORE opening.
            self.assertNotIn("MOCK_REACHED_AFTER_SHA_CHECK", wrong.stdout + wrong.stderr)
            # A single corrected SHA still stops at our mocked checkpoint
            # sentinel; there is no vendor invocation or generated artifact.
            correct = subprocess.run(
                ["tclsh", str(wrapper), str(TCL), str(dcp), str(evidence), right_sha],
                capture_output=True, text=True, timeout=10)
            self.assertIn("MOCK_REACHED_AFTER_SHA_CHECK", correct.stdout + correct.stderr)
            self.assertEqual(list(evidence.iterdir()), [])

    def test_mocked_vendor_success_is_not_physical_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            route, known = self.fake_original(base)
            output = base / "new_forensics"
            output.mkdir()

            def simulate_vendor(command, *, cwd, stdout, stderr, check):
                self.assertEqual(command[0], "vivado")
                self.assertIn("-nojournal", command)
                self.assertEqual(stderr, subprocess.STDOUT)
                self.assertFalse(check)
                self.assertEqual(cwd.parent, output)
                for name in m.REQUIRED_REPORTS:
                    (cwd / name).write_text("MOCK ONLY: " + name + "\n")
                stdout.write(m.SUCCESS + "\n")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(m, "EXPECTED_ORIGINAL_DCP_SHA256", known), \
                 patch.object(m, "check_owner_pc"), \
                 patch("subprocess.run", side_effect=simulate_vendor):
                evidence, success = m.execute(route, output)
            self.assertTrue(success)
            self.assertEqual((evidence / "02_vivado_exit.txt").read_text(),
                             "vivado_exit_status=0\n")
            review = __import__("json").loads((evidence / "98_review.json").read_text())
            self.assertFalse(review["hardware_safe_to_test"])
            self.assertFalse(review["atb_config_verified"])
            self.assertFalse(review["physical_axil_read_verified"])
            receipt = (evidence / "99_evidence_sha256.txt").read_text()
            self.assertIn("01_native_vivado.log", receipt)
            self.assertIn("16_dcp_reset_net_inventory.txt", receipt)
            self.assertEqual((route / m.EXPECTED_INPUT).read_bytes(),
                             b"fake original " + m.EXPECTED_INPUT.encode() + b"\n")

    def test_mocked_vendor_missing_marker_fails_closed_with_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            route, known = self.fake_original(base)
            output = base / "new_forensics"
            output.mkdir()

            def fake_no_marker(command, *, cwd, stdout, stderr, check):
                for name in m.REQUIRED_REPORTS:
                    (cwd / name).write_text("MOCK ONLY\n")
                stdout.write("No native inspection marker\n")
                return subprocess.CompletedProcess(command, 0)

            with patch.object(m, "EXPECTED_ORIGINAL_DCP_SHA256", known), \
                 patch.object(m, "check_owner_pc"), \
                 patch("subprocess.run", side_effect=fake_no_marker):
                evidence, success = m.execute(route, output)
            self.assertFalse(success)
            self.assertTrue((evidence / "99_evidence_sha256.txt").is_file())
            self.assertIn("FAILED_OR_INCOMPLETE",
                          (evidence / "98_review.json").read_text())


if __name__ == "__main__":
    unittest.main()
