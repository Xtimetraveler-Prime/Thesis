// M05.11a: 256-bit (32 byte per packet) AXI MM2S to original HLS AXIS.
// Instantiate once for each of neuron(128), synapse(192), external(128).
// Existing HLS kernel stays identical. All 32 bytes are considered valid in
// transport; high unused bits MUST be zero, low bits are original payload.
// Input TLAST MUST assert exactly on last beat; not passed to HLS, whose
// native port has only TDATA/TVALID/TREADY. Zero-length channel is allowed:
// no MM2S descriptor; module starts and ends without sending any beats.
// One clock domain; no real MMIO/DMA/PS driver is implemented here.
// On malformed data, fail closed: do not forward the failing beat to HLS;
// PS must reset/flush ALL outstanding channels before another session.
module m05_ingress_dma_unpad #(
    parameter integer PAYLOAD_WIDTH = 128
) (
    input wire clk,
    input wire rst_n,
    input wire start_valid,
    output wire start_ready,
    input wire [31:0] start_expected_beats,
    input wire [255:0] s_dma_tdata,
    input wire [31:0] s_dma_tkeep,
    input wire s_dma_tlast,
    input wire s_dma_tvalid,
    output wire s_dma_tready,
    output wire [PAYLOAD_WIDTH-1:0] m_hls_tdata,
    output wire m_hls_tvalid,
    input wire m_hls_tready,
    output reg done,
    output reg fault,
    output reg [31:0] accepted_beats
);
    reg active;
    reg [31:0] expected_beats;
    wire last_expected = (accepted_beats == expected_beats - 1'b1);
    wire pad_zero;
    generate
        if (PAYLOAD_WIDTH < 256) begin: gen_padding_check
            assign pad_zero = s_dma_tdata[255:PAYLOAD_WIDTH] == 0;
        end else begin: gen_no_padding
            assign pad_zero = 1'b1;
        end
    endgenerate
    wire legal_beat = pad_zero && s_dma_tkeep == 32'hffffffff &&
                      s_dma_tlast == last_expected;
    assign start_ready = !active && !fault;
    assign m_hls_tdata = s_dma_tdata[PAYLOAD_WIDTH-1:0];
    assign m_hls_tvalid = active && !fault && s_dma_tvalid &&
                          accepted_beats < expected_beats && legal_beat;
    // An invalid input beat is consumed/flagged, not forwarded to HLS.
    assign s_dma_tready = active && !fault &&
        (m_hls_tready || (s_dma_tvalid && !legal_beat)) &&
        accepted_beats < expected_beats;

    always @(posedge clk) begin
        if (!rst_n) begin
            active <= 1'b0;
            done <= 1'b0;
            fault <= 1'b0;
            accepted_beats <= 32'd0;
            expected_beats <= 32'd0;
        end else begin
            if (start_valid && start_ready) begin
                accepted_beats <= 32'd0;
                expected_beats <= start_expected_beats;
                if (start_expected_beats > 32'd262144) begin
                    active <= 1'b0;
                    fault <= 1'b1;
                    done <= 1'b0;
                end else if (start_expected_beats == 0) begin
                    active <= 1'b0;
                    done <= 1'b1;
                end else begin
                    active <= 1'b1;
                    done <= 1'b0;
                end
            end else if (active && s_dma_tvalid &&
                         s_dma_tready) begin
                if (!legal_beat) begin
                    active <= 1'b0;
                    fault <= 1'b1;
                end else begin
                    accepted_beats <= accepted_beats + 1'b1;
                    if (last_expected) begin
                        active <= 1'b0;
                        done <= 1'b1;
                    end
                end
            end
        end
    end
endmodule
