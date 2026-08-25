`timescale 1ns/1ps

module tb_recurrent_route_queue_differential_v1;
    `include "generated_m11_5_4_vectors.svh"

    logic ap_clk = 1'b0;
    logic ap_rst = 1'b1;
    always #5 ap_clk = ~ap_clk;

    logic core_reset_start = 1'b0;
    logic start = 1'b0;
    logic [8:0] neuron_count = 9'd1;
    logic [12:0] route_count = 13'd0;

    logic busy;
    logic core_reset_done;
    logic done;
    logic fault;
    logic [7:0] fault_code;
    logic current_bank;
    logic [12:0] current_count;
    logic [12:0] last_consumed_count;
    logic [12:0] last_routed_count;
    logic [7:0] active_source;
    logic [31:0] active_route_index;

    logic route_row_we = 1'b0;
    logic [8:0] route_row_addr = 9'd0;
    logic [31:0] route_row_wdata = 32'd0;
    logic route_target_we = 1'b0;
    logic [11:0] route_target_addr = 12'd0;
    logic [15:0] route_target_wdata = 16'd0;
    logic spike_we = 1'b0;
    logic [7:0] spike_addr = 8'd0;
    logic spike_wdata = 1'b0;

    logic debug_re = 1'b0;
    logic debug_bank = 1'b0;
    logic [11:0] debug_addr = 12'd0;
    logic debug_rvalid;
    logic [15:0] debug_rdata;
    logic [12:0] debug_bank0_count;
    logic [12:0] debug_bank1_count;

    recurrent_route_queue_v1 dut (
        .ap_clk(ap_clk),
        .ap_rst(ap_rst),
        .core_reset_start(core_reset_start),
        .start(start),
        .neuron_count(neuron_count),
        .route_count(route_count),
        .busy(busy),
        .core_reset_done(core_reset_done),
        .done(done),
        .fault(fault),
        .fault_code(fault_code),
        .current_bank(current_bank),
        .current_count(current_count),
        .last_consumed_count(last_consumed_count),
        .last_routed_count(last_routed_count),
        .active_source(active_source),
        .active_route_index(active_route_index),
        .route_row_we(route_row_we),
        .route_row_addr(route_row_addr),
        .route_row_wdata(route_row_wdata),
        .route_target_we(route_target_we),
        .route_target_addr(route_target_addr),
        .route_target_wdata(route_target_wdata),
        .spike_we(spike_we),
        .spike_addr(spike_addr),
        .spike_wdata(spike_wdata),
        .debug_re(debug_re),
        .debug_bank(debug_bank),
        .debug_addr(debug_addr),
        .debug_rvalid(debug_rvalid),
        .debug_rdata(debug_rdata),
        .debug_bank0_count(debug_bank0_count),
        .debug_bank1_count(debug_bank1_count)
    );

    task automatic write_row(input integer index, input logic [31:0] value);
        begin
            @(negedge ap_clk);
            route_row_we = 1'b1;
            route_row_addr = index[8:0];
            route_row_wdata = value;
            @(negedge ap_clk);
            route_row_we = 1'b0;
        end
    endtask

    task automatic write_target(input integer index, input logic [15:0] value);
        begin
            @(negedge ap_clk);
            route_target_we = 1'b1;
            route_target_addr = index[11:0];
            route_target_wdata = value;
            @(negedge ap_clk);
            route_target_we = 1'b0;
        end
    endtask

    task automatic write_spike(input integer index, input logic value);
        begin
            @(negedge ap_clk);
            spike_we = 1'b1;
            spike_addr = index[7:0];
            spike_wdata = value;
            @(negedge ap_clk);
            spike_we = 1'b0;
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

    task automatic wait_done;
        integer cycles;
        begin
            for (cycles = 0; cycles < 2000; cycles = cycles + 1) begin
                @(posedge ap_clk);
                #1;
                if (fault)
                    $fatal(1, "routing differential fault=0x%02x source=%0d route=%0d", fault_code, active_source, active_route_index);
                if (done)
                    return;
            end
            $fatal(1, "timeout waiting for routing differential done: source=%0d route=%0d bank=%0d count=%0d", active_source, active_route_index, current_bank, current_count);
        end
    endtask

    task automatic pulse_core_reset;
        begin
            @(negedge ap_clk);
            core_reset_start = 1'b1;
            @(posedge ap_clk);
            #1;
            if (!core_reset_done)
                $fatal(1, "recurrent differential architectural reset did not acknowledge");
            @(negedge ap_clk);
            core_reset_start = 1'b0;
        end
    endtask

    task automatic read_bank(
        input logic bank,
        input integer index,
        output logic [15:0] value
    );
        begin
            @(negedge ap_clk);
            debug_bank = bank;
            debug_addr = index[11:0];
            debug_re = 1'b1;
            @(posedge ap_clk);
            #1;
            if (!debug_rvalid)
                $fatal(1, "recurrent differential debug read did not assert rvalid");
            value = debug_rdata;
            @(negedge ap_clk);
            debug_re = 1'b0;
        end
    endtask

    initial begin : differential_sequence
        integer case_index;
        integer tick_index;
        integer tick_flat;
        integer row_base;
        integer target_base;
        integer spike_base;
        integer event_base;
        integer i;
        logic [15:0] observed;

        repeat (5) @(posedge ap_clk);
        @(negedge ap_clk);
        ap_rst = 1'b0;

        for (case_index = 0; case_index < M11_5_4_CASE_COUNT; case_index = case_index + 1) begin
            neuron_count = M11_5_4_NEURON_COUNTS[case_index];
            route_count = M11_5_4_ROUTE_COUNTS[case_index];
            row_base = case_index * (M11_5_4_MAX_NEURONS + 1);
            target_base = case_index * M11_5_4_MAX_ROUTES;

            pulse_core_reset();
            if (current_bank !== 1'b0 || current_count !== 13'd0 ||
                debug_bank0_count !== 13'd0 || debug_bank1_count !== 13'd0)
                $fatal(1, "case %0d did not begin from empty bank0 reset state", case_index);

            for (i = 0; i <= neuron_count; i = i + 1)
                write_row(i, M11_5_4_ROUTE_ROWS[row_base + i]);
            for (i = 0; i < route_count; i = i + 1)
                write_target(i, M11_5_4_ROUTE_TARGETS[target_base + i]);

            for (tick_index = 0; tick_index < M11_5_4_TICKS_PER_CASE; tick_index = tick_index + 1) begin
                tick_flat = case_index * M11_5_4_TICKS_PER_CASE + tick_index;
                event_base = tick_flat * M11_5_4_MAX_EVENTS;

                // Before routing, the current bank is exactly the recurrence
                // consumed by this tick. Check its complete valid prefix.
                if (current_count !== M11_5_4_EXPECTED_CONSUMED_COUNTS[tick_flat])
                    $fatal(1, "case %0d tick %0d pre-tick consumed count mismatch: expected=%0d actual=%0d", case_index, tick_index, M11_5_4_EXPECTED_CONSUMED_COUNTS[tick_flat], current_count);
                for (i = 0; i < M11_5_4_EXPECTED_CONSUMED_COUNTS[tick_flat]; i = i + 1) begin
                    read_bank(current_bank, i, observed);
                    if (observed !== M11_5_4_EXPECTED_CONSUMED[event_base + i])
                        $fatal(1, "case %0d tick %0d consumed event mismatch at %0d: expected=%0d actual=%0d", case_index, tick_index, i, M11_5_4_EXPECTED_CONSUMED[event_base + i], observed);
                end

                spike_base = tick_flat * M11_5_4_MAX_NEURONS;
                for (i = 0; i < neuron_count; i = i + 1)
                    write_spike(i, M11_5_4_SPIKES[spike_base + i]);

                pulse_start();
                wait_done();

                if (last_consumed_count !== M11_5_4_EXPECTED_CONSUMED_COUNTS[tick_flat])
                    $fatal(1, "case %0d tick %0d last_consumed mismatch: expected=%0d actual=%0d", case_index, tick_index, M11_5_4_EXPECTED_CONSUMED_COUNTS[tick_flat], last_consumed_count);
                if (last_routed_count !== M11_5_4_EXPECTED_ROUTED_COUNTS[tick_flat])
                    $fatal(1, "case %0d tick %0d routed count mismatch: expected=%0d actual=%0d", case_index, tick_index, M11_5_4_EXPECTED_ROUTED_COUNTS[tick_flat], last_routed_count);
                if (current_bank !== M11_5_4_EXPECTED_CURRENT_BANKS[tick_flat])
                    $fatal(1, "case %0d tick %0d bank selector mismatch: expected=%0d actual=%0d", case_index, tick_index, M11_5_4_EXPECTED_CURRENT_BANKS[tick_flat], current_bank);
                if (current_count !== M11_5_4_EXPECTED_CURRENT_COUNTS[tick_flat])
                    $fatal(1, "case %0d tick %0d current count mismatch: expected=%0d actual=%0d", case_index, tick_index, M11_5_4_EXPECTED_CURRENT_COUNTS[tick_flat], current_count);
                if (debug_bank0_count !== M11_5_4_EXPECTED_BANK0_COUNTS[tick_flat] ||
                    debug_bank1_count !== M11_5_4_EXPECTED_BANK1_COUNTS[tick_flat])
                    $fatal(1, "case %0d tick %0d bank-count mismatch: expected=(%0d,%0d) actual=(%0d,%0d)", case_index, tick_index, M11_5_4_EXPECTED_BANK0_COUNTS[tick_flat], M11_5_4_EXPECTED_BANK1_COUNTS[tick_flat], debug_bank0_count, debug_bank1_count);

                // After Phase-F commit, the newly current bank is the complete
                // routed-output sequence generated by this tick.
                for (i = 0; i < M11_5_4_EXPECTED_ROUTED_COUNTS[tick_flat]; i = i + 1) begin
                    read_bank(current_bank, i, observed);
                    if (observed !== M11_5_4_EXPECTED_ROUTED[event_base + i])
                        $fatal(1, "case %0d tick %0d routed event mismatch at %0d: expected=%0d actual=%0d", case_index, tick_index, i, M11_5_4_EXPECTED_ROUTED[event_base + i], observed);
                end
            end
        end

        $display("M11.5.4 Python/RTL routing differential passed: cases=%0d, ticks=%0d, seed=0x%08x", M11_5_4_CASE_COUNT, M11_5_4_CASE_COUNT * M11_5_4_TICKS_PER_CASE, M11_5_4_SEED);
        $finish;
    end

endmodule
