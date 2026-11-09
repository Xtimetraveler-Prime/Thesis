// M06 preliminary SYNTHESIZABLE one-resident-block transaction controller.
// This is NOT a DDR DMA, not FPGA integrated, and has no neuron datapath.
// One page request in flight. Explicit dirty writeback ACK then demand fill
// ACK, stable request/response handshakes, sticky fault and modeled stalls.
//
// The abstract dma_* interface requires a real transfer adapter to connect
// to four original AXI DMA masters and the selected canonical DDR region.
// Without it this module only establishes the ordered residency state FSM.
module m06_residency_control_fsm #(
    parameter [31:0] MAX_WAIT_CYCLES = 32'd1024
)(
    input  wire        aclk,
    input  wire        aresetn,
    input  wire        req_valid,
    output wire        req_ready,
    input  wire [31:0] req_block,
    input  wire        req_is_write,
    output wire        rsp_valid,
    input  wire        rsp_ready,
    output wire        rsp_error,
    output wire [31:0] rsp_block,
    output wire        dma_valid,
    input  wire        dma_ready,
    output wire        dma_is_writeback,
    output wire [31:0] dma_block,
    input  wire        dma_done,
    input  wire        dma_error,
    output wire        poisoned,
    output wire        resident_valid,
    output wire [31:0] resident_block,
    output wire        resident_dirty,
    output reg  [31:0] accesses,
    output reg  [31:0] hits,
    output reg  [31:0] misses,
    output reg  [31:0] acknowledged_writebacks,
    output reg  [31:0] acknowledged_fills,
    output reg  [31:0] stalled_cycles
);
    localparam [2:0] IDLE=0, ISSUE_WB=1, WAIT_WB=2,
                     ISSUE_FILL=3, WAIT_FILL=4, RESPONSE=5, FAILED=6;
    reg [2:0] state;
    reg tag_valid, tag_dirty;
    reg [31:0] tag_block;
    reg [31:0] pending_block;
    reg pending_write;
    reg [31:0] wait_cycles;
    assign req_ready = aresetn && state == IDLE;
    assign rsp_valid = aresetn && (state == RESPONSE || state == FAILED);
    assign rsp_error = state == FAILED;
    assign rsp_block = pending_block;
    assign dma_valid = aresetn && (state == ISSUE_WB || state == ISSUE_FILL);
    assign dma_is_writeback = (state == ISSUE_WB);
    assign dma_block = dma_is_writeback ? tag_block : pending_block;
    assign poisoned = (state == FAILED);
    assign resident_valid = tag_valid;
    assign resident_dirty = tag_dirty;
    assign resident_block = tag_block;

    always @(posedge aclk) begin
        if (!aresetn) begin
            state <= IDLE;
            tag_valid <= 0;
            tag_dirty <= 0;
            tag_block <= 0;
            pending_block <= 0;
            pending_write <= 0;
            wait_cycles <= 0;
            accesses <= 0;
            hits <= 0;
            misses <= 0;
            acknowledged_writebacks <= 0;
            acknowledged_fills <= 0;
            stalled_cycles <= 0;
        end else begin
            if (state == ISSUE_WB || state == WAIT_WB ||
                state == ISSUE_FILL || state == WAIT_FILL)
                stalled_cycles <= stalled_cycles + 1;
            case (state)
                IDLE: begin
                    wait_cycles <= 0;
                    if (req_valid && req_ready) begin
                        accesses <= accesses+1;
                        pending_block <= req_block;
                        pending_write <= req_is_write;
                        if (tag_valid && tag_block == req_block) begin
                            hits <= hits+1;
                            if (req_is_write)
                                tag_dirty <= 1;
                            state <= RESPONSE;
                        end else begin
                            misses <= misses+1;
                            state <= (tag_valid && tag_dirty)
                                     ? ISSUE_WB : ISSUE_FILL;
                        end
                    end
                end
                ISSUE_WB: begin
                    if (dma_ready && dma_valid) begin
                        wait_cycles <= 0;
                        state <= WAIT_WB;
                    end else if (wait_cycles >= MAX_WAIT_CYCLES)
                        state <= FAILED;
                    else
                        wait_cycles <= wait_cycles+1;
                end
                WAIT_WB: begin
                    if (dma_done) begin
                        if (dma_error) begin
                            // Unknown commit state. Keep the dirty tag.
                            state <= FAILED;
                        end else begin
                            acknowledged_writebacks <= acknowledged_writebacks+1;
                            tag_dirty <= 0;
                            wait_cycles <= 0;
                            state <= ISSUE_FILL;
                        end
                    end else if (wait_cycles >= MAX_WAIT_CYCLES)
                        state <= FAILED;
                    else
                        wait_cycles <= wait_cycles+1;
                end
                ISSUE_FILL: begin
                    if (dma_ready && dma_valid) begin
                        wait_cycles <= 0;
                        state <= WAIT_FILL;
                    end else if (wait_cycles >= MAX_WAIT_CYCLES)
                        state <= FAILED;
                    else
                        wait_cycles <= wait_cycles+1;
                end
                WAIT_FILL: begin
                    if (dma_done) begin
                        if (dma_error)
                            state <= FAILED;
                        else begin
                            acknowledged_fills <= acknowledged_fills+1;
                            tag_valid <= 1;
                            tag_block <= pending_block;
                            tag_dirty <= pending_write;
                            state <= RESPONSE;
                        end
                    end else if (wait_cycles >= MAX_WAIT_CYCLES)
                        state <= FAILED;
                    else
                        wait_cycles <= wait_cycles+1;
                end
                RESPONSE: if (rsp_valid && rsp_ready)
                    state <= IDLE;
                FAILED: begin
                    // Latched quarantine. Only aresetn can clear this.
                    state <= FAILED;
                end
                default: state <= FAILED;
            endcase
        end
    end
endmodule
