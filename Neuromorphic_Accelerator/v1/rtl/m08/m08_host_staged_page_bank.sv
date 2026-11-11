// M08.2b.1 first-party synthesizable ONE-slot signed16 state-page staging.
// A page is 16 M06 signed16 neurons x 16 bytes/record = 256 bytes.
// Host supplies one 32-bit word at a time (NOT AXI-Lite yet).
// A separate PS AXI-Lite adapter and real HLS engine are future gates.
// Reuses Loihi P08 host/compute EXCLUSION, not Loihi signed24 memory layout.
// The host is responsible for full readback comparison before commit and
// durable off-page save before save_done: assertions are NOT physical proof.
// No kernel DMA, DDR access, VIO/JTAG, bitstream or neural inference here.
module m08_host_staged_page_bank (
    input  wire        clk,
    input  wire        resetn,
    input  wire        host_begin,
    input  wire [31:0] host_begin_logical,
    input  wire        host_req,
    input  wire        host_write,
    input  wire [5:0]  host_word,
    input  wire [31:0] host_wdata,
    input  wire [3:0]  host_wstrb,
    input  wire        host_commit,
    input  wire        host_readback_verified,
    input  wire        host_save_done,
    output reg         host_ack,
    output reg         host_error,
    output reg  [31:0] host_rdata,
    input  wire        dispatch_req,
    input  wire [31:0] dispatch_logical,
    output reg         dispatch_accept,
    input  wire        compute_req,
    input  wire        compute_write,
    input  wire [5:0]  compute_word,
    input  wire [31:0] compute_wdata,
    input  wire [3:0]  compute_wstrb,
    output reg         compute_ack,
    output reg  [31:0] compute_rdata,
    input  wire        compute_done,
    input  wire        compute_fault,
    input  wire        fault_in,
    output wire [2:0]  phase,
    output wire        poisoned,
    output wire        host_busy,
    output wire        compute_busy,
    output wire        page_valid,
    output wire        page_dirty,
    output reg  [31:0] page_logical,
    output wire [8:0]  loaded_byte_count
);
    localparam [2:0] EMPTY=0, LOADING=1, READY=2,
                     RUNNING=3, DIRTY=4, FAILED=5;
    reg [2:0] state;
    reg [31:0] words [0:63];
    reg [255:0] loaded_bytes;
    reg host_armed, compute_armed;
    integer i;

    assign phase=state;
    assign poisoned=(state==FAILED);
    assign host_busy=(state==LOADING) || host_req || host_begin ||
                     host_commit || host_save_done || host_ack;
    assign compute_busy=(state==RUNNING);
    assign page_valid=(state==READY || state==RUNNING || state==DIRTY);
    assign page_dirty=(state==DIRTY);
    // 9 bits represent 0..256 fully initialized bytes without overflow.
    reg [8:0] loaded_count;
    assign loaded_byte_count=loaded_count;
    // Completeness is tracked per BYTE, not per 32-bit word. New strobe
    // bits are counted once; replaying a beat cannot inflate the count.
    reg [8:0] new_byte_count;
    integer k;
    always @* begin
        new_byte_count = 9'd0;
        for (k=0;k<4;k=k+1)
            if (host_wstrb[k] && !loaded_bytes[host_word*4+k])
                new_byte_count = new_byte_count + 9'd1;
    end

    always @(posedge clk) begin
        if (!resetn) begin
            state <= EMPTY;
            loaded_bytes <= 256'b0;
            loaded_count <= 9'd0;
            page_logical <= 32'd0;
            host_ack <= 1'b0;
            host_error <= 1'b0;
            host_rdata <= 32'd0;
            compute_ack <= 1'b0;
            compute_rdata <= 32'd0;
            dispatch_accept <= 1'b0;
            host_armed <= 1'b1;
            compute_armed <= 1'b1;
        end else begin
            host_ack <= 1'b0;
            host_error <= 1'b0;
            compute_ack <= 1'b0;
            dispatch_accept <= 1'b0;
            if (!host_req) host_armed <= 1'b1;
            if (!compute_req) compute_armed <= 1'b1;

            if (state==FAILED) begin
                // Sticky fail-closed until reset and complete NEW page fill.
                state <= FAILED;
            end else if (fault_in || compute_fault) begin
                state <= FAILED;
                host_error <= 1'b1;
            end else if ((host_req && host_armed &&
                          (host_begin || host_commit || host_save_done ||
                           dispatch_req || compute_req || compute_done)) ||
                         (compute_req && compute_armed &&
                          (compute_done || dispatch_req)) ||
                         (host_begin && (host_commit || host_save_done ||
                                         dispatch_req || compute_req)) ||
                         (host_commit && (host_save_done || dispatch_req ||
                                          compute_req)) ||
                         (dispatch_req && (host_save_done || compute_done))) begin
                // No ambiguous simultaneous state-changing operations.
                state <= FAILED;
                host_error <= 1'b1;
            end else begin
                case (state)
                    EMPTY: begin
                        if (host_begin && !host_req) begin
                            page_logical <= host_begin_logical;
                            loaded_bytes <= 256'b0;
                            loaded_count <= 9'd0;
                            state <= LOADING;
                        end else if (host_req || host_commit ||
                                     host_save_done || dispatch_req ||
                                     compute_req || compute_done) begin
                            state <= FAILED;
                            host_error <= 1'b1;
                        end
                    end
                    LOADING: begin
                        if (host_req && host_armed) begin
                            host_armed <= 1'b0;
                            if (host_write && host_wstrb!=4'b0) begin
                                for (i=0;i<4;i=i+1) begin
                                    if (host_wstrb[i]) begin
                                        words[host_word][i*8 +: 8] <=
                                            host_wdata[i*8 +: 8];
                                        loaded_bytes[host_word*4+i] <= 1'b1;
                                    end
                                end
                                loaded_count <= loaded_count + new_byte_count;
                                host_ack <= 1'b1;
                            end else if (!host_write &&
                                         (&loaded_bytes[host_word*4 +: 4])) begin
                                host_rdata <= words[host_word];
                                host_ack <= 1'b1;
                            end else begin
                                state <= FAILED;
                                host_error <= 1'b1;
                            end
                        end else if (host_commit && !host_ack &&
                                     !host_req) begin
                            if ((&loaded_bytes) && host_readback_verified) begin
                                state <= READY;
                            end else begin
                                state <= FAILED;
                                host_error <= 1'b1;
                            end
                        end else if (host_begin || host_save_done ||
                                     dispatch_req || compute_req ||
                                     compute_done) begin
                            state <= FAILED;
                            host_error <= 1'b1;
                        end
                    end
                    READY: begin
                        if (host_req && host_armed) begin
                            host_armed <= 1'b0;
                            if (!host_write) begin
                                host_rdata <= words[host_word];
                                host_ack <= 1'b1;
                            end else begin
                                state <= FAILED;
                                host_error <= 1'b1;
                            end
                        end else if (host_begin && !host_ack && !host_req) begin
                            // Clean page may be replaced; no outstanding
                            // compute or dirty update can be discarded.
                            page_logical <= host_begin_logical;
                            loaded_bytes <= 256'b0;
                            loaded_count <= 9'd0;
                            state <= LOADING;
                        end else if (dispatch_req && !host_busy) begin
                            if (dispatch_logical==page_logical) begin
                                state <= RUNNING;
                                dispatch_accept <= 1'b1;
                            end else begin
                                state <= FAILED;
                                host_error <= 1'b1;
                            end
                        end else if (host_commit || host_save_done ||
                                     compute_req || compute_done) begin
                            state <= FAILED;
                            host_error <= 1'b1;
                        end
                    end
                    RUNNING: begin
                        if (host_req || host_begin || host_commit ||
                            host_save_done || dispatch_req) begin
                            // Forbidden host access while compute owns state.
                            state <= FAILED;
                            host_error <= 1'b1;
                        end else if (compute_req && compute_armed) begin
                            compute_armed <= 1'b0;
                            if (compute_write && compute_wstrb==4'b0) begin
                                state <= FAILED;
                                host_error <= 1'b1;
                            end else begin
                                if (compute_write)
                                    for (i=0;i<4;i=i+1)
                                        if (compute_wstrb[i])
                                            words[compute_word][8*i +: 8]
                                                <= compute_wdata[8*i +: 8];
                                else compute_rdata <= words[compute_word];
                                compute_ack <= 1'b1;
                            end
                        end else if (compute_done && !compute_ack &&
                                     !compute_req) begin
                            state <= DIRTY;
                        end
                    end
                    DIRTY: begin
                        if (host_req && host_armed) begin
                            host_armed <= 1'b0;
                            if (!host_write) begin
                                host_rdata <= words[host_word];
                                host_ack <= 1'b1;
                            end else begin
                                state <= FAILED;
                                host_error <= 1'b1;
                            end
                        end else if (host_save_done && !host_ack &&
                                     !host_req) begin
                            // Software asserts durable, checked save.
                            state <= READY;
                        end else if (host_begin || host_commit ||
                                     dispatch_req || compute_req ||
                                     compute_done) begin
                            state <= FAILED;
                            host_error <= 1'b1;
                        end
                    end
                    default: state <= FAILED;
                endcase
            end
        end
    end
endmodule
