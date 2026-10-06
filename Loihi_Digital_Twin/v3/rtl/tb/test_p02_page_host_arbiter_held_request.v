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
    integer i = 0;

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

    task begin_debug_request;
        input [14:0] addr;
        begin
            @(negedge clk);
            debug_addr = addr;
            debug_req = 1'b1;
            #1;
            check(fabric_req, "fresh debug request was not forwarded");
            check(
                fabric_context_slot == debug_context_slot &&
                fabric_bank == debug_bank &&
                fabric_addr == addr,
                "forwarded debug request metadata mismatch"
            );

            // The ownership latch captures this request at the next clock.
            @(posedge clk);
            #1;
            check(!fabric_req, "captured debug request remained forwarded");
            check(debug_busy, "debug side was not busy for active request");
        end
    endtask

    task complete_debug_read;
        input [255:0] value;
        begin
            @(negedge clk);
            fabric_ack = 1'b1;
            fabric_rvalid = 1'b1;
            fabric_error = 1'b0;
            fabric_rdata = value;

            @(posedge clk);
            #1;
            check(debug_ack, "completed debug response was not latched");
            check(debug_rvalid, "completed debug read did not latch RVALID");
            check(!debug_error, "completed debug read latched an error");
            check(debug_rdata == value, "completed debug read latched wrong data");
            check(!fabric_req, "completed debug request was re-forwarded");
        end
    endtask

    task hold_response_visible;
        input [255:0] value;
        input integer cycles;
        begin
            for (i = 0; i < cycles; i = i + 1) begin
                @(posedge clk);
                #1;
                check(debug_ack,
                      "latched debug ACK did not remain visible while req stayed high");
                check(debug_rvalid,
                      "latched debug RVALID did not remain visible while req stayed high");
                check(!debug_error,
                      "latched debug response gained an error while held");
                check(debug_rdata == value,
                      "latched debug data changed while req stayed high");
                check(!fabric_req,
                      "held-high completed debug request was forwarded again");
                check(debug_busy,
                      "debug side stopped reporting busy before req release");
            end
        end
    endtask

    task release_debug_request;
        begin
            @(negedge clk);
            debug_req = 1'b0;

            @(posedge clk);
            #1;
            check(!debug_ack, "latched debug ACK did not clear after req went low");
            check(!debug_rvalid,
                  "latched debug RVALID did not clear after req went low");
            check(!debug_error,
                  "latched debug error did not clear after req went low");
            check(debug_rdata == 256'd0,
                  "latched debug data did not clear after req went low");
            check(!debug_busy,
                  "debug side did not release after request returned low");

            @(negedge clk);
            fabric_ack = 1'b0;
            fabric_rvalid = 1'b0;
            fabric_error = 1'b0;
            fabric_rdata = 256'd0;
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        // First transaction: leave the downstream response asserted for many
        // clocks. The arbiter must expose one stable latched response and must
        // not forward the still-high debug_req again.
        begin_debug_request(15'd7);
        complete_debug_read(256'hDEAD_BEEF);
        hold_response_visible(256'hDEAD_BEEF, 6);
        release_debug_request();

        repeat (2) @(posedge clk);

        // A genuinely new request after the low interval must work normally.
        begin_debug_request(15'd8);
        complete_debug_read(256'h1234);
        hold_response_visible(256'h1234, 3);
        release_debug_request();

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
