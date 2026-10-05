`timescale 1ns/1ps

// P02.3a arbitration for P05 context-memory Port B.
//
// While page_active is asserted, the page walker owns the existing P05
// host/debug transaction port.  External debug access is back-pressured.
// Compute ownership remains enforced inside p05_context_memory_fabric itself:
// that fabric rejects host-side accesses while compute_busy is asserted.
module p02_page_host_arbiter (
    input  wire         page_active,

    input  wire         debug_req,
    input  wire         debug_write,
    input  wire [1:0]   debug_context_slot,
    input  wire [3:0]   debug_bank,
    input  wire [14:0]  debug_addr,
    input  wire [255:0] debug_wdata,
    output wire         debug_busy,
    output wire         debug_ack,
    output wire         debug_rvalid,
    output wire         debug_error,
    output wire [255:0] debug_rdata,

    input  wire         page_req,
    input  wire         page_write,
    input  wire [1:0]   page_context_slot,
    input  wire [3:0]   page_bank,
    input  wire [14:0]  page_addr,
    input  wire [255:0] page_wdata,
    output wire         page_busy,
    output wire         page_ack,
    output wire         page_rvalid,
    output wire         page_error,
    output wire [255:0] page_rdata,

    output wire         fabric_req,
    output wire         fabric_write,
    output wire [1:0]   fabric_context_slot,
    output wire [3:0]   fabric_bank,
    output wire [14:0]  fabric_addr,
    output wire [255:0] fabric_wdata,
    input  wire         fabric_busy,
    input  wire         fabric_ack,
    input  wire         fabric_rvalid,
    input  wire         fabric_error,
    input  wire [255:0] fabric_rdata
);
    assign fabric_req = page_active ? page_req : debug_req;
    assign fabric_write = page_active ? page_write : debug_write;
    assign fabric_context_slot =
        page_active ? page_context_slot : debug_context_slot;
    assign fabric_bank = page_active ? page_bank : debug_bank;
    assign fabric_addr = page_active ? page_addr : debug_addr;
    assign fabric_wdata = page_active ? page_wdata : debug_wdata;

    assign debug_busy = page_active ? 1'b1 : fabric_busy;
    assign debug_ack = page_active ? 1'b0 : fabric_ack;
    assign debug_rvalid = page_active ? 1'b0 : fabric_rvalid;
    assign debug_error = page_active ? 1'b0 : fabric_error;
    assign debug_rdata = page_active ? 256'd0 : fabric_rdata;

    assign page_busy = fabric_busy;
    assign page_ack = page_active ? fabric_ack : 1'b0;
    assign page_rvalid = page_active ? fabric_rvalid : 1'b0;
    assign page_error = page_active ? fabric_error : 1'b0;
    assign page_rdata = page_active ? fabric_rdata : 256'd0;
endmodule
