`timescale 1ns/1ps

module test_p02_context_page_bank_walker;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;

    reg cmd_start = 1'b0;
    reg cmd_page_out = 1'b0;
    reg cmd_mutable_only = 1'b0;
    reg [1:0] cmd_context_slot = 2'd0;
    reg [63:0] cmd_record_base = 64'h0000_0000_4000_0000;

    wire page_req;
    wire page_write;
    wire [1:0] page_context_slot;
    wire [3:0] page_bank;
    wire [14:0] page_addr;
    wire [255:0] page_wdata;
    wire page_busy;
    wire page_ack;
    wire page_rvalid;
    wire page_error;
    wire [255:0] page_rdata;

    reg debug_req = 1'b0;
    reg debug_write = 1'b0;
    reg [1:0] debug_context_slot = 2'd0;
    reg [3:0] debug_bank = 4'd0;
    reg [14:0] debug_addr = 15'd0;
    reg [255:0] debug_wdata = 256'd0;
    wire debug_busy;
    wire debug_ack;
    wire debug_rvalid;
    wire debug_error;
    wire [255:0] debug_rdata;

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

    wire ddr_req;
    wire ddr_write;
    wire [63:0] ddr_addr;
    wire [5:0] ddr_size_bytes;
    wire [255:0] ddr_wdata;
    reg ddr_busy = 1'b0;
    reg ddr_ack = 1'b0;
    reg ddr_rvalid = 1'b0;
    reg ddr_error = 1'b0;
    reg [255:0] ddr_rdata = 256'd0;

    wire busy;
    wire transfer_done;
    wire start_blocked;
    wire [31:0] bytes_transferred;
    wire [31:0] completed_transfers;
    wire [63:0] active_cycles;
    wire [63:0] last_transfer_cycles;
    wire error_command;
    wire error_host;
    wire error_ddr;

    reg [3:0] fabric_bank_q = 4'd0;
    reg [14:0] fabric_addr_q = 15'd0;
    reg fabric_write_q = 1'b0;
    reg [255:0] fabric_wdata_q = 256'd0;
    reg [1:0] fabric_context_q = 2'd0;

    reg [63:0] ddr_addr_q = 64'd0;
    reg [5:0] ddr_size_q = 6'd0;
    reg ddr_write_q = 1'b0;
    reg [255:0] ddr_wdata_q = 256'd0;

    reg [255:0] last_host_read_data = 256'd0;
    reg [3:0] last_host_read_bank = 4'd0;
    reg [14:0] last_host_read_addr = 15'd0;

    integer failure_count = 0;
    integer timeout = 0;
    integer fabric_write_count = 0;
    integer fabric_read_count = 0;
    integer ddr_read_count = 0;
    integer ddr_write_count = 0;
    integer before_count = 0;

    p02_context_page_bank_walker walker (
        .clk(clk),
        .resetn(resetn),
        .cmd_start(cmd_start),
        .cmd_page_out(cmd_page_out),
        .cmd_mutable_only(cmd_mutable_only),
        .cmd_context_slot(cmd_context_slot),
        .cmd_record_base(cmd_record_base),
        .host_req(page_req),
        .host_write(page_write),
        .host_context_slot(page_context_slot),
        .host_bank(page_bank),
        .host_addr(page_addr),
        .host_wdata(page_wdata),
        .host_busy(page_busy),
        .host_ack(page_ack),
        .host_rvalid(page_rvalid),
        .host_error(page_error),
        .host_rdata(page_rdata),
        .ddr_req(ddr_req),
        .ddr_write(ddr_write),
        .ddr_addr(ddr_addr),
        .ddr_size_bytes(ddr_size_bytes),
        .ddr_wdata(ddr_wdata),
        .ddr_busy(ddr_busy),
        .ddr_ack(ddr_ack),
        .ddr_rvalid(ddr_rvalid),
        .ddr_error(ddr_error),
        .ddr_rdata(ddr_rdata),
        .busy(busy),
        .transfer_done(transfer_done),
        .start_blocked(start_blocked),
        .bytes_transferred(bytes_transferred),
        .completed_transfers(completed_transfers),
        .active_cycles(active_cycles),
        .last_transfer_cycles(last_transfer_cycles),
        .error_command(error_command),
        .error_host(error_host),
        .error_ddr(error_ddr)
    );

    p02_page_host_arbiter arbiter (
        .clk(clk),
        .resetn(resetn),
        .page_active(busy),
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

    function [19:0] bank_offset;
        input [3:0] bank_id;
        begin
            case (bank_id)
                4'd0: bank_offset = 20'h01000;
                4'd1: bank_offset = 20'h05000;
                4'd2: bank_offset = 20'h07000;
                4'd3: bank_offset = 20'h0F000;
                4'd4: bank_offset = 20'h4F000;
                4'd5: bank_offset = 20'h50000;
                4'd6: bank_offset = 20'h54000;
                4'd9: bank_offset = 20'h58000;
                4'd7: bank_offset = 20'h5C000;
                4'd8: bank_offset = 20'h64000;
                default: bank_offset = 20'h00000;
            endcase
        end
    endfunction

    function [5:0] bank_bytes;
        input [3:0] bank_id;
        begin
            case (bank_id)
                4'd0: bank_bytes = 6'd16;
                4'd1, 4'd2, 4'd3, 4'd8: bank_bytes = 6'd8;
                4'd4, 4'd5, 4'd6, 4'd9: bank_bytes = 6'd4;
                4'd7: bank_bytes = 6'd32;
                default: bank_bytes = 6'd0;
            endcase
        end
    endfunction

    function [63:0] expected_address;
        input [63:0] base;
        input [3:0] bank_id;
        input [14:0] index;
        reg [63:0] byte_offset;
        begin
            case (bank_bytes(bank_id))
                6'd4: byte_offset = index << 2;
                6'd8: byte_offset = index << 3;
                6'd16: byte_offset = index << 4;
                6'd32: byte_offset = index << 5;
                default: byte_offset = 0;
            endcase
            expected_address = base + bank_offset(bank_id) + byte_offset;
        end
    endfunction

    function [255:0] ddr_read_pattern;
        input [63:0] address;
        begin
            ddr_read_pattern = 256'd0;
            ddr_read_pattern[63:0] = address;
            ddr_read_pattern[127:64] = ~address;
        end
    endfunction

    function [255:0] host_read_pattern;
        input [3:0] bank_id;
        input [14:0] index;
        reg [63:0] tag;
        begin
            tag = {12'd0, bank_id, 15'd0, index, 18'h15555};
            host_read_pattern = 256'd0;
            host_read_pattern[63:0] = tag;
            host_read_pattern[127:64] = ~tag;
        end
    endfunction

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

    task pulse_command;
        begin
            @(negedge clk);
            cmd_start = 1'b1;
            @(negedge clk);
            cmd_start = 1'b0;
        end
    endtask

    task wait_transfer_done;
        begin
            timeout = 0;
            while (!transfer_done && timeout < 1000000) begin
                @(negedge clk);
                timeout = timeout + 1;
            end
            if (!transfer_done) begin
                $display(
                    "FAIL: transfer timeout busy=%0d bytes=%0d completed=%0d",
                    busy, bytes_transferred, completed_transfers
                );
                failure_count = failure_count + 1;
            end
        end
    endtask

    always @(posedge clk) begin
        fabric_ack <= 1'b0;
        fabric_rvalid <= 1'b0;
        fabric_error <= 1'b0;

        if (!fabric_busy && fabric_req) begin
            fabric_busy <= 1'b1;
            fabric_write_q <= fabric_write;
            fabric_context_q <= fabric_context_slot;
            fabric_bank_q <= fabric_bank;
            fabric_addr_q <= fabric_addr;
            fabric_wdata_q <= fabric_wdata;
        end else if (fabric_busy) begin
            fabric_busy <= 1'b0;
            fabric_ack <= 1'b1;

            check(
                fabric_context_q == cmd_context_slot,
                "page walker changed the requested resident context slot"
            );

            if (fabric_write_q) begin
                fabric_write_count <= fabric_write_count + 1;
                check(
                    fabric_wdata_q ==
                        ddr_read_pattern(
                            expected_address(
                                cmd_record_base, fabric_bank_q, fabric_addr_q
                            )
                        ),
                    "page-in host write data/address mapping mismatch"
                );
            end else begin
                fabric_read_count <= fabric_read_count + 1;
                fabric_rvalid <= 1'b1;
                fabric_rdata <= host_read_pattern(fabric_bank_q, fabric_addr_q);
                last_host_read_data <= host_read_pattern(
                    fabric_bank_q, fabric_addr_q
                );
                last_host_read_bank <= fabric_bank_q;
                last_host_read_addr <= fabric_addr_q;
            end
        end
    end

    always @(posedge clk) begin
        ddr_ack <= 1'b0;
        ddr_rvalid <= 1'b0;
        ddr_error <= 1'b0;

        if (!ddr_busy && ddr_req) begin
            ddr_busy <= 1'b1;
            ddr_write_q <= ddr_write;
            ddr_addr_q <= ddr_addr;
            ddr_size_q <= ddr_size_bytes;
            ddr_wdata_q <= ddr_wdata;

            if (ddr_write) begin
                check(
                    ddr_addr ==
                        expected_address(
                            cmd_record_base,
                            last_host_read_bank,
                            last_host_read_addr
                        ),
                    "page-out DDR address does not match preceding resident read"
                );
                check(
                    ddr_wdata == last_host_read_data,
                    "page-out DDR data does not match preceding resident read"
                );
            end
        end else if (ddr_busy) begin
            ddr_busy <= 1'b0;
            ddr_ack <= 1'b1;
            if (ddr_write_q) begin
                ddr_write_count <= ddr_write_count + 1;
            end else begin
                ddr_read_count <= ddr_read_count + 1;
                ddr_rvalid <= 1'b1;
                ddr_rdata <= ddr_read_pattern(ddr_addr_q);
            end
        end
    end

    initial begin
        repeat (5) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (3) @(posedge clk);

        cmd_page_out = 1'b0;
        cmd_mutable_only = 1'b0;
        cmd_context_slot = 2'd0;
        cmd_record_base = 64'h0000_0000_4000_1000;
        pulse_command();
        check(start_blocked && error_command && !busy,
              "misaligned DDR record base was not rejected");

        cmd_record_base = 64'h0000_0000_4000_0000;
        cmd_context_slot = 2'd2;
        cmd_page_out = 1'b0;
        cmd_mutable_only = 1'b0;
        pulse_command();
        check(busy && !error_command,
              "valid full page-in did not start");

        @(negedge clk);
        debug_req = 1'b1;
        @(posedge clk);
        check(debug_busy && !debug_ack,
              "debug transaction was not blocked by page ownership");
        @(negedge clk);
        debug_req = 1'b0;

        wait_transfer_done();
        check(!busy, "full page-in did not retire");
        check(bytes_transferred == 32'h0006_B000,
              "full page-in byte count is not 428 KiB");
        check(completed_transfers == 32'd1,
              "full page-in did not increment completed transfer count");
        check(last_transfer_cycles != 64'd0,
              "full page-in reported zero cycles");
        check(!error_host && !error_ddr,
              "full page-in raised host or DDR error");
        check(fabric_write_count == 57344,
              "full page-in resident write count mismatch");
        check(ddr_read_count == 57344,
              "full page-in DDR read count mismatch");

        before_count = fabric_read_count;
        cmd_page_out = 1'b1;
        cmd_mutable_only = 1'b1;
        cmd_context_slot = 2'd2;
        pulse_command();
        wait_transfer_done();

        check(bytes_transferred == 32'h0001_A000,
              "mutable-only page-out byte count is not 104 KiB");
        check(completed_transfers == 32'd2,
              "mutable-only page-out did not complete");
        check((fabric_read_count - before_count) == 14336,
              "mutable-only resident read count mismatch");
        check(ddr_write_count == 14336,
              "mutable-only DDR write count mismatch");
        check(!error_host && !error_ddr,
              "mutable-only page-out raised host or DDR error");

        before_count = fabric_read_count;
        cmd_page_out = 1'b1;
        cmd_mutable_only = 1'b0;
        cmd_context_slot = 2'd1;
        cmd_record_base = 64'h0000_0000_4080_0000;
        pulse_command();
        wait_transfer_done();

        check(bytes_transferred == 32'h0006_B000,
              "full page-out byte count is not 428 KiB");
        check(completed_transfers == 32'd3,
              "full page-out did not complete");
        check((fabric_read_count - before_count) == 57344,
              "full page-out resident read count mismatch");
        check((ddr_write_count - 14336) == 57344,
              "full page-out DDR write count mismatch");

        cmd_page_out = 1'b0;
        cmd_mutable_only = 1'b1;
        cmd_context_slot = 2'd0;
        cmd_record_base = 64'h0000_0000_4000_0000;
        pulse_command();
        check(start_blocked && error_command && !busy,
              "mutable-only page-in was not rejected");

        if (failure_count == 0)
            $display("PASS: p02_context_page_bank_walker");
        else
            $display(
                "FAIL: p02_context_page_bank_walker failures=%0d",
                failure_count
            );
        $finish;
    end
endmodule
