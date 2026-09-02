`timescale 1ns/1ps

module tb_m12_trace_read_bridge_v1;
    logic clk = 1'b0;
    logic rst = 1'b1;
    always #5 clk = ~clk;

    logic        core_busy;
    logic        req_valid;
    logic [2:0]  req_space;
    logic [11:0] req_addr;
    logic        req_ready;
    logic        rsp_valid;
    logic [2:0]  rsp_space;
    logic [11:0] rsp_addr;
    logic [63:0] rsp_data;
    logic        rsp_error;

    logic        debug_re;
    logic [7:0]  debug_addr;
    logic        debug_rvalid;
    logic [63:0] debug_state_before_rdata;
    logic [63:0] debug_state_rdata;
    logic signed [63:0] debug_synaptic_input_rdata;
    logic        debug_spike_rdata;

    logic        external_debug_re;
    logic [11:0] external_debug_addr;
    logic        external_debug_rvalid;
    logic [15:0] external_debug_rdata;

    logic        recurrent_debug_re;
    logic        recurrent_debug_bank;
    logic [11:0] recurrent_debug_addr;
    logic        recurrent_debug_rvalid;
    logic [15:0] recurrent_debug_rdata;

    logic mock_stall;
    integer debug_reads;
    integer external_reads;
    integer recurrent_reads;

    m12_trace_read_bridge_v1 dut (
        .ap_clk(clk),
        .ap_rst(rst),
        .core_busy(core_busy),
        .req_valid(req_valid),
        .req_space(req_space),
        .req_addr(req_addr),
        .req_ready(req_ready),
        .rsp_valid(rsp_valid),
        .rsp_space(rsp_space),
        .rsp_addr(rsp_addr),
        .rsp_data(rsp_data),
        .rsp_error(rsp_error),
        .debug_re(debug_re),
        .debug_addr(debug_addr),
        .debug_rvalid(debug_rvalid),
        .debug_state_before_rdata(debug_state_before_rdata),
        .debug_state_rdata(debug_state_rdata),
        .debug_synaptic_input_rdata(debug_synaptic_input_rdata),
        .debug_spike_rdata(debug_spike_rdata),
        .external_debug_re(external_debug_re),
        .external_debug_addr(external_debug_addr),
        .external_debug_rvalid(external_debug_rvalid),
        .external_debug_rdata(external_debug_rdata),
        .recurrent_debug_re(recurrent_debug_re),
        .recurrent_debug_bank(recurrent_debug_bank),
        .recurrent_debug_addr(recurrent_debug_addr),
        .recurrent_debug_rvalid(recurrent_debug_rvalid),
        .recurrent_debug_rdata(recurrent_debug_rdata)
    );

    // Simple one-cycle-latency models of the three existing debug interfaces.
    always_ff @(posedge clk) begin
        if (rst) begin
            debug_rvalid <= 1'b0;
            external_debug_rvalid <= 1'b0;
            recurrent_debug_rvalid <= 1'b0;
            debug_state_before_rdata <= 64'b0;
            debug_state_rdata <= 64'b0;
            debug_synaptic_input_rdata <= 64'sb0;
            debug_spike_rdata <= 1'b0;
            external_debug_rdata <= 16'b0;
            recurrent_debug_rdata <= 16'b0;
            debug_reads <= 0;
            external_reads <= 0;
            recurrent_reads <= 0;
        end else begin
            debug_rvalid <= debug_re && !mock_stall;
            external_debug_rvalid <= external_debug_re && !mock_stall;
            recurrent_debug_rvalid <= recurrent_debug_re && !mock_stall;

            if (debug_re) begin
                debug_reads <= debug_reads + 1;
                debug_state_before_rdata <= 64'hB000_0000_0000_0000 | debug_addr;
                debug_state_rdata <= 64'hA000_0000_0000_0000 | debug_addr;
                debug_synaptic_input_rdata <= $signed(64'h2000_0000_0000_0000 | debug_addr);
                debug_spike_rdata <= debug_addr[0];
            end
            if (external_debug_re) begin
                external_reads <= external_reads + 1;
                external_debug_rdata <= 16'hE000 | external_debug_addr;
            end
            if (recurrent_debug_re) begin
                recurrent_reads <= recurrent_reads + 1;
                if (recurrent_debug_bank)
                    recurrent_debug_rdata <= 16'hD000 | recurrent_debug_addr;
                else
                    recurrent_debug_rdata <= 16'hC000 | recurrent_debug_addr;
            end
        end
    end

    task automatic issue_and_check(
        input logic [2:0] space,
        input logic [11:0] addr,
        input logic [63:0] expected_data,
        input logic expected_error
    );
        integer timeout;
        begin
            @(negedge clk);
            timeout = 0;
            while (!req_ready && timeout < 20) begin
                @(negedge clk);
                timeout = timeout + 1;
            end
            if (!req_ready)
                $fatal(1, "request interface never became ready");

            req_space = space;
            req_addr = addr;
            req_valid = 1'b1;
            @(negedge clk);
            req_valid = 1'b0;

            timeout = 0;
            while (!rsp_valid && timeout < 20) begin
                @(posedge clk);
                #1;
                timeout = timeout + 1;
            end
            if (!rsp_valid)
                $fatal(1, "response timeout for space=%0d addr=%0d", space, addr);
            if (rsp_space !== space || rsp_addr !== addr)
                $fatal(1, "response tag mismatch got space=%0d addr=%0d", rsp_space, rsp_addr);
            if (rsp_error !== expected_error)
                $fatal(1, "response error mismatch for space=%0d addr=%0d", space, addr);
            if (rsp_data !== expected_data)
                $fatal(1, "response data mismatch space=%0d addr=%0d got=%h expected=%h",
                       space, addr, rsp_data, expected_data);
            @(negedge clk);
        end
    endtask

    initial begin
        core_busy = 1'b0;
        req_valid = 1'b0;
        req_space = 3'b0;
        req_addr = 12'b0;
        mock_stall = 1'b0;

        repeat (4) @(posedge clk);
        rst = 1'b0;
        repeat (2) @(posedge clk);

        if (!req_ready)
            $fatal(1, "bridge must be ready when idle after reset");

        issue_and_check(3'd0, 12'h012, 64'hB000_0000_0000_0012, 1'b0);
        issue_and_check(3'd1, 12'h034, 64'hA000_0000_0000_0034, 1'b0);
        issue_and_check(3'd2, 12'h056, 64'h2000_0000_0000_0056, 1'b0);
        issue_and_check(3'd3, 12'h011, 64'h0000_0000_0000_0001, 1'b0);
        issue_and_check(3'd4, 12'h234, 64'h0000_0000_0000_E234, 1'b0);
        issue_and_check(3'd5, 12'h345, 64'h0000_0000_0000_C345, 1'b0);
        issue_and_check(3'd6, 12'h456, 64'h0000_0000_0000_D456, 1'b0);

        if (debug_reads != 4 || external_reads != 1 || recurrent_reads != 2)
            $fatal(1, "unexpected backing read counts debug=%0d ext=%0d rec=%0d",
                   debug_reads, external_reads, recurrent_reads);

        // Space 7 is undefined. It must generate a tagged local error without
        // touching any backing interface.
        issue_and_check(3'd7, 12'h001, 64'b0, 1'b1);
        if (debug_reads != 4 || external_reads != 1 || recurrent_reads != 2)
            $fatal(1, "invalid selector touched a backing debug interface");

        // Per-neuron spaces have only eight physical address bits. Reject an
        // out-of-range address rather than silently aliasing 0x100 to neuron 0.
        issue_and_check(3'd0, 12'h100, 64'b0, 1'b1);
        if (debug_reads != 4)
            $fatal(1, "aliased neuron address touched the neuron debug interface");

        // Back-pressure while the architectural core is executing.
        @(negedge clk);
        core_busy = 1'b1;
        req_valid = 1'b1;
        req_space = 3'd4;
        req_addr = 12'h010;
        repeat (3) begin
            @(posedge clk);
            #1;
            if (req_ready)
                $fatal(1, "req_ready asserted while core_busy");
            if (external_debug_re)
                $fatal(1, "external read launched while core_busy");
        end
        @(negedge clk);
        req_valid = 1'b0;
        core_busy = 1'b0;
        repeat (2) @(posedge clk);
        if (external_reads != 1)
            $fatal(1, "busy-blocked request reached backing interface");

        // If execution begins after a request was accepted but before its
        // backing response arrives, return an error instead of mixed-tick data.
        mock_stall = 1'b1;
        @(negedge clk);
        if (!req_ready)
            $fatal(1, "bridge not ready for pending-read abort test");
        req_valid = 1'b1;
        req_space = 3'd1;
        req_addr = 12'h022;
        @(negedge clk);
        req_valid = 1'b0;
        core_busy = 1'b1;

        repeat (5) begin
            @(posedge clk);
            #1;
            if (rsp_valid) begin
                if (!rsp_error || rsp_space != 3'd1 || rsp_addr != 12'h022 || rsp_data != 64'b0)
                    $fatal(1, "pending-read abort returned malformed error response");
                core_busy = 1'b0;
                mock_stall = 1'b0;
                @(negedge clk);
                $display("M12.1.2 trace-read bridge RTL tests passed: 7 read spaces + guards");
                $finish;
            end
        end
        $fatal(1, "pending-read abort did not produce an error response");
    end

endmodule
