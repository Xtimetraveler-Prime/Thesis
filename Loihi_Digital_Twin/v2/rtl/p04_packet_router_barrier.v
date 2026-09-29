`timescale 1ns / 1ps

// P04 two-endpoint packet router + algorithmic-timestep barrier.
//
// The packet word is the accepted P03 64-bit egress format:
//   [6:0]    destination logical core
//   [18:7]   destination axon ID
//   [28:19]  source compartment
//   [60:29]  target algorithmic timestep
//   [61]     valid
//   [63:62]  reserved
//
// Source-core identity is implicit in the producer port (src0/src1).  This
// module intentionally models the P04 architectural routing boundary rather
// than native Loihi physical mesh timing.
module p04_packet_router_barrier #(
    parameter integer FIFO_DEPTH = 16
) (
    input  wire         clk,
    input  wire         resetn,

    input  wire         timestep_start,
    input  wire [31:0]  timestep_value,
    input  wire         advance_req,
    output reg          advance_ack,
    output reg          advance_blocked,
    output reg          barrier_active,
    output wire         can_advance,
    output reg  [1:0]   completed_mask,
    output wire [15:0]  in_flight_count,

    input  wire [1:0]   core_done,
    input  wire         service_reverse,

    input  wire         src0_valid,
    input  wire [63:0]  src0_packet,
    output wire         src0_ready,

    input  wire         src1_valid,
    input  wire [63:0]  src1_packet,
    output wire         src1_ready,

    output wire         dst0_valid,
    output wire [63:0]  dst0_packet,
    input  wire         dst0_ready,

    output wire         dst1_valid,
    output wire [63:0]  dst1_packet,
    input  wire         dst1_ready,

    output reg  [31:0]  local_packet_count,
    output reg  [31:0]  remote_packet_count,
    output reg          error_bad_valid,
    output reg          error_bad_destination,
    output reg          error_bad_timestep
);

    localparam integer PTR_WIDTH = (FIFO_DEPTH <= 2) ? 1 : $clog2(FIFO_DEPTH);
    localparam integer COUNT_WIDTH = (FIFO_DEPTH <= 1) ? 1 : $clog2(FIFO_DEPTH + 1);

    reg [31:0] active_timestep;

    reg        pending0_valid;
    reg [63:0] pending0_packet;
    reg        pending1_valid;
    reg [63:0] pending1_packet;

    reg [63:0] fifo0 [0:FIFO_DEPTH-1];
    reg [63:0] fifo1 [0:FIFO_DEPTH-1];
    reg [PTR_WIDTH-1:0] fifo0_wr_ptr;
    reg [PTR_WIDTH-1:0] fifo0_rd_ptr;
    reg [PTR_WIDTH-1:0] fifo1_wr_ptr;
    reg [PTR_WIDTH-1:0] fifo1_rd_ptr;
    reg [COUNT_WIDTH-1:0] fifo0_count;
    reg [COUNT_WIDTH-1:0] fifo1_count;

    wire pop0 = dst0_valid && dst0_ready;
    wire pop1 = dst1_valid && dst1_ready;

    assign src0_ready = barrier_active && !pending0_valid;
    assign src1_ready = barrier_active && !pending1_valid;

    assign dst0_valid = (fifo0_count != 0);
    assign dst1_valid = (fifo1_count != 0);
    assign dst0_packet = fifo0[fifo0_rd_ptr];
    assign dst1_packet = fifo1[fifo1_rd_ptr];

    wire [15:0] pending_count =
        (pending0_valid ? 16'd1 : 16'd0) +
        (pending1_valid ? 16'd1 : 16'd0);
    assign in_flight_count = pending_count + fifo0_count + fifo1_count;

    // A presented source transaction also blocks advance during the cycle in
    // which it is about to be captured.
    wire source_capture_pending =
        (src0_valid && src0_ready) || (src1_valid && src1_ready);

    assign can_advance =
        barrier_active &&
        (completed_mask == 2'b11) &&
        (in_flight_count == 0) &&
        !source_capture_pending;

    reg        selected_valid;
    reg        selected_source;
    reg [63:0] selected_packet;

    always @* begin
        selected_valid = 1'b0;
        selected_source = 1'b0;
        selected_packet = 64'd0;

        if (pending0_valid && pending1_valid) begin
            if (service_reverse) begin
                selected_valid = 1'b1;
                selected_source = 1'b1;
                selected_packet = pending1_packet;
            end else begin
                selected_valid = 1'b1;
                selected_source = 1'b0;
                selected_packet = pending0_packet;
            end
        end else if (pending0_valid) begin
            selected_valid = 1'b1;
            selected_source = 1'b0;
            selected_packet = pending0_packet;
        end else if (pending1_valid) begin
            selected_valid = 1'b1;
            selected_source = 1'b1;
            selected_packet = pending1_packet;
        end
    end

    wire [6:0] selected_destination = selected_packet[6:0];
    wire [31:0] selected_target_timestep = selected_packet[60:29];
    wire selected_word_valid = selected_packet[61];
    wire destination_supported =
        (selected_destination == 7'd0) || (selected_destination == 7'd1);
    wire timestep_supported =
        (selected_target_timestep == (active_timestep + 32'd1));
    wire integrity_ok =
        selected_word_valid && destination_supported && timestep_supported;

    wire selected_for_dst0 = selected_valid && (selected_destination == 7'd0);
    wire selected_for_dst1 = selected_valid && (selected_destination == 7'd1);

    // Allow a push into a full FIFO if that FIFO is also popping this cycle.
    wire dst0_has_space = (fifo0_count < FIFO_DEPTH) || pop0;
    wire dst1_has_space = (fifo1_count < FIFO_DEPTH) || pop1;

    wire selected_queue_has_space =
        selected_for_dst0 ? dst0_has_space :
        selected_for_dst1 ? dst1_has_space : 1'b1;

    // Invalid packets are consumed after setting a sticky status error so they
    // cannot deadlock the barrier. Valid packets wait for destination space.
    wire route_fire =
        selected_valid && (!integrity_ok || selected_queue_has_space);
    wire push0 = route_fire && integrity_ok && selected_for_dst0;
    wire push1 = route_fire && integrity_ok && selected_for_dst1;

    integer i;
    always @(posedge clk) begin
        if (!resetn) begin
            active_timestep <= 32'd0;
            advance_ack <= 1'b0;
            advance_blocked <= 1'b0;
            barrier_active <= 1'b0;
            completed_mask <= 2'b00;

            pending0_valid <= 1'b0;
            pending0_packet <= 64'd0;
            pending1_valid <= 1'b0;
            pending1_packet <= 64'd0;

            fifo0_wr_ptr <= {PTR_WIDTH{1'b0}};
            fifo0_rd_ptr <= {PTR_WIDTH{1'b0}};
            fifo1_wr_ptr <= {PTR_WIDTH{1'b0}};
            fifo1_rd_ptr <= {PTR_WIDTH{1'b0}};
            fifo0_count <= {COUNT_WIDTH{1'b0}};
            fifo1_count <= {COUNT_WIDTH{1'b0}};

            local_packet_count <= 32'd0;
            remote_packet_count <= 32'd0;
            error_bad_valid <= 1'b0;
            error_bad_destination <= 1'b0;
            error_bad_timestep <= 1'b0;

            for (i = 0; i < FIFO_DEPTH; i = i + 1) begin
                fifo0[i] <= 64'd0;
                fifo1[i] <= 64'd0;
            end
        end else begin
            advance_ack <= 1'b0;
            advance_blocked <= 1'b0;

            if (timestep_start && !barrier_active) begin
                active_timestep <= timestep_value;
                barrier_active <= 1'b1;
                completed_mask <= 2'b00;

                pending0_valid <= 1'b0;
                pending1_valid <= 1'b0;
                fifo0_wr_ptr <= {PTR_WIDTH{1'b0}};
                fifo0_rd_ptr <= {PTR_WIDTH{1'b0}};
                fifo1_wr_ptr <= {PTR_WIDTH{1'b0}};
                fifo1_rd_ptr <= {PTR_WIDTH{1'b0}};
                fifo0_count <= {COUNT_WIDTH{1'b0}};
                fifo1_count <= {COUNT_WIDTH{1'b0}};

                local_packet_count <= 32'd0;
                remote_packet_count <= 32'd0;
                error_bad_valid <= 1'b0;
                error_bad_destination <= 1'b0;
                error_bad_timestep <= 1'b0;
            end else if (barrier_active) begin
                completed_mask <= completed_mask | core_done;

                if (src0_valid && src0_ready) begin
                    pending0_valid <= 1'b1;
                    pending0_packet <= src0_packet;
                end
                if (src1_valid && src1_ready) begin
                    pending1_valid <= 1'b1;
                    pending1_packet <= src1_packet;
                end

                if (route_fire) begin
                    if (selected_source == 1'b0)
                        pending0_valid <= 1'b0;
                    else
                        pending1_valid <= 1'b0;

                    if (!selected_word_valid)
                        error_bad_valid <= 1'b1;
                    if (!destination_supported)
                        error_bad_destination <= 1'b1;
                    if (!timestep_supported)
                        error_bad_timestep <= 1'b1;

                    if (integrity_ok) begin
                        if ((selected_source == 1'b0 && selected_destination == 7'd0) ||
                            (selected_source == 1'b1 && selected_destination == 7'd1))
                            local_packet_count <= local_packet_count + 32'd1;
                        else
                            remote_packet_count <= remote_packet_count + 32'd1;
                    end
                end

                if (push0) begin
                    fifo0[fifo0_wr_ptr] <= selected_packet;
                    if (fifo0_wr_ptr == FIFO_DEPTH - 1)
                        fifo0_wr_ptr <= {PTR_WIDTH{1'b0}};
                    else
                        fifo0_wr_ptr <= fifo0_wr_ptr + 1'b1;
                end
                if (pop0) begin
                    if (fifo0_rd_ptr == FIFO_DEPTH - 1)
                        fifo0_rd_ptr <= {PTR_WIDTH{1'b0}};
                    else
                        fifo0_rd_ptr <= fifo0_rd_ptr + 1'b1;
                end
                case ({push0, pop0})
                    2'b10: fifo0_count <= fifo0_count + 1'b1;
                    2'b01: fifo0_count <= fifo0_count - 1'b1;
                    default: fifo0_count <= fifo0_count;
                endcase

                if (push1) begin
                    fifo1[fifo1_wr_ptr] <= selected_packet;
                    if (fifo1_wr_ptr == FIFO_DEPTH - 1)
                        fifo1_wr_ptr <= {PTR_WIDTH{1'b0}};
                    else
                        fifo1_wr_ptr <= fifo1_wr_ptr + 1'b1;
                end
                if (pop1) begin
                    if (fifo1_rd_ptr == FIFO_DEPTH - 1)
                        fifo1_rd_ptr <= {PTR_WIDTH{1'b0}};
                    else
                        fifo1_rd_ptr <= fifo1_rd_ptr + 1'b1;
                end
                case ({push1, pop1})
                    2'b10: fifo1_count <= fifo1_count + 1'b1;
                    2'b01: fifo1_count <= fifo1_count - 1'b1;
                    default: fifo1_count <= fifo1_count;
                endcase

                if (advance_req) begin
                    if (can_advance) begin
                        advance_ack <= 1'b1;
                        barrier_active <= 1'b0;
                    end else begin
                        advance_blocked <= 1'b1;
                    end
                end
            end
        end
    end

endmodule
