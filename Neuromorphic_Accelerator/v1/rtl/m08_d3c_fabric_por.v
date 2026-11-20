// M08 D3.C r2 bounded diagnostic: synchronous startup reset generator.
// Purpose: isolate the JTAG/AXI/BRAM reset from PS pl_resetn0 during raw JTAG
// replacement of a Linux-managed PL design. This is NOT a second clock source.
// Clock remains PS pl_clk0: if PS stops that clock, AXI still cannot run.
// Vivado FPGA configuration GSR initializes registers below deterministically.
module m08_d3c_fabric_por (
    input  wire clk,
    output wire aresetn
);
    reg [7:0] delay_count = 8'h00;
    reg       released    = 1'b0;

    // Assert reset for at least 256 rising edges of the live PL AXI clock.
    // An inactive clock holds reset asserted instead of permitting writes.
    always @(posedge clk) begin
        if (delay_count != 8'hFF) begin
            delay_count <= delay_count + 8'd1;
            released    <= 1'b0;
        end else begin
            released    <= 1'b1;
        end
    end

    assign aresetn = released;
endmodule
