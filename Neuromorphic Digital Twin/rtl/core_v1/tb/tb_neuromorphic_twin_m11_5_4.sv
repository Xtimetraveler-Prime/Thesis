`timescale 1ns/1ps

module tb_neuromorphic_twin_m11_5_4;
    `include "generated_m11_5_4_integrated_vectors.svh"

    logic ap_clk = 1'b0;
    logic ap_rst = 1'b1;
    always #5 ap_clk = ~ap_clk;

    logic core_reset_start = 0;
    logic tick_start = 0;
    logic [8:0] neuron_count = M11_5_4I_NEURON_COUNT;
    logic [10:0] axon_count = M11_5_4I_AXON_COUNT;
    logic [12:0] synapse_count = M11_5_4I_SYNAPSE_COUNT;
    logic [4:0] format_count = M11_5_4I_FORMAT_COUNT;
    logic [12:0] external_event_count = 0;
    logic [12:0] route_count = M11_5_4I_ROUTE_COUNT;

    logic busy, core_reset_done, tick_done, fault;
    logic [31:0] tick;
    logic [7:0] fault_code, active_neuron;
    logic recurrent_current_bank;
    logic [12:0] recurrent_current_count;
    logic [12:0] last_consumed_recurrent_count, last_routed_count;

    logic config_we = 0;
    logic [7:0] config_addr = 0;
    logic [127:0] config_wdata = 0;
    logic state_we = 0;
    logic [7:0] state_addr = 0;
    logic [63:0] state_wdata = 0;
    logic format_we = 0;
    logic [3:0] format_addr = 0;
    logic [15:0] format_wdata = 0;
    logic synapse_we = 0;
    logic [11:0] synapse_addr = 0;
    logic [31:0] synapse_wdata = 0;
    logic row_we = 0;
    logic [10:0] row_addr = 0;
    logic [31:0] row_wdata = 0;
    logic external_we = 0;
    logic [11:0] external_addr = 0;
    logic [15:0] external_wdata = 0;
    logic route_row_we = 0;
    logic [8:0] route_row_addr = 0;
    logic [31:0] route_row_wdata = 0;
    logic route_target_we = 0;
    logic [11:0] route_target_addr = 0;
    logic [15:0] route_target_wdata = 0;

    logic debug_re = 0;
    logic [7:0] debug_addr = 0;
    logic debug_rvalid;
    logic [127:0] debug_config_rdata;
    logic [63:0] debug_state_rdata;
    logic signed [63:0] debug_accum_rdata;
    logic debug_spike_rdata;

    logic recurrent_debug_re = 0;
    logic recurrent_debug_bank = 0;
    logic [11:0] recurrent_debug_addr = 0;
    logic recurrent_debug_rvalid;
    logic [15:0] recurrent_debug_rdata;
    logic [12:0] recurrent_bank0_count, recurrent_bank1_count;

    neuromorphic_twin_m11_5_4_wrapper dut (.*);

    task automatic write_config(input integer index, input logic [127:0] value);
        begin
            @(negedge ap_clk); config_we=1; config_addr=index[7:0]; config_wdata=value;
            @(negedge ap_clk); config_we=0;
        end
    endtask
    task automatic write_state(input integer index, input logic [63:0] value);
        begin
            @(negedge ap_clk); state_we=1; state_addr=index[7:0]; state_wdata=value;
            @(negedge ap_clk); state_we=0;
        end
    endtask
    task automatic write_format(input integer index, input logic [15:0] value);
        begin
            @(negedge ap_clk); format_we=1; format_addr=index[3:0]; format_wdata=value;
            @(negedge ap_clk); format_we=0;
        end
    endtask
    task automatic write_synapse(input integer index, input logic [31:0] value);
        begin
            @(negedge ap_clk); synapse_we=1; synapse_addr=index[11:0]; synapse_wdata=value;
            @(negedge ap_clk); synapse_we=0;
        end
    endtask
    task automatic write_weight_row(input integer index, input logic [31:0] value);
        begin
            @(negedge ap_clk); row_we=1; row_addr=index[10:0]; row_wdata=value;
            @(negedge ap_clk); row_we=0;
        end
    endtask
    task automatic write_route_row(input integer index, input logic [31:0] value);
        begin
            @(negedge ap_clk); route_row_we=1; route_row_addr=index[8:0]; route_row_wdata=value;
            @(negedge ap_clk); route_row_we=0;
        end
    endtask
    task automatic write_route_target(input integer index, input logic [15:0] value);
        begin
            @(negedge ap_clk); route_target_we=1; route_target_addr=index[11:0]; route_target_wdata=value;
            @(negedge ap_clk); route_target_we=0;
        end
    endtask
    task automatic write_external0(input logic [15:0] value);
        begin
            @(negedge ap_clk); external_we=1; external_addr=0; external_wdata=value;
            @(negedge ap_clk); external_we=0;
        end
    endtask

    task automatic pulse_reset;
        integer cycles;
        begin
            @(negedge ap_clk); core_reset_start=1;
            @(negedge ap_clk); core_reset_start=0;
            for (cycles=0; cycles<1000; cycles=cycles+1) begin
                @(posedge ap_clk); #1;
                if (fault) $fatal(1,"reset fault 0x%02x", fault_code);
                if (core_reset_done) return;
            end
            $fatal(1,"timeout waiting for M11.5.4 core reset");
        end
    endtask

    task automatic run_tick(input integer previous_tick);
        integer cycles;
        begin
            @(negedge ap_clk); tick_start=1;
            @(negedge ap_clk); tick_start=0;
            for (cycles=0; cycles<20000; cycles=cycles+1) begin
                @(posedge ap_clk); #1;
                if (fault)
                    $fatal(1,"tick fault 0x%02x tick=%0d active_neuron=%0d", fault_code, tick, active_neuron);
                if (!tick_done && tick !== previous_tick)
                    $fatal(1,"architectural tick became visible before Phase-F commit: previous=%0d actual=%0d", previous_tick, tick);
                if (tick_done) return;
            end
            $fatal(1,"timeout waiting for M11.5.4 tick_done tick=%0d", tick);
        end
    endtask

    task automatic read_neuron(
        input integer index,
        output logic [63:0] state_value,
        output logic spike_value
    );
        integer cycles;
        begin
            @(negedge ap_clk); debug_addr=index[7:0]; debug_re=1;
            for (cycles=0; cycles<20; cycles=cycles+1) begin
                @(posedge ap_clk); #1;
                if (debug_rvalid) begin
                    state_value=debug_state_rdata;
                    spike_value=debug_spike_rdata;
                    @(negedge ap_clk); debug_re=0;
                    return;
                end
            end
            debug_re=0;
            $fatal(1,"timeout reading neuron %0d", index);
        end
    endtask

    task automatic read_recurrent(
        input logic bank,
        input integer index,
        output logic [15:0] value
    );
        integer cycles;
        begin
            @(negedge ap_clk); recurrent_debug_bank=bank; recurrent_debug_addr=index[11:0]; recurrent_debug_re=1;
            for (cycles=0; cycles<20; cycles=cycles+1) begin
                @(posedge ap_clk); #1;
                if (recurrent_debug_rvalid) begin
                    value=recurrent_debug_rdata;
                    @(negedge ap_clk); recurrent_debug_re=0;
                    return;
                end
            end
            recurrent_debug_re=0;
            $fatal(1,"timeout reading recurrent bank=%0d index=%0d", bank, index);
        end
    endtask

    initial begin : test_sequence
        integer i, t;
        integer flat;
        logic [63:0] observed_state;
        logic observed_spike;
        logic [15:0] observed_event;

        repeat (5) @(posedge ap_clk);
        @(negedge ap_clk); ap_rst=0;

        for (i=0; i<M11_5_4I_NEURON_COUNT; i=i+1) begin
            write_config(i, M11_5_4I_CONFIG_WORDS[i]);
            write_state(i, M11_5_4I_INITIAL_STATE_WORDS[i]);
        end
        for (i=0; i<M11_5_4I_FORMAT_COUNT; i=i+1)
            write_format(i, M11_5_4I_FORMAT_WORDS[i]);
        for (i=0; i<M11_5_4I_SYNAPSE_COUNT; i=i+1)
            write_synapse(i, M11_5_4I_SYNAPSE_WORDS[i]);
        for (i=0; i<=M11_5_4I_AXON_COUNT; i=i+1)
            write_weight_row(i, M11_5_4I_WEIGHT_ROWS[i]);
        for (i=0; i<=M11_5_4I_NEURON_COUNT; i=i+1)
            write_route_row(i, M11_5_4I_ROUTE_ROWS[i]);
        for (i=0; i<M11_5_4I_ROUTE_COUNT; i=i+1)
            write_route_target(i, M11_5_4I_ROUTE_TARGETS[i]);

        pulse_reset();
        if (tick !== 0 || recurrent_current_bank !== 0 || recurrent_current_count !== 0)
            $fatal(1,"reset did not establish tick0/empty bank0");

        for (t=0; t<M11_5_4I_TICK_COUNT; t=t+1) begin
            external_event_count = M11_5_4I_EXTERNAL_COUNTS[t];
            if (external_event_count != 0)
                write_external0(M11_5_4I_EXTERNAL_EVENT0[t]);

            run_tick(t);

            if (tick !== (t+1))
                $fatal(1,"tick counter mismatch expected=%0d actual=%0d", t+1, tick);
            if (last_consumed_recurrent_count !== M11_5_4I_EXPECTED_CONSUMED_COUNTS[t])
                $fatal(1,"consumed count mismatch tick=%0d expected=%0d actual=%0d", t,
                       M11_5_4I_EXPECTED_CONSUMED_COUNTS[t], last_consumed_recurrent_count);
            if (last_routed_count !== M11_5_4I_EXPECTED_ROUTED_COUNTS[t])
                $fatal(1,"routed count mismatch tick=%0d expected=%0d actual=%0d", t,
                       M11_5_4I_EXPECTED_ROUTED_COUNTS[t], last_routed_count);
            if (recurrent_current_bank !== M11_5_4I_EXPECTED_CURRENT_BANK[t])
                $fatal(1,"current bank mismatch tick=%0d", t);
            if (recurrent_current_count !== M11_5_4I_EXPECTED_CURRENT_COUNTS[t])
                $fatal(1,"current recurrent count mismatch tick=%0d", t);

            if (recurrent_current_count != 0) begin
                read_recurrent(recurrent_current_bank, 0, observed_event);
                if (observed_event !== M11_5_4I_EXPECTED_CURRENT_EVENT0[t])
                    $fatal(1,"current recurrent event mismatch tick=%0d expected=%0d actual=%0d", t,
                           M11_5_4I_EXPECTED_CURRENT_EVENT0[t], observed_event);
            end

            for (i=0; i<M11_5_4I_NEURON_COUNT; i=i+1) begin
                flat = t*M11_5_4I_NEURON_COUNT+i;
                read_neuron(i, observed_state, observed_spike);
                if (observed_state !== M11_5_4I_EXPECTED_STATES[flat])
                    $fatal(1,"state mismatch tick=%0d neuron=%0d expected=%h actual=%h", t, i,
                           M11_5_4I_EXPECTED_STATES[flat], observed_state);
                if (observed_spike !== M11_5_4I_EXPECTED_SPIKES[flat])
                    $fatal(1,"spike mismatch tick=%0d neuron=%0d expected=%0d actual=%0d", t, i,
                           M11_5_4I_EXPECTED_SPIKES[flat], observed_spike);
            end
        end

        if (recurrent_bank0_count !== 0 || recurrent_bank1_count !== 0)
            $fatal(1,"final empty tick did not logically clear both recurrent bank counts");

        $display("M11.5.4 packed-M08 + real-HLS recurrent multi-tick passed: ticks=4, neurons=3, routes=2, tag=0x%08x", M11_5_4I_TAG);
        $finish;
    end
endmodule
