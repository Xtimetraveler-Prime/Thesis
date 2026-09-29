`timescale 1ns/1ps

// P03 implementation-shell observability and access interlock.  This module
// does not alter loihi_core_v2_tick arithmetic or architectural state.  It
// turns a VIO/JTAG start request into a one-cycle HLS ap_start pulse only while
// the host/debug memory path is idle and the HLS core is ready, measures
// physical PL cycles to ap_done, and exposes blocked-start events plus a
// heartbeat.
module p03_run_monitor (
    input  wire        ap_clk,
    input  wire        resetn,
    input  wire        start_request,
    input  wire        host_busy,
    input  wire        core_ready,
    input  wire        done,
    output reg         core_start,
    output reg         busy,
    output reg         start_seen,
    output reg         start_blocked,
    output reg  [63:0] last_run_cycles,
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
            active_cycles <= 64'd0;
            heartbeat <= 32'd0;
            start_request_d <= 1'b0;
        end else begin
            heartbeat <= heartbeat + 32'd1;
            start_request_d <= start_request;
            core_start <= 1'b0;
            start_blocked <= 1'b0;

            if (start_request && !start_request_d) begin
                if (!busy && !host_busy && core_ready) begin
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
                end
            end
        end
    end
endmodule
