"""G3.3 true independent M02/M03 neural parity vector tests (NO vendor sim)."""
from __future__ import annotations
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
import re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src"))
from m06_g3_3_m02_m03_owner_vectors import (
    fixture_oracles,metrics_reference,pack_neuron,pack_synapse,
    pack_external,pack_trace,twos,vectors,NEURONS,TICKS,CANONICAL_FIRST
)

class OriginalHLSDenseSparseVectorsTests(unittest.TestCase):
    def test_independent_dense_event_sparse_exact_network(self):
        net,events,dense,sparse=fixture_oracles()
        self.assertEqual(len(net.neurons),32)
        self.assertEqual(len(net.synapses),5)
        self.assertEqual(len(events),17)
        self.assertEqual(TICKS,4)
        self.assertEqual(CANONICAL_FIRST,4064)
        self.assertEqual(sparse.trace,dense)
        self.assertEqual(sum(map(len,dense.spike_rows)),8)
        self.assertGreater(sparse.evaluation_count,0)
        self.assertGreater(sum(sparse.deliveries_by_tick),len(events))
        self.assertEqual(sparse.deliveries_by_tick[0],5)
        self.assertTrue(any(syn.delay==2 for syn in net.synapses))

    def test_exact_typed_struct_abi_provisional_measured_pin_width(self):
        net,events,_,_=fixture_oracles()
        self.assertEqual(twos(-32768,16),0x8000)
        self.assertEqual(pack_neuron(net.neurons[0])&0xffffffff,
                         twos(net.neurons[0].initial_v,32))
        self.assertEqual(pack_synapse(net.synapses[0])&0xffffffff,0)
        self.assertEqual((pack_synapse(net.synapses[0])>>128),1)
        self.assertEqual((pack_synapse(net.synapses[0])>>96)&0xffffffff,0)
        self.assertEqual((pack_external(events[0])>>64)&0xffffffff,0)
        trace=pack_trace(3,16,-32768,True,True,27)
        self.assertEqual(trace&((1<<64)-1),3)
        self.assertEqual((trace>>64)&0xffffffff,16)
        self.assertEqual((trace>>96)&0xffffffff,0xffff8000)
        self.assertEqual((trace>>128)&0xff,1)
        self.assertEqual((trace>>136)&0xff,1)
        self.assertEqual((trace>>160)&0xffffffff,27)
        with self.assertRaises(ValueError):
            twos(-32769,16)

    def test_one_cache_slot_exact_eviction_and_metrics(self):
        _,_,_,sparse=fixture_oracles()
        metrics=metrics_reference(sparse)
        self.assertEqual(metrics["page_accesses"],
                         NEURONS*TICKS+sparse.evaluation_count)
        self.assertEqual(metrics["page_accesses"],
                         metrics["page_hits"]+metrics["page_misses"])
        self.assertEqual(metrics["page_fills"],metrics["page_misses"])
        self.assertEqual(metrics["page_evictions"],metrics["page_misses"]-1)
        self.assertGreater(metrics["dirty_writebacks"],2)
        self.assertEqual(metrics["m05_evaluations"],sparse.evaluation_count)
        self.assertEqual(metrics["emitted_spikes"],8)

    def test_independent_stream_and_every_trace_and_final_record_emitted(self):
        s=vectors()
        self.assertEqual(s,vectors())
        # The generator declares unpacked arrays as "oracle_x [0:N-1]"
        # (space before '['), while assignments use "oracle_x[i]".
        # Check each declaration separately and verify every assigned index:
        # a raw substring count incorrectly expects an extra declaration hit.
        for name, bits, count in (
            ("oracle_neurons", 128, NEURONS),
            ("oracle_synapses", 192, 5),
            ("oracle_external", 128, 17),
            ("oracle_trace", 192, NEURONS*TICKS),
            ("oracle_final_row", 128, NEURONS),
        ):
            self.assertIn(
                f"reg [{bits-1}:0] {name} [0:{count-1}];", s
            )
            actual_indices = [
                int(index) for index in re.findall(
                    rf"(?m)^  {name}\[(\d+)\] = {bits}'h[0-9a-f]+;$", s
                )
            ]
            self.assertEqual(
                actual_indices, list(range(count)),
                f"{name} must have exactly one value for every index"
            )
        self.assertIn("oracle_metrics = 256'h",s)
        self.assertIn("M02 dense + M02 event + M03 sparse",s)
        self.assertNotIn("$finish",s)

    def test_no_overwrite_and_zip_safe_source_generated_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"m06_g3_3_m02_m03_vectors.svh"
            cmd=[sys.executable,str(ROOT/"scripts/m06_g3_3_m02_m03_owner_vectors.py"),
                 "--output",str(p)]
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            self.assertIn("SOURCE_ONLY_NO_VENDOR_XSIM",first.stdout)
            self.assertEqual(p.read_text(),vectors())
            second=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(second.returncode,2)
            self.assertEqual(p.read_text(),vectors())

if __name__=="__main__":
    unittest.main()
