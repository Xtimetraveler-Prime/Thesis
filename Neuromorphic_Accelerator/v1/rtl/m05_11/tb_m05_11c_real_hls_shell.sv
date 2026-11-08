// M05.11c: END-TO-END *REAL GENERATED HLS VERILOG* + new AXI-Lite
// controller + 3 ingress 256->128/192 + trace 192->256 TLAST packetizer.
// No stub HLS model. The runner compiles this bench ONLY with original
// Vitis-generated m05_rolling_replay.v and all actual sibling modules.
// One HDL instance of each module. No PS, DDR, AMD DMA IP, device/board.
// Two runs WITHOUT fabric reset between them:
// run0: valid 12-tick 2-neuron replay, t0 n0 spike, recurrent t8 n1 spike,
//        24 transport rows + EXACT one terminal status0 TLAST, ACK success.
// run1: invalid external ticks 0,4,3, real BAD_EXTERNAL=4 after 8 provisional
//        rows, one terminal status4 TLAST, bridge sticky FAULT, no ACK/reuse.
// No changes to the signed32 HLS neural kernel, no fabricated HLS status.
`timescale 1ns/1ps
`include "m05_rolling_regmap.svh"

module tb_m05_11c_real_hls_shell;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0;
    wire interrupt;

    // Original Vivado HLS-generated AXI-Lite bank, register addresses from
    // m05_axis_regmap.py generated against THIS --impl artifact.
    reg [6:0] h_awaddr=0, h_araddr=0;
    reg h_awvalid=0, h_wvalid=0, h_bready=0;
    wire h_awready, h_wready, h_bvalid;
    reg [31:0] h_wdata=0;
    reg [3:0] h_wstrb=4'hf;
    wire [1:0] h_bresp, h_rresp;
    reg h_arvalid=0, h_rready=0;
    wire h_arready,h_rvalid;
    wire [31:0] h_rdata;

    // Independently addressed custom M05.11b transport-control AXI-Lite.
    reg [7:0] c_awaddr=0,c_araddr=0;
    reg [2:0] c_awprot=0,c_arprot=0;
    reg c_awvalid=0,c_wvalid=0,c_bready=0;
    wire c_awready,c_wready,c_bvalid;
    reg [31:0] c_wdata=0;
    reg [3:0] c_wstrb=4'hf;
    wire [1:0] c_bresp,c_rresp;
    reg c_arvalid=0,c_rready=0;
    wire c_arready,c_rvalid;
    wire [31:0] c_rdata;

    // Independent fixed-width 256-bit MM2S sources, all TKEEP=0xffffffff.
    reg [255:0] n_dma_data=0,s_dma_data=0,e_dma_data=0;
    reg n_dma_valid=0,s_dma_valid=0,e_dma_valid=0;
    reg n_dma_last=0,s_dma_last=0,e_dma_last=0;
    wire n_dma_ready,s_dma_ready,e_dma_ready;
    wire [127:0] n_hls_data,e_hls_data;
    wire [191:0] s_hls_data,trace_hls_data;
    wire n_hls_valid,s_hls_valid,e_hls_valid,trace_hls_valid;
    wire n_hls_ready,s_hls_ready,e_hls_ready,trace_hls_ready;

    wire [255:0] dma_trace_data;
    wire [31:0] dma_trace_keep;
    wire dma_trace_valid,dma_trace_last;
    wire [2:0] bridge_state;
    wire dma_trace_ready;

    integer cycle=0, run_epoch=0, n_sent=0,s_sent=0,e_sent=0;
    integer frame_rows=0, frame_footers=0, s2mm_stall_cycles=0;
    integer neuron_stalls=0, ext_stalls=0, packets_total=0;
    integer bridge_stalls=0;
    reg enable_feeds=0;
    reg prior_stall=0,prior_last=0;
    reg [255:0] prior_data=0;
    reg [31:0] prior_keep=0;

    localparam [63:0] MAGIC=64'h4d30353131454e44;
    localparam [63:0] SID_SUCCESS=64'h0102030405060708;
    localparam [63:0] SID_FAILURE=64'h1020304050607080;

    // Distinct values ensure exact native C HLS payload alignment.
    // native neuron: four signed i32 words (v0,bias,threshold,reset).
    wire [127:0] neuron_word={32'd0,32'd5,32'd0,32'd0};
    // native synapse: pre u32,post u32,weight i32, PAD32,delay u64.
    wire [191:0] synapse_word={64'd8,32'd0,32'd5,32'd1,32'd0};
    // native external: tick u64,ID u32,current i32.
    wire [127:0] external_word =
         run_epoch==0 ? {32'd5,32'd0,64'd0} :
         e_sent==0 ? {32'd5,32'd0,64'd0} :
         e_sent==1 ? {32'd5,32'd0,64'd4} :
                     {32'd5,32'd0,64'd3};

    // Every DMA source only changes its current word after a handshake.
    // Gate trace-TREADY 1/7 cycles to exercise REAL backpressure propagating
    // from 256b S2MM through shell down to unchanged 192b HLS kernel.
    assign dma_trace_ready = rst_n && cycle%7==0;

    m05_rolling_replay hls_dut(
        .ap_clk(clk),.ap_rst_n(rst_n),.interrupt(interrupt),
        .s_axi_control_AWADDR(h_awaddr),
        .s_axi_control_AWVALID(h_awvalid),
        .s_axi_control_AWREADY(h_awready),
        .s_axi_control_WDATA(h_wdata),
        .s_axi_control_WSTRB(h_wstrb),
        .s_axi_control_WVALID(h_wvalid),
        .s_axi_control_WREADY(h_wready),
        .s_axi_control_BRESP(h_bresp),
        .s_axi_control_BVALID(h_bvalid),
        .s_axi_control_BREADY(h_bready),
        .s_axi_control_ARADDR(h_araddr),
        .s_axi_control_ARVALID(h_arvalid),
        .s_axi_control_ARREADY(h_arready),
        .s_axi_control_RDATA(h_rdata),
        .s_axi_control_RRESP(h_rresp),
        .s_axi_control_RVALID(h_rvalid),
        .s_axi_control_RREADY(h_rready),
        .neurons_TDATA(n_hls_data),
        .neurons_TVALID(n_hls_valid),
        .neurons_TREADY(n_hls_ready),
        .synapses_TDATA(s_hls_data),
        .synapses_TVALID(s_hls_valid),
        .synapses_TREADY(s_hls_ready),
        .external_events_TDATA(e_hls_data),
        .external_events_TVALID(e_hls_valid),
        .external_events_TREADY(e_hls_ready),
        .trace_TDATA(trace_hls_data),
        .trace_TVALID(trace_hls_valid),
        .trace_TREADY(trace_hls_ready)
    );

    m05_11_stream_shell shell_dut(
        .clk(clk),.rst_n(rst_n),
        .s_axi_awaddr(c_awaddr),.s_axi_awprot(c_awprot),
        .s_axi_awvalid(c_awvalid),.s_axi_awready(c_awready),
        .s_axi_wdata(c_wdata),.s_axi_wstrb(c_wstrb),
        .s_axi_wvalid(c_wvalid),.s_axi_wready(c_wready),
        .s_axi_bresp(c_bresp),.s_axi_bvalid(c_bvalid),
        .s_axi_bready(c_bready),
        .s_axi_araddr(c_araddr),.s_axi_arprot(c_arprot),
        .s_axi_arvalid(c_arvalid),.s_axi_arready(c_arready),
        .s_axi_rdata(c_rdata),.s_axi_rresp(c_rresp),
        .s_axi_rvalid(c_rvalid),.s_axi_rready(c_rready),
        .n_dma_tdata(n_dma_data),.n_dma_tkeep(32'hffffffff),
        .n_dma_tlast(n_dma_last),.n_dma_tvalid(n_dma_valid),
        .n_dma_tready(n_dma_ready),
        .s_dma_tdata(s_dma_data),.s_dma_tkeep(32'hffffffff),
        .s_dma_tlast(s_dma_last),.s_dma_tvalid(s_dma_valid),
        .s_dma_tready(s_dma_ready),
        .e_dma_tdata(e_dma_data),.e_dma_tkeep(32'hffffffff),
        .e_dma_tlast(e_dma_last),.e_dma_tvalid(e_dma_valid),
        .e_dma_tready(e_dma_ready),
        .hls_neuron_tdata(n_hls_data),.hls_neuron_tvalid(n_hls_valid),
        .hls_neuron_tready(n_hls_ready),
        .hls_synapse_tdata(s_hls_data),.hls_synapse_tvalid(s_hls_valid),
        .hls_synapse_tready(s_hls_ready),
        .hls_external_tdata(e_hls_data),.hls_external_tvalid(e_hls_valid),
        .hls_external_tready(e_hls_ready),
        .hls_trace_tdata(trace_hls_data),.hls_trace_tvalid(trace_hls_valid),
        .hls_trace_tready(trace_hls_ready),
        .trace_dma_tdata(dma_trace_data),.trace_dma_tkeep(dma_trace_keep),
        .trace_dma_tvalid(dma_trace_valid),
        .trace_dma_tready(dma_trace_ready),
        .trace_dma_tlast(dma_trace_last),
        .session_state(bridge_state)
    );

    // Real AXIS input source models; honor stable VALID+TDATA during stalls.
    always @(posedge clk) begin
        if (!rst_n) begin
            cycle<=0;
            n_sent<=0;s_sent<=0;e_sent<=0;
            n_dma_valid<=0;s_dma_valid<=0;e_dma_valid<=0;
            frame_rows<=0;frame_footers<=0;packets_total<=0;
            s2mm_stall_cycles<=0;neuron_stalls<=0;ext_stalls<=0;
            prior_stall<=0;prior_data<=0;prior_last<=0;prior_keep<=0;
        end else begin
            cycle<=cycle+1;
            if(cycle>=250000)
                $fatal(1,"M05_11C_FAIL global timeout state=%0d run=%0d rows=%0d footers=%0d N/S/E=%0d/%0d/%0d",
                      bridge_state,run_epoch,frame_rows,frame_footers,
                      n_sent,s_sent,e_sent);
            if (n_dma_valid && n_dma_ready) begin
                n_sent<=n_sent+1;
                n_dma_valid<=0;
            end else if(!n_dma_valid && enable_feeds && n_sent<2
                        && cycle%7==2) n_dma_valid<=1;
            if (s_dma_valid && s_dma_ready) begin
                s_sent<=s_sent+1;
                s_dma_valid<=0;
            end else if(!s_dma_valid && enable_feeds && s_sent<1
                        && cycle%11==4) s_dma_valid<=1;
            if (e_dma_valid && e_dma_ready) begin
                e_sent<=e_sent+1;
                e_dma_valid<=0;
            end else if(!e_dma_valid && enable_feeds &&
                        e_sent<(run_epoch==0 ? 1 : 3)
                        && cycle%13==5) e_dma_valid<=1;

            // True transfer is TREADY && TVALID on the 256-bit DMA face.
            if(n_dma_valid && !n_dma_ready)
                neuron_stalls<=neuron_stalls+1;
            if(e_dma_valid && !e_dma_ready)
                ext_stalls<=ext_stalls+1;
            if(dma_trace_valid && !dma_trace_ready)
                s2mm_stall_cycles<=s2mm_stall_cycles+1;
            if(trace_hls_valid && !trace_hls_ready)
                bridge_stalls<=bridge_stalls+1;

            if(prior_stall && (!dma_trace_valid ||
               dma_trace_data !== prior_data ||
               dma_trace_last !== prior_last ||
               dma_trace_keep !== prior_keep))
                $fatal(1,"M05_11C_FAIL output TDATA/TKEEP/TLAST/TVALID changed while stalled");
            prior_stall<=dma_trace_valid && !dma_trace_ready;
            prior_data<=dma_trace_data;
            prior_last<=dma_trace_last;
            prior_keep<=dma_trace_keep;

            if(dma_trace_valid && dma_trace_ready) begin: check_dma
                integer t,n;
                reg expected_spike;
                reg [31:0] expected_count;
                reg [63:0] wanted_session;
                reg [31:0] wanted_status;
                if(dma_trace_keep !== 32'hffffffff)
                    $fatal(1,"M05_11C_FAIL invalid TKEEP");
                wanted_session=(run_epoch==0 ? SID_SUCCESS : SID_FAILURE);
                wanted_status=(run_epoch==0 ? 0 : 4);
                if(dma_trace_last) begin
                    if(frame_footers!=0 || dma_trace_data[255:192]!==MAGIC ||
                       dma_trace_data[191:128]!==wanted_session ||
                       dma_trace_data[127:96]!==wanted_status ||
                       dma_trace_data[95:64]!==frame_rows ||
                       dma_trace_data[63:0]!==0)
                        $fatal(1,"M05_11C_FAIL malformed footer or multiple TLAST run=%0d received=%0d raw=%h",
                               run_epoch,frame_rows,dma_trace_data);
                    if(frame_rows != (run_epoch==0 ? 24 : 8))
                        $fatal(1,"M05_11C_FAIL wrong data count at TLAST");
                    frame_footers<=frame_footers+1;
                    packets_total<=packets_total+1;
                    $display("M05_11C_FINAL run=%0d status=%0d rows=%0d committed=%0d session=%h tlast=1",
                             run_epoch,wanted_status,frame_rows,
                             (run_epoch==0?24:0),wanted_session);
                end else begin
                    if(frame_footers>0 || frame_rows>=(run_epoch==0?24:8))
                        $fatal(1,"M05_11C_FAIL extra trace after footer or run boundary");
                    t=frame_rows/2;
                    n=frame_rows%2;
                    expected_spike=(t==0 && n==0) ||
                                   (run_epoch==0 && t==8 && n==1);
                    expected_count=(t==0 || (run_epoch==0 && t==8))?1:0;
                    if(dma_trace_data[255:192]!==64'd0 ||
                       dma_trace_data[63:0]!==t ||
                       dma_trace_data[95:64]!==n ||
                       $signed(dma_trace_data[127:96])!==0 ||
                       dma_trace_data[135:128]!=={7'd0,expected_spike} ||
                       dma_trace_data[143:136]!=={7'd0,expected_spike} ||
                       dma_trace_data[191:160]!==expected_count)
                        $fatal(1,"M05_11C_FAIL neural trace misordered/corrupted run=%0d row=%0d raw=%h",
                               run_epoch,frame_rows,dma_trace_data);
                    frame_rows<=frame_rows+1;
                    $display("M05_11C_ROW run=%0d tick=%0d neuron=%0d voltage=0 spike=%0d evaluated=%0d delivered=%0d",
                             run_epoch,t,n,expected_spike,expected_spike,expected_count);
                end
            end
        end
    end

    // DMA simulator drives original native values, padded with high zero.
    // Use continuous assignments to prevent TDATA changes until counters
    // are advanced by accepted 256-bit AXIS handshakes.
    always @* begin
        n_dma_data={128'd0,neuron_word};
        s_dma_data={64'd0,synapse_word};
        e_dma_data={128'd0,external_word};
        n_dma_last=(n_sent==1);
        s_dma_last=1;
        e_dma_last=(e_sent==(run_epoch==0?0:2));
    end

    task automatic h_write(input [6:0] address,input [31:0] data);
        reg aw_done,w_done;
    begin
        aw_done=0;w_done=0;
        @(negedge clk);
        h_awaddr=address;h_wdata=data;h_awvalid=1;h_wvalid=1;h_bready=1;
        while(!aw_done || !w_done) begin
            @(posedge clk);
            if(h_awvalid && h_awready) aw_done=1;
            if(h_wvalid && h_wready) w_done=1;
            @(negedge clk);
            if(aw_done) h_awvalid=0;
            if(w_done) h_wvalid=0;
        end
        while(!h_bvalid) @(negedge clk);
        if(h_bresp!==2'b00)
            $fatal(1,"M05_11C_FAIL HLS AXI-Lite write failed addr=%h",address);
        @(negedge clk);
        h_bready=0;
    end
    endtask

    task automatic h_read(input [6:0] address,output [31:0] data);
        reg ar_done;
    begin
        ar_done=0;
        @(negedge clk);
        h_araddr=address;h_arvalid=1;h_rready=1;
        while(!ar_done) begin
            @(posedge clk);
            if(h_arvalid && h_arready) ar_done=1;
            @(negedge clk);
        end
        h_arvalid=0;
        while(!h_rvalid) @(negedge clk);
        data=h_rdata;
        if(h_rresp!==2'b00)
            $fatal(1,"M05_11C_FAIL HLS AXI-Lite read failed addr=%h",address);
        @(negedge clk);
        h_rready=0;
    end
    endtask

    task automatic c_write(input [7:0] address,input [31:0] data,
                           input [1:0] wanted_resp);
        reg aw_done,w_done;
    begin
        aw_done=0;w_done=0;
        @(negedge clk);
        c_awaddr=address;c_wdata=data;c_awvalid=1;c_wvalid=1;c_bready=1;
        while(!aw_done || !w_done) begin
            @(posedge clk);
            if(c_awvalid && c_awready) aw_done=1;
            if(c_wvalid && c_wready) w_done=1;
            @(negedge clk);
            if(aw_done) c_awvalid=0;
            if(w_done) c_wvalid=0;
        end
        while(!c_bvalid) @(negedge clk);
        if(c_bresp!==wanted_resp)
            $fatal(1,"M05_11C_FAIL bridge BRESP addr=%h observed=%h expected=%h",
                   address,c_bresp,wanted_resp);
        @(negedge clk);
        c_bready=0;
    end
    endtask

    task automatic c_read(input [7:0] address,output [31:0] data);
        reg ar_done;
    begin
        ar_done=0;
        @(negedge clk);
        c_araddr=address;c_arvalid=1;c_rready=1;
        while(!ar_done) begin
            @(posedge clk);
            if(c_arvalid && c_arready) ar_done=1;
            @(negedge clk);
        end
        c_arvalid=0;
        while(!c_rvalid) @(negedge clk);
        data=c_rdata;
        if(c_rresp!==2'b00)
            $fatal(1,"M05_11C_FAIL bridge read failed addr=%h",address);
        @(negedge clk);
        c_rready=0;
    end
    endtask

    task automatic setup_hls(input [31:0] external_count);
    begin
        h_write(`M05_ADDR_NEURON_COUNT_DATA,2);
        h_write(`M05_ADDR_SYNAPSE_COUNT_DATA,1);
        h_write(`M05_ADDR_EXTERNAL_COUNT_DATA,external_count);
        h_write(`M05_ADDR_TICKS_DATA,12);
        h_write(`M05_ADDR_DECAY_NUM_DATA,1);
        h_write(`M05_ADDR_DECAY_DEN_DATA,1);
    end
    endtask

    task automatic setup_bridge(input [63:0] session,
                                input [31:0] events);
        reg [31:0] d;
    begin
        c_write(8'h08,session[31:0],0);
        c_write(8'h0c,session[63:32],0);
        c_write(8'h10,24,0);
        c_write(8'h14,2,0);
        c_write(8'h18,1,0);
        c_write(8'h1c,events,0);
        c_read(8'h38,d);
        if(d!==32'h0005110b)
            $fatal(1,"M05_11C_FAIL unexpected bridge regmap version");
        c_write(8'h00,1,0);
        c_read(8'h04,d);
        if(d!==32'd1)
            $fatal(1,"M05_11C_FAIL bridge failed start");
    end
    endtask

    task automatic await_real_hls_status(output [31:0] result);
        reg [31:0] ctrl;
        integer i;
        reg done_seen;
    begin
        done_seen=0;
        for(i=0;i<600 && !done_seen;i=i+1) begin
            h_read(`M05_ADDR_AP_CTRL,ctrl);
            if(ctrl[1]) done_seen=1;
        end
        if(!done_seen)
            $fatal(1,"M05_11C_FAIL no real HLS ap_done");
        h_read(`M05_ADDR_AP_RETURN,result);
    end
    endtask

    task automatic finish_bridge(input [31:0] status,
                                 input [31:0] expected_state);
        reg [31:0] st;
        integer k;
    begin
        c_write(8'h20,status,0);
        c_write(8'h00,2,0);
        // The footer MUST be drained by the 256-bit S2MM sink before
        // expecting COMPLETE/FAULT. The HLS engine is already terminal.
        wait(frame_footers==1);
        for(k=0;k<100;k=k+1) begin
            c_read(8'h04,st);
            if(st==expected_state) k=100;
        end
        if(st!==expected_state)
            $fatal(1,"M05_11C_FAIL bridge terminal state observed=%0d expected=%0d",
                   st,expected_state);
    end
    endtask

    reg [31:0] hw_status, observed;
    initial begin
        repeat(8) @(negedge clk);
        rst_n=1;
        setup_hls(1);
        // Receive-first: no bus traffic until all output sinks are armed;
        // 256-bit testbench sink is permanently ready periodically.
        setup_bridge(SID_SUCCESS,1);
        enable_feeds=1;
        h_write(`M05_ADDR_AP_CTRL,1);
        // Don't block waiting on ap_done: the stream must drain until
        // all 24 valid trace rows are accepted under downstream stalls.
        wait(frame_rows==24);
        await_real_hls_status(hw_status);
        if(hw_status!==0)
            $fatal(1,"M05_11C_FAIL valid HLS run returned %0d",hw_status);
        finish_bridge(hw_status,3);
        if(frame_rows!=24 || frame_footers!=1 || n_sent!=2 ||
           s_sent!=1 || e_sent!=1)
            $fatal(1,"M05_11C_FAIL success DMA frame/count mismatch");
        c_read(8'h24,observed);
        if(observed!==24)
            $fatal(1,"M05_11C_FAIL success observed count");
        c_read(8'h28,observed);
        if(observed!==2)
            $fatal(1,"M05_11C_FAIL neuron accepted count");
        c_read(8'h2c,observed);
        if(observed!==1)
            $fatal(1,"M05_11C_FAIL synapse accepted count");
        c_read(8'h30,observed);
        if(observed!==1)
            $fatal(1,"M05_11C_FAIL external accepted count");
        c_write(8'h00,4,0);
        c_read(8'h04,observed);
        if(observed!==0)
            $fatal(1,"M05_11C_FAIL success ACK did not return idle");
        $display("M05_11C_COMMIT run=0 accepted_rows=24");

        // Run1 uses same un-reset physical simulated HLS and transport.
        // All source counters are TESTBENCH-owned, not hidden kernel state.
        @(negedge clk);
        enable_feeds=0;
        if(n_dma_valid || s_dma_valid || e_dma_valid)
            $fatal(1,"M05_11C_FAIL residual ingress after success");
        run_epoch=1;
        n_sent=0;s_sent=0;e_sent=0;
        frame_rows=0;frame_footers=0;
        prior_stall=0;
        setup_hls(3);
        setup_bridge(SID_FAILURE,3);
        enable_feeds=1;
        h_write(`M05_ADDR_AP_CTRL,1);
        wait(frame_rows==8);
        await_real_hls_status(hw_status);
        if(hw_status!==4)
            $fatal(1,"M05_11C_FAIL expected HLS BAD_EXTERNAL=4, got %0d",
                   hw_status);
        finish_bridge(hw_status,4);
        if(frame_rows!=8 || frame_footers!=1 || n_sent!=2 ||
           s_sent!=1 || e_sent!=3)
            $fatal(1,"M05_11C_FAIL failed DMA frame/count mismatch");
        c_write(8'h00,4,2);  // fail-closed: cannot ACK failed session
        c_write(8'h00,1,2);  // fail-closed: cannot restart after failure
        if(packets_total!=2 || s2mm_stall_cycles<20 || bridge_stalls<20)
            $fatal(1,"M05_11C_FAIL packet total or output backpressure absent");
        repeat(30) @(negedge clk);
        if(frame_rows!=8 || frame_footers!=1)
            $fatal(1,"M05_11C_FAIL stale/extra DMA output after failure");
        $display("M05_11C_COMMIT run=1 accepted_rows=0");
        $display("PASS: M05.11c REAL HLS RTL + AXIL shell + 3 ingress + trace TLAST; success=24/status0; failure=8/status4; committed=24+0; output_stalls=%0d; HLS_output_stalls=%0d",
                 s2mm_stall_cycles,bridge_stalls);
        $finish;
    end
endmodule
