`timescale 1ns/1ps

module test_p03_ps_control_regs;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;

    reg [39:0] awaddr = 40'd0;
    reg [2:0] awprot = 3'd0;
    reg awvalid = 1'b0;
    wire awready;
    reg [31:0] wdata = 32'd0;
    reg [3:0] wstrb = 4'hF;
    reg wvalid = 1'b0;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready = 1'b0;

    reg [39:0] araddr = 40'd0;
    reg [2:0] arprot = 3'd0;
    reg arvalid = 1'b0;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready = 1'b0;

    wire page_start;
    wire page_out;
    wire page_mutable_only;
    wire [1:0] page_context_slot;
    wire [63:0] page_record_base;
    reg page_busy = 1'b0;
    reg page_done = 1'b0;
    reg page_start_blocked = 1'b0;
    reg [31:0] page_bytes_transferred = 32'd0;
    reg [31:0] page_completed_transfers = 32'd0;
    reg [63:0] page_last_transfer_cycles = 64'd0;
    reg page_error_command = 1'b0;
    reg page_error_host = 1'b0;
    reg page_error_ddr = 1'b0;
    reg [31:0] page_completed_read_bursts = 32'd0;
    reg [31:0] page_completed_write_bursts = 32'd0;
    reg [63:0] page_axi_bytes_moved = 64'd0;
    reg page_protocol_error = 1'b0;
    reg page_range_error = 1'b0;
    reg [8:0] page_pending_write_bytes = 9'd0;

    wire dispatch_start;
    wire [1:0] dispatch_context_slot;
    wire [63:0] dispatch_metadata;
    wire [31:0] dispatch_timestep;
    wire dispatch_event_read_bank;
    reg dispatch_busy = 1'b0;
    reg dispatch_done = 1'b0;
    reg dispatch_start_blocked = 1'b0;
    reg [1:0] dispatch_active_context_slot = 2'd0;
    reg [6:0] dispatch_active_logical_core_id = 7'd0;
    reg dispatch_active_event_bank = 1'b0;
    reg [12:0] dispatch_packet_count = 13'd0;
    reg [31:0] dispatch_core_status = 32'd0;
    reg [31:0] dispatch_completed = 32'd0;
    reg [63:0] dispatch_last_cycles = 64'd0;
    reg dispatch_error_metadata = 1'b0;
    reg dispatch_error_packet_overflow = 1'b0;
    reg dispatch_error_core_status = 1'b0;
    reg dispatch_memory_address_error = 1'b0;

    wire debug_req;
    wire debug_write;
    wire [1:0] debug_context_slot;
    wire [3:0] debug_bank;
    wire [14:0] debug_addr;
    wire [255:0] debug_wdata;
    reg debug_busy = 1'b0;
    reg debug_ack = 1'b0;
    reg debug_rvalid = 1'b0;
    reg debug_error = 1'b0;
    reg [255:0] debug_rdata = 256'd0;

    integer failures = 0;
    integer timeout = 0;
    integer page_start_pulses = 0;
    integer dispatch_start_pulses = 0;
    reg [31:0] read_value;

    always @(posedge clk) begin
        if (page_start)
            page_start_pulses = page_start_pulses + 1;
        if (dispatch_start)
            dispatch_start_pulses = dispatch_start_pulses + 1;
    end

    p03_ps_control_regs dut (
        .s_axi_aclk(clk),
        .s_axi_aresetn(resetn),
        .s_axi_awaddr(awaddr),
        .s_axi_awprot(awprot),
        .s_axi_awvalid(awvalid),
        .s_axi_awready(awready),
        .s_axi_wdata(wdata),
        .s_axi_wstrb(wstrb),
        .s_axi_wvalid(wvalid),
        .s_axi_wready(wready),
        .s_axi_bresp(bresp),
        .s_axi_bvalid(bvalid),
        .s_axi_bready(bready),
        .s_axi_araddr(araddr),
        .s_axi_arprot(arprot),
        .s_axi_arvalid(arvalid),
        .s_axi_arready(arready),
        .s_axi_rdata(rdata),
        .s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid),
        .s_axi_rready(rready),

        .page_start(page_start),
        .page_out(page_out),
        .page_mutable_only(page_mutable_only),
        .page_context_slot(page_context_slot),
        .page_record_base(page_record_base),
        .page_busy(page_busy),
        .page_done(page_done),
        .page_start_blocked(page_start_blocked),
        .page_bytes_transferred(page_bytes_transferred),
        .page_completed_transfers(page_completed_transfers),
        .page_last_transfer_cycles(page_last_transfer_cycles),
        .page_error_command(page_error_command),
        .page_error_host(page_error_host),
        .page_error_ddr(page_error_ddr),
        .page_completed_read_bursts(page_completed_read_bursts),
        .page_completed_write_bursts(page_completed_write_bursts),
        .page_axi_bytes_moved(page_axi_bytes_moved),
        .page_protocol_error(page_protocol_error),
        .page_range_error(page_range_error),
        .page_pending_write_bytes(page_pending_write_bytes),

        .dispatch_start(dispatch_start),
        .dispatch_context_slot(dispatch_context_slot),
        .dispatch_metadata(dispatch_metadata),
        .dispatch_timestep(dispatch_timestep),
        .dispatch_event_read_bank(dispatch_event_read_bank),
        .dispatch_busy(dispatch_busy),
        .dispatch_done(dispatch_done),
        .dispatch_start_blocked(dispatch_start_blocked),
        .dispatch_active_context_slot(dispatch_active_context_slot),
        .dispatch_active_logical_core_id(dispatch_active_logical_core_id),
        .dispatch_active_event_bank(dispatch_active_event_bank),
        .dispatch_packet_count(dispatch_packet_count),
        .dispatch_core_status(dispatch_core_status),
        .dispatch_completed(dispatch_completed),
        .dispatch_last_cycles(dispatch_last_cycles),
        .dispatch_error_metadata(dispatch_error_metadata),
        .dispatch_error_packet_overflow(dispatch_error_packet_overflow),
        .dispatch_error_core_status(dispatch_error_core_status),
        .dispatch_memory_address_error(dispatch_memory_address_error),

        .debug_req(debug_req),
        .debug_write(debug_write),
        .debug_context_slot(debug_context_slot),
        .debug_bank(debug_bank),
        .debug_addr(debug_addr),
        .debug_wdata(debug_wdata),
        .debug_busy(debug_busy),
        .debug_ack(debug_ack),
        .debug_rvalid(debug_rvalid),
        .debug_error(debug_error),
        .debug_rdata(debug_rdata)
    );

    task check;
        input condition;
        input [8*160-1:0] message;
        begin
            if (!condition) begin
                $display("FAIL: %0s", message);
                failures = failures + 1;
            end
        end
    endtask

    task axi_write;
        input [11:0] addr;
        input [31:0] value;
        begin
            // Drive VALID on the falling edge and sample READY before the
            // rising edge that performs the AXI handshake.  Sampling READY
            // after that edge is incorrect for this DUT because the accepted
            // request immediately raises its pending flag and deasserts READY.
            @(negedge clk);
            awaddr = 40'h00_A4000000 + addr;
            awvalid = 1'b1;
            wdata = value;
            wstrb = 4'hF;
            wvalid = 1'b1;
            bready = 1'b0;

            timeout = 0;
            #1;
            while (!(awready && wready) && timeout < 20) begin
                @(negedge clk);
                #1;
                timeout = timeout + 1;
            end
            check(awready && wready,
                  "AXI write address/data handshake timeout");

            // AW and W are accepted on this rising edge.
            @(posedge clk);
            @(negedge clk);
            awvalid = 1'b0;
            wvalid = 1'b0;

            timeout = 0;
            #1;
            while (!bvalid && timeout < 20) begin
                @(negedge clk);
                #1;
                timeout = timeout + 1;
            end
            check(bvalid, "AXI write response timeout");
            check(bresp == 2'b00, "AXI write returned non-OKAY response");

            bready = 1'b1;
            @(posedge clk);
            @(negedge clk);
            bready = 1'b0;
        end
    endtask

    task axi_read;
        input [11:0] addr;
        output [31:0] value;
        begin
            // As with writes, READY must be observed before the accepting
            // rising edge.  Once the DUT captures ARVALID it raises RVALID and
            // its combinational ARREADY falls.
            @(negedge clk);
            araddr = 40'h00_A4000000 + addr;
            arvalid = 1'b1;
            rready = 1'b0;

            timeout = 0;
            #1;
            while (!arready && timeout < 20) begin
                @(negedge clk);
                #1;
                timeout = timeout + 1;
            end
            check(arready, "AXI read address handshake timeout");

            // AR is accepted on this rising edge.
            @(posedge clk);
            @(negedge clk);
            arvalid = 1'b0;

            timeout = 0;
            #1;
            while (!rvalid && timeout < 20) begin
                @(negedge clk);
                #1;
                timeout = timeout + 1;
            end
            check(rvalid, "AXI read data timeout");
            check(rresp == 2'b00, "AXI read returned non-OKAY response");
            value = rdata;

            rready = 1'b1;
            @(posedge clk);
            @(negedge clk);
            rready = 1'b0;
        end
    endtask

    initial begin
        repeat (5) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (3) @(posedge clk);

        axi_read(12'h000, read_value);
        check(read_value == 32'h4C54_3302, "MMIO ID mismatch");

        axi_read(12'h004, read_value);
        check(read_value == 32'h0001_0000, "MMIO version mismatch");

        axi_read(12'h008, read_value);
        check(read_value[4:0] == 5'b1_1111, "MMIO capability flags mismatch");

        axi_read(12'h018, read_value);
        check(read_value == 32'hD1A6_0018,
              "unmapped read diagnostic signature mismatch");
        check(read_value[10:8] == 3'd3, "resident-slot capability mismatch");
        check(read_value[23:16] == 8'd1, "physical-engine capability mismatch");

        // Page command programming and sticky completion.
        axi_write(12'h020, 32'h0000_0203); // slot2, mutable page-out
        axi_write(12'h024, 32'h4018_0000);
        axi_write(12'h028, 32'h0000_0000);
        axi_write(12'h02C, 32'h0000_0001);

        check(page_out, "page direction was not programmed");
        check(page_mutable_only, "mutable-only page flag was not programmed");
        check(page_context_slot == 2'd2, "page resident slot mismatch");
        check(page_record_base == 64'h0000_0000_4018_0000,
              "page DDR record base mismatch");

        // START is a one-cycle pulse.
        check(!page_start, "page_start did not retire to a pulse");
        check(page_start_pulses == 1,
              "page MMIO command did not emit exactly one START pulse");

        @(negedge clk);
        page_bytes_transferred = 32'h0001_A000;
        page_completed_transfers = 32'd7;
        page_last_transfer_cycles = 64'h0000_0001_2345_6789;
        page_completed_read_bursts = 32'd12;
        page_completed_write_bursts = 32'd416;
        page_axi_bytes_moved = 64'd106496;
        page_done = 1'b1;
        @(posedge clk);
        @(negedge clk);
        page_done = 1'b0;

        axi_read(12'h030, read_value);
        check(read_value[1], "page done was not latched for PS polling");
        axi_read(12'h034, read_value);
        check(read_value == 32'h0001_A000, "page byte counter mismatch");
        axi_read(12'h03C, read_value);
        check(read_value == 32'h2345_6789, "page cycle low word mismatch");
        axi_read(12'h040, read_value);
        check(read_value == 32'h0000_0001, "page cycle high word mismatch");

        axi_write(12'h02C, 32'h0000_0002); // clear sticky done
        axi_read(12'h030, read_value);
        check(!read_value[1], "page done clear command failed");

        // Dispatch programming and sticky completion.
        axi_write(12'h080, 32'h0000_0101); // slot1, event bank1
        axi_write(12'h084, 32'h89AB_CDEF);
        axi_write(12'h088, 32'h0123_4567);
        axi_write(12'h08C, 32'd42);
        axi_write(12'h090, 32'h0000_0001);

        check(dispatch_context_slot == 2'd1, "dispatch slot mismatch");
        check(dispatch_event_read_bank, "dispatch event bank mismatch");
        check(dispatch_metadata == 64'h0123_4567_89AB_CDEF,
              "dispatch metadata mismatch");
        check(dispatch_timestep == 32'd42, "dispatch timestep mismatch");
        check(!dispatch_start, "dispatch_start did not retire to a pulse");
        check(dispatch_start_pulses == 1,
              "dispatch MMIO command did not emit exactly one START pulse");

        @(negedge clk);
        dispatch_packet_count = 13'd9;
        dispatch_core_status = 32'h0000_0000;
        dispatch_completed = 32'd11;
        dispatch_last_cycles = 64'd3865;
        dispatch_active_context_slot = 2'd1;
        dispatch_active_logical_core_id = 7'd4;
        dispatch_active_event_bank = 1'b1;
        dispatch_done = 1'b1;
        @(posedge clk);
        @(negedge clk);
        dispatch_done = 1'b0;

        axi_read(12'h094, read_value);
        check(read_value[1], "dispatch done was not latched for PS polling");
        axi_read(12'h098, read_value);
        check(read_value == 32'd9, "dispatch packet count mismatch");
        axi_read(12'h0AC, read_value);
        check(read_value[1:0] == 2'd1, "dispatch active slot status mismatch");
        check(read_value[8], "dispatch active event-bank status mismatch");
        check(read_value[22:16] == 7'd4,
              "dispatch active logical-core status mismatch");

        // Resident read command: request must remain asserted until ACK, then
        // response must be captured into software-readable registers.
        axi_write(12'h100, 32'h0000_5200); // read, slot2, bank5
        axi_write(12'h104, 32'd17);
        axi_write(12'h108, 32'h0000_0001);

        check(debug_req, "resident read request was not asserted");
        check(!debug_write, "resident read incorrectly asserted write");
        check(debug_context_slot == 2'd2, "resident read slot mismatch");
        check(debug_bank == 4'd5, "resident read bank mismatch");
        check(debug_addr == 15'd17, "resident read address mismatch");

        repeat (5) begin
            @(posedge clk);
            #1;
            check(debug_req, "resident request was not level-held until ACK");
        end

        @(negedge clk);
        debug_ack = 1'b1;
        debug_rvalid = 1'b1;
        debug_rdata = 256'hFEDC_BA98_7654_3210_0123_4567_89AB_CDEF_0BAD_F00D_CAFE_BABE_DEAD_BEEF_1234_5678;
        @(posedge clk);
        #1;
        @(negedge clk);
        debug_ack = 1'b0;
        debug_rvalid = 1'b0;

        check(!debug_req, "resident request did not retire after ACK");

        axi_read(12'h10C, read_value);
        check(read_value[1], "resident completion was not latched");
        check(read_value[2], "resident read-valid was not latched");
        check(!read_value[3], "resident read latched an unexpected error");

        axi_read(12'h130, read_value);
        check(read_value == 32'h1234_5678, "resident RDATA word0 mismatch");
        axi_read(12'h14C, read_value);
        check(read_value == 32'hFEDC_BA98, "resident RDATA word7 mismatch");

        // Resident write data window and blocked-start behavior.
        axi_write(12'h110, 32'hA5A5_0001);
        axi_write(12'h12C, 32'hA5A5_0008);
        axi_write(12'h100, 32'h0000_3101); // write, slot1, bank3
        axi_write(12'h104, 32'd21);

        debug_busy = 1'b1;
        axi_write(12'h108, 32'h0000_0001);
        debug_busy = 1'b0;
        axi_read(12'h10C, read_value);
        check(read_value[4], "resident blocked-start status was not latched");
        check(!debug_req, "blocked resident request was forwarded");

        axi_write(12'h108, 32'h0000_0002); // clear
        axi_write(12'h108, 32'h0000_0001);
        check(debug_req, "resident write request was not asserted");
        check(debug_write, "resident write did not assert write direction");
        check(debug_context_slot == 2'd1, "resident write slot mismatch");
        check(debug_bank == 4'd3, "resident write bank mismatch");
        check(debug_addr == 15'd21, "resident write address mismatch");
        check(debug_wdata[31:0] == 32'hA5A5_0001,
              "resident WDATA word0 mismatch");
        check(debug_wdata[255:224] == 32'hA5A5_0008,
              "resident WDATA word7 mismatch");

        @(negedge clk);
        debug_ack = 1'b1;
        debug_rvalid = 1'b0;
        @(posedge clk);
        #1;
        @(negedge clk);
        debug_ack = 1'b0;

        axi_read(12'h10C, read_value);
        check(read_value[1], "resident write completion was not latched");
        check(!read_value[2], "resident write incorrectly latched RVALID");

        if (failures == 0)
            $display("PASS: p03_ps_control_regs");
        else
            $display("FAIL: p03_ps_control_regs failures=%0d", failures);
        $finish;
    end
endmodule
