"""D3.D.2B independent M02 recurrent network + actual Icarus RTL parity.

These tests run on PC/CI ONLY. Never connect, program or modify KV260.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2b_synaptic_gate as gate
import m08_d3d2b_synaptic_vectors as vectors


class SynapticRoutingTests(unittest.TestCase):
    def test_source_policy_and_no_physical_claim(self):
        data=gate.source()
        self.assertEqual(
            data["status"],"M08_D3D2B_ROUTED_SYNAPSES_SOURCE_ACCEPTED_PC_ONLY")
        self.assertFalse(data["hardware_executed"])
        self.assertFalse(data["recurrent_synapse_physical_verified"])

    def test_both_m02_oracles_and_nontrivial_recurrence(self):
        self.assertEqual(len(vectors.FIXTURES),2)
        for fixture in vectors.FIXTURES:
            observed=vectors.expected(fixture)
            self.assertEqual(observed,vectors.ANCHORS[fixture.name])
            self.assertEqual(len(vectors.format_fixture(fixture).split("|")),
                             vectors.FIELD_COUNT)
            self.assertEqual(len(fixture.edges),8)
            self.assertTrue(all(e.delay>0 for e in fixture.edges))
            self.assertTrue(any(e.weight<0 for e in fixture.edges))
            self.assertTrue(any(e.pre==e.post for e in fixture.edges))
            self.assertTrue(any(e.pre!=e.post for e in fixture.edges))
            self.assertTrue(any(sum(1 for x in fixture.edges
                                     if x.pre==e.pre and x.post==e.post and
                                     x.delay==e.delay)>1 for e in fixture.edges))
        self.assertEqual(vectors.ANCHORS["chain_recurrent"][1],(1,2,4,8))
        self.assertEqual(vectors.ANCHORS["inhibition_half_decay"][1],(1,10,4,8))

    def test_golden_generator_unique_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"golden.txt"
            argv=[sys.executable,str(ROOT/"scripts/m08_d3d2b_synaptic_vectors.py"),
                  "--out",str(out)]
            result=subprocess.run(argv,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn("M08_D3D2B_M02_ROUTED_GOLDENS_PC_ONLY=",result.stdout)
            self.assertEqual(len(out.read_text().splitlines()),4)
            before=out.read_bytes()
            duplicate=subprocess.run(argv,capture_output=True,text=True,timeout=30)
            self.assertNotEqual(duplicate.returncode,0)
            self.assertEqual(out.read_bytes(),before)

    def test_first_native_drc_fails_closed_on_unreviewed_warnings(self):
        with self.assertRaisesRegex(gate.Reject,"REVIEW_REQUIRED"):
            gate.inspect_new_drc("Checks found: 7\n")
        with self.assertRaisesRegex(gate.Reject,"ambiguous"):
            gate.inspect_new_drc("")
        with self.assertRaisesRegex(gate.Reject,"contradicts"):
            gate.inspect_new_drc(
                "Checks found: 0\nREQP-1858#1 Warning\n")
        self.assertEqual(gate.inspect_new_drc("Checks found: 0\n")["drc_checks"],0)

    def test_mutating_synapse_routing_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            damaged=Path(tmp)/"bad.v"
            damaged.write_text(gate.RTL.read_text().replace(
                "synaptic_sum = synaptic_sum +",
                "synaptic_sum = synaptic_sum -"))
            with patch.object(gate,"RTL",damaged):
                with self.assertRaisesRegex(gate.Reject,"neural hardware semantic"):
                    gate.source()

    def test_iverilog_actual_synaptic_network_and_axi(self):
        if shutil.which("iverilog") is None or shutil.which("vvp") is None:
            self.skipTest("Icarus not installed: cannot claim RTL simulation")
        with tempfile.TemporaryDirectory() as tmp:
            binary=Path(tmp)/"tb.vvp"
            compile=subprocess.run([
                "iverilog","-g2012","-s","tb_m08_d3d2b_synaptic_lif_axil",
                "-o",str(binary),
                str(ROOT/"rtl/m08/m08_d3d2b_synaptic_lif_axil.v"),
                str(ROOT/"rtl/m08/tb_m08_d3d2b_synaptic_lif_axil.sv"),
            ],capture_output=True,text=True,timeout=50)
            self.assertEqual(compile.returncode,0,compile.stdout+compile.stderr)
            sim=subprocess.run(["vvp",str(binary)],
                               capture_output=True,text=True,timeout=50)
            self.assertEqual(sim.returncode,0,sim.stdout+sim.stderr)
            for marker in (
                "M08_D3D2B_CHAIN_RECURRENT_RTL_PASS",
                "M08_D3D2B_INHIBITION_HALF_DECAY_RTL_PASS",
                "M08_D3D2B_SYNAPTIC_ROUTING_RTL_ALL_PASS",
            ):
                self.assertIn(marker,sim.stdout)


if __name__=="__main__":
    unittest.main()
