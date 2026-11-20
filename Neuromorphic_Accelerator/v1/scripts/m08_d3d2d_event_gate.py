#!/usr/bin/env python3
"""M08 D3.D.2D M32E v5 RAW EVENT ingress PC-only source gate. NO BOARD.

Requiring predecessor's original physically verified RTL SHA does not
magically verify the new event-ingress design. Full 32x4 M06 Icarus simulation
is required, followed by new owner Vivado route/DRC/timing and exact-image
review. There is deliberately NO accept/program mode in this source gate.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_gate as predecessor
import m08_d3d2d_event_vectors as oracle

RTL=ROOT/"rtl/m08/m08_d3d2d_raw_event_lif_axil.v"
TB=ROOT/"rtl/m08/tb_m08_d3d2d_raw_event_lif_axil.sv"
VECTORS=ROOT/"scripts/m08_d3d2d_event_vectors.py"
OLD_RTL=ROOT/"rtl/m08/m08_d3d2c_m06_32_lif_axil.v"
OLD_ACCEPTED_RTL_SHA="27b40475d75592d06f45bc5d66205e4a93e1684195c2965031ad32eb4c77ad04"

class Reject(ValueError):
    pass

def require(expr,why):
    if not expr:
        raise Reject(why)

def source()->dict:
    try:
        previous=predecessor.source()
    except (ValueError,predecessor.Reject) as exc:
        raise Reject("original physical D3.D.2C source drift: "+str(exc)) from exc
    require(previous["rtl_sha256"]==OLD_ACCEPTED_RTL_SHA and
            sha256(OLD_RTL.read_bytes()).hexdigest()==OLD_ACCEPTED_RTL_SHA,
            "immutable original owner physical M32N RTL changed")
    rtl,tb,vectors=(p.read_text() for p in (RTL,TB,VECTORS))
    for term in (
        "module m08_d3d2d_raw_event_lif_axil",
        "MAGIC=32'h4D333245", "VERSION=32'h00050000",
        "reg [4:0] event_neuron", "reg [1:0] event_tick",
        "reg signed [31:0] event_current",
        "reg [6:0] event_count",
        "wire signed [32:0] event_sum_ext",
        "wire event_overflow=event_sum_ext[32] != event_sum_ext[31]",
        "currents[event_index] <= event_sum_ext[31:0]",
        "event_count <= event_count + 1'b1",
        "event_count >= 7'd64", "event_count != 0",
        "12'h024", "12'h028", "12'h02C", "12'h030",
        "12'h034", "12'h038", "12'h03C",
        "if (w_data_q != 32'd1 || event_count >= 7'd64 ||",
        "for (i=0;i<128;i=i+1) currents[i] <= 0",
        "12'h030: s_axi_rresp <= SLVERR",
        "12'h038: s_axi_rresp <= SLVERR",
        "reg signed [19:0] syn_accum",
        "syn_accum <= syn_accum + selected_weight",
        "spike_mask[edge_pre[route_slot]][tick - edge_delay[route_slot]]",
        "PHASE_BASE","PHASE_EXT","PHASE_TOTAL","PHASE_COMMIT",
        "trace_voltage[compute_index] <= next_voltage",
        "trace_syn_current[compute_index] <=",
        "reg signed [33:0] total_stage",
        "three_scaled < 0 ? -((-three_scaled) >>> 2)",
    ):
        require(term in rtl,"required on-fabric event/neural semantic absent: "+term)
    for forbidden in (
        "synaptic_sum = synaptic_sum +",
        "wire signed [63:0] total =",
        "UNREVIEWED_M08_D3D2C_OWNER_IMAGE",
    ):
        require(forbidden not in rtl,"old RTL path or stale release reference: "+forbidden)
    for term in (
        "module tb_m08_d3d2d_raw_event_lif_axil",
        "vectors [0:629]", "load_raw_events", "check_fabric_event_sums",
        "M08_D3D2D_REAL_RTL_128_FPGA_EVENT_BUCKET_SUMS_PASS",
        "M08_D3D2D_M06_32X4_REAL_RTL_EVENT_PARITY_PASS",
        "M08_D3D2D_FULL_128_BUCKET_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_RTL_PASS",
        "vectors[579+3*ix]", "vectors[580+3*ix]",
        "vectors[581+3*ix]",
        "write_reg(12'h030,1,4'hF,2'b00)",
        "write_reg(12'h030,1,4'hF,2'b10)",
        "write_reg(12'h038,1,4'hF,2'b00)",
        "32'h4D333245", "32'h00050000",
    ):
        require(term in tb,"real AXI 17-event bench contract absent: "+term)
    require(oracle.WORDS==630 and len(oracle.words())==630,
            "original M06 630-word raw events/drift or M02/M03 mismatch")
    require("out.extend((m06.u32(ev.neuron),m06.u32(ev.tick),m06.u32(ev.current)))" in vectors,
            "oracle must contain actual individual M06 events; no host sum")
    for forbidden in ("open_hw_manager","program_hw_devices","run_hw_axi",
                      "connect_hw_server","/dev/mem","/dev/uio","ssh ","xmutil "):
        require(not any(forbidden in t for t in (rtl,tb,vectors)),
                "PC source contains forbidden hardware access "+forbidden)
    return dict(
        status="M08_D3D2D_RAW_17_EVENT_INGRESS_SOURCE_READY_PC_ONLY",
        original_d3d2c_physical_scope="OWNER_AUDITED_384_NEURAL_VALUES",
        original_d3d2c_image_reused=False,
        hardware_event_aggregation_in_rtl=True,
        raw_event_count=17, neurons=32, logical_ticks=4, synapses=5,
        event_transport="JTAG_AXI_LITE_MAILBOX_NOT_STREAM_DMA",
        original_m05_hls_physical=False, physical_ddr=False,
        new_native_image_reviewed=False, physical_programmed=False,
        raw_event_ingress_physically_verified=False,
        rtl_sha256=sha256(RTL.read_bytes()).hexdigest(),
        bench_sha256=sha256(TB.read_bytes()).hexdigest(),
        vector_source_sha256=sha256(VECTORS.read_bytes()).hexdigest())

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only",action="store_true",required=True)
    parser.parse_args()
    try:
        print(json.dumps(source(),sort_keys=True,indent=2))
        return 0
    except (OSError,Reject,ValueError,AssertionError,KeyError) as exc:
        print("M08_D3D2D_PC_SOURCE_REJECTED: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
