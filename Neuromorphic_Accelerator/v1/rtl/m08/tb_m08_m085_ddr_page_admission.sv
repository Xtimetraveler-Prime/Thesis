`timescale 1ns/1ps
// Real Icarus RTL protocol stimulus. Synthetic 0x1000 window, no AXI, no PS,
// no allocated DDR, no board/driver. Every negative must poison and embargo.
module tb_m08_m085_ddr_page_admission;
    reg clk=0;
    always #5 clk=~clk;
    reg resetn=0, owner_lease_active=1, compute_idle=1, page_bank_idle=1;
    reg req=0, req_write=0, downstream_done=0, downstream_error=0;
    reg downstream_rvalid=0;
    reg [63:0] req_addr=64'h1000;
    reg [15:0] req_size_bytes=16'd256;
    reg [31:0] req_logical_page=3, req_tick=2;
    wire forward_req, forward_write, ack, error, busy, poisoned, completed_write;
    wire [63:0] forward_addr;
    wire [15:0] forward_size_bytes;
    wire [31:0] forward_logical_page,forward_tick,completed_page,completed_tick;
    wire [31:0] completed_page_transfers;

    m08_m085_ddr_page_admission #(
        .WINDOW_BEGIN(64'h1000), .WINDOW_END(64'h1F80),
        .MAX_WAIT_CYCLES(5)
    ) dut(
        .clk(clk),.resetn(resetn),.owner_lease_active(owner_lease_active),
        .compute_idle(compute_idle),.page_bank_idle(page_bank_idle),
        .req(req),.req_write(req_write),.req_addr(req_addr),
        .req_size_bytes(req_size_bytes),.req_logical_page(req_logical_page),
        .req_tick(req_tick),.forward_req(forward_req),
        .forward_write(forward_write),.forward_addr(forward_addr),
        .forward_size_bytes(forward_size_bytes),
        .forward_logical_page(forward_logical_page),.forward_tick(forward_tick),
        .downstream_done(downstream_done),.downstream_error(downstream_error),
        .downstream_rvalid(downstream_rvalid),.ack(ack),.error(error),
        .busy(busy),.poisoned(poisoned),.completed_page(completed_page),
        .completed_tick(completed_tick),.completed_write(completed_write),
        .completed_page_transfers(completed_page_transfers)
    );

    reg default_req=0;
    wire default_forward,default_poison;
    m08_m085_ddr_page_admission default_deny(
        .clk(clk),.resetn(resetn),.owner_lease_active(1'b1),
        .compute_idle(1'b1),.page_bank_idle(1'b1),
        .req(default_req),.req_write(1'b0),.req_addr(64'h1000),
        .req_size_bytes(16'd256),.req_logical_page(32'd0),.req_tick(32'd0),
        .forward_req(default_forward),.forward_write(),
        .forward_addr(),.forward_size_bytes(),.forward_logical_page(),
        .forward_tick(),.downstream_done(1'b0),.downstream_error(1'b0),
        .downstream_rvalid(1'b0),.ack(),.error(),.busy(),
        .poisoned(default_poison),.completed_page(),.completed_tick(),
        .completed_write(),.completed_page_transfers()
    );

    integer case_id=0;
    task start_transfer;
        begin
            @(negedge clk);
            req=1;
            @(posedge clk); #1;
        end
    endtask
    task release_req;
        begin
            @(negedge clk); req=0;
            @(posedge clk); #1;
        end
    endtask
    task complete_transfer;
        input read_response;
        begin
            @(negedge clk);
            downstream_done=1; downstream_rvalid=read_response;
            @(posedge clk); #1;
        end
    endtask
    task clear_response;
        begin
            @(negedge clk);
            downstream_done=0; downstream_rvalid=0; downstream_error=0;
            @(posedge clk); #1;
        end
    endtask
    task expect_poison;
        begin
            if (!poisoned || !error || ack || forward_req || busy)
                $fatal(1,"M08.5 negative failed: no fail-closed poison case=%0d",case_id);
            @(negedge clk);
            req=0; downstream_done=0; downstream_rvalid=0;
            downstream_error=0; owner_lease_active=1; compute_idle=1;
            page_bank_idle=1;
            @(posedge clk); #1;
            if (!poisoned || ack || forward_req || completed_page_transfers!=0)
                $fatal(1,"M08.5 fault cleared without reset case=%0d",case_id);
            $display("M08_5_REAL_IVERILOG_GUARD_NEGATIVE_PASS case=%0d",case_id);
        end
    endtask

    initial begin
        if (!$value$plusargs("CASE=%d",case_id)) case_id=0;
        repeat (3) @(negedge clk);
        resetn=1;
        @(posedge clk); #1;

        case(case_id)
            0: begin
                start_transfer();
                if (!forward_req || !busy || forward_write ||
                    forward_addr!=64'h1000 || forward_size_bytes!=256 ||
                    forward_logical_page!=3 || forward_tick!=2)
                    $fatal(1,"valid read did not forward precise page and epoch");
                // Keep original req high throughout ack: must never rearm.
                complete_transfer(1'b1);
                if (!ack || busy || poisoned || completed_page_transfers!=1 ||
                    completed_page!=3 || completed_tick!=2 || completed_write)
                    $fatal(1,"read completed early/wrongly");
                clear_response();
                repeat (2) begin
                    @(posedge clk); #1;
                    if (ack || forward_req || completed_page_transfers!=1)
                        $fatal(1,"held request duplicated read");
                end
                release_req();
                @(negedge clk);req_write=1;req_addr=64'h1100;
                req_logical_page=4;req_tick=3;
                start_transfer();
                if (!forward_req || !forward_write || !busy ||
                     forward_logical_page!=4 || forward_tick!=3)
                    $fatal(1,"valid dirty save did not forward exact metadata");
                release_req();
                complete_transfer(1'b0);
                if (!ack || busy || poisoned || !completed_write ||
                    completed_page!=4 || completed_tick!=3 ||
                    completed_page_transfers!=2)
                    $fatal(1,"save did not require completed write response");
                clear_response();
                $display("M08_5_REAL_IVERILOG_256B_GUARD_TWO_TRANSFERS_PASS");
            end
            1: begin owner_lease_active=0;start_transfer();expect_poison();end
            2: begin req_addr=64'h1080;start_transfer();expect_poison();end
            3: begin req_size_bytes=128;start_transfer();expect_poison();end
            4: begin req_addr=64'h2000;start_transfer();expect_poison();end
            5: begin req_addr=64'h0002_0000_0000_1000;start_transfer();expect_poison();end
            6: begin compute_idle=0;start_transfer();expect_poison();end
            7: begin page_bank_idle=0;start_transfer();expect_poison();end
            8: begin
                start_transfer();release_req();
                @(negedge clk);downstream_error=1;
                @(posedge clk);#1;expect_poison();
            end
            9: begin start_transfer();release_req();complete_transfer(1'b0);expect_poison();end
            10: begin
                req_write=1;start_transfer();release_req();
                complete_transfer(1'b1);expect_poison();
            end
            11: begin
                start_transfer();release_req();
                @(negedge clk);owner_lease_active=0;
                @(posedge clk);#1;expect_poison();
            end
            12: begin
                start_transfer();release_req();
                repeat(8) @(posedge clk);
                #1;
                // error is a pulse; poison remains sticky.
                if (!poisoned || completed_page_transfers!=0 || ack)
                    $fatal(1,"timeout did not quarantine");
                @(negedge clk);
                req=0;
                @(posedge clk); #1;
                if (!poisoned) $fatal(1,"timeout poison not sticky");
                $display("M08_5_REAL_IVERILOG_GUARD_NEGATIVE_PASS case=12");
            end
            13: begin
                start_transfer();release_req();
                start_transfer();expect_poison();
            end
            14: begin
                @(negedge clk);downstream_done=1;downstream_rvalid=1;
                @(posedge clk);#1;expect_poison();
            end
            15: begin req_addr=64'h1F00;start_transfer();expect_poison();end
            16: begin
                @(negedge clk);default_req=1;
                @(posedge clk);#1;
                if (default_forward || !default_poison)
                    $fatal(1,"default zero window admitted request");
                $display("M08_5_REAL_IVERILOG_GUARD_NEGATIVE_PASS case=16");
            end
            default: $fatal(1,"bad test selector");
        endcase
        $finish;
    end
    initial begin #10000; $fatal(1,"M08.5 guard test hung"); end
endmodule
