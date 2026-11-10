// M06 stand-alone one-block RTL residency admission/dirty WB/fill test.
// No neuron engine, no real DMA adapter, no SmartConnect, no DDR/BOARD.
`timescale 1ns/1ps
module tb_m06_residency_control_fsm;
    reg clk = 0;
    always #5 clk=~clk;
    reg resetn=0;
    reg req_valid=0, req_is_write=0;
    reg [31:0] req_block=0;
    reg rsp_ready=0;
    reg dma_done=0, dma_error=0;
    wire req_ready, rsp_valid, rsp_error, dma_valid, dma_is_writeback;
    wire [31:0] rsp_block, dma_block;
    wire poisoned, resident_valid, resident_dirty;
    wire [31:0] resident_block;
    wire [31:0] accesses,hits,misses,acknowledged_writebacks,
                acknowledged_fills,stalled_cycles;
    reg fault_fill_page3=0, fault_wb_page4=0;
    reg next_error=0;
    integer cycles=0, wait_count=0, transfer_wb=0,transfer_fill=0;
    wire dma_ready = resetn && (cycles % 3 != 1);
    m06_residency_control_fsm #(.MAX_WAIT_CYCLES(32'd64)) dut(
        .aclk(clk),.aresetn(resetn),
        .req_valid(req_valid),.req_ready(req_ready),
        .req_block(req_block),.req_is_write(req_is_write),
        .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),
        .rsp_error(rsp_error),.rsp_block(rsp_block),
        .dma_valid(dma_valid),.dma_ready(dma_ready),
        .dma_is_writeback(dma_is_writeback),.dma_block(dma_block),
        .dma_done(dma_done),.dma_error(dma_error),
        .poisoned(poisoned),
        .resident_valid(resident_valid),.resident_block(resident_block),
        .resident_dirty(resident_dirty),
        .accesses(accesses),.hits(hits),.misses(misses),
        .acknowledged_writebacks(acknowledged_writebacks),
        .acknowledged_fills(acknowledged_fills),
        .stalled_cycles(stalled_cycles)
    );
    always @(posedge clk) begin
        if (!resetn) begin
            cycles <= 0;
            wait_count <= 0;
            dma_done <= 0;
            dma_error <= 0;
            transfer_wb <= 0;
            transfer_fill <= 0;
            next_error <= 0;
        end else begin
            cycles <= cycles+1;
            dma_done <= 0;
            dma_error <= 0;
            if (wait_count > 0) begin
                wait_count <= wait_count-1;
                if (wait_count == 1) begin
                    dma_done <= 1;
                    dma_error <= next_error;
                end
            end
            if (dma_valid && dma_ready) begin
                if (wait_count != 0)
                    $fatal(1,"new abstract DMA command before previous ACK");
                wait_count <= 3;
                if (dma_is_writeback) begin
                    transfer_wb <= transfer_wb+1;
                    next_error <= fault_wb_page4 && dma_block == 32'd4;
                end else begin
                    transfer_fill <= transfer_fill+1;
                    next_error <= fault_fill_page3 && dma_block == 32'd3;
                end
            end
        end
    end

    task automatic transact;
        input [31:0] block_no;
        input write_op;
        input expect_error;
        integer i;
        begin
            @(negedge clk);
            if (poisoned || !req_ready)
                $fatal(1,"request not idle: poisoned or previous response pending");
            req_block=block_no;
            req_is_write=write_op;
            req_valid=1;
            @(posedge clk);
            if (!req_ready)
                $fatal(1,"request dropped READY on idle handshake");
            @(negedge clk);
            req_valid=0;
            for (i=0; i<100 && !rsp_valid; i=i+1)
                @(negedge clk);
            if (!rsp_valid)
                $fatal(1,"missing residency response");
            if (rsp_block !== block_no || rsp_error !== expect_error)
                $fatal(1,"bad residency response block=%d error=%d",rsp_block,rsp_error);
            if (!expect_error) begin
                repeat (2) @(negedge clk);
                if (!rsp_valid || rsp_error || rsp_block !== block_no)
                    $fatal(1,"residency response unstable while RSP_READY low");
                rsp_ready=1;
                @(posedge clk);
                if (!rsp_valid)
                    $fatal(1,"residency ACK lost");
                @(negedge clk);
                rsp_ready=0;
            end
        end
    endtask

    initial begin
        repeat(4) @(negedge clk);
        resetn=1;
        transact(32'd1,0,0);  // miss, fill page1
        if (!resident_valid || resident_block != 1 || resident_dirty)
            $fatal(1,"first demand fill did not set clean resident tag");
        transact(32'd1,0,0);  // read hit
        transact(32'd1,1,0);  // write hit marks dirty
        if (!resident_dirty)
            $fatal(1,"write hit not marked dirty");
        transact(32'd2,0,0);  // dirty page1 writeback ACK then page2 fill
        if (resident_block != 2 || resident_dirty)
            $fatal(1,"dirty writeback / new clean fill state wrong");
        if (transfer_wb != 1 || transfer_fill != 2)
            $fatal(1,"missing real handshake sequence for writeback+fill");
        fault_fill_page3=1;
        transact(32'd3,0,1);  // fault after DMA fill accepted
        if (!poisoned || req_ready || dma_valid)
            $fatal(1,"error must quarantine new admission and DMA");
        if (!resident_valid || resident_block != 2 || resident_dirty)
            $fatal(1,"faulting fill must preserve old resident tag");
        if (accesses != 5 || hits != 2 || misses != 3 ||
            acknowledged_writebacks != 1 || acknowledged_fills != 2 ||
            stalled_cycles == 0)
            $fatal(1,"wrong counters a=%d h=%d m=%d w=%d f=%d stalls=%d",
                   accesses,hits,misses,acknowledged_writebacks,
                   acknowledged_fills,stalled_cycles);
        $display("M06_RESIDENCY_FSM_RTL_PASS first run accesses=%0d hits=%0d misses=%0d WB=%0d fills=%0d stalls=%0d",
                 accesses,hits,misses,acknowledged_writebacks,
                 acknowledged_fills,stalled_cycles);
        // Sticky quarantine reset may lose uncommitted page content:
        // real DDR recovery must authenticate canonical state separately.
        @(negedge clk);
        resetn=0;
        repeat(3) @(negedge clk);
        resetn=1;
        fault_fill_page3=0;
        fault_wb_page4=0;
        transact(32'd4,1,0);
        if (resident_block != 4 || !resident_dirty)
            $fatal(1,"new dirty resident tag missing");
        fault_wb_page4=1;
        transact(32'd5,0,1);
        if (!poisoned || !resident_dirty || resident_block != 4 ||
            acknowledged_writebacks != 0 || acknowledged_fills != 1)
            $fatal(1,"failed WB ACK must retain original dirty tag and reject fill");
        $display("M06_RESIDENCY_FSM_DIRTY_WB_QUARANTINE_PASS no fabricated DDR commit");
        $finish;
    end
    initial begin
        #100000;
        $fatal(1,"M06 residency FSM RTL watchdog timeout");
    end
endmodule
