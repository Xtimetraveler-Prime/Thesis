`timescale 1ns/1ps

// Verilog-2001 Module Reference boundary for the M12.2 capture controller.
// Port shape intentionally matches M12.1 so the proven VIO/JTAG transport can
// be reused without adding a new hardware-debug interface.
module m12_2_single_tick_capture_controller_bd_v1 (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ap_clk CLK" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_clk, ASSOCIATED_RESET capture_resetn" *)
    input  wire         ap_clk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 capture_resetn RST" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME capture_resetn, POLARITY ACTIVE_LOW" *)
    input  wire         capture_resetn,

    input  wire         capture_start,
    input  wire         capture_step,
    input  wire         trace_read_req,
    input  wire [2:0]   trace_read_space,
    input  wire [11:0]  trace_read_addr,

    output wire [31:0]  clock_heartbeat,
    output wire         start_seen,
    output wire         capture_busy,
    output wire         step_ready,
    output wire         trace_window_open,
    output wire         capture_done,
    output wire         capture_fault,
    output wire [7:0]   capture_fault_code,
    output wire [7:0]   capture_phase,
    output wire [31:0]  observed_tick,
    output wire         observed_core_fault,
    output wire [7:0]   observed_core_fault_code,
    output wire         observed_recurrent_bank,
    output wire [12:0]  observed_recurrent_count,
    output wire [12:0]  observed_recurrent_bank0_count,
    output wire [12:0]  observed_recurrent_bank1_count,
    output wire [12:0]  observed_consumed_recurrent_count,
    output wire [12:0]  observed_routed_recurrent_count,
    output wire [12:0]  observed_external_event_count,
    output wire         trace_read_ready,
    output wire [15:0]  trace_response_seq,
    output wire [2:0]   trace_response_space,
    output wire [11:0]  trace_response_addr,
    output wire [63:0]  trace_response_data,
    output wire         trace_response_error,

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

    reg [31:0] heartbeat_counter = 32'h00000000;
    always @(posedge ap_clk)
        heartbeat_counter <= heartbeat_counter + 32'd1;
    assign clock_heartbeat = heartbeat_counter;

    reg start_seen_reg = 1'b0;
    always @(posedge ap_clk) begin
        if (capture_start)
            start_seen_reg <= 1'b1;
    end
    assign start_seen = start_seen_reg;

    m12_2_single_tick_capture_controller_v1 capture_i (
        .ap_clk(ap_clk), .capture_resetn(capture_resetn),
        .capture_start(capture_start), .capture_step(capture_step),
        .capture_busy(capture_busy), .step_ready(step_ready),
        .trace_window_open(trace_window_open), .capture_done(capture_done),
        .capture_fault(capture_fault), .capture_fault_code(capture_fault_code),
        .capture_phase(capture_phase),
        .observed_tick(observed_tick), .observed_core_fault(observed_core_fault),
        .observed_core_fault_code(observed_core_fault_code),
        .observed_recurrent_bank(observed_recurrent_bank),
        .observed_recurrent_count(observed_recurrent_count),
        .observed_recurrent_bank0_count(observed_recurrent_bank0_count),
        .observed_recurrent_bank1_count(observed_recurrent_bank1_count),
        .observed_consumed_recurrent_count(observed_consumed_recurrent_count),
        .observed_routed_recurrent_count(observed_routed_recurrent_count),
        .observed_external_event_count(observed_external_event_count),
        .trace_read_req(trace_read_req), .trace_read_space(trace_read_space),
        .trace_read_addr(trace_read_addr), .trace_read_ready(trace_read_ready),
        .trace_response_seq(trace_response_seq),
        .trace_response_space(trace_response_space),
        .trace_response_addr(trace_response_addr),
        .trace_response_data(trace_response_data),
        .trace_response_error(trace_response_error),
        .hls_ap_start(hls_ap_start), .hls_ap_done(hls_ap_done),
        .hls_ap_idle(hls_ap_idle), .hls_ap_ready(hls_ap_ready),
        .hls_current_before(hls_current_before), .hls_voltage_before(hls_voltage_before),
        .hls_refractory_before(hls_refractory_before), .hls_synaptic_input(hls_synaptic_input),
        .hls_current_decay(hls_current_decay), .hls_voltage_decay(hls_voltage_decay),
        .hls_threshold(hls_threshold), .hls_bias(hls_bias),
        .hls_reset_voltage(hls_reset_voltage), .hls_refractory_ticks(hls_refractory_ticks),
        .hls_current_after(hls_current_after), .hls_current_after_ap_vld(hls_current_after_ap_vld),
        .hls_voltage_after(hls_voltage_after), .hls_voltage_after_ap_vld(hls_voltage_after_ap_vld),
        .hls_refractory_after(hls_refractory_after),
        .hls_refractory_after_ap_vld(hls_refractory_after_ap_vld),
        .hls_spiked(hls_spiked), .hls_spiked_ap_vld(hls_spiked_ap_vld)
    );

endmodule
