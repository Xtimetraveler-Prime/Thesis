"""D3.D.2C original M06 32×4 source, triple-oracle and REAL Icarus RTL.

All tests are PC-only. Missing iverilog must SKIP explicitly, not fake PASS.
A successful bench does not approve Vivado native, JTAG or physical M06.
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
import m08_d3d2c_m06_gate as gate
import m08_d3d2c_m06_vectors as vectors

class M0632NeuronSourceTests(unittest.TestCase):
    def test_original_m06_geometry_and_independent_triple_oracle(self):
        net,events,external,voltages,masks,syn=vectors.golden()
        self.assertEqual(len(net.neurons),32)
        self.assertEqual(len(net.synapses),5)
        self.assertEqual(len(events),17)
        self.assertEqual((net.decay_num,net.decay_den,net.state_bits),(3,4,16))
        self.assertEqual(len(voltages),32)
        self.assertEqual(len(masks),32)
        self.assertEqual(len(syn),32)
        self.assertTrue(all(len(row)==4 for row in voltages))
        self.assertTrue(all(len(row)==4 for row in syn))
        self.assertEqual(external[9][1],-1) # original opposite-sign pair
        self.assertEqual(len(vectors.words()),579)
        self.assertEqual(vectors.words()[:3],("D2C00001","00000003","00000005"))
        self.assertTrue(any(m != 0 for m in masks))
        self.assertTrue(any(w != 0 for row in syn for w in row))
        self.assertTrue(any(edge.weight<0 for edge in net.synapses))
        self.assertTrue(any(edge.pre==edge.post for edge in net.synapses))
        self.assertTrue(any(edge.pre>=16 or edge.post>=16 for edge in net.synapses))

    def test_source_stage_never_claims_real_hardware(self):
        result=gate.source()
        self.assertEqual(result["status"],
                         "M08_D3D2C_M06_32_NEURON_RTL_SOURCE_READY_PC_ONLY")
        for key in ("owner_new_vivado_native_accepted","new_fpga_programmed",
                    "physical_32_neuron_m02_parity_verified",
                    "external_event_coalescing_in_fpga",
                    "original_m06_hls_physically_integrated"):
            self.assertFalse(result[key],key)

    def test_oracle_unique_create_and_bad_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"m06.hex"
            run=[sys.executable,str(ROOT/"scripts/m08_d3d2c_m06_vectors.py"),
                 "--out",str(path)]
            first=subprocess.run(run,capture_output=True,text=True,timeout=30)
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            self.assertIn("DENSE_EVENT_SPARSE_GOLDEN_PC_ONLY",first.stdout)
            rows=path.read_text().splitlines()
            self.assertEqual(len(rows),579)
            self.assertEqual(tuple(rows),vectors.words())
            second=subprocess.run(run,capture_output=True,text=True,timeout=30)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(path.read_text().splitlines(),rows)

    def test_new_rtl_mutation_detected_before_native(self):
        with tempfile.TemporaryDirectory() as directory:
            altered=Path(directory)/"altered.v"
            altered.write_text(
                gate.RTL.read_text().replace(
                    "synaptic_sum = synaptic_sum +",
                    "synaptic_sum = synaptic_sum -"))
            with patch.object(gate,"RTL",altered):
                with self.assertRaisesRegex(gate.Reject,
                                            "hardware semantic absent"):
                    gate.source()

    def test_actual_32_neuron_m06_oracle_vs_icarus_rtl(self):
        if not shutil.which("iverilog") or not shutil.which("vvp"):
            self.skipTest("Icarus unavailable: REAL RTL parity not executed")
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory)
            vec=d/"original_m06.hex"
            vec.write_text("\n".join(vectors.words())+"\n")
            binary=d/"m06_32.vvp"
            compile=subprocess.run([
                "iverilog","-g2012","-s","tb_m08_d3d2c_m06_32_lif_axil",
                "-o",str(binary),
                str(ROOT/"rtl/m08/m08_d3d2c_m06_32_lif_axil.v"),
                str(ROOT/"rtl/m08/tb_m08_d3d2c_m06_32_lif_axil.sv")],
                capture_output=True,text=True,timeout=50)
            self.assertEqual(compile.returncode,0,compile.stdout+compile.stderr)
            sim=subprocess.run(
                ["vvp",str(binary),"+M06_VECTORS="+str(vec)],
                capture_output=True,text=True,timeout=80)
            self.assertEqual(sim.returncode,0,sim.stdout+sim.stderr)
            for marker in (
                "M08_D3D2C_M06_32X4_REAL_RTL_PARITY_PASS run=1",
                "M08_D3D2C_M06_32X4_REAL_RTL_PARITY_PASS run=2",
                "M08_D3D2C_M06_FULL_128_VOLTAGE_SPIKE_SYN_CURRENT_RTL_PASS"):
                self.assertIn(marker,sim.stdout)

if __name__=="__main__":
    unittest.main()
