"""M06 source-only safety regressions for the NEW Vitis paged HLS tool gate.

Every Verilog snippet here is SYNTHETIC; no generated RTL/vendor simulation
claim may arise from these port-contract parser tests.
"""
from __future__ import annotations
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"hls/m06_paged_rolling"))
from m06_paged_hls_port_audit import parse_top,REQUIRED,RDP,WRP
from prepare_hls_config import prepare


def synthetic_module() -> str:
    required=REQUIRED.copy()
    required.update({
        "neurons_TDATA":"input","neurons_TVALID":"input",
        "neurons_TREADY":"output",
        "synapses_TDATA":"input","synapses_TVALID":"input",
        "synapses_TREADY":"output",
        "external_events_TDATA":"input",
        "external_events_TVALID":"input",
        "external_events_TREADY":"output",
        "trace_TDATA":"output","trace_TVALID":"output",
        "trace_TREADY":"input",
        "metrics_TDATA":"output","metrics_TVALID":"output",
        "metrics_TREADY":"input",
    })
    header="module m06_paged_rolling_replay ("+", ".join(required)+");"
    declaration=["parameter BUS_WIDTH = 32;"]
    for name,direction in required.items():
        if name.endswith(("ADDR","RDATA","WDATA","TDATA")):
            decl=f"  {direction} wire [BUS_WIDTH-1:0] {name};"
        else:
            decl=f"  {direction} wire {name};"
        declaration.append(decl)
    return "\n".join((header,*declaration,"endmodule",""))


class M06RealHLSGenerationSafetyTests(unittest.TestCase):
    def test_source_has_bounded_4096_canonical_and_two_axi_master_roles(self):
        code=(ROOT/"hls/m06_paged_rolling/m06_paged_rolling.cpp").read_text()
        h=(ROOT/"hls/m06_paged_rolling/m06_paged_rolling.hpp").read_text()
        self.assertIn("m06_paged_rolling_replay(",code)
        self.assertIn("m05_rolling_replay",h)
        self.assertIn("M06_PAGED_MAX_LOGICAL_NEURONS = 4096",h)
        self.assertIn("M06_PAGED_MAX_SLOTS = 8",h)
        self.assertIn("m_axi port=canonical_read_words",code)
        self.assertIn("m_axi port=canonical_write_words",code)
        self.assertIn("bundle=gmem_read",code)
        self.assertIn("bundle=gmem_write",code)
        self.assertIn("m06_ensure_page(",code)
        self.assertNotIn("static std::int16_t voltage[",code)
        self.assertNotIn("static std::int16_t tick_voltage[",code)
        self.assertIn("m04_eval_one(request, response)",code)
        self.assertIn("canonical_first_neuron%16!=0",code)
        self.assertIn("page_words[pslot][row+1]=t+1",code)
        self.assertIn("metrics.write(page_metrics)",code)
        self.assertNotIn("program_hw_devices",code)

    def test_synthetic_module_parameter_widths_are_parsed_without_fake_vendor_claim(self):
        ports=parse_top(synthetic_module())
        self.assertEqual(ports[RDP+"RDATA"],("input",32))
        self.assertEqual(ports[WRP+"WDATA"],("output",32))
        self.assertEqual(ports[RDP+"ARADDR"],("output",32))
        self.assertEqual(ports[WRP+"AWADDR"],("output",32))
        self.assertEqual(len(ports),len(REQUIRED)+15)

    def test_wrong_synthetic_module_duplicate_or_invalid_parameter_rejected(self):
        base=synthetic_module()
        with self.assertRaisesRegex(ValueError,"exactly one"):
            parse_top(base.replace("m06_paged_rolling_replay","other_top"))
        with self.assertRaisesRegex(ValueError,"duplicate"):
            parse_top(base.replace("ap_clk,","ap_clk, ap_clk,"))
        with self.assertRaisesRegex(ValueError,"parameter"):
            parse_top(base.replace("BUS_WIDTH = 32;","BUS_WIDTH = BAD_PARAMETER;"))

    def test_effective_vitis_configuration_is_abs_and_exclusive(self):
        template=ROOT/"hls/m06_paged_rolling/m06_paged_rolling_hls_config.cfg"
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"effective.cfg"
            result=prepare(ROOT,template,out,"m06_paged_rolling_replay")
            self.assertEqual(result["top"],"m06_paged_rolling_replay")
            text=out.read_text()
            self.assertIn("syn.top=m06_paged_rolling_replay",text)
            self.assertIn(str(ROOT/"hls/m06_paged_rolling/m06_paged_rolling.cpp"),text)
            self.assertIn(str(ROOT/"hls/m04_lif_eval/m04_eval.cpp"),text)
            self.assertIn("part=xck26-sfvc784-2LV-c",text)
            with self.assertRaises(FileExistsError):
                prepare(ROOT,template,out,"m06_paged_rolling_replay")
            with self.assertRaisesRegex(ValueError,"unknown HLS top"):
                prepare(ROOT,template,Path(d)/"other.cfg","m05_rolling_replay")

    def test_vitis_runner_is_syntactically_valid_and_readonly_sources(self):
        runner=ROOT/"scripts/run_m06_paged_rolling_hls.sh"
        out=subprocess.run(["bash","-n",str(runner)],text=True,
                           capture_output=True)
        self.assertEqual(out.returncode,0,out.stderr)
        code=runner.read_text()
        self.assertIn("vitis-run --mode hls --csim",code)
        self.assertIn("v++ -c --mode hls",code)
        self.assertIn("vitis-run --mode hls --cosim",code)
        self.assertIn("source_before_sha256.txt",code)
        self.assertIn("source_after_sha256.txt",code)
        self.assertIn("m06_paged_rolling_hls_",code)
        self.assertNotIn("open_hw_manager",code)
        self.assertNotIn("program_hw_devices",code)
        self.assertNotIn("generate_target",code)
        self.assertNotIn("vitis-run --mode hls --impl",code)


if __name__=="__main__":
    unittest.main()
