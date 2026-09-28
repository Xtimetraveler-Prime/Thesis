`timescale 1ns/1ps

module tb_neuron_array_controller_v1;

    logic ap_clk = 1'b0;
    always #5 ap_clk = ~ap_clk;

    logic ap_rst;
    logic core_reset_start;
    logic tick_start;
    logic [8:0] neuron_count;
    logic busy;
    logic core_reset_done;
    logic tick_done;
    logic [31:0] tick;
    logic fault;
    logic [7:0] fault_code;
    logic [7:0] active_neuron;

    logic config_we;
    logic [7:0] config_addr;
    logic [127:0] config_wdata;
    logic state_we;
    logic [7:0] state_addr;
    logic [63:0] state_wdata;
    logic accum_we;
    logic [7:0] accum_addr;
    logic signed [63:0] accum_wdata;

    logic debug_re;
    logic [7:0] debug_addr;
    logic debug_rvalid;
    logic [127:0] debug_config_rdata;
    logic [63:0] debug_state_rdata;
    logic signed [63:0] debug_accum_rdata;
    logic debug_spike_rdata;

    logic hls_ap_start;
    logic hls_ap_done;
    logic hls_ap_idle;
    logic hls_ap_ready;

    logic signed [23:0] hls_current_before;
    logic signed [23:0] hls_voltage_before;
    logic [15:0] hls_refractory_before;
    logic signed [63:0] hls_synaptic_input;
    logic [12:0] hls_current_decay;
    logic [12:0] hls_voltage_decay;
    logic signed [23:0] hls_threshold;
    logic signed [23:0] hls_bias;
    logic signed [23:0] hls_reset_voltage;
    logic [15:0] hls_refractory_ticks;

    logic signed [23:0] hls_current_after;
    logic hls_current_after_ap_vld;
    logic signed [23:0] hls_voltage_after;
    logic hls_voltage_after_ap_vld;
    logic [15:0] hls_refractory_after;
    logic hls_refractory_after_ap_vld;
    logic hls_spiked;
    logic hls_spiked_ap_vld;

    neuron_array_controller_v1 dut (
        .ap_clk,
        .ap_rst,
        .core_reset_start,
        .tick_start,
        .neuron_count,
        .busy,
        .core_reset_done,
        .tick_done,
        .tick,
        .fault,
        .fault_code,
        .active_neuron,
        .config_we,
        .config_addr,
        .config_wdata,
        .state_we,
        .state_addr,
        .state_wdata,
        .accum_we,
        .accum_addr,
        .accum_wdata,
        .debug_re,
        .debug_addr,
        .debug_rvalid,
        .debug_config_rdata,
        .debug_state_rdata,
        .debug_accum_rdata,
        .debug_spike_rdata,
        .hls_ap_start,
        .hls_ap_done,
        .hls_ap_idle,
        .hls_ap_ready,
        .hls_current_before,
        .hls_voltage_before,
        .hls_refractory_before,
        .hls_synaptic_input,
        .hls_current_decay,
        .hls_voltage_decay,
        .hls_threshold,
        .hls_bias,
        .hls_reset_voltage,
        .hls_refractory_ticks,
        .hls_current_after,
        .hls_current_after_ap_vld,
        .hls_voltage_after,
        .hls_voltage_after_ap_vld,
        .hls_refractory_after,
        .hls_refractory_after_ap_vld,
        .hls_spiked,
        .hls_spiked_ap_vld
    );

    // Sequencer-only mock for the already independently verified HLS neuron IP.
    // It intentionally asserts ap_ready and ap_done together to exercise the
    // non-pipelined ap_ctrl_hs edge case seen in the synthesized M11.3 core.
    logic mock_active;
    logic signed [23:0] mock_current_before;
    logic signed [23:0] mock_voltage_before;
    logic [15:0] mock_refractory_before;
    logic signed [63:0] mock_synaptic_input;

    assign hls_ap_idle = !mock_active;

    always_ff @(posedge ap_clk) begin
        if (ap_rst) begin
            mock_active                    <= 1'b0;
            hls_ap_ready                   <= 1'b0;
            hls_ap_done                    <= 1'b0;
            hls_current_after              <= 24'sd0;
            hls_voltage_after              <= 24'sd0;
            hls_refractory_after           <= 16'd0;
            hls_spiked                     <= 1'b0;
            hls_current_after_ap_vld       <= 1'b0;
            hls_voltage_after_ap_vld       <= 1'b0;
            hls_refractory_after_ap_vld    <= 1'b0;
            hls_spiked_ap_vld              <= 1'b0;
            mock_current_before            <= 24'sd0;
            mock_voltage_before            <= 24'sd0;
            mock_refractory_before         <= 16'd0;
            mock_synaptic_input            <= 64'sd0;
        end else begin
            hls_ap_ready                <= 1'b0;
            hls_ap_done                 <= 1'b0;
            hls_current_after_ap_vld    <= 1'b0;
            hls_voltage_after_ap_vld    <= 1'b0;
            hls_refractory_after_ap_vld <= 1'b0;
            hls_spiked_ap_vld           <= 1'b0;

            if (!mock_active && hls_ap_start) begin
                mock_current_before    <= hls_current_before;
                mock_voltage_before    <= hls_voltage_before;
                mock_refractory_before <= hls_refractory_before;
                mock_synaptic_input    <= hls_synaptic_input;
                mock_active            <= 1'b1;
            end else if (mock_active) begin
                hls_current_after <=
                    mock_current_before + $signed(mock_synaptic_input[23:0]);
                hls_voltage_after <= mock_voltage_before + 24'sd1;
                hls_refractory_after <= mock_refractory_before;
                hls_spiked <= mock_synaptic_input[0];

                hls_current_after_ap_vld    <= 1'b1;
                hls_voltage_after_ap_vld    <= 1'b1;
                hls_refractory_after_ap_vld <= 1'b1;
                hls_spiked_ap_vld           <= 1'b1;
                hls_ap_ready                <= 1'b1;
                hls_ap_done                 <= 1'b1;
                mock_active                 <= 1'b0;
            end
        end
    end

    function automatic [127:0] make_config(input logic signed [23:0] reset_voltage);
        logic [127:0] word;
        begin
            word = 128'd0;
            word[12:0]   = 13'd0;
            word[25:13]  = 13'd0;
            word[49:26]  = $unsigned(24'sd100);
            word[73:50]  = $unsigned(24'sd0);
            word[97:74]  = $unsigned(reset_voltage);
            word[113:98] = 16'd0;
            make_config = word;
        end
    endfunction

    function automatic [63:0] make_state(
        input logic signed [23:0] current,
        input logic signed [23:0] voltage,
        input logic [15:0] refractory
    );
        make_state = {refractory, voltage, current};
    endfunction

    task automatic write_config(
        input logic [7:0] addr,
        input logic [127:0] data
    );
        begin
            @(negedge ap_clk);
            config_addr  = addr;
            config_wdata = data;
            config_we    = 1'b1;
            @(negedge ap_clk);
            config_we    = 1'b0;
        end
    endtask

    task automatic write_accum(
        input logic [7:0] addr,
        input logic signed [63:0] data
    );
        begin
            @(negedge ap_clk);
            accum_addr  = addr;
            accum_wdata = data;
            accum_we    = 1'b1;
            @(negedge ap_clk);
            accum_we    = 1'b0;
        end
    endtask

    task automatic read_and_check(
        input logic [7:0] addr,
        input logic [63:0] expected_state,
        input logic signed [63:0] expected_accum,
        input logic expected_spike
    );
        begin
            @(negedge ap_clk);
            debug_addr = addr;
            debug_re   = 1'b1;
            @(posedge ap_clk);
            #1;
            if (!debug_rvalid) begin
                $error("debug read for neuron %0d did not become valid", addr);
                $fatal(1);
            end
            if (debug_state_rdata !== expected_state) begin
                $error("state mismatch neuron %0d: expected=%h actual=%h",
                       addr, expected_state, debug_state_rdata);
                $fatal(1);
            end
            if (debug_accum_rdata !== expected_accum) begin
                $error("accumulator mismatch neuron %0d: expected=%0d actual=%0d",
                       addr, expected_accum, debug_accum_rdata);
                $fatal(1);
            end
            if (debug_spike_rdata !== expected_spike) begin
                $error("spike mismatch neuron %0d: expected=%0d actual=%0d",
                       addr, expected_spike, debug_spike_rdata);
                $fatal(1);
            end
            @(negedge ap_clk);
            debug_re = 1'b0;
        end
    endtask

    initial begin
        ap_rst          = 1'b1;
        core_reset_start = 1'b0;
        tick_start      = 1'b0;
        neuron_count    = 9'd3;
        config_we       = 1'b0;
        config_addr     = 8'd0;
        config_wdata    = 128'd0;
        state_we        = 1'b0;
        state_addr      = 8'd0;
        state_wdata     = 64'd0;
        accum_we        = 1'b0;
        accum_addr      = 8'd0;
        accum_wdata     = 64'sd0;
        debug_re        = 1'b0;
        debug_addr      = 8'd0;

        repeat (4) @(posedge ap_clk);
        @(negedge ap_clk);
        ap_rst = 1'b0;

        write_config(8'd0, make_config(-24'sd10));
        write_config(8'd1, make_config(-24'sd20));
        write_config(8'd2, make_config(-24'sd30));

        @(negedge ap_clk);
        core_reset_start = 1'b1;
        @(negedge ap_clk);
        core_reset_start = 1'b0;

        wait (core_reset_done === 1'b1);
        @(posedge ap_clk);

        if (fault) begin
            $error("unexpected fault after core reset: code=%0d", fault_code);
            $fatal(1);
        end
        if (tick !== 32'd0) begin
            $error("tick must be zero after core reset, got %0d", tick);
            $fatal(1);
        end

        read_and_check(8'd0, make_state(24'sd0, -24'sd10, 16'd0), 64'sd0, 1'b0);
        read_and_check(8'd1, make_state(24'sd0, -24'sd20, 16'd0), 64'sd0, 1'b0);
        read_and_check(8'd2, make_state(24'sd0, -24'sd30, 16'd0), 64'sd0, 1'b0);

        write_accum(8'd0, 64'sd11);
        write_accum(8'd1, 64'sd22);
        write_accum(8'd2, 64'sd33);

        @(negedge ap_clk);
        tick_start = 1'b1;
        @(negedge ap_clk);
        tick_start = 1'b0;

        wait (tick_done === 1'b1);
        @(posedge ap_clk);

        if (fault) begin
            $error("unexpected fault after tick: code=%0d", fault_code);
            $fatal(1);
        end
        if (tick !== 32'd1) begin
            $error("tick must increment exactly once, got %0d", tick);
            $fatal(1);
        end

        read_and_check(8'd0, make_state(24'sd11, -24'sd9, 16'd0), 64'sd0, 1'b1);
        read_and_check(8'd1, make_state(24'sd22, -24'sd19, 16'd0), 64'sd0, 1'b0);
        read_and_check(8'd2, make_state(24'sd33, -24'sd29, 16'd0), 64'sd0, 1'b1);

        $display("M11.5.2 neuron-array controller tests passed: 3 neurons, reset + 1 tick");
        $finish;
    end

endmodule
