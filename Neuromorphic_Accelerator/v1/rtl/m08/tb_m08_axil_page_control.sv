// M08.2b.2 Icarus standalone AXI4-Lite BFM, no AMD IP or KV260 hardware.
// Checks real bus handshakes, stalls, partial byte lanes, ownership, poison.
`timescale 1ns/1ps
module tb_m08_axil_page_control;
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
  integer dispatch_pulses=0;
  always @(posedge clk) begin
    if(!resetn) dispatch_pulses<=0;
    else if(dispatch_accept) dispatch_pulses<=dispatch_pulses+1;
  end
  reg [31:0] seen;
  m08_axil_page_control dut(
    .aclk(clk),.aresetn(resetn),
    .s_axi_awaddr(awaddr),.s_axi_awprot(awprot),
    .s_axi_awvalid(awvalid),.s_axi_awready(awready),
    .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),
    .s_axi_wvalid(wvalid),.s_axi_wready(wready),
    .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
    .s_axi_araddr(araddr),.s_axi_arprot(arprot),
    .s_axi_arvalid(arvalid),.s_axi_arready(arready),
    .s_axi_rdata(rdata),.s_axi_rresp(rresp),
    .s_axi_rvalid(rvalid),.s_axi_rready(rready),
    .compute_req(compute_req),.compute_write(compute_write),
    .compute_word(compute_word),.compute_wdata(compute_wdata),
    .compute_wstrb(compute_wstrb),.compute_ack(compute_ack),
    .compute_rdata(compute_rdata),.compute_done(compute_done),
    .compute_fault(compute_fault),.fault_in(fault_in),
    .dispatch_accept(dispatch_accept),.page_poisoned(page_poisoned)
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
             address,bresp,expected_resp,dut.bank_phase);
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
             address,rdata,expected_data,rresp,expected_resp,dut.bank_phase);
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
  task automatic run_compute(input [31:0] logical);
  begin
    axi_write(12'h010,logical,4'hf,0,2'b00);
    axi_write(12'h014,32'h4,4'hf,1,2'b00);
    if(!dut.bank_compute_busy || dut.bank_phase!==3'd3 ||
       dispatch_pulses<1)
      $fatal(1,"M08_AXIL_DISPATCH_MISSING");
    // The AXI slave must reject page traffic while the compute side
    // owns it, WITHOUT forwarding a dangerous bank host request.
    axi_read(12'h100,32'd0,2'b10);
    if(page_poisoned || dut.bank_phase!==3'd3)
      $fatal(1,"M08_AXIL_READ_DURING_COMPUTE_POISONED");
    @(negedge clk);compute_req=1;compute_write=0;compute_word=0;
    @(posedge clk);#1;
    if(!compute_ack || compute_rdata!==32'h55550004)
      $fatal(1,"M08_AXIL_COMPUTE_READ_BAD ack=%b value=%h",
             compute_ack,compute_rdata);
    @(negedge clk);compute_req=0;
    @(negedge clk);compute_req=1;compute_write=1;compute_word=0;
    compute_wdata=32'h00000006;compute_wstrb=4'h3;
    @(posedge clk);#1;
    if(!compute_ack)$fatal(1,"M08_AXIL_COMPUTE_WRITE_NO_ACK");
    @(negedge clk);compute_req=0;compute_write=0;
    @(negedge clk);compute_done=1;
    @(posedge clk);#1;
    if(!dut.bank_page_dirty)$fatal(1,"M08_AXIL_DIRTY_NOT_SET");
    @(negedge clk);compute_done=0;
  end
  endtask
  initial begin
    reset_all();
    axi_read(12'h000,32'h4d303850,2'b00);
    axi_read(12'h004,32'h00020002,2'b00);
    axi_read(12'h008,32'h00000001,2'b00);
    axi_read(12'h200,32'h00000000,2'b11);
    axi_read(12'h101,32'h00000000,2'b11);
    axi_write(12'h000,32'hffffffff,4'hf,2,2'b10);
    axi_write(12'h210,32'hffffffff,4'hf,0,2'b11);
    axi_write(12'h010,32'd7,4'h1,1,2'b10);
    axi_write(12'h014,32'h3,4'hf,2,2'b10);
    axi_write(12'h100,32'hc0ffee00,4'h0,0,2'b10);
    axi_read(12'h00c,32'd0,2'b00);
    $display("M08_AXIL_DECODE_AW_W_AND_STALLS_PASS");
    stage(32'd7,32'h55550004);
    $display("M08_AXIL_PAGE_STAGE_256B_READBACK_PASS");
    run_compute(32'd7);
    // A software host read during engine ownership is rejected by
    // AXI without forwarding it to the bank/poisoning the page.
    // Now DIRTY: save not allowed before 64 real reads.
    axi_write(12'h014,32'h8,4'hf,2,2'b10);
    if(page_poisoned!==1'b1)
      $fatal(1,"M08_AXIL_PREMATURE_SAVE_NOT_POISONED");
    $display("M08_AXIL_PREMATURE_SAVE_POISONED_PASS");
    reset_all();
    stage(32'd7,32'h55550004);
    run_compute(32'd7);
    // Full dirty observation; values reflect compute low-byte strobes.
    axi_read(12'h100,32'h55550006,2'b00);
    for(i=1;i<64;i=i+1)
      axi_read(12'h100+i*4,32'h10200000+i,2'b00);
    axi_write(12'h014,32'h8,4'hf,1,2'b00);
    axi_read(12'h00c,32'h00000012,2'b00);
    axi_write(12'h010,32'd9,4'hf,2,2'b00);
    axi_write(12'h014,32'h1,4'hf,0,2'b00);
    axi_read(12'h018,32'd9,2'b00);
    axi_read(12'h01c,32'd0,2'b00);
    $display("M08_AXIL_DIRTY_READBACK_SAVE_REPLACE_PASS");
    reset_all();
    // A page whose bytes were written but never read must not commit.
    axi_write(12'h010,32'd2,4'hf,2,2'b00);
    axi_write(12'h014,32'h1,4'hf,2,2'b00);
    for(i=0;i<64;i=i+1)
      axi_write(12'h100+i*4,32'h70000000+i,4'hf,i%3,2'b00);
    axi_write(12'h014,32'h2,4'hf,2,2'b10);
    if(!page_poisoned)$fatal(1,"M08_AXIL_FAKE_READBACK_NOT_POISONED");
    axi_read(12'h00c,32'h0000000d,2'b00);
    axi_read(12'h100,0,2'b10);
    $display("M08_AXIL_UNVERIFIED_LOAD_POISONED_PASS");

    // Simulate a permanently unresponsive page port. The AXI-Lite
    // request MUST receive a bounded SLVERR; later writes are blocked
    // until external reset, not indefinitely pending on a dead backend.
    reset_all();
    axi_write(12'h010,32'd13,4'hf,0,2'b00);
    axi_write(12'h014,32'h1,4'hf,1,2'b00);
    axi_write(12'h100,32'h12345678,4'hf,2,2'b00);
    force dut.bank_host_ack = 1'b0;
    axi_read(12'h100,32'd0,2'b10);
    release dut.bank_host_ack;
    if(!page_poisoned)
      $fatal(1,"M08_AXIL_BRIDGE_TIMEOUT_NOT_STICKY");
    axi_read(12'h00c,32'h00000181,2'b00);
    axi_write(12'h010,32'd15,4'hf,2,2'b10);
    $display("M08_AXIL_NO_ACK_TIMEOUT_QUARANTINE_PASS");
    $display("M08_AXIL_STANDALONE_NO_K26_NO_DDR_NO_DMA_PASS");
    $finish;
  end
  initial begin
    #5000000;$fatal(1,"M08_AXIL_TEST_GLOBAL_TIMEOUT");
  end
endmodule
