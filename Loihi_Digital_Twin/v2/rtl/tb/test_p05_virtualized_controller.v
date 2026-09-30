`timescale 1ns/1ps

module test_p05_virtualized_controller;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg epoch_load = 1'b0;
    reg [31:0] epoch_timestep = 0;
    reg tick_start = 1'b0;
    reg service_reverse = 1'b0;
    reg host_busy = 1'b0;
    reg [191:0] context_metadata = 0;

    wire core_start;
    reg core_done = 1'b0;
    reg [12:0] core_packet_count = 0;
    reg [31:0] core_status = 0;
    wire [10:0] core_compartment_count;
    wire [12:0] core_event_count;
    wire [15:0] core_synapse_count;
    wire [12:0] core_route_count;
    wire [31:0] core_timestep;
    wire [1:0] active_context_slot;
    wire [6:0] active_logical_core_id;
    wire event_read_bank;

    wire packet_mem_en;
    wire [1:0] packet_mem_context;
    wire [11:0] packet_mem_addr;
    reg [63:0] packet_mem_data = 0;
    wire event_mem_we;
    wire [1:0] event_mem_context;
    wire [11:0] event_mem_addr;
    wire [31:0] event_mem_data;

    wire busy;
    wire tick_done;
    wire start_blocked;
    wire epoch_loaded;
    wire [31:0] current_timestep;
    wire [38:0] current_event_counts_flat;
    wire [38:0] next_event_counts_flat;
    wire [2:0] barrier_completed_mask;
    wire barrier_can_advance;
    wire [31:0] local_packet_count;
    wire [31:0] remote_packet_count;
    wire [31:0] completed_ticks;
    wire [63:0] active_cycles;
    wire [63:0] last_tick_cycles;
    wire error_metadata;
    wire error_event_overflow;
    wire error_bad_packet_valid;
    wire error_bad_destination;
    wire error_bad_timestep;
    wire error_core_status;

    integer core_delay = 0;
    integer timeout = 0;
    integer start_count = 0;
    integer write_count = 0;
    reg [1:0] start_slots [0:5];
    reg [1:0] write_slots [0:5];
    reg [11:0] write_axons [0:5];
    reg observed_bank_during_tick;

    function [63:0] metadata_word;
        input [6:0] logical_core_id;
        input [12:0] initial_event_count;
        reg [63:0] word;
        begin
            word = 64'd0;
            word[6:0] = logical_core_id;
            word[17:7] = 11'd1;
            word[33:18] = 16'd1;
            word[46:34] = 13'd1;
            word[59:47] = initial_event_count;
            metadata_word = word;
        end
    endfunction

    function [63:0] packet_for_context;
        input [1:0] context_slot;
        input [31:0] timestep;
        reg [6:0] destination_core;
        reg [11:0] destination_axon;
        reg [63:0] word;
        begin
            case (context_slot)
                2'd0: begin destination_core = 7'd42; destination_axon = 12'd11; end
                2'd1: begin destination_core = 7'd99; destination_axon = 12'd12; end
                2'd2: begin destination_core = 7'd7; destination_axon = 12'd10; end
                default: begin destination_core = 7'd127; destination_axon = 12'd0; end
            endcase
            word = 64'd0;
            word[6:0] = destination_core;
            word[18:7] = destination_axon;
            word[28:19] = 10'd0;
            word[60:29] = timestep + 32'd1;
            word[61] = 1'b1;
            packet_for_context = word;
        end
    endfunction

    p05_virtualized_controller dut (
        .clk(clk),
        .resetn(resetn),
        .epoch_load(epoch_load),
        .epoch_timestep(epoch_timestep),
        .tick_start(tick_start),
        .service_reverse(service_reverse),
        .host_busy(host_busy),
        .context_metadata(context_metadata),
        .core_start(core_start),
        .core_ready(1'b0),
        .core_done(core_done),
        .core_packet_count(core_packet_count),
        .core_status(core_status),
        .core_compartment_count(core_compartment_count),
        .core_event_count(core_event_count),
        .core_synapse_count(core_synapse_count),
        .core_route_count(core_route_count),
        .core_timestep(core_timestep),
        .active_context_slot(active_context_slot),
        .active_logical_core_id(active_logical_core_id),
        .event_read_bank(event_read_bank),
        .packet_mem_en(packet_mem_en),
        .packet_mem_context(packet_mem_context),
        .packet_mem_addr(packet_mem_addr),
        .packet_mem_data(packet_mem_data),
        .event_mem_we(event_mem_we),
        .event_mem_context(event_mem_context),
        .event_mem_addr(event_mem_addr),
        .event_mem_data(event_mem_data),
        .busy(busy),
        .tick_done(tick_done),
        .start_blocked(start_blocked),
        .epoch_loaded(epoch_loaded),
        .current_timestep(current_timestep),
        .current_event_counts_flat(current_event_counts_flat),
        .next_event_counts_flat(next_event_counts_flat),
        .barrier_completed_mask(barrier_completed_mask),
        .barrier_can_advance(barrier_can_advance),
        .local_packet_count(local_packet_count),
        .remote_packet_count(remote_packet_count),
        .completed_ticks(completed_ticks),
        .active_cycles(active_cycles),
        .last_tick_cycles(last_tick_cycles),
        .error_metadata(error_metadata),
        .error_event_overflow(error_event_overflow),
        .error_bad_packet_valid(error_bad_packet_valid),
        .error_bad_destination(error_bad_destination),
        .error_bad_timestep(error_bad_timestep),
        .error_core_status(error_core_status)
    );

    always @(posedge clk) begin
        core_done <= 1'b0;
        if (core_start) begin
            start_slots[start_count] <= active_context_slot;
            start_count <= start_count + 1;
            core_delay <= 3;
            core_packet_count <= 13'd1;
            core_status <= 32'd0;
        end else if (core_delay > 0) begin
            core_delay <= core_delay - 1;
            if (core_delay == 1)
                core_done <= 1'b1;
        end

        if (packet_mem_en)
            packet_mem_data <= packet_for_context(packet_mem_context, core_timestep);

        if (event_mem_we) begin
            write_slots[write_count] <= event_mem_context;
            write_axons[write_count] <= event_mem_data[11:0];
            write_count <= write_count + 1;
        end

        if (busy)
            observed_bank_during_tick <= event_read_bank;
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
            while (!tick_done && timeout < 500) begin
                @(posedge clk);
                timeout = timeout + 1;
            end
            if (!tick_done) begin
                $display("FAIL: P05 tick timeout state busy=%0d slot=%0d completed=%b", busy, active_context_slot, barrier_completed_mask);
                $fatal(1);
            end
        end
    endtask

    task check_no_errors;
        begin
            if (error_metadata || error_event_overflow || error_bad_packet_valid ||
                error_bad_destination || error_bad_timestep || error_core_status) begin
                $display("FAIL: P05 unexpected errors metadata=%0d overflow=%0d valid=%0d dst=%0d time=%0d core=%0d",
                    error_metadata, error_event_overflow, error_bad_packet_valid,
                    error_bad_destination, error_bad_timestep, error_core_status);
                $fatal(1);
            end
        end
    endtask

    initial begin
        observed_bank_during_tick = 1'b0;
        context_metadata[63:0] = metadata_word(7, 13'd1);
        context_metadata[127:64] = metadata_word(42, 13'd0);
        context_metadata[191:128] = metadata_word(99, 13'd0);

        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        pulse_epoch_load();
        if (!epoch_loaded || current_timestep != 0 || event_read_bank != 0) begin
            $display("FAIL: P05 epoch load mismatch loaded=%0d time=%0d bank=%0d", epoch_loaded, current_timestep, event_read_bank);
            $fatal(1);
        end
        if (current_event_counts_flat[12:0] != 1 ||
            current_event_counts_flat[25:13] != 0 ||
            current_event_counts_flat[38:26] != 0) begin
            $display("FAIL: P05 initial event counts mismatch");
            $fatal(1);
        end

        service_reverse = 1'b0;
        observed_bank_during_tick = event_read_bank;
        pulse_tick_start();
        wait_tick_done();
        check_no_errors();

        if (start_slots[0] != 0 || start_slots[1] != 1 || start_slots[2] != 2) begin
            $display("FAIL: P05 forward service order mismatch %0d %0d %0d", start_slots[0], start_slots[1], start_slots[2]);
            $fatal(1);
        end
        if (write_slots[0] != 1 || write_axons[0] != 11 ||
            write_slots[1] != 2 || write_axons[1] != 12 ||
            write_slots[2] != 0 || write_axons[2] != 10) begin
            $display("FAIL: P05 routed event writes mismatch");
            $fatal(1);
        end
        if (current_timestep != 1 || completed_ticks != 1 || event_read_bank != 1) begin
            $display("FAIL: P05 first barrier advance mismatch time=%0d ticks=%0d bank=%0d", current_timestep, completed_ticks, event_read_bank);
            $fatal(1);
        end
        if (current_event_counts_flat[12:0] != 1 ||
            current_event_counts_flat[25:13] != 1 ||
            current_event_counts_flat[38:26] != 1) begin
            $display("FAIL: P05 next-event counts did not become current counts");
            $fatal(1);
        end
        if (local_packet_count != 0 || remote_packet_count != 3) begin
            $display("FAIL: P05 traffic counts mismatch local=%0d remote=%0d", local_packet_count, remote_packet_count);
            $fatal(1);
        end
        if (last_tick_cycles == 0) begin
            $display("FAIL: P05 first tick reported zero physical cycles");
            $fatal(1);
        end

        service_reverse = 1'b1;
        observed_bank_during_tick = event_read_bank;
        pulse_tick_start();
        wait_tick_done();
        check_no_errors();

        if (start_slots[3] != 2 || start_slots[4] != 1 || start_slots[5] != 0) begin
            $display("FAIL: P05 reverse service order mismatch %0d %0d %0d", start_slots[3], start_slots[4], start_slots[5]);
            $fatal(1);
        end
        if (current_timestep != 2 || completed_ticks != 2 || event_read_bank != 0) begin
            $display("FAIL: P05 second barrier advance mismatch time=%0d ticks=%0d bank=%0d", current_timestep, completed_ticks, event_read_bank);
            $fatal(1);
        end
        if (local_packet_count != 0 || remote_packet_count != 3) begin
            $display("FAIL: P05 second traffic counts mismatch local=%0d remote=%0d", local_packet_count, remote_packet_count);
            $fatal(1);
        end

        $display("PASS: P05 virtualized controller directed test completed successfully.");
        $finish;
    end
endmodule
