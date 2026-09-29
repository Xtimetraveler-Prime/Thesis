`timescale 1ns/1ps

// Reads one completed HLS packet_words image through its synchronous Port-B
// interface and presents the records as a ready/valid stream.  The P03 HLS core
// writes packet_words without backpressure, so P04 drains that retained image
// only after ap_done rather than trying to backpressure the HLS memory write
// port directly.
//
// done is a one-cycle completion pulse for each accepted start.  It must not be
// sticky across runs: a stale done from timestep t could otherwise make the
// barrier believe timestep t+1 egress had drained before the new packet-memory
// traversal actually started.
module p04_packet_memory_streamer (
    input  wire        clk,
    input  wire        resetn,

    input  wire        start,
    input  wire [12:0] packet_count,
    output reg         done,

    output wire        mem_en,
    output wire [11:0] mem_addr,
    input  wire [63:0] mem_data,

    output wire        stream_valid,
    output wire [63:0] stream_packet,
    input  wire        stream_ready
);
    localparam [1:0] ST_IDLE  = 2'd0;
    localparam [1:0] ST_ISSUE = 2'd1;
    localparam [1:0] ST_WAIT  = 2'd2;
    localparam [1:0] ST_HOLD  = 2'd3;

    reg [1:0] state;
    reg [12:0] latched_count;
    reg [11:0] index;
    reg [63:0] packet_hold;

    assign mem_en = (state == ST_ISSUE);
    assign mem_addr = index;
    assign stream_valid = (state == ST_HOLD);
    assign stream_packet = packet_hold;

    always @(posedge clk) begin
        if (!resetn) begin
            state <= ST_IDLE;
            latched_count <= 13'd0;
            index <= 12'd0;
            packet_hold <= 64'd0;
            done <= 1'b0;
        end else begin
            // Completion is a pulse, not retained state.  The router latches
            // endpoint completion, so one cycle is sufficient and avoids stale
            // completion leaking into a later algorithmic timestep.
            done <= 1'b0;

            if (start) begin
                latched_count <= packet_count;
                index <= 12'd0;
                if (packet_count == 0) begin
                    done <= 1'b1;
                    state <= ST_IDLE;
                end else begin
                    state <= ST_ISSUE;
                end
            end else begin
                case (state)
                    ST_IDLE: begin
                    end
                    ST_ISSUE: begin
                        // The synchronous memory samples mem_addr at this edge.
                        state <= ST_WAIT;
                    end
                    ST_WAIT: begin
                        // mem_data now corresponds to the address issued during
                        // the previous ST_ISSUE cycle.
                        packet_hold <= mem_data;
                        state <= ST_HOLD;
                    end
                    ST_HOLD: begin
                        if (stream_valid && stream_ready) begin
                            if (index + 12'd1 >= latched_count) begin
                                done <= 1'b1;
                                state <= ST_IDLE;
                            end else begin
                                index <= index + 12'd1;
                                state <= ST_ISSUE;
                            end
                        end
                    end
                    default: begin
                        state <= ST_IDLE;
                    end
                endcase
            end
        end
    end
endmodule
