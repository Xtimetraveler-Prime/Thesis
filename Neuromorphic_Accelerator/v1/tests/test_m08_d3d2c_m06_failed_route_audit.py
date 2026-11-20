"""PC-only original owner FAILED timing-route diagnostic regression.

Synthetic files are NOT real Vivado reports, bitstreams or acceptance. They
test parser policy only. Never invoke Vivado or touch hardware.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_d3d2c_m06_failed_route_audit as gate


class FailedRouteDiagnosticTests(unittest.TestCase):
    def make_synthetic(self, parent: Path) -> tuple[Path, Path]:
        base = parent / "M08"
        base.mkdir()
        run = base / "m08_d3d2c_m06_SYNTHETIC"
        impl = run / gate.IMPL_REL
        impl.mkdir(parents=True)
        (impl / gate.ROUTED_DCP).write_bytes(b"F" * 100001)
        report = """Fake routed timing format used ONLY for parser tests.
WNS(ns) TNS(ns) TNS Failing Endpoints TNS Total Endpoints WHS(ns) THS(ns) THS Failing Endpoints THS Total Endpoints WPWS(ns) TPWS(ns) TPWS Failing Endpoints TPWS Total Endpoints
----------------
-1.125 -6.750 4 1000 0.012 0.000 0 1000 0.000 0.000 0 0

Slack (VIOLATED) : -1.125ns
  Source:    synthetic/fpga/neuron[7]
  Destination: synthetic/fpga/trace_voltage[90]
  Path Group: clk_pl_0
  Requirement: 10.000ns
  Data Path Delay: 11.125ns

Slack (VIOLATED) : -0.748ns
  Source:    synthetic/fpga/spike_mask[0]
  Destination: synthetic/fpga/membrane[31]
"""
        for key, name in gate.REPORTS.items():
            (impl / name).write_text(report if key == "routed_timing"
                                     else "SYNTHETIC "+key+" report\n")
        return run, impl

    def test_synthetic_timing_failure_extraction_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, impl = self.make_synthetic(Path(tmp))
            before = {p.name: sha256(p.read_bytes()).hexdigest()
                      for p in impl.iterdir() if p.is_file()}
            result = gate.audit(run)
            after = {p.name: sha256(p.read_bytes()).hexdigest()
                     for p in impl.iterdir() if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(result["status"],
                             "M08_D3D2C_ORIGINAL_ROUTED_CHECKPOINT_TIMING_FAILED_NO_BITSTREAM")
            self.assertEqual(result["wns_ns"], -1.125)
            self.assertEqual(result["tns_ns"], -6.75)
            self.assertEqual(result["setup_failing_endpoints"], 4)
            self.assertEqual(result["whs_ns"], 0.012)
            self.assertEqual(result["hold_failing_endpoints"], 0)
            self.assertEqual(len(result["timing_violation_excerpts"]), 2)
            self.assertIn("synthetic/fpga/neuron[7]",
                          result["timing_violation_excerpts"][0]["original_path_excerpt"])
            self.assertTrue(result["no_evidence_written"])
            self.assertTrue(result["no_board_actions"])
            self.assertFalse(result["fpga_programmed"])
            self.assertFalse(result["new_bitstream_exists"])

    def test_missing_original_report_fails_without_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, impl = self.make_synthetic(Path(tmp))
            (impl / gate.REPORTS["routed_timing"]).unlink()
            before = sorted(p.name for p in impl.iterdir())
            with self.assertRaisesRegex(gate.Reject, "missing/symlinked original file"):
                gate.audit(run)
            self.assertEqual(before, sorted(p.name for p in impl.iterdir()))

    def test_symlinked_report_and_bitstream_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, impl = self.make_synthetic(Path(tmp))
            timing = impl / gate.REPORTS["routed_timing"]
            genuine = impl / "original.txt"
            timing.rename(genuine)
            timing.symlink_to(genuine)
            with self.assertRaisesRegex(gate.Reject, "missing/symlinked"):
                gate.audit(run)
            timing.unlink()
            genuine.rename(timing)
            new_bit = run / "bitstream_candidate" / (
                gate.DESIGN + "_UNRELEASED.bit")
            new_bit.parent.mkdir()
            new_bit.write_bytes(b"fake-bit-not-accepted")
            with self.assertRaisesRegex(gate.Reject, "unexpected bitstream"):
                gate.audit(run)

    def test_positive_timing_refuses_to_mislabel_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, impl = self.make_synthetic(Path(tmp))
            timing = impl / gate.REPORTS["routed_timing"]
            timing.write_text(timing.read_text().replace(
                "-1.125 -6.750 4", "0.125 0.000 0").replace(
                "Slack (VIOLATED)", "Slack (MET)").replace(
                "-0.748ns", "+0.748ns"))
            with self.assertRaisesRegex(gate.Reject,
                                        "does not show an actual negative"):
                gate.audit(run)

    def test_no_device_or_routing_side_effects(self):
        code = (ROOT/"scripts/m08_d3d2c_m06_failed_route_audit.py").read_text()
        for token in (
            "subprocess.run", "os.system", "open_hw_manager", "program_hw_devices",
            "write_bitstream", "launch_runs", "connect_hw_server",
            "shutil.copy", "Path.write_", "mkdir(", "unlink(",
        ):
            self.assertNotIn(token, code)
        self.assertIn("original_reports", code)
        self.assertIn("timing_violation_excerpts", code)


if __name__ == "__main__":
    unittest.main()
