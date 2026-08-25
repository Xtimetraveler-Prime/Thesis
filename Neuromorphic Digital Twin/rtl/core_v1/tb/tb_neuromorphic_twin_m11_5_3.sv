`timescale 1ns/1ps

module tb_neuromorphic_twin_m11_5_3;

    logic ap_clk = 1'b0;
    logic ap_rst = 1'b1;
    logic core_reset_start = 1'b0;
    logic tick_start = 1'b0;

    logic [8:0] neuron_count = 9'd0;
    logic [10:0] axon_count = 11'd0;
    logic [12:0] synapse_count = 13'd0;
    logic [4:0] format_count = 5'd0;
    logic [12:0] external_event_count = 13'd0;
    logic [12:0] recurrent_event_count = 13'd0;

    logic busy;
    logic core_reset_done;
    logic tick_done;
    logic [31:0] tick;
    logic fault;
    logic [7:0] fault_code;
    logic [7:0] active_neuron;
    logic phase_b_active_source;
    logic [12:0] phase_b_active_event_index;
    logic [31:0] phase_b_active_synapse_index;

    logic config_we = 1'b0;
    logic [7:0] config_addr = 8'd0;
    logic [127:0] config_wdata = 128'd0;
    logic state_we = 1'b0;
    logic [7:0] state_addr = 8'd0;
    logic [63:0] state_wdata = 64'd0;

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

    logic debug_re = 1'b0;
    logic [7:0] debug_addr = 8'd0;
    logic debug_rvalid;
    logic [127:0] debug_config_rdata;
    logic [63:0] debug_state_rdata;
    logic signed [63:0] debug_accum_rdata;
    logic debug_spike_rdata;

    `include "generated_m11_5_3_integrated_vectors.svh"

    neuromorphic_twin_m11_5_3_wrapper dut (
        .ap_clk(ap_clk), .ap_rst(ap_rst),
        .core_reset_start(core_reset_start), .tick_start(tick_start),
        .neuron_count(neuron_count), .axon_count(axon_count),
        .synapse_count(synapse_count), .format_count(format_count),
        .external_event_count(external_event_count),
        .recurrent_event_count(recurrent_event_count),
        .busy(busy), .core_reset_done(core_reset_done), .tick_done(tick_done),
        .tick(tick), .fault(fault), .fault_code(fault_code),
        .active_neuron(active_neuron),
        .phase_b_active_source(phase_b_active_source),
        .phase_b_active_event_index(phase_b_active_event_index),
        .phase_b_active_synapse_index(phase_b_active_synapse_index),
        .config_we(config_we), .config_addr(config_addr), .config_wdata(config_wdata),
        .state_we(state_we), .state_addr(state_addr), .state_wdata(state_wdata),
        .format_we(format_we), .format_addr(format_addr), .format_wdata(format_wdata),
        .synapse_we(synapse_we), .synapse_addr(synapse_addr), .synapse_wdata(synapse_wdata),
        .row_we(row_we), .row_addr(row_addr), .row_wdata(row_wdata),
        .external_we(external_we), .external_addr(external_addr), .external_wdata(external_wdata),
        .recurrent_we(recurrent_we), .recurrent_addr(recurrent_addr), .recurrent_wdata(recurrent_wdata),
        .debug_re(debug_re), .debug_addr(debug_addr), .debug_rvalid(debug_rvalid),
        .debug_config_rdata(debug_config_rdata), .debug_state_rdata(debug_state_rdata),
        .debug_accum_rdata(debug_accum_rdata), .debug_spike_rdata(debug_spike_rdata)
    );

    always #5 ap_clk = ~ap_clk;

    task automatic write_config(input int index, input logic [127:0] word);
        begin
            @(negedge ap_clk); config_addr = index[7:0]; config_wdata = word; config_we = 1'b1;
            @(negedge ap_clk); config_we = 1'b0;
        end
    endtask

    task automatic write_state(input int index, input logic [63:0] word);
        begin
            @(negedge ap_clk); state_addr = index[7:0]; state_wdata = word; state_we = 1'b1;
            @(negedge ap_clk); state_we = 1'b0;
        end
    endtask

    task automatic write_format(input int index, input logic [15:0] word);
        begin
            @(negedge ap_clk); format_addr = index[3:0]; format_wdata = word; format_we = 1'b1;
            @(negedge ap_clk); format_we = 1'b0;
        end
    endtask

    task automatic write_synapse(input int index, input logic [31:0] word);
        begin
            @(negedge ap_clk); synapse_addr = index[11:0]; synapse_wdata = word; synapse_we = 1'b1;
            @(negedge ap_clk); synapse_we = 1'b0;
        end
    endtask

    task automatic write_row(input int index, input logic [31:0] word);
        begin
            @(negedge ap_clk); row_addr = index[10:0]; row_wdata = word; row_we = 1'b1;
            @(negedge ap_clk); row_we = 1'b0;
        end
    endtask

    task automatic write_external(input int index, input logic [15:0] word);
        begin
            @(negedge ap_clk); external_addr = index[11:0]; external_wdata = word; external_we = 1'b1;
            @(negedge ap_clk); external_we = 1'b0;
        end
    endtask

    task automatic write_recurrent(input int index, input logic [15:0] word);
        begin
            @(negedge ap_clk); recurrent_addr = index[11:0]; recurrent_wdata = word; recurrent_we = 1'b1;
            @(negedge ap_clk); recurrent_we = 1'b0;
        end
    endtask

    task automatic pulse_reset;
        begin
            @(negedge ap_clk); core_reset_start = 1'b1;
            @(negedge ap_clk); core_reset_start = 1'b0;
        end
    endtask

    task automatic pulse_tick;
        begin
            @(negedge ap_clk); tick_start = 1'b1;
            @(negedge ap_clk); tick_start = 1'b0;
        end
    endtask

    task automatic wait_for_reset;
        int cycles;
        begin
            for (cycles = 0; cycles < 10000; cycles = cycles + 1) begin
                @(posedge ap_clk); #1;
                if (core_reset_done) return;
                if (fault) $fatal(1, "M11.5.3 reset fault: code=0x%02x neuron=%0d", fault_code, active_neuron);
            end
            $fatal(1, "M11.5.3 timeout waiting for core reset: busy=%0d fault=0x%02x neuron=%0d", busy, fault_code, active_neuron);
        end
    endtask

    task automatic wait_for_tick;
        int cycles;
        begin
            for (cycles = 0; cycles < 200000; cycles = cycles + 1) begin
                @(posedge ap_clk); #1;
                if (tick_done) return;
                if (fault)
                    $fatal(
                        1,
                        "M11.5.3 integrated fault: code=0x%02x neuron=%0d phase_b_source=%0d event=%0d synapse=%0d",
                        fault_code, active_neuron, phase_b_active_source,
                        phase_b_active_event_index, phase_b_active_synapse_index
                    );
            end
            $fatal(
                1,
                "M11.5.3 integrated timeout: busy=%0d tick=%0d neuron=%0d phase_b_source=%0d event=%0d synapse=%0d",
                busy, tick, active_neuron, phase_b_active_source,
                phase_b_active_event_index, phase_b_active_synapse_index
            );
        end
    endtask

    task automatic read_debug(
        input int index,
        output logic [127:0] config_word,
        output logic [63:0] state_word,
        output logic signed [63:0] accum_word,
        output logic spike
    );
        begin
            @(negedge ap_clk); debug_addr = index[7:0]; debug_re = 1'b1;
            @(posedge ap_clk); #1;
            if (!debug_rvalid) $fatal(1, "M11.5.3 debug read invalid at neuron %0d", index);
            config_word = debug_config_rdata;
            state_word = debug_state_rdata;
            accum_word = debug_accum_rdata;
            spike = debug_spike_rdata;
            @(negedge ap_clk); debug_re = 1'b0;
        end
    endtask

    initial begin : test_sequence
        integer index;
        logic [127:0] observed_config;
        logic [63:0] observed_state;
        logic signed [63:0] observed_accum;
        logic observed_spike;

        neuron_count = M11_5_3I_NEURON_COUNT;
        axon_count = M11_5_3I_AXON_COUNT;
        synapse_count = M11_5_3I_SYNAPSE_COUNT;
        format_count = M11_5_3I_FORMAT_COUNT;
        external_event_count = M11_5_3I_EXTERNAL_COUNT;
        recurrent_event_count = M11_5_3I_RECURRENT_COUNT;

        repeat (5) @(posedge ap_clk);
        @(negedge ap_clk); ap_rst = 1'b0;

        for (index = 0; index < M11_5_3I_FORMAT_COUNT; index = index + 1)
            write_format(index, M11_5_3I_FORMAT_WORDS[index]);
        for (index = 0; index < M11_5_3I_SYNAPSE_COUNT; index = index + 1)
            write_synapse(index, M11_5_3I_SYNAPSE_WORDS[index]);
        for (index = 0; index <= M11_5_3I_AXON_COUNT; index = index + 1)
            write_row(index, M11_5_3I_ROW_POINTERS[index]);
        for (index = 0; index < M11_5_3I_EXTERNAL_COUNT; index = index + 1)
            write_external(index, M11_5_3I_EXTERNAL_EVENTS[index]);
        for (index = 0; index < M11_5_3I_RECURRENT_COUNT; index = index + 1)
            write_recurrent(index, M11_5_3I_RECURRENT_EVENTS[index]);
        for (index = 0; index < M11_5_3I_NEURON_COUNT; index = index + 1)
            write_config(index, M11_5_3I_CONFIG_WORDS[index]);

        pulse_reset();
        wait_for_reset();
        if (tick !== 32'd0) $fatal(1, "M11.5.3 reset did not restore tick zero: %0d", tick);

        for (index = 0; index < M11_5_3I_NEURON_COUNT; index = index + 1) begin
            read_debug(index, observed_config, observed_state, observed_accum, observed_spike);
            if (observed_config !== M11_5_3I_CONFIG_WORDS[index])
                $fatal(1, "M11.5.3 config mismatch after reset at neuron %0d", index);
            if (observed_state !== M11_5_3I_RESET_STATE_WORDS[index])
                $fatal(1, "M11.5.3 reset-state mismatch at neuron %0d expected=%h actual=%h", index, M11_5_3I_RESET_STATE_WORDS[index], observed_state);
        end

        for (index = 0; index < M11_5_3I_NEURON_COUNT; index = index + 1)
            write_state(index, M11_5_3I_INITIAL_STATE_WORDS[index]);

        pulse_tick();
        wait_for_tick();

        if (tick !== 32'd1) $fatal(1, "M11.5.3 integrated tick did not increment exactly once: %0d", tick);
        for (index = 0; index < M11_5_3I_NEURON_COUNT; index = index + 1) begin
            read_debug(index, observed_config, observed_state, observed_accum, observed_spike);
            if (observed_config !== M11_5_3I_CONFIG_WORDS[index])
                $fatal(1, "M11.5.3 config changed during integrated tick at neuron %0d", index);
            if (observed_state !== M11_5_3I_EXPECTED_STATE_WORDS[index])
                $fatal(1, "M11.5.3 state mismatch at neuron %0d expected=%h actual=%h", index, M11_5_3I_EXPECTED_STATE_WORDS[index], observed_state);
            if (observed_accum !== 64'sd0)
                $fatal(1, "M11.5.3 controller accumulator not cleared at neuron %0d: %0d", index, observed_accum);
            if (observed_spike !== M11_5_3I_EXPECTED_SPIKES[index])
                $fatal(1, "M11.5.3 spike mismatch at neuron %0d expected=%0d actual=%0d", index, M11_5_3I_EXPECTED_SPIKES[index], observed_spike);
        end

        $display(
            "M11.5.3 packed-M08 + real-HLS integrated tick passed: neurons=%0d, axons=%0d, synapses=%0d, tag=0x%08x",
            M11_5_3I_NEURON_COUNT, M11_5_3I_AXON_COUNT,
            M11_5_3I_SYNAPSE_COUNT, M11_5_3I_TAG
        );
        $finish;
    end

endmodule
