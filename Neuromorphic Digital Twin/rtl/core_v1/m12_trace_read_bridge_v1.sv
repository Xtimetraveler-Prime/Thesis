`timescale 1ns/1ps

// M12.1.2 indexed, read-only physical trace bridge.
//
// The behaviorally complete recurrent core already exposes three independent
// debug read ports:
//   * per-neuron post-tick trace/state fields,
//   * external events consumed by the completed tick,
//   * either recurrent queue bank.
//
// This bridge gives the host one stable request/response namespace without
// adding any computational write path. Requests are accepted only while the
// recurrent core is idle. The numeric read-space values are frozen by
// neuromorphic_twin.fpga_physical_trace.FpgaTraceReadSpace.
module m12_trace_read_bridge_v1 (
    input  logic         ap_clk,
    input  logic         ap_rst,
    input  logic         core_busy,

    input  logic         req_valid,
    input  logic [2:0]   req_space,
    input  logic [11:0]  req_addr,
    output logic         req_ready,

    output logic         rsp_valid,
    output logic [2:0]   rsp_space,
    output logic [11:0]  rsp_addr,
    output logic [63:0]  rsp_data,
    output logic         rsp_error,

    // Existing per-neuron trace/debug interface.
    output logic         debug_re,
    output logic [7:0]   debug_addr,
    input  logic         debug_rvalid,
    input  logic [63:0]  debug_state_before_rdata,
    input  logic [63:0]  debug_state_rdata,
    input  logic signed [63:0] debug_synaptic_input_rdata,
    input  logic         debug_spike_rdata,

    // Existing completed-tick external-event trace interface.
    output logic         external_debug_re,
    output logic [11:0]  external_debug_addr,
    input  logic         external_debug_rvalid,
    input  logic [15:0]  external_debug_rdata,

    // Existing recurrent queue-bank debug interface.
    output logic         recurrent_debug_re,
    output logic         recurrent_debug_bank,
    output logic [11:0]  recurrent_debug_addr,
    input  logic         recurrent_debug_rvalid,
    input  logic [15:0]  recurrent_debug_rdata
);

    localparam logic [2:0] TRACE_SPACE_STATE_BEFORE          = 3'd0;
    localparam logic [2:0] TRACE_SPACE_STATE_AFTER           = 3'd1;
    localparam logic [2:0] TRACE_SPACE_SYNAPTIC_INPUT        = 3'd2;
    localparam logic [2:0] TRACE_SPACE_SPIKE                 = 3'd3;
    localparam logic [2:0] TRACE_SPACE_EXTERNAL_EVENT        = 3'd4;
    localparam logic [2:0] TRACE_SPACE_RECURRENT_BANK0_EVENT = 3'd5;
    localparam logic [2:0] TRACE_SPACE_RECURRENT_BANK1_EVENT = 3'd6;

    logic        pending;
    logic [2:0]  pending_space;
    logic [11:0] pending_addr;

    logic request_space_valid;
    logic request_is_neuron_space;
    logic request_addr_valid;
    logic request_fire;
    logic pending_response_valid;
    logic [63:0] pending_response_data;

    always_comb begin
        request_space_valid = 1'b1;
        case (req_space)
            TRACE_SPACE_STATE_BEFORE,
            TRACE_SPACE_STATE_AFTER,
            TRACE_SPACE_SYNAPTIC_INPUT,
            TRACE_SPACE_SPIKE,
            TRACE_SPACE_EXTERNAL_EVENT,
            TRACE_SPACE_RECURRENT_BANK0_EVENT,
            TRACE_SPACE_RECURRENT_BANK1_EVENT: begin end
            default: request_space_valid = 1'b0;
        endcase

        request_is_neuron_space =
            (req_space == TRACE_SPACE_STATE_BEFORE) ||
            (req_space == TRACE_SPACE_STATE_AFTER) ||
            (req_space == TRACE_SPACE_SYNAPTIC_INPUT) ||
            (req_space == TRACE_SPACE_SPIKE);

        // Neuron trace memories are physically 256 deep and have an 8-bit
        // address port. Reject upper address bits instead of silently aliasing.
        request_addr_valid = !request_is_neuron_space || (req_addr[11:8] == 4'b0000);
    end

    assign req_ready = !pending && !core_busy;
    assign request_fire = req_valid && req_ready;

    // Requests drive exactly one existing read port for one cycle. There is no
    // write signal in this module; the bridge cannot alter architectural state.
    always_comb begin
        debug_re             = 1'b0;
        debug_addr           = req_addr[7:0];
        external_debug_re    = 1'b0;
        external_debug_addr  = req_addr;
        recurrent_debug_re   = 1'b0;
        recurrent_debug_bank = 1'b0;
        recurrent_debug_addr = req_addr;

        if (request_fire && request_space_valid && request_addr_valid) begin
            case (req_space)
                TRACE_SPACE_STATE_BEFORE,
                TRACE_SPACE_STATE_AFTER,
                TRACE_SPACE_SYNAPTIC_INPUT,
                TRACE_SPACE_SPIKE: begin
                    debug_re = 1'b1;
                end
                TRACE_SPACE_EXTERNAL_EVENT: begin
                    external_debug_re = 1'b1;
                end
                TRACE_SPACE_RECURRENT_BANK0_EVENT: begin
                    recurrent_debug_re   = 1'b1;
                    recurrent_debug_bank = 1'b0;
                end
                TRACE_SPACE_RECURRENT_BANK1_EVENT: begin
                    recurrent_debug_re   = 1'b1;
                    recurrent_debug_bank = 1'b1;
                end
                default: begin end
            endcase
        end
    end

    // Select the response only from the interface associated with the latched
    // request. Smaller fields are zero-extended into the common 64-bit payload.
    always_comb begin
        pending_response_valid = 1'b0;
        pending_response_data  = 64'b0;
        case (pending_space)
            TRACE_SPACE_STATE_BEFORE: begin
                pending_response_valid = debug_rvalid;
                pending_response_data  = debug_state_before_rdata;
            end
            TRACE_SPACE_STATE_AFTER: begin
                pending_response_valid = debug_rvalid;
                pending_response_data  = debug_state_rdata;
            end
            TRACE_SPACE_SYNAPTIC_INPUT: begin
                pending_response_valid = debug_rvalid;
                pending_response_data  = debug_synaptic_input_rdata;
            end
            TRACE_SPACE_SPIKE: begin
                pending_response_valid = debug_rvalid;
                pending_response_data  = {63'b0, debug_spike_rdata};
            end
            TRACE_SPACE_EXTERNAL_EVENT: begin
                pending_response_valid = external_debug_rvalid;
                pending_response_data  = {48'b0, external_debug_rdata};
            end
            TRACE_SPACE_RECURRENT_BANK0_EVENT,
            TRACE_SPACE_RECURRENT_BANK1_EVENT: begin
                pending_response_valid = recurrent_debug_rvalid;
                pending_response_data  = {48'b0, recurrent_debug_rdata};
            end
            default: begin end
        endcase
    end

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            pending       <= 1'b0;
            pending_space <= 3'b0;
            pending_addr  <= 12'b0;
            rsp_valid     <= 1'b0;
            rsp_space     <= 3'b0;
            rsp_addr      <= 12'b0;
            rsp_data      <= 64'b0;
            rsp_error     <= 1'b0;
        end else begin
            // Responses are single-cycle pulses. rsp_* payload fields remain
            // stable until the next response so VIO can inspect them safely.
            rsp_valid <= 1'b0;

            if (pending) begin
                // A trace request is defined only for an idle architectural
                // observation window. If execution begins before the backing
                // debug port answers, abort rather than returning mixed-tick data.
                if (core_busy) begin
                    pending   <= 1'b0;
                    rsp_valid <= 1'b1;
                    rsp_space <= pending_space;
                    rsp_addr  <= pending_addr;
                    rsp_data  <= 64'b0;
                    rsp_error <= 1'b1;
                end else if (pending_response_valid) begin
                    pending   <= 1'b0;
                    rsp_valid <= 1'b1;
                    rsp_space <= pending_space;
                    rsp_addr  <= pending_addr;
                    rsp_data  <= pending_response_data;
                    rsp_error <= 1'b0;
                end
            end

            if (request_fire) begin
                rsp_space <= req_space;
                rsp_addr  <= req_addr;
                if (!request_space_valid || !request_addr_valid) begin
                    // Invalid selectors and aliased neuron addresses are
                    // rejected locally without touching a backing debug port.
                    pending   <= 1'b0;
                    rsp_valid <= 1'b1;
                    rsp_data  <= 64'b0;
                    rsp_error <= 1'b1;
                end else begin
                    pending       <= 1'b1;
                    pending_space <= req_space;
                    pending_addr  <= req_addr;
                end
            end
        end
    end

endmodule
