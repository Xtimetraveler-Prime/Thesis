"""M08.4 first REAL signed16 paged-LIF RTL vs unchanged M02/M03 M06 oracle.

Runs genuine Icarus if installed: configured five synapses, one 256B
resident AXI bank, six logical state pages x four ticks, full signed16
membrane recurrence, host save/eviction/reload, 512 independently checked
input/voltage/spike/syn values. External 17 events are presently
HOST-COALESCED (not on-fabric FIFO in this new shell), and NO physical
K26 execution/timing/DDR is claimed. Never use mocks as real RTL PASS.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as fixture

RTL=ROOT/"rtl/m08"
SOURCES=tuple(RTL/s for s in (
    "m08_paged_m06_lif_shell.v",
    "m08_paged_m06_lif_engine.v",
    "m08_axil_page_control.sv",
    "m08_host_staged_page_bank.sv",
    "tb_m08_paged_m06_lif.sv",
))
PASS_MARKERS=(
    "M08_PAGED_M06_ON_FABRIC_RECURRENT_EDGE_SETUP_5_PASS",
    "M08_PAGED_M06_ONE_RESIDENT_SIX_LOGICAL_NEURAL_PAGES_24_REAL_DISPATCHES_PASS",
    "M08_PAGED_M06_REAL_FABRIC_128_CURRENT_128_VOLTAGE_128_SPIKE_128_RECURRENT_M02_M03_PASS",
    "M08_PAGED_M06_512_REAL_IVERILOG_PARITY_NO_K26_NO_DDR_NO_RAW_FIFO_PASS",
)

class M08PagedM06LIFSourceTests(unittest.TestCase):
    def test_exact_original_32_neurons_17_events_5_edges_4_ticks_not_prepopulated(self):
        self.assertEqual([fixture.neurons_in_page(i) for i in range(6)],
                         [6,6,6,6,6,2])
        self.assertEqual(fixture.PAGES,6)
        self.assertEqual(fixture.PER_PAGE,6)
        self.assertEqual(fixture.BYTES,256)
        _,net,events,ext,volts,masks,syn=fixture.source()
        self.assertEqual(len(events),17)
        self.assertEqual(len(net.synapses),5)
        golden=fixture.golden_words()
        self.assertEqual(len(golden),512)
        for t in range(4):
            for n in range(32):
                offset=(t*32+n)*4
                self.assertEqual(golden[offset],int(fixture.m06.u32(ext[n][t]),16))
                self.assertEqual(golden[offset+1],int(fixture.m06.u32(volts[n][t]),16))
                self.assertEqual(golden[offset+2],(masks[n]>>t)&1)
                self.assertEqual(golden[offset+3],int(fixture.m06.u32(syn[n][t]),16))
        for p in range(6):
            page=fixture.neural_words(p)
            self.assertEqual(len(page),64)
            self.assertEqual(page[60:64],(fixture.MAGIC_NEURAL,p,
                          fixture.neurons_in_page(p),0))
            self.assertTrue(fixture.audit_page(page,p,0))
            for local in range(fixture.neurons_in_page(p)):
                base=local*10
                self.assertEqual(page[base+8],0,
                                 "no precomputed golden spike mask as input")
                self.assertEqual(page[base+9],0,
                                 "no precomputed golden syn trace as input")
        self.assertEqual(fixture.edge_words()[60:64],
                         (fixture.MAGIC_EDGES,fixture.EDGE_ID,5,0))

    def test_host_ownership_fixture_rejects_invalid_ids_ticks_and_mutations(self):
        for p in range(6):
            page=fixture.neural_words(p)
            for tick in (-1,4,"1",True):
                with self.subTest(page=p,tick=tick):
                    with self.assertRaises(fixture.Reject):
                        fixture.neural_words(p,tick)
            for other in range(6):
                if other==p: continue
                with self.assertRaises(fixture.Reject):
                    fixture.audit_page(page,other,0)
            for field in (1,2,3,4,5,6,7,8,9,60,61,62,63):
                mutated=list(page)
                mutated[field]^=1
                with self.subTest(page=p,field=field):
                    with self.assertRaises(fixture.Reject):
                        fixture.audit_page(tuple(mutated),p,0)
        for invalid in (-1,6,True,None,1.0):
            with self.assertRaises(fixture.Reject):
                fixture.neurons_in_page(invalid)

    def test_actual_compute_port_not_checksum_stub_and_fault_is_sticky(self):
        engine=(RTL/"m08_paged_m06_lif_engine.v").read_text()
        top=(RTL/"m08_paged_m06_lif_shell.v").read_text()
        original=(RTL/"m08_ps_page_safe_shell.v").read_text()
        self.assertIn("module m08_paged_m06_lif_engine",engine)
        self.assertIn("global_spikes",engine)
        self.assertIn("syn_sum",engine)
        self.assertIn("three_scaled",engine)
        self.assertIn("next_v",engine)
        self.assertIn("edge_configured",engine)
        self.assertIn("state<=S_FAULT",engine)
        self.assertIn("module m08_paged_m06_lif_shell",top)
        self.assertIn("m08_paged_m06_lif_engine neural_engine",top)
        self.assertIn("m08_axil_page_control #(.ENABLE_COMPUTE(1'b1))",top)
        self.assertIn("m08_axil_page_control #(.ENABLE_COMPUTE(1'b0))",original)
        for wire in ("awaddr","awprot","awvalid","awready","wdata","wstrb",
                     "wvalid","wready","bresp","bvalid","bready",
                     "araddr","arprot","arvalid","arready",
                     "rdata","rresp","rvalid","rready"):
            self.assertIn(f".s_axi_{wire}(s_axi_{wire})",top)
        for not_allowed in ("program_hw_devices","write_bitstream",
                            "dma_alloc","/dev/mem","m_axi_awaddr"):
            self.assertNotIn(not_allowed,top+engine)
        self.assertNotIn("$display",engine)
        self.assertNotIn("$fatal",engine)
        self.assertNotIn("m08_page_compute_probe probe",top)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Real Icarus+vvp mandatory for neural parity; skipped on hosts without it")
    def test_real_iverilog_32x4_paged_lif_512_m02_m03_results(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)
            plus=[]
            edges=tmp/"original_m06_edges.hex"
            fixture.write_hex(edges,fixture.edge_words())
            plus.append(f"+edge={edges}")
            golden=tmp/"independent_m02_m03_512.hex"
            fixture.write_hex(golden,fixture.golden_words())
            plus.append(f"+golden={golden}")
            for page in range(6):
                page_path=tmp/f"m06_neuron_page_{page}.hex"
                fixture.write_hex(page_path,fixture.neural_words(page))
                plus.append(f"+page{page}={page_path}")
            compiled=tmp/"paged_lif.vvp"
            args=["iverilog","-g2012","-s","tb_m08_paged_m06_lif",
                  "-o",str(compiled),*[str(s) for s in SOURCES]]
            build=subprocess.run(args,capture_output=True,text=True,timeout=90)
            self.assertEqual(build.returncode,0,build.stdout+"\n"+build.stderr)
            self.assertEqual(build.stderr.strip(),"", "unreviewed Icarus syntax warning")
            run=subprocess.run(["vvp",str(compiled),*plus],
                               capture_output=True,text=True,timeout=120)
            self.assertEqual(run.returncode,0,run.stdout+"\n"+run.stderr)
            self.assertEqual(run.stderr.strip(),"")
            self.assertNotIn("FATAL:",run.stdout)
            for name in PASS_MARKERS:
                self.assertEqual(run.stdout.count(name),1,run.stdout)
            for tick in range(4):
                self.assertEqual(
                    run.stdout.count(f"M08_PAGED_M06_TICK_BARRIER_NO_MIXED_EPOCH_PASS|{tick}"),
                    1,run.stdout)
                for page in range(6):
                    self.assertEqual(run.stdout.count(
                        f"M08_PAGED_M06_REAL_256B_STATE_LOAD_COMPUTE_DIRTY_SAVE_PASS|{tick}|{page}"),
                        1,run.stdout)

if __name__=="__main__":
    unittest.main()
