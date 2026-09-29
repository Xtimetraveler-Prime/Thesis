`timescale 1ns/1ps

// Unified P03 host/debug access path for the second port of every external
// logical-core memory bank.  Port A belongs to the HLS compute core; this
// module exclusively drives Port B while the compute core is idle.
//
// Bank IDs:
//   0 config_words       1024 x 128
//   1 state_words        1024 x 64
//   2 axon_words         4096 x 64
//   3 synapse_words     32768 x 64
//   4 route_desc_words   1024 x 32
//   5 route_words        4096 x 32
//   6 input_events       4096 x 32
//   7 trace_words        1024 x 256
//   8 packet_words       4096 x 64
//
// The command data path is a 256-bit superset.  Narrow banks consume/produce
// the least-significant bits.  A request is accepted only on a rising edge of
// req and only while compute_busy is low.  Reads and writes acknowledge after
// the synchronous Block Memory Generator transaction has completed.
module p03_memory_host_bridge (
    input  wire         clk,
    input  wire         resetn,
    input  wire         compute_busy,

    input  wire         req,
    input  wire         write,
    input  wire [3:0]   bank,
    input  wire [14:0]  addr,
    input  wire [255:0] wdata,

    output wire         host_busy,
    output reg          ack,
    output reg          rvalid,
    output reg          error,
    output reg  [255:0] rdata,

    output reg          config_words_enb,
    output reg          config_words_web,
    output reg  [9:0]   config_words_addrb,
    output reg  [127:0] config_words_dinb,
    input  wire [127:0] config_words_doutb,

    output reg          state_words_enb,
    output reg          state_words_web,
    output reg  [9:0]   state_words_addrb,
    output reg  [63:0]  state_words_dinb,
    input  wire [63:0]  state_words_doutb,

    output reg          axon_words_enb,
    output reg          axon_words_web,
    output reg  [11:0]  axon_words_addrb,
    output reg  [63:0]  axon_words_dinb,
    input  wire [63:0]  axon_words_doutb,

    output reg          synapse_words_enb,
    output reg          synapse_words_web,
    output reg  [14:0]  synapse_words_addrb,
    output reg  [63:0]  synapse_words_dinb,
    input  wire [63:0]  synapse_words_doutb,

    output reg          route_desc_words_enb,
    output reg          route_desc_words_web,
    output reg  [9:0]   route_desc_words_addrb,
    output reg  [31:0]  route_desc_words_dinb,
    input  wire [31:0]  route_desc_words_doutb,

    output reg          route_words_enb,
    output reg          route_words_web,
    output reg  [11:0]  route_words_addrb,
    output reg  [31:0]  route_words_dinb,
    input  wire [31:0]  route_words_doutb,

    output reg          input_events_enb,
    output reg          input_events_web,
    output reg  [11:0]  input_events_addrb,
    output reg  [31:0]  input_events_dinb,
    input  wire [31:0]  input_events_doutb,

    output reg          trace_words_enb,
    output reg          trace_words_web,
    output reg  [9:0]   trace_words_addrb,
    output reg  [255:0] trace_words_dinb,
    input  wire [255:0] trace_words_doutb,

    output reg          packet_words_enb,
    output reg          packet_words_web,
    output reg  [11:0]  packet_words_addrb,
    output reg  [63:0]  packet_words_dinb,
    input  wire [63:0]  packet_words_doutb
);
    localparam [1:0] ST_IDLE     = 2'd0;
    localparam [1:0] ST_ISSUE    = 2'd1;
    localparam [1:0] ST_COMPLETE = 2'd2;

    reg [1:0]   state;
    reg         req_d;
    reg         cmd_write;
    reg [3:0]   cmd_bank;
    reg [14:0]  cmd_addr;
    reg [255:0] cmd_wdata;

    // Treat an asserted request as busy immediately.  This gives the run
    // monitor a combinational interlock so a host transaction wins if a host
    // request and compute-start request are presented in the same cycle.
    assign host_busy = (state != ST_IDLE) || req;

    function addr_valid;
        input [3:0] bank_id;
        input [14:0] word_addr;
        begin
            case (bank_id)
                4'd0, 4'd1, 4'd4, 4'd7:
                    addr_valid = (word_addr < 15'd1024);
                4'd2, 4'd5, 4'd6, 4'd8:
                    addr_valid = (word_addr < 15'd4096);
                4'd3:
                    addr_valid = 1'b1; // 15 bits exactly cover 0..32767.
                default:
                    addr_valid = 1'b0;
            endcase
        end
    endfunction

    // Port-B controls are asserted for the complete ST_ISSUE cycle.  The
    // synchronous BMG performs the access at the following rising edge.  The
    // result is sampled one cycle later in ST_COMPLETE.
    always @* begin
        config_words_enb = 1'b0;
        config_words_web = 1'b0;
        config_words_addrb = cmd_addr[9:0];
        config_words_dinb = cmd_wdata[127:0];

        state_words_enb = 1'b0;
        state_words_web = 1'b0;
        state_words_addrb = cmd_addr[9:0];
        state_words_dinb = cmd_wdata[63:0];

        axon_words_enb = 1'b0;
        axon_words_web = 1'b0;
        axon_words_addrb = cmd_addr[11:0];
        axon_words_dinb = cmd_wdata[63:0];

        synapse_words_enb = 1'b0;
        synapse_words_web = 1'b0;
        synapse_words_addrb = cmd_addr;
        synapse_words_dinb = cmd_wdata[63:0];

        route_desc_words_enb = 1'b0;
        route_desc_words_web = 1'b0;
        route_desc_words_addrb = cmd_addr[9:0];
        route_desc_words_dinb = cmd_wdata[31:0];

        route_words_enb = 1'b0;
        route_words_web = 1'b0;
        route_words_addrb = cmd_addr[11:0];
        route_words_dinb = cmd_wdata[31:0];

        input_events_enb = 1'b0;
        input_events_web = 1'b0;
        input_events_addrb = cmd_addr[11:0];
        input_events_dinb = cmd_wdata[31:0];

        trace_words_enb = 1'b0;
        trace_words_web = 1'b0;
        trace_words_addrb = cmd_addr[9:0];
        trace_words_dinb = cmd_wdata;

        packet_words_enb = 1'b0;
        packet_words_web = 1'b0;
        packet_words_addrb = cmd_addr[11:0];
        packet_words_dinb = cmd_wdata[63:0];

        if (state == ST_ISSUE) begin
            case (cmd_bank)
                4'd0: begin
                    config_words_enb = 1'b1;
                    config_words_web = cmd_write;
                end
                4'd1: begin
                    state_words_enb = 1'b1;
                    state_words_web = cmd_write;
                end
                4'd2: begin
                    axon_words_enb = 1'b1;
                    axon_words_web = cmd_write;
                end
                4'd3: begin
                    synapse_words_enb = 1'b1;
                    synapse_words_web = cmd_write;
                end
                4'd4: begin
                    route_desc_words_enb = 1'b1;
                    route_desc_words_web = cmd_write;
                end
                4'd5: begin
                    route_words_enb = 1'b1;
                    route_words_web = cmd_write;
                end
                4'd6: begin
                    input_events_enb = 1'b1;
                    input_events_web = cmd_write;
                end
                4'd7: begin
                    trace_words_enb = 1'b1;
                    trace_words_web = cmd_write;
                end
                4'd8: begin
                    packet_words_enb = 1'b1;
                    packet_words_web = cmd_write;
                end
                default: begin end
            endcase
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            state <= ST_IDLE;
            req_d <= 1'b0;
            cmd_write <= 1'b0;
            cmd_bank <= 4'd0;
            cmd_addr <= 15'd0;
            cmd_wdata <= 256'd0;
            ack <= 1'b0;
            rvalid <= 1'b0;
            error <= 1'b0;
            rdata <= 256'd0;
        end else begin
            req_d <= req;
            ack <= 1'b0;
            rvalid <= 1'b0;
            error <= 1'b0;

            case (state)
                ST_IDLE: begin
                    if (req && !req_d) begin
                        if (compute_busy || !addr_valid(bank, addr)) begin
                            ack <= 1'b1;
                            error <= 1'b1;
                        end else begin
                            cmd_write <= write;
                            cmd_bank <= bank;
                            cmd_addr <= addr;
                            cmd_wdata <= wdata;
                            state <= ST_ISSUE;
                        end
                    end
                end

                ST_ISSUE: begin
                    state <= ST_COMPLETE;
                end

                ST_COMPLETE: begin
                    ack <= 1'b1;
                    if (!cmd_write) begin
                        rvalid <= 1'b1;
                        rdata <= 256'd0;
                        case (cmd_bank)
                            4'd0: rdata[127:0] <= config_words_doutb;
                            4'd1: rdata[63:0] <= state_words_doutb;
                            4'd2: rdata[63:0] <= axon_words_doutb;
                            4'd3: rdata[63:0] <= synapse_words_doutb;
                            4'd4: rdata[31:0] <= route_desc_words_doutb;
                            4'd5: rdata[31:0] <= route_words_doutb;
                            4'd6: rdata[31:0] <= input_events_doutb;
                            4'd7: rdata <= trace_words_doutb;
                            4'd8: rdata[63:0] <= packet_words_doutb;
                            default: begin
                                rdata <= 256'd0;
                                error <= 1'b1;
                            end
                        endcase
                    end
                    state <= ST_IDLE;
                end

                default: begin
                    state <= ST_IDLE;
                    error <= 1'b1;
                end
            endcase
        end
    end
endmodule
