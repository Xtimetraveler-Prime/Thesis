`timescale 1ns/1ps

// FPGA-v3 P02.3a resident-context page bank walker.
//
// This block freezes the PL-side sequencing between one 512 KiB DDR backing
// record and the ten accepted P05 resident-memory banks.  It deliberately does
// NOT implement AXI itself.  P02.3b will place a burst-capable AXI adapter on
// the ddr_* request/response side.
//
// The resident-memory side reuses the accepted P05 scalar host/debug contract.
// A page-in walks every payload bank in DDR offset order.  A page-out may walk
// either every payload bank or only the mutable runtime banks.
//
// DDR payload order / P05 host bank IDs:
//   config            0x01000  bank 0  1024 x 16 B
//   state             0x05000  bank 1  1024 x  8 B
//   axon              0x07000  bank 2  4096 x  8 B
//   synapse           0x0F000  bank 3 32768 x  8 B
//   route descriptor  0x4F000  bank 4  1024 x  4 B
//   route             0x50000  bank 5  4096 x  4 B
//   event0            0x54000  bank 6  4096 x  4 B
//   event1            0x58000  bank 9  4096 x  4 B
//   trace             0x5C000  bank 7  1024 x 32 B
//   packet            0x64000  bank 8  4096 x  8 B
//
// Header [0x00000,0x01000) and reserved tail [0x6C000,0x80000) are not
// resident URAM and are therefore not walked by this block.
module p02_context_page_bank_walker (
    input  wire         clk,
    input  wire         resetn,

    input  wire         cmd_start,
    input  wire         cmd_page_out,
    input  wire         cmd_mutable_only,
    input  wire [1:0]   cmd_context_slot,
    input  wire [63:0]  cmd_record_base,

    output reg          host_req,
    output reg          host_write,
    output reg  [1:0]   host_context_slot,
    output reg  [3:0]   host_bank,
    output reg  [14:0]  host_addr,
    output reg  [255:0] host_wdata,
    input  wire         host_busy,
    input  wire         host_ack,
    input  wire         host_rvalid,
    input  wire         host_error,
    input  wire [255:0] host_rdata,

    output reg          ddr_req,
    output reg          ddr_write,
    output reg  [63:0]  ddr_addr,
    output reg  [5:0]   ddr_size_bytes,
    output reg  [255:0] ddr_wdata,
    input  wire         ddr_busy,
    input  wire         ddr_ack,
    input  wire         ddr_rvalid,
    input  wire         ddr_error,
    input  wire [255:0] ddr_rdata,

    output reg          busy,
    output reg          transfer_done,
    output reg          start_blocked,
    output reg  [31:0]  bytes_transferred,
    output reg  [31:0]  completed_transfers,
    output reg  [63:0]  active_cycles,
    output reg  [63:0]  last_transfer_cycles,
    output reg          error_command,
    output reg          error_host,
    output reg          error_ddr
);
    localparam [3:0] ST_IDLE            = 4'd0;
    localparam [3:0] ST_DDR_READ_ISSUE  = 4'd1;
    localparam [3:0] ST_DDR_READ_WAIT   = 4'd2;
    localparam [3:0] ST_HOST_WRITE_ISSUE= 4'd3;
    localparam [3:0] ST_HOST_WRITE_WAIT = 4'd4;
    localparam [3:0] ST_HOST_READ_ISSUE = 4'd5;
    localparam [3:0] ST_HOST_READ_WAIT  = 4'd6;
    localparam [3:0] ST_DDR_WRITE_ISSUE = 4'd7;
    localparam [3:0] ST_DDR_WRITE_WAIT  = 4'd8;

    reg [3:0] state;
    reg cmd_start_d;
    reg page_out_latched;
    reg mutable_only_latched;
    reg [1:0] context_latched;
    reg [63:0] record_base_latched;
    reg [3:0] sequence_index;
    reg [14:0] word_index;
    reg [255:0] word_buffer;

    function [3:0] bank_id_for_sequence;
        input [3:0] index;
        input mutable_only;
        begin
            if (mutable_only) begin
                case (index)
                    4'd0: bank_id_for_sequence = 4'd1; // state
                    4'd1: bank_id_for_sequence = 4'd6; // event0
                    4'd2: bank_id_for_sequence = 4'd9; // event1
                    4'd3: bank_id_for_sequence = 4'd7; // trace
                    4'd4: bank_id_for_sequence = 4'd8; // packet
                    default: bank_id_for_sequence = 4'd15;
                endcase
            end else begin
                case (index)
                    4'd0: bank_id_for_sequence = 4'd0;
                    4'd1: bank_id_for_sequence = 4'd1;
                    4'd2: bank_id_for_sequence = 4'd2;
                    4'd3: bank_id_for_sequence = 4'd3;
                    4'd4: bank_id_for_sequence = 4'd4;
                    4'd5: bank_id_for_sequence = 4'd5;
                    4'd6: bank_id_for_sequence = 4'd6;
                    4'd7: bank_id_for_sequence = 4'd9;
                    4'd8: bank_id_for_sequence = 4'd7;
                    4'd9: bank_id_for_sequence = 4'd8;
                    default: bank_id_for_sequence = 4'd15;
                endcase
            end
        end
    endfunction

    function [15:0] bank_depth;
        input [3:0] bank_id;
        begin
            case (bank_id)
                4'd0, 4'd1, 4'd4, 4'd7: bank_depth = 16'd1024;
                4'd2, 4'd5, 4'd6, 4'd8, 4'd9: bank_depth = 16'd4096;
                4'd3: bank_depth = 16'd32768;
                default: bank_depth = 16'd0;
            endcase
        end
    endfunction

    function [5:0] bank_word_bytes;
        input [3:0] bank_id;
        begin
            case (bank_id)
                4'd0: bank_word_bytes = 6'd16;
                4'd1, 4'd2, 4'd3, 4'd8: bank_word_bytes = 6'd8;
                4'd4, 4'd5, 4'd6, 4'd9: bank_word_bytes = 6'd4;
                4'd7: bank_word_bytes = 6'd32;
                default: bank_word_bytes = 6'd0;
            endcase
        end
    endfunction

    function [19:0] bank_ddr_offset;
        input [3:0] bank_id;
        begin
            case (bank_id)
                4'd0: bank_ddr_offset = 20'h01000;
                4'd1: bank_ddr_offset = 20'h05000;
                4'd2: bank_ddr_offset = 20'h07000;
                4'd3: bank_ddr_offset = 20'h0F000;
                4'd4: bank_ddr_offset = 20'h4F000;
                4'd5: bank_ddr_offset = 20'h50000;
                4'd6: bank_ddr_offset = 20'h54000;
                4'd9: bank_ddr_offset = 20'h58000;
                4'd7: bank_ddr_offset = 20'h5C000;
                4'd8: bank_ddr_offset = 20'h64000;
                default: bank_ddr_offset = 20'h00000;
            endcase
        end
    endfunction

    function [63:0] word_byte_offset;
        input [14:0] index;
        input [5:0] word_bytes;
        begin
            case (word_bytes)
                6'd4:  word_byte_offset = {47'd0, index, 2'b00};
                6'd8:  word_byte_offset = {46'd0, index, 3'b000};
                6'd16: word_byte_offset = {45'd0, index, 4'b0000};
                6'd32: word_byte_offset = {44'd0, index, 5'b00000};
                default: word_byte_offset = 64'd0;
            endcase
        end
    endfunction

    wire [3:0] current_bank =
        bank_id_for_sequence(sequence_index, mutable_only_latched);
    wire [15:0] current_depth = bank_depth(current_bank);
    wire [5:0] current_word_bytes = bank_word_bytes(current_bank);
    wire [63:0] current_ddr_address =
        record_base_latched +
        {44'd0, bank_ddr_offset(current_bank)} +
        word_byte_offset(word_index, current_word_bytes);
    wire [3:0] sequence_length = mutable_only_latched ? 4'd5 : 4'd10;
    wire last_word = ({1'b0, word_index} == (current_depth - 16'd1));
    wire last_bank = (sequence_index == (sequence_length - 4'd1));

    wire cmd_request = cmd_start && !cmd_start_d;
    wire command_valid =
        (cmd_context_slot < 2'd3) &&
        (cmd_record_base[18:0] == 19'd0) &&
        !(cmd_mutable_only && !cmd_page_out);

    task advance_word;
        input [3:0] next_state;
        begin
            bytes_transferred <= bytes_transferred + current_word_bytes;
            if (last_word) begin
                if (last_bank) begin
                    busy <= 1'b0;
                    transfer_done <= 1'b1;
                    completed_transfers <= completed_transfers + 32'd1;
                    last_transfer_cycles <= active_cycles + 64'd1;
                    state <= ST_IDLE;
                end else begin
                    sequence_index <= sequence_index + 4'd1;
                    word_index <= 15'd0;
                    state <= next_state;
                end
            end else begin
                word_index <= word_index + 15'd1;
                state <= next_state;
            end
        end
    endtask

    task fail_transfer;
        input host_failure;
        input ddr_failure;
        begin
            busy <= 1'b0;
            transfer_done <= 1'b1;
            error_host <= error_host || host_failure;
            error_ddr <= error_ddr || ddr_failure;
            last_transfer_cycles <= active_cycles + 64'd1;
            state <= ST_IDLE;
        end
    endtask

    always @(posedge clk) begin
        if (!resetn) begin
            state <= ST_IDLE;
            cmd_start_d <= 1'b0;
            page_out_latched <= 1'b0;
            mutable_only_latched <= 1'b0;
            context_latched <= 2'd0;
            record_base_latched <= 64'd0;
            sequence_index <= 4'd0;
            word_index <= 15'd0;
            word_buffer <= 256'd0;

            host_req <= 1'b0;
            host_write <= 1'b0;
            host_context_slot <= 2'd0;
            host_bank <= 4'd0;
            host_addr <= 15'd0;
            host_wdata <= 256'd0;

            ddr_req <= 1'b0;
            ddr_write <= 1'b0;
            ddr_addr <= 64'd0;
            ddr_size_bytes <= 6'd0;
            ddr_wdata <= 256'd0;

            busy <= 1'b0;
            transfer_done <= 1'b0;
            start_blocked <= 1'b0;
            bytes_transferred <= 32'd0;
            completed_transfers <= 32'd0;
            active_cycles <= 64'd0;
            last_transfer_cycles <= 64'd0;
            error_command <= 1'b0;
            error_host <= 1'b0;
            error_ddr <= 1'b0;
        end else begin
            cmd_start_d <= cmd_start;
            host_req <= 1'b0;
            ddr_req <= 1'b0;
            transfer_done <= 1'b0;
            start_blocked <= 1'b0;

            if (cmd_request && !busy) begin
                if (command_valid) begin
                    page_out_latched <= cmd_page_out;
                    mutable_only_latched <= cmd_mutable_only;
                    context_latched <= cmd_context_slot;
                    record_base_latched <= cmd_record_base;
                    sequence_index <= 4'd0;
                    word_index <= 15'd0;
                    bytes_transferred <= 32'd0;
                    active_cycles <= 64'd0;
                    error_command <= 1'b0;
                    error_host <= 1'b0;
                    error_ddr <= 1'b0;
                    busy <= 1'b1;
                    state <= cmd_page_out ? ST_HOST_READ_ISSUE : ST_DDR_READ_ISSUE;
                end else begin
                    start_blocked <= 1'b1;
                    error_command <= 1'b1;
                end
            end

            if (busy)
                active_cycles <= active_cycles + 64'd1;

            case (state)
                ST_IDLE: begin
                end

                ST_DDR_READ_ISSUE: begin
                    if (!ddr_busy) begin
                        ddr_req <= 1'b1;
                        ddr_write <= 1'b0;
                        ddr_addr <= current_ddr_address;
                        ddr_size_bytes <= current_word_bytes;
                        ddr_wdata <= 256'd0;
                        state <= ST_DDR_READ_WAIT;
                    end
                end

                ST_DDR_READ_WAIT: begin
                    if (ddr_ack) begin
                        if (ddr_error || !ddr_rvalid) begin
                            fail_transfer(1'b0, 1'b1);
                        end else begin
                            word_buffer <= ddr_rdata;
                            state <= ST_HOST_WRITE_ISSUE;
                        end
                    end
                end

                ST_HOST_WRITE_ISSUE: begin
                    if (!host_busy) begin
                        host_req <= 1'b1;
                        host_write <= 1'b1;
                        host_context_slot <= context_latched;
                        host_bank <= current_bank;
                        host_addr <= word_index;
                        host_wdata <= word_buffer;
                        state <= ST_HOST_WRITE_WAIT;
                    end
                end

                ST_HOST_WRITE_WAIT: begin
                    if (host_ack) begin
                        if (host_error)
                            fail_transfer(1'b1, 1'b0);
                        else
                            advance_word(ST_DDR_READ_ISSUE);
                    end
                end

                ST_HOST_READ_ISSUE: begin
                    if (!host_busy) begin
                        host_req <= 1'b1;
                        host_write <= 1'b0;
                        host_context_slot <= context_latched;
                        host_bank <= current_bank;
                        host_addr <= word_index;
                        host_wdata <= 256'd0;
                        state <= ST_HOST_READ_WAIT;
                    end
                end

                ST_HOST_READ_WAIT: begin
                    if (host_ack) begin
                        if (host_error || !host_rvalid) begin
                            fail_transfer(1'b1, 1'b0);
                        end else begin
                            word_buffer <= host_rdata;
                            state <= ST_DDR_WRITE_ISSUE;
                        end
                    end
                end

                ST_DDR_WRITE_ISSUE: begin
                    if (!ddr_busy) begin
                        ddr_req <= 1'b1;
                        ddr_write <= 1'b1;
                        ddr_addr <= current_ddr_address;
                        ddr_size_bytes <= current_word_bytes;
                        ddr_wdata <= word_buffer;
                        state <= ST_DDR_WRITE_WAIT;
                    end
                end

                ST_DDR_WRITE_WAIT: begin
                    if (ddr_ack) begin
                        if (ddr_error)
                            fail_transfer(1'b0, 1'b1);
                        else
                            advance_word(ST_HOST_READ_ISSUE);
                    end
                end

                default: begin
                    busy <= 1'b0;
                    transfer_done <= 1'b1;
                    error_command <= 1'b1;
                    state <= ST_IDLE;
                end
            endcase
        end
    end

    // Keep the latched direction explicitly observable to synthesis/debug even
    // though state selection already embodies it.
    wire unused_page_out_latched = page_out_latched;
endmodule
