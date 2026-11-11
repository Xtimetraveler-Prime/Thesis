// Icarus-only first-party hardware proof of host-owned one-page staging.
// This DOES NOT simulate PS AXI-Lite, AMD IP, physical DDR or the full SNN.
// Testbench uses M06's real first-party signed16 arithmetic module.
`timescale 1ns/1ps
module tb_m08_host_staged_page_bank;
    reg clk=0;
    always #5 clk=~clk;
    reg resetn=0;
    reg host_begin=0, host_req=0, host_write=0, host_commit=0,
        host_readback_verified=0, host_save_done=0;
    reg [31:0] host_begin_logical=0, host_wdata=0;
    reg [5:0] host_word=0;
    reg [3:0] host_wstrb=0;
    wire host_ack,host_error;
    wire [31:0] host_rdata;
    reg dispatch_req=0;
    reg [31:0] dispatch_logical=0;
    wire dispatch_accept;
    reg compute_req=0,compute_write=0,compute_done=0,compute_fault=0,
        fault_in=0;
    reg [5:0] compute_word=0;
    reg [31:0] compute_wdata=0;
    reg [3:0] compute_wstrb=0;
    wire compute_ack;
    wire [31:0] compute_rdata;
    wire [2:0] phase;
    wire poisoned,host_busy,compute_busy,page_valid,page_dirty;
    wire [31:0] page_logical;
    wire [8:0] loaded_byte_count;
    reg [31:0] copied_backing=0;
    integer dirty_index;
    integer negative_index;
    reg signed [15:0] lif_previous=0;
    wire signed [15:0] lif_next;
    wire lif_spike,lif_invalid;

    m08_host_staged_page_bank dut (
        .clk(clk),.resetn(resetn),
        .host_begin(host_begin),.host_begin_logical(host_begin_logical),
        .host_req(host_req),.host_write(host_write),.host_word(host_word),
        .host_wdata(host_wdata),.host_wstrb(host_wstrb),
        .host_commit(host_commit),.host_readback_verified(host_readback_verified),
        .host_save_done(host_save_done),
        .host_ack(host_ack),.host_error(host_error),.host_rdata(host_rdata),
        .dispatch_req(dispatch_req),.dispatch_logical(dispatch_logical),
        .dispatch_accept(dispatch_accept),
        .compute_req(compute_req),.compute_write(compute_write),
        .compute_word(compute_word),.compute_wdata(compute_wdata),
        .compute_wstrb(compute_wstrb),.compute_ack(compute_ack),
        .compute_rdata(compute_rdata),
        .compute_done(compute_done),.compute_fault(compute_fault),
        .fault_in(fault_in),.phase(phase),.poisoned(poisoned),
        .host_busy(host_busy),.compute_busy(compute_busy),
        .page_valid(page_valid),.page_dirty(page_dirty),
        .page_logical(page_logical),.loaded_byte_count(loaded_byte_count)
    );
    m06_lif16_neuron_step lane(
        .previous_voltage(lif_previous),
        .bias(16'sd1),.threshold(16'sd25),.reset_voltage(16'sd0),
        .summed_current(32'sd2),.decay_num(32'd3),.decay_den(32'd4),
        .next_voltage(lif_next),.spike(lif_spike),.invalid_params(lif_invalid)
    );

    task automatic reset_dut;
    begin
        @(negedge clk);
        resetn=0; host_begin=0;host_req=0;host_commit=0;
        host_save_done=0;dispatch_req=0;compute_req=0;
        compute_done=0;compute_fault=0;fault_in=0;
        repeat(3) @(negedge clk);
        resetn=1;
        @(negedge clk);
        if(phase!==3'd0 || page_valid || loaded_byte_count!==9'd0)
            $fatal(1,"M08_PAGE_RESET_MUST_INVALIDATE_PAGE");
    end
    endtask

    task automatic begin_page(input [31:0] logical);
    begin
        @(negedge clk); host_begin_logical=logical;host_begin=1;
        @(posedge clk); #1;
        if(phase!==3'd1 || page_logical!==logical || page_valid)
            $fatal(1,"M08_PAGE_BEGIN_FAILED");
        @(negedge clk);host_begin=0;
    end
    endtask

    task automatic write_word(input [5:0] address,
                              input [31:0] value,input [3:0] strobe);
    begin
        @(negedge clk);
        host_req=1;host_write=1;host_word=address;
        host_wdata=value;host_wstrb=strobe;
        @(posedge clk); #1;
        if(!host_ack || host_error || poisoned)
            $fatal(1,"M08_PAGE_HOST_WRITE_FAILED word=%d",address);
        @(negedge clk);host_req=0;host_write=0;
    end
    endtask

    task automatic read_word(input [5:0] address,
                             input [31:0] expected);
    begin
        @(negedge clk);host_req=1;host_write=0;host_word=address;
        @(posedge clk); #1;
        if(!host_ack || host_error || host_rdata!==expected)
            $fatal(1,"M08_PAGE_HOST_READ_FAILED word=%0d got=%h expected=%h",
                   address,host_rdata,expected);
        @(negedge clk);host_req=0;
    end
    endtask

    task automatic commit_page;
    begin
        @(negedge clk);host_commit=1;host_readback_verified=1;
        @(posedge clk); #1;
        if(phase!==3'd2 || !page_valid || poisoned)
            $fatal(1,"M08_PAGE_VERIFY_COMMIT_FAILED");
        @(negedge clk);host_commit=0;host_readback_verified=0;
    end
    endtask

    task automatic fill_page(input [31:0] logical,
                             input [31:0] first_word);
        integer i;
        reg [31:0] word_value;
    begin
        begin_page(logical);
        for(i=0;i<64;i=i+1) begin
            word_value=(i==0)?first_word:(32'h10200000+i);
            write_word(i[5:0],word_value,4'hf);
        end
        if(loaded_byte_count!==9'd256)
            $fatal(1,"M08_PAGE_INCOMPLETE_BYTE_MASK");
        for(i=0;i<64;i=i+1) begin
            word_value=(i==0)?first_word:(32'h10200000+i);
            read_word(i[5:0],word_value);
        end
        commit_page();
    end
    endtask

    task automatic start_compute(input [31:0] logical);
    begin
        @(negedge clk);dispatch_req=1;dispatch_logical=logical;
        @(posedge clk);#1;
        if(!dispatch_accept || !compute_busy || poisoned)
            $fatal(1,"M08_PAGE_COMPUTE_DISPATCH_FAILED");
        @(negedge clk);dispatch_req=0;
    end
    endtask

    task automatic compute_read(input [5:0] idx,input [31:0] expected);
    begin
        @(negedge clk);compute_req=1;compute_write=0;compute_word=idx;
        @(posedge clk);#1;
        if(!compute_ack || compute_rdata!==expected)
            $fatal(1,"M08_PAGE_COMPUTE_READ_FAILED");
        @(negedge clk);compute_req=0;
    end
    endtask

    task automatic compute_write_word(input [5:0] idx,input [31:0] value,
                                      input [3:0] strobes);
    begin
        @(negedge clk);compute_req=1;compute_write=1;compute_word=idx;
        compute_wdata=value;compute_wstrb=strobes;
        @(posedge clk);#1;
        if(!compute_ack || poisoned)
            $fatal(1,"M08_PAGE_COMPUTE_WRITE_FAILED");
        @(negedge clk);compute_req=0;compute_write=0;
    end
    endtask

    task automatic finish_compute;
    begin
        @(negedge clk);compute_done=1;
        @(posedge clk);#1;
        if(phase!==3'd4 || !page_dirty || poisoned)
            $fatal(1,"M08_PAGE_COMPUTE_FINISH_FAILED");
        @(negedge clk);compute_done=0;
    end
    endtask

    task automatic save_page;
    begin
        @(negedge clk);host_save_done=1;
        @(posedge clk);#1;
        if(phase!==3'd2 || page_dirty || poisoned)
            $fatal(1,"M08_PAGE_HOST_SAVE_ACK_FAILED");
        @(negedge clk);host_save_done=0;
    end
    endtask

    initial begin
        reset_dut();
        fill_page(32'd7,32'h55550004);
        if(page_logical!==32'd7) $fatal(1,"M08_PAGE_LOGICAL_TAG_LOST");
        // A separate accepted M06 signed16 combinational arithmetic lane
        // operates on a correctly packed state byte pair.
        start_compute(32'd7);
        compute_read(6'd0,32'h55550004);
        lif_previous=16'sd4;
        #1;
        if(lif_invalid || lif_spike || lif_next!==16'sd6)
            $fatal(1,"M08_PAGE_M06_SIGNED16_LANE_MISMATCH");
        compute_write_word(6'd0,32'h00000006,4'b0011);
        finish_compute();
        read_word(6'd0,32'h55550006);
        copied_backing=host_rdata; // actual simulated host readback
        // The hardware gate tracks all 64 actual READ operations prior to
        // accepting an externally confirmed durable backing save.
        for(dirty_index=1;dirty_index<64;dirty_index=dirty_index+1)
            read_word(dirty_index[5:0],32'h10200000+dirty_index);
        save_page();
        fill_page(32'd9,32'h11110009);
        if(copied_backing!==32'h55550006 || page_logical!==32'd9 ||
           page_dirty || loaded_byte_count!==9'd256)
            $fatal(1,"M08_PAGE_BACKING_NOT_PRESERVED");
        $display("M08_ONE_SLOT_HOST_PAGE_SIGNED16_STAGING_PASS");

        // No dirty eviction before host reads and explicitly saves.
        reset_dut();
        fill_page(32'd1,32'h11110001);
        start_compute(32'd1);
        finish_compute();
        @(negedge clk);host_begin=1;host_begin_logical=2;
        @(posedge clk);#1;
        if(!poisoned || phase!==3'd5)
            $fatal(1,"M08_PAGE_DIRTY_EVICTION_MUST_POISON");
        @(negedge clk);host_begin=0;
        $display("M08_ONE_SLOT_DIRTY_EVICTION_DENIED");

        // Incomplete byte-lane fill may never be tagged verified.
        reset_dut();
        begin_page(32'd5);
        write_word(6'd0,32'hffbbccdd,4'b0001);
        if(loaded_byte_count!==9'd1)
            $fatal(1,"M08_PAGE_PARTIAL_BYTE_TRACKING_FAILED");
        @(negedge clk);host_commit=1;host_readback_verified=1;
        @(posedge clk);#1;
        if(!poisoned || page_valid)
            $fatal(1,"M08_PAGE_INCOMPLETE_FILL_MUST_POISON");
        @(negedge clk);host_commit=0;host_readback_verified=0;
        $display("M08_ONE_SLOT_PARTIAL_FILL_DENIED");

        // Even a full byte fill is not dispatchable until the host has
        // ACTUALLY read every word back; a false host flag cannot bypass.
        reset_dut();
        begin_page(32'd11);
        for(negative_index=0;negative_index<64;
            negative_index=negative_index+1)
            write_word(negative_index[5:0],
                       32'h20000000+negative_index,4'hf);
        @(negedge clk);host_commit=1;host_readback_verified=1;
        @(posedge clk);#1;
        if(!poisoned || page_valid)
            $fatal(1,"M08_PAGE_FULL_LOAD_WITHOUT_READBACK_MUST_POISON");
        @(negedge clk);host_commit=0;host_readback_verified=0;
        $display("M08_ONE_SLOT_FAKE_LOAD_READBACK_DENIED");

        // Save acknowledgement is rejected until all DIRTY words have
        // been physically observed through the host port.
        reset_dut();
        fill_page(32'd12,32'h12000001);
        start_compute(32'd12);
        finish_compute();
        @(negedge clk);host_save_done=1;
        @(posedge clk);#1;
        if(!poisoned || !host_error || page_valid)
            $fatal(1,"M08_PAGE_UNREAD_DIRTY_SAVE_MUST_POISON");
        @(negedge clk);host_save_done=0;
        $display("M08_ONE_SLOT_FAKE_DIRTY_SAVE_DENIED");

        // The compute engine owns the memory until completion.
        reset_dut();
        fill_page(32'd3,32'h44440003);
        start_compute(32'd3);
        @(negedge clk);host_req=1;host_word=0;host_write=0;
        @(posedge clk);#1;
        if(!poisoned || !host_error || host_ack)
            $fatal(1,"M08_PAGE_HOST_COMPUTE_CONFLICT_MUST_POISON");
        @(negedge clk);host_req=0;
        $display("M08_ONE_SLOT_HOST_COMPUTE_CONFLICT_DENIED");

        // Dispatch must use the currently VERIFIED logical ID.
        reset_dut();
        fill_page(32'd8,32'h00000008);
        @(negedge clk);dispatch_req=1;dispatch_logical=32'd7;
        @(posedge clk);#1;
        if(!poisoned || dispatch_accept)
            $fatal(1,"M08_PAGE_WRONG_LOGICAL_ID_MUST_POISON");
        @(negedge clk);dispatch_req=0;

        // External fault must never silently leave page valid.
        reset_dut();
        fill_page(32'd4,32'h00000004);
        @(negedge clk);fault_in=1;
        @(posedge clk);#1;
        if(!poisoned || page_valid)
            $fatal(1,"M08_PAGE_EXTERNAL_FAULT_MUST_QUARANTINE");
        @(negedge clk);fault_in=0;
        repeat(3) @(negedge clk);
        if(!poisoned) $fatal(1,"M08_PAGE_FAULT_NOT_STICKY");
        $display("M08_ONE_SLOT_SOURCE_ONLY_NO_AXI_NO_DMA_NO_BITSTREAM_PASS");
        $finish;
    end
    initial begin
        #1000000;
        $fatal(1,"M08_PAGE_TB_GLOBAL_TIMEOUT");
    end
endmodule
