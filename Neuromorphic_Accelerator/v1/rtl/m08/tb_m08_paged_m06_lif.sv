// M08.2b.2 Icarus standalone AXI4-Lite BFM, no AMD IP or KV260 hardware.
// Checks real bus handshakes, stalls, partial byte lanes, ownership, poison.
`timescale 1ns/1ps
module tb_m08_paged_m06_lif;
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
  task automatic stage_and_dispatch_edges;
    integer j,cycles;
  begin
    axi_write(12'h010,32'hffffffff,4'hf,0,2'b00);
    axi_write(12'h014,32'h1,4'hf,1,2'b00);
    for(j=0;j<64;j=j+1)
      axi_write(12'h100+j*4,edge_words[j],4'hf,j%3,2'b00);
    axi_read(12'h01c,32'd256,2'b00);
    for(j=0;j<64;j=j+1)
      axi_read(12'h100+j*4,edge_words[j],2'b00);
    axi_write(12'h014,32'h2,4'hf,2,2'b00);
    axi_write(12'h014,32'h4,4'hf,1,2'b00);
    cycles=0;
    while(dut.page_adapter.bank_phase!==3'd4 && cycles<1200) begin
      @(negedge clk);cycles=cycles+1;
    end
    if(cycles>=1200 || !dut.neural_engine.edge_configured ||
       dut.neural_engine.edge_count!==5 ||
       dut.neural_engine.expected_page!==0 ||
       dut.neural_engine.expected_tick!==0)
      $fatal(1,"M08_PAGED_M06_EDGE_CONFIGURATION_NO_REAL_RTL_ACK");
    for(j=0;j<64;j=j+1)
      axi_read(12'h100+j*4,edge_words[j],2'b00);
    axi_write(12'h014,32'h8,4'hf,0,2'b00);
    $display("M08_PAGED_M06_ON_FABRIC_RECURRENT_EDGE_SETUP_5_PASS");
  end
  endtask

  task automatic execute_one_neural_page(input integer tick,input integer page);
    integer j,local_idx,n,field,source_slot,cycles,count;
    reg [31:0] want,readback_mask;
  begin
    count=(page==5)?2:6;
    // This is a host-OWNED backing context. Only the tick field changes
    // between staging rounds. All prior dynamic state was saved from
    // actual Icarus bank readbacks at the previous tick.
    backing[page*64+63]=tick;
    axi_write(12'h010,page,4'hf,0,2'b00);
    axi_write(12'h014,32'h1,4'hf,1,2'b00);
    for(j=0;j<64;j=j+1)
      axi_write(12'h100+j*4,backing[page*64+j],4'hf,j%3,2'b00);
    axi_read(12'h01c,32'd256,2'b00);
    for(j=0;j<64;j=j+1)
      axi_read(12'h100+j*4,backing[page*64+j],2'b00);
    // Check the 128 external current inputs independently here, not
    // only via the page source-generator's Python test.
    for(local_idx=0;local_idx<count;local_idx=local_idx+1) begin
      n=page*6+local_idx;
      source_slot=tick*128+n*4;
      if(backing[page*64+local_idx*10+4+tick]!==golden[source_slot])
        $fatal(1,"M08_PAGED_M06_RAW_EVENT_BUCKET_ORACLE_INPUT_MISMATCH tick=%0d neuron=%0d",
                 tick,n);
      verified_input_currents=verified_input_currents+1;
    end
    axi_write(12'h014,32'h2,4'hf,2,2'b00);
    axi_write(12'h014,32'h4,4'hf,1,2'b00);
    cycles=0;
    while(dut.page_adapter.bank_phase!==3'd4 && cycles<3000) begin
      @(negedge clk);cycles=cycles+1;
    end
    if(cycles>=3000 || page_poisoned)
      $fatal(1,"M08_PAGED_M06_LIF_DISPATCH_FAILED tick=%0d page=%0d",
             tick,page);
    // Dirty page: independently read all sixty-four on-fabric words
    // BEFORE asserting SAVE. No oracle output was preloaded.
    for(j=0;j<64;j=j+1) begin
      want=backing[page*64+j];
      if(j<count*10) begin
        local_idx=j/10;
        field=j%10;
        n=page*6+local_idx;
        source_slot=tick*128+n*4;
        if(field==0) begin
          want=golden[source_slot+1]; // actual signed16 membrane
          verified_voltages=verified_voltages+1;
        end else if(field==8) begin
          readback_mask=expected_masks[n] |
                         ((golden[source_slot+2]&1)<<tick);
          want=readback_mask;
          expected_masks[n]=readback_mask[3:0];
          verified_spikes=verified_spikes+1;
        end else if(field==9) begin
          want=golden[source_slot+3]; // actual on-fabric syn current
          verified_syn_currents=verified_syn_currents+1;
        end
      end
      axi_read(12'h100+j*4,want,2'b00);
      backing[page*64+j]=want;
    end
    axi_write(12'h014,32'h8,4'hf,0,2'b00);
    axi_read(12'h00c,32'h00000012,2'b00);
    $display("M08_PAGED_M06_REAL_256B_STATE_LOAD_COMPUTE_DIRTY_SAVE_PASS|%0d|%0d",
             tick,page);
  end
  endtask

  integer t,p,n;
  initial begin
    if(!$value$plusargs("edge=%s",filename_edges) ||
       !$value$plusargs("golden=%s",filename_golden) ||
       !$value$plusargs("page0=%s",filename0) ||
       !$value$plusargs("page1=%s",filename1) ||
       !$value$plusargs("page2=%s",filename2) ||
       !$value$plusargs("page3=%s",filename3) ||
       !$value$plusargs("page4=%s",filename4) ||
       !$value$plusargs("page5=%s",filename5))
      $fatal(1,"M08_PAGED_M06_INDEPENDENT_ORIGINAL_M02_M03_INPUT_FILES_REQUIRED");
    $readmemh(filename_edges,edge_words);
    $readmemh(filename_golden,golden);
    $readmemh(filename0,backing,0,63);
    $readmemh(filename1,backing,64,127);
    $readmemh(filename2,backing,128,191);
    $readmemh(filename3,backing,192,255);
    $readmemh(filename4,backing,256,319);
    $readmemh(filename5,backing,320,383);
    for(n=0;n<32;n=n+1) expected_masks[n]=0;
    reset_all();
    axi_read(12'h000,32'h4d303850,2'b00);
    axi_read(12'h004,32'h00020002,2'b00);
    stage_and_dispatch_edges();
    for(t=0;t<4;t=t+1) begin
      for(p=0;p<6;p=p+1)
        execute_one_neural_page(t,p);
      if(dut.neural_engine.expected_tick!==t+1 ||
         dut.neural_engine.expected_page!==0)
        $fatal(1,"M08_PAGED_M06_FOUR_TICK_SERVICE_BARRIER_MISSING tick=%0d",t);
      $display("M08_PAGED_M06_TICK_BARRIER_NO_MIXED_EPOCH_PASS|%0d",t);
    end
    if(verified_input_currents!=128 ||
       verified_voltages!=128 ||
       verified_spikes!=128 ||
       verified_syn_currents!=128 ||
       dut.neural_engine.completed_neurons!==32'd128 ||
       dut.neural_engine.completed_pages!==32'd24)
      $fatal(1,"M08_PAGED_M06_512_COMPARE_COUNT_DRIFT input=%0d v=%0d spike=%0d syn=%0d neural=%d pages=%d",
             verified_input_currents,verified_voltages,verified_spikes,
             verified_syn_currents,dut.neural_engine.completed_neurons,
             dut.neural_engine.completed_pages);
    for(n=0;n<32;n=n+1)
      if(dut.neural_engine.global_spikes[n]!==expected_masks[n])
        $fatal(1,"M08_PAGED_M06_FABRIC_RECURRENT_HISTORY_DRIFT neuron=%0d",n);
    if(dut.neural_engine.computed_synaptic_events===0)
      $fatal(1,"M08_PAGED_M06_REAL_POSITIVE_DELAY_RECURRENT_FIRING_NOT_EXERCISED");
    $display("M08_PAGED_M06_ONE_RESIDENT_SIX_LOGICAL_NEURAL_PAGES_24_REAL_DISPATCHES_PASS");
    $display("M08_PAGED_M06_REAL_FABRIC_128_CURRENT_128_VOLTAGE_128_SPIKE_128_RECURRENT_M02_M03_PASS");
    $display("M08_PAGED_M06_512_REAL_IVERILOG_PARITY_NO_K26_NO_DDR_NO_RAW_FIFO_PASS");
    $finish;
  end
  initial begin
    #80000000;
    $fatal(1,"M08_PAGED_M06_NEURAL_GLOBAL_TIMEOUT");
  end
endmodule
