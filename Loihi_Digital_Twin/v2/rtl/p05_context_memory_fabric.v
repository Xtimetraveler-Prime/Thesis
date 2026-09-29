`timescale 1ns/1ps

// Full logical-core context bank for P05 virtualization.
//
// A context slot is a physical storage location, not a logical core ID.  The
// controller supplies the active slot while packets continue to carry logical
// source/destination IDs.  All local address widths/depths remain the accepted
// P03 logical/HLS widths; there is no P04-style reduced physical address space.
module p05_context_tdp_bank #(
    parameter integer DATA_WIDTH = 32,
    parameter integer LOCAL_ADDR_WIDTH = 10,
    parameter integer LOCAL_DEPTH = 1024,
    parameter integer CONTEXTS = 3,
    parameter MEMORY_PRIMITIVE = "ultra"
) (
    input  wire                         clk,

    input  wire [$clog2(CONTEXTS)-1:0] context_a,
    input  wire [LOCAL_ADDR_WIDTH-1:0]  addr_a,
    input  wire                         en_a,
    input  wire                         we_a,
    input  wire [DATA_WIDTH-1:0]        din_a,
    output wire [DATA_WIDTH-1:0]        dout_a,
    output wire                         invalid_a,

    input  wire [$clog2(CONTEXTS)-1:0] context_b,
    input  wire [LOCAL_ADDR_WIDTH-1:0]  addr_b,
    input  wire                         en_b,
    input  wire                         we_b,
    input  wire [DATA_WIDTH-1:0]        din_b,
    output wire [DATA_WIDTH-1:0]        dout_b,
    output wire                         invalid_b
);
    localparam integer TOTAL_DEPTH = CONTEXTS * LOCAL_DEPTH;
    localparam integer GLOBAL_ADDR_WIDTH = (TOTAL_DEPTH <= 2) ? 1 : $clog2(TOTAL_DEPTH);
    localparam integer MEMORY_SIZE_BITS = DATA_WIDTH * TOTAL_DEPTH;

    wire context_a_valid = (context_a < CONTEXTS);
    wire context_b_valid = (context_b < CONTEXTS);
    wire local_a_valid = (addr_a < LOCAL_DEPTH);
    wire local_b_valid = (addr_b < LOCAL_DEPTH);
    wire valid_a = context_a_valid && local_a_valid;
    wire valid_b = context_b_valid && local_b_valid;

    wire [GLOBAL_ADDR_WIDTH-1:0] global_addr_a =
        (context_a * LOCAL_DEPTH) + addr_a;
    wire [GLOBAL_ADDR_WIDTH-1:0] global_addr_b =
        (context_b * LOCAL_DEPTH) + addr_b;

    assign invalid_a = en_a && !valid_a;
    assign invalid_b = en_b && !valid_b;

    reg valid_a_d = 1'b0;
    reg valid_b_d = 1'b0;
    wire [DATA_WIDTH-1:0] raw_dout_a;
    wire [DATA_WIDTH-1:0] raw_dout_b;
    wire unused_sbiterra;
    wire unused_sbiterrb;
    wire unused_dbiterra;
    wire unused_dbiterrb;

    always @(posedge clk) begin
        valid_a_d <= en_a && valid_a;
        valid_b_d <= en_b && valid_b;
    end

    assign dout_a = valid_a_d ? raw_dout_a : {DATA_WIDTH{1'b0}};
    assign dout_b = valid_b_d ? raw_dout_b : {DATA_WIDTH{1'b0}};

    xpm_memory_tdpram #(
        .ADDR_WIDTH_A(GLOBAL_ADDR_WIDTH),
        .ADDR_WIDTH_B(GLOBAL_ADDR_WIDTH),
        .AUTO_SLEEP_TIME(0),
        .BYTE_WRITE_WIDTH_A(DATA_WIDTH),
        .BYTE_WRITE_WIDTH_B(DATA_WIDTH),
        .CLOCKING_MODE("common_clock"),
        .ECC_MODE("no_ecc"),
        .MEMORY_INIT_FILE("none"),
        .MEMORY_INIT_PARAM("0"),
        .MEMORY_OPTIMIZATION("false"),
        .MEMORY_PRIMITIVE(MEMORY_PRIMITIVE),
        .MEMORY_SIZE(MEMORY_SIZE_BITS),
        .MESSAGE_CONTROL(0),
        .READ_DATA_WIDTH_A(DATA_WIDTH),
        .READ_DATA_WIDTH_B(DATA_WIDTH),
        .READ_LATENCY_A(1),
        .READ_LATENCY_B(1),
        .READ_RESET_VALUE_A("0"),
        .READ_RESET_VALUE_B("0"),
        .USE_EMBEDDED_CONSTRAINT(0),
        .USE_MEM_INIT(0),
        .WAKEUP_TIME("disable_sleep"),
        .WRITE_DATA_WIDTH_A(DATA_WIDTH),
        .WRITE_DATA_WIDTH_B(DATA_WIDTH),
        .WRITE_MODE_A("no_change"),
        .WRITE_MODE_B("no_change")
    ) memory (
        .clka(clk),
        .clkb(clk),
        .addra(global_addr_a),
        .addrb(global_addr_b),
        .dina(din_a),
        .dinb(din_b),
        .douta(raw_dout_a),
        .doutb(raw_dout_b),
        .ena(en_a && valid_a),
        .enb(en_b && valid_b),
        .wea(we_a && valid_a),
        .web(we_b && valid_b),
        .regcea(1'b1),
        .regceb(1'b1),
        .rsta(1'b0),
        .rstb(1'b0),
        .sleep(1'b0),
        .injectsbiterra(1'b0),
        .injectdbiterra(1'b0),
        .injectsbiterrb(1'b0),
        .injectdbiterrb(1'b0),
        .sbiterra(unused_sbiterra),
        .sbiterrb(unused_sbiterrb),
        .dbiterra(unused_dbiterra),
        .dbiterrb(unused_dbiterrb)
    );
endmodule


// Three retained full logical-core contexts serviced by one P03-compatible HLS
// engine.  Port A is selected by active_context_slot. Port B is host/debug while
// idle and becomes the packet-read / next-event-write integration side while
// compute_busy is asserted.
//
// Input events are double buffered. HLS reads event_read_bank; routed packets
// are written to the opposite bank. The controller flips event_read_bank only
// after the logical-core barrier advances the algorithmic timestep.
module p05_context_memory_fabric #(
    parameter integer CONTEXTS = 3
) (
    input  wire         clk,
    input  wire         resetn,
    input  wire         compute_busy,
    input  wire [$clog2(CONTEXTS)-1:0] active_context_slot,
    input  wire         event_read_bank,

    input  wire         host_req,
    input  wire         host_write,
    input  wire [$clog2(CONTEXTS)-1:0] host_context_slot,
    input  wire [3:0]   host_bank,
    input  wire [14:0]  host_addr,
    input  wire [255:0] host_wdata,
    output wire         host_busy,
    output reg          host_ack,
    output reg          host_rvalid,
    output reg          host_error,
    output reg  [255:0] host_rdata,

    input  wire         integration_packet_en,
    input  wire [$clog2(CONTEXTS)-1:0] integration_packet_context,
    input  wire [11:0]  integration_packet_addr,
    output wire [63:0]  integration_packet_data,
    input  wire         integration_event_we,
    input  wire [$clog2(CONTEXTS)-1:0] integration_event_context,
    input  wire [11:0]  integration_event_addr,
    input  wire [31:0]  integration_event_data,

    input  wire [9:0]   config_words_addra,
    input  wire         config_words_ena,
    output wire [127:0] config_words_douta,
    input  wire [9:0]   state_words_addra,
    input  wire         state_words_ena,
    input  wire         state_words_wea,
    input  wire [63:0]  state_words_dina,
    output wire [63:0]  state_words_douta,
    input  wire [11:0]  axon_words_addra,
    input  wire         axon_words_ena,
    output wire [63:0]  axon_words_douta,
    input  wire [14:0]  synapse_words_addra,
    input  wire         synapse_words_ena,
    output wire [63:0]  synapse_words_douta,
    input  wire [9:0]   route_desc_words_addra,
    input  wire         route_desc_words_ena,
    output wire [31:0]  route_desc_words_douta,
    input  wire [11:0]  route_words_addra,
    input  wire         route_words_ena,
    output wire [31:0]  route_words_douta,
    input  wire [11:0]  input_events_addra,
    input  wire         input_events_ena,
    output wire [31:0]  input_events_douta,
    input  wire [9:0]   trace_words_addra,
    input  wire         trace_words_ena,
    input  wire         trace_words_wea,
    input  wire [255:0] trace_words_dina,
    input  wire [11:0]  packet_words_addra,
    input  wire         packet_words_ena,
    input  wire         packet_words_wea,
    input  wire [63:0]  packet_words_dina,

    output wire         hls_address_error,
    output wire         integration_address_error
);
    localparam [1:0] HOST_IDLE = 2'd0;
    localparam [1:0] HOST_ISSUE = 2'd1;
    localparam [1:0] HOST_COMPLETE = 2'd2;

    reg [1:0] host_state;
    reg host_req_d;
    reg cmd_write;
    reg [$clog2(CONTEXTS)-1:0] cmd_context;
    reg [3:0] cmd_bank;
    reg [14:0] cmd_addr;
    reg [255:0] cmd_wdata;

    assign host_busy = (host_state != HOST_IDLE) || host_req;

    function host_addr_valid;
        input [3:0] bank_id;
        input [14:0] word_addr;
        begin
            case (bank_id)
                4'd0, 4'd1, 4'd4, 4'd7:
                    host_addr_valid = (word_addr < 1024);
                4'd2:
                    host_addr_valid = (word_addr < 4096);
                4'd3:
                    host_addr_valid = (word_addr < 32768);
                4'd5, 4'd6, 4'd8, 4'd9:
                    host_addr_valid = (word_addr < 4096);
                default:
                    host_addr_valid = 1'b0;
            endcase
        end
    endfunction

    reg config_enb, config_web;
    reg [$clog2(CONTEXTS)-1:0] config_contextb;
    reg [9:0] config_addrb;
    reg [127:0] config_dinb;
    wire [127:0] config_doutb;

    reg state_enb, state_web;
    reg [$clog2(CONTEXTS)-1:0] state_contextb;
    reg [9:0] state_addrb;
    reg [63:0] state_dinb;
    wire [63:0] state_doutb;

    reg axon_enb, axon_web;
    reg [$clog2(CONTEXTS)-1:0] axon_contextb;
    reg [11:0] axon_addrb;
    reg [63:0] axon_dinb;
    wire [63:0] axon_doutb;

    reg synapse_enb, synapse_web;
    reg [$clog2(CONTEXTS)-1:0] synapse_contextb;
    reg [14:0] synapse_addrb;
    reg [63:0] synapse_dinb;
    wire [63:0] synapse_doutb;

    reg route_desc_enb, route_desc_web;
    reg [$clog2(CONTEXTS)-1:0] route_desc_contextb;
    reg [9:0] route_desc_addrb;
    reg [31:0] route_desc_dinb;
    wire [31:0] route_desc_doutb;

    reg route_enb, route_web;
    reg [$clog2(CONTEXTS)-1:0] route_contextb;
    reg [11:0] route_addrb;
    reg [31:0] route_dinb;
    wire [31:0] route_doutb;

    reg event0_enb, event0_web;
    reg [$clog2(CONTEXTS)-1:0] event0_contextb;
    reg [11:0] event0_addrb;
    reg [31:0] event0_dinb;
    wire [31:0] event0_doutb;

    reg event1_enb, event1_web;
    reg [$clog2(CONTEXTS)-1:0] event1_contextb;
    reg [11:0] event1_addrb;
    reg [31:0] event1_dinb;
    wire [31:0] event1_doutb;

    reg trace_enb, trace_web;
    reg [$clog2(CONTEXTS)-1:0] trace_contextb;
    reg [9:0] trace_addrb;
    reg [255:0] trace_dinb;
    wire [255:0] trace_doutb;

    reg packet_enb, packet_web;
    reg [$clog2(CONTEXTS)-1:0] packet_contextb;
    reg [11:0] packet_addrb;
    reg [63:0] packet_dinb;
    wire [63:0] packet_doutb;

    wire invalid_config_a, invalid_state_a, invalid_axon_a, invalid_synapse_a;
    wire invalid_route_desc_a, invalid_route_a, invalid_event0_a, invalid_event1_a;
    wire invalid_trace_a, invalid_packet_a;
    wire invalid_config_b, invalid_state_b, invalid_axon_b, invalid_synapse_b;
    wire invalid_route_desc_b, invalid_route_b, invalid_event0_b, invalid_event1_b;
    wire invalid_trace_b, invalid_packet_b;

    wire [31:0] event0_douta;
    wire [31:0] event1_douta;
    wire event0_hls_en = input_events_ena && !event_read_bank;
    wire event1_hls_en = input_events_ena && event_read_bank;
    assign input_events_douta = event_read_bank ? event1_douta : event0_douta;

    assign hls_address_error = invalid_config_a || invalid_state_a || invalid_axon_a ||
        invalid_synapse_a || invalid_route_desc_a || invalid_route_a ||
        invalid_event0_a || invalid_event1_a || invalid_trace_a || invalid_packet_a;
    assign integration_address_error = compute_busy &&
        (invalid_event0_b || invalid_event1_b || invalid_packet_b);
    assign integration_packet_data = packet_doutb;

    always @* begin
        config_enb = 1'b0; config_web = 1'b0; config_contextb = cmd_context; config_addrb = cmd_addr[9:0]; config_dinb = cmd_wdata[127:0];
        state_enb = 1'b0; state_web = 1'b0; state_contextb = cmd_context; state_addrb = cmd_addr[9:0]; state_dinb = cmd_wdata[63:0];
        axon_enb = 1'b0; axon_web = 1'b0; axon_contextb = cmd_context; axon_addrb = cmd_addr[11:0]; axon_dinb = cmd_wdata[63:0];
        synapse_enb = 1'b0; synapse_web = 1'b0; synapse_contextb = cmd_context; synapse_addrb = cmd_addr; synapse_dinb = cmd_wdata[63:0];
        route_desc_enb = 1'b0; route_desc_web = 1'b0; route_desc_contextb = cmd_context; route_desc_addrb = cmd_addr[9:0]; route_desc_dinb = cmd_wdata[31:0];
        route_enb = 1'b0; route_web = 1'b0; route_contextb = cmd_context; route_addrb = cmd_addr[11:0]; route_dinb = cmd_wdata[31:0];
        event0_enb = 1'b0; event0_web = 1'b0; event0_contextb = cmd_context; event0_addrb = cmd_addr[11:0]; event0_dinb = cmd_wdata[31:0];
        event1_enb = 1'b0; event1_web = 1'b0; event1_contextb = cmd_context; event1_addrb = cmd_addr[11:0]; event1_dinb = cmd_wdata[31:0];
        trace_enb = 1'b0; trace_web = 1'b0; trace_contextb = cmd_context; trace_addrb = cmd_addr[9:0]; trace_dinb = cmd_wdata;
        packet_enb = 1'b0; packet_web = 1'b0; packet_contextb = cmd_context; packet_addrb = cmd_addr[11:0]; packet_dinb = cmd_wdata[63:0];

        if (compute_busy) begin
            packet_enb = integration_packet_en;
            packet_web = 1'b0;
            packet_contextb = integration_packet_context;
            packet_addrb = integration_packet_addr;

            if (event_read_bank) begin
                event0_enb = integration_event_we;
                event0_web = integration_event_we;
                event0_contextb = integration_event_context;
                event0_addrb = integration_event_addr;
                event0_dinb = integration_event_data;
            end else begin
                event1_enb = integration_event_we;
                event1_web = integration_event_we;
                event1_contextb = integration_event_context;
                event1_addrb = integration_event_addr;
                event1_dinb = integration_event_data;
            end
        end else if (host_state == HOST_ISSUE) begin
            case (cmd_bank)
                4'd0: begin config_enb = 1'b1; config_web = cmd_write; end
                4'd1: begin state_enb = 1'b1; state_web = cmd_write; end
                4'd2: begin axon_enb = 1'b1; axon_web = cmd_write; end
                4'd3: begin synapse_enb = 1'b1; synapse_web = cmd_write; end
                4'd4: begin route_desc_enb = 1'b1; route_desc_web = cmd_write; end
                4'd5: begin route_enb = 1'b1; route_web = cmd_write; end
                4'd6: begin event0_enb = 1'b1; event0_web = cmd_write; end
                4'd7: begin trace_enb = 1'b1; trace_web = cmd_write; end
                4'd8: begin packet_enb = 1'b1; packet_web = cmd_write; end
                4'd9: begin event1_enb = 1'b1; event1_web = cmd_write; end
                default: begin end
            endcase
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            host_state <= HOST_IDLE;
            host_req_d <= 1'b0;
            cmd_write <= 1'b0;
            cmd_context <= 0;
            cmd_bank <= 4'd0;
            cmd_addr <= 15'd0;
            cmd_wdata <= 256'd0;
            host_ack <= 1'b0;
            host_rvalid <= 1'b0;
            host_error <= 1'b0;
            host_rdata <= 256'd0;
        end else begin
            host_req_d <= host_req;
            case (host_state)
                HOST_IDLE: begin
                    if (host_req && !host_req_d) begin
                        host_ack <= 1'b0;
                        host_rvalid <= 1'b0;
                        host_error <= 1'b0;
                        if (compute_busy || host_context_slot >= CONTEXTS ||
                            !host_addr_valid(host_bank, host_addr)) begin
                            host_ack <= 1'b1;
                            host_error <= 1'b1;
                        end else begin
                            cmd_write <= host_write;
                            cmd_context <= host_context_slot;
                            cmd_bank <= host_bank;
                            cmd_addr <= host_addr;
                            cmd_wdata <= host_wdata;
                            host_state <= HOST_ISSUE;
                        end
                    end
                end
                HOST_ISSUE: host_state <= HOST_COMPLETE;
                HOST_COMPLETE: begin
                    host_ack <= 1'b1;
                    host_rvalid <= !cmd_write;
                    host_error <= 1'b0;
                    if (!cmd_write) begin
                        host_rdata <= 256'd0;
                        case (cmd_bank)
                            4'd0: host_rdata[127:0] <= config_doutb;
                            4'd1: host_rdata[63:0] <= state_doutb;
                            4'd2: host_rdata[63:0] <= axon_doutb;
                            4'd3: host_rdata[63:0] <= synapse_doutb;
                            4'd4: host_rdata[31:0] <= route_desc_doutb;
                            4'd5: host_rdata[31:0] <= route_doutb;
                            4'd6: host_rdata[31:0] <= event0_doutb;
                            4'd7: host_rdata <= trace_doutb;
                            4'd8: host_rdata[63:0] <= packet_doutb;
                            4'd9: host_rdata[31:0] <= event1_doutb;
                            default: begin host_error <= 1'b1; host_rdata <= 256'd0; end
                        endcase
                    end
                    host_state <= HOST_IDLE;
                end
                default: begin
                    host_state <= HOST_IDLE;
                    host_ack <= 1'b1;
                    host_rvalid <= 1'b0;
                    host_error <= 1'b1;
                end
            endcase
        end
    end

    p05_context_tdp_bank #(.DATA_WIDTH(128), .LOCAL_ADDR_WIDTH(10), .LOCAL_DEPTH(1024), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) config_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(config_words_addra), .en_a(config_words_ena), .we_a(1'b0), .din_a(128'd0), .dout_a(config_words_douta), .invalid_a(invalid_config_a),
        .context_b(config_contextb), .addr_b(config_addrb), .en_b(config_enb), .we_b(config_web), .din_b(config_dinb), .dout_b(config_doutb), .invalid_b(invalid_config_b));
    p05_context_tdp_bank #(.DATA_WIDTH(64), .LOCAL_ADDR_WIDTH(10), .LOCAL_DEPTH(1024), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) state_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(state_words_addra), .en_a(state_words_ena), .we_a(state_words_wea), .din_a(state_words_dina), .dout_a(state_words_douta), .invalid_a(invalid_state_a),
        .context_b(state_contextb), .addr_b(state_addrb), .en_b(state_enb), .we_b(state_web), .din_b(state_dinb), .dout_b(state_doutb), .invalid_b(invalid_state_b));
    p05_context_tdp_bank #(.DATA_WIDTH(64), .LOCAL_ADDR_WIDTH(12), .LOCAL_DEPTH(4096), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) axon_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(axon_words_addra), .en_a(axon_words_ena), .we_a(1'b0), .din_a(64'd0), .dout_a(axon_words_douta), .invalid_a(invalid_axon_a),
        .context_b(axon_contextb), .addr_b(axon_addrb), .en_b(axon_enb), .we_b(axon_web), .din_b(axon_dinb), .dout_b(axon_doutb), .invalid_b(invalid_axon_b));
    p05_context_tdp_bank #(.DATA_WIDTH(64), .LOCAL_ADDR_WIDTH(15), .LOCAL_DEPTH(32768), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) synapse_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(synapse_words_addra), .en_a(synapse_words_ena), .we_a(1'b0), .din_a(64'd0), .dout_a(synapse_words_douta), .invalid_a(invalid_synapse_a),
        .context_b(synapse_contextb), .addr_b(synapse_addrb), .en_b(synapse_enb), .we_b(synapse_web), .din_b(synapse_dinb), .dout_b(synapse_doutb), .invalid_b(invalid_synapse_b));
    p05_context_tdp_bank #(.DATA_WIDTH(32), .LOCAL_ADDR_WIDTH(10), .LOCAL_DEPTH(1024), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) route_desc_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(route_desc_words_addra), .en_a(route_desc_words_ena), .we_a(1'b0), .din_a(32'd0), .dout_a(route_desc_words_douta), .invalid_a(invalid_route_desc_a),
        .context_b(route_desc_contextb), .addr_b(route_desc_addrb), .en_b(route_desc_enb), .we_b(route_desc_web), .din_b(route_desc_dinb), .dout_b(route_desc_doutb), .invalid_b(invalid_route_desc_b));
    p05_context_tdp_bank #(.DATA_WIDTH(32), .LOCAL_ADDR_WIDTH(12), .LOCAL_DEPTH(4096), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) route_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(route_words_addra), .en_a(route_words_ena), .we_a(1'b0), .din_a(32'd0), .dout_a(route_words_douta), .invalid_a(invalid_route_a),
        .context_b(route_contextb), .addr_b(route_addrb), .en_b(route_enb), .we_b(route_web), .din_b(route_dinb), .dout_b(route_doutb), .invalid_b(invalid_route_b));
    p05_context_tdp_bank #(.DATA_WIDTH(32), .LOCAL_ADDR_WIDTH(12), .LOCAL_DEPTH(4096), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) event0_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(input_events_addra), .en_a(event0_hls_en), .we_a(1'b0), .din_a(32'd0), .dout_a(event0_douta), .invalid_a(invalid_event0_a),
        .context_b(event0_contextb), .addr_b(event0_addrb), .en_b(event0_enb), .we_b(event0_web), .din_b(event0_dinb), .dout_b(event0_doutb), .invalid_b(invalid_event0_b));
    p05_context_tdp_bank #(.DATA_WIDTH(32), .LOCAL_ADDR_WIDTH(12), .LOCAL_DEPTH(4096), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) event1_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(input_events_addra), .en_a(event1_hls_en), .we_a(1'b0), .din_a(32'd0), .dout_a(event1_douta), .invalid_a(invalid_event1_a),
        .context_b(event1_contextb), .addr_b(event1_addrb), .en_b(event1_enb), .we_b(event1_web), .din_b(event1_dinb), .dout_b(event1_doutb), .invalid_b(invalid_event1_b));
    p05_context_tdp_bank #(.DATA_WIDTH(256), .LOCAL_ADDR_WIDTH(10), .LOCAL_DEPTH(1024), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) trace_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(trace_words_addra), .en_a(trace_words_ena), .we_a(trace_words_wea), .din_a(trace_words_dina), .dout_a(), .invalid_a(invalid_trace_a),
        .context_b(trace_contextb), .addr_b(trace_addrb), .en_b(trace_enb), .we_b(trace_web), .din_b(trace_dinb), .dout_b(trace_doutb), .invalid_b(invalid_trace_b));
    p05_context_tdp_bank #(.DATA_WIDTH(64), .LOCAL_ADDR_WIDTH(12), .LOCAL_DEPTH(4096), .CONTEXTS(CONTEXTS), .MEMORY_PRIMITIVE("ultra")) packet_bank (
        .clk(clk), .context_a(active_context_slot), .addr_a(packet_words_addra), .en_a(packet_words_ena), .we_a(packet_words_wea), .din_a(packet_words_dina), .dout_a(), .invalid_a(invalid_packet_a),
        .context_b(packet_contextb), .addr_b(packet_addrb), .en_b(packet_enb), .we_b(packet_web), .din_b(packet_dinb), .dout_b(packet_doutb), .invalid_b(invalid_packet_b));
endmodule
