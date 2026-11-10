"""M06 G3 positive/negative RTL address guards; NO AMD IP / HLS / BOARD.

CI uses Icarus to simulate the REAL candidate synthesizable guard modules.
A simulator PASS is NOT vendor SmartConnect, width-converter, or HLS-link proof.
"""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/m06/m06_axi64_to32_guards.sv"
TB = r"""
`timescale 1ns/1ps
module tb_m06_g3_addr_guards;
reg clk=0; always #5 clk=~clk;
reg rst=0;
reg [0:0] arid=1; reg [63:0] araddr=0;
reg [7:0] arlen=0; reg [2:0] arsize=2; reg [1:0] arburst=1;
reg arvalid=0; wire arready;
wire [0:0] marid;wire [31:0] maraddr;wire [7:0] marlen;
wire [2:0] marsize;wire [1:0] marburst;wire marvalid;
reg marready=1;
reg [0:0] mrid=1;reg [31:0] mrdata=32'hfabced01;
reg [1:0] mrresp=0;reg mrlast=1,mrvalid=0;wire mrready;
wire [0:0] rid;wire [31:0] rdata;wire [1:0] rresp;
wire rlast,rvalid;reg rready=0;wire rf;
m06_axi64_to32_read_guard rd(
 .aclk(clk),.aresetn(rst),
 .s_arid(arid),.s_araddr(araddr),.s_arlen(arlen),.s_arsize(arsize),
 .s_arburst(arburst),.s_arvalid(arvalid),.s_arready(arready),
 .m_arid(marid),.m_araddr(maraddr),.m_arlen(marlen),.m_arsize(marsize),
 .m_arburst(marburst),.m_arvalid(marvalid),.m_arready(marready),
 .m_rid(mrid),.m_rdata(mrdata),.m_rresp(mrresp),.m_rlast(mrlast),
 .m_rvalid(mrvalid),.m_rready(mrready),
 .s_rid(rid),.s_rdata(rdata),.s_rresp(rresp),.s_rlast(rlast),
 .s_rvalid(rvalid),.s_rready(rready),.fault_seen(rf));
reg [0:0] awid=1;reg [63:0] awaddr=0;reg [7:0] awlen=0;
reg [2:0] awsize=2;reg [1:0] awburst=1;reg awvalid=0;
wire awready;wire [0:0] mawid;wire [31:0] mawaddr;wire [7:0] mawlen;
wire [2:0] mawsize;wire [1:0] mawburst;wire mawvalid;
reg mawready=1;
reg [31:0] wdata=32'h12345678;reg [3:0] wstrb=4'b0101;
reg wlast=1,wvalid=0;wire wready;
wire [31:0] mwdata;wire [3:0] mwstrb;wire mwlast,mwvalid;
reg mwready=1;
reg [0:0] mbid=1;reg [1:0] mbresp=0;reg mbvalid=0;wire mbready;
wire [0:0] bid;wire [1:0] bresp;wire bvalid;
reg bready=0;wire wf;
m06_axi64_to32_write_guard wr(
 .aclk(clk),.aresetn(rst),
 .s_awid(awid),.s_awaddr(awaddr),.s_awlen(awlen),.s_awsize(awsize),
 .s_awburst(awburst),.s_awvalid(awvalid),.s_awready(awready),
 .m_awid(mawid),.m_awaddr(mawaddr),.m_awlen(mawlen),.m_awsize(mawsize),
 .m_awburst(mawburst),.m_awvalid(mawvalid),.m_awready(mawready),
 .s_wdata(wdata),.s_wstrb(wstrb),.s_wlast(wlast),.s_wvalid(wvalid),
 .s_wready(wready),.m_wdata(mwdata),.m_wstrb(mwstrb),
 .m_wlast(mwlast),.m_wvalid(mwvalid),.m_wready(mwready),
 .m_bid(mbid),.m_bresp(mbresp),.m_bvalid(mbvalid),.m_bready(mbready),
 .s_bid(bid),.s_bresp(bresp),.s_bvalid(bvalid),.s_bready(bready),
 .fault_seen(wf));
task automatic reset_all;
 begin
  @(negedge clk);rst=0;arvalid=0;awvalid=0;wvalid=0;
  mrvalid=0;mbvalid=0;rready=0;bready=0;
  repeat(3) @(negedge clk);
  rst=1;
 end
endtask
task automatic send_ar(input [63:0] addr,input [7:0] len,
                       input forwarded);
 begin
  @(negedge clk); araddr=addr;arlen=len;arsize=2;arburst=1;arvalid=1;
  #1;
  if(arready!==1 || marvalid!==forwarded)
   $fatal(1,"M06_G3_GUARD_FAIL READ_AR addr=%h",addr);
  if(forwarded && (maraddr!==addr[31:0] || marid!==1 || marlen!==len))
   $fatal(1,"M06_G3_GUARD_FAIL READ_AR payload");
  @(posedge clk);
  @(negedge clk);arvalid=0;
 end
endtask
task automatic send_aw(input [63:0] addr,input forwarded);
 begin
  @(negedge clk);awaddr=addr;awlen=0;awsize=2;awburst=1;awvalid=1;
  #1;
  if(awready!==1 || mawvalid!==forwarded)
   $fatal(1,"M06_G3_GUARD_FAIL WRITE_AW addr=%h",addr);
  if(forwarded && (mawaddr!==addr[31:0] || mawid!==1))
   $fatal(1,"M06_G3_GUARD_FAIL WRITE_AW payload");
  @(posedge clk);
  @(negedge clk);awvalid=0;
 end
endtask
task automatic send_w(input forwarded);
 begin
  @(negedge clk);wvalid=1;wlast=1;
  #1;
  if(wready!==1 || mwvalid!==forwarded)
   $fatal(1,"M06_G3_GUARD_FAIL WRITE_DATA valid");
  if(forwarded && (mwdata!==wdata || mwstrb!==wstrb))
   $fatal(1,"M06_G3_GUARD_FAIL WRITE_DATA bytes");
  @(posedge clk);
  @(negedge clk);wvalid=0;
 end
endtask
initial begin
 reset_all();
 send_ar(64'h0000_fffc,0,1);
 @(negedge clk);mrvalid=1;rready=0;
 #1;
 if(rvalid!==1 || rdata!==32'hfabced01 || mrready!==0 ||
    rlast!==1 || rresp!==0)
    $fatal(1,"M06_G3_GUARD_FAIL READ_R stall");
 repeat(2) @(negedge clk);
 rready=1;
 @(posedge clk);
 @(negedge clk);mrvalid=0;rready=0;
 if(rf!==0) $fatal(1,"M06_G3_GUARD_FAIL false read poison");

 send_aw(64'h0000_fffc,1);
 send_w(1);
 @(negedge clk);mbvalid=1;bready=0;
 #1;
 if(bvalid!==1 || bresp!==0 || mbready!==0)
    $fatal(1,"M06_G3_GUARD_FAIL WRITE_B stall");
 repeat(2) @(negedge clk);
 bready=1;
 @(posedge clk);
 @(negedge clk);mbvalid=0;bready=0;
 if(wf!==0) $fatal(1,"M06_G3_GUARD_FAIL false write poison");

 send_ar(64'h0001_0000,0,0);
 @(negedge clk);rready=0;
 #1;
 if(rvalid!==1 || rresp!==3 || rlast!==1 ||
    rdata!==0 || marvalid!==0 || rf!==1)
    $fatal(1,"M06_G3_GUARD_FAIL out-of-region READ DECERR");
 repeat(2) @(negedge clk);
 rready=1;
 @(posedge clk);
 @(negedge clk);rready=0;

 send_ar(64'h0,0,0);
 @(negedge clk);rready=1;
 #1;
 if(rresp!==3) $fatal(1,"M06_G3_GUARD_FAIL poisoned READ");
 @(posedge clk);
 @(negedge clk);rready=0;

 send_aw(64'h0001_0000,0);
 send_w(0);
 @(negedge clk);bready=0;
 #1;
 if(bvalid!==1 || bresp!==3 || bid!==1 || mbready!==0 || wf!==1)
    $fatal(1,"M06_G3_GUARD_FAIL out-of-region WRITE DECERR");
 repeat(2) @(negedge clk);
 bready=1;
 @(posedge clk);
 @(negedge clk);bready=0;

 reset_all();
 send_ar(64'hffc,1,0);
 @(negedge clk);rready=1;
 #1;
 if(rvalid!==1 || rlast!==0 || rresp!==3)
    $fatal(1,"M06_G3_GUARD_FAIL 4K boundary READ first beat");
 @(posedge clk);
 @(negedge clk);
 #1;
 if(rvalid!==1 || rlast!==1 || rresp!==3)
    $fatal(1,"M06_G3_GUARD_FAIL 4K boundary READ last beat");
 @(posedge clk);
 @(negedge clk);rready=0;
 if(rf!==1) $fatal(1,"M06_G3_GUARD_FAIL crossing poison");
 $display("M06_G3_AXI64_TO32_GUARDS_IVERILOG_PASS highpage255=1 illegal256=DECERR 4k=DECERR sticky_fault=1 NO_AMD_NO_BOARD");
 $finish;
end
initial begin #100000; $fatal(1,"M06_G3_GUARD_FAIL watchdog"); end
endmodule
""";


