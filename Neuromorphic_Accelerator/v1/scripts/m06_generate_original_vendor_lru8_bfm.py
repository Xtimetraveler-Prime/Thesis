#!/usr/bin/env python3
"""Generate a genuine-original AMD SmartConnect + 2048B 8-slot LRU XSim gate.

Tests exact one-slot predecessor ABI, with eight physical 256-byte on-chip
data slots and the new RTL LRU tag/dirty manager under 9+ page capacity
pressure. No real board or PS DDR and NO accepted M05 HLS top instantiated.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from m06_generate_original_mem_sc_bfm import original_ports
from m06_generate_original_paged_vendor_bfm import render_paged


LRU8_BODY = r"""
reg [255:0] expected [0:255];
reg [255:0] edited_payload=
  256'hffeeddccbbaa99887766554433221100_00112233445566778899aabbccddeeff;
reg [31:0] edited_mask=32'h80010001;
integer page,word_no,lane,byte_no;
always @(posedge clk) if(resetn) begin
  if(M00_AXI_wvalid && M00_AXI_wready)
    m00_wbeats<=m00_wbeats+1;
  if(M00_AXI_rvalid && M00_AXI_rready)
    m00_rbeats<=m00_rbeats+1;
end
"""


LRU8_SCENARIO = r"""
task automatic check_cached(input integer blk);
  integer word_no;
  begin
    for(word_no=0;word_no<8;word_no=word_no+1) begin
      @(negedge clk); word_index=word_no;
      @(negedge clk);
      if(word_data !== expected[8*blk+word_no])
        $fatal(1,"M06_VENDOR_LRU8_FAIL BYTE_PARITY block=%0d word=%0d",
               blk,word_no);
    end
  end
endtask
initial begin
  for(word_no=0;word_no<256;word_no=word_no+1) begin
    expected[word_no]=0;
    for(lane=0;lane<32;lane=lane+1)
      expected[word_no][8*lane+:8]=(13*(word_no*32+lane)+17)&255;
  end
  repeat(10) @(negedge clk);resetn=1;
  repeat(30) @(negedge clk);
  for(page=0;page<8;page=page+1) begin
    demand(page,(page==0 || page==1),0);
    if(rsp_slot !== page[2:0])
      $fatal(1,"M06_VENDOR_LRU8_FAIL INITIAL_SLOT_ALLOCATION");
    check_cached(page);
  end
  client_slot=0;word_index=3;
  @(negedge clk);
  if(word_data !== expected[3])
    $fatal(1,"M06_VENDOR_LRU8_FAIL BAD_INITIAL_BLOCK0");
  edit_data=edited_payload;edit_strobe=edited_mask;edit_enable=1;
  @(posedge clk);
  for(lane=0;lane<32;lane=lane+1)
    if(edited_mask[lane])
      expected[3][8*lane+:8]=edited_payload[8*lane+:8];
  @(negedge clk);edit_enable=0;
  if(word_data !== expected[3])
    $fatal(1,"M06_VENDOR_LRU8_FAIL MASKED_EDIT");
  demand(0,1,0); // most-recently-used page0
  demand(8,0,0); // NINTH page: dirty LRU page1 must WB first
  if(rsp_slot !== 1 || wb_acks !== 1 || evictions !== 1)
    $fatal(1,"M06_VENDOR_LRU8_FAIL LRU_DIRTY_VICTIM");
  demand(0,0,0); // hit page0, edited bytes retained
  client_slot=rsp_slot;word_index=3;
  @(negedge clk);
  if(word_data !== expected[3])
    $fatal(1,"M06_VENDOR_LRU8_FAIL HIT_CORRUPTION");
  for(page=9;page<=17;page=page+1) begin
    demand(page,0,0);
    check_cached(page);
  end
  // Page0 has now been evicted AND written back. Its latest bytes must
  // survive reloading through the original S00 and downstream 128b M00.
  demand(0,0,0);
  check_cached(0);
  if(accesses !== 21 || hits !== 2 || misses !== 19 ||
     evictions !== 11 || wb_acks !== 2 || fill_acks !== 19 ||
     axiar !== 152 || axir !== 152 ||
     axiaw !== 16 || axiw !== 16 || axib !== 16 ||
     m00_wbeats < 32 || m00_rbeats < 304)
    $fatal(1,"M06_VENDOR_LRU8_FAIL COUNTS a=%0d h=%0d m=%0d wb=%0d fills=%0d W=%0d R=%0d",
           accesses,hits,misses,wb_acks,fill_acks,m00_wbeats,m00_rbeats);
  $display("M06_ORIGINAL_VENDOR_LRU8_RTL_PASS slots=8 resident_bytes=2048 fills=19 evictions=11 dirty_wb=2 M00_write=%0d M00_read=%0d",
           m00_wbeats,m00_rbeats);
  inject_read_error=1;
  demand(18,0,1);
  if(!poisoned || req_ready || wb_acks !== 2 ||
     fill_acks !== 19 || axiar !== 153)
    $fatal(1,"M06_VENDOR_LRU8_FAIL QUARANTINE");
  $display("M06_ORIGINAL_VENDOR_LRU8_FAULT_PASS NO_REAL_DDR_NO_BOARD");
  $finish;
