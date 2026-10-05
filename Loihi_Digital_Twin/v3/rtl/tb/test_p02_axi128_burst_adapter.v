`timescale 1ns/1ps

module test_p02_axi128_burst_adapter;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;

    reg req = 1'b0;
    reg req_write = 1'b0;
    reg [63:0] req_addr = 64'd0;
    reg [5:0] req_size_bytes = 6'd0;
    reg [255:0] req_wdata = 256'd0;
    wire busy;
    wire ack;
    wire rvalid;
    wire error;
    wire [255:0] rdata;

    wire [31:0] completed_read_bursts;
    wire [31:0] completed_write_bursts;
    wire [63:0] axi_bytes_moved;
    wire [8:0] pending_write_bytes;
    wire protocol_error;

    wire [0:0] m_axi_awid;
    wire [48:0] m_axi_awaddr;
    wire [7:0] m_axi_awlen;
    wire [2:0] m_axi_awsize;
    wire [1:0] m_axi_awburst;
    wire m_axi_awlock;
    wire [3:0] m_axi_awcache;
    wire [2:0] m_axi_awprot;
    wire [3:0] m_axi_awqos;
    wire m_axi_awvalid;
    reg m_axi_awready = 1'b1;

    wire [127:0] m_axi_wdata;
    wire [15:0] m_axi_wstrb;
    wire m_axi_wlast;
    wire m_axi_wvalid;
    reg m_axi_wready = 1'b1;

    reg [0:0] m_axi_bid = 1'b0;
    reg [1:0] m_axi_bresp = 2'b00;
    reg m_axi_bvalid = 1'b0;
    wire m_axi_bready;

    wire [0:0] m_axi_arid;
    wire [48:0] m_axi_araddr;
    wire [7:0] m_axi_arlen;
    wire [2:0] m_axi_arsize;
    wire [1:0] m_axi_arburst;
    wire m_axi_arlock;
    wire [3:0] m_axi_arcache;
    wire [2:0] m_axi_arprot;
    wire [3:0] m_axi_arqos;
    wire m_axi_arvalid;
    reg m_axi_arready = 1'b1;

    reg [0:0] m_axi_rid = 1'b0;
    wire [127:0] m_axi_rdata;
    reg [1:0] m_axi_rresp = 2'b00;
    wire m_axi_rlast;
    wire m_axi_rvalid;
    wire m_axi_rready;

    integer failure_count = 0;
    integer timeout = 0;
    integer ar_count = 0;
    integer aw_count = 0;
    integer write_beat_count = 0;

    reg read_active = 1'b0;
    reg [48:0] read_base = 49'd0;
    reg [4:0] read_index = 5'd0;

    reg write_active = 1'b0;
    reg [48:0] write_base = 49'd0;
    reg [4:0] write_index = 5'd0;
    reg inject_write_error = 1'b0;
    reg write_error_latched = 1'b0;

    reg last_scalar_error = 1'b0;
    reg [255:0] last_scalar_rdata = 256'd0;
    reg last_scalar_rvalid = 1'b0;

    p02_axi128_burst_adapter dut (
        .clk(clk),
        .resetn(resetn),
        .req(req),
        .req_write(req_write),
        .req_addr(req_addr),
        .req_size_bytes(req_size_bytes),
        .req_wdata(req_wdata),
        .busy(busy),
        .ack(ack),
        .rvalid(rvalid),
        .error(error),
        .rdata(rdata),
        .completed_read_bursts(completed_read_bursts),
        .completed_write_bursts(completed_write_bursts),
        .axi_bytes_moved(axi_bytes_moved),
        .pending_write_bytes(pending_write_bytes),
        .protocol_error(protocol_error),
        .m_axi_awid(m_axi_awid),
        .m_axi_awaddr(m_axi_awaddr),
        .m_axi_awlen(m_axi_awlen),
        .m_axi_awsize(m_axi_awsize),
        .m_axi_awburst(m_axi_awburst),
        .m_axi_awlock(m_axi_awlock),
        .m_axi_awcache(m_axi_awcache),
        .m_axi_awprot(m_axi_awprot),
        .m_axi_awqos(m_axi_awqos),
        .m_axi_awvalid(m_axi_awvalid),
        .m_axi_awready(m_axi_awready),
        .m_axi_wdata(m_axi_wdata),
        .m_axi_wstrb(m_axi_wstrb),
        .m_axi_wlast(m_axi_wlast),
        .m_axi_wvalid(m_axi_wvalid),
        .m_axi_wready(m_axi_wready),
        .m_axi_bid(m_axi_bid),
        .m_axi_bresp(m_axi_bresp),
        .m_axi_bvalid(m_axi_bvalid),
        .m_axi_bready(m_axi_bready),
        .m_axi_arid(m_axi_arid),
        .m_axi_araddr(m_axi_araddr),
        .m_axi_arlen(m_axi_arlen),
        .m_axi_arsize(m_axi_arsize),
        .m_axi_arburst(m_axi_arburst),
        .m_axi_arlock(m_axi_arlock),
        .m_axi_arcache(m_axi_arcache),
        .m_axi_arprot(m_axi_arprot),
        .m_axi_arqos(m_axi_arqos),
        .m_axi_arvalid(m_axi_arvalid),
        .m_axi_arready(m_axi_arready),
        .m_axi_rid(m_axi_rid),
        .m_axi_rdata(m_axi_rdata),
        .m_axi_rresp(m_axi_rresp),
        .m_axi_rlast(m_axi_rlast),
        .m_axi_rvalid(m_axi_rvalid),
        .m_axi_rready(m_axi_rready)
    );

    function [127:0] pattern128;
        input [63:0] address;
        integer i;
        begin
            pattern128 = 128'd0;
            for (i = 0; i < 16; i = i + 1)
                pattern128[(i * 8) +: 8] = (address + i) & 8'hFF;
        end
    endfunction

    function [255:0] scalar_pattern;
        input [63:0] address;
        input [5:0] size_bytes;
        integer i;
        begin
            scalar_pattern = 256'd0;
            for (i = 0; i < 32; i = i + 1)
                if (i < size_bytes)
                    scalar_pattern[(i * 8) +: 8] =
                        (address + i) & 8'hFF;
        end
    endfunction

    assign m_axi_rvalid = read_active;
    assign m_axi_rdata =
        pattern128({15'd0, read_base} + (read_index * 16));
    assign m_axi_rlast = read_active && (read_index == 5'd15);

    task check;
        input condition;
        input [8*128-1:0] message;
        begin
            if (!condition) begin
                $display("FAIL: %0s", message);
                failure_count = failure_count + 1;
            end
        end
    endtask

    task scalar_read;
        input [63:0] address;
        input [5:0] size_bytes;
        begin
            while (busy) @(negedge clk);
            @(negedge clk);
            req_write = 1'b0;
            req_addr = address;
            req_size_bytes = size_bytes;
            req_wdata = 256'd0;
            req = 1'b1;
            @(negedge clk);
            req = 1'b0;

            timeout = 0;
            while (!ack && timeout < 500) begin
                @(negedge clk);
                timeout = timeout + 1;
            end
            check(ack, "scalar read timed out");
            last_scalar_error = error;
            last_scalar_rvalid = rvalid;
            last_scalar_rdata = rdata;
        end
    endtask

    task scalar_write;
        input [63:0] address;
        input [5:0] size_bytes;
        begin
            while (busy) @(negedge clk);
            @(negedge clk);
            req_write = 1'b1;
            req_addr = address;
            req_size_bytes = size_bytes;
            req_wdata = scalar_pattern(address, size_bytes);
            req = 1'b1;
            @(negedge clk);
            req = 1'b0;

            timeout = 0;
            while (!ack && timeout < 500) begin
                @(negedge clk);
                timeout = timeout + 1;
            end
            check(ack, "scalar write timed out");
            last_scalar_error = error;
            last_scalar_rvalid = rvalid;
            last_scalar_rdata = rdata;
        end
    endtask

    always @(posedge clk) begin
        if (!resetn) begin
            read_active <= 1'b0;
            read_base <= 49'd0;
            read_index <= 5'd0;
            ar_count <= 0;
        end else begin
            if (m_axi_arvalid && m_axi_arready) begin
                check(!read_active, "new AR issued while prior read burst active");
                check(m_axi_arlen == 8'd15, "ARLEN is not 16 beats");
                check(m_axi_arsize == 3'd4, "ARSIZE is not 16 bytes");
                check(m_axi_arburst == 2'b01, "ARBURST is not INCR");
                check(m_axi_araddr[7:0] == 8'd0,
                      "ARADDR is not 256-byte aligned");
                check(m_axi_araddr[11:0] <= 12'hF00,
                      "read burst would cross a 4 KiB boundary");
                read_active <= 1'b1;
                read_base <= m_axi_araddr;
                read_index <= 5'd0;
                ar_count <= ar_count + 1;
            end

            if (read_active && m_axi_rready) begin
                if (read_index == 5'd15) begin
                    read_active <= 1'b0;
                    read_index <= 5'd0;
                end else begin
                    read_index <= read_index + 5'd1;
                end
            end
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            write_active <= 1'b0;
            write_base <= 49'd0;
            write_index <= 5'd0;
            aw_count <= 0;
            write_beat_count <= 0;
            m_axi_bvalid <= 1'b0;
            m_axi_bresp <= 2'b00;
            write_error_latched <= 1'b0;
        end else begin
            if (m_axi_bvalid && m_axi_bready)
                m_axi_bvalid <= 1'b0;

            if (m_axi_awvalid && m_axi_awready) begin
                check(!write_active, "new AW issued while prior write burst active");
                check(m_axi_awlen == 8'd15, "AWLEN is not 16 beats");
                check(m_axi_awsize == 3'd4, "AWSIZE is not 16 bytes");
                check(m_axi_awburst == 2'b01, "AWBURST is not INCR");
                check(m_axi_awaddr[7:0] == 8'd0,
                      "AWADDR is not 256-byte aligned");
                check(m_axi_awaddr[11:0] <= 12'hF00,
                      "write burst would cross a 4 KiB boundary");
                write_active <= 1'b1;
                write_base <= m_axi_awaddr;
                write_index <= 5'd0;
                aw_count <= aw_count + 1;
                write_error_latched <= inject_write_error;
            end

            if (write_active && m_axi_wvalid && m_axi_wready) begin
                check(m_axi_wstrb == 16'hFFFF,
                      "write burst did not assert all byte strobes");
                check(
                    m_axi_wdata ==
                        pattern128(
                            {15'd0, write_base} + (write_index * 16)
                        ),
                    "write burst data packing mismatch"
                );
                check(
                    m_axi_wlast == (write_index == 5'd15),
                    "WLAST mismatch"
                );
                write_beat_count <= write_beat_count + 1;

                if (write_index == 5'd15) begin
                    write_active <= 1'b0;
                    write_index <= 5'd0;
                    m_axi_bvalid <= 1'b1;
                    m_axi_bresp <= write_error_latched ? 2'b10 : 2'b00;
                end else begin
                    write_index <= write_index + 5'd1;
                end
            end
        end
    end

    integer i;
    initial begin
        repeat (5) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (3) @(posedge clk);

        // Unsupported scalar sizes are rejected before AXI.
        scalar_read(64'h4000_1000, 6'd12);
        check(last_scalar_error && protocol_error,
              "unsupported scalar size was not rejected");
        check(ar_count == 0 && aw_count == 0,
              "invalid request unexpectedly reached AXI");

        // Thirty-two 8-byte reads fit exactly in one 256-byte prefetch.
        for (i = 0; i < 32; i = i + 1) begin
            scalar_read(64'h4000_5000 + (i * 8), 6'd8);
            check(!last_scalar_error && last_scalar_rvalid,
                  "valid 8-byte scalar read failed");
            check(
                last_scalar_rdata[63:0] ==
                    scalar_pattern(64'h4000_5000 + (i * 8), 6'd8)[63:0],
                "8-byte read data mismatch"
            );
        end
        check(ar_count == 1 && completed_read_bursts == 1,
              "8-byte reads did not collapse to one AXI burst");

        // Eight 32-byte trace-style reads also use one 256-byte burst.
        for (i = 0; i < 8; i = i + 1) begin
            scalar_read(64'h4005_C000 + (i * 32), 6'd32);
            check(!last_scalar_error && last_scalar_rvalid,
                  "valid 32-byte scalar read failed");
            check(
                last_scalar_rdata ==
                    scalar_pattern(64'h4005_C000 + (i * 32), 6'd32),
                "32-byte read data mismatch"
            );
        end
        check(ar_count == 2 && completed_read_bursts == 2,
              "32-byte reads did not collapse to one AXI burst");

        // Sixty-four 4-byte writes are packed into one 16-beat AXI burst.
        inject_write_error = 1'b0;
        for (i = 0; i < 64; i = i + 1) begin
            scalar_write(64'h4005_4000 + (i * 4), 6'd4);
            check(!last_scalar_error, "valid 4-byte scalar write failed");
        end
        check(aw_count == 1 && completed_write_bursts == 1,
              "4-byte writes did not collapse to one AXI burst");
        check(write_beat_count == 16,
              "first write burst did not contain 16 beats");
        check(pending_write_bytes == 0,
              "write coalescer retained bytes after successful burst");

        // Eight 32-byte writes form a second complete burst.
        for (i = 0; i < 8; i = i + 1) begin
            scalar_write(64'h4005_C000 + (i * 32), 6'd32);
            check(!last_scalar_error, "valid 32-byte scalar write failed");
        end
        check(aw_count == 2 && completed_write_bursts == 2,
              "32-byte writes did not collapse to one AXI burst");
        check(write_beat_count == 32,
              "second write burst beat accounting mismatch");

        // The scalar request completing a failing burst receives the AXI error.
        inject_write_error = 1'b1;
        for (i = 0; i < 31; i = i + 1) begin
            scalar_write(64'h4000_7000 + (i * 8), 6'd8);
            check(!last_scalar_error,
                  "intermediate write reported an early AXI error");
        end
        scalar_write(64'h4000_7000 + (31 * 8), 6'd8);
        check(last_scalar_error,
              "AXI BRESP error was not propagated to final scalar write");
        check(aw_count == 3 && completed_write_bursts == 2,
              "failed burst incorrectly advanced successful burst count");
        check(pending_write_bytes == 0,
              "failed burst did not release the write buffer");

        check(axi_bytes_moved == (64'd4 * 64'd256),
              "successful AXI byte accounting mismatch");

        if (failure_count == 0)
            $display("PASS: p02_axi128_burst_adapter");
        else
            $display(
                "FAIL: p02_axi128_burst_adapter failures=%0d",
                failure_count
            );
        $finish;
    end
endmodule
