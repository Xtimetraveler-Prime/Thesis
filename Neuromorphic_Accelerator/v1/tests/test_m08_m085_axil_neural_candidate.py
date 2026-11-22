"""Genuine source-only AXI-Lite CSR grant -> 7-page LIF AXI4 workload.

The original signed16 model and exact 512-word M02/M03 oracle remain
comparison-only. This uses a REAL iverilog testbench over synthetic DDR and
FAKE driver/route/drain signals, not PS HPM0, kernel DMA or physical K26.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/"rtl/m08"
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as fixture

SOURCES=tuple(RTL/name for name in (
    "m08_host_staged_page_bank.sv",
    "m08_paged_m06_lif_engine.v",
    "m08_m085_ddr_page_admission.v",
    "m08_m085_axi128_page_engine.v",
    "m08_m085_axi128_page_candidate.v",
    "m08_m085_axi_bank_bridge.v",
    "m08_m085_axi_neural_shell.v",
    "m08_m085_kernel_dma_lease_fence.v",
    "m08_m085_trusted_control_abi.v",
    "m08_m085_axil_control_candidate.v",
    "m08_m085_axil_neural_candidate.v",
    "tb_m08_m085_axil_neural_candidate.sv",
))
MARK="M08_5_AXIL_NEURAL_512_ORACLE_24_DISPATCHES_PASS"


class M085AXILRealNeuralSourceTests(unittest.TestCase):
    def test_source_connects_csr_grant_and_real_neural_not_fake_oracle(self):
        src=SOURCES[-2].read_text()
        tb=SOURCES[-1].read_text()
        control=(RTL/"m08_m085_axil_control_candidate.v").read_text()
        for expected in (
            "m08_m085_axil_control_candidate control_plane",
            "m08_m085_axi_neural_shell",
            ".owner_lease_active(lease_active && !lease_poisoned)",
            ".session_poison(lease_poisoned || unauthorized_request)",
            ".USE_RUNTIME_WINDOW(1)",
            "page_dma_address",
            "admitted_begin+({32'd0,request_page}<<8)",
            ".stop_new_requests(stop_new_requests)",
            ".s_axi_awaddr(s_axi_awaddr)",
            ".m_axi_araddr(m_axi_araddr)",
        ):
            self.assertIn(expected,src)
        self.assertIn("assign admit_work=csr_admit && !write_embargo",control)
        self.assertIn("M08_5_AXIL_CSR_7_SLOT_REAL_NEURAL_GRANT_PASS",tb)
        self.assertIn(MARK,tb)
        self.assertIn("M08_5_REAL_LIF_AXI_BANK_M02_M03_512_PARITY_24_DISPATCHES_5_EDGES_PASS",tb)
        self.assertNotIn("m08_m085_kernel_owned_neural_candidate #(",tb)
        for forbidden in ("program_hw_devices", "/dev/mem", "0x40000000",
                          "dma_alloc_coherent(", "open_hw_manager"):
            self.assertNotIn(forbidden,src+tb)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "real Icarus required; no mock RTL substitute")
    def test_axil_grant_actual_lif_24_page_dispatches_original_512_oracle(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            exe=out/"m085_axil_neural.vvp"
            comp=subprocess.run(
                ["iverilog","-g2012","-s","tb_m08_m085_axil_neural_candidate",
                 "-o",str(exe),*[str(p) for p in SOURCES]],
                capture_output=True,text=True,timeout=90
            )
            self.assertEqual(comp.returncode,0,comp.stdout+comp.stderr)
            self.assertEqual(comp.stderr.strip(),"","Icarus warnings prohibited")
            _,net,events,_,_,_,_=fixture.source()
            self.assertEqual(len(events),17)
            self.assertEqual(len(net.synapses),5)
            oracle=out/"independent_512_comparison_only.hex"
            fixture.write_hex(oracle,fixture.golden_words())
            edges=out/"edge_input.hex"
            fixture.write_hex(edges,fixture.edge_words())
            inputs=[f"+golden={oracle}",f"+edge={edges}"]
            for p in range(6):
                words=fixture.neural_words(p)
                self.assertTrue(fixture.audit_page(words,p,0))
                source=out/f"neural_input_{p}.hex"
                fixture.write_hex(source,words)
                inputs.append(f"+page{p}={source}")
            run=subprocess.run(
                ["vvp",str(exe),"+CASE=0",*inputs],
                capture_output=True,text=True,timeout=120
            )
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertEqual(run.stderr.strip(),"")
            for marker in (
                MARK,
                "M08_5_AXIL_CSR_7_SLOT_REAL_NEURAL_GRANT_PASS",
                "M08_5_REAL_LIF_AXI_BANK_M02_M03_512_PARITY_24_DISPATCHES_5_EDGES_PASS",
                "M08_5_M6EG_SEVENTH_SLOT_FIVE_EDGE_BOOTSTRAP_PASS",
            ):
                self.assertEqual(run.stdout.count(marker),1,run.stdout)
            self.assertEqual(run.stdout.count("M08_5_AXIDDR_REAL_SIGNED16_PAGE_PASS tick="),24)
            self.assertEqual(run.stdout.count("M08_5_AXIDDR_TICK_BARRIER_PASS tick="),4)


if __name__=="__main__":
    unittest.main()
