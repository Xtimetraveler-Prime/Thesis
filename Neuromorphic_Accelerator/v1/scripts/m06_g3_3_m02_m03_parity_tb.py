#!/usr/bin/env python3
"""Prospective genuine generated-HLS/original-AMD G3.3 full M02/M03 parity XSim.

Original Vitis RTL + AMD DWC/SmartConnect unchanged. Source-only generation
and fake-stub syntax CI do not constitute original XSim or physical DDR.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

from m06_g3_3_positive16_axilite_tb import positive_tb

ANCHOR="integer ctrl_b_count=0, ctrl_r_count=0;"
INPUTS=(("h_synapses_TDATA",192),("h_synapses_TVALID",1),
        ("h_external_events_TDATA",128),("h_external_events_TVALID",1))

def parity_tb(idle: str, inventory: dict, control: dict) -> str:
    s=positive_tb(idle,inventory,control)
    if s.count(ANCHOR)!=1:
        raise ValueError("original positive16 controller anchor drift")
    s=s[:s.index(ANCHOR)]
    old="module tb_m06_g3_3_actual_hls_original_amd_positive16;"
    if s.count(old)!=1:
        raise ValueError("original positive16 module drift")
    s=s.replace(old,
        "module tb_m06_g3_3_actual_hls_original_amd_parity32;\n"
        '  `include "m06_g3_3_m02_m03_owner_vectors.svh"')
    for name,width in INPUTS:
        dim=f"[{width-1}:0] " if width>1 else ""
        original=f"wire {dim}{name};"
        assign=f"assign {name} = {width}'d0; // IDLE: no start/inputs\n"
        if s.count(original)!=1 or s.count(assign)!=1:
            raise ValueError("original HLS stream ABI/tieoff drift: "+name)
        s=s.replace(original,f"reg {dim}{name}=0;")
        s=s.replace(assign,"")
    regs=control["register_offsets"]
    wanted=("AP_CTRL","CANONICAL_READ_WORDS_DATA_0","CANONICAL_READ_WORDS_DATA_1",
            "CANONICAL_WRITE_WORDS_DATA_0","CANONICAL_WRITE_WORDS_DATA_1",
            "NEURON_COUNT_DATA_0","SYNAPSE_COUNT_DATA_0",
            "EXTERNAL_COUNT_DATA_0","TICKS_DATA_0","DECAY_NUM_DATA_0",
            "DECAY_DEN_DATA_0","RESIDENT_SLOTS_DATA_0",
            "CANONICAL_FIRST_NEURON_DATA_0")
    offsets={key:"7'h"+format(regs[key],"02x") for key in wanted}
    offsets["AP_RETURN"]="7'h"+format(control["ap_return"],"02x")
    tail=r"""
integer ctrl_b_count=0, ctrl_r_count=0;
integer trace_count=0, metrics_count=0;
integer read_ar_count=0, write_aw_count=0, write_b_count=0;
integer inflight_writes=0;
integer polls=0, i=0, b=0, base=0;
reg [31:0] observed_ctrl=0, observed_status=32'hffffffff;

