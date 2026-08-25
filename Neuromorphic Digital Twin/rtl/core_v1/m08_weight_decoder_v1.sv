`timescale 1ns/1ps

// Reconstruct the frozen M08.5 effective integer weight from one packed
// synapse word plus its referenced shared 16-bit weight-format word.
module m08_weight_decoder_v1 (
    input  logic [15:0] format_word,
    input  logic [31:0] synapse_word,

    output logic               valid,
    output logic [7:0]         fault_code,
    output logic [15:0]        target_neuron,
    output logic [3:0]         format_index,
    output logic signed [8:0]  requested_mantissa,
    output logic signed [31:0] effective_weight
);

    localparam logic [7:0] FAULT_NONE              = 8'h00;
    localparam logic [7:0] FAULT_FORMAT_RESERVED   = 8'h01;
    localparam logic [7:0] FAULT_SYNAPSE_RESERVED  = 8'h02;
    localparam logic [7:0] FAULT_NUM_WEIGHT_BITS   = 8'h03;
    localparam logic [7:0] FAULT_SIGN_MODE         = 8'h04;
    localparam logic [7:0] FAULT_MANTISSA_SIGN     = 8'h05;

    localparam integer signed WEIGHT_LIMIT = 2097088;

    integer signed mantissa_i;
    integer signed magnitude_i;
    integer signed quantized_i;
    integer signed exponent_i;
    integer signed aligned_units_i;
    integer signed aligned_weight_i;
    integer signed clipped_weight_i;
    integer signed precision_shift_i;
    integer signed num_weight_bits_i;
    integer signed sign_mode_i;

    always_comb begin
        valid = 1'b0;
        fault_code = FAULT_NONE;
        target_neuron = synapse_word[28:13];
        format_index = synapse_word[12:9];
        requested_mantissa = $signed(synapse_word[8:0]);
        effective_weight = 32'sd0;

        mantissa_i = $signed(synapse_word[8:0]);
        exponent_i = $signed(format_word[3:0]);
        num_weight_bits_i = format_word[7:4];
        sign_mode_i = format_word[9:8];
        magnitude_i = 0;
        quantized_i = 0;
        aligned_units_i = 0;
        aligned_weight_i = 0;
        clipped_weight_i = 0;
        precision_shift_i = 0;

        if (format_word[15:10] != 6'd0) begin
            fault_code = FAULT_FORMAT_RESERVED;
        end else if (synapse_word[31:29] != 3'd0) begin
            fault_code = FAULT_SYNAPSE_RESERVED;
        end else if (num_weight_bits_i < 0 || num_weight_bits_i > 8) begin
            fault_code = FAULT_NUM_WEIGHT_BITS;
        end else if (sign_mode_i == 3) begin
            fault_code = FAULT_SIGN_MODE;
        end else if (
            (sign_mode_i == 1 && (mantissa_i < 0 || mantissa_i > 255)) ||
            (sign_mode_i == 2 && (mantissa_i < -256 || mantissa_i > 0)) ||
            (sign_mode_i == 0 && (mantissa_i < -256 || mantissa_i > 254))
        ) begin
            fault_code = FAULT_MANTISSA_SIGN;
        end else begin
            // M08 precision shift:
            //   non-mixed: 8 - num_weight_bits
            //   mixed:     8 - num_weight_bits + 1
            precision_shift_i = 8 - num_weight_bits_i;
            if (sign_mode_i == 0)
                precision_shift_i = precision_shift_i + 1;

            magnitude_i = (mantissa_i < 0) ? -mantissa_i : mantissa_i;
            quantized_i = (magnitude_i >> precision_shift_i) << precision_shift_i;
            if (mantissa_i < 0)
                quantized_i = -quantized_i;

            // Arithmetic right shift implements Python floor division for
            // negative powers-of-two, matching the frozen M08 encoder.
            if (exponent_i >= 0)
                aligned_units_i = quantized_i <<< exponent_i;
            else
                aligned_units_i = quantized_i >>> (-exponent_i);

            aligned_weight_i = aligned_units_i <<< 6;
            if (aligned_weight_i > WEIGHT_LIMIT)
                clipped_weight_i = WEIGHT_LIMIT;
            else if (aligned_weight_i < -WEIGHT_LIMIT)
                clipped_weight_i = -WEIGHT_LIMIT;
            else
                clipped_weight_i = aligned_weight_i;

            effective_weight = clipped_weight_i;
            valid = 1'b1;
        end
    end

endmodule
