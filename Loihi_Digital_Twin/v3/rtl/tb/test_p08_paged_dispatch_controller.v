`timescale 1ns/1ps

module test_p08_paged_dispatch_controller;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg dispatch_start = 1'b0;
    reg host_busy = 1'b0;
    reg [1:0] requested_context_slot = 2'd0;
    reg [63:0] context_metadata = 64'd0;
    reg [31:0] dispatch_timestep = 32'd0;
    reg requested_event_read_bank = 1'b0;

    wire core_start;
    reg core_ready = 1'b1;
    reg core_done = 1'b0;
    reg [12:0] core_packet_count = 13'd0;
    reg [31:0] core_status = 32'd0;

    wire [10:0] core_compartment_count;
    wire [12:0] core_event_count;
    wire [15:0] core_synapse_count;
    wire [12:0] core_route_count;
    wire [31:0] core_timestep;
    wire [1:0] active_context_slot;
    wire [6:0] active_logical_core_id;
    wire event_read_bank;
    wire busy;
    wire dispatch_done;
    wire start_blocked;
    wire [12:0] packet_count_latched;
    wire [31:0] status_latched;
    wire [31:0] completed_dispatches;
    wire [63:0] active_cycles;
    wire [63:0] last_dispatch_cycles;
    wire error_metadata;
    wire error_packet_overflow;
    wire error_core_status;

    integer core_delay = 0;
    integer timeout = 0;
    integer failure_count = 0;
    reg response_error = 1'b0;

    p08_paged_dispatch_controller dut (
        .clk(clk),
        .resetn(resetn),
        .dispatch_start(dispatch_start),
        .host_busy(host_busy),
        .requested_context_slot(requested_context_slot),
        .context_metadata(context_metadata),
        .dispatch_timestep(dispatch_timestep),
        .requested_event_read_bank(requested_event_read_bank),
        .core_start(core_start),
        .core_ready(core_ready),
        .core_done(core_done),
        .core_packet_count(core_packet_count),
        .core_status(core_status),
        .core_compartment_count(core_compartment_count),
        .core_event_count(core_event_count),
        .core_synapse_count(core_synapse_count),
        .core_route_count(core_route_count),
        .core_timestep(core_timestep),
        .active_context_slot(active_context_slot),
        .active_logical_core_id(active_logical_core_id),
        .event_read_bank(event_read_bank),
        .busy(busy),
        .dispatch_done(dispatch_done),
        .start_blocked(start_blocked),
        .packet_count_latched(packet_count_latched),
        .status_latched(status_latched),
        .completed_dispatches(completed_dispatches),
        .active_cycles(active_cycles),
        .last_dispatch_cycles(last_dispatch_cycles),
        .error_metadata(error_metadata),
        .error_packet_overflow(error_packet_overflow),
        .error_core_status(error_core_status)
    );

    function [63:0] make_meta;
        input [6:0] logical_core_id;
        input [10:0] compartment_count;
        input [15:0] synapse_count;
        input [12:0] route_count;
        input [12:0] event_count;
        begin
            make_meta = 64'd0;
            make_meta[6:0] = logical_core_id;
            make_meta[17:7] = compartment_count;
            make_meta[33:18] = synapse_count;
            make_meta[46:34] = route_count;
            make_meta[59:47] = event_count;
        end
    endfunction

    // Model the accepted HLS ap_ctrl_hs behavior using the same race-resistant
    // clocked response pattern as the validated P05 controller testbench.  The
    // core response is generated from core_start rather than being manually
    // toggled from the main stimulus process at a positive clock edge.
    always @(posedge clk) begin
        core_done <= 1'b0;
        if (core_start) begin
            core_delay <= 3;
            if (response_error) begin
                core_packet_count <= 13'd4097;
                core_status <= 32'h00000005;
            end else begin
                core_packet_count <= 13'd7;
                core_status <= 32'd0;
            end
        end else if (core_delay > 0) begin
            core_delay <= core_delay - 1;
            if (core_delay == 1)
                core_done <= 1'b1;
        end
    end

    task pulse_dispatch;
        begin
            @(negedge clk);
            dispatch_start = 1'b1;
            @(negedge clk);
            dispatch_start = 1'b0;
        end
    endtask

    task wait_dispatch_done;
        begin
            timeout = 0;
            while (!dispatch_done && timeout < 100) begin
                @(negedge clk);
                timeout = timeout + 1;
            end
            if (!dispatch_done) begin
                $display("FAIL: dispatch timeout busy=%0d completed=%0d", busy, completed_dispatches);
                failure_count = failure_count + 1;
            end
        end
    endtask

    task check;
        input condition;
        input [8*96-1:0] message;
        begin
            if (!condition) begin
                $display("FAIL: %0s", message);
                failure_count = failure_count + 1;
            end
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        // Valid dispatch of logical core 4 through resident slot 2.
        response_error = 1'b0;
        requested_context_slot = 2'd2;
        context_metadata = make_meta(7'd4, 11'd618, 16'd18966, 13'd521, 13'd17);
        dispatch_timestep = 32'd23;
        requested_event_read_bank = 1'b1;
        pulse_dispatch();

        check(busy && core_start, "valid request did not start the HLS dispatch");
        check(
            active_context_slot == 2'd2 && active_logical_core_id == 7'd4,
            "resident slot or logical identity was not latched"
        );
        check(
            core_compartment_count == 11'd618 && core_synapse_count == 16'd18966,
            "metadata resource counts were not preserved"
        );
        check(
            core_route_count == 13'd521 && core_event_count == 13'd17,
            "route/event metadata was not preserved"
        );
        check(
            core_timestep == 32'd23 && event_read_bank == 1'b1,
            "timestep/event bank was not latched"
        );

        wait_dispatch_done();
        check(!busy, "completed dispatch did not retire cleanly");
        check(
            packet_count_latched == 13'd7 && status_latched == 32'd0,
            "packet count/status was not latched"
        );
        check(
            completed_dispatches == 32'd1 && last_dispatch_cycles != 64'd0,
            "dispatch accounting did not advance"
        );
        check(
            !error_metadata && !error_packet_overflow && !error_core_status,
            "valid dispatch raised an error"
        );

        // Host access and compute must remain mutually exclusive.
        host_busy = 1'b1;
        requested_context_slot = 2'd0;
        context_metadata = make_meta(7'd1, 11'd10, 16'd20, 13'd3, 13'd0);
        pulse_dispatch();
        check(start_blocked && !busy, "host-busy request was not blocked");
        host_busy = 1'b0;

        // Reserved metadata bits must fail before HLS starts.
        context_metadata = make_meta(7'd2, 11'd10, 16'd20, 13'd3, 13'd0);
        context_metadata[60] = 1'b1;
        pulse_dispatch();
        check(
            start_blocked && error_metadata && !busy,
            "invalid metadata was not rejected"
        );

        // A later valid dispatch clears metadata error and reports HLS failures.
        response_error = 1'b1;
        context_metadata = make_meta(7'd2, 11'd10, 16'd20, 13'd3, 13'd0);
        requested_context_slot = 2'd1;
        requested_event_read_bank = 1'b0;
        dispatch_timestep = 32'd24;
        pulse_dispatch();
        check(busy && !error_metadata, "valid dispatch did not clear prior metadata error");

        wait_dispatch_done();
        check(
            !busy && error_packet_overflow && error_core_status,
            "HLS packet/status errors were not surfaced"
        );
        check(
            packet_count_latched == 13'd4097 && status_latched == 32'h00000005,
            "failing HLS result was not retained for host inspection"
        );
        check(completed_dispatches == 32'd2, "completed dispatch counter is incorrect");

        if (failure_count == 0)
            $display("PASS: p08_paged_dispatch_controller");
        else
            $display("FAIL: p08_paged_dispatch_controller failures=%0d", failure_count);
        $finish;
    end
endmodule
