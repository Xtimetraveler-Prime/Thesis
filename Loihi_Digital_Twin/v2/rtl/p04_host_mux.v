`timescale 1ns/1ps

// Shared VIO/debug host path for the two resource-scaled P04 endpoint fabrics.
// core_select must remain stable from request assertion through completion; the
// physical harness follows that rule.
module p04_host_mux (
    input  wire         req,
    input  wire         write,
    input  wire         core_select,
    input  wire [3:0]   bank,
    input  wire [14:0]  addr,
    input  wire [255:0] wdata,

    output wire         req0,
    output wire         write0,
    output wire [3:0]   bank0,
    output wire [14:0]  addr0,
    output wire [255:0] wdata0,
    input  wire         busy0,
    input  wire         ack0,
    input  wire         rvalid0,
    input  wire         error0,
    input  wire [255:0] rdata0,

    output wire         req1,
    output wire         write1,
    output wire [3:0]   bank1,
    output wire [14:0]  addr1,
    output wire [255:0] wdata1,
    input  wire         busy1,
    input  wire         ack1,
    input  wire         rvalid1,
    input  wire         error1,
    input  wire [255:0] rdata1,

    output wire         busy,
    output wire         ack,
    output wire         rvalid,
    output wire         error,
    output wire [255:0] rdata
);
    assign req0 = req && !core_select;
    assign req1 = req && core_select;
    assign write0 = write;
    assign write1 = write;
    assign bank0 = bank;
    assign bank1 = bank;
    assign addr0 = addr;
    assign addr1 = addr;
    assign wdata0 = wdata;
    assign wdata1 = wdata;

    assign busy = core_select ? busy1 : busy0;
    assign ack = core_select ? ack1 : ack0;
    assign rvalid = core_select ? rvalid1 : rvalid0;
    assign error = core_select ? error1 : error0;
    assign rdata = core_select ? rdata1 : rdata0;
endmodule

module p04_heartbeat (
    input wire clk,
    input wire resetn,
    output reg [31:0] count
);
    always @(posedge clk) begin
        if (!resetn)
            count <= 32'd0;
        else
            count <= count + 32'd1;
    end
endmodule
