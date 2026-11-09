// M06 REAL RTL residency FSM + AXI256 block mover + INDEPENDENT
// single-beat 256-bit memory BFM. This does NOT instantiate AMD IP.
// Tests 256B dirty block eviction/writeback/reload with 1 resident slot,
// byte-lane preserved, 4KiB-safe addresses and failed-read quarantine.
`timescale 1ns/1ps
module tb_m06_paged_lif16;
  // Independent Python M02 dense fixtures generated into this .vh by CI.
  // Neuron state occupies 16B (2 neurons per 256b AXI word, 16/page).
  reg signed [15:0] initial_v [0:31];
  reg signed [15:0] neuron_bias [0:31];
  reg signed [15:0] neuron_threshold [0:31];
  reg signed [15:0] neuron_reset [0:31];
  reg signed [31:0] routed_current [0:127];
  reg signed [15:0] oracle_v [0:127];
  reg oracle_spike [0:127];
  reg signed [15:0] lif_previous=0, lif_bias=0, lif_threshold=1,
                    lif_reset=0;
  reg signed [31:0] lif_current=0;
  wire signed [15:0] lif_next;
  wire lif_spike, lif_invalid;
  m06_lif16_neuron_step neural_lane (
    .previous_voltage(lif_previous), .bias(lif_bias),
    .threshold(lif_threshold), .reset_voltage(lif_reset),
    .summed_current(lif_current),
    .decay_num(32'd3), .decay_den(32'd4),
    .next_voltage(lif_next), .spike(lif_spike),
    .invalid_params(lif_invalid)
  );
  `include "m06_lif16_vectors.vh"
  integer tick_idx, neuron_id, word_idx, offset_bytes;
  integer neural_updates=0, neural_spikes=0;
  reg [255:0] edited_record_word=0;
  reg [31:0] edited_record_strobe=0;
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
  reg [2:0] client_idx=0;
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

  m06_residency_control_fsm #(.MAX_WAIT_CYCLES(32'd128)) controller (
    .aclk(clk),.aresetn(resetn),
    .req_valid(req_valid),.req_ready(req_ready),
    .req_block(req_block),.req_is_write(req_write),
    .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),
    .rsp_error(rsp_error),.rsp_block(rsp_block),
    .dma_valid(dma_valid),.dma_ready(dma_ready),
    .dma_is_writeback(dma_is_writeback),.dma_block(dma_block),
    .dma_done(dma_done),.dma_error(dma_error),
    .poisoned(poisoned),.resident_valid(resident_valid),
    .resident_block(resident_block),.resident_dirty(resident_dirty),
    .accesses(accesses),.hits(hits),.misses(misses),
    .acknowledged_writebacks(acknowledged_writebacks),
    .acknowledged_fills(acknowledged_fills),
    .stalled_cycles(stalled_cycles)
  );
  m06_axi256_block_transfer #(
    .MAX_BLOCKS(32),.MAX_WAIT_CYCLES(32'd128)
  ) mover (
    .clk(clk),.resetn(resetn),
    .cmd_valid(dma_valid),.cmd_ready(dma_ready),
    .cmd_is_writeback(dma_is_writeback),.cmd_block(dma_block),
    .cmd_done(dma_done),.cmd_error(dma_error),.busy(busy),
    .client_word_index(client_idx),.client_word_data(client_rdata),
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
      end
    end
  endtask

  initial begin
    // M02 oracle fixture is loaded before canonical DRAM memory is seeded.
    load_m06_lif_vectors();
    for(word_i=0;word_i<256;word_i=word_i+1) begin
      canonical[word_i]=256'd0;
      expected[word_i]=256'd0;
    end
    for(neuron_id=0;neuron_id<32;neuron_id=neuron_id+1) begin
      word_idx=neuron_id/2;
      offset_bytes=(neuron_id%2)*16;
      canonical[word_idx][8*offset_bytes+:16]=initial_v[neuron_id];
      expected[word_idx][8*offset_bytes+:16]=initial_v[neuron_id];
    end
    repeat(6) @(negedge clk); resetn=1;
    for(tick_idx=0;tick_idx<4;tick_idx=tick_idx+1) begin
      for(neuron_id=0;neuron_id<32;neuron_id=neuron_id+1) begin
        // 16 neurons/block. Two blocks, one physical 256B resident slot.
        // Every logical timestep forces at least one dirty eviction.
        if (neuron_id % 16 == 0)
          demand(neuron_id/16,1,0);
        word_idx=(neuron_id%16)/2;
        offset_bytes=(neuron_id%2)*16;
        client_idx=word_idx;
        @(negedge clk);
        lif_previous=$signed(client_rdata[8*offset_bytes+:16]);
        lif_bias=neuron_bias[neuron_id];
        lif_threshold=neuron_threshold[neuron_id];
        lif_reset=neuron_reset[neuron_id];
        lif_current=routed_current[tick_idx*32+neuron_id];
        if (client_rdata[8*(offset_bytes+2)+:32] !== tick_idx)
          $fatal(1,"M06_PAGED_LIF16_FAIL TIME_METADATA t=%0d neuron=%0d got=%0d",
                 tick_idx,neuron_id,client_rdata[8*(offset_bytes+2)+:32]);
        #1;
        if (lif_invalid || lif_next !== oracle_v[tick_idx*32+neuron_id]
            || lif_spike !== oracle_spike[tick_idx*32+neuron_id])
          $fatal(1,"M06_PAGED_LIF16_FAIL M02_NUMERIC_PARITY t=%0d n=%0d prev=%0d I=%0d v=%0d want=%0d spike=%b want=%b",
                 tick_idx,neuron_id,lif_previous,lif_current,lif_next,
                 oracle_v[tick_idx*32+neuron_id],lif_spike,
                 oracle_spike[tick_idx*32+neuron_id]);
        neural_spikes=neural_spikes+lif_spike;
        edited_record_word=256'd0;
        edited_record_strobe=32'd0;
        edited_record_word[8*offset_bytes+:16]=lif_next;
        edited_record_word[8*(offset_bytes+2)+:32]=tick_idx+1;
        for(byte_i=0;byte_i<6;byte_i=byte_i+1)
          edited_record_strobe[offset_bytes+byte_i]=1'b1;
        @(negedge clk);
        client_wdata=edited_record_word;
        client_wstrb=edited_record_strobe;
        client_wr=1;
        @(posedge clk);
        @(negedge clk);
        client_wr=0;
        expected[neuron_id/2][8*offset_bytes+:16]=
            oracle_v[tick_idx*32+neuron_id];
        expected[neuron_id/2][8*(offset_bytes+2)+:32]=tick_idx+1;
        if (client_rdata !== expected[neuron_id/2])
          $fatal(1,"M06_PAGED_LIF16_FAIL BYTE_RECORD_UPDATE t=%0d neuron=%0d",
                 tick_idx,neuron_id);
        neural_updates=neural_updates+1;
      end
    end
    // Final dirty-page flush by switching to clean page0, then reload page1
    // and check that *all* 32 logical canonical neuron records survived.
    demand(0,0,0);
    for(word_i=0;word_i<16;word_i=word_i+1)
      if (canonical[word_i] !== expected[word_i])
        $fatal(1,"M06_PAGED_LIF16_FAIL CANONICAL_WB word=%0d",
               word_i);
    for(word_i=0;word_i<8;word_i=word_i+1) begin
      client_idx=word_i;
      @(negedge clk);
      if (client_rdata !== expected[word_i])
        $fatal(1,"M06_PAGED_LIF16_FAIL RELOADED_PAGE0 word=%0d",word_i);
    end
    demand(1,0,0);
    for(word_i=0;word_i<8;word_i=word_i+1) begin
      client_idx=word_i;
      @(negedge clk);
      if (client_rdata !== expected[8+word_i])
        $fatal(1,"M06_PAGED_LIF16_FAIL RELOADED_PAGE1 word=%0d",word_i);
    end
    demand(1,0,0); // clean page hit, no additional canonical AXI
    if(neural_updates !== 128 || neural_spikes < 1 ||
       accesses !== 11 || hits !== 1 || misses !== 10 ||
       acknowledged_writebacks !== 8 || acknowledged_fills !== 10 ||
       accepted_ar !== 80 || accepted_r !== 80 ||
       accepted_aw !== 64 || accepted_w !== 64 || accepted_b !== 64)
      $fatal(1,"M06_PAGED_LIF16_FAIL COUNTS updates=%0d spikes=%0d a=%0d h=%0d m=%0d wb=%0d fills=%0d ar=%0d aw=%0d",
             neural_updates,neural_spikes,accesses,hits,misses,
             acknowledged_writebacks,acknowledged_fills,
             accepted_ar,accepted_aw);
    $display("M06_PAGED_LIF16_M02_RTL_PARITY_PASS neurons=32 ticks=4 updates=%0d spikes=%0d fills=10 wb=8 ar=80 aw=64 resident_slots=1 ORIGINAL_M05_HLS_NOT_CONNECTED",
             neural_updates,neural_spikes);
    inject_read_error=1;
    demand(2,0,1);
    if(!poisoned || req_ready || acknowledged_fills !== 10)
      $fatal(1,"M06_PAGED_LIF16_FAIL ERROR_QUARANTINE");
    $display("M06_PAGED_LIF16_FAULT_QUARANTINE_PASS no_real_DDR=1");
    $finish;
  end
  initial begin
    #2000000;
    $fatal(1,"M06_AXIBRIDGE_GLOBAL_WATCHDOG");
  end
endmodule
