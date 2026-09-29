`timescale 1ns/1ps

// P04 directed two-core integration controller.
//
// One tick consists of:
//   1. start both accepted P03 HLS core endpoints on the same algorithmic time;
//   2. after each ap_done, drain that core's retained packet_words image;
//   3. route packets through p04_packet_router_barrier;
//   4. write destination axon IDs into the next-timestep input_events image;
//   5. advance only after both egress streams and both destination queues drain.
//
// The physical allocation parameters describe the P04 validation fixture only;
// they are not Loihi logical capacities.
module p04_two_core_controller #(
    parameter integer PHYS_COMPARTMENTS = 16,
    parameter integer PHYS_AXONS = 64,
    parameter integer PHYS_SYNAPSES = 256,
    parameter integer PHYS_ROUTES = 64,
    parameter integer PHYS_EVENTS = 64,
    parameter integer PHYS_PACKETS = 64,
    parameter integer ROUTER_FIFO_DEPTH = 16
) (
    input  wire         clk,
    input  wire         resetn,

    input  wire         epoch_load,
    input  wire [31:0]  epoch_timestep,
    input  wire [12:0]  epoch_event_count0,
    input  wire [12:0]  epoch_event_count1,
    input  wire         tick_start,
    input  wire         service_reverse,
    input  wire         host_busy0,
    input  wire         host_busy1,

    input  wire [10:0]  compartment_count0,
    input  wire [15:0]  synapse_count0,
    input  wire [12:0]  route_count0,
    input  wire [10:0]  compartment_count1,
    input  wire [15:0]  synapse_count1,
    input  wire [12:0]  route_count1,

    output reg          core0_start,
    input  wire         core0_ready,
    input  wire         core0_done,
    input  wire [12:0]  core0_packet_count,
    input  wire [31:0]  core0_status,

    output reg          core1_start,
    input  wire         core1_ready,
    input  wire         core1_done,
    input  wire [12:0]  core1_packet_count,
    input  wire [31:0]  core1_status,

    output wire [12:0]  core0_event_count,
    output wire [12:0]  core1_event_count,
    output wire [31:0]  core_timestep,

    output wire         core0_packet_mem_en,
    output wire [11:0]  core0_packet_mem_addr,
    input  wire [63:0]  core0_packet_mem_data,
    output wire         core1_packet_mem_en,
    output wire [11:0]  core1_packet_mem_addr,
    input  wire [63:0]  core1_packet_mem_data,

    output reg          core0_event_mem_we,
    output reg  [11:0]  core0_event_mem_addr,
    output reg  [31:0]  core0_event_mem_data,
    output reg          core1_event_mem_we,
    output reg  [11:0]  core1_event_mem_addr,
    output reg  [31:0]  core1_event_mem_data,

    output reg          busy,
    output reg          tick_done,
    output reg          start_blocked,
    output reg          epoch_loaded,
    output reg  [31:0]  current_timestep,
    output reg  [12:0]  current_event_count0,
    output reg  [12:0]  current_event_count1,
    output reg  [12:0]  next_event_count0,
    output reg  [12:0]  next_event_count1,
    output wire [15:0]  in_flight_count,
    output wire [1:0]   barrier_completed_mask,
    output wire         barrier_can_advance,
    output wire [31:0]  local_packet_count,
    output wire [31:0]  remote_packet_count,
    output reg  [31:0]  completed_ticks,
    output reg  [63:0]  active_cycles,
    output reg  [63:0]  last_tick_cycles,

    output reg          error_physical_capacity,
    output reg          error_event_overflow,
    output reg          error_event_axon,
    output reg          error_core_status,
    output wire         error_router_bad_valid,
    output wire         error_router_bad_destination,
    output wire         error_router_bad_timestep
);
    reg tick_start_d;
    reg epoch_load_d;
    reg core0_done_seen;
    reg core1_done_seen;
    reg core0_stream_start;
    reg core1_stream_start;

    wire core0_stream_done;
    wire core1_stream_done;
    wire core0_stream_valid;
    wire core1_stream_valid;
    wire [63:0] core0_stream_packet;
    wire [63:0] core1_stream_packet;
    wire core0_stream_ready;
    wire core1_stream_ready;

    wire router_dst0_valid;
    wire router_dst1_valid;
    wire [63:0] router_dst0_packet;
    wire [63:0] router_dst1_packet;
    wire router_dst0_ready;
    wire router_dst1_ready;
    wire router_advance_ack;
    wire router_advance_blocked;
    wire router_barrier_active;

    wire core0_egress_done = core0_done_seen && core0_stream_done;
    wire core1_egress_done = core1_done_seen && core1_stream_done;

    wire counts_fit_fixture =
        (compartment_count0 <= PHYS_COMPARTMENTS) &&
        (compartment_count1 <= PHYS_COMPARTMENTS) &&
        (synapse_count0 <= PHYS_SYNAPSES) &&
        (synapse_count1 <= PHYS_SYNAPSES) &&
        (route_count0 <= PHYS_ROUTES) &&
        (route_count1 <= PHYS_ROUTES) &&
        (current_event_count0 <= PHYS_EVENTS) &&
        (current_event_count1 <= PHYS_EVENTS);

    wire tick_request = tick_start && !tick_start_d;
    wire epoch_request = epoch_load && !epoch_load_d;
    wire start_allowed =
        !busy && epoch_loaded && !host_busy0 && !host_busy1 &&
        core0_ready && core1_ready && counts_fit_fixture;

    assign core0_event_count = current_event_count0;
    assign core1_event_count = current_event_count1;
    assign core_timestep = current_timestep;

    // Backpressure preserves events rather than silently dropping them when the
    // directed physical event allocation is exhausted.
    assign router_dst0_ready = (next_event_count0 < PHYS_EVENTS);
    assign router_dst1_ready = (next_event_count1 < PHYS_EVENTS);

    p04_packet_memory_streamer core0_streamer (
        .clk(clk),
        .resetn(resetn),
        .start(core0_stream_start),
        .packet_count(core0_packet_count),
        .done(core0_stream_done),
        .mem_en(core0_packet_mem_en),
        .mem_addr(core0_packet_mem_addr),
        .mem_data(core0_packet_mem_data),
        .stream_valid(core0_stream_valid),
        .stream_packet(core0_stream_packet),
        .stream_ready(core0_stream_ready)
    );

    p04_packet_memory_streamer core1_streamer (
        .clk(clk),
        .resetn(resetn),
        .start(core1_stream_start),
        .packet_count(core1_packet_count),
        .done(core1_stream_done),
        .mem_en(core1_packet_mem_en),
        .mem_addr(core1_packet_mem_addr),
        .mem_data(core1_packet_mem_data),
        .stream_valid(core1_stream_valid),
        .stream_packet(core1_stream_packet),
        .stream_ready(core1_stream_ready)
    );

    p04_packet_router_barrier #(
        .FIFO_DEPTH(ROUTER_FIFO_DEPTH)
    ) router (
        .clk(clk),
        .resetn(resetn),
        .timestep_start(core0_start && core1_start),
        .timestep_value(current_timestep),
        .advance_req(busy && barrier_can_advance),
        .advance_ack(router_advance_ack),
        .advance_blocked(router_advance_blocked),
        .barrier_active(router_barrier_active),
        .can_advance(barrier_can_advance),
        .completed_mask(barrier_completed_mask),
        .in_flight_count(in_flight_count),
        .core_done({core1_egress_done, core0_egress_done}),
        .service_reverse(service_reverse),
        .src0_valid(core0_stream_valid),
        .src0_packet(core0_stream_packet),
        .src0_ready(core0_stream_ready),
        .src1_valid(core1_stream_valid),
        .src1_packet(core1_stream_packet),
        .src1_ready(core1_stream_ready),
        .dst0_valid(router_dst0_valid),
        .dst0_packet(router_dst0_packet),
        .dst0_ready(router_dst0_ready),
        .dst1_valid(router_dst1_valid),
        .dst1_packet(router_dst1_packet),
        .dst1_ready(router_dst1_ready),
        .local_packet_count(local_packet_count),
        .remote_packet_count(remote_packet_count),
        .error_bad_valid(error_router_bad_valid),
        .error_bad_destination(error_router_bad_destination),
        .error_bad_timestep(error_router_bad_timestep)
    );

    always @(posedge clk) begin
        if (!resetn) begin
            tick_start_d <= 1'b0;
            epoch_load_d <= 1'b0;
            core0_start <= 1'b0;
            core1_start <= 1'b0;
            core0_stream_start <= 1'b0;
            core1_stream_start <= 1'b0;
            core0_done_seen <= 1'b0;
            core1_done_seen <= 1'b0;

            core0_event_mem_we <= 1'b0;
            core0_event_mem_addr <= 12'd0;
            core0_event_mem_data <= 32'd0;
            core1_event_mem_we <= 1'b0;
            core1_event_mem_addr <= 12'd0;
            core1_event_mem_data <= 32'd0;

            busy <= 1'b0;
            tick_done <= 1'b0;
            start_blocked <= 1'b0;
            epoch_loaded <= 1'b0;
            current_timestep <= 32'd0;
            current_event_count0 <= 13'd0;
            current_event_count1 <= 13'd0;
            next_event_count0 <= 13'd0;
            next_event_count1 <= 13'd0;
            completed_ticks <= 32'd0;
            active_cycles <= 64'd0;
            last_tick_cycles <= 64'd0;

            error_physical_capacity <= 1'b0;
            error_event_overflow <= 1'b0;
            error_event_axon <= 1'b0;
            error_core_status <= 1'b0;
        end else begin
            tick_start_d <= tick_start;
            epoch_load_d <= epoch_load;
            core0_start <= 1'b0;
            core1_start <= 1'b0;
            core0_stream_start <= 1'b0;
            core1_stream_start <= 1'b0;
            core0_event_mem_we <= 1'b0;
            core1_event_mem_we <= 1'b0;
            tick_done <= 1'b0;
            start_blocked <= 1'b0;

            if (epoch_request && !busy) begin
                current_timestep <= epoch_timestep;
                current_event_count0 <= epoch_event_count0;
                current_event_count1 <= epoch_event_count1;
                next_event_count0 <= 13'd0;
                next_event_count1 <= 13'd0;
                epoch_loaded <= 1'b1;
                error_physical_capacity <=
                    (epoch_event_count0 > PHYS_EVENTS) ||
                    (epoch_event_count1 > PHYS_EVENTS);
                error_event_overflow <= 1'b0;
                error_event_axon <= 1'b0;
                error_core_status <= 1'b0;
            end

            if (tick_request && !busy) begin
                if (start_allowed) begin
                    core0_start <= 1'b1;
                    core1_start <= 1'b1;
                    busy <= 1'b1;
                    core0_done_seen <= 1'b0;
                    core1_done_seen <= 1'b0;
                    next_event_count0 <= 13'd0;
                    next_event_count1 <= 13'd0;
                    active_cycles <= 64'd0;
                    error_physical_capacity <= 1'b0;
                    error_event_overflow <= 1'b0;
                    error_event_axon <= 1'b0;
                    error_core_status <= 1'b0;
                end else begin
                    start_blocked <= 1'b1;
                    if (!counts_fit_fixture)
                        error_physical_capacity <= 1'b1;
                end
            end

            if (busy) begin
                active_cycles <= active_cycles + 64'd1;

                if (core0_done && !core0_done_seen) begin
                    core0_done_seen <= 1'b1;
                    core0_stream_start <= 1'b1;
                    if (core0_status != 0)
                        error_core_status <= 1'b1;
                    if (core0_packet_count > PHYS_PACKETS)
                        error_physical_capacity <= 1'b1;
                end
                if (core1_done && !core1_done_seen) begin
                    core1_done_seen <= 1'b1;
                    core1_stream_start <= 1'b1;
                    if (core1_status != 0)
                        error_core_status <= 1'b1;
                    if (core1_packet_count > PHYS_PACKETS)
                        error_physical_capacity <= 1'b1;
                end

                if (router_dst0_valid && !router_dst0_ready)
                    error_event_overflow <= 1'b1;
                if (router_dst1_valid && !router_dst1_ready)
                    error_event_overflow <= 1'b1;

                if (router_dst0_valid && router_dst0_ready) begin
                    if (router_dst0_packet[18:7] >= PHYS_AXONS) begin
                        error_event_axon <= 1'b1;
                    end else begin
                        core0_event_mem_we <= 1'b1;
                        core0_event_mem_addr <= next_event_count0[11:0];
                        core0_event_mem_data <= {20'd0, router_dst0_packet[18:7]};
                        next_event_count0 <= next_event_count0 + 13'd1;
                    end
                end

                if (router_dst1_valid && router_dst1_ready) begin
                    if (router_dst1_packet[18:7] >= PHYS_AXONS) begin
                        error_event_axon <= 1'b1;
                    end else begin
                        core1_event_mem_we <= 1'b1;
                        core1_event_mem_addr <= next_event_count1[11:0];
                        core1_event_mem_data <= {20'd0, router_dst1_packet[18:7]};
                        next_event_count1 <= next_event_count1 + 13'd1;
                    end
                end

                if (router_advance_ack) begin
                    busy <= 1'b0;
                    tick_done <= 1'b1;
                    current_timestep <= current_timestep + 32'd1;
                    current_event_count0 <= next_event_count0;
                    current_event_count1 <= next_event_count1;
                    completed_ticks <= completed_ticks + 32'd1;
                    last_tick_cycles <= active_cycles;
                end
            end
        end
    end
endmodule
