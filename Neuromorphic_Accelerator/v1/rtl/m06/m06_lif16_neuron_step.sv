// M06 independent signed16 arithmetic lane for byte-packed canonical state.
// Implements M02 rev1's per-tick arithmetic ONLY: not an event router,
// M05 accepted HLS top or complete neuromorphic accelerator integration.
// This combinational block is synthesis-oriented; dynamic integer division
// has NOT been HLS/synthesis measured for timing/area.
module m06_lif16_neuron_step (
    input  wire signed [15:0] previous_voltage,
    input  wire signed [15:0] bias,
    input  wire signed [15:0] threshold,
    input  wire signed [15:0] reset_voltage,
    input  wire signed [31:0] summed_current,
    input  wire [31:0] decay_num,
    input  wire [31:0] decay_den,
    output reg  signed [15:0] next_voltage,
    output reg                spike,
    output wire               invalid_params
);
    // M02 dense oracle: trunc_zero(v * num / den), add bias+current,
    // saturate signed16, inclusive threshold comparison, then reset.
    wire signed [63:0] scaled = $signed(previous_voltage) *
                                $signed({1'b0,decay_num});
    wire signed [63:0] divider = $signed({1'b0,decay_den});
    wire signed [63:0] leaked =
        (decay_den != 0) ? scaled / divider : 64'sd0;
    wire signed [63:0] candidate = leaked +
                                   $signed(bias) + $signed(summed_current);
    wire signed [15:0] saturated =
        (candidate > 64'sd32767) ? 16'sd32767 :
        (candidate < -64'sd32768) ? -16'sd32768 :
        candidate[15:0];
    assign invalid_params = (decay_den == 0) || (decay_num > decay_den) ||
                            (threshold <= 0) || (reset_voltage >= threshold);
    always @* begin
        next_voltage = previous_voltage;
        spike = 0;
        if (!invalid_params) begin
            if (saturated >= threshold) begin
                next_voltage = reset_voltage;
                spike = 1;
            end else begin
                next_voltage = saturated;
                spike = 0;
            end
        end
    end
endmodule
