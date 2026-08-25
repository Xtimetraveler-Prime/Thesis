`timescale 1ns/1ps

// IP-Integrator-facing wrapper for neuron_array_controller_v1.
//
// The wrapper adds Vivado interface metadata only. The sequencing/memory logic
// remains entirely in neuron_array_controller_v1. The hls_ctrl interface is the
// acc_handshake master that directly drives the packaged neuron_step_v1 ap_ctrl
// slave interface without overriding individual interface-member pins in BD.
module neuron_array_controller_bd_v1 #(
    parameter integer MAX_NEURONS = 256
) (
    input  logic         ap_clk,
    input  logic         ap_rst,

    input  logic         core_reset_start,
    input  logic         tick_start,
    input  logic [8:0]   neuron_count,

    output logic         busy,
    output logic         core_reset_done,
    output logic         tick_done,
    output logic [31:0]  tick,
    output logic         fault,
    output logic [7:0]   fault_code,
    output logic [7:0]   active_neuron,

    input  logic         config_we,
    input  logic [7:0]   config_addr,
    input  logic [127:0] config_wdata,
    input  logic         state_we,
    input  logic [7:0]   state_addr,
    input  logic [63:0]  state_wdata,
    input  logic         accum_we,
    input  logic [7:0]   accum_addr,
    input  logic signed [63:0] accum_wdata,

    input  logic         debug_re,
    input  logic [7:0]   debug_addr,
    output logic         debug_rvalid,
    output logic [127:0] debug_config_rdata,
    output logic [63:0]  debug_state_rdata,
    output logic signed [63:0] debug_accum_rdata,
    output logic         debug_spike_rdata,

    (* X_INTERFACE_INFO = "xilinx.com:interface:acc_handshake:1.0 hls_ctrl AP_START" *)
    output logic         hls_ap_start,
    (* X_INTERFACE_INFO = "xilinx.com:interface:acc_handshake:1.0 hls_ctrl AP_DONE" *)
    input  logic         hls_ap_done,
    (* X_INTERFACE_INFO = "xilinx.com:interface:acc_handshake:1.0 hls_ctrl AP_IDLE" *)
    input  logic         hls_ap_idle,
    (* X_INTERFACE_INFO = "xilinx.com:interface:acc_handshake:1.0 hls_ctrl AP_READY" *)
    input  logic         hls_ap_ready,

    output logic signed [23:0] hls_current_before,
    output logic signed [23:0] hls_voltage_before,
    output logic        [15:0] hls_refractory_before,
    output logic signed [63:0] hls_synaptic_input,
    output logic        [12:0] hls_current_decay,
    output logic        [12:0] hls_voltage_decay,
    output logic signed [23:0] hls_threshold,
    output logic signed [23:0] hls_bias,
    output logic signed [23:0] hls_reset_voltage,
    output logic        [15:0] hls_refractory_ticks,

    input  logic signed [23:0] hls_current_after,
    input  logic                hls_current_after_ap_vld,
    input  logic signed [23:0] hls_voltage_after,
    input  logic                hls_voltage_after_ap_vld,
    input  logic        [15:0] hls_refractory_after,
    input  logic                hls_refractory_after_ap_vld,
    input  logic                hls_spiked,
    input  logic                hls_spiked_ap_vld
);

    neuron_array_controller_v1 #(
        .MAX_NEURONS(MAX_NEURONS)
    ) controller_i (
        .ap_clk(ap_clk),
        .ap_rst(ap_rst),
        .core_reset_start(core_reset_start),
        .tick_start(tick_start),
        .neuron_count(neuron_count),
        .busy(busy),
        .core_reset_done(core_reset_done),
        .tick_done(tick_done),
        .tick(tick),
        .fault(fault),
        .fault_code(fault_code),
        .active_neuron(active_neuron),
        .config_we(config_we),
        .config_addr(config_addr),
        .config_wdata(config_wdata),
        .state_we(state_we),
        .state_addr(state_addr),
        .state_wdata(state_wdata),
        .accum_we(accum_we),
        .accum_addr(accum_addr),
        .accum_wdata(accum_wdata),
        .debug_re(debug_re),
        .debug_addr(debug_addr),
        .debug_rvalid(debug_rvalid),
        .debug_config_rdata(debug_config_rdata),
        .debug_state_rdata(debug_state_rdata),
        .debug_accum_rdata(debug_accum_rdata),
        .debug_spike_rdata(debug_spike_rdata),
        .hls_ap_start(hls_ap_start),
        .hls_ap_done(hls_ap_done),
        .hls_ap_idle(hls_ap_idle),
        .hls_ap_ready(hls_ap_ready),
        .hls_current_before(hls_current_before),
        .hls_voltage_before(hls_voltage_before),
        .hls_refractory_before(hls_refractory_before),
        .hls_synaptic_input(hls_synaptic_input),
        .hls_current_decay(hls_current_decay),
        .hls_voltage_decay(hls_voltage_decay),
        .hls_threshold(hls_threshold),
        .hls_bias(hls_bias),
        .hls_reset_voltage(hls_reset_voltage),
        .hls_refractory_ticks(hls_refractory_ticks),
        .hls_current_after(hls_current_after),
        .hls_current_after_ap_vld(hls_current_after_ap_vld),
        .hls_voltage_after(hls_voltage_after),
        .hls_voltage_after_ap_vld(hls_voltage_after_ap_vld),
        .hls_refractory_after(hls_refractory_after),
        .hls_refractory_after_ap_vld(hls_refractory_after_ap_vld),
        .hls_spiked(hls_spiked),
        .hls_spiked_ap_vld(hls_spiked_ap_vld)
    );

endmodule
