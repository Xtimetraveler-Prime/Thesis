`timescale 1ns/1ps

module tb_recurrent_route_queue_v1;
    logic ap_clk = 1'b0;
    logic ap_rst = 1'b1;
    always #5 ap_clk = ~ap_clk;

    logic core_reset_start = 1'b0;
    logic start = 1'b0;
    logic [8:0] neuron_count = 9'd3;
    logic [12:0] route_count = 13'd5;

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

    task automatic write_row(input integer index, input integer value);
        begin
            @(negedge ap_clk);
            route_row_we = 1'b1;
            route_row_addr = index[8:0];
            route_row_wdata = value;
            @(negedge ap_clk);
            route_row_we = 1'b0;
        end
    endtask

    task automatic write_target(input integer index, input integer value);
        begin
            @(negedge ap_clk);
            route_target_we = 1'b1;
            route_target_addr = index[11:0];
            route_target_wdata = value[15:0];
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
            for (cycles = 0; cycles < 500; cycles = cycles + 1) begin
                @(posedge ap_clk);
                #1;
                if (fault)
                    $fatal(1, "unexpected routing fault 0x%02x source=%0d route=%0d", fault_code, active_source, active_route_index);
                if (done)
                    return;
            end
            $fatal(1, "timeout waiting for recurrent routing done");
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
                $fatal(1, "recurrent bank debug read did not assert rvalid");
            value = debug_rdata;
            @(negedge ap_clk);
            debug_re = 1'b0;
        end
    endtask

    task automatic pulse_core_reset;
        begin
            @(negedge ap_clk);
            core_reset_start = 1'b1;
            @(posedge ap_clk);
            #1;
            if (!core_reset_done)
                $fatal(1, "recurrent core reset did not assert done");
            @(negedge ap_clk);
            core_reset_start = 1'b0;
        end
    endtask

    initial begin : test_sequence
        logic [15:0] observed;
        integer i;
        integer expected [0:4];
        expected[0] = 6;
        expected[1] = 8;
        expected[2] = 7;
        expected[3] = 9;
        expected[4] = 6;

        repeat (5) @(posedge ap_clk);
        @(negedge ap_clk);
        ap_rst = 1'b0;

        // CSR image:
        // source 0 -> [6]
        // source 1 -> [8, 7] (declaration order)
        // source 2 -> [9, 6] (same target 6 as source 0 preserves multiplicity)
        write_row(0, 0);
        write_row(1, 1);
        write_row(2, 3);
        write_row(3, 5);
        write_target(0, 6);
        write_target(1, 8);
        write_target(2, 7);
        write_target(3, 9);
        write_target(4, 6);
        write_spike(0, 1'b1);
        write_spike(1, 1'b1);
        write_spike(2, 1'b1);

        // Tick t starts with an empty current bank. Generated events must land
        // only in bank1 and become current after the commit.
        pulse_start();
        wait_done();
        if (current_bank !== 1'b1 || current_count !== 13'd5)
            $fatal(1, "first commit bank/count mismatch: bank=%0d count=%0d", current_bank, current_count);
        if (last_consumed_count !== 13'd0 || last_routed_count !== 13'd5)
            $fatal(1, "first commit consumed/routed mismatch: consumed=%0d routed=%0d", last_consumed_count, last_routed_count);
        for (i = 0; i < 5; i = i + 1) begin
            read_bank(1'b1, i, observed);
            if (observed !== expected[i][15:0])
                $fatal(1, "route order mismatch at %0d: expected=%0d actual=%0d", i, expected[i], observed);
        end

        // Tick t+1 begins with those five events as current. Clear spikes so the
        // inactive bank is rebuilt empty. The current count after commit must be
        // zero while last_consumed_count proves the old bank was the input.
        write_spike(0, 1'b0);
        write_spike(1, 1'b0);
        write_spike(2, 1'b0);
        pulse_start();
        wait_done();
        if (last_consumed_count !== 13'd5 || last_routed_count !== 13'd0)
            $fatal(1, "second commit did not consume prior recurrence exactly once");
        if (current_bank !== 1'b0 || current_count !== 13'd0)
            $fatal(1, "second commit bank/count mismatch: bank=%0d count=%0d", current_bank, current_count);

        // A third empty tick must clear the old bank1 count before swapping back,
        // proving stale physical words cannot replay two ticks later.
        pulse_start();
        wait_done();
        if (last_consumed_count !== 13'd0 || current_bank !== 1'b1 || current_count !== 13'd0)
            $fatal(1, "stale recurrent events replayed after empty tick");
        if (debug_bank1_count !== 13'd0)
            $fatal(1, "inactive bank1 count was not logically cleared");

        // Architectural reset clears both counts and restores bank zero.
        pulse_core_reset();
        if (current_bank !== 1'b0 || current_count !== 13'd0 ||
            debug_bank0_count !== 13'd0 || debug_bank1_count !== 13'd0)
            $fatal(1, "architectural recurrent reset failed");

        // Invalid route target must fault rather than truncate to the physical
        // 10-bit axon address space.
        neuron_count = 9'd1;
        route_count = 13'd1;
        write_row(0, 0);
        write_row(1, 1);
        write_target(0, 1024);
        write_spike(0, 1'b1);
        pulse_start();
        for (i = 0; i < 100; i = i + 1) begin
            @(posedge ap_clk);
            #1;
            if (fault) begin
                if (fault_code !== 8'h04)
                    $fatal(1, "wrong route-target fault code: 0x%02x", fault_code);
                $display("M11.5.4 recurrent-route RTL tests passed: order + multiplicity + next-tick banks + reset + target fault");
                $finish;
            end
        end
        $fatal(1, "expected invalid route-target fault did not occur");
    end

endmodule
