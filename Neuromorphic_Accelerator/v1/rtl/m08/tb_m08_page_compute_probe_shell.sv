// M08.2b.2 Icarus standalone AXI4-Lite BFM, no AMD IP or KV260 hardware.
// Checks real bus handshakes, stalls, partial byte lanes, ownership, poison.
`timescale 1ns/1ps
module tb_m08_page_compute_probe_shell;
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
  reg compute_req=0,compute_write=0,compute_done=0,compute_fault=0,fault_in=0;
  reg [5:0] compute_word=0;
  reg [31:0] compute_wdata=0;
  reg [3:0] compute_wstrb=0;
  wire compute_ack,dispatch_accept,page_poisoned;
  wire [31:0] compute_rdata;
  integer i;
  reg [31:0] expected_checksum;
  assign dispatch_accept=dut.dispatch_accept;
  assign page_poisoned=dut.page_poisoned;
  integer dispatch_pulses=0;
  always @(posedge clk) begin
    if(!resetn) dispatch_pulses<=0;
    else if(dispatch_accept) dispatch_pulses<=dispatch_pulses+1;
  end
  reg [31:0] seen;
  m08_page_compute_probe_shell dut(
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
    bready=0;rready=0;compute_req=0;compute_done=0;compute_fault=0;fault_in=0;
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
  task automatic stage(input [31:0] logical,input [31:0] first_word);
    reg [31:0] expected;
    integer j;
  begin
    axi_write(12'h010,logical,4'hf,0,2'b00);
    axi_write(12'h014,32'h1,4'hf,1,2'b00);
    axi_read(12'h01c,32'd0,2'b00);
    axi_read(12'h010,logical,2'b00);
    // Partial byte writes to one 32-bit word, then all other words.
    axi_write(12'h100,{16'd0,first_word[15:0]},4'h3,2,2'b00);
    axi_write(12'h100,{first_word[31:16],16'd0},4'hc,0,2'b00);
    for(j=1;j<64;j=j+1)
      axi_write(12'h100+j*4,32'h10200000+j,4'hf,j%3,2'b00);
    axi_read(12'h01c,32'd256,2'b00);
    for(j=0;j<64;j=j+1) begin
      expected=(j==0)?first_word:(32'h10200000+j);
      axi_read(12'h100+j*4,expected,2'b00);
    end
    axi_write(12'h014,32'h2,4'hf,2,2'b00);
    axi_read(12'h018,logical,2'b00);
    // phase=READY 2, page_valid bit4=1.
    axi_read(12'h00c,32'h00000012,2'b00);
  end
  endtask
  task automatic scan_page(input [31:0] logical_id,input [31:0] first_word);
    integer j, cycles;
    reg [31:0] check;
  begin
    check=first_word;
    for(j=1;j<63;j=j+1) check=check^(32'h10200000+j);
    axi_write(12'h010,logical_id,4'hf,0,2'b00);
    axi_write(12'h014,32'h4,4'hf,1,2'b00);
    // Host may NOT read the resident bank while engine owns it.
    axi_read(12'h100,32'h00000000,2'b10);
    if(page_poisoned)
      $fatal(1,"M08_PROBE_HOST_READ_DURING_COMPUTE_POISONED");
    cycles=0;
    while(dut.page_adapter.bank_phase!==3'd4 && cycles<2000) begin
      @(negedge clk);
      cycles=cycles+1;
    end
    if(cycles>=2000 || dut.probe.last_checksum!==check)
      $fatal(1,"M08_PROBE_FULL_SCAN_OR_DONE_FAILED cycles=%d computed=%h expected=%h",
             cycles,dut.probe.last_checksum,check);
    expected_checksum=check;
    // Dirty host readback includes all 64 words; fake SAVE poisons.
    for(j=0;j<64;j=j+1)
      axi_read(12'h100+j*4,
               (j==0)?first_word:((j==63)?check:(32'h10200000+j)),
               2'b00);
    axi_write(12'h014,32'h8,4'hf,1,2'b00);
    axi_read(12'h00c,32'h00000012,2'b00);
  end
  endtask

  initial begin
    reset_all();
    axi_read(12'h000,32'h4d303850,2'b00);
    axi_read(12'h004,32'h00020002,2'b00);
    stage(32'd7,32'h55550004);
    $display("M08_PAGE_PROBE_ACTUAL_AXIL_STAGE_FULL_READBACK_PASS");
    scan_page(32'd7,32'h55550004);
    if(dut.probe.completed_runs!==32'd1)
      $fatal(1,"M08_PAGE_PROBE_DISPATCH_ONE_RUN_FAILED");
    $display("M08_PAGE_PROBE_63_READ_1_WRITE_DIRTY_SAVE_PASS");
    // Host source retains logical backing, now replaces with new context.
    stage(32'd9,32'hA5A51234);
    scan_page(32'd9,32'hA5A51234);
    if(dut.probe.completed_runs!==32'd2 ||
       dut.page_adapter.bank_page_logical!==32'd9)
      $fatal(1,"M08_PAGE_PROBE_SECOND_LOGICAL_PAGE_NOT_RUN");
    $display("M08_PAGE_PROBE_TWO_SEPARATE_LOGICAL_CONTEXTS_PASS");

    reset_all();
    stage(32'd13,32'h00000000);
    axi_write(12'h010,32'd77,4'hf,2,2'b00);
    axi_write(12'h014,32'h4,4'hf,1,2'b10);
    if(!page_poisoned) $fatal(1,"M08_PAGE_PROBE_WRONG_LOGICAL_NOT_POISONED");
    $display("M08_PAGE_PROBE_WRONG_LOGICAL_POISON_PASS");

    reset_all();
    stage(32'd21,32'h11223344);
    axi_write(12'h014,32'h4,4'hf,2,2'b00);
    repeat(500) @(negedge clk);
    if(dut.page_adapter.bank_phase!==3'd4)
      $fatal(1,"M08_PAGE_PROBE_DIRTY_BEFORE_SAVE_MISSING");
    axi_write(12'h014,32'h8,4'hf,2,2'b10);
    if(!page_poisoned)
      $fatal(1,"M08_PAGE_PROBE_PREMATURE_SAVE_NOT_QUARANTINED");
    $display("M08_PAGE_PROBE_PREMATURE_SAVE_POISON_PASS");

    reset_all();
    stage(32'd23,32'hDEADC0DE);
    force dut.compute_ack = 1'b0;
    axi_write(12'h014,32'h4,4'hf,2,2'b00);
    repeat(40) @(negedge clk);
    if(!dut.probe.compute_fault || !page_poisoned)
      $fatal(1,"M08_PAGE_PROBE_NO_ACK_WATCHDOG_FAILED");
    release dut.compute_ack;
    $display("M08_PAGE_PROBE_STALLED_COMPUTE_WATCHDOG_POISON_PASS");
    $display("M08_PAGE_PROBE_REAL_RTL_SOFTWARE_ONLY_NO_DDR_NO_K26_PASS");
    $finish;
  end
  initial begin
    #12000000;$fatal(1,"M08_PAGE_PROBE_GLOBAL_TIMEOUT");
  end
endmodule
