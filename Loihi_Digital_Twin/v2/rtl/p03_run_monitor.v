`timescale 1ns/1ps

// P03 implementation-shell observability and access interlock. This module
// does not alter loihi_core_v2_tick arithmetic or architectural state. It
// converts a VIO/JTAG start request into a protocol-correct ap_ctrl_hs start,
// measures physical PL cycles to ap_done, and exposes a sticky run counter for
// slow JTAG polling.
//
// ap_ctrl_hs requires ap_start to remain asserted until ap_ready. ap_ready is
// inactive before the first transaction, so it must never be a prerequisite
// for accepting the request. start_pending latches the request and core_start
// is held high while ap_ready is low. As soon as ap_ready rises, core_start
// drops combinationally, so the HLS block sees ap_start=0 with ap_ready=1 and
// does not immediately launch a second transaction.
module p03_run_monitor (
    input  wire        ap_clk,
    input  wire        resetn,
    input  wire        start_request,
    input  wire        host_busy,
    input  wire        core_ready,
    input  wire        done,
    output wire        core_start,
    output reg         busy,
    output reg         start_seen,
    output reg         start_blocked,
    output reg  [63:0] last_run_cycles,
    output reg  [31:0] completed_runs,
    output reg  [31:0] heartbeat
);
    reg start_request_d;
    reg start_pending;
    reg [63:0] active_cycles;

    assign core_start = start_pending && !core_ready;

    always @(posedge ap_clk) begin
        if (!resetn) begin
            busy <= 1'b0;
            start_seen <= 1'b0;
            start_blocked <= 1'b0;
            last_run_cycles <= 64'd0;
            completed_runs <= 32'd0;
            active_cycles <= 64'd0;
            heartbeat <= 32'd0;
            start_request_d <= 1'b0;
            start_pending <= 1'b0;
        end else begin
            heartbeat <= heartbeat + 32'd1;
            start_request_d <= start_request;
            start_blocked <= 1'b0;

            if (start_request && !start_request_d) begin
                if (!busy && !host_busy) begin
                    start_pending <= 1'b1;
                    busy <= 1'b1;
                    start_seen <= 1'b1;
                    active_cycles <= 64'd0;
                end else begin
                    start_blocked <= 1'b1;
                end
            end

            if (busy) begin
                active_cycles <= active_cycles + 64'd1;
                if (core_ready) begin
                    start_pending <= 1'b0;
                end
                if (done) begin
                    start_pending <= 1'b0;
                    busy <= 1'b0;
                    last_run_cycles <= active_cycles + 64'd1;
                    completed_runs <= completed_runs + 32'd1;
                end
            end
        end
    end
endmodule
