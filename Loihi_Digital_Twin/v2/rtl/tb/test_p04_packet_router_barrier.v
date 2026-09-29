`timescale 1ns / 1ps

module test_p04_packet_router_barrier;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg timestep_start = 1'b0;
    reg [31:0] timestep_value = 32'd0;
    reg advance_req = 1'b0;
    wire advance_ack;
    wire advance_blocked;
    wire barrier_active;
    wire can_advance;
    wire [1:0] completed_mask;
    wire [15:0] in_flight_count;

    reg [1:0] core_done = 2'b00;
    reg service_reverse = 1'b0;

    reg src0_valid = 1'b0;
    reg [63:0] src0_packet = 64'd0;
    wire src0_ready;
    reg src1_valid = 1'b0;
    reg [63:0] src1_packet = 64'd0;
    wire src1_ready;

    wire dst0_valid;
    wire [63:0] dst0_packet;
    reg dst0_ready = 1'b0;
    wire dst1_valid;
    wire [63:0] dst1_packet;
    reg dst1_ready = 1'b0;

    wire [31:0] local_packet_count;
    wire [31:0] remote_packet_count;
    wire error_bad_valid;
    wire error_bad_destination;
    wire error_bad_timestep;

    integer dst0_seen = 0;
    integer dst1_seen = 0;
    reg [63:0] dst0_words [0:7];
    reg [63:0] dst1_words [0:7];

    p04_packet_router_barrier #(
        .FIFO_DEPTH(4)
    ) dut (
        .clk(clk),
        .resetn(resetn),
        .timestep_start(timestep_start),
        .timestep_value(timestep_value),
        .advance_req(advance_req),
        .advance_ack(advance_ack),
        .advance_blocked(advance_blocked),
        .barrier_active(barrier_active),
        .can_advance(can_advance),
        .completed_mask(completed_mask),
        .in_flight_count(in_flight_count),
        .core_done(core_done),
        .service_reverse(service_reverse),
        .src0_valid(src0_valid),
        .src0_packet(src0_packet),
        .src0_ready(src0_ready),
        .src1_valid(src1_valid),
        .src1_packet(src1_packet),
        .src1_ready(src1_ready),
        .dst0_valid(dst0_valid),
        .dst0_packet(dst0_packet),
        .dst0_ready(dst0_ready),
        .dst1_valid(dst1_valid),
        .dst1_packet(dst1_packet),
        .dst1_ready(dst1_ready),
        .local_packet_count(local_packet_count),
        .remote_packet_count(remote_packet_count),
        .error_bad_valid(error_bad_valid),
        .error_bad_destination(error_bad_destination),
        .error_bad_timestep(error_bad_timestep)
    );

    function [63:0] make_packet;
        input [6:0] destination_core;
        input [11:0] destination_axon;
        input [9:0] source_compartment;
        input [31:0] target_timestep;
        reg [63:0] word;
        begin
            word = 64'd0;
            word[6:0] = destination_core;
            word[18:7] = destination_axon;
            word[28:19] = source_compartment;
            word[60:29] = target_timestep;
            word[61] = 1'b1;
            make_packet = word;
        end
    endfunction

    task fail;
        input [8*120-1:0] message;
        begin
            $display("FAIL: %0s", message);
            $finish(1);
        end
    endtask

    task start_timestep;
        input [31:0] value;
        begin
            @(negedge clk);
            timestep_value = value;
            timestep_start = 1'b1;
            @(negedge clk);
            timestep_start = 1'b0;
            if (!barrier_active)
                fail("barrier did not become active after timestep_start");
        end
    endtask

    task pulse_done;
        input [1:0] mask;
        begin
            @(negedge clk);
            core_done = mask;
            @(negedge clk);
            core_done = 2'b00;
        end
    endtask

    task send_both;
        input [63:0] packet0;
        input [63:0] packet1;
        begin
            while (!(src0_ready && src1_ready))
                @(negedge clk);
            src0_packet = packet0;
            src1_packet = packet1;
            src0_valid = 1'b1;
            src1_valid = 1'b1;
            @(negedge clk);
            src0_valid = 1'b0;
            src1_valid = 1'b0;
        end
    endtask

    task request_blocked_advance;
        begin
            @(negedge clk);
            advance_req = 1'b1;
            @(negedge clk);
            advance_req = 1'b0;
            if (!advance_blocked)
                fail("advance request was not blocked while traffic remained pending");
        end
    endtask

    task request_successful_advance;
        begin
            while (!can_advance)
                @(negedge clk);
            @(negedge clk);
            advance_req = 1'b1;
            @(negedge clk);
            advance_req = 1'b0;
            if (!advance_ack)
                fail("advance request did not acknowledge at quiescence");
            @(negedge clk);
            if (barrier_active)
                fail("barrier remained active after successful advance");
        end
    endtask

    always @(posedge clk) begin
        if (dst0_valid && dst0_ready) begin
            dst0_words[dst0_seen] <= dst0_packet;
            dst0_seen <= dst0_seen + 1;
        end
        if (dst1_valid && dst1_ready) begin
            dst1_words[dst1_seen] <= dst1_packet;
            dst1_seen <= dst1_seen + 1;
        end
    end

    reg [63:0] p0;
    reg [63:0] p1;
    integer timeout;

    initial begin
        repeat (4) @(negedge clk);
        resetn = 1'b1;
        repeat (2) @(negedge clk);

        // Test A: simultaneous producers. src0 sends remotely to core 1 while
        // src1 sends locally to core 1. Hold destination 1 stalled so an
        // advance request must be rejected until both packets are delivered.
        service_reverse = 1'b0;
        dst0_ready = 1'b0;
        dst1_ready = 1'b0;
        dst0_seen = 0;
        dst1_seen = 0;
        start_timestep(32'd0);

        p0 = make_packet(7'd1, 12'd17, 10'd3, 32'd1);
        p1 = make_packet(7'd1, 12'd23, 10'd4, 32'd1);
        send_both(p0, p1);
        pulse_done(2'b11);

        timeout = 0;
        while (in_flight_count < 2 && timeout < 20) begin
            timeout = timeout + 1;
            @(negedge clk);
        end
        if (in_flight_count < 2)
            fail("simultaneous producers were not both retained");
        if (completed_mask != 2'b11)
            fail("core completion mask did not latch both participants");

        request_blocked_advance();
        if (can_advance)
            fail("can_advance asserted while destination queue was stalled");

        dst1_ready = 1'b1;
        timeout = 0;
        while (dst1_seen < 2 && timeout < 40) begin
            timeout = timeout + 1;
            @(negedge clk);
        end
        if (dst1_seen != 2)
            fail("destination 1 did not receive both queued packets");
        if (!((dst1_words[0] == p0 && dst1_words[1] == p1) ||
              (dst1_words[0] == p1 && dst1_words[1] == p0)))
            fail("destination 1 packet multiset mismatch");
        if (local_packet_count != 32'd1 || remote_packet_count != 32'd1)
            fail("local/remote traffic counters were incorrect");
        if (error_bad_valid || error_bad_destination || error_bad_timestep)
            fail("unexpected packet-integrity error in Test A");

        request_successful_advance();

        // Test B: reverse the legal arbitration priority. Both producers send
        // remote packets to opposite destinations. The delivered packet set and
        // quiescence result must remain correct despite the different service
        // preference.
        service_reverse = 1'b1;
        dst0_ready = 1'b1;
        dst1_ready = 1'b1;
        dst0_seen = 0;
        dst1_seen = 0;
        start_timestep(32'd1);

        p0 = make_packet(7'd1, 12'd31, 10'd5, 32'd2);
        p1 = make_packet(7'd0, 12'd37, 10'd6, 32'd2);
        send_both(p0, p1);
        pulse_done(2'b11);

        timeout = 0;
        while ((dst0_seen < 1 || dst1_seen < 1) && timeout < 40) begin
            timeout = timeout + 1;
            @(negedge clk);
        end
        if (dst0_seen != 1 || dst1_seen != 1)
            fail("reverse arbitration did not deliver one packet to each destination");
        if (dst0_words[0] != p1 || dst1_words[0] != p0)
            fail("reverse arbitration routed a packet to the wrong destination");
        if (local_packet_count != 32'd0 || remote_packet_count != 32'd2)
            fail("reverse-arbitration traffic counters were incorrect");
        if (error_bad_valid || error_bad_destination || error_bad_timestep)
            fail("unexpected packet-integrity error in Test B");

        request_successful_advance();

        $display("PASS: P04 packet router/barrier directed test completed successfully.");
        $finish(0);
    end

endmodule
