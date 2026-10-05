`timescale 1ns/1ps

// P05 one-engine / three-logical-context scheduler and barrier controller.
//
// The unchanged P03 HLS engine services one retained logical context at a time.
// Logical core IDs come from context_metadata and remain visible in packet words;
// active_context_slot is only a physical memory-selection index.
//
// context_metadata packs three 64-bit records. For each slot:
//   [6:0]   logical_core_id
//   [17:7]  compartment_count
//   [33:18] synapse_count
//   [46:34] route_count
//   [59:47] initial_event_count
//   [63:60] reserved
//
// Input events are double-buffered in p05_context_memory_fabric. During one
// algorithmic timestep HLS reads event_read_bank and routed packets are appended
// to the opposite bank. The bank flips only after every logical context has
// completed and the packet stream is fully drained.
module p05_virtualized_controller (
    input  wire         clk,
    input  wire         resetn,

    input  wire         epoch_load,
    input  wire [31:0]  epoch_timestep,
    input  wire         tick_start,
    input  wire         service_reverse,
    input  wire         host_busy,
    input  wire [191:0] context_metadata,

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

    output wire         packet_mem_en,
    output wire [1:0]   packet_mem_context,
    output wire [11:0]  packet_mem_addr,
    input  wire [63:0]  packet_mem_data,

    output reg          event_mem_we,
    output reg  [1:0]   event_mem_context,
    output reg  [11:0]  event_mem_addr,
    output reg  [31:0]  event_mem_data,

    output reg          busy,
    output reg          tick_done,
    output reg          start_blocked,
    output reg          epoch_loaded,
    output reg  [31:0]  current_timestep,
    output wire [38:0]  current_event_counts_flat,
    output wire [38:0]  next_event_counts_flat,
    output reg  [2:0]   barrier_completed_mask,
    output wire         barrier_can_advance,
    output reg  [31:0]  local_packet_count,
    output reg  [31:0]  remote_packet_count,
    output reg  [31:0]  completed_ticks,
    output reg  [63:0]  active_cycles,
    output reg  [63:0]  last_tick_cycles,

    output reg          error_metadata,
    output reg          error_event_overflow,
    output reg          error_bad_packet_valid,
    output reg          error_bad_destination,
    output reg          error_bad_timestep,
    output reg          error_core_status
);
    localparam [1:0] ST_IDLE    = 2'd0;
    localparam [1:0] ST_HLS     = 2'd1;
    localparam [1:0] ST_STREAM  = 2'd2;
    localparam [1:0] ST_BARRIER = 2'd3;

    reg [1:0] state;
    reg tick_start_d;
    reg epoch_load_d;
    reg reverse_latched;
    reg stream_start;
    reg stream_done_seen;
    reg packet_pending;
    reg [63:0] packet_pending_word;

    reg [12:0] current_event_count [0:2];
    reg [12:0] next_event_count [0:2];

    wire [63:0] meta0 = context_metadata[63:0];
    wire [63:0] meta1 = context_metadata[127:64];
    wire [63:0] meta2 = context_metadata[191:128];

    reg [63:0] active_meta;
    always @* begin
        case (active_context_slot)
            2'd0: active_meta = meta0;
            2'd1: active_meta = meta1;
            2'd2: active_meta = meta2;
            default: active_meta = 64'd0;
        endcase
    end

    assign active_logical_core_id = active_meta[6:0];
    assign core_compartment_count = active_meta[17:7];
    assign core_synapse_count = active_meta[33:18];
    assign core_route_count = active_meta[46:34];
    assign core_event_count =
        (active_context_slot == 2'd0) ? current_event_count[0] :
        (active_context_slot == 2'd1) ? current_event_count[1] :
        current_event_count[2];
    assign core_timestep = current_timestep;

    assign current_event_counts_flat[12:0] = current_event_count[0];
    assign current_event_counts_flat[25:13] = current_event_count[1];
    assign current_event_counts_flat[38:26] = current_event_count[2];
    assign next_event_counts_flat[12:0] = next_event_count[0];
    assign next_event_counts_flat[25:13] = next_event_count[1];
    assign next_event_counts_flat[38:26] = next_event_count[2];

    wire metadata_counts_valid =
        (meta0[63:60] == 0) && (meta1[63:60] == 0) && (meta2[63:60] == 0) &&
        (meta0[17:7] <= 11'd1024) && (meta1[17:7] <= 11'd1024) && (meta2[17:7] <= 11'd1024) &&
        (meta0[33:18] <= 16'd32768) && (meta1[33:18] <= 16'd32768) && (meta2[33:18] <= 16'd32768) &&
        (meta0[46:34] <= 13'd4096) && (meta1[46:34] <= 13'd4096) && (meta2[46:34] <= 13'd4096) &&
        (meta0[59:47] <= 13'd4096) && (meta1[59:47] <= 13'd4096) && (meta2[59:47] <= 13'd4096);
    wire metadata_ids_unique =
        (meta0[6:0] != meta1[6:0]) &&
        (meta0[6:0] != meta2[6:0]) &&
        (meta1[6:0] != meta2[6:0]);
    wire metadata_valid = metadata_counts_valid && metadata_ids_unique;

    wire tick_request = tick_start && !tick_start_d;
    wire epoch_request = epoch_load && !epoch_load_d;
    wire start_allowed = !busy && epoch_loaded && !host_busy && metadata_valid;

    wire stream_done;
    wire stream_valid;
    wire [63:0] stream_packet;
    wire stream_ready = !packet_pending;

    assign packet_mem_context = active_context_slot;

    p04_packet_memory_streamer packet_streamer (
        .clk(clk),
        .resetn(resetn),
        .start(stream_start),
        .packet_count(core_packet_count),
        .done(stream_done),
        .mem_en(packet_mem_en),
        .mem_addr(packet_mem_addr),
        .mem_data(packet_mem_data),
        .stream_valid(stream_valid),
        .stream_packet(stream_packet),
        .stream_ready(stream_ready)
    );

    reg destination_found;
    reg [1:0] destination_slot;
    always @* begin
        destination_found = 1'b1;
        if (packet_pending_word[6:0] == meta0[6:0])
            destination_slot = 2'd0;
        else if (packet_pending_word[6:0] == meta1[6:0])
            destination_slot = 2'd1;
        else if (packet_pending_word[6:0] == meta2[6:0])
            destination_slot = 2'd2;
        else begin
            destination_slot = 2'd0;
            destination_found = 1'b0;
        end
    end

    wire [12:0] destination_next_count =
        (destination_slot == 2'd0) ? next_event_count[0] :
        (destination_slot == 2'd1) ? next_event_count[1] :
        next_event_count[2];

    assign barrier_can_advance =
        (state == ST_BARRIER) &&
        (barrier_completed_mask == 3'b111) &&
        !packet_pending &&
        !stream_valid;

    // ap_ready remains an observation only. P04 physical bring-up proved that
    // requiring it before ap_start creates a circular ap_ctrl_hs dependency.
    wire unused_core_ready = core_ready;

    integer i;
    always @(posedge clk) begin
        if (!resetn) begin
            state <= ST_IDLE;
            tick_start_d <= 1'b0;
            epoch_load_d <= 1'b0;
            reverse_latched <= 1'b0;
            core_start <= 1'b0;
            stream_start <= 1'b0;
            stream_done_seen <= 1'b0;
            packet_pending <= 1'b0;
            packet_pending_word <= 64'd0;
            active_context_slot <= 2'd0;
            event_read_bank <= 1'b0;
            event_mem_we <= 1'b0;
            event_mem_context <= 2'd0;
            event_mem_addr <= 12'd0;
            event_mem_data <= 32'd0;
            busy <= 1'b0;
            tick_done <= 1'b0;
            start_blocked <= 1'b0;
            epoch_loaded <= 1'b0;
            current_timestep <= 32'd0;
            barrier_completed_mask <= 3'b000;
            local_packet_count <= 32'd0;
            remote_packet_count <= 32'd0;
            completed_ticks <= 32'd0;
            active_cycles <= 64'd0;
            last_tick_cycles <= 64'd0;
            error_metadata <= 1'b0;
            error_event_overflow <= 1'b0;
            error_bad_packet_valid <= 1'b0;
            error_bad_destination <= 1'b0;
            error_bad_timestep <= 1'b0;
            error_core_status <= 1'b0;
            for (i = 0; i < 3; i = i + 1) begin
                current_event_count[i] <= 13'd0;
                next_event_count[i] <= 13'd0;
            end
        end else begin
            tick_start_d <= tick_start;
            epoch_load_d <= epoch_load;
            core_start <= 1'b0;
            stream_start <= 1'b0;
            event_mem_we <= 1'b0;
            tick_done <= 1'b0;
            start_blocked <= 1'b0;

            if (epoch_request && !busy) begin
                current_timestep <= epoch_timestep;
                current_event_count[0] <= meta0[59:47];
                current_event_count[1] <= meta1[59:47];
                current_event_count[2] <= meta2[59:47];
                next_event_count[0] <= 13'd0;
                next_event_count[1] <= 13'd0;
                next_event_count[2] <= 13'd0;
                event_read_bank <= 1'b0;
                epoch_loaded <= metadata_valid;
                error_metadata <= !metadata_valid;
                error_event_overflow <= 1'b0;
                error_bad_packet_valid <= 1'b0;
                error_bad_destination <= 1'b0;
                error_bad_timestep <= 1'b0;
                error_core_status <= 1'b0;
            end

            if (tick_request && !busy) begin
                if (start_allowed) begin
                    busy <= 1'b1;
                    state <= ST_HLS;
                    reverse_latched <= service_reverse;
                    active_context_slot <= service_reverse ? 2'd2 : 2'd0;
                    core_start <= 1'b1;
                    barrier_completed_mask <= 3'b000;
                    next_event_count[0] <= 13'd0;
                    next_event_count[1] <= 13'd0;
                    next_event_count[2] <= 13'd0;
                    local_packet_count <= 32'd0;
                    remote_packet_count <= 32'd0;
                    active_cycles <= 64'd0;
                    stream_done_seen <= 1'b0;
                    packet_pending <= 1'b0;
                    error_metadata <= 1'b0;
                    error_event_overflow <= 1'b0;
                    error_bad_packet_valid <= 1'b0;
                    error_bad_destination <= 1'b0;
                    error_bad_timestep <= 1'b0;
                    error_core_status <= 1'b0;
                end else begin
                    start_blocked <= 1'b1;
                    if (!metadata_valid)
                        error_metadata <= 1'b1;
                end
            end

            if (busy)
                active_cycles <= active_cycles + 64'd1;

            case (state)
                ST_IDLE: begin
                end

                ST_HLS: begin
                    if (core_done) begin
                        if (core_status != 0)
                            error_core_status <= 1'b1;
                        if (core_packet_count > 13'd4096)
                            error_event_overflow <= 1'b1;
                        stream_start <= 1'b1;
                        stream_done_seen <= 1'b0;
                        state <= ST_STREAM;
                    end
                end

                ST_STREAM: begin
                    if (stream_done)
                        stream_done_seen <= 1'b1;

                    if (stream_valid && stream_ready) begin
                        packet_pending <= 1'b1;
                        packet_pending_word <= stream_packet;
                    end

                    if (packet_pending) begin
                        if (!packet_pending_word[61]) begin
                            error_bad_packet_valid <= 1'b1;
                        end else if (packet_pending_word[63:62] != 0) begin
                            error_bad_packet_valid <= 1'b1;
                        end else if (!destination_found) begin
                            error_bad_destination <= 1'b1;
                        end else if (packet_pending_word[60:29] != (current_timestep + 32'd1)) begin
                            error_bad_timestep <= 1'b1;
                        end else if (destination_next_count >= 13'd4096) begin
                            error_event_overflow <= 1'b1;
                        end else begin
                            event_mem_we <= 1'b1;
                            event_mem_context <= destination_slot;
                            event_mem_addr <= destination_next_count[11:0];
                            event_mem_data <= {20'd0, packet_pending_word[18:7]};
                            case (destination_slot)
                                2'd0: next_event_count[0] <= next_event_count[0] + 13'd1;
                                2'd1: next_event_count[1] <= next_event_count[1] + 13'd1;
                                2'd2: next_event_count[2] <= next_event_count[2] + 13'd1;
                                default: begin end
                            endcase
                            if (packet_pending_word[6:0] == active_logical_core_id)
                                local_packet_count <= local_packet_count + 32'd1;
                            else
                                remote_packet_count <= remote_packet_count + 32'd1;
                        end
                        packet_pending <= 1'b0;
                    end

                    if (stream_done_seen && !packet_pending && !stream_valid) begin
                        barrier_completed_mask[active_context_slot] <= 1'b1;
                        stream_done_seen <= 1'b0;
                        if ((!reverse_latched && active_context_slot == 2'd2) ||
                            (reverse_latched && active_context_slot == 2'd0)) begin
                            state <= ST_BARRIER;
                        end else begin
                            active_context_slot <= reverse_latched
                                ? active_context_slot - 2'd1
                                : active_context_slot + 2'd1;
                            core_start <= 1'b1;
                            state <= ST_HLS;
                        end
                    end
                end

                ST_BARRIER: begin
                    if (barrier_can_advance) begin
                        busy <= 1'b0;
                        tick_done <= 1'b1;
                        state <= ST_IDLE;
                        current_timestep <= current_timestep + 32'd1;
                        current_event_count[0] <= next_event_count[0];
                        current_event_count[1] <= next_event_count[1];
                        current_event_count[2] <= next_event_count[2];
                        next_event_count[0] <= 13'd0;
                        next_event_count[1] <= 13'd0;
                        next_event_count[2] <= 13'd0;
                        event_read_bank <= !event_read_bank;
                        completed_ticks <= completed_ticks + 32'd1;
                        last_tick_cycles <= active_cycles + 64'd1;
                    end
                end

                default: begin
                    state <= ST_IDLE;
                    busy <= 1'b0;
                    error_metadata <= 1'b1;
                end
            endcase
        end
    end
endmodule
