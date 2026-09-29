`timescale 1ns/1ps

// Source-controlled reset conditioner for the P04 K26 validation shell.
//
// The VIO reset request is synchronous to the same PL0 clock used by the P04
// fabric. A high request asserts reset on the next clock edge. After the request
// is released, reset remains asserted for 16 additional PL clocks before both
// active-high and active-low reset outputs are released together.
//
// Initializing the release pipeline to all ones also gives the newly programmed
// fabric a deterministic startup reset even when the VIO output initializes low.
module p04_reset_conditioner (
    input  wire clk,
    input  wire reset_request,
    output wire reset,
    output wire resetn
);
    reg [15:0] release_pipe = 16'hFFFF;

    always @(posedge clk) begin
        if (reset_request)
            release_pipe <= 16'hFFFF;
        else
            release_pipe <= {release_pipe[14:0], 1'b0};
    end

    assign reset = |release_pipe;
    assign resetn = ~reset;
endmodule
