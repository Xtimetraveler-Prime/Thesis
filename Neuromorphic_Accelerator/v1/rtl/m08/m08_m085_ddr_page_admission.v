`timescale 1ns/1ps
// M08.5 SOURCE-ONLY signed16 page-transaction admission before a FUTURE AXI
// master. Inspired by the v3 P02 DDR range/owner gates, not reused Loihi
// signed24/512KiB RTL. NO DDR, DMA, AXI converter or PS endpoint is connected.
// A high owner_lease_active input is a *simulation signal*, NEVER proof that
// Linux/kernel firmware granted physical DDR ownership. The future connected
// design must drive it only from independently authenticated admission.
// Default empty window rejects EVERY request even when this input is high.
module m08_m085_ddr_page_admission #(
    parameter [63:0] WINDOW_BEGIN = 64'd0,
    parameter [63:0] WINDOW_END   = 64'd0, // exclusive
    parameter integer MAX_WAIT_CYCLES = 32,
    parameter integer LOGICAL_PAGES = 6,
    parameter integer LOGICAL_TICKS = 4,
    parameter integer USE_RUNTIME_WINDOW = 0
)(
    input wire clk,
    input wire resetn,
    input wire owner_lease_active,
    input wire [63:0] runtime_window_begin,
    input wire [63:0] runtime_window_end,
    input wire compute_idle,
    input wire page_bank_idle,
    input wire req,
    input wire req_write,
    input wire [63:0] req_addr,
    input wire [15:0] req_size_bytes,
    input wire [31:0] req_logical_page,
    input wire [31:0] req_tick,
    output reg forward_req,
    output reg forward_write,
    output reg [63:0] forward_addr,
    output reg [15:0] forward_size_bytes,
    output reg [31:0] forward_logical_page,
    output reg [31:0] forward_tick,
    input wire downstream_done,
    input wire downstream_error,
    input wire downstream_rvalid,
    output reg ack,
    output reg error,
    output reg busy,
    output reg poisoned,
    output reg [31:0] completed_page,
    output reg [31:0] completed_tick,
    output reg completed_write,
    output reg [31:0] completed_page_transfers
);
    // 49-bit PL address constraint follows the inherited v3 HP0 adapter
    // physical address-width interface, NOT a verified M08 platform map.
    // M08 must independently validate mapped limits against its eventual
    // routed XSA/PS/driver before the parameters are given nonzero values.
    wire [63:0] effective_begin = USE_RUNTIME_WINDOW != 0 ?
        runtime_window_begin : WINDOW_BEGIN;
    wire [63:0] effective_end = USE_RUNTIME_WINDOW != 0 ?
        runtime_window_end : WINDOW_END;
    wire [64:0] last_exclusive =
        {1'b0, req_addr} + {49'd0, req_size_bytes};
    wire legal_window =
        (effective_end > effective_begin) &&
        (effective_begin[63:49] == 15'd0) &&
        (effective_end[63:49] == 15'd0) &&
        (req_addr[63:49] == 15'd0) &&
        (req_addr[7:0] == 8'd0) &&
        (req_size_bytes == 16'd256) &&
        (LOGICAL_PAGES > 0) && (LOGICAL_TICKS > 0) &&
        (req_logical_page < LOGICAL_PAGES) &&
        (req_tick < LOGICAL_TICKS) &&
        (req_addr >= effective_begin) &&
        (last_exclusive <= {1'b0, effective_end});

    reg armed;
    reg [31:0] wait_count;
    always @(posedge clk) begin
        if (!resetn) begin
            forward_req <= 1'b0;
            forward_write <= 1'b0;
            forward_addr <= 64'd0;
            forward_size_bytes <= 16'd0;
            forward_logical_page <= 32'd0;
            forward_tick <= 32'd0;
            ack <= 1'b0;
            error <= 1'b0;
            busy <= 1'b0;
            poisoned <= 1'b0;
            armed <= 1'b1;
            wait_count <= 32'd0;
            completed_page <= 32'd0;
            completed_tick <= 32'd0;
            completed_write <= 1'b0;
            completed_page_transfers <= 32'd0;
        end else begin
            forward_req <= 1'b0;
            ack <= 1'b0;
            error <= 1'b0;
            if (!req)
                armed <= 1'b1;

            if (poisoned) begin
                // All outputs remain embargoed until an explicit reset.
                busy <= 1'b0;
                poisoned <= 1'b1;
            end else if (busy) begin
                // No two outstanding page transfers; no host/compute overlap.
                if (!owner_lease_active || !compute_idle || !page_bank_idle ||
                        downstream_error || (req && armed)) begin
                    poisoned <= 1'b1;
                    busy <= 1'b0;
                    error <= 1'b1;
                end else if (downstream_done) begin
                    if ((!forward_write && !downstream_rvalid) ||
                        (forward_write && downstream_rvalid)) begin
                        poisoned <= 1'b1;
                        busy <= 1'b0;
                        error <= 1'b1;
                    end else begin
                        busy <= 1'b0;
                        ack <= 1'b1;
                        completed_page <= forward_logical_page;
                        completed_tick <= forward_tick;
                        completed_write <= forward_write;
                        completed_page_transfers <= completed_page_transfers + 32'd1;
                    end
                end else if (wait_count >= (MAX_WAIT_CYCLES-1)) begin
                    poisoned <= 1'b1;
                    busy <= 1'b0;
                    error <= 1'b1;
                end else begin
                    wait_count <= wait_count + 32'd1;
                end
            end else if (downstream_done || downstream_error || downstream_rvalid) begin
                // Orphan responses may not be passed to another page lease.
                poisoned <= 1'b1;
                error <= 1'b1;
            end else if (req && armed) begin
                armed <= 1'b0;
                if (!owner_lease_active || !compute_idle || !page_bank_idle ||
                    !legal_window || MAX_WAIT_CYCLES < 1) begin
                    poisoned <= 1'b1;
                    error <= 1'b1;
                end else begin
                    busy <= 1'b1;
                    forward_req <= 1'b1;
                    forward_write <= req_write;
                    forward_addr <= req_addr;
                    forward_size_bytes <= req_size_bytes;
                    forward_logical_page <= req_logical_page;
                    forward_tick <= req_tick;
                    wait_count <= 32'd0;
                end
            end
        end
    end
endmodule
