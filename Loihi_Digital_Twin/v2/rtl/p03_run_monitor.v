`timescale 1ns/1ps

// P03 implementation-shell observability only. This module does not alter
// loihi_core_v2_tick architectural behavior; it measures physical PL cycles
// between a VIO/JTAG start pulse and HLS ap_done and provides a heartbeat.
module p03_run_monitor (
    input  wire        ap_clk,
    input  wire        resetn,
    input  wire        start,
    input  wire        done,
    output reg         busy,
    output reg         start_seen,
    output reg  [63:0] last_run_cycles,
    output reg  [31:0] heartbeat
);
    reg start_d;
    reg [63:0] active_cycles;

    always @(posedge ap_clk) begin
        heartbeat <= heartbeat + 32'd1;
        start_d <= start;

        if (!resetn) begin
            busy <= 1'b0;
            start_seen <= 1'b0;
            last_run_cycles <= 64'd0;
            active_cycles <= 64'd0;
            start_d <= 1'b0;
        end else begin
            if (start && !start_d && !busy) begin
                busy <= 1'b1;
                start_seen <= 1'b1;
                active_cycles <= 64'd0;
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
