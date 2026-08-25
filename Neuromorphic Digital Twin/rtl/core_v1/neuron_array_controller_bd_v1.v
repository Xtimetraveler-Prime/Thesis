`timescale 1ns/1ps

// IP-Integrator-facing Verilog wrapper for neuron_array_controller_v1.
//
// Vivado Module Reference requires the top module definition to be Verilog or
// VHDL; the underlying neuron_array_controller_v1 implementation remains
// SystemVerilog. Keep the HLS control handshake as four ordinary scalar pins so
// the source-controlled Vivado Tcl can wire every ap_ctrl_hs member explicitly.
module neuron_array_controller_bd_v1 #(
    parameter integer MAX_NEURONS = 256
) (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ap_clk CLK" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_clk, ASSOCIATED_RESET ap_rst, FREQ_HZ 100000000" *)
    input  wire         ap_clk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 ap_rst RST" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_rst, POLARITY ACTIVE_HIGH" *)
    input  wire         ap_rst,

    input  wire         core_reset_start,
    input  wire         tick_start,
    input  wire [8:0]   neuron_count,

    output wire         busy,
    output wire         core_reset_done,
    output wire         tick_done,
    output wire [31:0]  tick,
    output wire         fault,
    output wire [7:0]   fault_code,
    output wire [7:0]   active_neuron,

    input  wire         config_we,
    input  wire [7:0]   config_addr,
    input  wire [127:0] config_wdata,
    input  wire         state_we,
    input  wire [7:0]   state_addr,
    input  wire [63:0]  state_wdata,
    input  wire         accum_we,
    input  wire [7:0]   accum_addr,
    input  wire signed [63:0] accum_wdata,

    input  wire         debug_re,
    input  wire [7:0]   debug_addr,
    output wire         debug_rvalid,
    output wire [127:0] debug_config_rdata,
    output wire [63:0]  debug_state_rdata,
    output wire signed [63:0] debug_accum_rdata,
    output wire         debug_spike_rdata,

    output wire         hls_ap_start,
    input  wire         hls_ap_done,
    input  wire         hls_ap_idle,
    input  wire         hls_ap_ready,

    output wire signed [23:0] hls_current_before,
    output wire signed [23:0] hls_voltage_before,
    output wire        [15:0] hls_refractory_before,
    output wire signed [63:0] hls_synaptic_input,
    output wire        [12:0] hls_current_decay,
    output wire        [12:0] hls_voltage_decay,
    output wire signed [23:0] hls_threshold,
    output wire signed [23:0] hls_bias,
    output wire signed [23:0] hls_reset_voltage,
    output wire        [15:0] hls_refractory_ticks,

    input  wire signed [23:0] hls_current_after,
    input  wire                hls_current_after_ap_vld,
    input  wire signed [23:0] hls_voltage_after,
    input  wire                hls_voltage_after_ap_vld,
    input  wire        [15:0] hls_refractory_after,
    input  wire                hls_refractory_after_ap_vld,
    input  wire                hls_spiked,
    input  wire                hls_spiked_ap_vld
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
