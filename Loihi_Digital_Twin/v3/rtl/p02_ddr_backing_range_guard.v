`timescale 1ns/1ps

// P02.3b2 fixed DDR backing-window guard.
//
// The page walker is the only intended requester.  This guard adds a final
// transport-side containment check before requests reach the AXI burst adapter.
// The accepted v3 backing region is 64 MiB beginning at 0x4000_0000:
//
//   [0x4000_0000, 0x4400_0000)
//
// This covers 128 fixed 512 KiB logical-core records exactly.
module p02_ddr_backing_range_guard #(
    parameter [63:0] BACKING_BASE = 64'h0000_0000_4000_0000,
    parameter [63:0] BACKING_BYTES = 64'h0000_0000_0400_0000
) (
    input  wire         req,
    input  wire         req_write,
    input  wire [63:0]  req_addr,
    input  wire [5:0]   req_size_bytes,
    input  wire [255:0] req_wdata,

    output wire         downstream_req,
    output wire         downstream_write,
    output wire [63:0]  downstream_addr,
    output wire [5:0]   downstream_size_bytes,
    output wire [255:0] downstream_wdata,
    input  wire         downstream_busy,
    input  wire         downstream_ack,
    input  wire         downstream_rvalid,
    input  wire         downstream_error,
    input  wire [255:0] downstream_rdata,

    output wire         busy,
    output wire         ack,
    output wire         rvalid,
    output wire         error,
    output wire [255:0] rdata,
    output wire         range_error
);
    wire [64:0] request_end =
        {1'b0, req_addr} + {59'd0, req_size_bytes};
    wire [64:0] allowed_end =
        {1'b0, BACKING_BASE} + {1'b0, BACKING_BYTES};

    wire range_valid =
        (req_size_bytes != 0) &&
        (req_addr >= BACKING_BASE) &&
        (request_end <= allowed_end);

    assign downstream_req = req && range_valid;
    assign downstream_write = req_write;
    assign downstream_addr = req_addr;
    assign downstream_size_bytes = req_size_bytes;
    assign downstream_wdata = req_wdata;

    assign busy = range_valid ? downstream_busy : 1'b0;
    assign ack = range_valid ? downstream_ack : req;
    assign rvalid = range_valid ? downstream_rvalid : 1'b0;
    assign error = range_valid ? downstream_error : req;
    assign rdata = range_valid ? downstream_rdata : 256'd0;
    assign range_error = req && !range_valid;
endmodule
