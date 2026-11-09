#!/usr/bin/env python3
"""Generate ONE genuine original mem_sc 96-port XSim BFM, not vendor proof.

Never check original AMD HDL into Git. Require real owner generated SIM wrapper
and nested BD module SHA, 2026-11-09 Vivado source report identity, exact AXI
port names/directions/widths; NEVER silently infer a nonexistent ID/USER.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT_NAME="neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
MODULE="m05_12d3_real_signed32_hls_six_control_address_candidate_mem_sc_0"
SUBDIR=("13_file_backed_project/m05_d3_output_products.gen/sources_1/bd/"
        "m05_12d3_real_signed32_hls_six_control_address_candidate/ip/"+MODULE)
SIM_PATH=SUBDIR+"/sim/"+MODULE+".sv"
BD_PATH=SUBDIR+"/bd_0/sim/bd_13bd.v"
SIM_SHA="0ec8a01dfc7c23825a8d5c8934c7f26dc5b92b924be88d51addd9e76555b8e12"
BD_SHA="c3d7c5021f532aae29c860a63fb92da9529dac489f87a74267b9af82472444f3"
REPORT_SHA="3c85a47ad2230efd730d30a07739c18ca00690b1a1e6ed7ad998fc6e39fd76d0"

READ=dict(araddr=32,arlen=8,arsize=3,arburst=2,arlock=1,
          arcache=4,arprot=3,arqos=4,arvalid=1,arready=1,
          rdata=256,rresp=2,rlast=1,rvalid=1,rready=1)
WRITE=dict(awaddr=32,awlen=8,awsize=3,awburst=2,awlock=1,
           awcache=4,awprot=3,awqos=4,awvalid=1,awready=1,
           wdata=256,wstrb=32,wlast=1,wvalid=1,wready=1,
           bresp=2,bvalid=1,bready=1)
M00={**{k:(49 if k in ("awaddr","araddr") else
             128 if k in ("wdata","rdata") else
             16 if k=="wstrb" else v)
        for k,v in {**WRITE,**READ}.items()}}
M00["wstrb"]=16


def required_ports():
    ports={}
    for n in range(3):
        for key,w in READ.items():
            mode="output" if key in ("arready","rdata","rresp","rlast","rvalid") else "input"
            ports[f"S0{n}_AXI_{key}"]=(mode,w)
    for key,w in WRITE.items():
        mode="output" if key in ("awready","wready","bresp","bvalid") else "input"
        ports["S03_AXI_"+key]=(mode,w)
    for key,w in M00.items():
        mode="input" if key in ("awready","wready","bresp","bvalid",
                               "arready","rdata","rresp","rlast","rvalid") else "output"
        ports["M00_AXI_"+key]=(mode,w)
    assert len(ports)==96
    return ports


def original_ports(original:Path, headers:dict):
    if original.name!=ROOT_NAME or not original.is_dir():
        raise ValueError("wrong authentic original D3 folder")
    if (headers.get("original_report_sha256")!=REPORT_SHA or
        headers.get("status")!="MODULE_HEADERS_FOUND_NOT_COMPILED" or
        headers.get("vendor_functional_axi")!="NOT_EXECUTED"):
        raise ValueError("wrong original port report/functional-status provenance")
    matches=[p for p in headers.get("wrapper_candidates",[])
             if p.get("module")==MODULE and
                p.get("source_relative_to_original")==SIM_PATH]
    if len(matches)!=1 or matches[0].get("source_sha256")!=SIM_SHA:
        raise ValueError("original simulation wrapper identity invalid")
    p=matches[0]
    observed={x["name"]:(x["direction"],x["packed_width"])
              for x in p["ansi_axi_ports"]}
    exact=required_ports()
    if len(p["ansi_axi_ports"])!=96 or observed!=exact:
        raise ValueError("original vendor 96-signal AXI port contract mismatch")
    other={x["name"]:(x["direction"],x["packed_width"])
           for x in p.get("other_ports",[])}
    if other!={"aclk":("input",1),"aresetn":("input",1)}:
        raise ValueError("original clock/reset contract mismatch")
    for rel,digest in ((SIM_PATH,SIM_SHA),(BD_PATH,BD_SHA)):
        path=(original/rel).resolve(strict=True)
        if not path.is_relative_to(original):
            raise ValueError("attempted source path outside D3")
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError(f"original RTL SHA mismatch: {rel}")
    return p["ansi_axi_ports"]


def read_task(port:int):
    s=f"S0{port}_AXI"
    return f"""
  task automatic read{port}(input integer addr);
    reg [255:0] wanted;
    begin
      wanted=expected_word(addr);
      @(negedge clk);
      {s}_araddr=addr; {s}_arlen=0; {s}_arsize=3'd5;
      {s}_arburst=2'b01; {s}_arlock=0; {s}_arcache=4'b0011;
      {s}_arprot=0; {s}_arqos=0; {s}_arvalid=1;
      @(posedge clk);
      while({s}_arready !== 1'b1) @(posedge clk);
      @(negedge clk); {s}_arvalid=0;
      @(posedge clk);
      while({s}_rvalid !== 1'b1) @(posedge clk);
      if({s}_rdata !== wanted || {s}_rresp !== 2'b00 ||
         {s}_rlast !== 1'b1)
        $fatal(1,"M06_VENDOR_FAIL S0{port} WRONG_DATA addr=%h actual=%h expected=%h resp=%b last=%b",
               addr,{s}_rdata,wanted,{s}_rresp,{s}_rlast);
      repeat(3) begin
        @(posedge clk);
        if({s}_rvalid !== 1'b1 || {s}_rdata !== wanted ||
           {s}_rresp !== 2'b00 || {s}_rlast !== 1'b1)
          $fatal(1,"M06_VENDOR_FAIL S0{port} RVALID_STABILITY");
      end
      @(negedge clk); {s}_rready=1;
      @(posedge clk);
      if({s}_rvalid !== 1'b1 || {s}_rdata !== wanted)
        $fatal(1,"M06_VENDOR_FAIL S0{port} R_HANDSHAKE");
      @(negedge clk); {s}_rready=0;
      verified_reads=verified_reads+1;
    end
  endtask
"""


def render(ports:list[dict])->str:
    lines=["// ORIGINAL vendor RTL compiled externally from immutable D3 evidence.",
           "// ONLY this generated TB is new; no physical PS/DDR/BOARD.",
           chr(96)+"timescale 1ns/1ps",
           "module tb_m06_original_mem_sc_vendor;",
           "reg clk=0; always #5 clk=~clk;",
           "reg resetn=0;",
           "integer verified_writes=0, verified_reads=0;",
           "integer m00_wbeats=0,m00_rbeats=0,m00_wstalls=0,m00_rstalls=0;"]
    exact=required_ports()
    for p in ports:
        name=p["name"]
        mode,w=exact[name]
        kind="wire" if mode=="output" or name.startswith("M00_AXI_") else "reg"
        width=f"[{w-1}:0] " if w>1 else ""
        lines.append(f"{kind} {width}{name}"+("=0;" if kind=="reg" else ";"))
    lines += [
        MODULE+" dut (.aclk(clk),.aresetn(resetn),",
        ",\n".join(f".{p['name']}({p['name']})" for p in ports)+");"
    ]
    signals=("awaddr awlen awsize awburst awvalid awready "
             "wdata wstrb wlast wvalid wready bresp bvalid bready "
             "araddr arlen arsize arburst arvalid arready "
             "rdata rresp rlast rvalid rready").split()
    lines += ["m06_axi128_scratch_mem ram (.aclk(clk),.aresetn(resetn),",
              ",\n".join(f".s_axi_{k}(M00_AXI_{k})" for k in signals)+",",
              ".inject_next_b_slverr(1'b0),.inject_next_r_slverr(1'b0));",
              """
reg [7:0] expected_mem [0:8191];
integer j;
function automatic [255:0] expected_word(input integer at);
  integer lane;
  begin
    expected_word=0;
    for(lane=0;lane<32;lane=lane+1)
      expected_word[8*lane+:8]=expected_mem[at+lane];
  end
endfunction
function automatic [255:0] payload_for(input integer which);
  integer lane;
  begin
    payload_for=0;
    for(lane=0;lane<32;lane=lane+1)
      payload_for[8*lane+:8]=(17*which+3*lane+11)&255;
  end
endfunction
always @(posedge clk) if(resetn) begin
  if(M00_AXI_wvalid && !M00_AXI_wready) m00_wstalls<=m00_wstalls+1;
  if(M00_AXI_rvalid && !M00_AXI_rready) m00_rstalls<=m00_rstalls+1;
  if(M00_AXI_wvalid && M00_AXI_wready) m00_wbeats<=m00_wbeats+1;
  if(M00_AXI_rvalid && M00_AXI_rready) m00_rbeats<=m00_rbeats+1;
end
task automatic write_one(input integer at,input integer which,
                          input [31:0] mask);
  reg [255:0] data;
  integer lane;
  begin
    data=payload_for(which);
    @(negedge clk);
    S03_AXI_awaddr=at; S03_AXI_awlen=0; S03_AXI_awsize=3'd5;
    S03_AXI_awburst=2'b01; S03_AXI_awlock=0;
    S03_AXI_awcache=4'b0011; S03_AXI_awprot=0; S03_AXI_awqos=0;
    S03_AXI_awvalid=1;
    @(posedge clk);
    while(S03_AXI_awready !== 1'b1) @(posedge clk);
    @(negedge clk);
    S03_AXI_awvalid=0;
    S03_AXI_wdata=data; S03_AXI_wstrb=mask;
    S03_AXI_wlast=1; S03_AXI_wvalid=1;
    @(posedge clk);
    while(S03_AXI_wready !== 1'b1) @(posedge clk);
    @(negedge clk);
    S03_AXI_wvalid=0; S03_AXI_wlast=0;
    @(posedge clk);
    while(S03_AXI_bvalid !== 1'b1) @(posedge clk);
    if(S03_AXI_bresp !== 2'b00)
      $fatal(1,"M06_VENDOR_FAIL S03_BRESP=%b addr=%h",
             S03_AXI_bresp,at);
    repeat(3) begin
      @(posedge clk);
      if(S03_AXI_bvalid !== 1'b1 || S03_AXI_bresp !== 2'b00)
        $fatal(1,"M06_VENDOR_FAIL S03_B_STABILITY");
    end
    @(negedge clk);
    S03_AXI_bready=1;
    @(posedge clk);
    if(S03_AXI_bvalid !== 1'b1)
      $fatal(1,"M06_VENDOR_FAIL S03_B_HANDSHAKE");
    @(negedge clk);
    S03_AXI_bready=0;
    for(lane=0;lane<32;lane=lane+1)
      if(mask[lane]) expected_mem[at+lane]=data[8*lane+:8];
    verified_writes=verified_writes+1;
  end
endtask
"""
    ]
    lines.extend(read_task(i) for i in range(3))
    lines.append("""
initial begin
  for(j=0;j<8192;j=j+1) expected_mem[j]=(13*j+17)&255;
  repeat(12) @(negedge clk); resetn=1;
  repeat(20) @(negedge clk);
  write_one('h0fe0,0,32'hffffffff);
  write_one('h1000,1,32'h80010001);
  write_one('h1020,2,32'h00ff00ff);
  write_one('h1040,3,32'h0000ffff);
  read0('h0fe0); read0('h1000); read0('h1020); read0('h1040);
  read1('h0fe0); read1('h1000); read1('h1020); read1('h1040);
  read2('h0fe0); read2('h1000); read2('h1020); read2('h1040);
  read0('h0fc0); read0('h1060); // independent 4 KiB neighborhood
  if(verified_writes !== 4 || verified_reads !== 14)
    $fatal(1,"M06_VENDOR_FAIL COUNT W=%0d R=%0d",
           verified_writes,verified_reads);
  if(m00_wbeats < 8 || m00_rbeats < 28)
    $fatal(1,"M06_VENDOR_FAIL NO_REAL_M00_TRAFFIC W=%0d R=%0d",
           m00_wbeats,m00_rbeats);
  $display("M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS writes=%0d reads=%0d M00_wbeats=%0d M00_rbeats=%0d M00_wstalls=%0d M00_rstalls=%0d NO_BOARD_NO_REAL_DDR",
            verified_writes,verified_reads,m00_wbeats,m00_rbeats,
            m00_wstalls,m00_rstalls);
  $finish;
end
initial begin
  #400000;
  $fatal(1,"M06_VENDOR_FAIL WATCHDOG_TIMEOUT");
end
endmodule
""")
    return "\n".join(lines)


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original",required=True,type=Path)
    parser.add_argument("--headers",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("new exclusive output in existing directory required")
        src=original_ports(args.original.resolve(strict=True),
                           json.loads(args.headers.read_text(encoding="utf-8")))
        with args.output.open("x",encoding="utf-8") as fp:
            fp.write(render(src))
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(f"M06 original 96-port vendor BFM FAILED: {exc}",file=sys.stderr)
        return 2
    print("M06 REAL ORIGINAL SMARTCONNECT 96-PORT TB GENERATED; "
          "ACTUAL VENDOR XSIM NOT RUN; NO BOARD")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
