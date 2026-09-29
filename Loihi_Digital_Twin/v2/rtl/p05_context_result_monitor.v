`timescale 1ns/1ps

// Capture the most recent HLS spike/packet counts for each retained logical
// context.  The HLS core itself is physically shared, so its scalar result ports
// otherwise only expose whichever context completed most recently.
//
// This monitor is observability only: it does not participate in scheduling,
// routing, barrier completion, or architectural state updates.
module p05_context_result_monitor (
    input  wire        clk,
    input  wire        resetn,
    input  wire        core_done,
    input  wire [1:0]  active_context_slot,
    input  wire [10:0] core_spike_count,
    input  wire [12:0] core_packet_count,

    output wire [32:0] spike_counts_flat,
    output wire [38:0] packet_counts_flat
);
    reg [10:0] spike_count [0:2];
    reg [12:0] packet_count [0:2];
    integer i;

    assign spike_counts_flat[10:0] = spike_count[0];
    assign spike_counts_flat[21:11] = spike_count[1];
    assign spike_counts_flat[32:22] = spike_count[2];

    assign packet_counts_flat[12:0] = packet_count[0];
    assign packet_counts_flat[25:13] = packet_count[1];
    assign packet_counts_flat[38:26] = packet_count[2];

    always @(posedge clk) begin
        if (!resetn) begin
            for (i = 0; i < 3; i = i + 1) begin
                spike_count[i] <= 11'd0;
                packet_count[i] <= 13'd0;
            end
        end else if (core_done) begin
            case (active_context_slot)
                2'd0: begin
                    spike_count[0] <= core_spike_count;
                    packet_count[0] <= core_packet_count;
                end
                2'd1: begin
                    spike_count[1] <= core_spike_count;
                    packet_count[1] <= core_packet_count;
                end
                2'd2: begin
                    spike_count[2] <= core_spike_count;
                    packet_count[2] <= core_packet_count;
                end
                default: begin
                end
            endcase
        end
    end
endmodule
