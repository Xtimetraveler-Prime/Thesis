`timescale 1ns/1ps

// Fixed-capacity P03 external-memory fabric.
//
// Port A of each bank is the HLS compute port. Port B is owned by the unified
// p03_memory_host_bridge. The banks are XPM true-dual-port memories rather than
// Block Memory Generator IP Integrator instances so depth/width are explicit
// RTL parameters and cannot silently fall back to an IP default.

(* keep_hierarchy = "yes" *)
module p03_tdp_xpm_bank #(
    parameter integer DATA_WIDTH = 32,
    parameter integer ADDR_WIDTH = 10,
    parameter integer DEPTH = 1024
) (
    input  wire                  clk,

    input  wire [ADDR_WIDTH-1:0] addra,
    input  wire                  ena,
    input  wire                  wea,
    input  wire [DATA_WIDTH-1:0] dina,
    output wire [DATA_WIDTH-1:0] douta,

    input  wire [ADDR_WIDTH-1:0] addrb,
    input  wire                  enb,
    input  wire                  web,
    input  wire [DATA_WIDTH-1:0] dinb,
    output wire [DATA_WIDTH-1:0] doutb
);
    localparam integer MEMORY_SIZE_BITS = DATA_WIDTH * DEPTH;

    wire unused_sbiterra;
    wire unused_sbiterrb;
    wire unused_dbiterra;
    wire unused_dbiterrb;

    xpm_memory_tdpram #(
        .ADDR_WIDTH_A(ADDR_WIDTH),
        .ADDR_WIDTH_B(ADDR_WIDTH),
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
    ) xpm_memory_tdpram_inst (
        .clka(clk),
        .clkb(clk),
        .addra(addra),
        .addrb(addrb),
        .dina(dina),
        .dinb(dinb),
        .douta(douta),
        .doutb(doutb),
        .ena(ena),
        .enb(enb),
        .wea(wea),
        .web(web),
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

(* keep_hierarchy = "yes" *)
module p03_memory_fabric (
    input  wire         clk,
    input  wire         resetn,
    input  wire         compute_busy,

    input  wire         host_req,
    input  wire         host_write,
    input  wire [3:0]   host_bank,
    input  wire [14:0]  host_addr,
    input  wire [255:0] host_wdata,
    output wire         host_busy,
    output wire         host_ack,
    output wire         host_rvalid,
    output wire         host_error,
    output wire [255:0] host_rdata,

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
    input  wire [63:0]  packet_words_dina
);
    wire config_words_enb;
    wire config_words_web;
    wire [9:0] config_words_addrb;
    wire [127:0] config_words_dinb;
    wire [127:0] config_words_doutb;

    wire state_words_enb;
    wire state_words_web;
    wire [9:0] state_words_addrb;
    wire [63:0] state_words_dinb;
    wire [63:0] state_words_doutb;

    wire axon_words_enb;
    wire axon_words_web;
    wire [11:0] axon_words_addrb;
    wire [63:0] axon_words_dinb;
    wire [63:0] axon_words_doutb;

    wire synapse_words_enb;
    wire synapse_words_web;
    wire [14:0] synapse_words_addrb;
    wire [63:0] synapse_words_dinb;
    wire [63:0] synapse_words_doutb;

    wire route_desc_words_enb;
    wire route_desc_words_web;
    wire [9:0] route_desc_words_addrb;
    wire [31:0] route_desc_words_dinb;
    wire [31:0] route_desc_words_doutb;

    wire route_words_enb;
    wire route_words_web;
    wire [11:0] route_words_addrb;
    wire [31:0] route_words_dinb;
    wire [31:0] route_words_doutb;

    wire input_events_enb;
    wire input_events_web;
    wire [11:0] input_events_addrb;
    wire [31:0] input_events_dinb;
    wire [31:0] input_events_doutb;

    wire trace_words_enb;
    wire trace_words_web;
    wire [9:0] trace_words_addrb;
    wire [255:0] trace_words_dinb;
    wire [255:0] trace_words_doutb;
    wire [255:0] unused_trace_words_douta;

    wire packet_words_enb;
    wire packet_words_web;
    wire [11:0] packet_words_addrb;
    wire [63:0] packet_words_dinb;
    wire [63:0] packet_words_doutb;
    wire [63:0] unused_packet_words_douta;

    p03_memory_host_bridge host_bridge (
        .clk(clk),
        .resetn(resetn),
        .compute_busy(compute_busy),
        .req(host_req),
        .write(host_write),
        .bank(host_bank),
        .addr(host_addr),
        .wdata(host_wdata),
        .host_busy(host_busy),
        .ack(host_ack),
        .rvalid(host_rvalid),
        .error(host_error),
        .rdata(host_rdata),
        .config_words_enb(config_words_enb),
        .config_words_web(config_words_web),
        .config_words_addrb(config_words_addrb),
        .config_words_dinb(config_words_dinb),
        .config_words_doutb(config_words_doutb),
        .state_words_enb(state_words_enb),
        .state_words_web(state_words_web),
        .state_words_addrb(state_words_addrb),
        .state_words_dinb(state_words_dinb),
        .state_words_doutb(state_words_doutb),
        .axon_words_enb(axon_words_enb),
        .axon_words_web(axon_words_web),
        .axon_words_addrb(axon_words_addrb),
        .axon_words_dinb(axon_words_dinb),
        .axon_words_doutb(axon_words_doutb),
        .synapse_words_enb(synapse_words_enb),
        .synapse_words_web(synapse_words_web),
        .synapse_words_addrb(synapse_words_addrb),
        .synapse_words_dinb(synapse_words_dinb),
        .synapse_words_doutb(synapse_words_doutb),
        .route_desc_words_enb(route_desc_words_enb),
        .route_desc_words_web(route_desc_words_web),
        .route_desc_words_addrb(route_desc_words_addrb),
        .route_desc_words_dinb(route_desc_words_dinb),
        .route_desc_words_doutb(route_desc_words_doutb),
        .route_words_enb(route_words_enb),
        .route_words_web(route_words_web),
        .route_words_addrb(route_words_addrb),
        .route_words_dinb(route_words_dinb),
        .route_words_doutb(route_words_doutb),
        .input_events_enb(input_events_enb),
        .input_events_web(input_events_web),
        .input_events_addrb(input_events_addrb),
        .input_events_dinb(input_events_dinb),
        .input_events_doutb(input_events_doutb),
        .trace_words_enb(trace_words_enb),
        .trace_words_web(trace_words_web),
        .trace_words_addrb(trace_words_addrb),
        .trace_words_dinb(trace_words_dinb),
        .trace_words_doutb(trace_words_doutb),
        .packet_words_enb(packet_words_enb),
        .packet_words_web(packet_words_web),
        .packet_words_addrb(packet_words_addrb),
        .packet_words_dinb(packet_words_dinb),
        .packet_words_doutb(packet_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(128), .ADDR_WIDTH(10), .DEPTH(1024)) u_config_words (
        .clk(clk),
        .addra(config_words_addra), .ena(config_words_ena), .wea(1'b0), .dina(128'd0), .douta(config_words_douta),
        .addrb(config_words_addrb), .enb(config_words_enb), .web(config_words_web), .dinb(config_words_dinb), .doutb(config_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(64), .ADDR_WIDTH(10), .DEPTH(1024)) u_state_words (
        .clk(clk),
        .addra(state_words_addra), .ena(state_words_ena), .wea(state_words_wea), .dina(state_words_dina), .douta(state_words_douta),
        .addrb(state_words_addrb), .enb(state_words_enb), .web(state_words_web), .dinb(state_words_dinb), .doutb(state_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(64), .ADDR_WIDTH(12), .DEPTH(4096)) u_axon_words (
        .clk(clk),
        .addra(axon_words_addra), .ena(axon_words_ena), .wea(1'b0), .dina(64'd0), .douta(axon_words_douta),
        .addrb(axon_words_addrb), .enb(axon_words_enb), .web(axon_words_web), .dinb(axon_words_dinb), .doutb(axon_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(64), .ADDR_WIDTH(15), .DEPTH(32768)) u_synapse_words (
        .clk(clk),
        .addra(synapse_words_addra), .ena(synapse_words_ena), .wea(1'b0), .dina(64'd0), .douta(synapse_words_douta),
        .addrb(synapse_words_addrb), .enb(synapse_words_enb), .web(synapse_words_web), .dinb(synapse_words_dinb), .doutb(synapse_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(32), .ADDR_WIDTH(10), .DEPTH(1024)) u_route_desc_words (
        .clk(clk),
        .addra(route_desc_words_addra), .ena(route_desc_words_ena), .wea(1'b0), .dina(32'd0), .douta(route_desc_words_douta),
        .addrb(route_desc_words_addrb), .enb(route_desc_words_enb), .web(route_desc_words_web), .dinb(route_desc_words_dinb), .doutb(route_desc_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(32), .ADDR_WIDTH(12), .DEPTH(4096)) u_route_words (
        .clk(clk),
        .addra(route_words_addra), .ena(route_words_ena), .wea(1'b0), .dina(32'd0), .douta(route_words_douta),
        .addrb(route_words_addrb), .enb(route_words_enb), .web(route_words_web), .dinb(route_words_dinb), .doutb(route_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(32), .ADDR_WIDTH(12), .DEPTH(4096)) u_input_events (
        .clk(clk),
        .addra(input_events_addra), .ena(input_events_ena), .wea(1'b0), .dina(32'd0), .douta(input_events_douta),
        .addrb(input_events_addrb), .enb(input_events_enb), .web(input_events_web), .dinb(input_events_dinb), .doutb(input_events_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(256), .ADDR_WIDTH(10), .DEPTH(1024)) u_trace_words (
        .clk(clk),
        .addra(trace_words_addra), .ena(trace_words_ena), .wea(trace_words_wea), .dina(trace_words_dina), .douta(unused_trace_words_douta),
        .addrb(trace_words_addrb), .enb(trace_words_enb), .web(trace_words_web), .dinb(trace_words_dinb), .doutb(trace_words_doutb)
    );

    (* keep_hierarchy = "yes" *) p03_tdp_xpm_bank #(.DATA_WIDTH(64), .ADDR_WIDTH(12), .DEPTH(4096)) u_packet_words (
        .clk(clk),
        .addra(packet_words_addra), .ena(packet_words_ena), .wea(packet_words_wea), .dina(packet_words_dina), .douta(unused_packet_words_douta),
        .addrb(packet_words_addrb), .enb(packet_words_enb), .web(packet_words_web), .dinb(packet_words_dinb), .doutb(packet_words_doutb)
    );
endmodule
