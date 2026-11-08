// RTL-ONLY direct Verilog validation of generated HLS IP, NOT C/RTL co-sim,
// PS/PL integration, or physical board evidence. Source kernel is UNCHANGED.
// Compile with the actual HLS syn/verilog RTL and tool-derived register map.
// The stress test drives delayed ingress TVALID, repeated output TREADY stalls,
// asserts stable TDATA/TVALID on EVERY stalled AXIS beat and checks full trace.
// 2025.2 K26 Vivado IP-flow C struct padding: these specific widths/field
// offsets are checked against the known 128/192/128/192-bit top-level ports.
//
// Vitis AXIS structs use native C ABI field alignment, not concatenation of
// tightly packed bit fields. The 192-bit synapse word has 32-bit padding at
// bits 127:96 before delay[191:128]. The trace word has 16 bits padding
// between evaluated and delivered_count. Check this packing in actual RTL.
`timescale 1ns/1ps
`include "m05_rolling_regmap.svh"

module tb_m05_rolling_axis_stress;
    reg ap_clk = 1'b0;
    always #5 ap_clk = ~ap_clk;
    reg ap_rst_n = 1'b0;
    wire interrupt;

    reg [6:0] s_axi_control_AWADDR = 0;
    reg s_axi_control_AWVALID = 0;
    wire s_axi_control_AWREADY;
    reg [31:0] s_axi_control_WDATA = 0;
    reg [3:0] s_axi_control_WSTRB = 4'hf;
    reg s_axi_control_WVALID = 0;
    wire s_axi_control_WREADY;
    wire [1:0] s_axi_control_BRESP;
    wire s_axi_control_BVALID;
    reg s_axi_control_BREADY = 0;
    reg [6:0] s_axi_control_ARADDR = 0;
    reg s_axi_control_ARVALID = 0;
    wire s_axi_control_ARREADY;
    wire [31:0] s_axi_control_RDATA;
    wire [1:0] s_axi_control_RRESP;
    wire s_axi_control_RVALID;
    reg s_axi_control_RREADY = 0;

    wire [127:0] neurons_TDATA;
    reg neurons_TVALID = 0;
    wire neurons_TREADY;
    wire [191:0] synapses_TDATA;
    reg synapses_TVALID = 0;
    wire synapses_TREADY;
    wire [127:0] external_events_TDATA;
    reg external_events_TVALID = 0;
    wire external_events_TREADY;
    wire [191:0] trace_TDATA;
    wire trace_TVALID;
    wire trace_TREADY;

    // Named port mapping, never assume the Vivado IP wrapper has TLAST:
    // this HLS top's original synthesis report exposed ONLY TDATA/TVALID/TREADY.
    m05_rolling_replay dut (
        .ap_clk(ap_clk), .ap_rst_n(ap_rst_n), .interrupt(interrupt),
        .s_axi_control_AWADDR(s_axi_control_AWADDR),
        .s_axi_control_AWVALID(s_axi_control_AWVALID),
        .s_axi_control_AWREADY(s_axi_control_AWREADY),
        .s_axi_control_WDATA(s_axi_control_WDATA),
        .s_axi_control_WSTRB(s_axi_control_WSTRB),
        .s_axi_control_WVALID(s_axi_control_WVALID),
        .s_axi_control_WREADY(s_axi_control_WREADY),
        .s_axi_control_BRESP(s_axi_control_BRESP),
        .s_axi_control_BVALID(s_axi_control_BVALID),
        .s_axi_control_BREADY(s_axi_control_BREADY),
        .s_axi_control_ARADDR(s_axi_control_ARADDR),
        .s_axi_control_ARVALID(s_axi_control_ARVALID),
        .s_axi_control_ARREADY(s_axi_control_ARREADY),
        .s_axi_control_RDATA(s_axi_control_RDATA),
        .s_axi_control_RRESP(s_axi_control_RRESP),
        .s_axi_control_RVALID(s_axi_control_RVALID),
        .s_axi_control_RREADY(s_axi_control_RREADY),
        .neurons_TDATA(neurons_TDATA),
        .neurons_TVALID(neurons_TVALID),
        .neurons_TREADY(neurons_TREADY),
        .synapses_TDATA(synapses_TDATA),
        .synapses_TVALID(synapses_TVALID),
        .synapses_TREADY(synapses_TREADY),
        .external_events_TDATA(external_events_TDATA),
        .external_events_TVALID(external_events_TVALID),
        .external_events_TREADY(external_events_TREADY),
        .trace_TDATA(trace_TDATA),
        .trace_TVALID(trace_TVALID),
        .trace_TREADY(trace_TREADY)
    );

    integer cycle_count = 0;
    integer neurons_sent = 0;
    integer synapses_sent = 0;
    integer external_sent = 0;
    integer trace_received = 0;
    integer trace_stall_cycles = 0;
    integer neuron_stall_cycles = 0;
    integer synapse_stall_cycles = 0;
    integer external_stall_cycles = 0;
    integer ingress_gap_cycles = 0;
    reg enable_feeds = 0;

    reg stalled_trace_prior = 0;
    reg [191:0] prior_trace_word = 0;

    // Successful 12-tick workload:
    //   neuron0 at tick0 receives +5, fires and resets to 0.
    //   edge 0->1, +5, delay 8 => neuron1 fires at tick8.
    //   all 24 trace records must be received and in correct tick/neuron order.
    // Struct order: first member at least significant bits, native C padding.
    assign neurons_TDATA = {32'd0, 32'd5, 32'd0, 32'd0};
    assign synapses_TDATA = {64'd8, 32'd0, 32'd5, 32'd1, 32'd0};
    assign external_events_TDATA = {32'd5, 32'd0, 64'd0};

    // TREADY is LOW for ten of eleven consecutive cycles, forcing actual
    // DUT output stall regardless of absolute timing of neuron evaluation.
    assign trace_TREADY = ap_rst_n && (cycle_count % 11 == 0);

    always @(posedge ap_clk) begin
        if (!ap_rst_n) begin
            cycle_count <= 0;
            neurons_sent <= 0;
            synapses_sent <= 0;
            external_sent <= 0;
            trace_received <= 0;
            trace_stall_cycles <= 0;
            neuron_stall_cycles <= 0;
            synapse_stall_cycles <= 0;
            external_stall_cycles <= 0;
            ingress_gap_cycles <= 0;
            neurons_TVALID <= 0;
            synapses_TVALID <= 0;
            external_events_TVALID <= 0;
            stalled_trace_prior <= 0;
            prior_trace_word <= 0;
        end else begin
            cycle_count <= cycle_count + 1;
            if (cycle_count >= 200000)
                $fatal(1, "RTL_STRESS_FAIL timeout/deadlock at cycle %0d, outputs=%0d",
                       cycle_count, trace_received);

            // Hold VALID continuously until handshake; TDATA is a function
            // only of the immutable event word for each source.
            if (neurons_TVALID && neurons_TREADY) begin
                neurons_sent <= neurons_sent + 1;
                neurons_TVALID <= 0;
            end else if (!neurons_TVALID && enable_feeds &&
                         neurons_sent < 2 && cycle_count % 7 == 2) begin
                neurons_TVALID <= 1;
            end
            if (synapses_TVALID && synapses_TREADY) begin
                synapses_sent <= synapses_sent + 1;
                synapses_TVALID <= 0;
            end else if (!synapses_TVALID && enable_feeds &&
                         synapses_sent < 1 && cycle_count % 13 == 4) begin
                synapses_TVALID <= 1;
            end
            if (external_events_TVALID && external_events_TREADY) begin
                external_sent <= external_sent + 1;
                external_events_TVALID <= 0;
            end else if (!external_events_TVALID && enable_feeds &&
                         external_sent < 1 && cycle_count % 17 == 9) begin
                external_events_TVALID <= 1;
            end

            if (enable_feeds && (!neurons_TVALID || !synapses_TVALID ||
                                 !external_events_TVALID))
                ingress_gap_cycles <= ingress_gap_cycles + 1;
            if (neurons_TVALID && !neurons_TREADY)
                neuron_stall_cycles <= neuron_stall_cycles + 1;
            if (synapses_TVALID && !synapses_TREADY)
                synapse_stall_cycles <= synapse_stall_cycles + 1;
            if (external_events_TVALID && !external_events_TREADY)
                external_stall_cycles <= external_stall_cycles + 1;

            // Real AXIS stability contract: VALID and payload must remain
            // stable from a stalled cycle through the subsequent cycle,
            // including the cycle in which READY finally rises.
            if (stalled_trace_prior &&
                (!trace_TVALID || trace_TDATA !== prior_trace_word))
                $fatal(1, "RTL_STRESS_FAIL trace_TVALID/TDATA changed during stall");
            stalled_trace_prior <= (trace_TVALID && !trace_TREADY);
            prior_trace_word <= trace_TDATA;

            if (trace_TVALID && !trace_TREADY)
                trace_stall_cycles <= trace_stall_cycles + 1;

            if (trace_TVALID && trace_TREADY) begin : check_trace
                integer expected_tick;
                integer expected_id;
                reg expected_spike;
                reg [31:0] expected_count;
                if (trace_received >= 24)
                    $fatal(1, "RTL_STRESS_FAIL duplicate/extra output row");
                expected_tick = trace_received / 2;
                expected_id = trace_received % 2;
                expected_spike = ((expected_tick == 0 && expected_id == 0) ||
                                  (expected_tick == 8 && expected_id == 1));
                expected_count = (expected_tick == 0 || expected_tick == 8) ? 1 : 0;
                if (trace_TDATA[63:0] !== expected_tick ||
                    trace_TDATA[95:64] !== expected_id ||
                    trace_TDATA[127:96] !== 32'd0 ||
                    trace_TDATA[135:128] !== {7'd0, expected_spike} ||
                    trace_TDATA[143:136] !== {7'd0, expected_spike} ||
                    trace_TDATA[191:160] !== expected_count)
                    $fatal(1, "RTL_STRESS_FAIL trace mismatch row=%0d TDATA=%h",
                           trace_received, trace_TDATA);
                trace_received <= trace_received + 1;
            end
        end
    end

    // AXI-Lite tasks use independent AW and W handshakes, with fixed WSTRB,
    // and poll AP_CTRL read-to-clear ap_done after draining all expected rows.
    task automatic axi_write(input [6:0] addr, input [31:0] data);
        reg aw_done;
        reg w_done;
        begin
            aw_done = 0;
            w_done = 0;
            @(negedge ap_clk);
            s_axi_control_AWADDR = addr;
            s_axi_control_WDATA = data;
            s_axi_control_AWVALID = 1;
            s_axi_control_WVALID = 1;
            s_axi_control_BREADY = 1;
            while (!aw_done || !w_done) begin
                @(posedge ap_clk);
                if (s_axi_control_AWVALID && s_axi_control_AWREADY) aw_done = 1;
                if (s_axi_control_WVALID && s_axi_control_WREADY) w_done = 1;
                @(negedge ap_clk);
                if (aw_done) s_axi_control_AWVALID = 0;
                if (w_done) s_axi_control_WVALID = 0;
            end
            while (!s_axi_control_BVALID) @(negedge ap_clk);
            if (s_axi_control_BRESP !== 2'b00)
                $fatal(1, "RTL_STRESS_FAIL AXI-Lite write response");
            @(negedge ap_clk);
            s_axi_control_BREADY = 0;
        end
    endtask

    task automatic axi_read(input [6:0] addr, output [31:0] data);
        reg done_ar;
        begin
            done_ar = 0;
            @(negedge ap_clk);
            s_axi_control_ARADDR = addr;
            s_axi_control_ARVALID = 1;
            s_axi_control_RREADY = 1;
            while (!done_ar) begin
                @(posedge ap_clk);
                if (s_axi_control_ARVALID && s_axi_control_ARREADY)
                    done_ar = 1;
                @(negedge ap_clk);
            end
            s_axi_control_ARVALID = 0;
            while (!s_axi_control_RVALID) @(negedge ap_clk);
            data = s_axi_control_RDATA;
            if (s_axi_control_RRESP !== 2'b00)
                $fatal(1, "RTL_STRESS_FAIL AXI-Lite read response");
            @(negedge ap_clk);
            s_axi_control_RREADY = 0;
        end
    endtask

    initial begin : main
        integer poll;
        reg done_seen;
        reg [31:0] ctrl;
        reg [31:0] status;
        repeat (12) @(negedge ap_clk);
        ap_rst_n = 1;

        // Register offsets are parsed from Vitis-generated *_hw.h, not
        // assumed from memory or a hard-coded prior tool version.
        axi_write(`M05_ADDR_NEURON_COUNT_DATA, 2);
        axi_write(`M05_ADDR_SYNAPSE_COUNT_DATA, 1);
        axi_write(`M05_ADDR_EXTERNAL_COUNT_DATA, 1);
        axi_write(`M05_ADDR_TICKS_DATA, 12);
        axi_write(`M05_ADDR_DECAY_NUM_DATA, 1);
        axi_write(`M05_ADDR_DECAY_DEN_DATA, 1);
        enable_feeds = 1;
        axi_write(`M05_ADDR_AP_CTRL, 1);  // ap_start, one hardware run

        wait(trace_received == 24);
        done_seen = 0;
        for (poll = 0; poll < 200 && !done_seen; poll = poll + 1) begin
            axi_read(`M05_ADDR_AP_CTRL, ctrl);
            if (ctrl[1]) done_seen = 1;   // ap_done (clear on read)
        end
        if (!done_seen)
            $fatal(1, "RTL_STRESS_FAIL completed trace but ap_done not observed");
        axi_read(`M05_ADDR_AP_RETURN, status);
        if (status !== 32'd0)
            $fatal(1, "RTL_STRESS_FAIL nonzero final HLS return %h", status);
        if (neurons_sent != 2 || synapses_sent != 1 || external_sent != 1)
            $fatal(1, "RTL_STRESS_FAIL accepted input beat counts N=%0d S=%0d E=%0d",
                   neurons_sent, synapses_sent, external_sent);
        if (trace_stall_cycles < 10)
            $fatal(1, "RTL_STRESS_FAIL no meaningful AXIS output backpressure");
        if (ingress_gap_cycles < 10)
            $fatal(1, "RTL_STRESS_FAIL no deliberate input TVALID gaps");
        repeat (25) @(negedge ap_clk);
        if (trace_received != 24)
            $fatal(1, "RTL_STRESS_FAIL extra trace rows after completion");
        // SystemVerilog does not concatenate adjacent string literals
        // merely by writing them on consecutive source lines. Use one
        // continuous format string accepted by Vivado 2025.2 xvlog.
        $display("PASS: M05 REAL RTL AXIS stall stress N=2 E=1 S=1 T=12; trace=24; stalled_output_cycles=%0d; ingress_gap_cycles=%0d; input_stalls N/S/E=%0d/%0d/%0d; final_status=0",
                 trace_stall_cycles, ingress_gap_cycles,
                 neuron_stall_cycles, synapse_stall_cycles, external_stall_cycles);
        $finish;
    end
endmodule
