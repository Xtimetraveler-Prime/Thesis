`timescale 1ns/1ps

// Guarded true-dual-port bank used by the P04 directed validation fixture.
// Logical address widths remain identical to P03/HLS.  Requests outside the
// smaller physical allocation are disabled rather than aliased into low memory.
module p04_guarded_tdp_bank #(
    parameter integer DATA_WIDTH = 32,
    parameter integer LOGICAL_ADDR_WIDTH = 10,
    parameter integer DEPTH = 16
) (
    input  wire                          clk,
    input  wire [LOGICAL_ADDR_WIDTH-1:0] addra,
    input  wire                          ena,
    input  wire                          wea,
    input  wire [DATA_WIDTH-1:0]         dina,
    output wire [DATA_WIDTH-1:0]         douta,
    output wire                          invalid_a,
    input  wire [LOGICAL_ADDR_WIDTH-1:0] addrb,
    input  wire                          enb,
    input  wire                          web,
    input  wire [DATA_WIDTH-1:0]         dinb,
    output wire [DATA_WIDTH-1:0]         doutb,
    output wire                          invalid_b
);
    localparam integer PHYS_ADDR_WIDTH = (DEPTH <= 2) ? 1 : $clog2(DEPTH);
    localparam integer MEMORY_SIZE_BITS = DATA_WIDTH * DEPTH;

    wire valid_a = (addra < DEPTH);
    wire valid_b = (addrb < DEPTH);
    assign invalid_a = ena && !valid_a;
    assign invalid_b = enb && !valid_b;

    reg valid_a_d = 1'b0;
    reg valid_b_d = 1'b0;
    wire [DATA_WIDTH-1:0] raw_douta;
    wire [DATA_WIDTH-1:0] raw_doutb;
    wire unused_sbiterra;
    wire unused_sbiterrb;
    wire unused_dbiterra;
    wire unused_dbiterrb;

    always @(posedge clk) begin
        valid_a_d <= ena && valid_a;
        valid_b_d <= enb && valid_b;
    end

    assign douta = valid_a_d ? raw_douta : {DATA_WIDTH{1'b0}};
    assign doutb = valid_b_d ? raw_doutb : {DATA_WIDTH{1'b0}};

    xpm_memory_tdpram #(
        .ADDR_WIDTH_A(PHYS_ADDR_WIDTH),
        .ADDR_WIDTH_B(PHYS_ADDR_WIDTH),
        .AUTO_SLEEP_TIME(0),
        .BYTE_WRITE_WIDTH_A(DATA_WIDTH),
        .BYTE_WRITE_WIDTH_B(DATA_WIDTH),
        .CLOCKING_MODE("common_clock"),
        .ECC_MODE("no_ecc"),
        .MEMORY_INIT_FILE("none"),
        .MEMORY_INIT_PARAM("0"),
        .MEMORY_OPTIMIZATION("false"),
        .MEMORY_PRIMITIVE("block"),
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
        .addra(addra[PHYS_ADDR_WIDTH-1:0]),
        .addrb(addrb[PHYS_ADDR_WIDTH-1:0]),
        .dina(dina),
        .dinb(dinb),
        .douta(raw_douta),
        .doutb(raw_doutb),
        .ena(ena && valid_a),
        .enb(enb && valid_b),
        .wea(wea && valid_a),
        .web(web && valid_b),
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

// One resource-scaled P04 endpoint memory image.  Port A is the unchanged P03
// HLS interface.  Port B belongs to the host while idle; during a tick, only
// input_events (controller writes) and packet_words (controller reads) use it.
module p04_endpoint_memory_fabric #(
    parameter integer PHYS_COMPARTMENTS = 16,
    parameter integer PHYS_AXONS = 64,
    parameter integer PHYS_SYNAPSES = 256,
    parameter integer PHYS_ROUTES = 64,
    parameter integer PHYS_EVENTS = 64,
    parameter integer PHYS_PACKETS = 64
) (
    input  wire         clk,
    input  wire         resetn,
    input  wire         compute_busy,

    input  wire         host_req,
    input  wire         host_write,
    input  wire [3:0]   host_bank,
    input  wire [14:0]  host_addr,
    input  wire [255:0] host_wdata,
    output wire         host_busy,
    output reg          host_ack,
    output reg          host_rvalid,
    output reg          host_error,
    output reg  [255:0] host_rdata,

    input  wire         integration_packet_en,
    input  wire [11:0]  integration_packet_addr,
    output wire [63:0]  integration_packet_data,
    input  wire         integration_event_we,
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
                    host_addr_valid = (word_addr < PHYS_COMPARTMENTS);
                4'd2:
                    host_addr_valid = (word_addr < PHYS_AXONS);
                4'd3:
                    host_addr_valid = (word_addr < PHYS_SYNAPSES);
                4'd5:
                    host_addr_valid = (word_addr < PHYS_ROUTES);
                4'd6:
                    host_addr_valid = (word_addr < PHYS_EVENTS);
                4'd8:
                    host_addr_valid = (word_addr < PHYS_PACKETS);
                default:
                    host_addr_valid = 1'b0;
            endcase
        end
    endfunction

    reg config_enb, config_web;
    reg [9:0] config_addrb;
    reg [127:0] config_dinb;
    wire [127:0] config_doutb;
    reg state_enb, state_web;
    reg [9:0] state_addrb;
    reg [63:0] state_dinb;
    wire [63:0] state_doutb;
    reg axon_enb, axon_web;
    reg [11:0] axon_addrb;
    reg [63:0] axon_dinb;
    wire [63:0] axon_doutb;
    reg synapse_enb, synapse_web;
    reg [14:0] synapse_addrb;
    reg [63:0] synapse_dinb;
    wire [63:0] synapse_doutb;
    reg route_desc_enb, route_desc_web;
    reg [9:0] route_desc_addrb;
    reg [31:0] route_desc_dinb;
    wire [31:0] route_desc_doutb;
    reg route_enb, route_web;
    reg [11:0] route_addrb;
    reg [31:0] route_dinb;
    wire [31:0] route_doutb;
    reg event_enb, event_web;
    reg [11:0] event_addrb;
    reg [31:0] event_dinb;
    wire [31:0] event_doutb;
    reg trace_enb, trace_web;
    reg [9:0] trace_addrb;
    reg [255:0] trace_dinb;
    wire [255:0] trace_doutb;
    reg packet_enb, packet_web;
    reg [11:0] packet_addrb;
    reg [63:0] packet_dinb;
    wire [63:0] packet_doutb;

    wire invalid_config_a, invalid_state_a, invalid_axon_a, invalid_synapse_a;
    wire invalid_route_desc_a, invalid_route_a, invalid_event_a, invalid_trace_a;
    wire invalid_packet_a;
    wire invalid_config_b, invalid_state_b, invalid_axon_b, invalid_synapse_b;
    wire invalid_route_desc_b, invalid_route_b, invalid_event_b, invalid_trace_b;
    wire invalid_packet_b;

    assign hls_address_error = invalid_config_a || invalid_state_a || invalid_axon_a ||
        invalid_synapse_a || invalid_route_desc_a || invalid_route_a ||
        invalid_event_a || invalid_trace_a || invalid_packet_a;
    assign integration_address_error = compute_busy && (invalid_event_b || invalid_packet_b);
    assign integration_packet_data = packet_doutb;

    always @* begin
        config_enb = 1'b0; config_web = 1'b0; config_addrb = cmd_addr[9:0]; config_dinb = cmd_wdata[127:0];
        state_enb = 1'b0; state_web = 1'b0; state_addrb = cmd_addr[9:0]; state_dinb = cmd_wdata[63:0];
        axon_enb = 1'b0; axon_web = 1'b0; axon_addrb = cmd_addr[11:0]; axon_dinb = cmd_wdata[63:0];
        synapse_enb = 1'b0; synapse_web = 1'b0; synapse_addrb = cmd_addr; synapse_dinb = cmd_wdata[63:0];
        route_desc_enb = 1'b0; route_desc_web = 1'b0; route_desc_addrb = cmd_addr[9:0]; route_desc_dinb = cmd_wdata[31:0];
        route_enb = 1'b0; route_web = 1'b0; route_addrb = cmd_addr[11:0]; route_dinb = cmd_wdata[31:0];
        event_enb = 1'b0; event_web = 1'b0; event_addrb = cmd_addr[11:0]; event_dinb = cmd_wdata[31:0];
        trace_enb = 1'b0; trace_web = 1'b0; trace_addrb = cmd_addr[9:0]; trace_dinb = cmd_wdata;
        packet_enb = 1'b0; packet_web = 1'b0; packet_addrb = cmd_addr[11:0]; packet_dinb = cmd_wdata[63:0];

        if (compute_busy) begin
            event_enb = integration_event_we;
            event_web = integration_event_we;
            event_addrb = integration_event_addr;
            event_dinb = integration_event_data;
            packet_enb = integration_packet_en;
            packet_web = 1'b0;
            packet_addrb = integration_packet_addr;
        end else if (host_state == HOST_ISSUE) begin
            case (cmd_bank)
                4'd0: begin config_enb = 1'b1; config_web = cmd_write; end
                4'd1: begin state_enb = 1'b1; state_web = cmd_write; end
                4'd2: begin axon_enb = 1'b1; axon_web = cmd_write; end
                4'd3: begin synapse_enb = 1'b1; synapse_web = cmd_write; end
                4'd4: begin route_desc_enb = 1'b1; route_desc_web = cmd_write; end
                4'd5: begin route_enb = 1'b1; route_web = cmd_write; end
                4'd6: begin event_enb = 1'b1; event_web = cmd_write; end
                4'd7: begin trace_enb = 1'b1; trace_web = cmd_write; end
                4'd8: begin packet_enb = 1'b1; packet_web = cmd_write; end
                default: begin end
            endcase
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            host_state <= HOST_IDLE;
            host_req_d <= 1'b0;
            cmd_write <= 1'b0;
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
                        if (compute_busy || !host_addr_valid(host_bank, host_addr)) begin
                            host_ack <= 1'b1;
                            host_error <= 1'b1;
                        end else begin
                            cmd_write <= host_write;
                            cmd_bank <= host_bank;
                            cmd_addr <= host_addr;
                            cmd_wdata <= host_wdata;
                            host_state <= HOST_ISSUE;
                        end
                    end
                end
                HOST_ISSUE: begin
                    host_state <= HOST_COMPLETE;
                end
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
                            4'd6: host_rdata[31:0] <= event_doutb;
                            4'd7: host_rdata <= trace_doutb;
                            4'd8: host_rdata[63:0] <= packet_doutb;
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

    p04_guarded_tdp_bank #(.DATA_WIDTH(128), .LOGICAL_ADDR_WIDTH(10), .DEPTH(PHYS_COMPARTMENTS)) config_bank (
        .clk(clk), .addra(config_words_addra), .ena(config_words_ena), .wea(1'b0), .dina(128'd0), .douta(config_words_douta), .invalid_a(invalid_config_a),
        .addrb(config_addrb), .enb(config_enb), .web(config_web), .dinb(config_dinb), .doutb(config_doutb), .invalid_b(invalid_config_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(64), .LOGICAL_ADDR_WIDTH(10), .DEPTH(PHYS_COMPARTMENTS)) state_bank (
        .clk(clk), .addra(state_words_addra), .ena(state_words_ena), .wea(state_words_wea), .dina(state_words_dina), .douta(state_words_douta), .invalid_a(invalid_state_a),
        .addrb(state_addrb), .enb(state_enb), .web(state_web), .dinb(state_dinb), .doutb(state_doutb), .invalid_b(invalid_state_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(64), .LOGICAL_ADDR_WIDTH(12), .DEPTH(PHYS_AXONS)) axon_bank (
        .clk(clk), .addra(axon_words_addra), .ena(axon_words_ena), .wea(1'b0), .dina(64'd0), .douta(axon_words_douta), .invalid_a(invalid_axon_a),
        .addrb(axon_addrb), .enb(axon_enb), .web(axon_web), .dinb(axon_dinb), .doutb(axon_doutb), .invalid_b(invalid_axon_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(64), .LOGICAL_ADDR_WIDTH(15), .DEPTH(PHYS_SYNAPSES)) synapse_bank (
        .clk(clk), .addra(synapse_words_addra), .ena(synapse_words_ena), .wea(1'b0), .dina(64'd0), .douta(synapse_words_douta), .invalid_a(invalid_synapse_a),
        .addrb(synapse_addrb), .enb(synapse_enb), .web(synapse_web), .dinb(synapse_dinb), .doutb(synapse_doutb), .invalid_b(invalid_synapse_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(32), .LOGICAL_ADDR_WIDTH(10), .DEPTH(PHYS_COMPARTMENTS)) route_desc_bank (
        .clk(clk), .addra(route_desc_words_addra), .ena(route_desc_words_ena), .wea(1'b0), .dina(32'd0), .douta(route_desc_words_douta), .invalid_a(invalid_route_desc_a),
        .addrb(route_desc_addrb), .enb(route_desc_enb), .web(route_desc_web), .dinb(route_desc_dinb), .doutb(route_desc_doutb), .invalid_b(invalid_route_desc_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(32), .LOGICAL_ADDR_WIDTH(12), .DEPTH(PHYS_ROUTES)) route_bank (
        .clk(clk), .addra(route_words_addra), .ena(route_words_ena), .wea(1'b0), .dina(32'd0), .douta(route_words_douta), .invalid_a(invalid_route_a),
        .addrb(route_addrb), .enb(route_enb), .web(route_web), .dinb(route_dinb), .doutb(route_doutb), .invalid_b(invalid_route_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(32), .LOGICAL_ADDR_WIDTH(12), .DEPTH(PHYS_EVENTS)) event_bank (
        .clk(clk), .addra(input_events_addra), .ena(input_events_ena), .wea(1'b0), .dina(32'd0), .douta(input_events_douta), .invalid_a(invalid_event_a),
        .addrb(event_addrb), .enb(event_enb), .web(event_web), .dinb(event_dinb), .doutb(event_doutb), .invalid_b(invalid_event_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(256), .LOGICAL_ADDR_WIDTH(10), .DEPTH(PHYS_COMPARTMENTS)) trace_bank (
        .clk(clk), .addra(trace_words_addra), .ena(trace_words_ena), .wea(trace_words_wea), .dina(trace_words_dina), .douta(), .invalid_a(invalid_trace_a),
        .addrb(trace_addrb), .enb(trace_enb), .web(trace_web), .dinb(trace_dinb), .doutb(trace_doutb), .invalid_b(invalid_trace_b));
    p04_guarded_tdp_bank #(.DATA_WIDTH(64), .LOGICAL_ADDR_WIDTH(12), .DEPTH(PHYS_PACKETS)) packet_bank (
        .clk(clk), .addra(packet_words_addra), .ena(packet_words_ena), .wea(packet_words_wea), .dina(packet_words_dina), .douta(), .invalid_a(invalid_packet_a),
        .addrb(packet_addrb), .enb(packet_enb), .web(packet_web), .dinb(packet_dinb), .doutb(packet_doutb), .invalid_b(invalid_packet_b));
endmodule
