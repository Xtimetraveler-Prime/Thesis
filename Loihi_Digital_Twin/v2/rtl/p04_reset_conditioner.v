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
// Explicit Xilinx signal-interface metadata prevents Vivado module-reference
// polarity inference from misclassifying the two reset outputs and tells block-
// design validation that both reset outputs are synchronous to clk.
module p04_reset_conditioner (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 clk CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_RESET reset:resetn" *)
    input  wire clk,

    input  wire reset_request,

    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 reset RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_HIGH" *)
    output wire reset,

    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 resetn RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
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
