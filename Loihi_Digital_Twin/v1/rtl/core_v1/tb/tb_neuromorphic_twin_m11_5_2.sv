`timescale 1ns/1ps

module tb_neuromorphic_twin_m11_5_2;

    logic ap_clk = 1'b0;
    logic ap_rst = 1'b1;

    logic core_reset_start = 1'b0;
    logic tick_start = 1'b0;
    logic [8:0] neuron_count = 9'd0;

    logic busy;
    logic core_reset_done;
    logic tick_done;
    logic [31:0] tick;
    logic fault;
    logic [7:0] fault_code;
    logic [7:0] active_neuron;

    logic config_we = 1'b0;
    logic [7:0] config_addr = 8'd0;
    logic [127:0] config_wdata = 128'd0;
    logic state_we = 1'b0;
    logic [7:0] state_addr = 8'd0;
    logic [63:0] state_wdata = 64'd0;
    logic accum_we = 1'b0;
    logic [7:0] accum_addr = 8'd0;
    logic signed [63:0] accum_wdata = 64'sd0;

    logic debug_re = 1'b0;
    logic [7:0] debug_addr = 8'd0;
    logic debug_rvalid;
    logic [127:0] debug_config_rdata;
    logic [63:0] debug_state_rdata;
    logic signed [63:0] debug_accum_rdata;
    logic debug_spike_rdata;

    `include "generated_m11_5_2_vectors.svh"

    neuromorphic_twin_m11_5_2_wrapper dut (
        .ap_clk(ap_clk),
        .ap_rst(ap_rst),
        .core_reset_start(core_reset_start),
        .tick_start(tick_start),
        .neuron_count(neuron_count),
        .busy(busy),
        .core_reset_done(core_reset_done),
        .tick_done(tick_done),
        .tick(tick),
        .fault(fault),
        .fault_code(fault_code),
        .active_neuron(active_neuron),
        .config_we(config_we),
        .config_addr(config_addr),
        .config_wdata(config_wdata),
        .state_we(state_we),
        .state_addr(state_addr),
        .state_wdata(state_wdata),
        .accum_we(accum_we),
        .accum_addr(accum_addr),
        .accum_wdata(accum_wdata),
        .debug_re(debug_re),
        .debug_addr(debug_addr),
        .debug_rvalid(debug_rvalid),
        .debug_config_rdata(debug_config_rdata),
        .debug_state_rdata(debug_state_rdata),
        .debug_accum_rdata(debug_accum_rdata),
        .debug_spike_rdata(debug_spike_rdata)
    );

    always #5 ap_clk = ~ap_clk;

    task automatic write_config(input int index, input logic [127:0] word);
        begin
            @(negedge ap_clk);
            config_addr  = index[7:0];
            config_wdata = word;
            config_we    = 1'b1;
            @(negedge ap_clk);
            config_we    = 1'b0;
        end
    endtask

    task automatic write_state(input int index, input logic [63:0] word);
        begin
            @(negedge ap_clk);
            state_addr  = index[7:0];
            state_wdata = word;
            state_we    = 1'b1;
            @(negedge ap_clk);
            state_we    = 1'b0;
        end
    endtask

    task automatic write_accum(input int index, input logic signed [63:0] word);
        begin
            @(negedge ap_clk);
            accum_addr  = index[7:0];
            accum_wdata = word;
            accum_we    = 1'b1;
            @(negedge ap_clk);
            accum_we    = 1'b0;
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
            @(negedge ap_clk);
            debug_addr = index[7:0];
            debug_re   = 1'b1;
            @(posedge ap_clk);
            #1;
            if (!debug_rvalid) begin
                $fatal(1, "debug read did not become valid for neuron %0d", index);
            end
            config_word = debug_config_rdata;
            state_word  = debug_state_rdata;
            accum_word  = debug_accum_rdata;
            spike       = debug_spike_rdata;
            @(negedge ap_clk);
            debug_re = 1'b0;
        end
    endtask

    task automatic pulse_core_reset;
        begin
            @(negedge ap_clk);
            core_reset_start = 1'b1;
            @(negedge ap_clk);
            core_reset_start = 1'b0;
        end
    endtask

    task automatic pulse_tick;
        begin
            @(negedge ap_clk);
            tick_start = 1'b1;
            @(negedge ap_clk);
            tick_start = 1'b0;
        end
    endtask

    task automatic wait_for_core_reset_done;
        int cycles;
        begin
            for (cycles = 0; cycles < 5000; cycles = cycles + 1) begin
                @(posedge ap_clk);
                #1;
                if (core_reset_done)
                    return;
                if (fault)
                    $fatal(1, "controller fault during core reset: code=0x%02x active_neuron=%0d", fault_code, active_neuron);
            end
            $fatal(1, "timeout waiting for core_reset_done: busy=%0d active_neuron=%0d fault=%0d fault_code=0x%02x tick=%0d", busy, active_neuron, fault, fault_code, tick);
        end
    endtask

    task automatic wait_for_tick_done;
        int cycles;
        begin
            for (cycles = 0; cycles < 20000; cycles = cycles + 1) begin
                @(posedge ap_clk);
                #1;
                if (tick_done)
                    return;
                if (fault)
                    $fatal(1, "controller fault during tick: code=0x%02x active_neuron=%0d", fault_code, active_neuron);
            end
            $fatal(1, "timeout waiting for tick_done: busy=%0d active_neuron=%0d fault=%0d fault_code=0x%02x tick=%0d", busy, active_neuron, fault, fault_code, tick);
        end
    endtask

    initial begin : test_sequence
        integer index;
        logic [127:0] observed_config;
        logic [63:0] observed_state;
        logic signed [63:0] observed_accum;
        logic observed_spike;

        neuron_count = M11_5_2_NEURON_COUNT;

        repeat (5) @(posedge ap_clk);
        @(negedge ap_clk);
        ap_rst = 1'b0;

        // Load every configuration word before architectural reset because the
        // reset voltage itself is part of the per-neuron static configuration.
        for (index = 0; index < M11_5_2_NEURON_COUNT; index = index + 1) begin
            write_config(index, M11_5_2_CONFIG_WORDS[index]);
        end

        pulse_core_reset();
        wait_for_core_reset_done();

        if (fault)
            $fatal(1, "fault remained asserted after architectural reset: 0x%02x", fault_code);
        if (tick !== 32'd0)
            $fatal(1, "architectural reset did not restore tick to zero: %0d", tick);

        // Verify reset is a full architectural operation and configuration is
        // preserved while dynamic state, accumulator, and spike flag reset.
        for (index = 0; index < M11_5_2_NEURON_COUNT; index = index + 1) begin
            read_debug(index, observed_config, observed_state, observed_accum, observed_spike);
            if (observed_config !== M11_5_2_CONFIG_WORDS[index])
                $fatal(1, "config mismatch after reset at neuron %0d", index);
            if (observed_state !== M11_5_2_RESET_STATE_WORDS[index])
                $fatal(1, "reset-state mismatch at neuron %0d: expected=%h actual=%h", index, M11_5_2_RESET_STATE_WORDS[index], observed_state);
            if (observed_accum !== 64'sd0)
                $fatal(1, "accumulator not cleared by reset at neuron %0d", index);
            if (observed_spike !== 1'b0)
                $fatal(1, "spike flag not cleared by reset at neuron %0d", index);
        end

        // Replay the exact pre-tick packed state/accumulator image generated
        // from the Python golden vectors.
        for (index = 0; index < M11_5_2_NEURON_COUNT; index = index + 1) begin
            write_state(index, M11_5_2_INITIAL_STATE_WORDS[index]);
            write_accum(index, M11_5_2_ACCUM_WORDS[index]);
        end

        pulse_tick();
        wait_for_tick_done();

        if (fault)
            $fatal(1, "fault remained asserted after tick: 0x%02x", fault_code);
        if (tick !== 32'd1)
            $fatal(1, "one integrated tick did not increment tick to one: %0d", tick);

        // Exact packed-memory comparison against Python-generated expectations.
        for (index = 0; index < M11_5_2_NEURON_COUNT; index = index + 1) begin
            read_debug(index, observed_config, observed_state, observed_accum, observed_spike);
            if (observed_config !== M11_5_2_CONFIG_WORDS[index])
                $fatal(1, "config changed during tick at neuron %0d", index);
            if (observed_state !== M11_5_2_EXPECTED_STATE_WORDS[index])
                $fatal(1, "state mismatch at neuron %0d: expected=%h actual=%h", index, M11_5_2_EXPECTED_STATE_WORDS[index], observed_state);
            if (observed_accum !== 64'sd0)
                $fatal(1, "accumulator was not cleared after consumption at neuron %0d", index);
            if (observed_spike !== M11_5_2_EXPECTED_SPIKES[index])
                $fatal(1, "spike mismatch at neuron %0d: expected=%0d actual=%0d", index, M11_5_2_EXPECTED_SPIKES[index], observed_spike);
        end

        $display(
            "M11.5.2 real packaged-IP integration passed: neurons=%0d, directed=24, random=40, seed=0x%08x",
            M11_5_2_NEURON_COUNT,
            M11_5_2_SEED
        );
        $finish;
    end

endmodule
