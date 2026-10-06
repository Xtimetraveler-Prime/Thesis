`timescale 1ns/1ps

module test_p02_ddr_backing_range_guard;
    reg req = 1'b0;
    reg req_write = 1'b0;
    reg [63:0] req_addr = 64'd0;
    reg [5:0] req_size_bytes = 6'd8;
    reg [255:0] req_wdata = 256'h1234;

    wire downstream_req;
    wire downstream_write;
    wire [63:0] downstream_addr;
    wire [5:0] downstream_size_bytes;
    wire [255:0] downstream_wdata;

    reg downstream_busy = 1'b0;
    reg downstream_ack = 1'b0;
    reg downstream_rvalid = 1'b0;
    reg downstream_error = 1'b0;
    reg [255:0] downstream_rdata = 256'hCAFE;

    wire busy;
    wire ack;
    wire rvalid;
    wire error;
    wire [255:0] rdata;
    wire range_error;

    integer failure_count = 0;

    p02_ddr_backing_range_guard dut (
        .req(req),
        .req_write(req_write),
        .req_addr(req_addr),
        .req_size_bytes(req_size_bytes),
        .req_wdata(req_wdata),
        .downstream_req(downstream_req),
        .downstream_write(downstream_write),
        .downstream_addr(downstream_addr),
        .downstream_size_bytes(downstream_size_bytes),
        .downstream_wdata(downstream_wdata),
        .downstream_busy(downstream_busy),
        .downstream_ack(downstream_ack),
        .downstream_rvalid(downstream_rvalid),
        .downstream_error(downstream_error),
        .downstream_rdata(downstream_rdata),
        .busy(busy),
        .ack(ack),
        .rvalid(rvalid),
        .error(error),
        .rdata(rdata),
        .range_error(range_error)
    );

    task check;
        input condition;
        input [8*120-1:0] message;
        begin
            if (!condition) begin
                $display("FAIL: %0s", message);
                failure_count = failure_count + 1;
            end
        end
    endtask

    initial begin
        req = 1'b1;
        req_addr = 64'h0000_0000_4000_1000;
        req_size_bytes = 6'd16;
        #1;
        check(downstream_req && !range_error,
              "valid backing request was blocked");
        check(
            downstream_addr == req_addr &&
            downstream_size_bytes == req_size_bytes &&
            downstream_wdata == req_wdata,
            "valid backing request fields changed"
        );

        downstream_busy = 1'b1;
        #1;
        check(busy, "downstream busy was not propagated");
        downstream_busy = 1'b0;
        downstream_ack = 1'b1;
        downstream_rvalid = 1'b1;
        #1;
        check(ack && rvalid && !error && rdata == downstream_rdata,
              "valid response was not propagated");

        downstream_ack = 1'b0;
        downstream_rvalid = 1'b0;

        req_addr = 64'h0000_0000_3FFF_FFF8;
        req_size_bytes = 6'd8;
        #1;
        check(!downstream_req && ack && error && range_error,
              "request below backing window was not rejected");

        req_addr = 64'h0000_0000_43FF_FFF8;
        req_size_bytes = 6'd8;
        #1;
        check(downstream_req && !range_error,
              "request ending exactly at backing limit was rejected");

        req_addr = 64'h0000_0000_43FF_FFF8;
        req_size_bytes = 6'd16;
        #1;
        check(!downstream_req && ack && error && range_error,
              "request crossing backing limit was not rejected");

        req_addr = 64'h0000_0000_4400_0000;
        req_size_bytes = 6'd4;
        #1;
        check(!downstream_req && ack && error && range_error,
              "request starting at exclusive limit was not rejected");

        req_addr = 64'h0000_0000_4000_0000;
        req_size_bytes = 6'd0;
        #1;
        check(!downstream_req && ack && error && range_error,
              "zero-byte request was not rejected");

        if (failure_count == 0)
            $display("PASS: p02_ddr_backing_range_guard");
        else
            $display(
                "FAIL: p02_ddr_backing_range_guard failures=%0d",
                failure_count
            );
        $finish;
    end
endmodule
