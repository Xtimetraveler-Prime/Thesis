// M05.12d.1 PL-only AXI4-Stream interface exposure around unchanged M05.11.
// Enables Vivado Module Reference AXIS inference. DOES NOT attach HLS/PS/DDR.
// All four 256-bit AXIS channels carry TDATA/TKEEP/TLAST/TVALID/TREADY.
// Do not turn HLS native 128/192-bit streams into faux 256-bit signals.
module m05_12d_axis_shell_ref(
    input wire clk,
    input wire rst_n,
    input wire [7:0] s_axi_awaddr,
    input wire [2:0] s_axi_awprot,
    input wire s_axi_awvalid,
    output wire s_axi_awready,
    input wire [31:0] s_axi_wdata,
    input wire [3:0] s_axi_wstrb,
    input wire s_axi_wvalid,
    output wire s_axi_wready,
    output wire [1:0] s_axi_bresp,
    output wire s_axi_bvalid,
    input wire s_axi_bready,
    input wire [7:0] s_axi_araddr,
    input wire [2:0] s_axi_arprot,
    input wire s_axi_arvalid,
    output wire s_axi_arready,
    output wire [31:0] s_axi_rdata,
    output wire [1:0] s_axi_rresp,
    output wire s_axi_rvalid,
    input wire s_axi_rready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_NEURONS TDATA", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXIS_NEURONS, TDATA_NUM_BYTES 32, HAS_TKEEP 1, HAS_TLAST 1" *)
    input wire [255:0] n_dma_tdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_NEURONS TKEEP" *)
    input wire [31:0] n_dma_tkeep,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_NEURONS TLAST" *)
    input wire n_dma_tlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_NEURONS TVALID" *)
    input wire n_dma_tvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_NEURONS TREADY" *)
    output wire n_dma_tready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_SYNAPSES TDATA", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXIS_SYNAPSES, TDATA_NUM_BYTES 32, HAS_TKEEP 1, HAS_TLAST 1" *)
    input wire [255:0] s_dma_tdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_SYNAPSES TKEEP" *)
    input wire [31:0] s_dma_tkeep,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_SYNAPSES TLAST" *)
    input wire s_dma_tlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_SYNAPSES TVALID" *)
    input wire s_dma_tvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_SYNAPSES TREADY" *)
    output wire s_dma_tready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_EXTERNAL TDATA", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXIS_EXTERNAL, TDATA_NUM_BYTES 32, HAS_TKEEP 1, HAS_TLAST 1" *)
    input wire [255:0] e_dma_tdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_EXTERNAL TKEEP" *)
    input wire [31:0] e_dma_tkeep,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_EXTERNAL TLAST" *)
    input wire e_dma_tlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_EXTERNAL TVALID" *)
    input wire e_dma_tvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 S_AXIS_EXTERNAL TREADY" *)
    output wire e_dma_tready,
    output wire [127:0] hls_neuron_tdata,
    output wire hls_neuron_tvalid,
    input wire hls_neuron_tready,
    output wire [191:0] hls_synapse_tdata,
    output wire hls_synapse_tvalid,
    input wire hls_synapse_tready,
    output wire [127:0] hls_external_tdata,
    output wire hls_external_tvalid,
    input wire hls_external_tready,
    input wire [191:0] hls_trace_tdata,
    input wire hls_trace_tvalid,
    output wire hls_trace_tready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_TRACE TDATA", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME M_AXIS_TRACE, TDATA_NUM_BYTES 32, HAS_TKEEP 1, HAS_TLAST 1" *)
    output wire [255:0] trace_dma_tdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_TRACE TKEEP" *)
    output wire [31:0] trace_dma_tkeep,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_TRACE TVALID" *)
    output wire trace_dma_tvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_TRACE TREADY" *)
    input wire trace_dma_tready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 M_AXIS_TRACE TLAST" *)
    output wire trace_dma_tlast,
    output wire [2:0] session_state
);
    m05_11_stream_shell shell_core(
        .clk(clk),
        .rst_n(rst_n),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awprot(s_axi_awprot),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arprot(s_axi_arprot),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .n_dma_tdata(n_dma_tdata),
        .n_dma_tkeep(n_dma_tkeep),
        .n_dma_tlast(n_dma_tlast),
        .n_dma_tvalid(n_dma_tvalid),
        .n_dma_tready(n_dma_tready),
        .s_dma_tdata(s_dma_tdata),
        .s_dma_tkeep(s_dma_tkeep),
        .s_dma_tlast(s_dma_tlast),
        .s_dma_tvalid(s_dma_tvalid),
        .s_dma_tready(s_dma_tready),
        .e_dma_tdata(e_dma_tdata),
        .e_dma_tkeep(e_dma_tkeep),
        .e_dma_tlast(e_dma_tlast),
        .e_dma_tvalid(e_dma_tvalid),
        .e_dma_tready(e_dma_tready),
        .hls_neuron_tdata(hls_neuron_tdata),
        .hls_neuron_tvalid(hls_neuron_tvalid),
        .hls_neuron_tready(hls_neuron_tready),
        .hls_synapse_tdata(hls_synapse_tdata),
        .hls_synapse_tvalid(hls_synapse_tvalid),
        .hls_synapse_tready(hls_synapse_tready),
        .hls_external_tdata(hls_external_tdata),
        .hls_external_tvalid(hls_external_tvalid),
        .hls_external_tready(hls_external_tready),
        .hls_trace_tdata(hls_trace_tdata),
        .hls_trace_tvalid(hls_trace_tvalid),
        .hls_trace_tready(hls_trace_tready),
        .trace_dma_tdata(trace_dma_tdata),
        .trace_dma_tkeep(trace_dma_tkeep),
        .trace_dma_tvalid(trace_dma_tvalid),
        .trace_dma_tready(trace_dma_tready),
        .trace_dma_tlast(trace_dma_tlast),
        .session_state(session_state)
    );
endmodule
