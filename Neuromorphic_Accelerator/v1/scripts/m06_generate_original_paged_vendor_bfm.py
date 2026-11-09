#!/usr/bin/env python3
"""Generate actual vendor SmartConnect + paged RTL BFM from authenticated D3.

The testbench runs the REAL original-generated AMD memory-IP model, the
synthesizable M06 residency FSM, the actual 8x256b block mover, and
independent 128b scratch RAM. Generation is NOT an XSim result.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from m06_generate_original_mem_sc_bfm import (
    MODULE, READ, WRITE, original_ports, required_ports,
)


def render_paged(ports: list[dict]) -> str:
    expected = required_ports()
    result = [
        "// M06 generated ORIGINAL AMD vendor-paged RTL transaction TB.",
        "// Real vendor module is provided externally from immutable D3.",
        "// All addresses refer to simulation scratch bytes; NO BOARD/DDR.",
        chr(96)+"timescale 1ns/1ps",
        "module tb_m06_original_vendor_paged;",
        "reg clk=0; always #5 clk=~clk;",
        "reg resetn=0;",
    ]
    for row in ports:
        name=row["name"]
        original_direction,width=expected[name]
        tied_off=(original_direction=="input" and
                  name.startswith(("S01_AXI_","S02_AXI_")))
        kind="reg" if tied_off else "wire"
        dims=f"[{width-1}:0] " if width>1 else ""
        result.append(f"{kind} {dims}{name}"+("=0;" if tied_off else ";"))
    result.extend([
        MODULE+" dut (.aclk(clk),.aresetn(resetn),",
        ",\n".join(f".{p['name']}({p['name']})" for p in ports)+");",
        "reg req_valid=0,req_is_write=0,rsp_ready=0;",
        "reg [31:0] req_block=0;",
        "wire req_ready,rsp_valid,rsp_error,poisoned;",
        "wire [31:0] rsp_block;",
        "wire dma_valid,dma_ready,dma_wb,dma_done,dma_error;",
        "wire [31:0] dma_block;",
        "wire resident_valid,resident_dirty;",
        "wire [31:0] resident_block;",
        "wire [31:0] accesses,hits,misses,wb_acks,fill_acks,stall_cycles;",
        "wire [31:0] axiar,axir,axiaw,axiw,axib,axi_stalls;",
        "reg [2:0] word_index=0;",
        "reg edit_enable=0;",
        "reg [255:0] edit_data=0;",
        "reg [31:0] edit_strobe=0;",
        "wire [255:0] word_data;",
        "wire mover_busy;",
        "reg inject_read_error=0;",
        "integer m00_wbeats=0,m00_rbeats=0;",
        "m06_residency_control_fsm #(.MAX_WAIT_CYCLES(32'd4096)) residency (",
        ".aclk(clk),.aresetn(resetn),",
        ".req_valid(req_valid),.req_ready(req_ready),",
        ".req_block(req_block),.req_is_write(req_is_write),",
        ".rsp_valid(rsp_valid),.rsp_ready(rsp_ready),",
        ".rsp_error(rsp_error),.rsp_block(rsp_block),",
        ".dma_valid(dma_valid),.dma_ready(dma_ready),",
        ".dma_is_writeback(dma_wb),.dma_block(dma_block),",
        ".dma_done(dma_done),.dma_error(dma_error),",
        ".poisoned(poisoned),.resident_valid(resident_valid),",
        ".resident_block(resident_block),.resident_dirty(resident_dirty),",
        ".accesses(accesses),.hits(hits),.misses(misses),",
        ".acknowledged_writebacks(wb_acks),",
        ".acknowledged_fills(fill_acks),.stalled_cycles(stall_cycles));",
        "m06_axi256_block_transfer #(.MAX_BLOCKS(32),",
        ".MAX_WAIT_CYCLES(32'd4096)) mover (",
        ".clk(clk),.resetn(resetn),",
        ".cmd_valid(dma_valid),.cmd_ready(dma_ready),",
        ".cmd_is_writeback(dma_wb),.cmd_block(dma_block),",
        ".cmd_done(dma_done),.cmd_error(dma_error),.busy(mover_busy),",
        ".client_word_index(word_index),.client_word_data(word_data),",
        ".client_write_enable(edit_enable),.client_write_data(edit_data),",
        ".client_write_strobe(edit_strobe),",
    ])
    pins = []
    for key in READ:
        pins.append(f".s00_{key}(S00_AXI_{key})")
    for key in WRITE:
        pins.append(f".s03_{key}(S03_AXI_{key})")
    for key,net in (("accepted_ar","axiar"),("accepted_r","axir"),
                    ("accepted_aw","axiaw"),("accepted_w","axiw"),
                    ("accepted_b","axib"),("wait_stalls","axi_stalls")):
        pins.append(f".{key}({net})")
    result.append(",\n".join(pins)+");")
    ram_signals = ("awaddr awlen awsize awburst awvalid awready "
                   "wdata wstrb wlast wvalid wready bresp bvalid bready "
                   "araddr arlen arsize arburst arvalid arready "
                   "rdata rresp rlast rvalid rready").split()
    result.extend([
        "m06_axi128_scratch_mem ram (.aclk(clk),.aresetn(resetn),",
        ",\n".join(f".s_axi_{pin}(M00_AXI_{pin})" for pin in ram_signals)+",",
        ".inject_next_b_slverr(1'b0),",
        ".inject_next_r_slverr(inject_read_error));",
        """