task automatic write_reg(input [6:0] addr,input [31:0] value);
begin
    @(negedge clk);
    h_s_axi_control_AWADDR=addr; h_s_axi_control_AWVALID=1;
    h_s_axi_control_WDATA=value; h_s_axi_control_WSTRB=4'hf;
    h_s_axi_control_WVALID=1;
    fork
        begin
            @(posedge clk);
            while(h_s_axi_control_AWREADY !== 1'b1) @(posedge clk);
            @(negedge clk); h_s_axi_control_AWVALID=0;
        end
        begin
            @(posedge clk);
            while(h_s_axi_control_WREADY !== 1'b1) @(posedge clk);
            @(negedge clk); h_s_axi_control_WVALID=0;
        end
    join
    @(posedge clk);
    while(h_s_axi_control_BVALID !== 1'b1) @(posedge clk);
    if(h_s_axi_control_BRESP !== 2'b00)
        $fatal(1,"M06_G3_3_PARITY_FAIL AXILITE_BRESP addr=%h",addr);
    @(negedge clk); h_s_axi_control_BREADY=1;
    @(posedge clk); @(negedge clk); h_s_axi_control_BREADY=0;
    ctrl_b_count=ctrl_b_count+1;
end
endtask
task automatic read_reg(input [6:0] addr,output [31:0] value);
begin
    @(negedge clk); h_s_axi_control_ARADDR=addr; h_s_axi_control_ARVALID=1;
    @(posedge clk);
    while(h_s_axi_control_ARREADY !== 1'b1) @(posedge clk);
    @(negedge clk); h_s_axi_control_ARVALID=0;
    @(posedge clk);
    while(h_s_axi_control_RVALID !== 1'b1) @(posedge clk);
    if(h_s_axi_control_RRESP !== 2'b00)
        $fatal(1,"M06_G3_3_PARITY_FAIL AXILITE_RRESP addr=%h",addr);
    value=h_s_axi_control_RDATA;
    @(negedge clk); h_s_axi_control_RREADY=1;
    @(posedge clk); @(negedge clk); h_s_axi_control_RREADY=0;
    ctrl_r_count=ctrl_r_count+1;
end
endtask
task automatic feed_neurons;
integer n;
begin
    for(n=0;n<32;n=n+1) begin
        @(negedge clk);
        h_neurons_TDATA=oracle_neurons[n]; h_neurons_TVALID=1;
        @(posedge clk);
        while(h_neurons_TREADY !== 1'b1) @(posedge clk);
        @(negedge clk); h_neurons_TVALID=0;
    end
end
endtask
task automatic feed_synapses;
integer n;
begin
    for(n=0;n<5;n=n+1) begin
        @(negedge clk);
        h_synapses_TDATA=oracle_synapses[n]; h_synapses_TVALID=1;
        @(posedge clk);
        while(h_synapses_TREADY !== 1'b1) @(posedge clk);
        @(negedge clk); h_synapses_TVALID=0;
    end
end
endtask
task automatic feed_external;
integer n;
begin
    for(n=0;n<17;n=n+1) begin
        @(negedge clk);
        h_external_events_TDATA=oracle_external[n]; h_external_events_TVALID=1;
        @(posedge clk);
        while(h_external_events_TREADY !== 1'b1) @(posedge clk);
        @(negedge clk); h_external_events_TVALID=0;
    end
end
endtask

// Original-HLS trace: SIX real fields compared to independent M02/M03.
// Only C ABI padding [159:144] is ignored. Fail on first mismatch.
always @(posedge clk) if(resetn) begin
    if(h_trace_TVALID && h_trace_TREADY) begin
        if(trace_count>=128)
            $fatal(1,"M06_G3_3_PARITY_FAIL TRACE_OVERFLOW");
        if(h_trace_TDATA[63:0]!==oracle_trace[trace_count][63:0] ||
           h_trace_TDATA[95:64]!==oracle_trace[trace_count][95:64] ||
           h_trace_TDATA[127:96]!==oracle_trace[trace_count][127:96] ||
           h_trace_TDATA[135:128]!==oracle_trace[trace_count][135:128] ||
           h_trace_TDATA[143:136]!==oracle_trace[trace_count][143:136] ||
           h_trace_TDATA[191:160]!==oracle_trace[trace_count][191:160])
            $fatal(1,"M06_G3_3_PARITY_FAIL TRACE tick=%0d neuron=%0d got=%h expected=%h",
                   trace_count/32,trace_count%32,
                   h_trace_TDATA,oracle_trace[trace_count]);
        trace_count=trace_count+1;
    end
    if(h_metrics_TVALID && h_metrics_TREADY) begin
        if(metrics_count>=1 || h_metrics_TDATA!==oracle_metrics)
            $fatal(1,"M06_G3_3_PARITY_FAIL METRICS got=%h expected=%h",
                   h_metrics_TDATA,oracle_metrics);
        metrics_count=metrics_count+1;
    end
    if(h_m_axi_gmem_write_AWVALID && h_m_axi_gmem_write_AWREADY) begin
        write_aw_count=write_aw_count+1;
        inflight_writes=inflight_writes+1;
    end
    if(h_m_axi_gmem_write_BVALID && h_m_axi_gmem_write_BREADY) begin
        write_b_count=write_b_count+1;
        inflight_writes=inflight_writes-1;
        if(inflight_writes<0)
            $fatal(1,"M06_G3_3_PARITY_FAIL UNMATCHED_WRITE_B");
    end
    if(h_m_axi_gmem_read_ARVALID && h_m_axi_gmem_read_ARREADY) begin
        read_ar_count=read_ar_count+1;
        if(inflight_writes!=0)
            $fatal(1,"M06_G3_3_PARITY_FAIL READ_AR_BEFORE_WRITE_B inflight=%0d",
                   inflight_writes);
    end
end
initial begin
    repeat(12) @(negedge clk); resetn=1;
    repeat(30) @(negedge clk);
    fork
        feed_neurons();
        feed_synapses();
        feed_external();
        begin
            write_reg(@CANONICAL_READ_WORDS_DATA_0@,32'd0);
            write_reg(@CANONICAL_READ_WORDS_DATA_1@,32'd0);
            write_reg(@CANONICAL_WRITE_WORDS_DATA_0@,32'd0);
            write_reg(@CANONICAL_WRITE_WORDS_DATA_1@,32'd0);
            write_reg(@NEURON_COUNT_DATA_0@,32'd32);
            write_reg(@SYNAPSE_COUNT_DATA_0@,32'd5);
            write_reg(@EXTERNAL_COUNT_DATA_0@,32'd17);
            write_reg(@TICKS_DATA_0@,32'd4);
            write_reg(@DECAY_NUM_DATA_0@,32'd3);
            write_reg(@DECAY_DEN_DATA_0@,32'd4);
            write_reg(@RESIDENT_SLOTS_DATA_0@,32'd1);
            write_reg(@CANONICAL_FIRST_NEURON_DATA_0@,32'd4064);
            write_reg(@AP_CTRL@,32'd1);
            while(observed_ctrl[1] !== 1'b1 && polls < 20000) begin
                repeat(50) @(negedge clk);
                read_reg(@AP_CTRL@,observed_ctrl);
                polls=polls+1;
            end
            if(observed_ctrl[1] !== 1'b1)
                $fatal(1,"M06_G3_3_PARITY_FAIL AP_DONE_TIMEOUT");
            read_reg(@AP_RETURN@,observed_status);
        end
    join
    repeat(10) @(negedge clk);
    if(observed_status!==32'd0 || ctrl_b_count!==13)
        $fatal(1,"M06_G3_3_PARITY_FAIL STATUS=%h CTRL_B=%0d",
               observed_status,ctrl_b_count);
    if(trace_count!==128 || metrics_count!==1 ||
       read_ar_count<1 || write_aw_count<1 ||
       write_b_count!==write_aw_count || inflight_writes!==0)
        $fatal(1,"M06_G3_3_PARITY_FAIL IO trace=%0d metrics=%0d AR=%0d AW=%0d B=%0d",
               trace_count,metrics_count,read_ar_count,
               write_aw_count,write_b_count);
    for(i=0;i<32;i=i+1) begin
        base=(4064+i)*16;
        for(b=0;b<16;b=b+1)
            if(ram.mem[base+b]!==oracle_final_row[i][b*8+:8])
                $fatal(1,"M06_G3_3_PARITY_FAIL CANONICAL_STATE neuron=%0d byte=%0d got=%h expected=%h",
                       i,b,ram.mem[base+b],oracle_final_row[i][b*8+:8]);
    end
    if(ram.mem[0]!==8'h11 || ram.mem[65023]!==8'h04)
        $fatal(1,"M06_G3_3_PARITY_FAIL MEMORY_BOUNDARY");
    if(read_guard_fault || write_guard_fault)
        $fatal(1,"M06_G3_3_PARITY_FAIL ADDRESS_GUARD");
    $display("M06_G3_3_ACTUAL_HLS_AMD_M02_M03_TRACE_STATE_PARITY_XSIM_PASS 32_NEURONS 4_TICKS 1_CACHE_SLOT HIGH_ADDR DIRTY_EVICT B_BEFORE_AR NO_DDR_NO_BOARD");
    $finish;
end
initial begin
    #50000000;
    $fatal(1,"M06_G3_3_PARITY_FAIL GLOBAL_WATCHDOG");
end
endmodule
"""
    for name,value in offsets.items():
        tail=tail.replace("@"+name+"@",value)
    if re.search(r"@[A-Z][A-Z0-9_]*@",tail):
        raise ValueError("unresolved original HLS AXI-Lite register")
    return s+tail

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--idle-tb",required=True,type=Path)
    ap.add_argument("--accepted-inventory",required=True,type=Path)
    ap.add_argument("--control-map",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("parity TB must be NEW in existing evidence directory")
        s=parity_tb(a.idle_tb.read_text(),
                    json.loads(a.accepted_inventory.read_text()),
                    json.loads(a.control_map.read_text()))
        a.output.write_text(s)
    except (ValueError,KeyError,OSError) as error:
        print("M06_G3_3_PARITY_TB_REJECTED:",error,file=sys.stderr)
        return 2
    print("M06_G3_3_M02_M03_PARITY_TB_GENERATED SOURCE_ONLY_NO_XSIM_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
