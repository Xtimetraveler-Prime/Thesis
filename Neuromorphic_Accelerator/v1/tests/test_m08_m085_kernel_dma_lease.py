"""Real Icarus kernel-DMA-lease SOURCE CANDIDATE over actual recurrent LIF.

Lease inputs are testbench SYNTHETIC. No Linux driver or PS DDR is bound.
This is a simulation of 7 distinct 256B source pages: 1 M6EG edge
configuration and 6 M6NF signed16 neuron pages, ONE resident bank.
Original independent M02/M03 512-word output oracle is READ/CHECK-ONLY.
No physical K26/PS DDR/DMA/bitstream, no sparse-update or timing claims.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as fixture

RTL=ROOT/"rtl/m08"
SOURCES=tuple(RTL/p for p in (
    "m08_host_staged_page_bank.sv",
    "m08_paged_m06_lif_engine.v",
    "m08_m085_ddr_page_admission.v",
    "m08_m085_axi128_page_engine.v",
    "m08_m085_axi128_page_candidate.v",
    "m08_m085_axi_bank_bridge.v",
    "m08_m085_axi_neural_shell.v",
    "m08_m085_kernel_dma_lease_fence.v",
    "m08_m085_kernel_owned_neural_candidate.v",
    "tb_m08_m085_kernel_dma_neural.sv",
))
MARK="M08_5_REAL_LIF_AXI_BANK_M02_M03_512_PARITY_24_DISPATCHES_5_EDGES_PASS"


class M085KernelDMAWindowSourceTests(unittest.TestCase):
    def test_explicit_seventh_configuration_slot_is_separate_and_default_disabled(self):
        src=(RTL/"m08_m085_axi_bank_bridge.v").read_text()
        standalone=(RTL/"m08_m085_axi128_page_candidate.v").read_text()
        self.assertIn("parameter integer ENABLE_EDGE_SLOT=0",src)
        self.assertIn("BACKING_SLOTS=ENABLE_EDGE_SLOT ? 7 : 6",src)
        self.assertIn("semantic_page_id=is_edge ? 32'hFFFFFFFF : page_q",src)
        self.assertIn("32'h4D364547",src)
        self.assertIn("32'h4D364E46",src)
        self.assertIn("WINDOW_BEGIN=64'd0",src)
        self.assertIn("WINDOW_END=64'd0",src)
        self.assertIn("LOGICAL_PAGES=6",standalone)
        self.assertIn("m08_host_staged_page_bank bank",src)
        self.assertIn("host_readback_verified(host_commit)",src)
        self.assertIn("axi_read_page!==expected_save",src)
        self.assertIn("real_bank_logical==semantic_page_id",src)
        neural=(RTL/"m08_paged_m06_lif_engine.v").read_text()
        self.assertIn("edge_configured",neural)
        self.assertIn("computed_synaptic_events",neural)
        self.assertIn("global_spikes",neural)
        tb=SOURCES[-1].read_text()
        shell=(RTL/"m08_m085_axi_neural_shell.v").read_text()
        leased=(RTL/"m08_m085_kernel_owned_neural_candidate.v").read_text()
        fence=(RTL/"m08_m085_kernel_dma_lease_fence.v").read_text()
        self.assertIn(".USE_RUNTIME_WINDOW(1)",leased)
        self.assertIn("page_dma_address",leased)
        self.assertIn("lease_fence",leased)
        self.assertIn("lease_generation",fence)
        self.assertIn("AXI49_EXCLUSIVE=(65'd1 << 49)",fence)
        self.assertIn("bus_quiescent",fence)
        self.assertIn("runtime_window_begin",fence)
        self.assertIn("session_poison(lease_poisoned)",leased)
        self.assertNotIn("input wire [63:0] request_addr",leased)
        self.assertIn("m08_paged_m06_lif_engine neural_engine",shell)
        self.assertIn(".ENABLE_EDGE_SLOT(1)",shell)
        self.assertIn("m08_m085_kernel_owned_neural_candidate",tb)
        self.assertIn("M08_5_REAL_LIF_AXI_BANK_M02_M03_512_PARITY_24_DISPATCHES_5_EDGES_PASS",tb)
        for forbidden in ("program_hw_devices","open_hw_manager","/dev/mem",
                          "dma_alloc_coherent","0x40000000"):
            self.assertNotIn(forbidden,src+tb+leased+fence)

    def _build(self, dest: Path) -> Path:
        exe=dest/"m085_neural_axi.vvp"
        result=subprocess.run(
            ["iverilog","-g2012","-s","tb_m08_m085_kernel_dma_neural",
             "-o",str(exe),*[str(p) for p in SOURCES]],
            capture_output=True,text=True,timeout=90
        )
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(result.stderr.strip(),"",
                         "new neural DDR source generated Icarus warnings")
        return exe

    def _original_input_arguments(self, output: Path) -> list[str]:
        _,net,events,_,_,_,_=fixture.source()
        self.assertEqual(len(events),17)
        self.assertEqual(len(net.synapses),5)
        args=[]
        edges=output/"original_recurrent_edge_input.hex"
        fixture.write_hex(edges,fixture.edge_words())
        args.append(f"+edge={edges}")
        golden=output/"independent_original_512_comparison_ONLY.hex"
        fixture.write_hex(golden,fixture.golden_words())
        args.append(f"+golden={golden}")
        for page in range(6):
            words=fixture.neural_words(page)
            self.assertTrue(fixture.audit_page(words,page,0))
            path=output/f"original_neural_input_page_{page}.hex"
            fixture.write_hex(path,words)
            args.append(f"+page{page}={path}")
        return args

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "requires real Icarus; no mock neural RTL substitutes")
    def test_actual_recurrent_lif_24_axi_dispatches_512_original_oracle_checks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            exe=self._build(root)
            plus=self._original_input_arguments(root)
            run=subprocess.run(["vvp",str(exe),"+CASE=0",*plus],
                               capture_output=True,text=True,timeout=120)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertEqual(run.stderr.strip(),"")
            self.assertNotIn("FATAL",run.stdout)
            self.assertEqual(run.stdout.count(MARK),1,run.stdout)
            self.assertIn("M08_5_M6EG_SEVENTH_SLOT_FIVE_EDGE_BOOTSTRAP_PASS",run.stdout)
            for tick in range(4):
                self.assertIn(f"M08_5_AXIDDR_TICK_BARRIER_PASS tick={tick}",run.stdout)
                for p in range(6):
                    self.assertIn(
                        f"M08_5_AXIDDR_REAL_SIGNED16_PAGE_PASS tick={tick} slot={p}",
                        run.stdout
                    )

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "requires real Icarus; no mock neural RTL substitutes")
    def test_recurrent_neural_and_lease_poison_scenarios(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            exe=self._build(root)
            plus=self._original_input_arguments(root)
            for case in range(1,27):
                with self.subTest(case=case):
                    run=subprocess.run(["vvp",str(exe),f"+CASE={case}",*plus],
                                       capture_output=True,text=True,timeout=120)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                    self.assertIn(
                        f"M08_5_REAL_BANK_AXI_NEGATIVE_PASS case={case}",
                        run.stdout
                    )
                    self.assertNotIn(MARK,run.stdout)
                    self.assertNotIn("FATAL",run.stdout+run.stderr)


if __name__=="__main__":
    unittest.main()
