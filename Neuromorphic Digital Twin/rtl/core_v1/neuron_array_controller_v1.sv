`timescale 1ns/1ps

// M11.5.2 serialized multi-neuron controller.
//
// This module owns the first physical neuron state/config/accumulator memories
// and drives the already-verified neuron_step_v1 HLS IP one neuron at a time.
// Synaptic traversal is intentionally outside this boundary until M11.5.3;
// software/testbench logic may preload one signed-64 accumulator per neuron.
//
// Architectural observations are only serviced while !busy, so per-neuron
// writeback during a tick cannot expose a partially committed tick externally.
module neuron_array_controller_v1 #(
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

    // Host/testbench preload ports. Writes are accepted only while !busy.
    input  logic         config_we,
    input  logic [7:0]   config_addr,
    input  logic [127:0] config_wdata,
    input  logic         state_we,
    input  logic [7:0]   state_addr,
    input  logic [63:0]  state_wdata,
    input  logic         accum_we,
    input  logic [7:0]   accum_addr,
    input  logic signed [63:0] accum_wdata,

    // Synchronous debug read. Reads are serviced only while !busy.
    input  logic         debug_re,
    input  logic [7:0]   debug_addr,
    output logic         debug_rvalid,
    output logic [127:0] debug_config_rdata,
    output logic [63:0]  debug_state_rdata,
    output logic signed [63:0] debug_accum_rdata,
    output logic         debug_spike_rdata,

    // ap_ctrl_hs connection to neuron_step_v1.
    output logic         hls_ap_start,
    input  logic         hls_ap_done,
    input  logic         hls_ap_idle,
    input  logic         hls_ap_ready,

    // neuron_step_v1 scalar inputs.
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

    // neuron_step_v1 ap_vld outputs.
    input  logic signed [23:0] hls_current_after,
    input  logic                hls_current_after_ap_vld,
    input  logic signed [23:0] hls_voltage_after,
    input  logic                hls_voltage_after_ap_vld,
    input  logic        [15:0] hls_refractory_after,
    input  logic                hls_refractory_after_ap_vld,
    input  logic                hls_spiked,
    input  logic                hls_spiked_ap_vld
);

    localparam logic [7:0] FAULT_NONE              = 8'h00;
    localparam logic [7:0] FAULT_INVALID_COUNT     = 8'h01;
    localparam logic [7:0] FAULT_CONCURRENT_CMD    = 8'h02;
    localparam logic [7:0] FAULT_INVALID_CONFIG    = 8'h03;
    localparam logic [7:0] FAULT_MISSING_HLS_VALID = 8'h04;

    typedef enum logic [3:0] {
        S_IDLE,
        S_RESET_READ,
        S_RESET_VALIDATE,
        S_RESET_WRITE,
        S_TICK_READ,
        S_TICK_VALIDATE,
        S_HLS_WAIT_READY,
        S_HLS_WAIT_DONE,
        S_HLS_COMMIT
    } controller_state_t;

    controller_state_t controller_state;

    (* ram_style = "block" *) logic [63:0]  neuron_state_mem [0:MAX_NEURONS-1];
    (* ram_style = "block" *) logic [127:0] neuron_config_mem [0:MAX_NEURONS-1];
    (* ram_style = "block" *) logic signed [63:0] synaptic_accum_mem [0:MAX_NEURONS-1];
    (* ram_style = "distributed" *) logic spike_mem [0:MAX_NEURONS-1];

    logic [63:0]  work_state;
    logic [127:0] work_config;
    logic signed [63:0] work_accum;
    logic [8:0] active_count;

    logic signed [23:0] result_current;
    logic signed [23:0] result_voltage;
    logic        [15:0] result_refractory;
    logic               result_spiked;
    logic        [3:0]  result_valid;

    wire signed [23:0] cfg_threshold = $signed(work_config[49:26]);
    wire signed [23:0] cfg_reset_voltage = $signed(work_config[97:74]);

    wire config_valid =
        (work_config[127:114] == 14'd0) &&
        (work_config[12:0] <= 13'd4096) &&
        (work_config[25:13] <= 13'd4096) &&
        (cfg_threshold > cfg_reset_voltage);

    // ap_ctrl_hs requires ap_start to remain asserted until ap_ready. For the
    // non-pipelined M11.3 HLS block ap_ready may coincide with ap_done, so the
    // FSM also captures ap_done while still in S_HLS_WAIT_READY.
    assign hls_ap_start = (controller_state == S_HLS_WAIT_READY);

    assign hls_current_before      = $signed(work_state[23:0]);
    assign hls_voltage_before      = $signed(work_state[47:24]);
    assign hls_refractory_before   = work_state[63:48];
    assign hls_synaptic_input      = work_accum;
    assign hls_current_decay       = work_config[12:0];
    assign hls_voltage_decay       = work_config[25:13];
    assign hls_threshold           = $signed(work_config[49:26]);
    assign hls_bias                = $signed(work_config[73:50]);
    assign hls_reset_voltage       = $signed(work_config[97:74]);
    assign hls_refractory_ticks    = work_config[113:98];

    // Keep ap_idle present at the integration boundary for observability. The
    // launch handshake itself is defined entirely by ap_start/ap_ready.
    wire unused_hls_idle = hls_ap_idle;

    function automatic logic count_is_valid(input logic [8:0] count);
        count_is_valid = (count != 9'd0) && (count <= MAX_NEURONS);
    endfunction

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            controller_state     <= S_IDLE;
            busy                 <= 1'b0;
            core_reset_done      <= 1'b0;
            tick_done            <= 1'b0;
            tick                 <= 32'd0;
            fault                <= 1'b0;
            fault_code           <= FAULT_NONE;
            active_neuron        <= 8'd0;
            active_count         <= 9'd0;
            work_state           <= 64'd0;
            work_config          <= 128'd0;
            work_accum           <= 64'sd0;
            result_current       <= 24'sd0;
            result_voltage       <= 24'sd0;
            result_refractory    <= 16'd0;
            result_spiked        <= 1'b0;
            result_valid         <= 4'd0;
            debug_rvalid         <= 1'b0;
            debug_config_rdata   <= 128'd0;
            debug_state_rdata    <= 64'd0;
            debug_accum_rdata    <= 64'sd0;
            debug_spike_rdata    <= 1'b0;
        end else begin
            core_reset_done <= 1'b0;
            tick_done       <= 1'b0;
            debug_rvalid    <= 1'b0;

            // Configuration/replay writes and architectural reads occur only
            // between transactions. This prevents partial-tick observation.
            if (!busy) begin
                if (config_we)
                    neuron_config_mem[config_addr] <= config_wdata;
                if (state_we)
                    neuron_state_mem[state_addr] <= state_wdata;
                if (accum_we)
                    synaptic_accum_mem[accum_addr] <= accum_wdata;
                if (debug_re) begin
                    debug_config_rdata <= neuron_config_mem[debug_addr];
                    debug_state_rdata  <= neuron_state_mem[debug_addr];
                    debug_accum_rdata  <= synaptic_accum_mem[debug_addr];
                    debug_spike_rdata  <= spike_mem[debug_addr];
                    debug_rvalid       <= 1'b1;
                end
            end

            case (controller_state)
                S_IDLE: begin
                    busy <= 1'b0;

                    if (core_reset_start && tick_start) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_CONCURRENT_CMD;
                    end else if (core_reset_start) begin
                        if (!count_is_valid(neuron_count)) begin
                            fault      <= 1'b1;
                            fault_code <= FAULT_INVALID_COUNT;
                        end else begin
                            fault            <= 1'b0;
                            fault_code       <= FAULT_NONE;
                            busy             <= 1'b1;
                            active_count     <= neuron_count;
                            active_neuron    <= 8'd0;
                            controller_state <= S_RESET_READ;
                        end
                    end else if (tick_start) begin
                        if (!count_is_valid(neuron_count)) begin
                            fault      <= 1'b1;
                            fault_code <= FAULT_INVALID_COUNT;
                        end else begin
                            fault            <= 1'b0;
                            fault_code       <= FAULT_NONE;
                            busy             <= 1'b1;
                            active_count     <= neuron_count;
                            active_neuron    <= 8'd0;
                            controller_state <= S_TICK_READ;
                        end
                    end
                end

                S_RESET_READ: begin
                    work_config      <= neuron_config_mem[active_neuron];
                    controller_state <= S_RESET_VALIDATE;
                end

                S_RESET_VALIDATE: begin
                    if (!config_valid) begin
                        fault            <= 1'b1;
                        fault_code       <= FAULT_INVALID_CONFIG;
                        busy             <= 1'b0;
                        controller_state <= S_IDLE;
                    end else begin
                        controller_state <= S_RESET_WRITE;
                    end
                end

                S_RESET_WRITE: begin
                    neuron_state_mem[active_neuron] <= {
                        16'd0,
                        work_config[97:74],
                        24'd0
                    };
                    synaptic_accum_mem[active_neuron] <= 64'sd0;
                    spike_mem[active_neuron] <= 1'b0;

                    if (({1'b0, active_neuron} + 9'd1) >= active_count) begin
                        tick            <= 32'd0;
                        busy            <= 1'b0;
                        core_reset_done <= 1'b1;
                        controller_state <= S_IDLE;
                    end else begin
                        active_neuron    <= active_neuron + 8'd1;
                        controller_state <= S_RESET_READ;
                    end
                end

                S_TICK_READ: begin
                    work_state      <= neuron_state_mem[active_neuron];
                    work_config     <= neuron_config_mem[active_neuron];
                    work_accum      <= synaptic_accum_mem[active_neuron];
                    result_valid    <= 4'd0;
                    controller_state <= S_TICK_VALIDATE;
                end

                S_TICK_VALIDATE: begin
                    if (!config_valid) begin
                        fault            <= 1'b1;
                        fault_code       <= FAULT_INVALID_CONFIG;
                        busy             <= 1'b0;
                        controller_state <= S_IDLE;
                    end else begin
                        controller_state <= S_HLS_WAIT_READY;
                    end
                end

                S_HLS_WAIT_READY: begin
                    // hls_ap_start remains high in this state. Capture a result
                    // immediately if ap_done coincides with the ready handshake.
                    if (hls_ap_done) begin
                        result_current    <= hls_current_after;
                        result_voltage    <= hls_voltage_after;
                        result_refractory <= hls_refractory_after;
                        result_spiked     <= hls_spiked;
                        result_valid      <= {
                            hls_spiked_ap_vld,
                            hls_refractory_after_ap_vld,
                            hls_voltage_after_ap_vld,
                            hls_current_after_ap_vld
                        };
                        controller_state <= S_HLS_COMMIT;
                    end else if (hls_ap_ready) begin
                        controller_state <= S_HLS_WAIT_DONE;
                    end
                end

                S_HLS_WAIT_DONE: begin
                    if (hls_ap_done) begin
                        result_current    <= hls_current_after;
                        result_voltage    <= hls_voltage_after;
                        result_refractory <= hls_refractory_after;
                        result_spiked     <= hls_spiked;
                        result_valid      <= {
                            hls_spiked_ap_vld,
                            hls_refractory_after_ap_vld,
                            hls_voltage_after_ap_vld,
                            hls_current_after_ap_vld
                        };
                        controller_state <= S_HLS_COMMIT;
                    end
                end

                S_HLS_COMMIT: begin
                    if (result_valid != 4'b1111) begin
                        fault            <= 1'b1;
                        fault_code       <= FAULT_MISSING_HLS_VALID;
                        busy             <= 1'b0;
                        controller_state <= S_IDLE;
                    end else begin
                        neuron_state_mem[active_neuron] <= {
                            result_refractory,
                            result_voltage,
                            result_current
                        };
                        spike_mem[active_neuron] <= result_spiked;
                        synaptic_accum_mem[active_neuron] <= 64'sd0;

                        if (({1'b0, active_neuron} + 9'd1) >= active_count) begin
                            tick             <= tick + 32'd1;
                            busy             <= 1'b0;
                            tick_done        <= 1'b1;
                            controller_state <= S_IDLE;
                        end else begin
                            active_neuron    <= active_neuron + 8'd1;
                            controller_state <= S_TICK_READ;
                        end
                    end
                end

                default: begin
                    fault            <= 1'b1;
                    fault_code       <= 8'hFF;
                    busy             <= 1'b0;
                    controller_state <= S_IDLE;
                end
            endcase
        end
    end

endmodule