reg [255:0] expected [0:255];
reg [255:0] edit_payload=
  256'hffeeddccbbaa99887766554433221100_00112233445566778899aabbccddeeff;
reg [31:0] edit_mask=32'h80010001;
integer i,j;
always @(posedge clk) if(resetn) begin
  if(M00_AXI_wvalid && M00_AXI_wready)
    m00_wbeats<=m00_wbeats+1;
  if(M00_AXI_rvalid && M00_AXI_rready)
    m00_rbeats<=m00_rbeats+1;
end

task automatic demand(input integer blk,input use_write,
                      input expect_fault);
  integer cycle;
  begin
    @(negedge clk);
    if(poisoned || !req_ready)
      $fatal(1,"M06_ORIGINAL_PAGED_FAIL BAD_REQUEST_READY");
    req_block=blk; req_is_write=use_write; req_valid=1;
    @(posedge clk);
    if(!req_ready)
      $fatal(1,"M06_ORIGINAL_PAGED_FAIL LOST_REQUEST");
    @(negedge clk); req_valid=0;
    for(cycle=0;cycle<8000 && !rsp_valid;cycle=cycle+1)
      @(negedge clk);
    if(!rsp_valid)
      $fatal(1,"M06_ORIGINAL_PAGED_FAIL BLOCK_TRANSFER_TIMEOUT");
    if(rsp_block !== blk || rsp_error !== expect_fault)
      $fatal(1,"M06_ORIGINAL_PAGED_FAIL WRONG_BLOCK_RESPONSE %h %b",
             rsp_block,rsp_error);
    if(!expect_fault) begin
      @(negedge clk);rsp_ready=1;
      @(posedge clk);
      if(!rsp_valid)
        $fatal(1,"M06_ORIGINAL_PAGED_FAIL RSP_UNSTABLE");
      @(negedge clk);rsp_ready=0;
    end
  end
endtask

task automatic check_page(input integer blk);
  integer idx;
  begin
    if(!resident_valid || poisoned || resident_block !== blk)
      $fatal(1,"M06_ORIGINAL_PAGED_FAIL MISSING_RESIDENT_BLOCK");
    for(idx=0;idx<8;idx=idx+1) begin
      @(negedge clk); word_index=idx;
      @(negedge clk);
      if(word_data !== expected[blk*8+idx])
        $fatal(1,"M06_ORIGINAL_PAGED_FAIL BYTE_PARITY block=%0d word=%0d got=%h expected=%h",
               blk,idx,word_data,expected[blk*8+idx]);
    end
  end
endtask

initial begin
  // Independent byte formula, same as scratch RAM initial memory.
  for(i=0;i<256;i=i+1) begin
    expected[i]=0;
    for(j=0;j<32;j=j+1)
      expected[i][8*j+:8]=(13*(i*32+j)+17)&255;
  end
  repeat(10) @(negedge clk);resetn=1;
  repeat(30) @(negedge clk);
  demand(1,1,0);
  check_page(1);
  word_index=3;
  @(negedge clk);
  edit_data=edit_payload;edit_strobe=edit_mask;edit_enable=1;
  @(posedge clk);
  for(j=0;j<32;j=j+1)
    if(edit_mask[j])
      expected[11][8*j+:8]=edit_payload[8*j+:8];
  @(negedge clk);edit_enable=0;
  if(word_data !== expected[11])
    $fatal(1,"M06_ORIGINAL_PAGED_FAIL LOCAL_EDIT");
  demand(2,0,0);check_page(2); // Evict dirty page1, then fill page2
  demand(1,0,0);check_page(1); // Reload saved canonical page1
  demand(1,0,0); // Must hit, issue no AXI transaction
  if(wb_acks!==1 || fill_acks!==3 || misses!==3 || hits!==1 ||
     accesses!==4 || axiaw!==8 || axiw!==8 || axib!==8 ||
     axiar!==24 || axir!==24 || m00_wbeats<16 ||
     m00_rbeats<48)
    $fatal(1,"M06_ORIGINAL_PAGED_FAIL REAL_DUT_AXITX W=%0d R=%0d",
           m00_wbeats,m00_rbeats);
  $display("M06_ORIGINAL_VENDOR_PAGED_RTL_PASS fills=3 wb=1 reload_byte_exact=1 M00_write=%0d M00_read=%0d",
           m00_wbeats,m00_rbeats);
  inject_read_error=1;
  demand(3,0,1);
  if(!poisoned || req_ready || resident_block!==1 ||
     wb_acks!==1 || fill_acks!==3)
    $fatal(1,"M06_ORIGINAL_PAGED_FAIL NO_FAILURE_QUARANTINE");
  $display("M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS M00_read=%0d stalls=%0d NO_BOARD_NO_REAL_DDR",
           m00_rbeats,stall_cycles);
  $finish;
end
initial begin
  #2000000;
  $fatal(1,"M06_ORIGINAL_PAGED_FAIL GLOBAL_WATCHDOG");
end
endmodule
""",
    ])
    return "\n".join(result)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--headers",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("requires new exclusive generated TB path")
        raw=json.loads(args.headers.read_text(encoding="utf-8"))
        ports=original_ports(args.original.resolve(strict=True),raw)
        with args.output.open("x",encoding="utf-8") as f:
            f.write(render_paged(ports))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print("M06 genuine original vendor PAGED BFM generation failed: "+str(exc),
              file=sys.stderr)
        return 2
    print("M06 original AMD 96-pin PAGED vendor BFM generated; REAL XSIM NOT RUN")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
