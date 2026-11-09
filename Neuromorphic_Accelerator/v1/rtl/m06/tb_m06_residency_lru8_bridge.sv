// M06 REAL RTL residency FSM + AXI256 block mover + INDEPENDENT
// single-beat 256-bit memory BFM. This does NOT instantiate AMD IP.
// Tests 256B dirty block eviction/writeback/reload with 1 resident slot,
// byte-lane preserved, 4KiB-safe addresses and failed-read quarantine.
`timescale 1ns/1ps
module tb_m06_residency_lru8_bridge;
  reg clk=0;
  always #5 clk=~clk;
  reg resetn=0;
  reg req_valid=0, req_write=0, rsp_ready=0;
  reg [31:0] req_block=0;
  wire req_ready, rsp_valid, rsp_error, poisoned;
  wire [31:0] rsp_block;
  wire dma_valid, dma_ready, dma_is_writeback, dma_done, dma_error;
  wire [31:0] dma_block;
  wire resident_valid, resident_dirty;
  wire [31:0] resident_block;
  wire [31:0] accesses,hits,misses,acknowledged_writebacks,
               acknowledged_fills,stalled_cycles;
  reg [2:0] client_idx=0,client_slot=0;
  wire [2:0] dma_slot,rsp_slot;
  wire [31:0] evictions;
  reg client_wr=0;
  reg [255:0] client_wdata=0;
  reg [31:0] client_wstrb=0;
  wire [255:0] client_rdata;
  wire busy;
  wire [31:0] araddr,awaddr;
  wire [7:0] arlen,awlen;
  wire [2:0] arsize,awsize;
  wire [1:0] arburst,awburst;
  wire arlock,awlock,arvalid,arready,rvalid,rready,rlast;
  wire awvalid,awready,wvalid,wready,wlast,bvalid,bready;
  wire [3:0] arcache,awcache,arqos,awqos;
  wire [2:0] arprot,awprot;
  wire [255:0] rdata,wdata;
  wire [31:0] wstrb;
  reg [1:0] rresp=0,bresp=0;
  wire [31:0] accepted_ar,accepted_r,accepted_aw,accepted_w,
              accepted_b,wait_stalls;
  reg [255:0] canonical [0:255];
  reg [255:0] expected [0:255];
  reg model_rvalid=0,model_bvalid=0,model_rlast=0;
  reg [255:0] model_rdata=0;
  reg [31:0] model_waddr=0;
  reg have_aw=0, inject_read_error=0, inject_write_error=0;
  integer cycles=0;
  integer byte_i, word_i;
  reg [255:0] new_data=256'hffeeddccbbaa99887766554433221100_00112233445566778899aabbccddeeff;
  reg [31:0] byte_mask=32'h80010001;

  m06_residency_lru8 #(.MAX_WAIT_CYCLES(32'd128)) controller (
    .clk(clk),.resetn(resetn),
    .req_valid(req_valid),.req_ready(req_ready),
    .req_block(req_block),.req_is_write(req_write),
    .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),
    .rsp_error(rsp_error),.rsp_block(rsp_block),.rsp_slot(rsp_slot),
    .dma_valid(dma_valid),.dma_ready(dma_ready),
    .dma_is_writeback(dma_is_writeback),.dma_block(dma_block),
    .dma_slot(dma_slot),
    .dma_done(dma_done),.dma_error(dma_error),
    .poisoned(poisoned),
    .accesses(accesses),.hits(hits),.misses(misses),
    .evictions(evictions),
    .acknowledged_writebacks(acknowledged_writebacks),
    .acknowledged_fills(acknowledged_fills),
    .stalled_cycles(stalled_cycles)
  );
  m06_axi256_multislot_transfer #(
    .MAX_BLOCKS(32),.MAX_WAIT_CYCLES(32'd128)
  ) mover (
    .clk(clk),.resetn(resetn),
    .cmd_valid(dma_valid),.cmd_ready(dma_ready),
    .cmd_is_writeback(dma_is_writeback),.cmd_block(dma_block),
    .cmd_slot(dma_slot),
    .cmd_done(dma_done),.cmd_error(dma_error),.busy(busy),
    .client_word_index(client_idx),.client_slot(client_slot),
    .client_word_data(client_rdata),
    .client_write_enable(client_wr),.client_write_data(client_wdata),
    .client_write_strobe(client_wstrb),
    .s00_araddr(araddr),.s00_arlen(arlen),.s00_arsize(arsize),
    .s00_arburst(arburst),.s00_arlock(arlock),.s00_arcache(arcache),
    .s00_arprot(arprot),.s00_arqos(arqos),
    .s00_arvalid(arvalid),.s00_arready(arready),
    .s00_rdata(rdata),.s00_rresp(rresp),.s00_rlast(rlast),
    .s00_rvalid(rvalid),.s00_rready(rready),
    .s03_awaddr(awaddr),.s03_awlen(awlen),.s03_awsize(awsize),
    .s03_awburst(awburst),.s03_awlock(awlock),.s03_awcache(awcache),
    .s03_awprot(awprot),.s03_awqos(awqos),
    .s03_awvalid(awvalid),.s03_awready(awready),
    .s03_wdata(wdata),.s03_wstrb(wstrb),.s03_wlast(wlast),
    .s03_wvalid(wvalid),.s03_wready(wready),
    .s03_bresp(bresp),.s03_bvalid(bvalid),.s03_bready(bready),
    .accepted_ar(accepted_ar),.accepted_r(accepted_r),
    .accepted_aw(accepted_aw),.accepted_w(accepted_w),
    .accepted_b(accepted_b),.wait_stalls(wait_stalls)
  );
  assign arready=resetn && !model_rvalid && (cycles%3 != 1);
  assign rvalid=model_rvalid;
  assign rlast=model_rlast;
  assign rdata=model_rdata;
  assign awready=resetn && !have_aw && !model_bvalid && (cycles%3 != 1);
  assign wready=resetn && have_aw && !model_bvalid && (cycles%3 != 2);
  assign bvalid=model_bvalid;

  integer lane;
  always @(posedge clk) begin
    if (!resetn) begin
      cycles<=0;
      have_aw<=0;
      model_rvalid<=0;
      model_bvalid<=0;
      model_rlast<=0;
      model_rdata<=0;
      rresp<=0;
      bresp<=0;
    end else begin
      cycles<=cycles+1;
      if(arvalid && arready) begin
        if(araddr[4:0]!=0 || araddr>=8192 ||
           arlen!=0 || arsize!=5 || arburst!=2'b01)
          $fatal(1,"M06_AXIBRIDGE_BAD_READ_PROTOCOL");
        model_rdata<=canonical[araddr>>5];
        rresp<=inject_read_error ? 2'b10 : 2'b00;
        model_rlast<=1;
        model_rvalid<=1;
      end
      if(model_rvalid && rready) begin
        model_rvalid<=0;
        model_rlast<=0;
      end
      if(awvalid && awready) begin
        if(awaddr[4:0]!=0 || awaddr>=8192 ||
           awlen!=0 || awsize!=5 || awburst!=2'b01)
          $fatal(1,"M06_AXIBRIDGE_BAD_WRITE_PROTOCOL");
        model_waddr<=awaddr;
        have_aw<=1;
      end
      if(wvalid && wready) begin
        if(wstrb!==32'hffffffff || !wlast)
          $fatal(1,"M06_AXIBRIDGE_BAD_WLAST_WSTRB");
        for(lane=0;lane<32;lane=lane+1)
          if(wstrb[lane])
            canonical[model_waddr>>5][8*lane+:8]
              <=wdata[8*lane+:8];
        have_aw<=0;
        model_bvalid<=1;
        bresp<=inject_write_error ? 2'b10 : 2'b00;
      end
      if(model_bvalid && bready)
        model_bvalid<=0;
    end
  end

  task automatic demand(input [31:0] block_num,
                        input is_write,input expect_error);
    integer k;
    begin
      @(negedge clk);
      if(!req_ready || poisoned)
        $fatal(1,"M06_AXIBRIDGE_BAD_FSM_READY");
      req_block=block_num;
      req_write=is_write;
      req_valid=1;
      @(posedge clk);
      if(!req_ready) $fatal(1,"M06_AXIBRIDGE_LOST_REQUEST");
      @(negedge clk); req_valid=0;
      for(k=0; k<1500 && !rsp_valid; k=k+1) @(negedge clk);
      if(!rsp_valid)
        $fatal(1,"M06_AXIBRIDGE_TIMEOUT");
      if(rsp_error !== expect_error || rsp_block !== block_num)
        $fatal(1,"M06_AXIBRIDGE_WRONG_RESPONSE block=%d err=%b",rsp_block,rsp_error);
      if(!expect_error) begin
        @(negedge clk); rsp_ready=1;
        @(posedge clk);
        if(!rsp_valid) $fatal(1,"M06_AXIBRIDGE_RESPONSE_EARLY");
        @(negedge clk); rsp_ready=0;
        client_slot=rsp_slot;
      end
    end
  endtask

  integer page_i;
  reg [2:0] slot_page0=0;
  initial begin
    for(word_i=0;word_i<256;word_i=word_i+1) begin
      canonical[word_i]=0;
      expected[word_i]=0;
      for(byte_i=0;byte_i<32;byte_i=byte_i+1) begin
        canonical[word_i][8*byte_i+:8]=(13*(32*word_i+byte_i)+17)&255;
        expected[word_i][8*byte_i+:8]=(13*(32*word_i+byte_i)+17)&255;
      end
    end
    repeat(6) @(negedge clk);resetn=1;
    // Fill all 8 physical slots. Only the first two are dirty.
    for(page_i=0;page_i<8;page_i=page_i+1) begin
      demand(page_i, (page_i==0 || page_i==1), 0);
      if(rsp_slot !== page_i[2:0])
        $fatal(1,"M06_LRU8_FAIL SLOT_INITIAL_MAPPING page=%0d slot=%0d",
               page_i,rsp_slot);
    end
    client_idx=3;client_slot=0;
    @(negedge clk);
    if(client_rdata !== expected[3])
      $fatal(1,"M06_LRU8_FAIL FIRST_PAGE_DATA");
    client_wdata=new_data;client_wstrb=byte_mask;client_wr=1;
    @(posedge clk);
    for(byte_i=0;byte_i<32;byte_i=byte_i+1)
      if(byte_mask[byte_i])
        expected[3][8*byte_i+:8]=new_data[8*byte_i+:8];
    @(negedge clk);client_wr=0;
    if(client_rdata !== expected[3])
      $fatal(1,"M06_LRU8_FAIL LOCAL_MASKED_EDIT");
    // Touch slot0 so slot1 becomes true LRU. Page8 is the NINTH page.
    demand(0,1,0);
    demand(8,0,0);
    if(rsp_slot !== 1 || acknowledged_writebacks !== 1 ||
       evictions !== 1)
      $fatal(1,"M06_LRU8_FAIL DIRTY_LRU_VICTIM");
    if(canonical[8+3] !== expected[8+3])
      $fatal(1,"M06_LRU8_FAIL DIRTY_PAGE1_WB");
    // A page0 hit must preserve the edited bytes while slot0 is resident.
    demand(0,0,0);
    client_idx=3;client_slot=rsp_slot;
    @(negedge clk);
    if(client_rdata !== expected[3])
      $fatal(1,"M06_LRU8_FAIL NO_HIT_REUSE");
    // Circular sweep eventually evicts page0: its dirty bytes must reach
    // canonical memory, despite ALL eight slots being full.
    for(page_i=9;page_i<=17;page_i=page_i+1)
      demand(page_i,0,0);
    if(canonical[3] !== expected[3])
      $fatal(1,"M06_LRU8_FAIL PERSISTED_DIRTY_PAGE0_WB");
    demand(0,0,0);
    client_idx=3;client_slot=rsp_slot;
    @(negedge clk);
    if(client_rdata !== expected[3])
      $fatal(1,"M06_LRU8_FAIL EXACT_RELOADED_VOLTS");
    if(accesses !== 21 || hits !== 2 || misses !== 19 ||
       evictions !== 11 || acknowledged_fills !== 19 ||
       acknowledged_writebacks !== 2 ||
       accepted_ar !== 152 || accepted_r !== 152 ||
       accepted_aw !== 16 || accepted_w !== 16 || accepted_b !== 16)
      $fatal(1,"M06_LRU8_FAIL REAL_DMA_COUNTS a=%0d h=%0d m=%0d evict=%0d WB=%0d fills=%0d AR=%0d AW=%0d",
             accesses,hits,misses,evictions,acknowledged_writebacks,
             acknowledged_fills,accepted_ar,accepted_aw);
    $display("M06_LRU8_AXIBRIDGE_RTL_PASS physical_slots=8 resident_bytes=2048 fills=19 WB=2 evictions=11 AR=152 AW=16");
    inject_read_error=1;
    demand(18,0,1);
    if(!poisoned || req_ready || acknowledged_fills !== 19 ||
       acknowledged_writebacks !== 2 || accepted_ar !== 153)
      $fatal(1,"M06_LRU8_FAIL STICKY_FAULT");
    $display("M06_LRU8_FAULT_QUARANTINE_RTL_PASS M00_MODEL_ONLY NO_DDR_BOARD");
    $finish;
  end
  initial begin
    #1000000;
    $fatal(1,"M06_AXIBRIDGE_GLOBAL_WATCHDOG");
  end
endmodule
