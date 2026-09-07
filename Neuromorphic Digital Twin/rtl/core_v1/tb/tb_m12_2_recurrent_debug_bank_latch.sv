`timescale 1ns/1ps

module tb_m12_2_recurrent_debug_bank_latch;
    logic ap_clk = 0;
    logic ap_rst = 1;
    always #5 ap_clk = ~ap_clk;

    logic core_reset_start = 0, start = 0;
    logic [8:0] neuron_count = 1;
    logic [12:0] route_count = 1;
    logic busy, core_reset_done, done, fault;
    logic [7:0] fault_code;
    logic current_bank;
    logic [12:0] current_count, last_consumed_count, last_routed_count;
    logic [7:0] active_source;
    logic [31:0] active_route_index;
    logic route_target_write_seen;
    logic [11:0] last_route_target_write_addr, last_route_target_read_addr;
    logic [15:0] last_route_target_write_data, last_route_target_read_data;
    logic recurrent_bank_write_seen, last_recurrent_bank_write_bank;
    logic [11:0] last_recurrent_bank_write_addr;
    logic [15:0] last_recurrent_bank_write_data;
    logic route_row_we = 0;
    logic [8:0] route_row_addr = 0;
    logic [31:0] route_row_wdata = 0;
    logic route_target_we = 0;
    logic [11:0] route_target_addr = 0;
    logic [15:0] route_target_wdata = 0;
    logic spike_we = 0;
    logic [7:0] spike_addr = 0;
    logic spike_wdata = 0;
    logic debug_re = 0, debug_bank = 0;
    logic [11:0] debug_addr = 0;
    logic debug_rvalid;
    logic [15:0] debug_rdata;
    logic [12:0] debug_bank0_count, debug_bank1_count;

    recurrent_route_queue_v1 #(
        .MAX_NEURONS(4), .MAX_AXONS(8), .MAX_ROUTES(8), .MAX_EVENTS(8)
    ) dut (.*);

    task automatic wr_row(input [8:0] a, input [31:0] d);
        @(negedge ap_clk); route_row_we=1; route_row_addr=a; route_row_wdata=d;
        @(negedge ap_clk); route_row_we=0;
    endtask

    task automatic wr_target(input [11:0] a, input [15:0] d);
        @(negedge ap_clk); route_target_we=1; route_target_addr=a; route_target_wdata=d;
        @(negedge ap_clk); route_target_we=0;
    endtask

    task automatic wr_spike(input [7:0] a, input logic d);
        @(negedge ap_clk); spike_we=1; spike_addr=a; spike_wdata=d;
        @(negedge ap_clk); spike_we=0;
    endtask

    initial begin
        repeat (4) @(posedge ap_clk);
        @(negedge ap_clk); ap_rst=0;

        wr_row(0, 0);
        wr_row(1, 1);
        wr_target(0, 16'd1);
        wr_spike(0, 1'b1);

        @(negedge ap_clk); core_reset_start=1;
        @(negedge ap_clk); core_reset_start=0;
        wait(core_reset_done);

        @(negedge ap_clk); start=1;
        @(negedge ap_clk); start=0;
        wait(done);
        #1;

        if (current_bank !== 1'b1 || current_count !== 13'd1)
            $fatal(1, "route did not commit to bank1/count1");
        if (!recurrent_bank_write_seen || last_recurrent_bank_write_bank !== 1'b1 ||
            last_recurrent_bank_write_addr !== 12'd0 || last_recurrent_bank_write_data !== 16'd1)
            $fatal(1, "bank write witness mismatch");

        // Request bank1, then immediately return the live selector to bank0.
        // The synchronous response must still come from the bank selected when
        // debug_re was accepted.
        @(negedge ap_clk); debug_bank=1; debug_addr=0; debug_re=1;
        @(negedge ap_clk); debug_re=0; debug_bank=0;
        if (!debug_rvalid)
            $fatal(1, "debug_rvalid was not asserted for synchronous response");
        if (debug_rdata !== 16'd1)
            $fatal(1, "latched-bank read mismatch expected=1 actual=%0d", debug_rdata);

        $display("M12.2 recurrent debug bank-latch regression passed: bank1 payload survives selector release");
        $finish;
    end
endmodule
