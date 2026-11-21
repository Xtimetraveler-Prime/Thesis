#!/usr/bin/env python3
"""M08.4 new page-neural source boundary; PC only, not K26 release.

Refuses changed original signed16/4-tick M06 input oracle geometry and
incomplete source of a real host/compute SRAM bridge with recurrent LIF.
Functional confidence comes from separate REAL iverilog/vvp tests.
This gate NEVER authorizes a native image or physical JTAG programming.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as fixture

SRCS={
    "shell": ROOT/"rtl/m08/m08_paged_m06_lif_shell.v",
    "lif": ROOT/"rtl/m08/m08_paged_m06_lif_engine.v",
    "axi": ROOT/"rtl/m08/m08_axil_page_control.sv",
    "bank": ROOT/"rtl/m08/m08_host_staged_page_bank.sv",
    "rtl_positive": ROOT/"rtl/m08/tb_m08_paged_m06_lif.sv",
    "rtl_negative": ROOT/"rtl/m08/tb_m08_paged_m06_lif_fail_closed.sv",
    "independent_fixture": ROOT/"scripts/m08_paged_m06_lif_fixture.py",
}

class Reject(ValueError): pass

def require(ok, message):
    if not ok: raise Reject(message)

def inspect():
    texts={name:path.read_text(encoding="utf-8") for name,path in SRCS.items()}
    require(all(len(t)>300 for t in texts.values()),"missing complete real paged neural source")
    _,net,ev,ext,volts,masks,syn=fixture.source()
    golden=fixture.golden_words()
    require(len(net.neurons)==32 and len(net.synapses)==5 and
            len(ev)==17 and len(golden)==512 and
            [fixture.neurons_in_page(n) for n in range(6)]==[6,6,6,6,6,2],
            "original M02/M03 M06 page geometry drift")
    core=texts["lif"]
    for term in ("module m08_paged_m06_lif_engine", "global_spikes",
                 "edge_configured","three_scaled","syn_sum","exact_total",
                 "computed_synaptic_events","K_EDGE_VALIDATE","K_WRITE_SYN",
                 "state<=S_FAULT"):
        require(term in core,"real neural/state/routing invariant absent: "+term)
    wrapper=texts["shell"]
    require("module m08_paged_m06_lif_shell" in wrapper and
            "m08_paged_m06_lif_engine neural_engine" in wrapper and
            "m08_axil_page_control #(.ENABLE_COMPUTE(1'b1))" in wrapper,
            "neural compute port not genuinely wired to safe AXIL host bank")
    for name in ("awaddr","awprot","awvalid","awready","wdata","wstrb",
                 "wvalid","wready","bresp","bvalid","bready","araddr",
                 "arprot","arvalid","arready","rdata","rresp","rvalid","rready"):
        require(f".s_axi_{name}(s_axi_{name})" in wrapper,
                "unbound AXI4-Lite host-page pin "+name)
    require("512_REAL_IVERILOG_PARITY_NO_K26_NO_DDR_NO_RAW_FIFO_PASS" in
            texts["rtl_positive"],"missing real 512-value RTL assertion marker")
    require("M08_PAGED_LIF_FAIL_CLOSED_REAL_RTL_CASE_PASS" in
            texts["rtl_negative"],"missing real negative RTL quarantine markers")
    for forbidden in ("program_hw_devices","open_hw_manager","connect_hw_server",
                      "run_hw_axi","/dev/mem","xmutil ","write_bitstream",
                      "dma_alloc_coherent"):
        require(all(forbidden not in v for v in texts.values()),
                "forbidden board/native programming from source asset "+forbidden)
    return {
        "status":"M08_4_PAGED_SIGNED16_32x4_M06_SOURCE_CANDIDATE_NO_BOARD",
        "logical_neural_pages":6,
        "resident_neural_pages":1,
        "physical_KV260_page_neural_execution":False,
        "original_m06_neurons":32,
        "original_m06_ticks":4,
        "original_m06_recurrent_edges":5,
        "input_events_host_coalesced":17,
        "independently_required_numerical_results":512,
        "source_sha256":{n:sha256(p.read_bytes()).hexdigest() for n,p in SRCS.items()},
        "new_vivado_image_currently_accepted":False,
        "owner_bitstream_release_allowed":False,
        "physical_ddr":False,
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-only",action="store_true",required=True)
    ap.parse_args()
    try:
        print(json.dumps(inspect(),indent=2,sort_keys=True))
        return 0
    except (Reject,ValueError,OSError,AssertionError) as exc:
        print("M08_4_PAGED_NEURAL_SOURCE_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
