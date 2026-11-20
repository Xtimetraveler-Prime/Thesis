"""M32Q D3.D.2E.1 actual clocked AXI RTL + 17-event M02/M03 M06 parity.

Icarus MUST be installed: no skipped neural simulation is counted as pass.
This test never opens Vivado hardware or alters accepted physical evidence.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import m08_d3d2e_queue_gate as gate
import m08_d3d2d_event_vectors as vectors
import m08_d3d2c_m06_vectors as independent_m06

class QueueTickSourceTests(unittest.TestCase):
    def test_gate_oracle_retains_accepted_m06(self):
        payload = gate.source()
        self.assertEqual(payload["status"], "M08_D3D2E_TICK_QUEUE_SOURCE_CANDIDATE_NO_BOARD")
        self.assertEqual(payload["queue_capacity"], 32)
        self.assertEqual(payload["expected_neural_and_input_checks"], 512)
        for field in ("native_candidate_routed", "new_image_drc_timing_sha_reviewed",
                      "physical_programming_authorized", "physical_programmed",
                      "asynchronous_ingress_proven", "physical_ddr"):
            self.assertFalse(payload[field], field)
        original = independent_m06.golden()
        self.assertEqual(len(original[1]), 17)
        self.assertEqual(tuple(vectors.words()[:579]),
                         independent_m06.words())
        self.assertEqual(len(vectors.words()), 630)

    def test_admission_service_and_tick_contract_mutations_fail_closed(self):
        original = gate.RTL.read_text()
        for anchor, changed in (
            ("fifo_depth == 6'd32", "fifo_depth == 6'd33"),
            ("event_count >= 7'd64", "event_count >= 7'd65"),
            ("shadow_current[event_index] <= event_sum_ext[31:0]",
             "shadow_current[event_index] <= event_current"),
            ("serviced_count <= serviced_count + 1'b1",
             "serviced_count <= serviced_count"),
            ("serviced_tick_mask[active_service_tick] <= 1'b1",
             "serviced_tick_mask[active_service_tick] <= 1'b0"),
            ("next_service_tick <= next_service_tick + 1'b1",
             "next_service_tick <= next_service_tick"),
            ("serviced_count == event_count", "serviced_count != event_count"),
        ):
            self.assertEqual(original.count(anchor), 1, anchor)
            with tempfile.TemporaryDirectory() as td:
                mutated = Path(td) / "mutated.v"
                mutated.write_text(original.replace(anchor, changed))
                with patch.object(gate, "RTL", mutated):
                    with self.assertRaisesRegex(gate.Reject, "missing new queue/neuronal"):
                        gate.source()

    def test_real_clocked_fifo_512_comparisons_and_negative_paths(self):
        self.assertIsNotNone(shutil.which("iverilog"),
                             "Icarus required, install iverilog; never skip RTL")
        self.assertIsNotNone(shutil.which("vvp"),
                             "vvp required, install iverilog; never skip RTL")
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            vector_path = folder / "original_m06_raw17.hex"
            vector_path.write_text("\n".join(vectors.words()) + "\n")
            binary = folder / "m32q.vvp"
            built = subprocess.run([
                "iverilog", "-g2012", "-s", "tb_m08_d3d2e_tick_queue_lif_axil",
                "-o", str(binary), str(gate.RTL), str(gate.TB)
            ], capture_output=True, text=True, timeout=75)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            simulated = subprocess.run(
                ["vvp", str(binary), "+M06_EVENT_VECTORS=" + str(vector_path)],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(simulated.returncode, 0,
                             simulated.stdout + simulated.stderr)
            transcript = simulated.stdout
            self.assertEqual(
                transcript.count("M08_D3D2E_REAL_RTL_17_EVENTS_TICK_SERVICE_PASS"), 2)
            self.assertEqual(
                transcript.count("M08_D3D2E_REAL_RTL_128_FPGA_EVENT_BUCKET_SUMS_PASS"), 2)
            for number in (1, 2, 3):
                self.assertIn(
                    f"M08_D3D2E_M06_32X4_REAL_RTL_EVENT_PARITY_PASS run={number}",
                    transcript)
            self.assertIn(
                "M08_D3D2E_FULL_128_BUCKET_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_RTL_PASS",
                transcript)

if __name__ == "__main__":
    unittest.main()
