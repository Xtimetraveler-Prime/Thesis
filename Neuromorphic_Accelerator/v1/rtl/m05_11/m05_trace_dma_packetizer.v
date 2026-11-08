// M05.11a: 192b HLS TRACE AXIS to 256b packet-oriented S2MM AXIS.
// Synthesizable Verilog separate from verified HLS neural kernel.
// Genuine XSim, full DMA, and physical timing proof are pending.
// 32-byte DMA words: low 192b exact trace, high 64b zero; TKEEP all bytes.
// A final 32-byte footer with TLAST=1 always follows, even for zero traces.
// Footer: [63:0]=0 [95:64]=trace count [127:96]=status
// [191:128]=session ID [255:192]=0x4d30353131454e44 ("M0511END").
// final_valid/status are external CONTROL inputs from a future MMIO bridge
// AFTER PS observes actual HLS ap_done/return. Not auto-exported by HLS.
// One clock domain. Errors require full verified DMA/PL reset and flush.
module m05_trace_dma_packetizer (
    input wire clk,
    input wire rst_n,
    input wire start_valid,
    output wire start_ready,
    input wire [63:0] start_session_id,
    input wire [31:0] start_expected_rows,
    input wire finish_valid,
    output wire finish_ready,
    input wire [31:0] finish_status,
    input wire [191:0] trace_tdata,
    input wire trace_tvalid,
    output wire trace_tready,
    output wire [255:0] dma_tdata,
    output wire [31:0] dma_tkeep,
    output wire dma_tvalid,
    input wire dma_tready,
    output wire dma_tlast,
    output reg done,
    output reg fault,
    output reg [31:0] captured_rows
);
    localparam [63:0] FOOTER_MAGIC = 64'h4d30353131454e44;
    localparam [31:0] FRAME_MISMATCH = 32'hffff0001;
    localparam [31:0] BAD_RETURN = 32'hffff0002;
    localparam [1:0] IDLE = 2'd0, STREAM = 2'd1,
                     FOOTER = 2'd2, FAILED = 2'd3;
    reg [1:0] state;
    reg [63:0] session_id;
    reg [31:0] expected_rows;
    reg [31:0] saved_status;

    assign start_ready = state == IDLE && !fault;
    assign finish_ready = state == STREAM && !trace_tvalid && !fault;
    assign trace_tready = state == STREAM && !fault &&
                          captured_rows < expected_rows && dma_tready;
    assign dma_tvalid = (state == STREAM && !fault &&
                         trace_tvalid && captured_rows < expected_rows) ||
                        (state == FOOTER);
    assign dma_tlast = state == FOOTER;
    assign dma_tkeep = 32'hffffffff;
    assign dma_tdata = (state == FOOTER) ?
        {FOOTER_MAGIC, session_id, saved_status, captured_rows, 64'd0} :
        {64'd0, trace_tdata};

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            done <= 1'b0;
            fault <= 1'b0;
            captured_rows <= 32'd0;
            expected_rows <= 32'd0;
            saved_status <= 32'd0;
            session_id <= 64'd0;
        end else begin
            case (state)
                IDLE: begin
                    if (start_valid && start_ready) begin
                        done <= 1'b0;
                        captured_rows <= 32'd0;
                        expected_rows <= start_expected_rows;
                        session_id <= start_session_id;
                        if (start_expected_rows == 0 ||
                            start_expected_rows > 32'd65536) begin
                            fault <= 1'b1;
                            state <= FAILED;
                        end else
                            state <= STREAM;
                    end
                end
                STREAM: begin
                    // Never overflow the preallocated S2MM buffer.
                    // Overproduction sticks in FAILED until full reset/flush.
                    if (trace_tvalid && captured_rows >= expected_rows) begin
                        fault <= 1'b1;
                        state <= FAILED;
                    end else if (trace_tvalid && trace_tready) begin
                        captured_rows <= captured_rows + 1'b1;
                    end
                    // PS must hold finish until finish_ready; status is read
                    // from actual HLS AXI-Lite control register first.
                    if (finish_valid && finish_ready) begin
                        if (finish_status > 32'd6)
                            saved_status <= BAD_RETURN;
                        else if (finish_status == 0 &&
                                 captured_rows != expected_rows)
                            saved_status <= FRAME_MISMATCH;
                        else
                            saved_status <= finish_status;
                        state <= FOOTER;
                    end
                end
                FOOTER: begin
                    if (dma_tvalid && dma_tready) begin
                        done <= 1'b1;
                        state <= IDLE;
                    end
                end
                FAILED: begin
                    fault <= 1'b1;
                end
                default: begin
                    fault <= 1'b1;
                    state <= FAILED;
                end
            endcase
        end
    end
endmodule
