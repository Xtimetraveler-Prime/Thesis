"""D3.D.2D real raw-event AXI ingress and original M06 32x4 RTL parity.

No Vivado, JTAG or physical actions. Icarus must execute actual RTL; when it
is missing the test explicitly SKIPs rather than faking neural parity.
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
import m08_d3d2d_event_gate as gate
import m08_d3d2d_event_vectors as vec
import m08_d3d2c_m06_vectors as predecessor

class D3D2DOriginalRawEventSourceTests(unittest.TestCase):
    def test_original_m06_17_individual_signed_events_reconstruct_exact_currents(self):
        net,events,external,voltages,masks,syn=predecessor.golden()
        self.assertEqual((len(net.neurons),len(net.synapses),len(events)),(32,5,17))
        self.assertEqual(vec.WORDS,630)
        words=vec.words()
        self.assertEqual(tuple(words[:579]),predecessor.words())
        self.assertEqual(len(words[579:]),51)
        actual=[[0]*4 for _ in range(32)]
        for k in range(17):
            n=int(words[579+3*k],16)
            t=int(words[580+3*k],16)
            current=int(words[581+3*k],16)
            if current>=(1<<31): current-=1<<32
            self.assertEqual((n,t,current),
                             (events[k].neuron,events[k].tick,events[k].current))
            actual[n][t]+=current
        self.assertEqual(actual,external)
        self.assertTrue(any(ev.current < 0 for ev in events))
        self.assertTrue(any(e.weight < 0 for e in net.synapses))

    def test_new_source_gate_no_hardware_claim_and_preserves_m32n(self):
        out=gate.source()
        self.assertEqual(out["status"],"M08_D3D2D_RAW_17_EVENT_INGRESS_SOURCE_READY_PC_ONLY")
        self.assertTrue(out["hardware_event_aggregation_in_rtl"])
        for key in ("original_d3d2c_image_reused","new_native_image_reviewed",
                    "physical_programmed","physical_ddr",
                    "raw_event_ingress_physically_verified",
                    "original_m05_hls_physical"):
            self.assertFalse(out[key],key)
        self.assertEqual(out["event_transport"],"JTAG_AXI_LITE_MAILBOX_NOT_STREAM_DMA")

    def test_event_push_sign_overflow_and_clear_mutations_reject(self):
        rtl=gate.RTL.read_text()
        for old,mutation in (
            ("event_overflow=event_sum_ext[32] != event_sum_ext[31]",
             "event_overflow=1'b0"),
            ("currents[event_index] <= event_sum_ext[31:0]",
             "currents[event_index] <= event_current"),
            ("event_count <= event_count + 1'b1", "event_count <= event_count"),
            ("for (i=0;i<128;i=i+1) currents[i] <= 0",
             "for (i=0;i<128;i=i+1) currents[i] <= 1"),
        ):
            self.assertEqual(rtl.count(old),1)
            with tempfile.TemporaryDirectory() as temp:
                changed=Path(temp)/"changed.v"
                changed.write_text(rtl.replace(old,mutation))
                with patch.object(gate,"RTL",changed):
                    with self.assertRaisesRegex(gate.Reject,"event/neural semantic absent"):
                        gate.source()

    def test_generate_original_hex_only_once_exclusively(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"raw17.hex"
            cmd=[sys.executable,str(ROOT/"scripts/m08_d3d2d_event_vectors.py"),
                 "--out",str(target)]
            first=subprocess.run(cmd,capture_output=True,text=True,timeout=35)
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            self.assertIn("RAW_17_EVENTS_M02_M03_GOLDEN_PC_ONLY",first.stdout)
            self.assertEqual(target.read_text().splitlines(),list(vec.words()))
            again=subprocess.run(cmd,capture_output=True,text=True,timeout=35)
            self.assertNotEqual(again.returncode,0)
            self.assertEqual(target.read_text().splitlines(),list(vec.words()))

    def test_real_17_event_mailbox_and_384_value_m06_icarus_parity(self):
        if not shutil.which("iverilog") or not shutil.which("vvp"):
            self.skipTest("Icarus missing: no REAL D3.D.2D RTL parity")
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            path=folder/"raw17.hex"
            path.write_text("\n".join(vec.words())+"\n")
            binary=folder/"raw17.vvp"
            build=subprocess.run([
                "iverilog","-g2012","-s","tb_m08_d3d2d_raw_event_lif_axil",
                "-o",str(binary),
                str(ROOT/"rtl/m08/m08_d3d2d_raw_event_lif_axil.v"),
                str(ROOT/"rtl/m08/tb_m08_d3d2d_raw_event_lif_axil.sv")
            ],capture_output=True,text=True,timeout=75)
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            run=subprocess.run(["vvp",str(binary),"+M06_EVENT_VECTORS="+str(path)],
                               capture_output=True,text=True,timeout=100)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertEqual(
                run.stdout.count("M08_D3D2D_REAL_RTL_128_FPGA_EVENT_BUCKET_SUMS_PASS"),2)
            for k in (1,2,3):
                self.assertIn(
                    f"M08_D3D2D_M06_32X4_REAL_RTL_EVENT_PARITY_PASS run={k}",
                    run.stdout)
            self.assertIn(
                "M08_D3D2D_FULL_128_BUCKET_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_RTL_PASS",
                run.stdout)

if __name__=="__main__":
    unittest.main()
