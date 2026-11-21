// M08 PAGED PHYSICAL INTEGRATION: first real PL compute-port handshake probe.
// 63 sequential bank READs, one WRITE to reserved word 63, DONE. This proves
// host/compute exclusion and page roundtrip ONLY; NOT a LIF neuron or M06 HLS.
// Original M06 independent neural reference and accepted M32Q .bit unchanged.
// Synchronous one clock, no DDR/DMA/PS driver. Real Icarus functional test
// required before creating a separate native K26 image and hardware evidence.
module m08_page_compute_probe (
    input wire clk,
    input wire resetn,
    input wire dispatch_accept,
    input wire compute_ack,
    input wire [31:0] compute_rdata,
    output wire compute_req,
    output wire compute_write,
    output wire [5:0] compute_word,
    output wire [31:0] compute_wdata,
    output wire [3:0] compute_wstrb,
    output wire compute_done,
    output wire compute_fault,
    output reg [31:0] last_checksum,
    output reg [31:0] completed_runs
);
    localparam [2:0] IDLE=3'd0, RD_REQ=3'd1, RD_WAIT=3'd2,
                     WR_REQ=3'd3, WR_WAIT=3'd4, DONE=3'd5,
                     FAULT=3'd6;
    reg [2:0] state;
    reg [5:0] idx;
    reg [31:0] checksum;
    reg [4:0] watchdog;

    assign compute_req=(state==RD_REQ || state==WR_REQ);
    assign compute_write=(state==WR_REQ);
    assign compute_word=(state==WR_REQ)?6'd63:idx;
    assign compute_wdata=checksum;
    assign compute_wstrb=(state==WR_REQ)?4'hf:4'h0;
    assign compute_done=(state==DONE);
    assign compute_fault=(state==FAULT);

    always @(posedge clk) begin
        if(!resetn) begin
            state<=IDLE;
            idx<=0;
            checksum<=0;
            watchdog<=0;
            last_checksum<=0;
            completed_runs<=0;
        end else begin
            case(state)
                IDLE: if(dispatch_accept) begin
                    idx<=0;
                    checksum<=0;
                    state<=RD_REQ;
                end
                RD_REQ:begin
                    watchdog<=0;
                    state<=RD_WAIT;
                end
                RD_WAIT:begin
                    if(compute_ack) begin
                        checksum<=checksum ^ compute_rdata;
                        if(idx==6'd62)
                            state<=WR_REQ;
                        else begin
                            idx<=idx+6'd1;
                            state<=RD_REQ;
                        end
                    end else if(watchdog==5'd15)
                        state<=FAULT;
                    else watchdog<=watchdog+5'd1;
                end
                WR_REQ:begin
                    watchdog<=0;
                    state<=WR_WAIT;
                end
                WR_WAIT:begin
                    if(compute_ack) begin
                        last_checksum<=checksum;
                        completed_runs<=completed_runs+32'd1;
                        state<=DONE;
                    end else if(watchdog==5'd15)
                        state<=FAULT;
                    else watchdog<=watchdog+5'd1;
                end
                DONE:state<=IDLE;
                FAULT:state<=FAULT;  // hard sticky; owner must reset/reload
                default:state<=FAULT;
            endcase
        end
    end
endmodule
