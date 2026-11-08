// M05.11b bus-to-stream shell: AXI4-Lite command slave plus all 4 shims.
// No HLS kernel is instantiated here. This shell is one-clock only.
// PS MUST independently read actual HLS ap_done/ap_return before FINISH.
// Driver/clock/reset, AMD AXI DMA IP, PS DDR, and HLS RTL integration are
// NOT implemented or verified by this structural assembly alone.
module m05_11_stream_shell(
    input wire clk, input wire rst_n,
    input wire [7:0] s_axi_awaddr,
    input wire s_axi_awvalid, output wire s_axi_awready,
    input wire [31:0] s_axi_wdata, input wire [3:0] s_axi_wstrb,
    input wire s_axi_wvalid, output wire s_axi_wready,
    output wire [1:0] s_axi_bresp, output wire s_axi_bvalid,
    input wire s_axi_bready,
    input wire [7:0] s_axi_araddr, input wire s_axi_arvalid,
    output wire s_axi_arready,
    output wire [31:0] s_axi_rdata,
    output wire [1:0] s_axi_rresp,
    output wire s_axi_rvalid, input wire s_axi_rready,

    input wire [255:0] n_dma_tdata,
    input wire [31:0] n_dma_tkeep,
    input wire n_dma_tlast, input wire n_dma_tvalid,
    output wire n_dma_tready,
    input wire [255:0] s_dma_tdata,
    input wire [31:0] s_dma_tkeep,
    input wire s_dma_tlast, input wire s_dma_tvalid,
    output wire s_dma_tready,
    input wire [255:0] e_dma_tdata,
    input wire [31:0] e_dma_tkeep,
    input wire e_dma_tlast, input wire e_dma_tvalid,
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
    output wire [255:0] trace_dma_tdata,
    output wire [31:0] trace_dma_tkeep,
    output wire trace_dma_tvalid,
    input wire trace_dma_tready,
    output wire trace_dma_tlast,
    output wire [2:0] session_state
);
    wire start_pulse, finish_valid;
    wire [63:0] session_id;
    wire [31:0] trace_expected, neuron_expected, synapse_expected,
                external_expected, finish_status;
    wire trace_start_ready, n_start_ready, s_start_ready, e_start_ready;
    wire trace_finish_ready;
    wire trace_done, trace_fault, n_done, s_done, e_done, n_fault, s_fault,
         e_fault;
    wire [31:0] trace_rows, n_count, s_count, e_count;
    wire all_ready = trace_start_ready && n_start_ready &&
                     s_start_ready && e_start_ready;

    m05_11_axil_session_controller control(
        .clk(clk), .rst_n(rst_n),
        .s_axi_awaddr(s_axi_awaddr), .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready), .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb), .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready), .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid), .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr), .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready), .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp), .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .bridge_start_ready(all_ready), .trace_finish_ready(trace_finish_ready),
        .trace_packet_done(trace_done), .trace_packet_fault(trace_fault),
        .neuron_done(n_done), .synapse_done(s_done), .external_done(e_done),
        .neuron_fault(n_fault), .synapse_fault(s_fault),
        .external_fault(e_fault),
        .trace_rows(trace_rows), .neuron_beats(n_count),
        .synapse_beats(s_count), .external_beats(e_count),
        .bridge_start_pulse(start_pulse), .bridge_session_id(session_id),
        .bridge_expected_trace(trace_expected),
        .bridge_neurons(neuron_expected),
        .bridge_synapses(synapse_expected),
        .bridge_external(external_expected),
        .bridge_finish_valid(finish_valid), .bridge_finish_status(finish_status),
        .controller_state(session_state)
    );
    m05_ingress_dma_unpad #(.PAYLOAD_WIDTH(128)) neuron_bridge(
        .clk(clk), .rst_n(rst_n), .start_valid(start_pulse),
        .start_ready(n_start_ready), .start_expected_beats(neuron_expected),
        .s_dma_tdata(n_dma_tdata), .s_dma_tkeep(n_dma_tkeep),
        .s_dma_tlast(n_dma_tlast), .s_dma_tvalid(n_dma_tvalid),
        .s_dma_tready(n_dma_tready), .m_hls_tdata(hls_neuron_tdata),
        .m_hls_tvalid(hls_neuron_tvalid),
        .m_hls_tready(hls_neuron_tready), .done(n_done),
        .fault(n_fault), .accepted_beats(n_count)
    );
    m05_ingress_dma_unpad #(.PAYLOAD_WIDTH(192)) synapse_bridge(
        .clk(clk), .rst_n(rst_n), .start_valid(start_pulse),
        .start_ready(s_start_ready), .start_expected_beats(synapse_expected),
        .s_dma_tdata(s_dma_tdata), .s_dma_tkeep(s_dma_tkeep),
        .s_dma_tlast(s_dma_tlast), .s_dma_tvalid(s_dma_tvalid),
        .s_dma_tready(s_dma_tready), .m_hls_tdata(hls_synapse_tdata),
        .m_hls_tvalid(hls_synapse_tvalid),
        .m_hls_tready(hls_synapse_tready), .done(s_done),
        .fault(s_fault), .accepted_beats(s_count)
    );
    m05_ingress_dma_unpad #(.PAYLOAD_WIDTH(128)) external_bridge(
        .clk(clk), .rst_n(rst_n), .start_valid(start_pulse),
        .start_ready(e_start_ready), .start_expected_beats(external_expected),
        .s_dma_tdata(e_dma_tdata), .s_dma_tkeep(e_dma_tkeep),
        .s_dma_tlast(e_dma_tlast), .s_dma_tvalid(e_dma_tvalid),
        .s_dma_tready(e_dma_tready), .m_hls_tdata(hls_external_tdata),
        .m_hls_tvalid(hls_external_tvalid),
        .m_hls_tready(hls_external_tready), .done(e_done),
        .fault(e_fault), .accepted_beats(e_count)
    );
    m05_trace_dma_packetizer trace_bridge(
        .clk(clk), .rst_n(rst_n), .start_valid(start_pulse),
        .start_ready(trace_start_ready), .start_session_id(session_id),
        .start_expected_rows(trace_expected),
        .finish_valid(finish_valid), .finish_ready(trace_finish_ready),
        .finish_status(finish_status),
        .trace_tdata(hls_trace_tdata), .trace_tvalid(hls_trace_tvalid),
        .trace_tready(hls_trace_tready),
        .dma_tdata(trace_dma_tdata), .dma_tkeep(trace_dma_tkeep),
        .dma_tvalid(trace_dma_tvalid), .dma_tready(trace_dma_tready),
        .dma_tlast(trace_dma_tlast),
        .done(trace_done), .fault(trace_fault), .captured_rows(trace_rows)
    );
endmodule