end
initial begin
  #4000000;
  $fatal(1,"M06_VENDOR_LRU8_FAIL WATCHDOG");
end
endmodule
"""


def render_lru8(ports: list[dict]) -> str:
    old=render_paged(ports)
    marker="reg [255:0] expected [0:255];"
    if old.count(marker)!=1:
        raise ValueError("original AMD vendor paged ABI changed")
    head=old.split(marker,1)[0]
    head=head.replace("module tb_m06_original_vendor_paged;",
                      "module tb_m06_original_vendor_lru8;")
    head=head.replace("reg [2:0] word_index=0;",
                      "reg [2:0] word_index=0,client_slot=0;\n"
                      "wire [2:0] dma_slot,rsp_slot;\n"
                      "wire [31:0] evictions;")
    head=head.replace("m06_residency_control_fsm #(",
                      "m06_residency_lru8 #(")
    head=head.replace("residency (\n.aclk(clk),.aresetn(resetn),",
                      "residency (\n.clk(clk),.resetn(resetn),")
    head=head.replace(".rsp_error(rsp_error),.rsp_block(rsp_block),",
                      ".rsp_error(rsp_error),.rsp_block(rsp_block),"
                      ".rsp_slot(rsp_slot),")
    head=head.replace(".dma_is_writeback(dma_wb),.dma_block(dma_block),",
                      ".dma_is_writeback(dma_wb),.dma_block(dma_block),"
                      ".dma_slot(dma_slot),")
    head=head.replace(".poisoned(poisoned),.resident_valid(resident_valid),"
                      "\n.resident_block(resident_block),.resident_dirty(resident_dirty),",
                      ".poisoned(poisoned),")
    head=head.replace(".accesses(accesses),.hits(hits),.misses(misses),",
                      ".accesses(accesses),.hits(hits),.misses(misses),"
                      ".evictions(evictions),")
    head=head.replace("m06_axi256_block_transfer #(",
                      "m06_axi256_multislot_transfer #(")
    head=head.replace(".cmd_is_writeback(dma_wb),.cmd_block(dma_block),",
                      ".cmd_is_writeback(dma_wb),.cmd_block(dma_block),"
                      ".cmd_slot(dma_slot),")
    head=head.replace(".client_word_index(word_index),.client_word_data(word_data),",
                      ".client_word_index(word_index),"
                      ".client_slot(client_slot),.client_word_data(word_data),")
    start=old.index("task automatic demand(input integer blk,")
    stop=old.index("task automatic check_page(input integer blk)",start)
    demand=old[start:stop]
    demand=demand.replace("@(negedge clk);rsp_ready=0;",
                          "@(negedge clk);rsp_ready=0;\n      client_slot=rsp_slot;")
    if "client_slot=rsp_slot" not in demand:
        raise ValueError("cannot propagate real resident slot on response")
    return head+LRU8_BODY+demand+LRU8_SCENARIO


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original",type=Path,required=True)
    ap.add_argument("--headers",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("new exclusive XSim TB path required")
        ports=original_ports(args.original.resolve(strict=True),
                             json.loads(args.headers.read_text()))
        with args.output.open("x",encoding="utf-8") as stream:
            stream.write(render_lru8(ports))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("M06 original AMD vendor 8-slot BFM GENERATION FAILED: "+str(exc),
              file=sys.stderr)
        return 2
    print("M06 ORIGINAL AMD vendor 8-slot RTL LRU bench generated; "
          "REAL XSIM NOT RUN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
