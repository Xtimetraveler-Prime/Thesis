`timescale 1ns/1ps

// M11.5.3 composition controller.
//
// This module preserves the independently verified M11.5.2 neuron controller
// and the standalone M11.5.3 Phase-B walker as separate blocks. For tick_start,
// it runs Phase B to completion, copies the resulting signed-64 accumulator
// image internally into the M11.5.2 controller, then launches Phase C. There is
// deliberately no host/testbench accumulator preload at this boundary.
module integrated_core_controller_v1 #(
    parameter integer MAX_NEURONS  = 256,
    parameter integer MAX_AXONS    = 1024,
    parameter integer MAX_SYNAPSES = 4096,
    parameter integer MAX_FORMATS  = 16,
    parameter integer MAX_EVENTS   = 4096
) (
    input  logic         ap_clk,
    input  logic         ap_rst,

    input  logic         core_reset_start,
    input  logic         tick_start,
    input  logic [8:0]   neuron_count,
    input  logic [10:0]  axon_count,
    input  logic [12:0]  synapse_count,
    input  logic [4:0]   format_count,
    input  logic [12:0]  external_event_count,
    input  logic [12:0]  recurrent_event_count,

    output logic         busy,
    output logic         core_reset_done,
    output logic         tick_done,
    output logic [31:0]  tick,
    output logic         fault,
    output logic [7:0]   fault_code,
    output logic [7:0]   active_neuron,
    output logic         phase_b_active_source,
    output logic [12:0]  phase_b_active_event_index,
    output logic [31:0]  phase_b_active_synapse_index,

    // Neuron configuration/state preload. Accumulators are intentionally absent.
    input  logic         config_we,
    input  logic [7:0]   config_addr,
    input  logic [127:0] config_wdata,
    input  logic         state_we,
    input  logic [7:0]   state_addr,
    input  logic [63:0]  state_wdata,

    // Frozen M08 image + tick event preload.
    input  logic         format_we,
    input  logic [3:0]   format_addr,
    input  logic [15:0]  format_wdata,
    input  logic         synapse_we,
    input  logic [11:0]  synapse_addr,
    input  logic [31:0]  synapse_wdata,
    input  logic         row_we,
    input  logic [10:0]  row_addr,
    input  logic [31:0]  row_wdata,
    input  logic         external_we,
    input  logic [11:0]  external_addr,
    input  logic [15:0]  external_wdata,
    input  logic         recurrent_we,
    input  logic [11:0]  recurrent_addr,
    input  logic [15:0]  recurrent_wdata,

    // Committed neuron observability. Reads are accepted only while top idle.
    input  logic         debug_re,
    input  logic [7:0]   debug_addr,
    output logic         debug_rvalid,
    output logic [127:0] debug_config_rdata,
    output logic [63:0]  debug_state_rdata,
    output logic signed [63:0] debug_accum_rdata,
    output logic         debug_spike_rdata,

    // Scalar connection to packaged neuron_step_v1.
    output logic         hls_ap_start,
    input  logic         hls_ap_done,
    input  logic         hls_ap_idle,
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

    localparam logic [7:0] FAULT_NONE            = 8'h00;
    localparam logic [7:0] FAULT_CONCURRENT_CMD  = 8'h01;
    localparam logic [7:0] FAULT_PHASE_B_BASE    = 8'h40;
    localparam logic [7:0] FAULT_NEURON_BASE     = 8'h80;
    localparam logic [7:0] FAULT_COPY_PROTOCOL   = 8'hFE;

    typedef enum logic [3:0] {
        S_IDLE,
        S_RESET_START,
        S_RESET_WAIT,
        S_PHASE_B_START,
        S_PHASE_B_WAIT,
        S_COPY_READ,
        S_COPY_WAIT,
        S_COPY_WRITE,
        S_NEURON_TICK_START,
        S_NEURON_TICK_WAIT
    } integration_state_t;

    integration_state_t integration_state;
    logic [8:0] active_count;
    logic [7:0] copy_index;
    logic signed [63:0] copy_data;

    logic phase_b_start;
    logic phase_b_busy;
    logic phase_b_done;
    logic phase_b_fault;
    logic [7:0] phase_b_fault_code;
    logic phase_b_debug_re;
    logic [7:0] phase_b_debug_addr;
    logic phase_b_debug_rvalid;
    logic signed [63:0] phase_b_debug_rdata;

    logic neuron_busy;
    logic neuron_core_reset_start;
    logic neuron_tick_start;
    logic neuron_core_reset_done;
    logic neuron_tick_done;
    logic neuron_fault;
    logic [7:0] neuron_fault_code;
    logic neuron_config_we;
    logic neuron_state_we;
    logic neuron_accum_we;
    logic [7:0] neuron_accum_addr;
    logic signed [63:0] neuron_accum_wdata;
    logic neuron_debug_re;

    assign busy = (integration_state != S_IDLE);
    assign phase_b_start = (integration_state == S_PHASE_B_START);
    assign neuron_core_reset_start = (integration_state == S_RESET_START);
    assign neuron_tick_start = (integration_state == S_NEURON_TICK_START);
    assign phase_b_debug_re = (integration_state == S_COPY_READ);
    assign phase_b_debug_addr = copy_index;
    assign neuron_accum_we = (integration_state == S_COPY_WRITE);
    assign neuron_accum_addr = copy_index;
    assign neuron_accum_wdata = copy_data;

    // Preserve the atomic integrated boundary: host/config/debug access is
    // accepted only while the composition controller is idle.
    assign neuron_config_we = config_we && (integration_state == S_IDLE);
    assign neuron_state_we = state_we && (integration_state == S_IDLE);
    assign neuron_debug_re = debug_re && (integration_state == S_IDLE);

    phase_b_synapse_accumulator_v1 #(
        .MAX_NEURONS(MAX_NEURONS),
        .MAX_AXONS(MAX_AXONS),
        .MAX_SYNAPSES(MAX_SYNAPSES),
        .MAX_FORMATS(MAX_FORMATS),
        .MAX_EVENTS(MAX_EVENTS)
    ) phase_b_i (
        .ap_clk(ap_clk),
        .ap_rst(ap_rst),
        .start(phase_b_start),
        .neuron_count(neuron_count),
        .axon_count(axon_count),
        .synapse_count(synapse_count),
        .format_count(format_count),
        .external_event_count(external_event_count),
        .recurrent_event_count(recurrent_event_count),
        .busy(phase_b_busy),
        .done(phase_b_done),
        .fault(phase_b_fault),
        .fault_code(phase_b_fault_code),
        .active_source(phase_b_active_source),
        .active_event_index(phase_b_active_event_index),
        .active_synapse_index(phase_b_active_synapse_index),
        .format_we(format_we && (integration_state == S_IDLE)),
        .format_addr(format_addr),
        .format_wdata(format_wdata),
        .synapse_we(synapse_we && (integration_state == S_IDLE)),
        .synapse_addr(synapse_addr),
        .synapse_wdata(synapse_wdata),
        .row_we(row_we && (integration_state == S_IDLE)),
        .row_addr(row_addr),
        .row_wdata(row_wdata),
        .external_we(external_we && (integration_state == S_IDLE)),
        .external_addr(external_addr),
        .external_wdata(external_wdata),
        .recurrent_we(recurrent_we && (integration_state == S_IDLE)),
        .recurrent_addr(recurrent_addr),
        .recurrent_wdata(recurrent_wdata),
        .debug_accum_re(phase_b_debug_re),
        .debug_accum_addr(phase_b_debug_addr),
        .debug_accum_rvalid(phase_b_debug_rvalid),
        .debug_accum_rdata(phase_b_debug_rdata)
    );

    neuron_array_controller_v1 #(
        .MAX_NEURONS(MAX_NEURONS)
    ) neuron_controller_i (
        .ap_clk(ap_clk),
        .ap_rst(ap_rst),
        .core_reset_start(neuron_core_reset_start),
        .tick_start(neuron_tick_start),
        .neuron_count(neuron_count),
        .busy(neuron_busy),
        .core_reset_done(neuron_core_reset_done),
        .tick_done(neuron_tick_done),
        .tick(tick),
        .fault(neuron_fault),
        .fault_code(neuron_fault_code),
        .active_neuron(active_neuron),
        .config_we(neuron_config_we),
        .config_addr(config_addr),
        .config_wdata(config_wdata),
        .state_we(neuron_state_we),
        .state_addr(state_addr),
        .state_wdata(state_wdata),
        .accum_we(neuron_accum_we),
        .accum_addr(neuron_accum_addr),
        .accum_wdata(neuron_accum_wdata),
        .debug_re(neuron_debug_re),
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

    wire unused_sub_busy = phase_b_busy ^ neuron_busy;

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            integration_state <= S_IDLE;
            active_count       <= 9'd0;
            copy_index         <= 8'd0;
            copy_data          <= 64'sd0;
            core_reset_done    <= 1'b0;
            tick_done          <= 1'b0;
            fault              <= 1'b0;
            fault_code         <= FAULT_NONE;
        end else begin
            core_reset_done <= 1'b0;
            tick_done       <= 1'b0;

            case (integration_state)
                S_IDLE: begin
                    if (core_reset_start && tick_start) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_CONCURRENT_CMD;
                    end else if (core_reset_start) begin
                        fault             <= 1'b0;
                        fault_code        <= FAULT_NONE;
                        active_count      <= neuron_count;
                        integration_state <= S_RESET_START;
                    end else if (tick_start) begin
                        fault             <= 1'b0;
                        fault_code        <= FAULT_NONE;
                        active_count      <= neuron_count;
                        integration_state <= S_PHASE_B_START;
                    end
                end

                S_RESET_START: begin
                    integration_state <= S_RESET_WAIT;
                end

                S_RESET_WAIT: begin
                    if (neuron_fault) begin
                        fault             <= 1'b1;
                        fault_code        <= FAULT_NEURON_BASE | neuron_fault_code;
                        integration_state <= S_IDLE;
                    end else if (neuron_core_reset_done) begin
                        core_reset_done    <= 1'b1;
                        integration_state  <= S_IDLE;
                    end
                end

                S_PHASE_B_START: begin
                    integration_state <= S_PHASE_B_WAIT;
                end

                S_PHASE_B_WAIT: begin
                    if (phase_b_fault) begin
                        fault             <= 1'b1;
                        fault_code        <= FAULT_PHASE_B_BASE | phase_b_fault_code;
                        integration_state <= S_IDLE;
                    end else if (phase_b_done) begin
                        copy_index         <= 8'd0;
                        integration_state  <= S_COPY_READ;
                    end
                end

                S_COPY_READ: begin
                    integration_state <= S_COPY_WAIT;
                end

                S_COPY_WAIT: begin
                    if (!phase_b_debug_rvalid) begin
                        // The Phase-B debug read is synchronous. Remain here for
                        // the one-cycle response, but make a missing response a
                        // deterministic protocol fault on the following cycle.
                        integration_state <= S_COPY_WAIT;
                    end else begin
                        copy_data          <= phase_b_debug_rdata;
                        integration_state  <= S_COPY_WRITE;
                    end
                end

                S_COPY_WRITE: begin
                    if (({1'b0, copy_index} + 9'd1) >= active_count) begin
                        integration_state <= S_NEURON_TICK_START;
                    end else begin
                        copy_index        <= copy_index + 8'd1;
                        integration_state <= S_COPY_READ;
                    end
                end

                S_NEURON_TICK_START: begin
                    integration_state <= S_NEURON_TICK_WAIT;
                end

                S_NEURON_TICK_WAIT: begin
                    if (neuron_fault) begin
                        fault             <= 1'b1;
                        fault_code        <= FAULT_NEURON_BASE | neuron_fault_code;
                        integration_state <= S_IDLE;
                    end else if (neuron_tick_done) begin
                        tick_done          <= 1'b1;
                        integration_state  <= S_IDLE;
                    end
                end

                default: begin
                    fault             <= 1'b1;
                    fault_code        <= FAULT_COPY_PROTOCOL;
                    integration_state <= S_IDLE;
                end
            endcase
        end
    end

endmodule
