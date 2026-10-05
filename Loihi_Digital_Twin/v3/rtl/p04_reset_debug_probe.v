`timescale 1ns/1ps

// Temporary P04 board-bring-up diagnostic.
//
// This counter intentionally has no runtime reset input. Its only purpose is to
// prove that the PS PL0 clock is physically toggling even when proc_sys_reset
// keeps the functional P04 fabric in reset. Xilinx configuration initializes
// the register to the declared value when the bitstream is programmed.
module p04_reset_debug_probe (
    input  wire        clk,
    output reg [31:0]  raw_clock_count = 32'd0
);
    always @(posedge clk)
        raw_clock_count <= raw_clock_count + 32'd1;
endmodule
