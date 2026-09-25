`timescale 1ns/1ps

// MNIST-09 shared runtime controller.
//
// Reuses the exact M12.3 VIO/BD port shape. capture_start selects one of the
// two frozen profiles using trace_read_addr. Trace spaces 0..6 retain the
// existing indexed-read meaning. Space 7 is reserved by this application as a
// host command that appends one external axon ID (trace_read_addr) to the next
// tick's input buffer. capture_step commits that buffered event list as one
// algorithmic tick. No expected outputs are present in this RTL.
module m12_3_multitick_capture_controller_v1 (
    input  logic         ap_clk,
    input  logic         capture_resetn,
    input  logic         capture_start,
    input  logic         capture_step,

    output logic         capture_busy,
    output logic         step_ready,
    output logic         trace_window_open,
    output logic         capture_done,
    output logic         capture_fault,
    output logic [7:0]   capture_fault_code,
    output logic [7:0]   capture_phase,

    output logic [31:0]  observed_tick,
    output logic         observed_core_fault,
    output logic [7:0]   observed_core_fault_code,
    output logic         observed_recurrent_bank,
    output logic [12:0]  observed_recurrent_count,
    output logic [12:0]  observed_recurrent_bank0_count,
    output logic [12:0]  observed_recurrent_bank1_count,
    output logic [12:0]  observed_consumed_recurrent_count,
    output logic [12:0]  observed_routed_recurrent_count,
    output logic [12:0]  observed_external_event_count,
    output logic         observed_route_target_write_seen,
    output logic [11:0]  observed_route_target_write_addr,
    output logic [15:0]  observed_route_target_write_data,
    output logic [11:0]  observed_route_target_read_addr,
    output logic [15:0]  observed_route_target_read_data,
    output logic         observed_recurrent_bank_write_seen,
    output logic         observed_recurrent_bank_write_bank,
    output logic [11:0]  observed_recurrent_bank_write_addr,
    output logic [15:0]  observed_recurrent_bank_write_data,

    input  logic         trace_read_req,
    input  logic [2:0]   trace_read_space,
    input  logic [11:0]  trace_read_addr,
    output logic         trace_read_ready,
    output logic [15:0]  trace_response_seq,
    output logic [2:0]   trace_response_space,
    output logic [11:0]  trace_response_addr,
    output logic [63:0]  trace_response_data,
    output logic         trace_response_error,

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

    `include "generated_m12_3_multitick_cases.svh"

    localparam logic [2:0] RUNTIME_APPEND_SPACE = 3'd7;
    localparam logic [7:0] FAULT_NONE          = 8'h00;
    localparam logic [7:0] FAULT_PROFILE       = 8'h20;
    localparam logic [7:0] FAULT_APPEND_STATE  = 8'h21;
    localparam logic [7:0] FAULT_APPEND_AXON   = 8'h22;
    localparam logic [7:0] FAULT_APPEND_FULL   = 8'h23;
    localparam logic [7:0] FAULT_RESET_CORE    = 8'h30;
    localparam logic [7:0] FAULT_RESET_TIMEOUT = 8'h31;
    localparam logic [7:0] FAULT_TICK_CORE     = 8'h40;
    localparam logic [7:0] FAULT_TICK_TIMEOUT  = 8'h41;
    localparam logic [23:0] WAIT_LIMIT = 24'd5_000_000;

    typedef enum logic [3:0] {
        S_IDLE,
        S_LOAD_CONFIG,
        S_LOAD_FORMAT,
        S_LOAD_SYNAPSE,
        S_LOAD_WEIGHT_ROW,
        S_LOAD_ROUTE_ROW,
        S_LOAD_ROUTE_TARGET,
        S_RESET_PULSE,
        S_RESET_WAIT,
        S_LOAD_STATE,
        S_READY,
        S_TICK_PULSE,
        S_TICK_WAIT,
        S_CAPTURE_HOLD,
        S_FAIL
    } runtime_state_t;

    runtime_state_t state;
    logic [7:0] active_profile_id;
    logic [12:0] load_index;
    logic [11:0] event_write_index;
    logic [12:0] pending_event_count;
    logic [23:0] watchdog;

    logic [1:0] reset_sync;
    logic ap_rst;
    always_ff @(posedge ap_clk or negedge capture_resetn) begin
        if (!capture_resetn)
            reset_sync <= 2'b11;
        else
            reset_sync <= {reset_sync[0], 1'b0};
    end
    assign ap_rst = reset_sync[1];

    logic capture_start_d, capture_step_d, trace_read_req_d;
    wire capture_start_pulse = capture_start && !capture_start_d;
    wire capture_step_pulse = capture_step && !capture_step_d;
    wire trace_read_req_pulse = trace_read_req && !trace_read_req_d;
    wire append_event_pulse = trace_read_req_pulse && (trace_read_space == RUNTIME_APPEND_SPACE);
    wire normal_trace_req_pulse = trace_read_req_pulse && (trace_read_space != RUNTIME_APPEND_SPACE);

    logic [8:0]  profile_neuron_count;
    logic [10:0] profile_axon_count;
    logic [12:0] profile_synapse_count;
    logic [4:0]  profile_format_count;
    logic [12:0] profile_route_count;
    always_comb begin
        profile_neuron_count  = M12_3_NEURON_COUNTS[active_profile_id];
        profile_axon_count    = M12_3_AXON_COUNTS[active_profile_id];
        profile_synapse_count = M12_3_SYNAPSE_COUNTS[active_profile_id];
        profile_format_count  = M12_3_FORMAT_COUNTS[active_profile_id];
        profile_route_count   = M12_3_ROUTE_COUNTS[active_profile_id];
    end

    logic core_reset_start, tick_start, core_busy, core_reset_done, tick_done;
    logic [31:0] core_tick;
    logic core_fault;
    logic [7:0] core_fault_code;
    logic [7:0] active_neuron;
    logic recurrent_current_bank;
    logic [12:0] recurrent_current_count, last_consumed_recurrent_count, last_routed_count;
    logic [12:0] trace_external_event_count;

    logic config_we; logic [7:0] config_addr; logic [127:0] config_wdata;
    logic state_we; logic [7:0] state_addr; logic [63:0] state_wdata;
    logic format_we; logic [3:0] format_addr; logic [15:0] format_wdata;
    logic synapse_we; logic [11:0] synapse_addr; logic [31:0] synapse_wdata;
    logic row_we; logic [10:0] row_addr; logic [31:0] row_wdata;
    logic external_we; logic [11:0] external_addr; logic [15:0] external_wdata;
    logic route_row_we; logic [8:0] route_row_addr; logic [31:0] route_row_wdata;
    logic route_target_we; logic [11:0] route_target_addr; logic [15:0] route_target_wdata;

    logic debug_re; logic [7:0] debug_addr; logic debug_rvalid;
    logic [127:0] debug_config_rdata;
    logic [63:0] debug_state_before_rdata, debug_state_rdata;
    logic signed [63:0] debug_synaptic_input_rdata, debug_accum_rdata;
    logic debug_spike_rdata;
    logic external_debug_re; logic [11:0] external_debug_addr; logic external_debug_rvalid; logic [15:0] external_debug_rdata;
    logic recurrent_debug_re, recurrent_debug_bank; logic [11:0] recurrent_debug_addr; logic recurrent_debug_rvalid; logic [15:0] recurrent_debug_rdata;
    logic [12:0] recurrent_bank0_count, recurrent_bank1_count;

    logic bridge_req_ready, bridge_rsp_valid, bridge_rsp_error;
    logic [2:0] bridge_rsp_space;
    logic [11:0] bridge_rsp_addr;
    logic [63:0] bridge_rsp_data;
    logic bridge_busy_guard;

    wire append_state_ok = (state == S_READY) || (state == S_CAPTURE_HOLD);
    wire append_valid = append_state_ok && !capture_done &&
                        (pending_event_count < 13'd4096) &&
                        (trace_read_addr < profile_axon_count);

    assign capture_busy = !((state == S_IDLE) || (state == S_READY) ||
                            (state == S_CAPTURE_HOLD) || (state == S_FAIL));
    assign step_ready = ((state == S_READY) || (state == S_CAPTURE_HOLD)) && !capture_done;
    assign trace_window_open = (state == S_CAPTURE_HOLD);
    assign capture_phase = {active_profile_id[3:0], state};
    assign observed_tick = core_tick;
    assign observed_core_fault = core_fault;
    assign observed_core_fault_code = core_fault_code;
    assign observed_recurrent_bank = recurrent_current_bank;
    assign observed_recurrent_count = recurrent_current_count;
    assign observed_recurrent_bank0_count = recurrent_bank0_count;
    assign observed_recurrent_bank1_count = recurrent_bank1_count;
    assign observed_consumed_recurrent_count = last_consumed_recurrent_count;
    assign observed_routed_recurrent_count = last_routed_count;
    assign observed_external_event_count = trace_external_event_count;

    assign bridge_busy_guard = core_busy || !trace_window_open;
    assign trace_read_ready = bridge_req_ready && trace_window_open &&
                              (trace_read_space != RUNTIME_APPEND_SPACE);

    always_comb begin
        core_reset_start = 1'b0;
        tick_start = 1'b0;
        config_we = 1'b0; config_addr = load_index[7:0]; config_wdata = 128'b0;
        state_we = 1'b0; state_addr = load_index[7:0]; state_wdata = 64'b0;
        format_we = 1'b0; format_addr = load_index[3:0]; format_wdata = 16'b0;
        synapse_we = 1'b0; synapse_addr = load_index[11:0]; synapse_wdata = 32'b0;
        row_we = 1'b0; row_addr = load_index[10:0]; row_wdata = 32'b0;
        external_we = 1'b0; external_addr = event_write_index; external_wdata = {4'b0, trace_read_addr};
        route_row_we = 1'b0; route_row_addr = load_index[8:0]; route_row_wdata = 32'b0;
        route_target_we = 1'b0; route_target_addr = load_index[11:0]; route_target_wdata = 16'b0;

        case (state)
            S_LOAD_CONFIG: begin
                config_we = 1'b1;
                config_wdata = M12_3_CONFIG_WORDS[(active_profile_id * M12_3_MAX_NEURONS) + load_index];
            end
            S_LOAD_FORMAT: begin
                format_we = 1'b1;
                format_wdata = M12_3_FORMAT_WORDS[(active_profile_id * M12_3_MAX_FORMATS) + load_index];
            end
            S_LOAD_SYNAPSE: begin
                synapse_we = 1'b1;
                synapse_wdata = M12_3_SYNAPSE_WORDS[(active_profile_id * M12_3_MAX_SYNAPSES) + load_index];
            end
            S_LOAD_WEIGHT_ROW: begin
                row_we = 1'b1;
                row_wdata = M12_3_WEIGHT_ROWS[(active_profile_id * (M12_3_MAX_AXONS + 1)) + load_index];
            end
            S_LOAD_ROUTE_ROW: begin
                route_row_we = 1'b1;
                route_row_wdata = M12_3_ROUTE_ROWS[(active_profile_id * (M12_3_MAX_NEURONS + 1)) + load_index];
            end
            S_LOAD_ROUTE_TARGET: begin
                route_target_we = 1'b1;
                route_target_wdata = M12_3_ROUTE_TARGETS[(active_profile_id * M12_3_MAX_ROUTES) + load_index];
            end
            S_RESET_PULSE: core_reset_start = 1'b1;
            S_LOAD_STATE: begin
                state_we = 1'b1;
                state_wdata = M12_3_INITIAL_STATE_WORDS[(active_profile_id * M12_3_MAX_NEURONS) + load_index];
            end
            S_TICK_PULSE: tick_start = 1'b1;
            default: begin end
        endcase
        if (append_event_pulse && append_valid) begin
            external_we = 1'b1;
            external_addr = event_write_index;
            external_wdata = {4'b0, trace_read_addr};
        end
    end

    recurrent_integrated_core_controller_v1 core_i (
        .ap_clk(ap_clk), .ap_rst(ap_rst),
        .core_reset_start(core_reset_start), .tick_start(tick_start),
        .neuron_count(profile_neuron_count), .axon_count(profile_axon_count),
        .synapse_count(profile_synapse_count), .format_count(profile_format_count),
        .external_event_count(pending_event_count), .route_count(profile_route_count),
        .busy(core_busy), .core_reset_done(core_reset_done), .tick_done(tick_done),
        .tick(core_tick), .fault(core_fault), .fault_code(core_fault_code), .active_neuron(active_neuron),
        .recurrent_current_bank(recurrent_current_bank), .recurrent_current_count(recurrent_current_count),
        .last_consumed_recurrent_count(last_consumed_recurrent_count), .last_routed_count(last_routed_count),
        .trace_external_event_count(trace_external_event_count),
        .route_target_write_seen(observed_route_target_write_seen),
        .last_route_target_write_addr(observed_route_target_write_addr),
        .last_route_target_write_data(observed_route_target_write_data),
        .last_route_target_read_addr(observed_route_target_read_addr),
        .last_route_target_read_data(observed_route_target_read_data),
        .recurrent_bank_write_seen(observed_recurrent_bank_write_seen),
        .last_recurrent_bank_write_bank(observed_recurrent_bank_write_bank),
        .last_recurrent_bank_write_addr(observed_recurrent_bank_write_addr),
        .last_recurrent_bank_write_data(observed_recurrent_bank_write_data),
        .config_we(config_we), .config_addr(config_addr), .config_wdata(config_wdata),
        .state_we(state_we), .state_addr(state_addr), .state_wdata(state_wdata),
        .format_we(format_we), .format_addr(format_addr), .format_wdata(format_wdata),
        .synapse_we(synapse_we), .synapse_addr(synapse_addr), .synapse_wdata(synapse_wdata),
        .row_we(row_we), .row_addr(row_addr), .row_wdata(row_wdata),
        .external_we(external_we), .external_addr(external_addr), .external_wdata(external_wdata),
        .route_row_we(route_row_we), .route_row_addr(route_row_addr), .route_row_wdata(route_row_wdata),
        .route_target_we(route_target_we), .route_target_addr(route_target_addr), .route_target_wdata(route_target_wdata),
        .debug_re(debug_re), .debug_addr(debug_addr), .debug_rvalid(debug_rvalid),
        .debug_config_rdata(debug_config_rdata), .debug_state_before_rdata(debug_state_before_rdata),
        .debug_state_rdata(debug_state_rdata), .debug_synaptic_input_rdata(debug_synaptic_input_rdata),
        .debug_accum_rdata(debug_accum_rdata), .debug_spike_rdata(debug_spike_rdata),
        .external_debug_re(external_debug_re), .external_debug_addr(external_debug_addr),
        .external_debug_rvalid(external_debug_rvalid), .external_debug_rdata(external_debug_rdata),
        .recurrent_debug_re(recurrent_debug_re), .recurrent_debug_bank(recurrent_debug_bank),
        .recurrent_debug_addr(recurrent_debug_addr), .recurrent_debug_rvalid(recurrent_debug_rvalid),
        .recurrent_debug_rdata(recurrent_debug_rdata), .recurrent_bank0_count(recurrent_bank0_count),
        .recurrent_bank1_count(recurrent_bank1_count),
        .hls_ap_start(hls_ap_start), .hls_ap_done(hls_ap_done), .hls_ap_idle(hls_ap_idle), .hls_ap_ready(hls_ap_ready),
        .hls_current_before(hls_current_before), .hls_voltage_before(hls_voltage_before),
        .hls_refractory_before(hls_refractory_before), .hls_synaptic_input(hls_synaptic_input),
        .hls_current_decay(hls_current_decay), .hls_voltage_decay(hls_voltage_decay),
        .hls_threshold(hls_threshold), .hls_bias(hls_bias), .hls_reset_voltage(hls_reset_voltage),
        .hls_refractory_ticks(hls_refractory_ticks), .hls_current_after(hls_current_after),
        .hls_current_after_ap_vld(hls_current_after_ap_vld), .hls_voltage_after(hls_voltage_after),
        .hls_voltage_after_ap_vld(hls_voltage_after_ap_vld), .hls_refractory_after(hls_refractory_after),
        .hls_refractory_after_ap_vld(hls_refractory_after_ap_vld), .hls_spiked(hls_spiked),
        .hls_spiked_ap_vld(hls_spiked_ap_vld)
    );

    m12_trace_read_bridge_v1 trace_bridge_i (
        .ap_clk(ap_clk), .ap_rst(ap_rst), .core_busy(bridge_busy_guard),
        .req_valid(normal_trace_req_pulse), .req_space(trace_read_space), .req_addr(trace_read_addr),
        .req_ready(bridge_req_ready), .rsp_valid(bridge_rsp_valid), .rsp_space(bridge_rsp_space),
        .rsp_addr(bridge_rsp_addr), .rsp_data(bridge_rsp_data), .rsp_error(bridge_rsp_error),
        .debug_re(debug_re), .debug_addr(debug_addr), .debug_rvalid(debug_rvalid),
        .debug_state_before_rdata(debug_state_before_rdata), .debug_state_rdata(debug_state_rdata),
        .debug_synaptic_input_rdata(debug_synaptic_input_rdata), .debug_spike_rdata(debug_spike_rdata),
        .external_debug_re(external_debug_re), .external_debug_addr(external_debug_addr),
        .external_debug_rvalid(external_debug_rvalid), .external_debug_rdata(external_debug_rdata),
        .recurrent_debug_re(recurrent_debug_re), .recurrent_debug_bank(recurrent_debug_bank),
        .recurrent_debug_addr(recurrent_debug_addr), .recurrent_debug_rvalid(recurrent_debug_rvalid),
        .recurrent_debug_rdata(recurrent_debug_rdata)
    );

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            trace_response_seq <= 16'd0; trace_response_space <= 3'd0;
            trace_response_addr <= 12'd0; trace_response_data <= 64'd0;
            trace_response_error <= 1'b0;
        end else if (bridge_rsp_valid) begin
            trace_response_seq <= trace_response_seq + 16'd1;
            trace_response_space <= bridge_rsp_space; trace_response_addr <= bridge_rsp_addr;
            trace_response_data <= bridge_rsp_data; trace_response_error <= bridge_rsp_error;
        end
    end

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            state <= S_IDLE; active_profile_id <= 8'd0;
            capture_start_d <= 1'b0; capture_step_d <= 1'b0; trace_read_req_d <= 1'b0;
            capture_done <= 1'b0; capture_fault <= 1'b0; capture_fault_code <= FAULT_NONE;
            load_index <= 13'd0; event_write_index <= 12'd0; pending_event_count <= 13'd0;
            watchdog <= 24'd0;
        end else begin
            capture_start_d <= capture_start;
            capture_step_d <= capture_step;
            trace_read_req_d <= trace_read_req;

            if (append_event_pulse) begin
                if (!append_state_ok || capture_done) begin
                    capture_fault <= 1'b1; capture_fault_code <= FAULT_APPEND_STATE; state <= S_FAIL;
                end else if (trace_read_addr >= profile_axon_count) begin
                    capture_fault <= 1'b1; capture_fault_code <= FAULT_APPEND_AXON; state <= S_FAIL;
                end else if (pending_event_count >= 13'd4096) begin
                    capture_fault <= 1'b1; capture_fault_code <= FAULT_APPEND_FULL; state <= S_FAIL;
                end else begin
                    event_write_index <= event_write_index + 12'd1;
                    pending_event_count <= pending_event_count + 13'd1;
                end
            end

            case (state)
                S_IDLE, S_CAPTURE_HOLD, S_FAIL: begin
                    if (capture_start_pulse) begin
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin
                            capture_fault <= 1'b1; capture_fault_code <= FAULT_PROFILE; state <= S_FAIL;
                        end else begin
                            active_profile_id <= trace_read_addr[7:0];
                            capture_done <= 1'b0; capture_fault <= 1'b0; capture_fault_code <= FAULT_NONE;
                            load_index <= 13'd0; event_write_index <= 12'd0; pending_event_count <= 13'd0;
                            watchdog <= 24'd0; state <= S_LOAD_CONFIG;
                        end
                    end else if ((state == S_CAPTURE_HOLD) && capture_step_pulse && !capture_done) begin
                        watchdog <= 24'd0; state <= S_TICK_PULSE;
                    end
                end
                S_LOAD_CONFIG: begin
                    if (load_index + 13'd1 >= profile_neuron_count) begin load_index <= 0; state <= S_LOAD_FORMAT; end
                    else load_index <= load_index + 1;
                end
                S_LOAD_FORMAT: begin
                    if (load_index + 13'd1 >= profile_format_count) begin load_index <= 0; state <= S_LOAD_SYNAPSE; end
                    else load_index <= load_index + 1;
                end
                S_LOAD_SYNAPSE: begin
                    if (load_index + 13'd1 >= profile_synapse_count) begin load_index <= 0; state <= S_LOAD_WEIGHT_ROW; end
                    else load_index <= load_index + 1;
                end
                S_LOAD_WEIGHT_ROW: begin
                    if (load_index >= profile_axon_count) begin load_index <= 0; state <= S_LOAD_ROUTE_ROW; end
                    else load_index <= load_index + 1;
                end
                S_LOAD_ROUTE_ROW: begin
                    if (load_index >= profile_neuron_count) begin
                        load_index <= 0;
                        if (profile_route_count == 0) state <= S_RESET_PULSE;
                        else state <= S_LOAD_ROUTE_TARGET;
                    end else load_index <= load_index + 1;
                end
                S_LOAD_ROUTE_TARGET: begin
                    if (load_index + 13'd1 >= profile_route_count) begin load_index <= 0; state <= S_RESET_PULSE; end
                    else load_index <= load_index + 1;
                end
                S_RESET_PULSE: begin watchdog <= 0; state <= S_RESET_WAIT; end
                S_RESET_WAIT: begin
                    if (core_fault) begin capture_fault <= 1; capture_fault_code <= FAULT_RESET_CORE; state <= S_FAIL; end
                    else if (core_reset_done) begin load_index <= 0; watchdog <= 0; state <= S_LOAD_STATE; end
                    else if (watchdog >= WAIT_LIMIT) begin capture_fault <= 1; capture_fault_code <= FAULT_RESET_TIMEOUT; state <= S_FAIL; end
                    else watchdog <= watchdog + 1;
                end
                S_LOAD_STATE: begin
                    if (load_index + 13'd1 >= profile_neuron_count) begin
                        load_index <= 0; event_write_index <= 0; pending_event_count <= 0; state <= S_READY;
                    end else load_index <= load_index + 1;
                end
                S_READY: begin
                    if (capture_start_pulse) begin
                        if (trace_read_addr >= M12_3_CASE_COUNT) begin capture_fault <= 1; capture_fault_code <= FAULT_PROFILE; state <= S_FAIL; end
                        else begin active_profile_id <= trace_read_addr[7:0]; load_index <= 0; event_write_index <= 0; pending_event_count <= 0; state <= S_LOAD_CONFIG; end
                    end else if (capture_step_pulse) begin watchdog <= 0; state <= S_TICK_PULSE; end
                end
                S_TICK_PULSE: begin watchdog <= 0; state <= S_TICK_WAIT; end
                S_TICK_WAIT: begin
                    if (core_fault) begin capture_fault <= 1; capture_fault_code <= FAULT_TICK_CORE; state <= S_FAIL; end
                    else if (tick_done) begin
                        capture_done <= (core_tick >= 32'd16);
                        event_write_index <= 0; pending_event_count <= 0; watchdog <= 0; state <= S_CAPTURE_HOLD;
                    end else if (watchdog >= WAIT_LIMIT) begin capture_fault <= 1; capture_fault_code <= FAULT_TICK_TIMEOUT; state <= S_FAIL; end
                    else watchdog <= watchdog + 1;
                end
                default: begin capture_fault <= 1; capture_fault_code <= 8'hff; state <= S_FAIL; end
            endcase
        end
    end
endmodule
