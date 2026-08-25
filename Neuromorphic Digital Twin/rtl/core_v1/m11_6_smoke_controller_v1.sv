`timescale 1ns/1ps

// M11.6 physical-board smoke sequencer.
//
// This wrapper reuses the already Python-golden M11.5.4 four-tick recurrent
// chain as an autonomous FPGA self-test. A single VIO/JTAG start pulse causes
// the sequencer to preload the packed M08 memories and recurrent route CSR,
// issue architectural reset, execute four complete ticks through the real
// recurrent core + packaged HLS neuron step, and compare post-commit state,
// spikes, queue counts, and routed recurrent data with the frozen expectations.
//
// The generated include is produced from
// examples/generate_m11_5_4_integrated_vectors.py by run_m11_6_bitstream.sh.
module m11_6_smoke_controller_v1 (
    input  logic         ap_clk,
    input  logic         pl_resetn0,
    input  logic         smoke_start,

    output logic         smoke_busy,
    output logic         smoke_done,
    output logic         smoke_pass,
    output logic [7:0]   smoke_fail_code,
    output logic [7:0]   smoke_phase,
    output logic [31:0]  observed_tick,
    output logic [7:0]   observed_core_fault_code,
    output logic [63:0]  observed_state0,
    output logic [63:0]  observed_state1,
    output logic [63:0]  observed_state2,
    output logic [2:0]   observed_spikes,
    output logic         observed_recurrent_bank,
    output logic [12:0]  observed_recurrent_count,

    // Reset and scalar connection to packaged neuron_step_v1.
    output logic                hls_ap_rst,
    output logic                hls_ap_start,
    input  logic                hls_ap_done,
    input  logic                hls_ap_idle,
    input  logic                hls_ap_ready,
    output logic signed [23:0]  hls_current_before,
    output logic signed [23:0]  hls_voltage_before,
    output logic        [15:0]  hls_refractory_before,
    output logic signed [63:0]  hls_synaptic_input,
    output logic        [12:0]  hls_current_decay,
    output logic        [12:0]  hls_voltage_decay,
    output logic signed [23:0]  hls_threshold,
    output logic signed [23:0]  hls_bias,
    output logic signed [23:0]  hls_reset_voltage,
    output logic        [15:0]  hls_refractory_ticks,
    input  logic signed [23:0]  hls_current_after,
    input  logic                hls_current_after_ap_vld,
    input  logic signed [23:0]  hls_voltage_after,
    input  logic                hls_voltage_after_ap_vld,
    input  logic        [15:0]  hls_refractory_after,
    input  logic                hls_refractory_after_ap_vld,
    input  logic                hls_spiked,
    input  logic                hls_spiked_ap_vld
);

    `include "generated_m11_5_4_integrated_vectors.svh"

    localparam logic [7:0] FAIL_NONE                   = 8'h00;
    localparam logic [7:0] FAIL_RESET_CORE            = 8'h01;
    localparam logic [7:0] FAIL_RESET_TIMEOUT         = 8'h02;
    localparam logic [7:0] FAIL_RESET_STATE           = 8'h03;
    localparam logic [7:0] FAIL_TICK_CORE             = 8'h10;
    localparam logic [7:0] FAIL_TICK_TIMEOUT          = 8'h11;
    localparam logic [7:0] FAIL_TICK_COUNT            = 8'h12;
    localparam logic [7:0] FAIL_CONSUMED_COUNT        = 8'h13;
    localparam logic [7:0] FAIL_ROUTED_COUNT          = 8'h14;
    localparam logic [7:0] FAIL_CURRENT_BANK          = 8'h15;
    localparam logic [7:0] FAIL_CURRENT_COUNT         = 8'h16;
    localparam logic [7:0] FAIL_DEBUG_TIMEOUT         = 8'h20;
    localparam logic [7:0] FAIL_STATE                 = 8'h21;
    localparam logic [7:0] FAIL_SPIKE                 = 8'h22;
    localparam logic [7:0] FAIL_RECURRENT_TIMEOUT     = 8'h23;
    localparam logic [7:0] FAIL_RECURRENT_EVENT       = 8'h24;
    localparam logic [7:0] FAIL_FINAL_BANK_COUNTS     = 8'h25;

    localparam logic [23:0] WAIT_LIMIT = 24'd5_000_000;

    typedef enum logic [4:0] {
        S_IDLE,
        S_LOAD_CONFIG,
        S_LOAD_STATE,
        S_LOAD_FORMAT,
        S_LOAD_SYNAPSE,
        S_LOAD_WEIGHT_ROW,
        S_LOAD_ROUTE_ROW,
        S_LOAD_ROUTE_TARGET,
        S_RESET_PULSE,
        S_RESET_WAIT,
        S_RESET_VALIDATE,
        S_EXTERNAL_WRITE,
        S_TICK_PULSE,
        S_TICK_WAIT,
        S_TICK_VALIDATE,
        S_DEBUG_REQUEST,
        S_DEBUG_WAIT,
        S_RECURRENT_REQUEST,
        S_RECURRENT_WAIT,
        S_TICK_ADVANCE,
        S_FINAL_VALIDATE,
        S_PASS,
        S_FAIL
    } smoke_state_t;

    smoke_state_t state;

    // Active-low PS fabric reset is asynchronously asserted and synchronously
    // released into the PL clock domain. The same synchronized reset is sent to
    // the HLS IP so the complete smoke path shares one reset boundary.
    logic [1:0] reset_sync;
    logic       ap_rst;
    always_ff @(posedge ap_clk or negedge pl_resetn0) begin
        if (!pl_resetn0)
            reset_sync <= 2'b11;
        else
            reset_sync <= {reset_sync[0], 1'b0};
    end
    assign ap_rst     = reset_sync[1];
    assign hls_ap_rst = ap_rst;

    logic smoke_start_d;
    wire  smoke_start_pulse = smoke_start && !smoke_start_d;

    logic [12:0] load_index;
    logic [2:0]  tick_index;
    logic [1:0]  neuron_index;
    logic [23:0] watchdog;

    logic         core_reset_start;
    logic         tick_start;
    logic [12:0]  external_event_count;
    logic         core_busy;
    logic         core_reset_done;
    logic         tick_done;
    logic [31:0]  core_tick;
    logic         core_fault;
    logic [7:0]   core_fault_code;
    logic [7:0]   active_neuron;
    logic         recurrent_current_bank;
    logic [12:0]  recurrent_current_count;
    logic [12:0]  last_consumed_recurrent_count;
    logic [12:0]  last_routed_count;
    logic [12:0]  trace_external_event_count;

    logic         config_we;
    logic [7:0]   config_addr;
    logic [127:0] config_wdata;
    logic         state_we;
    logic [7:0]   state_addr;
    logic [63:0]  state_wdata;
    logic         format_we;
    logic [3:0]   format_addr;
    logic [15:0]  format_wdata;
    logic         synapse_we;
    logic [11:0]  synapse_addr;
    logic [31:0]  synapse_wdata;
    logic         row_we;
    logic [10:0]  row_addr;
    logic [31:0]  row_wdata;
    logic         external_we;
    logic [11:0]  external_addr;
    logic [15:0]  external_wdata;
    logic         route_row_we;
    logic [8:0]   route_row_addr;
    logic [31:0]  route_row_wdata;
    logic         route_target_we;
    logic [11:0]  route_target_addr;
    logic [15:0]  route_target_wdata;

    logic         debug_re;
    logic [7:0]   debug_addr;
    logic         debug_rvalid;
    logic [127:0] debug_config_rdata;
    logic [63:0]  debug_state_before_rdata;
    logic [63:0]  debug_state_rdata;
    logic signed [63:0] debug_synaptic_input_rdata;
    logic signed [63:0] debug_accum_rdata;
    logic         debug_spike_rdata;

    logic         external_debug_rvalid;
    logic [15:0]  external_debug_rdata;

    logic         recurrent_debug_re;
    logic         recurrent_debug_bank;
    logic [11:0]  recurrent_debug_addr;
    logic         recurrent_debug_rvalid;
    logic [15:0]  recurrent_debug_rdata;
    logic [12:0]  recurrent_bank0_count;
    logic [12:0]  recurrent_bank1_count;

    assign observed_tick            = core_tick;
    assign observed_core_fault_code = core_fault_code;
    assign observed_recurrent_bank  = recurrent_current_bank;
    assign observed_recurrent_count = recurrent_current_count;
    assign smoke_phase              = {3'b000, state};

    // Drive the complete core from the autonomous smoke sequencer. All writes
    // occur only while the core is idle.
    always_comb begin
        core_reset_start = 1'b0;
        tick_start = 1'b0;
        external_event_count = M11_5_4I_EXTERNAL_COUNTS[tick_index];

        config_we = 1'b0;
        config_addr = load_index[7:0];
        config_wdata = 128'b0;
        state_we = 1'b0;
        state_addr = load_index[7:0];
        state_wdata = 64'b0;
        format_we = 1'b0;
        format_addr = load_index[3:0];
        format_wdata = 16'b0;
        synapse_we = 1'b0;
        synapse_addr = load_index[11:0];
        synapse_wdata = 32'b0;
        row_we = 1'b0;
        row_addr = load_index[10:0];
        row_wdata = 32'b0;
        external_we = 1'b0;
        external_addr = 12'b0;
        external_wdata = M11_5_4I_EXTERNAL_EVENT0[tick_index];
        route_row_we = 1'b0;
        route_row_addr = load_index[8:0];
        route_row_wdata = 32'b0;
        route_target_we = 1'b0;
        route_target_addr = load_index[11:0];
        route_target_wdata = 16'b0;

        debug_re = 1'b0;
        debug_addr = neuron_index;
        recurrent_debug_re = 1'b0;
        recurrent_debug_bank = recurrent_current_bank;
        recurrent_debug_addr = 12'b0;

        case (state)
            S_LOAD_CONFIG: begin
                config_we = 1'b1;
                config_wdata = M11_5_4I_CONFIG_WORDS[load_index];
            end
            S_LOAD_STATE: begin
                state_we = 1'b1;
                state_wdata = M11_5_4I_INITIAL_STATE_WORDS[load_index];
            end
            S_LOAD_FORMAT: begin
                format_we = 1'b1;
                format_wdata = M11_5_4I_FORMAT_WORDS[load_index];
            end
            S_LOAD_SYNAPSE: begin
                synapse_we = 1'b1;
                synapse_wdata = M11_5_4I_SYNAPSE_WORDS[load_index];
            end
            S_LOAD_WEIGHT_ROW: begin
                row_we = 1'b1;
                row_wdata = M11_5_4I_WEIGHT_ROWS[load_index];
            end
            S_LOAD_ROUTE_ROW: begin
                route_row_we = 1'b1;
                route_row_wdata = M11_5_4I_ROUTE_ROWS[load_index];
            end
            S_LOAD_ROUTE_TARGET: begin
                route_target_we = 1'b1;
                route_target_wdata = M11_5_4I_ROUTE_TARGETS[load_index];
            end
            S_RESET_PULSE:
                core_reset_start = 1'b1;
            S_EXTERNAL_WRITE:
                external_we = 1'b1;
            S_TICK_PULSE:
                tick_start = 1'b1;
            S_DEBUG_REQUEST:
                debug_re = 1'b1;
            S_RECURRENT_REQUEST:
                recurrent_debug_re = 1'b1;
            default: begin end
        endcase
    end

    recurrent_integrated_core_controller_v1 core_i (
        .ap_clk(ap_clk),
        .ap_rst(ap_rst),
        .core_reset_start(core_reset_start),
        .tick_start(tick_start),
        .neuron_count(M11_5_4I_NEURON_COUNT[8:0]),
        .axon_count(M11_5_4I_AXON_COUNT[10:0]),
        .synapse_count(M11_5_4I_SYNAPSE_COUNT[12:0]),
        .format_count(M11_5_4I_FORMAT_COUNT[4:0]),
        .external_event_count(external_event_count),
        .route_count(M11_5_4I_ROUTE_COUNT[12:0]),
        .busy(core_busy),
        .core_reset_done(core_reset_done),
        .tick_done(tick_done),
        .tick(core_tick),
        .fault(core_fault),
        .fault_code(core_fault_code),
        .active_neuron(active_neuron),
        .recurrent_current_bank(recurrent_current_bank),
        .recurrent_current_count(recurrent_current_count),
        .last_consumed_recurrent_count(last_consumed_recurrent_count),
        .last_routed_count(last_routed_count),
        .trace_external_event_count(trace_external_event_count),
        .config_we(config_we),
        .config_addr(config_addr),
        .config_wdata(config_wdata),
        .state_we(state_we),
        .state_addr(state_addr),
        .state_wdata(state_wdata),
        .format_we(format_we),
        .format_addr(format_addr),
        .format_wdata(format_wdata),
        .synapse_we(synapse_we),
        .synapse_addr(synapse_addr),
        .synapse_wdata(synapse_wdata),
        .row_we(row_we),
        .row_addr(row_addr),
        .row_wdata(row_wdata),
        .external_we(external_we),
        .external_addr(external_addr),
        .external_wdata(external_wdata),
        .route_row_we(route_row_we),
        .route_row_addr(route_row_addr),
        .route_row_wdata(route_row_wdata),
        .route_target_we(route_target_we),
        .route_target_addr(route_target_addr),
        .route_target_wdata(route_target_wdata),
        .debug_re(debug_re),
        .debug_addr(debug_addr),
        .debug_rvalid(debug_rvalid),
        .debug_config_rdata(debug_config_rdata),
        .debug_state_before_rdata(debug_state_before_rdata),
        .debug_state_rdata(debug_state_rdata),
        .debug_synaptic_input_rdata(debug_synaptic_input_rdata),
        .debug_accum_rdata(debug_accum_rdata),
        .debug_spike_rdata(debug_spike_rdata),
        .external_debug_re(1'b0),
        .external_debug_addr(12'b0),
        .external_debug_rvalid(external_debug_rvalid),
        .external_debug_rdata(external_debug_rdata),
        .recurrent_debug_re(recurrent_debug_re),
        .recurrent_debug_bank(recurrent_debug_bank),
        .recurrent_debug_addr(recurrent_debug_addr),
        .recurrent_debug_rvalid(recurrent_debug_rvalid),
        .recurrent_debug_rdata(recurrent_debug_rdata),
        .recurrent_bank0_count(recurrent_bank0_count),
        .recurrent_bank1_count(recurrent_bank1_count),
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

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            state <= S_IDLE;
            smoke_start_d <= 1'b0;
            smoke_busy <= 1'b0;
            smoke_done <= 1'b0;
            smoke_pass <= 1'b0;
            smoke_fail_code <= FAIL_NONE;
            load_index <= 13'b0;
            tick_index <= 3'b0;
            neuron_index <= 2'b0;
            watchdog <= 24'b0;
            observed_state0 <= 64'b0;
            observed_state1 <= 64'b0;
            observed_state2 <= 64'b0;
            observed_spikes <= 3'b0;
        end else begin
            smoke_start_d <= smoke_start;

            case (state)
                S_IDLE: begin
                    smoke_busy <= 1'b0;
                    if (smoke_start_pulse) begin
                        smoke_busy <= 1'b1;
                        smoke_done <= 1'b0;
                        smoke_pass <= 1'b0;
                        smoke_fail_code <= FAIL_NONE;
                        load_index <= 13'b0;
                        tick_index <= 3'b0;
                        neuron_index <= 2'b0;
                        watchdog <= 24'b0;
                        observed_state0 <= 64'b0;
                        observed_state1 <= 64'b0;
                        observed_state2 <= 64'b0;
                        observed_spikes <= 3'b0;
                        state <= S_LOAD_CONFIG;
                    end
                end

                S_LOAD_CONFIG: begin
                    if (load_index + 1 >= M11_5_4I_NEURON_COUNT) begin
                        load_index <= 13'b0;
                        state <= S_LOAD_STATE;
                    end else
                        load_index <= load_index + 1'b1;
                end

                S_LOAD_STATE: begin
                    if (load_index + 1 >= M11_5_4I_NEURON_COUNT) begin
                        load_index <= 13'b0;
                        state <= S_LOAD_FORMAT;
                    end else
                        load_index <= load_index + 1'b1;
                end

                S_LOAD_FORMAT: begin
                    if (load_index + 1 >= M11_5_4I_FORMAT_COUNT) begin
                        load_index <= 13'b0;
                        state <= S_LOAD_SYNAPSE;
                    end else
                        load_index <= load_index + 1'b1;
                end

                S_LOAD_SYNAPSE: begin
                    if (load_index + 1 >= M11_5_4I_SYNAPSE_COUNT) begin
                        load_index <= 13'b0;
                        state <= S_LOAD_WEIGHT_ROW;
                    end else
                        load_index <= load_index + 1'b1;
                end

                S_LOAD_WEIGHT_ROW: begin
                    if (load_index >= M11_5_4I_AXON_COUNT) begin
                        load_index <= 13'b0;
                        state <= S_LOAD_ROUTE_ROW;
                    end else
                        load_index <= load_index + 1'b1;
                end

                S_LOAD_ROUTE_ROW: begin
                    if (load_index >= M11_5_4I_NEURON_COUNT) begin
                        load_index <= 13'b0;
                        state <= S_LOAD_ROUTE_TARGET;
                    end else
                        load_index <= load_index + 1'b1;
                end

                S_LOAD_ROUTE_TARGET: begin
                    if (load_index + 1 >= M11_5_4I_ROUTE_COUNT) begin
                        load_index <= 13'b0;
                        watchdog <= 24'b0;
                        state <= S_RESET_PULSE;
                    end else
                        load_index <= load_index + 1'b1;
                end

                S_RESET_PULSE: begin
                    watchdog <= 24'b0;
                    state <= S_RESET_WAIT;
                end

                S_RESET_WAIT: begin
                    if (core_fault) begin
                        smoke_fail_code <= FAIL_RESET_CORE;
                        state <= S_FAIL;
                    end else if (core_reset_done) begin
                        watchdog <= 24'b0;
                        state <= S_RESET_VALIDATE;
                    end else if (watchdog >= WAIT_LIMIT) begin
                        smoke_fail_code <= FAIL_RESET_TIMEOUT;
                        state <= S_FAIL;
                    end else
                        watchdog <= watchdog + 1'b1;
                end

                S_RESET_VALIDATE: begin
                    if ((core_tick != 0) || (recurrent_current_bank != 0) ||
                        (recurrent_current_count != 0)) begin
                        smoke_fail_code <= FAIL_RESET_STATE;
                        state <= S_FAIL;
                    end else if (M11_5_4I_EXTERNAL_COUNTS[tick_index] != 0) begin
                        state <= S_EXTERNAL_WRITE;
                    end else begin
                        watchdog <= 24'b0;
                        state <= S_TICK_PULSE;
                    end
                end

                S_EXTERNAL_WRITE: begin
                    watchdog <= 24'b0;
                    state <= S_TICK_PULSE;
                end

                S_TICK_PULSE: begin
                    watchdog <= 24'b0;
                    state <= S_TICK_WAIT;
                end

                S_TICK_WAIT: begin
                    if (core_fault) begin
                        smoke_fail_code <= FAIL_TICK_CORE;
                        state <= S_FAIL;
                    end else if (tick_done) begin
                        watchdog <= 24'b0;
                        state <= S_TICK_VALIDATE;
                    end else if (watchdog >= WAIT_LIMIT) begin
                        smoke_fail_code <= FAIL_TICK_TIMEOUT;
                        state <= S_FAIL;
                    end else
                        watchdog <= watchdog + 1'b1;
                end

                S_TICK_VALIDATE: begin
                    if (core_tick != (tick_index + 1'b1)) begin
                        smoke_fail_code <= FAIL_TICK_COUNT;
                        state <= S_FAIL;
                    end else if (last_consumed_recurrent_count !=
                                 M11_5_4I_EXPECTED_CONSUMED_COUNTS[tick_index]) begin
                        smoke_fail_code <= FAIL_CONSUMED_COUNT;
                        state <= S_FAIL;
                    end else if (last_routed_count !=
                                 M11_5_4I_EXPECTED_ROUTED_COUNTS[tick_index]) begin
                        smoke_fail_code <= FAIL_ROUTED_COUNT;
                        state <= S_FAIL;
                    end else if (recurrent_current_bank !=
                                 M11_5_4I_EXPECTED_CURRENT_BANK[tick_index]) begin
                        smoke_fail_code <= FAIL_CURRENT_BANK;
                        state <= S_FAIL;
                    end else if (recurrent_current_count !=
                                 M11_5_4I_EXPECTED_CURRENT_COUNTS[tick_index]) begin
                        smoke_fail_code <= FAIL_CURRENT_COUNT;
                        state <= S_FAIL;
                    end else begin
                        neuron_index <= 2'b0;
                        observed_spikes <= 3'b0;
                        watchdog <= 24'b0;
                        state <= S_DEBUG_REQUEST;
                    end
                end

                S_DEBUG_REQUEST: begin
                    watchdog <= 24'b0;
                    state <= S_DEBUG_WAIT;
                end

                S_DEBUG_WAIT: begin
                    if (debug_rvalid) begin
                        watchdog <= 24'b0;
                        if (debug_state_rdata !=
                            M11_5_4I_EXPECTED_STATES[(tick_index * M11_5_4I_NEURON_COUNT) + neuron_index]) begin
                            smoke_fail_code <= FAIL_STATE;
                            state <= S_FAIL;
                        end else if (debug_spike_rdata !=
                                     M11_5_4I_EXPECTED_SPIKES[(tick_index * M11_5_4I_NEURON_COUNT) + neuron_index]) begin
                            smoke_fail_code <= FAIL_SPIKE;
                            state <= S_FAIL;
                        end else begin
                            case (neuron_index)
                                0: observed_state0 <= debug_state_rdata;
                                1: observed_state1 <= debug_state_rdata;
                                2: observed_state2 <= debug_state_rdata;
                                default: begin end
                            endcase
                            observed_spikes[neuron_index] <= debug_spike_rdata;

                            if (neuron_index + 1 >= M11_5_4I_NEURON_COUNT) begin
                                if (M11_5_4I_EXPECTED_CURRENT_COUNTS[tick_index] != 0)
                                    state <= S_RECURRENT_REQUEST;
                                else
                                    state <= S_TICK_ADVANCE;
                            end else begin
                                neuron_index <= neuron_index + 1'b1;
                                state <= S_DEBUG_REQUEST;
                            end
                        end
                    end else if (watchdog >= WAIT_LIMIT) begin
                        smoke_fail_code <= FAIL_DEBUG_TIMEOUT;
                        state <= S_FAIL;
                    end else
                        watchdog <= watchdog + 1'b1;
                end

                S_RECURRENT_REQUEST: begin
                    watchdog <= 24'b0;
                    state <= S_RECURRENT_WAIT;
                end

                S_RECURRENT_WAIT: begin
                    if (recurrent_debug_rvalid) begin
                        watchdog <= 24'b0;
                        if (recurrent_debug_rdata !=
                            M11_5_4I_EXPECTED_CURRENT_EVENT0[tick_index]) begin
                            smoke_fail_code <= FAIL_RECURRENT_EVENT;
                            state <= S_FAIL;
                        end else
                            state <= S_TICK_ADVANCE;
                    end else if (watchdog >= WAIT_LIMIT) begin
                        smoke_fail_code <= FAIL_RECURRENT_TIMEOUT;
                        state <= S_FAIL;
                    end else
                        watchdog <= watchdog + 1'b1;
                end

                S_TICK_ADVANCE: begin
                    if (tick_index + 1 >= M11_5_4I_TICK_COUNT) begin
                        state <= S_FINAL_VALIDATE;
                    end else begin
                        tick_index <= tick_index + 1'b1;
                        if (M11_5_4I_EXTERNAL_COUNTS[tick_index + 1'b1] != 0)
                            state <= S_EXTERNAL_WRITE;
                        else begin
                            watchdog <= 24'b0;
                            state <= S_TICK_PULSE;
                        end
                    end
                end

                S_FINAL_VALIDATE: begin
                    if ((recurrent_bank0_count != 0) || (recurrent_bank1_count != 0)) begin
                        smoke_fail_code <= FAIL_FINAL_BANK_COUNTS;
                        state <= S_FAIL;
                    end else
                        state <= S_PASS;
                end

                S_PASS: begin
                    smoke_busy <= 1'b0;
                    smoke_done <= 1'b1;
                    smoke_pass <= 1'b1;
                    smoke_fail_code <= FAIL_NONE;
                    state <= S_IDLE;
                end

                S_FAIL: begin
                    smoke_busy <= 1'b0;
                    smoke_done <= 1'b1;
                    smoke_pass <= 1'b0;
                    state <= S_IDLE;
                end

                default: begin
                    smoke_fail_code <= 8'hFF;
                    state <= S_FAIL;
                end
            endcase
        end
    end

endmodule
