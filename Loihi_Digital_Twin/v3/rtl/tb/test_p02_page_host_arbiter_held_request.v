`timescale 1ns/1ps

module test_p02_page_host_arbiter_held_request;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg page_active = 1'b0;

    reg debug_req = 1'b0;
    reg debug_write = 1'b0;
    reg [1:0] debug_context_slot = 2'd1;
    reg [3:0] debug_bank = 4'd5;
    reg [14:0] debug_addr = 15'd7;
    reg [255:0] debug_wdata = 256'd0;

    wire debug_busy;
    wire debug_ack;
    wire debug_rvalid;
    wire debug_error;
    wire [255:0] debug_rdata;

    reg page_req = 1'b0;
    reg page_write = 1'b0;
    reg [1:0] page_context_slot = 2'd0;
    reg [3:0] page_bank = 4'd0;
    reg [14:0] page_addr = 15'd0;
    reg [255:0] page_wdata = 256'd0;

    wire page_busy;
    wire page_ack;
    wire page_rvalid;
    wire page_error;
    wire [255:0] page_rdata;

    wire fabric_req;
    wire fabric_write;
    wire [1:0] fabric_context_slot;
    wire [3:0] fabric_bank;
    wire [14:0] fabric_addr;
    wire [255:0] fabric_wdata;

    reg fabric_busy = 1'b0;
    reg fabric_ack = 1'b0;
    reg fabric_rvalid = 1'b0;
    reg fabric_error = 1'b0;
    reg [255:0] fabric_rdata = 256'd0;

    integer failures = 0;
    integer forwarded_req_high_cycles_after_completion = 0;
    reg response_completed = 1'b0;

    p02_page_host_arbiter dut (
        .clk(clk),
        .resetn(resetn),
        .page_active(page_active),
        .debug_req(debug_req),
        .debug_write(debug_write),
        .debug_context_slot(debug_context_slot),
        .debug_bank(debug_bank),
        .debug_addr(debug_addr),
        .debug_wdata(debug_wdata),
        .debug_busy(debug_busy),
        .debug_ack(debug_ack),
        .debug_rvalid(debug_rvalid),
        .debug_error(debug_error),
        .debug_rdata(debug_rdata),
        .page_req(page_req),
        .page_write(page_write),
        .page_context_slot(page_context_slot),
        .page_bank(page_bank),
        .page_addr(page_addr),
        .page_wdata(page_wdata),
        .page_busy(page_busy),
        .page_ack(page_ack),
        .page_rvalid(page_rvalid),
        .page_error(page_error),
        .page_rdata(page_rdata),
        .fabric_req(fabric_req),
        .fabric_write(fabric_write),
        .fabric_context_slot(fabric_context_slot),
        .fabric_bank(fabric_bank),
        .fabric_addr(fabric_addr),
        .fabric_wdata(fabric_wdata),
        .fabric_busy(fabric_busy),
        .fabric_ack(fabric_ack),
        .fabric_rvalid(fabric_rvalid),
        .fabric_error(fabric_error),
        .fabric_rdata(fabric_rdata)
    );

    task check;
        input condition;
        input [8*160-1:0] message;
        begin
            if (!condition) begin
                $display("FAIL: %0s", message);
                failures = failures + 1;
            end
        end
    endtask

    always @(posedge clk) begin
        if (response_completed && debug_req && fabric_req)
            forwarded_req_high_cycles_after_completion =
                forwarded_req_high_cycles_after_completion + 1;
    end

    initial begin
        repeat (4) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        // Begin one debug transaction.
        @(negedge clk);
        debug_req = 1'b1;

        // Allow the arbiter to capture debug ownership.
        repeat (2) @(posedge clk);
        check(fabric_req, "initial debug request was not forwarded");

        // Complete it, but intentionally hold ACK/RVALID/RDATA high for several
        // clocks while debug_req also remains asserted. This models the
        // accepted P05 host interface plus slow VIO/Tcl request deassertion.
        @(negedge clk);
        fabric_ack = 1'b1;
        fabric_rvalid = 1'b1;
        fabric_rdata = 256'hDEAD_BEEF;

        @(posedge clk);
        #1;
        response_completed = 1'b1;
        check(debug_ack, "completed debug response was not latched");
        check(debug_rvalid, "completed debug read did not latch RVALID");
        check(debug_rdata == 256'hDEAD_BEEF,
              "completed debug read did not latch response data");

        repeat (5) begin
            @(posedge clk);
            #1;
            check(debug_ack,
                  "latched debug ACK did not remain visible while req stayed high");
            check(debug_rvalid,
                  "latched debug RVALID did not remain visible while req stayed high");
            check(debug_rdata == 256'hDEAD_BEEF,
                  "latched debug data changed while req stayed high");
            check(!fabric_req,
                  "held-high completed debug request was forwarded again");
        end

        check(
            forwarded_req_high_cycles_after_completion == 0,
            "held-high completed request was re-forwarded before going low"
        );
        check(
            debug_busy,
            "debug side should remain busy while requester still holds req high"
        );

        // Requester finally acknowledges completion by dropping req. The
        // latched response must retire and the fabric may accept a later edge.
        @(negedge clk);
        debug_req = 1'b0;
        @(posedge clk);
        #1;
        response_completed = 1'b0;
        check(!debug_ack, "latched debug ACK did not clear after req went low");
        check(!debug_rvalid, "latched debug RVALID did not clear after req went low");

        // Retire the old downstream response before issuing a new request.
        @(negedge clk);
        fabric_ack = 1'b0;
        fabric_rvalid = 1'b0;
        fabric_rdata = 256'd0;
        repeat (2) @(posedge clk);

        check(!debug_busy, "debug side did not release after request returned low");

        // A genuinely new request must be accepted normally.
        @(negedge clk);
        debug_addr = 15'd8;
        debug_req = 1'b1;
        @(posedge clk);
        #1;
        check(fabric_req, "new debug request was not accepted after response retirement");

        @(negedge clk);
        fabric_ack = 1'b1;
        fabric_rvalid = 1'b1;
        fabric_rdata = 256'h1234;
        @(posedge clk);
        #1;
        check(debug_ack, "new transaction did not latch ACK");
        check(debug_rvalid, "new transaction did not latch RVALID");
        check(debug_rdata == 256'h1234, "new transaction returned wrong data");

        repeat (3) begin
            @(posedge clk);
            #1;
            check(debug_ack, "new latched ACK was not held for slow requester");
            check(debug_rdata == 256'h1234,
                  "new latched response data changed before req release");
            check(!fabric_req,
                  "new completed request was re-forwarded while req stayed high");
        end

        @(negedge clk);
        debug_req = 1'b0;
        @(posedge clk);
        #1;
        check(!debug_ack, "new latched ACK did not retire after req release");
        fabric_ack = 1'b0;
        fabric_rvalid = 1'b0;

        repeat (2) @(posedge clk);

        if (failures == 0)
            $display("PASS: p02_page_host_arbiter_held_request");
        else
            $display(
                "FAIL: p02_page_host_arbiter_held_request failures=%0d",
                failures
            );
        $finish;
    end
endmodule
