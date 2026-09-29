`timescale 1ns/1ps

// P03 implementation-shell observability and access interlock. This module
// does not alter loihi_core_v2_tick arithmetic or architectural state. It
// turns a VIO/JTAG start request into a one-cycle HLS ap_start pulse while the
// host/debug memory path is idle, measures physical PL cycles to ap_done, and
// exposes a sticky run counter for slow JTAG polling.
//
// Important: ap_ready is deliberately NOT a prerequisite for issuing ap_start.
// For ap_ctrl_hs, ap_ready is inactive until a transaction has started (and for
// a non-pipelined design is commonly asserted with ap_done). Gating ap_start
// on ap_ready therefore deadlocks the first transaction.
module p03_run_monitor (
    input  wire        ap_clk,
    input  wire        resetn,
    input  wire        start_request,
    input  wire        host_busy,
    input  wire        done,
    output reg         core_start,
    output reg         busy,
    output reg         start_seen,
    output reg         start_blocked,
    output reg  [63:0] last_run_cycles,
    output reg  [31:0] completed_runs,
    output reg  [31:0] heartbeat
);
    reg start_request_d;
    reg [63:0] active_cycles;

    always @(posedge ap_clk) begin
        if (!resetn) begin
            core_start <= 1'b0;
            busy <= 1'b0;
            start_seen <= 1'b0;
            start_blocked <= 1'b0;
            last_run_cycles <= 64'd0;
            completed_runs <= 32'd0;
            active_cycles <= 64'd0;
            heartbeat <= 32'd0;
            start_request_d <= 1'b0;
        end else begin
            heartbeat <= heartbeat + 32'd1;
            start_request_d <= start_request;
            core_start <= 1'b0;
            start_blocked <= 1'b0;

            if (start_request && !start_request_d) begin
                if (!busy && !host_busy) begin
                    core_start <= 1'b1;
                    busy <= 1'b1;
                    start_seen <= 1'b1;
                    active_cycles <= 64'd0;
                end else begin
                    start_blocked <= 1'b1;
                end
            end else if (busy) begin
                active_cycles <= active_cycles + 64'd1;
                if (done) begin
                    busy <= 1'b0;
                    last_run_cycles <= active_cycles + 64'd1;
                    completed_runs <= completed_runs + 32'd1;
                end
            end
        end
    end
endmodule
