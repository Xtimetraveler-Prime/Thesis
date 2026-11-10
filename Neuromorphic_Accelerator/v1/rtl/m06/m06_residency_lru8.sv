// M06 synthesis-oriented 8 x 256B option-B state-block LRU residency.
// Metadata-only controller, paired with m06_axi256_multislot_transfer:
// the slot is tracked explicitly for both dirty writeback and fill.
// Original M05 neural/event top is NOT directly connected here.
//
// Dirty victim must be ACKed before its slot can be replaced. A failed
// dirty writeback leaves the old dirty tag; a failed demand fill leaves
// the old tag (possibly clean after acknowledged WB) but poisons service.
// The canonical DDR image may be partially written after AXI errors;
// resetting this controller is NOT an atomic recovery protocol.
module m06_residency_lru8 #(
    parameter integer SLOT_COUNT=8,
    parameter [31:0] MAX_WAIT_CYCLES=32'd1024
)(
    input wire clk,
    input wire resetn,
    input wire req_valid,
    output wire req_ready,
    input wire [31:0] req_block,
    input wire req_is_write,
    output wire rsp_valid,
    input wire rsp_ready,
    output wire rsp_error,
    output wire [31:0] rsp_block,
    output wire [2:0] rsp_slot,
    output wire dma_valid,
    input wire dma_ready,
    output wire dma_is_writeback,
    output wire [31:0] dma_block,
    output wire [2:0] dma_slot,
    input wire dma_done,
    input wire dma_error,
    output wire poisoned,
    output reg [31:0] accesses,
    output reg [31:0] hits,
    output reg [31:0] misses,
    output reg [31:0] evictions,
    output reg [31:0] acknowledged_writebacks,
    output reg [31:0] acknowledged_fills,
    output reg [31:0] stalled_cycles
);
    localparam [2:0] IDLE=0, ISSUE_WB=1, WAIT_WB=2,
                     ISSUE_FILL=3, WAIT_FILL=4, RESPONSE=5, FAILED=6;
    reg [2:0] state;
    reg [SLOT_COUNT-1:0] valid_tag;
    reg [SLOT_COUNT-1:0] dirty_tag;
    reg [31:0] tag [0:SLOT_COUNT-1];
    reg [31:0] recent [0:SLOT_COUNT-1];
    reg [31:0] recency_clock;
    reg [31:0] pending_block;
    reg [2:0] pending_slot;
    reg pending_write;
    reg pending_victim_present;
    reg [31:0] elapsed;

    reg found_hit, found_empty;
    reg [2:0] matched_slot,empty_slot,oldest_slot,chosen_slot;
    reg [31:0] oldest_stamp;
    integer x,reset_index;

    always @* begin
        found_hit=0;
        found_empty=0;
        matched_slot=0;
        empty_slot=0;
        oldest_slot=0;
        oldest_stamp=32'hffffffff;
        for (integer j=0;j<SLOT_COUNT;j=j+1) begin
            if (valid_tag[j] && tag[j]==req_block && !found_hit) begin
                found_hit=1;
                matched_slot=j[2:0];
            end
            if (!valid_tag[j] && !found_empty) begin
                found_empty=1;
                empty_slot=j[2:0];
            end
            if (valid_tag[j] && recent[j]<oldest_stamp) begin
                oldest_stamp=recent[j];
                oldest_slot=j[2:0];
            end
        end
        chosen_slot=found_hit ? matched_slot :
                    found_empty ? empty_slot : oldest_slot;
    end

    assign req_ready = resetn && state==IDLE;
    assign rsp_valid = resetn && (state==RESPONSE || state==FAILED);
    assign rsp_error = state==FAILED;
    assign rsp_block = pending_block;
    assign rsp_slot = pending_slot;
    assign dma_valid = resetn && (state==ISSUE_WB || state==ISSUE_FILL);
    assign dma_is_writeback = state==ISSUE_WB;
    assign dma_slot = pending_slot;
    assign dma_block = dma_is_writeback
                       ? tag[pending_slot] : pending_block;
    assign poisoned = state==FAILED;

    always @(posedge clk) begin
        if (!resetn) begin
            state<=IDLE;
            valid_tag<=0;
            dirty_tag<=0;
            recency_clock<=0;
            pending_block<=0;
            pending_slot<=0;
            pending_write<=0;
            pending_victim_present<=0;
            elapsed<=0;
            accesses<=0;
            hits<=0;
            misses<=0;
            evictions<=0;
            acknowledged_writebacks<=0;
            acknowledged_fills<=0;
            stalled_cycles<=0;
            for(reset_index=0;reset_index<SLOT_COUNT;reset_index=reset_index+1) begin
                tag[reset_index]<=0;
                recent[reset_index]<=0;
            end
        end else begin
            if (state==ISSUE_WB || state==WAIT_WB ||
                state==ISSUE_FILL || state==WAIT_FILL)
                stalled_cycles<=stalled_cycles+1;
            case (state)
                IDLE: begin
                    elapsed<=0;
                    if (req_valid && req_ready) begin
                        accesses<=accesses+1;
                        pending_block<=req_block;
                        pending_slot<=chosen_slot;
                        pending_write<=req_is_write;
                        pending_victim_present<=valid_tag[chosen_slot];
                        if (found_hit) begin
                            hits<=hits+1;
                            if(req_is_write)
                                dirty_tag[chosen_slot]<=1;
                            recent[chosen_slot]<=recency_clock+1;
                            recency_clock<=recency_clock+1;
                            state<=RESPONSE;
                        end else begin
                            misses<=misses+1;
                            state <= (valid_tag[chosen_slot] &&
                                      dirty_tag[chosen_slot])
                                     ? ISSUE_WB : ISSUE_FILL;
                        end
                    end
                end
                ISSUE_WB: begin
                    if(dma_valid && dma_ready) begin
                        elapsed<=0;
                        state<=WAIT_WB;
                    end else if(elapsed>=MAX_WAIT_CYCLES)
                        state<=FAILED;
                    else elapsed<=elapsed+1;
                end
                WAIT_WB: begin
                    if(dma_done) begin
                        if(dma_error) begin
                            // No confirmation the old page is intact.
                            state<=FAILED;
                        end else begin
                            dirty_tag[pending_slot]<=0;
                            acknowledged_writebacks<=acknowledged_writebacks+1;
                            elapsed<=0;
                            state<=ISSUE_FILL;
                        end
                    end else if(elapsed>=MAX_WAIT_CYCLES)
                        state<=FAILED;
                    else elapsed<=elapsed+1;
                end
                ISSUE_FILL: begin
                    if(dma_valid && dma_ready) begin
                        elapsed<=0;
                        state<=WAIT_FILL;
                    end else if(elapsed>=MAX_WAIT_CYCLES)
                        state<=FAILED;
                    else elapsed<=elapsed+1;
                end
                WAIT_FILL: begin
                    if(dma_done) begin
                        if(dma_error) begin
                            // Partially loaded slot MUST NOT be exposed by
                            // the client after sticky FAILED is entered.
                            state<=FAILED;
                        end else begin
                            if(pending_victim_present)
                                evictions<=evictions+1;
                            acknowledged_fills<=acknowledged_fills+1;
                            valid_tag[pending_slot]<=1;
                            dirty_tag[pending_slot]<=pending_write;
                            tag[pending_slot]<=pending_block;
                            recent[pending_slot]<=recency_clock+1;
                            recency_clock<=recency_clock+1;
                            state<=RESPONSE;
                        end
                    end else if(elapsed>=MAX_WAIT_CYCLES)
                        state<=FAILED;
                    else elapsed<=elapsed+1;
                end
                RESPONSE: if(rsp_ready && rsp_valid)
                    state<=IDLE;
                FAILED: state<=FAILED;
                default: state<=FAILED;
            endcase
        end
    end
endmodule
