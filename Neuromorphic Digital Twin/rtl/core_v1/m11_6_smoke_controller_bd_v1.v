`timescale 1ns/1ps

// Verilog-2001 Module Reference boundary for the SystemVerilog M11.6 smoke
// sequencer. Vivado 2025.2 Module Reference requires a Verilog top in this flow.
module m11_6_smoke_controller_bd_v1 (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ap_clk CLK" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_clk, ASSOCIATED_RESET smoke_resetn" *)
    input  wire         ap_clk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 pl_resetn0 RST" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME smoke_resetn, POLARITY ACTIVE_LOW" *)
    input  wire         smoke_resetn,
    input  wire         smoke_start,

    output wire [31:0]  clock_heartbeat,
    output wire         smoke_busy,
    output wire         smoke_done,
    output wire         smoke_pass,
    output wire [7:0]   smoke_fail_code,
    output wire [7:0]   smoke_phase,
    output wire [31:0]  observed_tick,
    output wire [7:0]   observed_core_fault_code,
    output wire [63:0]  observed_state0,
    output wire [63:0]  observed_state1,
    output wire [63:0]  observed_state2,
    output wire [2:0]   observed_spikes,
    output wire         observed_recurrent_bank,
    output wire [12:0]  observed_recurrent_count,

    output wire                hls_ap_rst,
    output wire                hls_ap_start,
    input  wire                hls_ap_done,
    input  wire                hls_ap_idle,
    input  wire                hls_ap_ready,
    output wire signed [23:0]  hls_current_before,
    output wire signed [23:0]  hls_voltage_before,
    output wire        [15:0]  hls_refractory_before,
    output wire signed [63:0]  hls_synaptic_input,
    output wire        [12:0]  hls_current_decay,
    output wire        [12:0]  hls_voltage_decay,
    output wire signed [23:0]  hls_threshold,
    output wire signed [23:0]  hls_bias,
    output wire signed [23:0]  hls_reset_voltage,
    output wire        [15:0]  hls_refractory_ticks,
    input  wire signed [23:0]  hls_current_after,
    input  wire                hls_current_after_ap_vld,
    input  wire signed [23:0]  hls_voltage_after,
    input  wire                hls_voltage_after_ap_vld,
    input  wire        [15:0]  hls_refractory_after,
    input  wire                hls_refractory_after_ap_vld,
    input  wire                hls_spiked,
    input  wire                hls_spiked_ap_vld
);

    // Free-running physical PL-clock witness. It is intentionally independent
    // of the smoke/core reset so Hardware Manager can distinguish a stopped
    // pl_clk0 from a reset or datapath problem before starting the workload.
    reg [31:0] heartbeat_counter = 32'h00000000;
    always @(posedge ap_clk) begin
        heartbeat_counter <= heartbeat_counter + 32'd1;
    end
    assign clock_heartbeat = heartbeat_counter;

    m11_6_smoke_controller_v1 smoke_i (
        .ap_clk(ap_clk),
        .smoke_resetn(smoke_resetn),
        .smoke_start(smoke_start),
        .smoke_busy(smoke_busy),
        .smoke_done(smoke_done),
        .smoke_pass(smoke_pass),
        .smoke_fail_code(smoke_fail_code),
        .smoke_phase(smoke_phase),
        .observed_tick(observed_tick),
        .observed_core_fault_code(observed_core_fault_code),
        .observed_state0(observed_state0),
        .observed_state1(observed_state1),
        .observed_state2(observed_state2),
        .observed_spikes(observed_spikes),
        .observed_recurrent_bank(observed_recurrent_bank),
        .observed_recurrent_count(observed_recurrent_count),
        .hls_ap_rst(hls_ap_rst),
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
