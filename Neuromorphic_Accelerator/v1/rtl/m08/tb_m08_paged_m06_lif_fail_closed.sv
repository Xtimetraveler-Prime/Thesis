// M08.2b.2 Icarus standalone AXI4-Lite BFM, no AMD IP or KV260 hardware.
// Checks real bus handshakes, stalls, partial byte lanes, ownership, poison.
`timescale 1ns/1ps
module tb_m08_paged_m06_lif_fail_closed;
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
  reg [31:0] backing [0:383];
  reg [31:0] edge_page_words [0:63];
  reg [31:0] neuron0 [0:63];
  reg [31:0] neuron1 [0:63];
  reg [31:0] edge_words [0:63];
  reg [31:0] golden [0:511];
  reg [3:0] expected_masks [0:31];
  integer verified_input_currents=0;
  integer verified_voltages=0;
  integer verified_spikes=0;
  integer verified_syn_currents=0;
  reg [1023:0] filename0,filename1,filename2,filename3,filename4,filename5;
  reg [1023:0] filename_edges,filename_golden;
  assign dispatch_accept=dut.dispatch_accept;
  assign page_poisoned=dut.page_poisoned;
  integer dispatch_pulses=0;
  always @(posedge clk) begin
    if(!resetn) dispatch_pulses<=0;
    else if(dispatch_accept) dispatch_pulses<=dispatch_pulses+1;
  end
  reg [31:0] seen;
  m08_paged_m06_lif_shell dut(
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
  task automatic stage_words(input [31:0] logical,input integer kind);
    integer w;
    reg [31:0] value;
  begin
    axi_write(12'h010,logical,4'hf,0,2'b00);
    axi_write(12'h014,32'h1,4'hf,1,2'b00);
    for(w=0;w<64;w=w+1) begin
      case(kind)
        0:value=edge_page_words[w];
        1:value=neuron0[w];
        2:value=neuron1[w];
        default:value=0;
      endcase
      axi_write(12'h100+w*4,value,4'hf,w%3,2'b00);
    end
    for(w=0;w<64;w=w+1) begin
      case(kind)
        0:value=edge_page_words[w];
        1:value=neuron0[w];
        2:value=neuron1[w];
        default:value=0;
      endcase
      axi_read(12'h100+w*4,value,2'b00);
    end
    axi_write(12'h014,32'h2,4'hf,2,2'b00);
  end
  endtask
  task automatic expect_poison(input integer case_number);
    integer cycles;
  begin
    cycles=0;
    while(!page_poisoned && cycles<3000) begin
      @(negedge clk);cycles=cycles+1;
    end
    if(cycles>=3000 ||
       dut.neural_engine.state!==3'd5 ||
       dut.page_adapter.bank_phase!==3'd5)
      $fatal(1,"M08_PAGED_LIF_FAULT_CASE_NOT_STICKY case=%d cycles=%d",
             case_number,cycles);
    axi_write(12'h010,32'd123,4'hf,1,2'b10);
    axi_read(12'h100,32'd0,2'b10);
    repeat(10) @(negedge clk);
    if(!page_poisoned || dut.neural_engine.state!==3'd5)
      $fatal(1,"M08_PAGED_LIF_FAULT_RELEASED_WITHOUT_RESET case=%0d",case_number);
    $display("M08_PAGED_LIF_FAIL_CLOSED_REAL_RTL_CASE_PASS|%0d",case_number);
  end
  endtask

  reg [1023:0] edges_file,page0_file,page1_file;
  integer cas;
  initial begin
    if(!$value$plusargs("edge=%s",edges_file) ||
       !$value$plusargs("page0=%s",page0_file) ||
       !$value$plusargs("page1=%s",page1_file))
      $fatal(1,"M08_PAGED_LIF_FAIL_CLOSED_ORIGINAL_SOURCE_PAGES_REQUIRED");
    $readmemh(edges_file,edge_page_words);
    $readmemh(page0_file,neuron0);
    $readmemh(page1_file,neuron1);
    for(cas=0;cas<6;cas=cas+1) begin
      reset_all();
      // Missing setup: cannot dispatch a neural page without configuring
      // positive-delay recurrent connections.
      if(cas==0) begin
        stage_words(0,1);
        axi_write(12'h014,32'h4,4'hf,1,2'b00);
      end else if(cas==5) begin
        // Malformed edge delay=0 MUST NOT be accepted as safe recurrent
        // configuration; the actual RTL, not Python, performs validation.
        edge_page_words[3]=0;
        stage_words(32'hffffffff,0);
        axi_write(12'h014,32'h4,4'hf,1,2'b00);
      end else begin
        stage_words(32'hffffffff,0);
        axi_write(12'h014,32'h4,4'hf,1,2'b00);
        // Real neural engine edge_page_words must finish without bank/engine fault.
        begin:wait_setup
          integer c;
          c=0;
          while(dut.page_adapter.bank_phase!==3'd4 && c<1500) begin
            @(negedge clk);c=c+1;
          end
          if(c>=1500 || page_poisoned || !dut.neural_engine.edge_configured)
            $fatal(1,"M08_PAGED_LIF_FAIL_CLOSED_PRECONDITION_FAILED case=%0d",cas);
        end
        for(integer w=0;w<64;w=w+1)
          axi_read(12'h100+w*4,edge_page_words[w],2'b00);
        axi_write(12'h014,32'h8,4'hf,1,2'b00);
        case(cas)
          1:stage_words(1,2); // PAGE1 ahead of page0 forbidden
          2:begin
              neuron0[63]=32'd1; // skip expected tick0
              stage_words(0,1);
            end
          3:begin
              neuron0[2]=32'd0; // invalid positive threshold
              stage_words(0,1);
            end
          4:stage_words(0,1); // withheld bank compute-ack watchdog
        endcase
        if(cas==4) force dut.compute_ack=1'b0;
        axi_write(12'h014,32'h4,4'hf,1,2'b00);
      end
      expect_poison(cas);
      if(cas==4) release dut.compute_ack;
      // Restore independent source input for next regression scenario.
      if(cas==2) neuron0[63]=0;
      if(cas==3) $readmemh(page0_file,neuron0);
    end
    $display("M08_PAGED_LIF_MISSING_SETUP_PAGE_TICK_THRESHOLD_TIMEOUT_BAD_EDGE_REAL_RTL_POISON_PASS");
    $finish;
  end
  initial begin
    #80000000;$fatal(1,"M08_PAGED_LIF_FAIL_CLOSED_GLOBAL_TIMEOUT");
  end
endmodule