class M06AXI64to32RealRTLTests(unittest.TestCase):
    def test_real_candidate_iverilog_positive_and_negative(self):
        if not shutil.which("iverilog") or not shutil.which("vvp"):
            self.skipTest("Icarus unavailable; requires real CI or local Icarus")
        with tempfile.TemporaryDirectory() as root:
            temp = Path(root)
            bench = temp / "tb_guard.sv"
            bench.write_text(TB)
            executable = temp / "m06_guard.vvp"
            build = subprocess.run(
                ["iverilog", "-g2012", "-s", "tb_m06_g3_addr_guards",
                 "-o", str(executable), str(RTL), str(bench)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            run = subprocess.run(
                ["vvp", str(executable)], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("M06_G3_AXI64_TO32_GUARDS_IVERILOG_PASS", run.stdout)
            self.assertNotIn("M06_G3_GUARD_FAIL", run.stdout)

    def test_fail_closed_source_invariants_without_iverilog(self):
        source = RTL.read_text()
        self.assertIn("module m06_axi64_to32_read_guard", source)
        self.assertIn("module m06_axi64_to32_write_guard", source)
        self.assertEqual(source.count("num_bytes<=17'd4096"), 2)
        self.assertEqual(source.count("num_bytes<=17'd65536"), 2)
        self.assertEqual(source.count("len<=8'd15"), 2)
        self.assertEqual(source.count("fault_seen<=1'b1"), 6)
        self.assertIn("state<=DISCARD", source)
        self.assertIn("state<=DECERR", source)
        self.assertIn("2'b11", source)


if __name__ == "__main__":
    unittest.main()
