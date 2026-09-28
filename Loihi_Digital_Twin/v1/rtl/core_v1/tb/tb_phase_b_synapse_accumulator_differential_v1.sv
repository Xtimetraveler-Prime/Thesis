`timescale 1ns/1ps

module tb_phase_b_synapse_accumulator_differential_v1;

    logic ap_clk = 1'b0;
    logic ap_rst = 1'b1;
    logic start = 1'b0;

    logic [8:0]  neuron_count = 9'd0;
    logic [10:0] axon_count = 11'd0;
    logic [12:0] synapse_count = 13'd0;
    logic [4:0]  format_count = 5'd0;
    logic [12:0] external_event_count = 13'd0;
    logic [12:0] recurrent_event_count = 13'd0;

    logic busy;
    logic done;
    logic fault;
    logic [7:0] fault_code;
    logic active_source;
    logic [12:0] active_event_index;
    logic [31:0] active_synapse_index;

    logic format_we = 1'b0;
    logic [3:0] format_addr = 4'd0;
    logic [15:0] format_wdata = 16'd0;
    logic synapse_we = 1'b0;
    logic [11:0] synapse_addr = 12'd0;
    logic [31:0] synapse_wdata = 32'd0;
    logic row_we = 1'b0;
    logic [10:0] row_addr = 11'd0;
    logic [31:0] row_wdata = 32'd0;
    logic external_we = 1'b0;
    logic [11:0] external_addr = 12'd0;
    logic [15:0] external_wdata = 16'd0;
    logic recurrent_we = 1'b0;
    logic [11:0] recurrent_addr = 12'd0;
    logic [15:0] recurrent_wdata = 16'd0;

    logic debug_accum_re = 1'b0;
    logic [7:0] debug_accum_addr = 8'd0;
    logic debug_accum_rvalid;
    logic signed [63:0] debug_accum_rdata;

    `include "generated_m11_5_3_vectors.svh"

    phase_b_synapse_accumulator_v1 #(
        .MAX_NEURONS(M11_5_3_MAX_NEURONS),
        .MAX_AXONS(M11_5_3_MAX_AXONS),
        .MAX_SYNAPSES(M11_5_3_MAX_SYNAPSES),
        .MAX_FORMATS(M11_5_3_MAX_FORMATS),
        .MAX_EVENTS(M11_5_3_MAX_EXTERNAL_EVENTS)
    ) dut (
        .ap_clk(ap_clk),
        .ap_rst(ap_rst),
        .start(start),
        .neuron_count(neuron_count),
        .axon_count(axon_count),
        .synapse_count(synapse_count),
        .format_count(format_count),
        .external_event_count(external_event_count),
        .recurrent_event_count(recurrent_event_count),
        .busy(busy),
        .done(done),
        .fault(fault),
        .fault_code(fault_code),
        .active_source(active_source),
        .active_event_index(active_event_index),
        .active_synapse_index(active_synapse_index),
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
        .recurrent_we(recurrent_we),
        .recurrent_addr(recurrent_addr),
        .recurrent_wdata(recurrent_wdata),
        .debug_accum_re(debug_accum_re),
        .debug_accum_addr(debug_accum_addr),
        .debug_accum_rvalid(debug_accum_rvalid),
        .debug_accum_rdata(debug_accum_rdata)
    );

    always #5 ap_clk = ~ap_clk;

    task automatic write_format(input int index, input logic [15:0] word);
        begin
            @(negedge ap_clk);
            format_addr = index[3:0];
            format_wdata = word;
            format_we = 1'b1;
            @(negedge ap_clk);
            format_we = 1'b0;
        end
    endtask

    task automatic write_synapse(input int index, input logic [31:0] word);
        begin
            @(negedge ap_clk);
            synapse_addr = index[11:0];
            synapse_wdata = word;
            synapse_we = 1'b1;
            @(negedge ap_clk);
            synapse_we = 1'b0;
        end
    endtask

    task automatic write_row(input int index, input logic [31:0] word);
        begin
            @(negedge ap_clk);
            row_addr = index[10:0];
            row_wdata = word;
            row_we = 1'b1;
            @(negedge ap_clk);
            row_we = 1'b0;
        end
    endtask

    task automatic write_external(input int index, input logic [15:0] word);
        begin
            @(negedge ap_clk);
            external_addr = index[11:0];
            external_wdata = word;
            external_we = 1'b1;
            @(negedge ap_clk);
            external_we = 1'b0;
        end
    endtask

    task automatic write_recurrent(input int index, input logic [15:0] word);
        begin
            @(negedge ap_clk);
            recurrent_addr = index[11:0];
            recurrent_wdata = word;
            recurrent_we = 1'b1;
            @(negedge ap_clk);
            recurrent_we = 1'b0;
        end
    endtask

    task automatic read_accumulator(input int index, output logic signed [63:0] value);
        begin
            @(negedge ap_clk);
            debug_accum_addr = index[7:0];
            debug_accum_re = 1'b1;
            @(posedge ap_clk);
            #1;
            if (!debug_accum_rvalid)
                $fatal(1, "M11.5.3 differential debug read invalid at neuron %0d", index);
            value = debug_accum_rdata;
            @(negedge ap_clk);
            debug_accum_re = 1'b0;
        end
    endtask

    task automatic pulse_start;
        begin
            @(negedge ap_clk);
            start = 1'b1;
            @(negedge ap_clk);
            start = 1'b0;
        end
    endtask

    task automatic wait_for_done(input int case_index);
        int cycles;
        begin
            for (cycles = 0; cycles < 200000; cycles = cycles + 1) begin
                @(posedge ap_clk);
                #1;
                if (done)
                    return;
                if (fault)
                    $fatal(
                        1,
                        "M11.5.3 differential fault: case=%0d code=0x%02x source=%0d event=%0d synapse=%0d",
                        case_index,
                        fault_code,
                        active_source,
                        active_event_index,
                        active_synapse_index
                    );
            end
            $fatal(
                1,
                "M11.5.3 differential timeout: case=%0d busy=%0d source=%0d event=%0d synapse=%0d",
                case_index,
                busy,
                active_source,
                active_event_index,
                active_synapse_index
            );
        end
    endtask

    initial begin : test_sequence
        integer case_index;
        integer index;
        integer base;
        logic signed [63:0] observed;
        logic signed [63:0] expected;

        repeat (5) @(posedge ap_clk);
        @(negedge ap_clk);
        ap_rst = 1'b0;

        for (case_index = 0; case_index < M11_5_3_CASE_COUNT; case_index = case_index + 1) begin
            neuron_count = M11_5_3_NEURON_COUNTS[case_index];
            axon_count = M11_5_3_AXON_COUNTS[case_index];
            synapse_count = M11_5_3_SYNAPSE_COUNTS[case_index];
            format_count = M11_5_3_FORMAT_COUNTS[case_index];
            external_event_count = M11_5_3_EXTERNAL_COUNTS[case_index];
            recurrent_event_count = M11_5_3_RECURRENT_COUNTS[case_index];

            base = case_index * M11_5_3_MAX_FORMATS;
            for (index = 0; index < format_count; index = index + 1)
                write_format(index, M11_5_3_FORMAT_WORDS[base + index]);

            base = case_index * M11_5_3_MAX_SYNAPSES;
            for (index = 0; index < synapse_count; index = index + 1)
                write_synapse(index, M11_5_3_SYNAPSE_WORDS[base + index]);

            base = case_index * (M11_5_3_MAX_AXONS + 1);
            for (index = 0; index <= axon_count; index = index + 1)
                write_row(index, M11_5_3_ROW_POINTERS[base + index]);

            base = case_index * M11_5_3_MAX_EXTERNAL_EVENTS;
            for (index = 0; index < external_event_count; index = index + 1)
                write_external(index, M11_5_3_EXTERNAL_EVENTS[base + index]);

            base = case_index * M11_5_3_MAX_RECURRENT_EVENTS;
            for (index = 0; index < recurrent_event_count; index = index + 1)
                write_recurrent(index, M11_5_3_RECURRENT_EVENTS[base + index]);

            pulse_start();
            wait_for_done(case_index);

            if (fault)
                $fatal(1, "M11.5.3 differential fault remained asserted after case %0d: 0x%02x", case_index, fault_code);

            base = case_index * M11_5_3_MAX_NEURONS;
            for (index = 0; index < neuron_count; index = index + 1) begin
                read_accumulator(index, observed);
                expected = M11_5_3_EXPECTED_ACCUMULATORS[base + index];
                if (observed !== expected)
                    $fatal(
                        1,
                        "M11.5.3 accumulator mismatch: case=%0d neuron=%0d expected=%0d (0x%016h) actual=%0d (0x%016h)",
                        case_index,
                        index,
                        expected,
                        expected,
                        observed,
                        observed
                    );
            end
        end

        $display(
            "M11.5.3 Python/RTL accumulator differential passed: cases=%0d, seed=0x%08x",
            M11_5_3_CASE_COUNT,
            M11_5_3_SEED
        );
        $finish;
    end

endmodule
