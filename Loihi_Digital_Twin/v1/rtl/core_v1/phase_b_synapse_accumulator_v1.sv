`timescale 1ns/1ps

// M11.5.3 standalone Phase-B engine.
//
// The engine consumes external events first, then recurrent events, traverses
// the frozen M08 axon-row CSR image, reconstructs each effective weight with
// m08_weight_decoder_v1, and produces one exact signed-64 accumulator per
// configured neuron. It is intentionally serialized for traceability.
//
// M11.5.5 keeps the large event/accumulator arrays on canonical synchronous
// single-clock RAM access patterns so Vivado can map them into dedicated block
// RAM rather than building deep LUT read muxes. The extra S_ACCUM_READ cycle is
// an implementation timing detail and does not change the algorithmic tick.
module phase_b_synapse_accumulator_v1 #(
    parameter integer MAX_NEURONS  = 256,
    parameter integer MAX_AXONS    = 1024,
    parameter integer MAX_SYNAPSES = 4096,
    parameter integer MAX_FORMATS  = 16,
    parameter integer MAX_EVENTS   = 4096
) (
    input  logic         ap_clk,
    input  logic         ap_rst,
    input  logic         start,

    input  logic [8:0]   neuron_count,
    input  logic [10:0]  axon_count,
    input  logic [12:0]  synapse_count,
    input  logic [4:0]   format_count,
    input  logic [12:0]  external_event_count,
    input  logic [12:0]  recurrent_event_count,

    output logic         busy,
    output logic         done,
    output logic         fault,
    output logic [7:0]   fault_code,
    output logic         active_source,
    output logic [12:0]  active_event_index,
    output logic [31:0]  active_synapse_index,

    // Configuration/image preload ports. Writes are accepted only while idle.
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

    input  logic         debug_accum_re,
    input  logic [7:0]   debug_accum_addr,
    output logic         debug_accum_rvalid,
    output logic signed [63:0] debug_accum_rdata,

    // M11.5.5 idle-only readback of the actual external-event buffer consumed
    // by Phase B. This is trace-only and never feeds the datapath.
    input  logic         debug_external_re,
    input  logic [11:0]  debug_external_addr,
    output logic         debug_external_rvalid,
    output logic [15:0]  debug_external_rdata
);

    localparam logic [7:0] FAULT_NONE           = 8'h00;
    localparam logic [7:0] FAULT_INVALID_COUNT  = 8'h01;
    localparam logic [7:0] FAULT_EVENT_AXON     = 8'h02;
    localparam logic [7:0] FAULT_ROW_POINTER    = 8'h03;
    localparam logic [7:0] FAULT_FORMAT_INDEX   = 8'h04;
    localparam logic [7:0] FAULT_TARGET_NEURON  = 8'h05;
    localparam logic [7:0] FAULT_WEIGHT_WORD    = 8'h06;
    localparam logic [7:0] FAULT_ACCUM_OVERFLOW = 8'h07;

    typedef enum logic [3:0] {
        S_IDLE,
        S_CLEAR,
        S_EVENT_LOAD,
        S_EVENT_VALIDATE,
        S_ROW_VALIDATE,
        S_SYN_READ,
        S_SYN_VALIDATE,
        S_ACCUM_READ,
        S_ACCUMULATE,
        S_EVENT_ADVANCE
    } phase_b_state_t;

    phase_b_state_t state;

    (* ram_style = "distributed" *) logic [15:0] format_mem [0:MAX_FORMATS-1];
    (* ram_style = "block" *) logic [31:0] synapse_mem [0:MAX_SYNAPSES-1];
    (* ram_style = "block" *) logic [31:0] axon_row_mem [0:MAX_AXONS];
    (* ram_style = "block" *) logic [15:0] external_event_mem [0:MAX_EVENTS-1];
    (* ram_style = "block" *) logic [15:0] recurrent_event_mem [0:MAX_EVENTS-1];
    (* ram_style = "block" *) logic signed [63:0] accumulator_mem [0:MAX_NEURONS-1];

    logic [8:0]  latched_neuron_count;
    logic [10:0] latched_axon_count;
    logic [12:0] latched_synapse_count;
    logic [4:0]  latched_format_count;
    logic [12:0] latched_external_count;
    logic [12:0] latched_recurrent_count;

    logic [7:0]  clear_index;
    logic [31:0] row_start;
    logic [31:0] row_stop;
    logic [31:0] work_synapse;
    logic [15:0] work_format;

    // Canonical synchronous RAM port controls for memories that previously
    // synthesized into LUT fabric. Each array is touched by exactly one RAM
    // process; host/runtime/debug accesses are multiplexed onto that port.
    logic        external_mem_we;
    logic [11:0] external_mem_waddr;
    logic [15:0] external_mem_wdata;
    logic        external_mem_re;
    logic [11:0] external_mem_raddr;
    logic [15:0] external_mem_rdata;

    logic        recurrent_mem_we;
    logic [11:0] recurrent_mem_waddr;
    logic [15:0] recurrent_mem_wdata;
    logic        recurrent_mem_re;
    logic [11:0] recurrent_mem_raddr;
    logic [15:0] recurrent_mem_rdata;

    logic               accumulator_mem_we;
    logic [7:0]         accumulator_mem_waddr;
    logic signed [63:0] accumulator_mem_wdata;
    logic               accumulator_mem_re;
    logic [7:0]         accumulator_mem_raddr;
    logic signed [63:0] accumulator_mem_rdata;

    logic               decoded_valid;
    logic [7:0]         decoded_fault_code;
    logic [15:0]        decoded_target;
    logic [3:0]         decoded_format_index;
    logic signed [8:0]  decoded_mantissa;
    logic signed [31:0] decoded_weight;

    wire [7:0] target_index = decoded_target[7:0];
    wire signed [63:0] decoded_weight_64 = {{32{decoded_weight[31]}}, decoded_weight};
    wire signed [63:0] accumulator_sum = accumulator_mem_rdata + decoded_weight_64;
    wire accumulator_overflow =
        (accumulator_mem_rdata[63] == decoded_weight_64[63]) &&
        (accumulator_sum[63] != accumulator_mem_rdata[63]);
    wire [15:0] current_event_axon = active_source
        ? recurrent_mem_rdata
        : external_mem_rdata;

    m08_weight_decoder_v1 decoder_i (
        .format_word(work_format),
        .synapse_word(work_synapse),
        .valid(decoded_valid),
        .fault_code(decoded_fault_code),
        .target_neuron(decoded_target),
        .format_index(decoded_format_index),
        .requested_mantissa(decoded_mantissa),
        .effective_weight(decoded_weight)
    );

    wire unused_decoder_fields = ^{decoded_fault_code, decoded_format_index, decoded_mantissa};

    function automatic logic counts_valid;
        counts_valid =
            (neuron_count != 9'd0) &&
            (neuron_count <= MAX_NEURONS) &&
            (axon_count <= MAX_AXONS) &&
            (synapse_count <= MAX_SYNAPSES) &&
            (format_count <= MAX_FORMATS) &&
            (external_event_count <= MAX_EVENTS) &&
            (recurrent_event_count <= MAX_EVENTS);
    endfunction

    // External-event RAM: one synchronous read port plus one synchronous write
    // port on the same clock. Runtime reads have priority over idle trace reads.
    always_comb begin
        external_mem_we    = (!busy) && external_we;
        external_mem_waddr = external_addr;
        external_mem_wdata = external_wdata;
        external_mem_re    = 1'b0;
        external_mem_raddr = 12'd0;

        if ((state == S_EVENT_LOAD) && !active_source) begin
            external_mem_re    = 1'b1;
            external_mem_raddr = active_event_index[11:0];
        end else if ((!busy) && debug_external_re) begin
            external_mem_re    = 1'b1;
            external_mem_raddr = debug_external_addr;
        end
    end

    always_ff @(posedge ap_clk) begin
        if (external_mem_we)
            external_event_mem[external_mem_waddr] <= external_mem_wdata;
        if (external_mem_re)
            external_mem_rdata <= external_event_mem[external_mem_raddr];
    end

    // Recurrent-event RAM is loaded by the integration controller while Phase B
    // is idle and read synchronously while recurrent events are consumed.
    always_comb begin
        recurrent_mem_we    = (!busy) && recurrent_we;
        recurrent_mem_waddr = recurrent_addr;
        recurrent_mem_wdata = recurrent_wdata;
        recurrent_mem_re    = (state == S_EVENT_LOAD) && active_source;
        recurrent_mem_raddr = active_event_index[11:0];
    end

    always_ff @(posedge ap_clk) begin
        if (recurrent_mem_we)
            recurrent_event_mem[recurrent_mem_waddr] <= recurrent_mem_wdata;
        if (recurrent_mem_re)
            recurrent_mem_rdata <= recurrent_event_mem[recurrent_mem_raddr];
    end

    // Accumulator RAM is synchronous on both accesses. S_ACCUM_READ requests
    // the existing target value; S_ACCUMULATE consumes that registered value on
    // the following cycle. This is the block-RAM-compatible replacement for the
    // previous asynchronous array read.
    always_comb begin
        accumulator_mem_we    = 1'b0;
        accumulator_mem_waddr = 8'd0;
        accumulator_mem_wdata = 64'sd0;
        accumulator_mem_re    = 1'b0;
        accumulator_mem_raddr = 8'd0;

        if (state == S_CLEAR) begin
            accumulator_mem_we    = 1'b1;
            accumulator_mem_waddr = clear_index;
            accumulator_mem_wdata = 64'sd0;
        end else if ((state == S_ACCUMULATE) && decoded_valid && !accumulator_overflow) begin
            accumulator_mem_we    = 1'b1;
            accumulator_mem_waddr = target_index;
            accumulator_mem_wdata = accumulator_sum;
        end

        if (state == S_ACCUM_READ) begin
            accumulator_mem_re    = 1'b1;
            accumulator_mem_raddr = target_index;
        end else if ((!busy) && debug_accum_re) begin
            accumulator_mem_re    = 1'b1;
            accumulator_mem_raddr = debug_accum_addr;
        end
    end

    always_ff @(posedge ap_clk) begin
        if (accumulator_mem_we)
            accumulator_mem[accumulator_mem_waddr] <= accumulator_mem_wdata;
        if (accumulator_mem_re)
            accumulator_mem_rdata <= accumulator_mem[accumulator_mem_raddr];
    end

    assign debug_accum_rdata = accumulator_mem_rdata;
    assign debug_external_rdata = external_mem_rdata;

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            state                   <= S_IDLE;
            busy                    <= 1'b0;
            done                    <= 1'b0;
            fault                   <= 1'b0;
            fault_code              <= FAULT_NONE;
            active_source           <= 1'b0;
            active_event_index      <= 13'd0;
            active_synapse_index    <= 32'd0;
            latched_neuron_count    <= 9'd0;
            latched_axon_count      <= 11'd0;
            latched_synapse_count   <= 13'd0;
            latched_format_count    <= 5'd0;
            latched_external_count  <= 13'd0;
            latched_recurrent_count <= 13'd0;
            clear_index             <= 8'd0;
            row_start               <= 32'd0;
            row_stop                <= 32'd0;
            work_synapse            <= 32'd0;
            work_format             <= 16'd0;
            debug_accum_rvalid      <= 1'b0;
            debug_external_rvalid   <= 1'b0;
        end else begin
            done                    <= 1'b0;
            debug_accum_rvalid      <= 1'b0;
            debug_external_rvalid   <= 1'b0;

            if ((!busy) && debug_accum_re)
                debug_accum_rvalid <= 1'b1;
            if ((!busy) && debug_external_re)
                debug_external_rvalid <= 1'b1;

            // Small/static image memories keep their already-verified access
            // patterns. The large event/accumulator RAMs are owned above.
            if (!busy) begin
                if (format_we)
                    format_mem[format_addr] <= format_wdata;
                if (synapse_we)
                    synapse_mem[synapse_addr] <= synapse_wdata;
                if (row_we)
                    axon_row_mem[row_addr] <= row_wdata;
            end

            case (state)
                S_IDLE: begin
                    busy <= 1'b0;
                    if (start) begin
                        if (!counts_valid()) begin
                            fault      <= 1'b1;
                            fault_code <= FAULT_INVALID_COUNT;
                        end else begin
                            fault                   <= 1'b0;
                            fault_code              <= FAULT_NONE;
                            busy                    <= 1'b1;
                            latched_neuron_count    <= neuron_count;
                            latched_axon_count      <= axon_count;
                            latched_synapse_count   <= synapse_count;
                            latched_format_count    <= format_count;
                            latched_external_count  <= external_event_count;
                            latched_recurrent_count <= recurrent_event_count;
                            clear_index             <= 8'd0;
                            active_source           <= 1'b0;
                            active_event_index      <= 13'd0;
                            active_synapse_index    <= 32'd0;
                            state                   <= S_CLEAR;
                        end
                    end
                end

                S_CLEAR: begin
                    if (({1'b0, clear_index} + 9'd1) >= latched_neuron_count) begin
                        if (latched_external_count != 13'd0) begin
                            active_source      <= 1'b0;
                            active_event_index <= 13'd0;
                            state              <= S_EVENT_LOAD;
                        end else if (latched_recurrent_count != 13'd0) begin
                            active_source      <= 1'b1;
                            active_event_index <= 13'd0;
                            state              <= S_EVENT_LOAD;
                        end else begin
                            busy  <= 1'b0;
                            done  <= 1'b1;
                            state <= S_IDLE;
                        end
                    end else begin
                        clear_index <= clear_index + 8'd1;
                    end
                end

                // The synchronous event RAM read is requested combinationally
                // while in S_EVENT_LOAD and is available throughout the next
                // S_EVENT_VALIDATE cycle.
                S_EVENT_LOAD: begin
                    state <= S_EVENT_VALIDATE;
                end

                S_EVENT_VALIDATE: begin
                    if (current_event_axon >= MAX_AXONS) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_EVENT_AXON;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else if (current_event_axon >= latched_axon_count) begin
                        // Physically valid but unconfigured axon: no-op.
                        state <= S_EVENT_ADVANCE;
                    end else begin
                        row_start <= axon_row_mem[current_event_axon];
                        row_stop  <= axon_row_mem[current_event_axon + 16'd1];
                        state     <= S_ROW_VALIDATE;
                    end
                end

                S_ROW_VALIDATE: begin
                    if (
                        row_start > row_stop ||
                        row_start > latched_synapse_count ||
                        row_stop > latched_synapse_count ||
                        row_stop > MAX_SYNAPSES
                    ) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_ROW_POINTER;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else if (row_start == row_stop) begin
                        state <= S_EVENT_ADVANCE;
                    end else begin
                        active_synapse_index <= row_start;
                        state                <= S_SYN_READ;
                    end
                end

                S_SYN_READ: begin
                    work_synapse <= synapse_mem[active_synapse_index[11:0]];
                    state        <= S_SYN_VALIDATE;
                end

                S_SYN_VALIDATE: begin
                    if (work_synapse[12:9] >= latched_format_count) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_FORMAT_INDEX;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else if (work_synapse[28:13] >= latched_neuron_count) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_TARGET_NEURON;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else begin
                        work_format <= format_mem[work_synapse[12:9]];
                        state       <= S_ACCUM_READ;
                    end
                end

                S_ACCUM_READ: begin
                    if (!decoded_valid) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_WEIGHT_WORD;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else begin
                        state <= S_ACCUMULATE;
                    end
                end

                S_ACCUMULATE: begin
                    if (accumulator_overflow) begin
                        fault      <= 1'b1;
                        fault_code <= FAULT_ACCUM_OVERFLOW;
                        busy       <= 1'b0;
                        state      <= S_IDLE;
                    end else if ((active_synapse_index + 32'd1) >= row_stop) begin
                        state <= S_EVENT_ADVANCE;
                    end else begin
                        active_synapse_index <= active_synapse_index + 32'd1;
                        state                <= S_SYN_READ;
                    end
                end

                S_EVENT_ADVANCE: begin
                    if (!active_source) begin
                        if ((active_event_index + 13'd1) < latched_external_count) begin
                            active_event_index <= active_event_index + 13'd1;
                            state              <= S_EVENT_LOAD;
                        end else if (latched_recurrent_count != 13'd0) begin
                            active_source      <= 1'b1;
                            active_event_index <= 13'd0;
                            state              <= S_EVENT_LOAD;
                        end else begin
                            busy  <= 1'b0;
                            done  <= 1'b1;
                            state <= S_IDLE;
                        end
                    end else begin
                        if ((active_event_index + 13'd1) < latched_recurrent_count) begin
                            active_event_index <= active_event_index + 13'd1;
                            state              <= S_EVENT_LOAD;
                        end else begin
                            busy  <= 1'b0;
                            done  <= 1'b1;
                            state <= S_IDLE;
                        end
                    end
                end

                default: begin
                    fault      <= 1'b1;
                    fault_code <= 8'hFF;
                    busy       <= 1'b0;
                    state      <= S_IDLE;
                end
            endcase
        end
    end

endmodule
