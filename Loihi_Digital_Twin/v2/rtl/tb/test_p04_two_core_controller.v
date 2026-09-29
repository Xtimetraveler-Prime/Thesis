`timescale 1ns/1ps

module test_p04_two_core_controller;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg epoch_load = 1'b0;
    reg [31:0] epoch_timestep = 0;
    reg [12:0] epoch_event_count0 = 0;
    reg [12:0] epoch_event_count1 = 0;
    reg tick_start = 1'b0;
    reg service_reverse = 1'b0;

    wire core0_start;
    wire core1_start;
    reg core0_done = 1'b0;
    reg core1_done = 1'b0;
    reg [12:0] core0_packet_count = 0;
    reg [12:0] core1_packet_count = 0;
    reg [31:0] core0_status = 0;
    reg [31:0] core1_status = 0;

    wire [12:0] core0_event_count;
    wire [12:0] core1_event_count;
    wire [31:0] core_timestep;

    wire core0_packet_mem_en;
    wire [11:0] core0_packet_mem_addr;
    reg [63:0] core0_packet_mem_data = 0;
    wire core1_packet_mem_en;
    wire [11:0] core1_packet_mem_addr;
    reg [63:0] core1_packet_mem_data = 0;

    wire core0_event_mem_we;
    wire [11:0] core0_event_mem_addr;
    wire [31:0] core0_event_mem_data;
    wire core1_event_mem_we;
    wire [11:0] core1_event_mem_addr;
    wire [31:0] core1_event_mem_data;

    wire busy;
    wire tick_done;
    wire start_blocked;
    wire epoch_loaded;
    wire [31:0] current_timestep;
    wire [12:0] current_event_count0;
    wire [12:0] current_event_count1;
    wire [12:0] next_event_count0;
    wire [12:0] next_event_count1;
    wire [15:0] in_flight_count;
    wire [1:0] barrier_completed_mask;
    wire barrier_can_advance;
    wire [31:0] local_packet_count;
    wire [31:0] remote_packet_count;
    wire [31:0] completed_ticks;
    wire [63:0] active_cycles;
    wire [63:0] last_tick_cycles;
    wire error_physical_capacity;
    wire error_event_overflow;
    wire error_event_axon;
    wire error_core_status;
    wire error_router_bad_valid;
    wire error_router_bad_destination;
    wire error_router_bad_timestep;

    reg [63:0] packet_mem0 [0:7];
    reg [63:0] packet_mem1 [0:7];
    reg [31:0] event_mem0 [0:7];
    reg [31:0] event_mem1 [0:7];

    integer core0_delay = 0;
    integer core1_delay = 0;
    integer timeout;
    integer i;

    function [63:0] make_packet;
        input [6:0] destination_core;
        input [11:0] destination_axon;
        input [31:0] target_timestep;
        reg [63:0] word;
        begin
            word = 64'd0;
            word[6:0] = destination_core;
            word[18:7] = destination_axon;
            word[28:19] = 10'd0;
            word[60:29] = target_timestep;
            word[61] = 1'b1;
            make_packet = word;
        end
    endfunction

    p04_two_core_controller #(
        .PHYS_COMPARTMENTS(4),
        .PHYS_AXONS(8),
        .PHYS_SYNAPSES(16),
        .PHYS_ROUTES(8),
        .PHYS_EVENTS(8),
        .PHYS_PACKETS(8),
        .ROUTER_FIFO_DEPTH(4)
    ) dut (
        .clk(clk),
        .resetn(resetn),
        .epoch_load(epoch_load),
        .epoch_timestep(epoch_timestep),
        .epoch_event_count0(epoch_event_count0),
        .epoch_event_count1(epoch_event_count1),
        .tick_start(tick_start),
        .service_reverse(service_reverse),
        .host_busy0(1'b0),
        .host_busy1(1'b0),
        .compartment_count0(11'd1),
        .synapse_count0(16'd2),
        .route_count0(13'd2),
        .compartment_count1(11'd1),
        .synapse_count1(16'd2),
        .route_count1(13'd2),
        .core0_start(core0_start),
        .core0_ready(1'b1),
        .core0_done(core0_done),
        .core0_packet_count(core0_packet_count),
        .core0_status(core0_status),
        .core1_start(core1_start),
        .core1_ready(1'b1),
        .core1_done(core1_done),
        .core1_packet_count(core1_packet_count),
        .core1_status(core1_status),
        .core0_event_count(core0_event_count),
        .core1_event_count(core1_event_count),
        .core_timestep(core_timestep),
        .core0_packet_mem_en(core0_packet_mem_en),
        .core0_packet_mem_addr(core0_packet_mem_addr),
        .core0_packet_mem_data(core0_packet_mem_data),
        .core1_packet_mem_en(core1_packet_mem_en),
        .core1_packet_mem_addr(core1_packet_mem_addr),
        .core1_packet_mem_data(core1_packet_mem_data),
        .core0_event_mem_we(core0_event_mem_we),
        .core0_event_mem_addr(core0_event_mem_addr),
        .core0_event_mem_data(core0_event_mem_data),
        .core1_event_mem_we(core1_event_mem_we),
        .core1_event_mem_addr(core1_event_mem_addr),
        .core1_event_mem_data(core1_event_mem_data),
        .busy(busy),
        .tick_done(tick_done),
        .start_blocked(start_blocked),
        .epoch_loaded(epoch_loaded),
        .current_timestep(current_timestep),
        .current_event_count0(current_event_count0),
        .current_event_count1(current_event_count1),
        .next_event_count0(next_event_count0),
        .next_event_count1(next_event_count1),
        .in_flight_count(in_flight_count),
        .barrier_completed_mask(barrier_completed_mask),
        .barrier_can_advance(barrier_can_advance),
        .local_packet_count(local_packet_count),
        .remote_packet_count(remote_packet_count),
        .completed_ticks(completed_ticks),
        .active_cycles(active_cycles),
        .last_tick_cycles(last_tick_cycles),
        .error_physical_capacity(error_physical_capacity),
        .error_event_overflow(error_event_overflow),
        .error_event_axon(error_event_axon),
        .error_core_status(error_core_status),
        .error_router_bad_valid(error_router_bad_valid),
        .error_router_bad_destination(error_router_bad_destination),
        .error_router_bad_timestep(error_router_bad_timestep)
    );

    always @(posedge clk) begin
        if (core0_packet_mem_en)
            core0_packet_mem_data <= packet_mem0[core0_packet_mem_addr[2:0]];
        if (core1_packet_mem_en)
            core1_packet_mem_data <= packet_mem1[core1_packet_mem_addr[2:0]];

        if (core0_event_mem_we)
            event_mem0[core0_event_mem_addr[2:0]] <= core0_event_mem_data;
        if (core1_event_mem_we)
            event_mem1[core1_event_mem_addr[2:0]] <= core1_event_mem_data;

        core0_done <= 1'b0;
        core1_done <= 1'b0;
        if (core0_start)
            core0_delay <= 3;
        else if (core0_delay > 0) begin
            core0_delay <= core0_delay - 1;
            if (core0_delay == 1)
                core0_done <= 1'b1;
        end
        if (core1_start)
            core1_delay <= 3;
        else if (core1_delay > 0) begin
            core1_delay <= core1_delay - 1;
            if (core1_delay == 1)
                core1_done <= 1'b1;
        end
    end

    task pulse_epoch_load;
        begin
            @(negedge clk);
            epoch_load = 1'b1;
            @(negedge clk);
            epoch_load = 1'b0;
        end
    endtask

    task pulse_tick_start;
        begin
            @(negedge clk);
            tick_start = 1'b1;
            @(negedge clk);
            tick_start = 1'b0;
        end
    endtask

    task wait_tick_done;
        begin
            timeout = 0;
            while (!tick_done && timeout < 300) begin
                @(posedge clk);
                timeout = timeout + 1;
            end
            if (!tick_done) begin
                $display("FAIL: controller tick timed out busy=%0d in_flight=%0d completed=%b", busy, in_flight_count, barrier_completed_mask);
                $fatal(1);
            end
        end
    endtask

    task check_no_errors;
        begin
            if (error_physical_capacity || error_event_overflow || error_event_axon ||
                error_core_status || error_router_bad_valid ||
                error_router_bad_destination || error_router_bad_timestep) begin
                $display("FAIL: unexpected P04 controller error flags cap=%0d overflow=%0d axon=%0d core=%0d valid=%0d dst=%0d time=%0d",
                    error_physical_capacity, error_event_overflow, error_event_axon,
                    error_core_status, error_router_bad_valid,
                    error_router_bad_destination, error_router_bad_timestep);
                $fatal(1);
            end
        end
    endtask

    initial begin
        for (i = 0; i < 8; i = i + 1) begin
            packet_mem0[i] = 0;
            packet_mem1[i] = 0;
            event_mem0[i] = 0;
            event_mem1[i] = 0;
        end

        // Tick 0: each source emits one local and one remote packet. The two
        // core done pulses occur together, exercising simultaneous source drain.
        packet_mem0[0] = make_packet(7'd0, 12'd1, 32'd1);
        packet_mem0[1] = make_packet(7'd1, 12'd2, 32'd1);
        packet_mem1[0] = make_packet(7'd1, 12'd1, 32'd1);
        packet_mem1[1] = make_packet(7'd0, 12'd2, 32'd1);
        core0_packet_count = 13'd2;
        core1_packet_count = 13'd2;

        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        epoch_timestep = 0;
        epoch_event_count0 = 1;
        epoch_event_count1 = 1;
        pulse_epoch_load();
        if (!epoch_loaded || current_timestep != 0 ||
            current_event_count0 != 1 || current_event_count1 != 1) begin
            $display("FAIL: epoch load did not establish initial state");
            $fatal(1);
        end

        pulse_tick_start();
        wait_tick_done();
        check_no_errors();
        if (current_timestep != 1 || current_event_count0 != 2 ||
            current_event_count1 != 2 || local_packet_count != 2 ||
            remote_packet_count != 2 || completed_ticks != 1) begin
            $display("FAIL: tick0 completion mismatch time=%0d ev=%0d/%0d local=%0d remote=%0d completed=%0d",
                current_timestep, current_event_count0, current_event_count1,
                local_packet_count, remote_packet_count, completed_ticks);
            $fatal(1);
        end
        if (!((event_mem0[0] == 1 && event_mem0[1] == 2) ||
              (event_mem0[0] == 2 && event_mem0[1] == 1))) begin
            $display("FAIL: core0 next-event memory mismatch %0d %0d", event_mem0[0], event_mem0[1]);
            $fatal(1);
        end
        if (!((event_mem1[0] == 1 && event_mem1[1] == 2) ||
              (event_mem1[0] == 2 && event_mem1[1] == 1))) begin
            $display("FAIL: core1 next-event memory mismatch %0d %0d", event_mem1[0], event_mem1[1]);
            $fatal(1);
        end

        // Tick 1 uses reversed legal service priority and target timestep 2.
        service_reverse = 1'b1;
        packet_mem0[0] = make_packet(7'd0, 12'd1, 32'd2);
        packet_mem0[1] = make_packet(7'd1, 12'd2, 32'd2);
        packet_mem1[0] = make_packet(7'd1, 12'd1, 32'd2);
        packet_mem1[1] = make_packet(7'd0, 12'd2, 32'd2);
        pulse_tick_start();
        wait_tick_done();
        check_no_errors();
        if (current_timestep != 2 || current_event_count0 != 2 ||
            current_event_count1 != 2 || local_packet_count != 2 ||
            remote_packet_count != 2 || completed_ticks != 2) begin
            $display("FAIL: tick1 reversed-service completion mismatch");
            $fatal(1);
        end

        // A fresh epoch with an event count outside the *physical fixture*
        // allocation must block start and flag the physical-capacity condition.
        epoch_timestep = 10;
        epoch_event_count0 = 9;
        epoch_event_count1 = 0;
        pulse_epoch_load();
        pulse_tick_start();
        @(posedge clk);
        if (!start_blocked || !error_physical_capacity || busy) begin
            $display("FAIL: physical fixture capacity guard did not block start");
            $fatal(1);
        end

        $display("PASS: P04 two-core controller directed test completed successfully.");
        $finish;
    end
endmodule
