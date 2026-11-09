#!/usr/bin/env python3
"""Original AMD SmartConnect + paged LIF16 numerical RTL experiment.

Uses the exact authenticated original AMD 96-port vendor wrapper and our
already independently verified M06 resident-page RTL + M02 neural arithmetic.
The original M05 HLS event top is NOT instantiated here; a separate M06
native adapter exercises ORIGINAL m05_stream_eval on paged state.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from m06_generate_original_mem_sc_bfm import original_ports
from m06_generate_original_paged_vendor_bfm import render_paged


NEURAL_DECLS = r"""
reg signed [15:0] initial_v [0:31];
reg signed [15:0] neuron_bias [0:31];
reg signed [15:0] neuron_threshold [0:31];
reg signed [15:0] neuron_reset [0:31];
reg signed [31:0] routed_current [0:127];
reg signed [15:0] oracle_v [0:127];
reg oracle_spike [0:127];
reg signed [15:0] lif_previous=0,lif_bias=0,lif_threshold=1,lif_reset=0;
reg signed [31:0] lif_current=0;
wire signed [15:0] lif_next;
wire lif_spike,lif_invalid;
m06_lif16_neuron_step neural_lane (
  .previous_voltage(lif_previous),.bias(lif_bias),
  .threshold(lif_threshold),.reset_voltage(lif_reset),
  .summed_current(lif_current),
  .decay_num(32'd3),.decay_den(32'd4),
  .next_voltage(lif_next),.spike(lif_spike),
  .invalid_params(lif_invalid)
);
reg [255:0] expected_state [0:15];
reg [255:0] edited_word=0;
reg [31:0] edited_mask=0;
integer tick_no,neuron,word_no,byte_off,init_word,byte_lane;
integer neural_updates=0,neural_spikes=0;
always @(posedge clk) if(resetn) begin
  if(M00_AXI_wvalid && M00_AXI_wready)
    m00_wbeats<=m00_wbeats+1;
  if(M00_AXI_rvalid && M00_AXI_rready)
    m00_rbeats<=m00_rbeats+1;
end
"""


NEURAL_MAIN = r"""
task automatic check_resident(input integer blk);
  integer index;
  begin
    if(!resident_valid || resident_block !== blk || poisoned)
      $fatal(1,"M06_VENDOR_NEURAL_FAIL WRONG_RESIDENT_TAG");
    for(index=0;index<8;index=index+1) begin
      @(negedge clk); word_index=index;
      @(negedge clk);
      if(word_data !== expected_state[blk*8+index])
        $fatal(1,"M06_VENDOR_NEURAL_FAIL PAGE_RELOAD_PARITY blk=%0d word=%0d",
               blk,index);
    end
  end
