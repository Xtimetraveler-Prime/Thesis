// M05.11b - independent 32-bit AXI4-Lite session command/status slave.
//
// Controls the M05.11a 3 MM2S unpad bridges + trace packetizer, but NOT the
// existing HLS AXI-Lite core. The PS must still configure HLS registers and
// read genuine HLS ap_done/ap_return BEFORE it writes FINISH to this slave.
//
// 32-bit little-endian register map, byte addresses:
//   0x00 COMMAND (write-only): 1=START, 2=FINISH, 4=ACK_SUCCESS.
//   0x04 STATE   (RO): 0=IDLE, 1=RUN, 2=FINALIZING, 3=COMPLETE, 4=FAULT
//   0x08 SID_LO  (RW), 0x0c SID_HI (RW)
//   0x10 EXPECT_TRACE (RW, 1..65536)
//   0x14 NEURON_BEATS (RW, 1..1024)
//   0x18 SYNAPSE_BEATS (RW, 0..4096)
//   0x1c EXTERNAL_BEATS (RW, 0..262144)
//   0x20 FINAL_STATUS (RW, 0..6; only while RUNNING)
//   0x24 OBS_TRACE_ROWS (RO), 0x28 OBS_NEURON_BEATS (RO)
//   0x2c OBS_SYN_BEATS (RO), 0x30 OBS_EXT_BEATS (RO)
//   0x34 FLAGS (RO): bit0 packet_done, bit1 any_fault,
//          bit2 ingress_all_done, bit3 finish_pending, bit4 finish_acked
//   0x38 VERSION (RO) = 0x0005110b
//
// Design contract:
// - AW and W channels are independently buffered; one outstanding response.
// - RDATA/RRESP remain stable until RREADY; BVALID/BRESP until BREADY.
// - WSTRB honored for config, COMMAND requires full strobe and onehot value.
// - START only in IDLE with all 4 bridges ready and valid config; all starts
//   are one-cycle pulses on the same edge (one clock domain).
// - FINISH only in RUN after the PS has observed REAL HLS ap_done and return.
//   It is latched until packetizer finish_ready (may be stalled by trace).
// - Status!=0 or any bridge fault quarantines controller, requires full
//   external PS/DMA+PL reset and verified flush before another START.
// - ACK_SUCCESS is NOT proof of S2MM completion: PS MUST independently
//   certify DMA done/TLAST/length/cache/idle before writing ACK.
// No physical MMIO driver, Vivado AXI interconnect, CDC or DMA is yet proven.
module m05_11_axil_session_controller(
    input wire clk,
    input wire rst_n,
    input wire [7:0] s_axi_awaddr,
    input wire [2:0] s_axi_awprot,
    input wire s_axi_awvalid,
    output wire s_axi_awready,
    input wire [31:0] s_axi_wdata,
    input wire [3:0] s_axi_wstrb,
    input wire s_axi_wvalid,
    output wire s_axi_wready,
    output reg [1:0] s_axi_bresp,
    output reg s_axi_bvalid,
    input wire s_axi_bready,
    input wire [7:0] s_axi_araddr,
    input wire [2:0] s_axi_arprot,
    input wire s_axi_arvalid,
    output wire s_axi_arready,
    output reg [31:0] s_axi_rdata,
    output reg [1:0] s_axi_rresp,
    output reg s_axi_rvalid,
    input wire s_axi_rready,

    input wire bridge_start_ready,
    input wire trace_finish_ready,
    input wire trace_packet_done,
    input wire trace_packet_fault,
    input wire neuron_done,
    input wire synapse_done,
    input wire external_done,
    input wire neuron_fault,
    input wire synapse_fault,
    input wire external_fault,
    input wire [31:0] trace_rows,
    input wire [31:0] neuron_beats,
    input wire [31:0] synapse_beats,
    input wire [31:0] external_beats,

    output reg bridge_start_pulse,
    output wire [63:0] bridge_session_id,
    output wire [31:0] bridge_expected_trace,
    output wire [31:0] bridge_neurons,
    output wire [31:0] bridge_synapses,
    output wire [31:0] bridge_external,
    output wire bridge_finish_valid,
    output wire [31:0] bridge_finish_status,
    output wire [2:0] controller_state
);
    localparam [2:0] ST_IDLE=3'd0, ST_RUN=3'd1,
                     ST_FINAL=3'd2, ST_COMPLETE=3'd3, ST_FAULT=3'd4;
    localparam [1:0] RESP_OKAY=2'b00, RESP_SLVERR=2'b10;
    reg [2:0] state;
    reg [31:0] sid_lo, sid_hi, cfg_trace, cfg_neurons,
               cfg_synapses, cfg_external, cfg_final_status;
    reg [31:0] finish_latched_status;
    reg finish_acked;
    reg aw_staged, w_staged;
    reg [7:0] addr_staged;
    reg [31:0] data_staged;
    reg [3:0] strb_staged;

    wire any_fault = trace_packet_fault || neuron_fault ||
                     synapse_fault || external_fault;
    wire all_ingress_done = neuron_done && synapse_done && external_done;
    wire good_config = cfg_trace >= 1 && cfg_trace <= 32'd65536 &&
                       cfg_neurons >= 1 && cfg_neurons <= 32'd1024 &&
                       cfg_synapses <= 32'd4096 &&
                       cfg_external <= 32'd262144;
    wire [31:0] flags = {27'd0, finish_acked,
        (state == ST_FINAL && !finish_acked),
        all_ingress_done, any_fault, trace_packet_done};

    assign controller_state = state;
    assign bridge_session_id = {sid_hi, sid_lo};
    assign bridge_expected_trace = cfg_trace;
    assign bridge_neurons = cfg_neurons;
    assign bridge_synapses = cfg_synapses;
    assign bridge_external = cfg_external;
    assign bridge_finish_valid = (state == ST_FINAL) && !finish_acked;
    assign bridge_finish_status = finish_latched_status;
    assign s_axi_awready = !aw_staged && !s_axi_bvalid;
    assign s_axi_wready = !w_staged && !s_axi_bvalid;
    assign s_axi_arready = !s_axi_rvalid;

    function [31:0] put_bytes;
        input [31:0] old_value;
        input [31:0] new_value;
        input [3:0] strobes;
        integer ix;
        begin
            put_bytes=old_value;
            for (ix=0;ix<4;ix=ix+1)
                if (strobes[ix])
                    put_bytes[ix*8+:8]=new_value[ix*8+:8];
        end
    endfunction

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            sid_lo <= 0; sid_hi <= 0;
            cfg_trace <= 0; cfg_neurons <= 0;
            cfg_synapses <= 0; cfg_external <= 0;
            cfg_final_status <= 0; finish_latched_status <= 0;
            finish_acked <= 0; bridge_start_pulse <= 0;
            aw_staged <= 0; w_staged <= 0;
            addr_staged <= 0; data_staged <= 0; strb_staged <= 0;
            s_axi_bresp <= RESP_OKAY; s_axi_bvalid <= 0;
            s_axi_rdata <= 0; s_axi_rresp <= RESP_OKAY;
            s_axi_rvalid <= 0;
        end else begin
            bridge_start_pulse <= 1'b0;
            if (any_fault && state != ST_IDLE)
                state <= ST_FAULT;
            else if (state == ST_FINAL && bridge_finish_valid &&
                     trace_finish_ready)
                finish_acked <= 1'b1;
            else if (state == ST_FINAL && finish_acked &&
                     trace_packet_done) begin
                if (finish_latched_status == 0 && all_ingress_done &&
                    trace_rows == cfg_trace && !any_fault)
                    state <= ST_COMPLETE;
                else
                    state <= ST_FAULT;
            end

            if (s_axi_awvalid && s_axi_awready) begin
                aw_staged <= 1;
                addr_staged <= s_axi_awaddr;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                w_staged <= 1;
                data_staged <= s_axi_wdata;
                strb_staged <= s_axi_wstrb;
            end
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 0;
            if (aw_staged && w_staged && !s_axi_bvalid) begin
                aw_staged <= 0;
                w_staged <= 0;
                s_axi_bvalid <= 1;
                s_axi_bresp <= RESP_OKAY;
                if (addr_staged[1:0] != 2'b00)
                    s_axi_bresp <= RESP_SLVERR;
                else begin
                    case(addr_staged)
                        8'h00: begin
                            if (strb_staged != 4'hf)
                                s_axi_bresp <= RESP_SLVERR;
                            else if (data_staged == 32'd1 && state == ST_IDLE &&
                                     bridge_start_ready && good_config) begin
                                bridge_start_pulse <= 1;
                                finish_acked <= 0;
                                state <= ST_RUN;
                            end else if (data_staged == 32'd2 &&
                                         state == ST_RUN &&
                                         cfg_final_status <= 32'd6) begin
                                finish_latched_status <= cfg_final_status;
                                finish_acked <= 0;
                                state <= ST_FINAL;
                            end else if (data_staged == 32'd4 &&
                                         state == ST_COMPLETE && !any_fault &&
                                         all_ingress_done && trace_packet_done) begin
                                state <= ST_IDLE;
                            end else
                                s_axi_bresp <= RESP_SLVERR;
                        end
                        8'h08: if(state == ST_IDLE)
                            sid_lo <= put_bytes(sid_lo,data_staged,strb_staged);
                            else s_axi_bresp <= RESP_SLVERR;
                        8'h0c: if(state == ST_IDLE)
                            sid_hi <= put_bytes(sid_hi,data_staged,strb_staged);
                            else s_axi_bresp <= RESP_SLVERR;
                        8'h10: if(state == ST_IDLE)
                            cfg_trace <= put_bytes(cfg_trace,data_staged,strb_staged);
                            else s_axi_bresp <= RESP_SLVERR;
                        8'h14: if(state == ST_IDLE)
                            cfg_neurons <= put_bytes(cfg_neurons,data_staged,strb_staged);
                            else s_axi_bresp <= RESP_SLVERR;
                        8'h18: if(state == ST_IDLE)
                            cfg_synapses <= put_bytes(cfg_synapses,data_staged,strb_staged);
                            else s_axi_bresp <= RESP_SLVERR;
                        8'h1c: if(state == ST_IDLE)
                            cfg_external <= put_bytes(cfg_external,data_staged,strb_staged);
                            else s_axi_bresp <= RESP_SLVERR;
                        8'h20: if(state == ST_RUN)
                            cfg_final_status <= put_bytes(cfg_final_status,data_staged,strb_staged);
                            else s_axi_bresp <= RESP_SLVERR;
                        default: s_axi_bresp <= RESP_SLVERR;
                    endcase
                end
            end
            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 0;
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1;
                s_axi_rresp <= RESP_OKAY;
                if (s_axi_araddr[1:0] != 2'b00) begin
                    s_axi_rdata <= 32'd0;
                    s_axi_rresp <= RESP_SLVERR;
                end else begin
                    case(s_axi_araddr)
                        8'h00: begin s_axi_rdata <= 0;
                                     s_axi_rresp <= RESP_SLVERR; end
                        8'h04: s_axi_rdata <= {29'd0,state};
                        8'h08: s_axi_rdata <= sid_lo;
                        8'h0c: s_axi_rdata <= sid_hi;
                        8'h10: s_axi_rdata <= cfg_trace;
                        8'h14: s_axi_rdata <= cfg_neurons;
                        8'h18: s_axi_rdata <= cfg_synapses;
                        8'h1c: s_axi_rdata <= cfg_external;
                        8'h20: s_axi_rdata <= cfg_final_status;
                        8'h24: s_axi_rdata <= trace_rows;
                        8'h28: s_axi_rdata <= neuron_beats;
                        8'h2c: s_axi_rdata <= synapse_beats;
                        8'h30: s_axi_rdata <= external_beats;
                        8'h34: s_axi_rdata <= flags;
                        8'h38: s_axi_rdata <= 32'h0005110b;
                        default: begin s_axi_rdata <= 0;
                                       s_axi_rresp <= RESP_SLVERR; end
                    endcase
                end
            end
        end
    end
endmodule
