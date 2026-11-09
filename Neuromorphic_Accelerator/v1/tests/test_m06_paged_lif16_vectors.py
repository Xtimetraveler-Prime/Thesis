"""Independent M02 dense LIF fixture/provenance for 1-slot hardware paging."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_generate_paged_lif16_vectors import (
    DECAY_DEN, DECAY_NUM, NEURONS, TICKS, fixture, generate,
)
from neuromorphic_accelerator_v1.m02_types import InputCurrent


class M06PagedLIFHardwareFixtureTests(unittest.TestCase):
    def test_paged_workload_is_bigger_than_one_physical_page(self):
        net,trace,deliveries=fixture()
        self.assertEqual(NEURONS,32)
        self.assertEqual(TICKS,4)
        self.assertEqual((DECAY_NUM,DECAY_DEN),(3,4))
        self.assertEqual(len(net.neurons),32)
        self.assertEqual(len(trace.voltage_rows),TICKS)
        self.assertEqual(len(deliveries),TICKS)
        self.assertEqual(len(deliveries[0]),NEURONS)
        self.assertTrue(any(edge.delay==2 for edge in net.synapses))
        self.assertTrue(any(edge.pre==16 and edge.post==0 for edge in net.synapses))

    def test_strict_negative_saturation_and_positive_saturation_before_threshold(self):
        _,trace,deliveries=fixture()
        self.assertEqual(deliveries[0][7],32767)
        self.assertEqual(deliveries[0][8],-32768)
        self.assertIn(7,trace.spike_rows[0])
        self.assertEqual(trace.voltage_rows[0][8],-32768)
        self.assertLessEqual(max(max(row) for row in trace.voltage_rows),32767)
        self.assertGreaterEqual(min(min(row) for row in trace.voltage_rows),-32768)

    def test_duplicate_current_events_cancel_before_saturation(self):
        _,_,deliveries=fixture()
        self.assertEqual(deliveries[1][9],-1)

    def test_deterministic_complete_sv_vector_generation(self):
        s=generate()
        self.assertEqual(s,generate())
        self.assertIn("task automatic load_m06_lif_vectors;",s)
        self.assertIn("initial_v[31]=",s)
        self.assertIn("neuron_bias[31]=",s)
        self.assertIn("neuron_threshold[31]=",s)
        self.assertIn("routed_current[127]=",s)
        self.assertIn("oracle_v[127]=",s)
        self.assertIn("oracle_spike[127]=",s)
        self.assertIn("routed_current[8]=-32'sd32768;",s)
        self.assertIn("routed_current[7]=32'sd32767;",s)
        self.assertIn("oracle_v[8]=-16'sd32768;",s)
        self.assertEqual(s.count("oracle_spike["),128)

    def test_exclusive_fixture_cli_does_not_replace_prior_run(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"m06_lif16_vectors.vh"
            cmd=[sys.executable,
                 str(ROOT/"scripts/m06_generate_paged_lif16_vectors.py"),
                 "--output",str(p)]
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertEqual(p.read_text(),generate())
            old=p.read_bytes()
            again=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(again.returncode,2)
            self.assertIn("exclusive",again.stderr)
            self.assertEqual(p.read_bytes(),old)


if __name__=="__main__":
    unittest.main()
