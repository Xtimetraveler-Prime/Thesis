// First-party M08.2b.3 PS-only safe shell: dispatch must be disabled.
// Genuine Icarus SOURCE simulation, not KV260 Vivado, Linux MMIO or DDR.
`timescale 1ns/1ps
module tb_m08_ps_page_safe_shell;
  reg clk=0; always #5 clk=~clk;
  reg resetn=0;
  reg [11:0] awaddr=0,araddr=0;
  reg [2:0] awprot=0,arprot=0;
  reg awvalid=0,wvalid=0,arvalid=0,bready=0,rready=0;
  reg [31:0] wdata=0;
  reg [3:0] wstrb=0;
  wire awready,wready,arready,bvalid,rvalid;
  wire [1:0] bresp,rresp;
  wire [31:0] rdata;
  integer j;
  reg [31:0] seen;
  wire page_poisoned=dut.page_adapter.page_poisoned;
  m08_ps_page_safe_shell dut(
    .aclk(clk),.aresetn(resetn),
    .s_axi_awaddr(awaddr),.s_axi_awprot(awprot),
    .s_axi_awvalid(awvalid),.s_axi_awready(awready),
    .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),
    .s_axi_wvalid(wvalid),.s_axi_wready(wready),
    .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
    .s_axi_araddr(araddr),.s_axi_arprot(arprot),
    .s_axi_arvalid(arvalid),.s_axi_arready(arready),
    .s_axi_rdata(rdata),.s_axi_rresp(rresp),
    .s_axi_rvalid(rvalid),.s_axi_rready(rready)
  );
  task automatic reset_all;
  begin
    @(negedge clk);resetn=0;awvalid=0;wvalid=0;arvalid=0;
    bready=0;rready=0;
    repeat(4) @(negedge clk);resetn=1;
    @(negedge clk);
    if(bvalid || rvalid || page_poisoned)
      $fatal(1,"M08_AXIL_RESET_FAILED");
  end
  endtask
  task automatic send_aw(input [11:0] address);
  begin
    @(negedge clk);awaddr=address;awvalid=1;
    #1;if(!awready)$fatal(1,"M08_AXIL_AW_NOT_READY address=%h",address);
    @(posedge clk);@(negedge clk);awvalid=0;
  end
  endtask
  task automatic send_w(input [31:0] value,input [3:0] strobes);
  begin
    @(negedge clk);wdata=value;wstrb=strobes;wvalid=1;
    #1;if(!wready)$fatal(1,"M08_AXIL_W_NOT_READY value=%h",value);
    @(posedge clk);@(negedge clk);wvalid=0;
  end
  endtask
  task automatic axi_write(input [11:0] address,input [31:0] value,
                           input [3:0] strobes,input integer order,
                           input [1:0] expected_resp);
    integer cycles;
    reg [1:0] held;
  begin
    if(order==0) begin
      send_aw(address);
      if(bvalid)$fatal(1,"M08_AXIL_EARLY_B_AW_ONLY");
      send_w(value,strobes);
    end else if(order==1) begin
      send_w(value,strobes);
      if(bvalid)$fatal(1,"M08_AXIL_EARLY_B_W_ONLY");
      send_aw(address);
    end else begin
      @(negedge clk);awaddr=address;awvalid=1;
      wdata=value;wstrb=strobes;wvalid=1;
      #1;if(!awready || !wready)
        $fatal(1,"M08_AXIL_CONCURRENT_AW_W_BLOCKED");
      @(posedge clk);@(negedge clk);awvalid=0;wvalid=0;
    end
    cycles=0;
    while(!bvalid && cycles<32) begin @(negedge clk); cycles=cycles+1;end
    if(!bvalid || bresp!==expected_resp)
      $fatal(1,"M08_AXIL_BRESP_BAD address=%h resp=%b expected=%b phase=%d",
             address,bresp,expected_resp,dut.page_adapter.bank_phase);
    held=bresp;
    repeat(3) begin
      @(negedge clk);
      if(!bvalid || bresp!==held)
        $fatal(1,"M08_AXIL_B_BACKPRESSURE_BROKEN");
    end
    bready=1;@(posedge clk);@(negedge clk);bready=0;
  end
  endtask
  task automatic axi_read(input [11:0] address,
                          input [31:0] expected_data,
                          input [1:0] expected_resp);
    integer cycles;
    reg [31:0] held;
    reg [1:0] held_resp;
  begin
    @(negedge clk);araddr=address;arvalid=1;
    #1;if(!arready)$fatal(1,"M08_AXIL_AR_NOT_READY addr=%h",address);
    @(posedge clk);@(negedge clk);arvalid=0;
    cycles=0;
    while(!rvalid && cycles<160) begin @(negedge clk);cycles=cycles+1;end
    if(!rvalid || rresp!==expected_resp || rdata!==expected_data)
      $fatal(1,"M08_AXIL_R_BAD addr=%h actual=%h expected=%h resp=%b want=%b phase=%d",
             address,rdata,expected_data,rresp,expected_resp,dut.page_adapter.bank_phase);
    held=rdata;held_resp=rresp;
    repeat(2) begin
      @(negedge clk);
      if(!rvalid || rresp!==held_resp || rdata!==held)
        $fatal(1,"M08_AXIL_R_BACKPRESSURE_BROKEN");
    end
    seen=rdata;
    rready=1;@(posedge clk);@(negedge clk);rready=0;
  end
  endtask
  initial begin
    reset_all();
    axi_read(12'h000,32'h4d303850,2'b00);
    axi_read(12'h004,32'h00020002,2'b00);
    axi_read(12'h008,32'h00000001,2'b00);
    axi_read(12'h210,32'h00000000,2'b11);
    axi_write(12'h014,32'h4,4'hf,2,2'b10);
    axi_write(12'h010,32'd41,4'hf,1,2'b00);
    axi_write(12'h014,32'h1,4'hf,0,2'b00);
    for(j=0;j<64;j=j+1)
       axi_write(12'h100+j*4,32'h47000000+j,4'hf,j%3,2'b00);
    axi_read(12'h01c,32'd256,2'b00);
    for(j=0;j<64;j=j+1)
       axi_read(12'h100+j*4,32'h47000000+j,2'b00);
    axi_write(12'h014,32'h2,4'hf,0,2'b00);
    axi_read(12'h00c,32'h12,2'b00);
    axi_read(12'h018,32'd41,2'b00);
    $display("M08_SAFE_SHELL_AXIL_FULL_PAGE_READBACK_PASS");
    // No compute is connected: DISPATCH must NEVER enter RUNNING.
    axi_write(12'h014,32'h4,4'hf,2,2'b10);
    axi_read(12'h00c,32'h12,2'b00);
    if(dut.page_adapter.bank_compute_busy || page_poisoned)
       $fatal(1,"M08_SAFE_SHELL_REJECT_DISPATCH_WITHOUT_ENGINE_FAILED");
    axi_read(12'h100,32'h47000000,2'b00);
    $display("M08_SAFE_SHELL_DISPATCH_DISABLED_NOT_STUCK_BUSY_PASS");
    $display("M08_SAFE_SHELL_SOURCE_ONLY_NO_K26_NO_BITSTREAM_NO_DDR_PASS");
    $finish;
  end
  initial begin
    #5000000;$fatal(1,"M08_SAFE_SHELL_TEST_GLOBAL_TIMEOUT");
  end
endmodule
