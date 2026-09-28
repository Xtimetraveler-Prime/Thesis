`timescale 1ns/1ps

module tb_phase_b_synapse_accumulator_v1;

    logic ap_clk = 1'b0;
    logic ap_rst = 1'b1;
    logic start = 1'b0;

    logic [8:0]  neuron_count = 9'd2;
    logic [10:0] axon_count = 11'd2;
    logic [12:0] synapse_count = 13'd3;
    logic [4:0]  format_count = 5'd3;
    logic [12:0] external_event_count = 13'd3;
    logic [12:0] recurrent_event_count = 13'd1;

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

    logic [15:0] dec_format_word = 16'd0;
    logic [31:0] dec_synapse_word = 32'd0;
    logic dec_valid;
    logic [7:0] dec_fault_code;
    logic [15:0] dec_target;
    logic [3:0] dec_format_index;
    logic signed [8:0] dec_mantissa;
    logic signed [31:0] dec_weight;

    phase_b_synapse_accumulator_v1 dut (
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

    m08_weight_decoder_v1 decoder_probe (
        .format_word(dec_format_word),
        .synapse_word(dec_synapse_word),
        .valid(dec_valid),
        .fault_code(dec_fault_code),
        .target_neuron(dec_target),
        .format_index(dec_format_index),
        .requested_mantissa(dec_mantissa),
        .effective_weight(dec_weight)
    );

    always #5 ap_clk = ~ap_clk;

    task automatic write_format(input int addr, input logic [15:0] word);
        begin
            @(negedge ap_clk);
            format_addr = addr[3:0];
            format_wdata = word;
            format_we = 1'b1;
            @(negedge ap_clk);
            format_we = 1'b0;
        end
    endtask

    task automatic write_synapse(input int addr, input logic [31:0] word);
        begin
            @(negedge ap_clk);
            synapse_addr = addr[11:0];
            synapse_wdata = word;
            synapse_we = 1'b1;
            @(negedge ap_clk);
            synapse_we = 1'b0;
        end
    endtask

    task automatic write_row(input int addr, input logic [31:0] word);
        begin
            @(negedge ap_clk);
            row_addr = addr[10:0];
            row_wdata = word;
            row_we = 1'b1;
            @(negedge ap_clk);
            row_we = 1'b0;
        end
    endtask

    task automatic write_external(input int addr, input logic [15:0] axon);
        begin
            @(negedge ap_clk);
            external_addr = addr[11:0];
            external_wdata = axon;
            external_we = 1'b1;
            @(negedge ap_clk);
            external_we = 1'b0;
        end
    endtask

    task automatic write_recurrent(input int addr, input logic [15:0] axon);
        begin
            @(negedge ap_clk);
            recurrent_addr = addr[11:0];
            recurrent_wdata = axon;
            recurrent_we = 1'b1;
            @(negedge ap_clk);
            recurrent_we = 1'b0;
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
        int cycles;
        begin
            for (cycles = 0; cycles < 2000; cycles = cycles + 1) begin
                @(posedge ap_clk);
                #1;
                if (done)
                    return;
                if (fault)
                    $fatal(1, "Phase-B fault: code=0x%02x source=%0d event=%0d synapse=%0d",
                        fault_code, active_source, active_event_index, active_synapse_index);
            end
            $fatal(1, "timeout waiting for Phase-B done: busy=%0d source=%0d event=%0d synapse=%0d fault=0x%02x",
                busy, active_source, active_event_index, active_synapse_index, fault_code);
        end
    endtask

    task automatic read_accum(input int addr, output logic signed [63:0] value);
        begin
            @(negedge ap_clk);
            debug_accum_addr = addr[7:0];
            debug_accum_re = 1'b1;
            @(posedge ap_clk);
            #1;
            if (!debug_accum_rvalid)
                $fatal(1, "accumulator debug read invalid at neuron %0d", addr);
            value = debug_accum_rdata;
            @(negedge ap_clk);
            debug_accum_re = 1'b0;
        end
    endtask

    task automatic check_decoder(
        input logic [15:0] format_word,
        input logic [31:0] synapse_word,
        input integer signed expected_weight
    );
        begin
            dec_format_word = format_word;
            dec_synapse_word = synapse_word;
            #1;
            if (!dec_valid)
                $fatal(1, "decoder rejected directed vector: fault=0x%02x", dec_fault_code);
            if (dec_weight !== expected_weight)
                $fatal(1, "decoder mismatch: expected=%0d actual=%0d", expected_weight, dec_weight);
        end
    endtask

    initial begin : test_sequence
        logic signed [63:0] accum0;
        logic signed [63:0] accum1;
        int cycles;

        // Directed decoder boundaries:
        // inhibitory -256, exponent +7 clips at -2,097,088.
        check_decoder(16'h0287, 32'h00000100, -2097088);
        // mixed -5 quantizes to -4; exponent -1 floors to -2; align -> -128.
        check_decoder(16'h008f, 32'h000001fb, -128);
        // excitatory 7 with four weight bits quantizes toward zero to 0.
        check_decoder(16'h0140, 32'h00000007, 0);

        repeat (5) @(posedge ap_clk);
        @(negedge ap_clk);
        ap_rst = 1'b0;

        // M08 packed formats: excitatory, inhibitory, mixed; exponent 0, 8 bits.
        write_format(0, 16'h0180);
        write_format(1, 16'h0280);
        write_format(2, 16'h0080);

        // Axon 0: target0 +2 => +128, target1 -3 => -192.
        // Axon 1: target0 mixed +5 => quantized +4 => +256.
        write_synapse(0, 32'h00000002);
        write_synapse(1, 32'h000023fd);
        write_synapse(2, 32'h00000405);
        write_row(0, 32'd0);
        write_row(1, 32'd2);
        write_row(2, 32'd3);

        // External events first: 0,1,0. Recurrent event: 1.
        write_external(0, 16'd0);
        write_external(1, 16'd1);
        write_external(2, 16'd0);
        write_recurrent(0, 16'd1);

        pulse_start();
        wait_done();
        if (fault)
            $fatal(1, "fault remained after successful Phase-B run: 0x%02x", fault_code);

        read_accum(0, accum0);
        read_accum(1, accum1);
        if (accum0 !== 64'sd768)
            $fatal(1, "neuron0 accumulator mismatch: expected=768 actual=%0d", accum0);
        if (accum1 !== -64'sd384)
            $fatal(1, "neuron1 accumulator mismatch: expected=-384 actual=%0d", accum1);

        // A physically valid but unconfigured axon must be a no-op and the
        // start of a new Phase-B transaction must clear old accumulator values.
        write_external(0, 16'd7);
        external_event_count = 13'd1;
        recurrent_event_count = 13'd0;
        pulse_start();
        wait_done();
        read_accum(0, accum0);
        read_accum(1, accum1);
        if (accum0 !== 64'sd0 || accum1 !== 64'sd0)
            $fatal(1, "unconfigured axon was not a no-op: accum0=%0d accum1=%0d", accum0, accum1);

        // Physical axon overflow must fault rather than truncate.
        write_external(0, 16'd1024);
        pulse_start();
        for (cycles = 0; cycles < 100; cycles = cycles + 1) begin
            @(posedge ap_clk);
            #1;
            if (fault) begin
                if (fault_code !== 8'h02)
                    $fatal(1, "wrong event-axon fault code: 0x%02x", fault_code);
                $display("M11.5.3 Phase-B RTL tests passed: decoder boundaries + CSR traversal + multiplicity + capacity fault");
                $finish;
            end
        end
        $fatal(1, "expected event-axon capacity fault did not occur");
    end

endmodule
