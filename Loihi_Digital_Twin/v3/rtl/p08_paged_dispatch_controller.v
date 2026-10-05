`timescale 1ns/1ps

// P08 host-orchestrated one-engine dispatch controller.
//
// P05 keeps three full logical-context memory slots resident. P08 allows more
// logical cores to exist in host/backing storage by dispatching exactly one
// loaded slot at a time. The host is responsible for save/load, packet readback,
// logical-ID routing into backing next-event images, and the global algorithmic
// barrier. This controller deliberately does not require packet destinations to
// be resident.
//
// context_metadata reuses the accepted P05 64-bit record layout:
//   [6:0]   logical_core_id
//   [17:7]  compartment_count
//   [33:18] synapse_count
//   [46:34] route_count
//   [59:47] current event count
//   [63:60] reserved (must be zero)
module p08_paged_dispatch_controller (
    input  wire         clk,
    input  wire         resetn,

    input  wire         dispatch_start,
    input  wire         host_busy,
    input  wire [1:0]   requested_context_slot,
    input  wire [63:0]  context_metadata,
    input  wire [31:0]  dispatch_timestep,
    input  wire         requested_event_read_bank,

    output reg          core_start,
    input  wire         core_ready,
    input  wire         core_done,
    input  wire [12:0]  core_packet_count,
    input  wire [31:0]  core_status,

    output wire [10:0]  core_compartment_count,
    output wire [12:0]  core_event_count,
    output wire [15:0]  core_synapse_count,
    output wire [12:0]  core_route_count,
    output wire [31:0]  core_timestep,

    output reg  [1:0]   active_context_slot,
    output wire [6:0]   active_logical_core_id,
    output reg          event_read_bank,

    output reg          busy,
    output reg          dispatch_done,
    output reg          start_blocked,
    output reg  [12:0]  packet_count_latched,
    output reg  [31:0]  status_latched,
    output reg  [31:0]  completed_dispatches,
    output reg  [63:0]  active_cycles,
    output reg  [63:0]  last_dispatch_cycles,

    output reg          error_metadata,
    output reg          error_packet_overflow,
    output reg          error_core_status
);
    reg dispatch_start_d;
    reg [63:0] metadata_latched;
    reg [31:0] timestep_latched;

    wire metadata_valid =
        (context_metadata[63:60] == 4'd0) &&
        (context_metadata[17:7] <= 11'd1024) &&
        (context_metadata[33:18] <= 16'd32768) &&
        (context_metadata[46:34] <= 13'd4096) &&
        (context_metadata[59:47] <= 13'd4096) &&
        (requested_context_slot < 2'd3);

    wire dispatch_request = dispatch_start && !dispatch_start_d;
    wire start_allowed = !busy && !host_busy && metadata_valid;

    assign active_logical_core_id = metadata_latched[6:0];
    assign core_compartment_count = metadata_latched[17:7];
    assign core_synapse_count = metadata_latched[33:18];
    assign core_route_count = metadata_latched[46:34];
    assign core_event_count = metadata_latched[59:47];
    assign core_timestep = timestep_latched;

    // ap_ready remains an observation only, matching the accepted P04/P05 rule.
    wire unused_core_ready = core_ready;

    always @(posedge clk) begin
        if (!resetn) begin
            dispatch_start_d <= 1'b0;
            metadata_latched <= 64'd0;
            timestep_latched <= 32'd0;
            core_start <= 1'b0;
            active_context_slot <= 2'd0;
            event_read_bank <= 1'b0;
            busy <= 1'b0;
            dispatch_done <= 1'b0;
            start_blocked <= 1'b0;
            packet_count_latched <= 13'd0;
            status_latched <= 32'd0;
            completed_dispatches <= 32'd0;
            active_cycles <= 64'd0;
            last_dispatch_cycles <= 64'd0;
            error_metadata <= 1'b0;
            error_packet_overflow <= 1'b0;
            error_core_status <= 1'b0;
        end else begin
            dispatch_start_d <= dispatch_start;
            core_start <= 1'b0;
            dispatch_done <= 1'b0;
            start_blocked <= 1'b0;

            if (dispatch_request && !busy) begin
                if (start_allowed) begin
                    metadata_latched <= context_metadata;
                    timestep_latched <= dispatch_timestep;
                    active_context_slot <= requested_context_slot;
                    event_read_bank <= requested_event_read_bank;
                    packet_count_latched <= 13'd0;
                    status_latched <= 32'd0;
                    active_cycles <= 64'd0;
                    error_metadata <= 1'b0;
                    error_packet_overflow <= 1'b0;
                    error_core_status <= 1'b0;
                    busy <= 1'b1;
                    core_start <= 1'b1;
                end else begin
                    start_blocked <= 1'b1;
                    if (!metadata_valid)
                        error_metadata <= 1'b1;
                end
            end

            if (busy) begin
                active_cycles <= active_cycles + 64'd1;
                if (core_done) begin
                    packet_count_latched <= core_packet_count;
                    status_latched <= core_status;
                    last_dispatch_cycles <= active_cycles + 64'd1;
                    completed_dispatches <= completed_dispatches + 32'd1;
                    if (core_packet_count > 13'd4096)
                        error_packet_overflow <= 1'b1;
                    if (core_status != 32'd0)
                        error_core_status <= 1'b1;
                    busy <= 1'b0;
                    dispatch_done <= 1'b1;
                end
            end
        end
    end
endmodule
