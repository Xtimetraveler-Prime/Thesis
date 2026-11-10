#!/usr/bin/env python3
"""Generate original AMD SmartConnect high-address 4096-neuron image XSim.

This optional fifth test preserves the 256-bit READ S00/WRITE S03 and 128-bit
M00 original role, but expands ONLY our scratch memory to 64KiB. Exercises
canonical block 255 and out-of-range block 256. NO PHYSICAL PS DDR ACCESS.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from m06_generate_original_mem_sc_bfm import original_ports
from m06_generate_original_paged_vendor_bfm import render_paged


HIGH_MAIN = r"""
reg [255:0] expected [0:2047];
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
"""


HIGH_SCENARIO = r"""
initial begin
  // Exact 64KiB original scratch formula over all 4096 neuron records.
  for(i=0;i<2048;i=i+1) begin
    expected[i]=0;
    for(j=0;j<32;j=j+1)
      expected[i][8*j+:8]=(13*(i*32+j)+17)&255;
  end
  repeat(10) @(negedge clk); resetn=1;
  repeat(30) @(negedge clk);
  // The highest canonical page begins at byte 65280 (0xff00),
  // occupies rows 4080..4095 and ENDS exactly at byte 65535.
  demand(255,1,0);
  check_page(255);
  word_index=3;
  @(negedge clk);
  edit_data=edit_payload;edit_strobe=edit_mask;edit_enable=1;
  @(posedge clk);
  for(j=0;j<32;j=j+1)
    if(edit_mask[j])
      expected[255*8+3][8*j+:8]=edit_payload[8*j+:8];
  @(negedge clk);edit_enable=0;
  if(word_data !== expected[255*8+3])
    $fatal(1,"M06_VENDOR_4096_FAIL LOCAL_MASKED_HIGH_ADDRESS_EDIT");
  // Evict the highest dirty page, then reload its exact canonical bytes
  // through original AXI S00 read port and 128b downstream M00.
  demand(254,0,0);
  check_page(254);
  demand(255,0,0);
  check_page(255);
  demand(255,0,0);
  if(wb_acks!==1 || fill_acks!==3 || misses!==3 || hits!==1 ||
     accesses!==4 || axiar!==24 || axir!==24 ||
     axiaw!==8 || axiw!==8 || axib!==8 ||
     m00_wbeats<16 || m00_rbeats<48)
    $fatal(1,"M06_VENDOR_4096_FAIL HIGH_ADDRESS_TRANSFER_COUNTS W=%0d R=%0d",
           m00_wbeats,m00_rbeats);
  $display("M06_ORIGINAL_VENDOR_4096_RANGE_PASS highest_page=255 last_neuron=4095 last_byte=65535 dirty_wb=1 M00_write=%0d M00_read=%0d",
           m00_wbeats,m00_rbeats);
  // Block 256 begins at byte 65536 and is NOT part of the canonical image.
  // The RTL mover must reject this without issuing any memory AXI traffic.
  demand(256,0,1);
  if(!poisoned || req_ready || wb_acks!==1 || fill_acks!==3 ||
     axiar!==24 || axiaw!==8 ||
     m00_wbeats!==16 || m00_rbeats!==48)
    $fatal(1,"M06_VENDOR_4096_FAIL OUT_OF_RANGE_NOT_QUARANTINED");
  $display("M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS block256_rejected=1 no_physical_DDR=1");
  $finish;
end
initial begin
  #4000000;
  $fatal(1,"M06_VENDOR_4096_FAIL GLOBAL_WATCHDOG");
end
endmodule
"""


def render_full_canonical(ports: list[dict]) -> str:
    old=render_paged(ports)
    start=old.index("reg [255:0] expected [0:255];")
    head=old[:start]
    head=head.replace("module tb_m06_original_vendor_paged;",
                      "module tb_m06_original_vendor_4096;")
    head=head.replace("m06_axi256_block_transfer #(.MAX_BLOCKS(32),",
                      "m06_axi256_block_transfer #(.MAX_BLOCKS(256),")
    head=head.replace("m06_axi128_scratch_mem ram (",
                      "m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536)) ram (")
    if "MAX_BLOCKS(256)" not in head or "SCRATCH_BYTES(65536)" not in head:
        raise ValueError("cannot enlarge genuine original vendor scratch ABI")
    src_task=old.index("task automatic demand(input integer blk,")
    stop=old.index("\ninitial begin\n  // Independent byte formula",src_task)
    tasks=old[src_task:stop]
    return head+HIGH_MAIN+tasks+HIGH_SCENARIO


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--original",type=Path,required=True)
    ap.add_argument("--headers",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("exclusive new output in existing evidence dir required")
        ports=original_ports(a.original.resolve(strict=True),
                             json.loads(a.headers.read_text()))
        with a.output.open("x",encoding="utf-8") as fp:
            fp.write(render_full_canonical(ports))
    except (OSError,ValueError,KeyError,TypeError) as e:
        print("M06 4096-neuron original vendor TB GENERATION REJECTED: "+str(e),
              file=sys.stderr)
        return 2
    print("M06 4096-neuron 64KiB ORIGINAL vendor high-offset TB GENERATED; "
          "genuine XSim NOT RUN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
