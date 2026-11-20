// M08 D3.D.2A: four independent hardware LIF neurons, four logical ticks.
// PC supplies each neuron's signed16 parameters and 4 signed32 input currents.
// Hardware performs all 16 state transitions; host cannot write any results.
// This phase has NO SYNAPTIC ROUTING, recurrent delay, DDR, or M06 HLS integration.
// Exact M02 rev1 supported decay {0, 1/2, 1}, signed truncation toward zero,
// ONE final signed16 saturation, inclusive threshold, spike and reset.
// ABI (32-bit words): magic 000, version 004, status 008, nonce 00C,
// decay 010, start 014, completed nonce 018, completed run count 01C.
// Neuron n inputs at 040 + 020*n: initial,bias,threshold,reset,4 currents.
// Neuron n outputs at 100 + 020*n: four voltages and four-bit spike mask.
// Outputs gated until DONE; four neurons updated once each tick, tick-major.
// AXI4-Lite independent AW/W channels; B and R remain stable under backpressure.
module m08_d3d2a_four_lif_axil (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 aclk CLK", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME aclk, ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET aresetn" *)
    input  wire        aclk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 aresetn RST", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME aresetn, POLARITY ACTIVE_LOW" *)
    input  wire        aresetn,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 12, HAS_BURST 0, HAS_LOCK 0, HAS_CACHE 0, HAS_PROT 1" *)
    input wire [11:0] s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWPROT" *)
    input wire [2:0] s_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
    input wire s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
    output wire s_axi_awready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
    input wire [31:0] s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
    input wire [3:0] s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
    input wire s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
    output wire s_axi_wready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
    output reg [1:0] s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output reg s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
    input wire s_axi_bready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
    input wire [11:0] s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARPROT" *)
    input wire [2:0] s_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
    input wire s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
    output wire s_axi_arready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
    output reg [31:0] s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output reg [1:0] s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output reg s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input wire s_axi_rready
);
    localparam [1:0] OKAY=2'b00, SLVERR=2'b10, DECERR=2'b11;
    localparam [31:0] MAGIC=32'h4D344C46; // "M4LF"
    localparam [31:0] VERSION=32'h00020000;
    reg aw_pending, w_pending;
    reg [11:0] aw_addr_q;
    reg [31:0] w_data_q;
    reg [3:0] w_strb_q;
    reg [31:0] cfg_nonce;
    reg [1:0] cfg_decay;
    reg signed [15:0] cfg_initial [0:3];
    reg signed [15:0] cfg_bias [0:3];
    reg signed [15:0] cfg_threshold [0:3];
    reg signed [15:0] cfg_reset [0:3];
    reg signed [31:0] currents [0:15];
    reg signed [15:0] membrane [0:3];
    reg signed [15:0] trace_voltage [0:15];
    reg [3:0] spike_mask [0:3];
    reg [1:0] neuron, tick;
    reg busy, done;
    reg [31:0] result_nonce, run_count;
    integer i;

    assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid &&
                           !s_axi_rvalid;
    assign s_axi_wready = aresetn && !w_pending && !s_axi_bvalid &&
                          !s_axi_rvalid;
    assign s_axi_arready = aresetn && !s_axi_rvalid && !s_axi_bvalid &&
                           !aw_pending && !w_pending &&
                           !s_axi_awvalid && !s_axi_wvalid;

    wire [11:0] write_offset = aw_addr_q - 12'h040;
    wire [1:0] write_neuron = write_offset[6:5];
    wire [2:0] write_word = write_offset[4:2];
    wire [11:0] read_offset = s_axi_araddr - 12'h040;
    wire [1:0] read_neuron = read_offset[6:5];
    wire [2:0] read_word = read_offset[4:2];
    wire [11:0] result_offset = s_axi_araddr - 12'h100;
    wire [1:0] result_neuron = result_offset[6:5];
    wire [2:0] result_word = result_offset[4:2];

    wire signed16_write = (w_data_q[31:16] == {16{w_data_q[15]}});
    wire config_valid =
        cfg_nonce != 0 && cfg_decay <= 2'd2 &&
        cfg_threshold[0] > 0 && cfg_reset[0] < cfg_threshold[0] &&
        cfg_threshold[1] > 0 && cfg_reset[1] < cfg_threshold[1] &&
        cfg_threshold[2] > 0 && cfg_reset[2] < cfg_threshold[2] &&
        cfg_threshold[3] > 0 && cfg_reset[3] < cfg_threshold[3];

    wire [3:0] compute_index = {neuron,tick};
    wire signed [31:0] prev_ext =
        {{16{membrane[neuron][15]}},membrane[neuron]};
    wire signed [31:0] half_trunc =
        prev_ext < 0 ? -((-prev_ext) >>> 1) : (prev_ext >>> 1);
    wire signed [31:0] leaked =
        cfg_decay == 0 ? 32'sd0 :
        cfg_decay == 1 ? half_trunc : prev_ext;
    wire signed [31:0] current_now = currents[compute_index];
    wire signed [63:0] total =
        $signed({{32{leaked[31]}},leaked}) +
        $signed({{48{cfg_bias[neuron][15]}},cfg_bias[neuron]}) +
        $signed({{32{current_now[31]}},current_now});
    wire signed [15:0] saturated =
        total > 64'sd32767 ? 16'sd32767 :
        total < -64'sd32768 ? -16'sd32768 : total[15:0];
    wire fired = saturated >= cfg_threshold[neuron];
    wire signed [15:0] next_voltage =
        fired ? cfg_reset[neuron] : saturated;

    always @(posedge aclk) begin
        if (!aresetn) begin
            aw_pending <= 0; w_pending <= 0; aw_addr_q <= 0;
            w_data_q <= 0; w_strb_q <= 0;
            s_axi_bvalid <= 0; s_axi_bresp <= OKAY;
            s_axi_rvalid <= 0; s_axi_rresp <= OKAY; s_axi_rdata <= 0;
            cfg_nonce <= 0; cfg_decay <= 0;
            neuron <= 0; tick <= 0;
            busy <= 0; done <= 0;
            result_nonce <= 0; run_count <= 0;
            for (i=0; i<4; i=i+1) begin
                cfg_initial[i] <= 0;
                cfg_bias[i] <= 0;
                cfg_threshold[i] <= 0;
                cfg_reset[i] <= 0;
                membrane[i] <= 0;
                spike_mask[i] <= 0;
            end
            for (i=0; i<16; i=i+1) begin
                currents[i] <= 0;
                trace_voltage[i] <= 0;
            end
        end else begin
            if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;
            if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;
            if (s_axi_awvalid && s_axi_awready) begin
                aw_pending <= 1;
                aw_addr_q <= s_axi_awaddr;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                w_pending <= 1;
                w_data_q <= s_axi_wdata;
                w_strb_q <= s_axi_wstrb;
            end
            // One independent neuron update per clock; no premature next-tick
            // propagation. All four neurons update even with zero input.
            if (busy) begin
                membrane[neuron] <= next_voltage;
                trace_voltage[compute_index] <= next_voltage;
                spike_mask[neuron][tick] <= fired;
                if (neuron == 2'd3) begin
                    neuron <= 0;
                    if (tick == 2'd3) begin
                        tick <= 0;
                        busy <= 0;
                        done <= 1;
                        run_count <= run_count + 1;
                    end else tick <= tick + 1'b1;
                end else neuron <= neuron + 1'b1;
            end
            if (aw_pending && w_pending && !s_axi_bvalid) begin
                aw_pending <= 0; w_pending <= 0;
                s_axi_bvalid <= 1; s_axi_bresp <= OKAY;
                if (aw_addr_q[1:0] != 0) s_axi_bresp <= DECERR;
                else if (w_strb_q != 4'hF || busy) s_axi_bresp <= SLVERR;
                else if (aw_addr_q >= 12'h040 &&
                         aw_addr_q < 12'h0C0) begin
                    case (write_word)
                        3'd0: if (signed16_write) cfg_initial[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd1: if (signed16_write) cfg_bias[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd2: if (signed16_write) cfg_threshold[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd3: if (signed16_write) cfg_reset[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd4: currents[{write_neuron,2'b00} + 4'd0] <= w_data_q;
                        3'd5: currents[{write_neuron,2'b00} + 4'd1] <= w_data_q;
                        3'd6: currents[{write_neuron,2'b00} + 4'd2] <= w_data_q;
                        3'd7: currents[{write_neuron,2'b00} + 4'd3] <= w_data_q;
                    endcase
                end else begin
                    case (aw_addr_q)
                        12'h00C: cfg_nonce <= w_data_q;
                        12'h010: if (w_data_q <= 32'd2)
                                     cfg_decay <= w_data_q[1:0];
                                 else s_axi_bresp <= SLVERR;
                        12'h014: begin
                            if (w_data_q != 32'd1 || !config_valid)
                                s_axi_bresp <= SLVERR;
                            else begin
                                for (i=0; i<4; i=i+1) begin
                                    membrane[i] <= cfg_initial[i];
                                    spike_mask[i] <= 0;
                                end
                                for (i=0; i<16; i=i+1)
                                    trace_voltage[i] <= 0;
                                neuron <= 0; tick <= 0;
                                busy <= 1; done <= 0;
                                result_nonce <= cfg_nonce;
                            end
                        end
                        12'h100,12'h104,12'h108,12'h10C,12'h110,
                        12'h120,12'h124,12'h128,12'h12C,12'h130,
                        12'h140,12'h144,12'h148,12'h14C,12'h150,
                        12'h160,12'h164,12'h168,12'h16C,12'h170:
                            s_axi_bresp <= SLVERR;
                        default: s_axi_bresp <= DECERR;
                    endcase
                end
            end
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1; s_axi_rresp <= OKAY;
                s_axi_rdata <= 0;
                if (s_axi_araddr[1:0] != 0) s_axi_rresp <= DECERR;
                else if (s_axi_araddr >= 12'h040 &&
                         s_axi_araddr < 12'h0C0) begin
                    case (read_word)
                        3'd0: s_axi_rdata <= {{16{cfg_initial[read_neuron][15]}},cfg_initial[read_neuron]};
                        3'd1: s_axi_rdata <= {{16{cfg_bias[read_neuron][15]}},cfg_bias[read_neuron]};
                        3'd2: s_axi_rdata <= {{16{cfg_threshold[read_neuron][15]}},cfg_threshold[read_neuron]};
                        3'd3: s_axi_rdata <= {{16{cfg_reset[read_neuron][15]}},cfg_reset[read_neuron]};
                        3'd4: s_axi_rdata <= currents[{read_neuron,2'b00} + 4'd0];
                        3'd5: s_axi_rdata <= currents[{read_neuron,2'b00} + 4'd1];
                        3'd6: s_axi_rdata <= currents[{read_neuron,2'b00} + 4'd2];
                        3'd7: s_axi_rdata <= currents[{read_neuron,2'b00} + 4'd3];
                    endcase
                end else if (s_axi_araddr >= 12'h100 &&
                             s_axi_araddr < 12'h180) begin
                    if (!done) s_axi_rresp <= SLVERR;
                    else begin
                        case (result_word)
                            3'd0,3'd1,3'd2,3'd3:
                                s_axi_rdata <= {{16{trace_voltage[{result_neuron,2'b00}+result_word[1:0]][15]}},
                                                 trace_voltage[{result_neuron,2'b00}+result_word[1:0]]};
                            3'd4: s_axi_rdata <= {28'b0,spike_mask[result_neuron]};
                            default: s_axi_rresp <= DECERR;
                        endcase
                    end
                end else begin
                    case (s_axi_araddr)
                        12'h000: s_axi_rdata <= MAGIC;
                        12'h004: s_axi_rdata <= VERSION;
                        12'h008: s_axi_rdata <= {30'b0,busy,done};
                        12'h00C: s_axi_rdata <= cfg_nonce;
                        12'h010: s_axi_rdata <= {30'b0,cfg_decay};
                        12'h018: if (done) s_axi_rdata <= result_nonce;
                                 else s_axi_rresp <= SLVERR;
                        12'h01C: s_axi_rdata <= run_count;
                        default: s_axi_rresp <= DECERR;
                    endcase
                end
            end
        end
    end
endmodule