endtask
initial begin
  load_m06_lif_vectors();
  for(init_word=0;init_word<16;init_word=init_word+1)
    expected_state[init_word]=0;
  for(neuron=0;neuron<32;neuron=neuron+1) begin
    init_word=neuron/2;
    byte_off=(neuron%2)*16;
    expected_state[init_word][8*byte_off+:16]=initial_v[neuron];
  end
  // Simulation-only canonical seeding at t=1ns, before reset release.
  // Subsequent state loads and writebacks MUST traverse the original
  // AMD SmartConnect, not direct hierarchical access to ram.mem.
  #1;
  for(init_word=0;init_word<16;init_word=init_word+1)
    for(byte_lane=0;byte_lane<32;byte_lane=byte_lane+1)
      ram.mem[init_word*32+byte_lane] =
          expected_state[init_word][8*byte_lane+:8];
  repeat(10) @(negedge clk); resetn=1;
  repeat(30) @(negedge clk);
  for(tick_no=0;tick_no<4;tick_no=tick_no+1) begin
    for(neuron=0;neuron<32;neuron=neuron+1) begin
      if(neuron%16==0)
        demand(neuron/16,1,0);
      word_index=(neuron%16)/2;
      byte_off=(neuron%2)*16;
      @(negedge clk);
      lif_previous=$signed(word_data[8*byte_off+:16]);
      lif_bias=neuron_bias[neuron];
      lif_threshold=neuron_threshold[neuron];
      lif_reset=neuron_reset[neuron];
      lif_current=routed_current[tick_no*32+neuron];
      if(word_data[8*(byte_off+2)+:32] !== tick_no)
        $fatal(1,"M06_VENDOR_NEURAL_FAIL LOST_TIME_METADATA t=%0d n=%0d",
               tick_no,neuron);
      #1;
      if(lif_invalid || lif_next !== oracle_v[tick_no*32+neuron] ||
         lif_spike !== oracle_spike[tick_no*32+neuron])
        $fatal(1,"M06_VENDOR_NEURAL_FAIL M02_NUMERIC_PARITY t=%0d n=%0d",
               tick_no,neuron);
      neural_updates=neural_updates+1;
      neural_spikes=neural_spikes+lif_spike;
      edited_word=0; edited_mask=0;
      edited_word[8*byte_off+:16]=lif_next;
      edited_word[8*(byte_off+2)+:32]=tick_no+1;
      for(byte_lane=0;byte_lane<6;byte_lane=byte_lane+1)
        edited_mask[byte_off+byte_lane]=1;
      @(negedge clk);
      edit_data=edited_word;
      edit_strobe=edited_mask;
      edit_enable=1;
      @(posedge clk);
      @(negedge clk); edit_enable=0;
      expected_state[neuron/2][8*byte_off+:16]=
          oracle_v[tick_no*32+neuron];
      expected_state[neuron/2][8*(byte_off+2)+:32]=tick_no+1;
      if(word_data !== expected_state[neuron/2])
        $fatal(1,"M06_VENDOR_NEURAL_FAIL RECORD_BYTE_PARITY t=%0d n=%0d",
               tick_no,neuron);
    end
  end
  demand(0,0,0);check_resident(0);
  demand(1,0,0);check_resident(1);
  demand(1,0,0);
  if(neural_updates !== 128 || neural_spikes !== 8 ||
     accesses !== 11 || hits !== 1 || misses !== 10 ||
     wb_acks !== 8 || fill_acks !== 10 ||
     axiar !== 80 || axir !== 80 ||
     axiaw !== 64 || axiw !== 64 || axib !== 64 ||
     m00_rbeats < 160 || m00_wbeats < 128)
    $fatal(1,"M06_VENDOR_NEURAL_FAIL TRANSFER_OR_NEURAL_COUNTS");
  $display("M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS neurons=32 ticks=4 updates=%0d spikes=%0d fills=10 wb=8 M00_write=%0d M00_read=%0d ORIGINAL_M05_HLS_NOT_INSTANTIATED",
           neural_updates,neural_spikes,m00_wbeats,m00_rbeats);
  inject_read_error=1;
  demand(2,0,1);
  if(!poisoned || req_ready || fill_acks !== 10 || wb_acks !== 8)
    $fatal(1,"M06_VENDOR_NEURAL_FAIL ERROR_NOT_QUARANTINED");
  $display("M06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS NO_REAL_DDR_NO_BOARD");
  $finish;
end
initial begin
  #2000000;
  $fatal(1,"M06_VENDOR_NEURAL_FAIL WATCHDOG");
end
endmodule
"""


def render_neural_paged(ports: list[dict]) -> str:
    prior=render_paged(ports)
    marker="reg [255:0] expected [0:255];"
    if prior.count(marker)!=1:
        raise ValueError("original vendor paged testbench ABI changed")
    head=prior.split(marker,1)[0].replace(
        "module tb_m06_original_vendor_paged;",
        "module tb_m06_original_vendor_neural_paged;")
    start=prior.index("task automatic demand(input integer blk,")
    stop=prior.index("task automatic check_page(input integer blk)",start)
    one_task=prior[start:stop]
    include=chr(96)+'include "m06_lif16_vectors.vh"\n'
    return head+NEURAL_DECLS+include+one_task+NEURAL_MAIN


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--headers",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("exclusive output in existing evidence directory required")
        ports=original_ports(
            a.original.resolve(strict=True),
            json.loads(a.headers.read_text(encoding="utf-8")))
        with a.output.open("x",encoding="utf-8") as fp:
            fp.write(render_neural_paged(ports))
    except (OSError,ValueError,KeyError,TypeError) as error:
        print("M06 original vendor neural BFM GENERATION FAILED: "+str(error),
              file=sys.stderr)
        return 2
    print("M06 original vendor + M02 neural RTL paging TB GENERATED; "
          "REAL VENDOR XSIM NOT RUN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
