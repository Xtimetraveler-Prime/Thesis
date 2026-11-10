// M06 synthesizable FIRST block mover for a single 256-byte resident slot.
// Original mem_sc S00 READ ONLY (256b) and S03 WRITE ONLY (256b).
// Each canonical block transfers as eight independent 256-bit AXI4
// single-beat transactions (ARLEN/AWLEN=0; SIZE=5; INCR); these stay
// within 4KiB. Connect this module to the existing residency FSM's
// dma_* request/ack. It is NOT real DDR or a Linux memory allocator.
//
// In a fill error, the resident slot's bytes may be PARTIALLY REPLACED;
// the residency FSM must POISON/quarantine the slot. In a write response
// error, canonical memory may be PARTIALLY MODIFIED; never retry silently.
// Local edit port is valid only when the mover is idle and caller has
// admitted the block via the residency FSM. This module doesn't implement
// neuron-update semantics itself.
module m06_axi256_block_transfer #(
    parameter integer MAX_BLOCKS = 32,
    parameter [31:0] MAX_WAIT_CYCLES = 32'd1024
)(
    input wire clk,
    input wire resetn,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire cmd_is_writeback,
    input wire [31:0] cmd_block,
    output reg cmd_done,
    output reg cmd_error,
    output wire busy,
    input wire [2:0] client_word_index,
    output wire [255:0] client_word_data,
    input wire client_write_enable,
    input wire [255:0] client_write_data,
    input wire [31:0] client_write_strobe,
    // Original mem_sc S00 read-only
    output wire [31:0] s00_araddr,
    output wire [7:0] s00_arlen,
    output wire [2:0] s00_arsize,
    output wire [1:0] s00_arburst,
    output wire s00_arlock,
    output wire [3:0] s00_arcache,
    output wire [2:0] s00_arprot,
    output wire [3:0] s00_arqos,
    output wire s00_arvalid,
    input wire s00_arready,
    input wire [255:0] s00_rdata,
    input wire [1:0] s00_rresp,
    input wire s00_rlast,
    input wire s00_rvalid,
    output wire s00_rready,
    // Original mem_sc S03 write-only
    output wire [31:0] s03_awaddr,
    output wire [7:0] s03_awlen,
    output wire [2:0] s03_awsize,
    output wire [1:0] s03_awburst,
    output wire s03_awlock,
    output wire [3:0] s03_awcache,
    output wire [2:0] s03_awprot,
    output wire [3:0] s03_awqos,
    output wire s03_awvalid,
    input wire s03_awready,
    output wire [255:0] s03_wdata,
    output wire [31:0] s03_wstrb,
    output wire s03_wlast,
    output wire s03_wvalid,
    input wire s03_wready,
    input wire [1:0] s03_bresp,
    input wire s03_bvalid,
    output wire s03_bready,
    output reg [31:0] accepted_ar,
    output reg [31:0] accepted_r,
    output reg [31:0] accepted_aw,
    output reg [31:0] accepted_w,
    output reg [31:0] accepted_b,
    output reg [31:0] wait_stalls
);
    localparam [2:0] IDLE=0, READ_ADDR=1, READ_DATA=2,
                     WRITE_ADDR=3, WRITE_DATA=4, WRITE_RESP=5,
                     ACK=6;
    reg [2:0] state;
    reg [255:0] slot [0:7];
    reg [31:0] block;
    reg [2:0] index;
    reg [31:0] wait_cycles;
    reg transfer_failed;
    reg [31:0] accepted_word_address;
    integer byte_lane;

    assign busy = state != IDLE;
    assign cmd_ready = resetn && state == IDLE;
    assign client_word_data = slot[client_word_index];
    assign s00_araddr = accepted_word_address;
    assign s00_arlen = 8'd0;
    assign s00_arsize = 3'd5;
    assign s00_arburst = 2'b01;
    assign s00_arlock = 1'b0;
    assign s00_arcache = 4'b0011;
    assign s00_arprot = 3'b000;
    assign s00_arqos = 4'b0000;
    assign s00_arvalid = resetn && state == READ_ADDR;
    assign s00_rready = resetn && state == READ_DATA;
    assign s03_awaddr = accepted_word_address;
    assign s03_awlen = 8'd0;
    assign s03_awsize = 3'd5;
    assign s03_awburst = 2'b01;
    assign s03_awlock = 1'b0;
    assign s03_awcache = 4'b0011;
    assign s03_awprot = 3'b000;
    assign s03_awqos = 4'b0000;
    assign s03_awvalid = resetn && state == WRITE_ADDR;
    assign s03_wdata = slot[index];
    assign s03_wstrb = 32'hffffffff;
    assign s03_wlast = 1'b1;
    assign s03_wvalid = resetn && state == WRITE_DATA;
    assign s03_bready = resetn && state == WRITE_RESP;

    always @(posedge clk) begin
        if (!resetn) begin
            state <= IDLE;
            cmd_done <= 0;
            cmd_error <= 0;
            transfer_failed <= 0;
            block <= 0;
            index <= 0;
            wait_cycles <= 0;
            accepted_word_address <= 0;
            accepted_ar <= 0;
            accepted_r <= 0;
            accepted_aw <= 0;
            accepted_w <= 0;
            accepted_b <= 0;
            wait_stalls <= 0;
        end else begin
            cmd_done <= 0;
            cmd_error <= 0;
            if (client_write_enable && state == IDLE && !cmd_valid) begin
                for (byte_lane=0; byte_lane<32; byte_lane=byte_lane+1)
                    if (client_write_strobe[byte_lane])
                        slot[client_word_index][8*byte_lane +: 8] <=
                            client_write_data[8*byte_lane +: 8];
            end
            if (state != IDLE && state != ACK)
                wait_stalls <= wait_stalls+1;
            case (state)
                IDLE: begin
                    wait_cycles <= 0;
                    transfer_failed <= 0;
                    if (cmd_valid && cmd_ready) begin
                        block <= cmd_block;
                        index <= 0;
                        accepted_word_address <= cmd_block << 8;
                        if (cmd_block >= MAX_BLOCKS) begin
                            transfer_failed <= 1;
                            state <= ACK;
                        end else begin
                            state <= cmd_is_writeback ? WRITE_ADDR : READ_ADDR;
                        end
                    end
                end
                READ_ADDR: begin
                    if (s00_arready && s00_arvalid) begin
                        accepted_ar <= accepted_ar+1;
                        wait_cycles <= 0;
                        state <= READ_DATA;
                    end else if (wait_cycles >= MAX_WAIT_CYCLES) begin
                        transfer_failed <= 1;
                        state <= ACK;
                    end else wait_cycles <= wait_cycles+1;
                end
                READ_DATA: begin
                    if (s00_rvalid && s00_rready) begin
                        accepted_r <= accepted_r+1;
                        wait_cycles <= 0;
                        if (s00_rresp != 2'b00 || s00_rlast != 1'b1) begin
                            transfer_failed <= 1;
                            state <= ACK;
                        end else begin
                            slot[index] <= s00_rdata;
                            if (index == 7)
                                state <= ACK;
                            else begin
                                index <= index+1;
                                accepted_word_address <=
                                    accepted_word_address+32;
                                state <= READ_ADDR;
                            end
                        end
                    end else if (wait_cycles >= MAX_WAIT_CYCLES) begin
                        transfer_failed <= 1;
                        state <= ACK;
                    end else wait_cycles <= wait_cycles+1;
                end
                WRITE_ADDR: begin
                    if (s03_awready && s03_awvalid) begin
                        accepted_aw <= accepted_aw+1;
                        wait_cycles <= 0;
                        state <= WRITE_DATA;
                    end else if (wait_cycles >= MAX_WAIT_CYCLES) begin
                        transfer_failed <= 1;
                        state <= ACK;
                    end else wait_cycles <= wait_cycles+1;
                end
                WRITE_DATA: begin
                    if (s03_wready && s03_wvalid) begin
                        accepted_w <= accepted_w+1;
                        wait_cycles <= 0;
                        state <= WRITE_RESP;
                    end else if (wait_cycles >= MAX_WAIT_CYCLES) begin
                        transfer_failed <= 1;
                        state <= ACK;
                    end else wait_cycles <= wait_cycles+1;
                end
                WRITE_RESP: begin
                    if (s03_bvalid && s03_bready) begin
                        accepted_b <= accepted_b+1;
                        wait_cycles <= 0;
                        if (s03_bresp != 2'b00) begin
                            transfer_failed <= 1;
                            state <= ACK;
                        end else if (index == 7)
                            state <= ACK;
                        else begin
                            index <= index+1;
                            accepted_word_address <=
                                accepted_word_address+32;
                            state <= WRITE_ADDR;
                        end
                    end else if (wait_cycles >= MAX_WAIT_CYCLES) begin
                        transfer_failed <= 1;
                        state <= ACK;
                    end else wait_cycles <= wait_cycles+1;
                end
                ACK: begin
                    cmd_done <= 1;
                    cmd_error <= transfer_failed;
                    state <= IDLE;
                end
                default: begin
                    transfer_failed <= 1;
                    state <= ACK;
                end
            endcase
        end
    end
endmodule
