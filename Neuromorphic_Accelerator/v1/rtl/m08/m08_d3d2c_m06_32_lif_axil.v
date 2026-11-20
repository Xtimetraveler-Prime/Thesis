// M08 D3.D.2C: 32 LIF neurons x4 ticks, M06 5-edge recurrent workload.
// Independent new RTL candidate; NOT physically implemented or owner-accepted.
// 17 M06 external events are coalesced on PC before AXI signed32 currents.
// NO DDR, PS HPM, Linux MMIO, event coalescing in fabric, throughput claims.
// ABI (byte offsets): header 000-020, neurons 100-4FF (n*20 + 8 words),
// synapses 500-57F (e*10 + 4 words), voltage/mask 900-CFF,
// computed synaptic currents D00-EFF. All values base A0001000 over JTAG.
// New "M32N" v4. M06 decay mode 3 = signed truncation toward zero of 3V/4.
module m08_d3d2c_m06_32_lif_axil (
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
    localparam [31:0] MAGIC=32'h4D33324E; // "M32N"
    localparam [31:0] VERSION=32'h00040000;
    reg aw_pending, w_pending;
    reg [11:0] aw_addr_q;
    reg [31:0] w_data_q;
    reg [3:0] w_strb_q;
    reg [31:0] cfg_nonce;
    reg [1:0] cfg_decay;
    reg [3:0] cfg_edge_count; // 0..8
    reg [4:0] edge_pre [0:7];
    reg [4:0] edge_post [0:7];
    reg signed [15:0] edge_weight [0:7];
    reg [1:0] edge_delay [0:7];
    reg signed [15:0] cfg_initial [0:31];
    reg signed [15:0] cfg_bias [0:31];
    reg signed [15:0] cfg_threshold [0:31];
    reg signed [15:0] cfg_reset [0:31];
    reg signed [31:0] currents [0:127];
    reg signed [15:0] membrane [0:31];
    reg signed [15:0] trace_voltage [0:127];
    reg signed [31:0] trace_syn_current [0:127];
    reg [3:0] spike_mask [0:31];
    reg [4:0] neuron;
    reg [1:0] tick;
    reg busy, done;
    reg [31:0] result_nonce, run_count;
    integer i;
    integer route_idx;
    integer validate_idx;
    integer validate_neuron;
    reg neurons_valid;
    always @* begin
        neurons_valid = 1'b1;
        for (validate_neuron=0; validate_neuron<32; validate_neuron=validate_neuron+1)
            if (cfg_threshold[validate_neuron] <= 0 ||
                cfg_reset[validate_neuron] >= cfg_threshold[validate_neuron])
                neurons_valid = 1'b0;
    end
    reg edges_valid;
    reg signed [63:0] synaptic_sum;

    // All active edges must have genuine positive delays, exact IDs and
    // sign-extended weights. Inactive slots are never visited at execution.
    always @* begin
        edges_valid = 1'b1;
        for (validate_idx=0;validate_idx<8;validate_idx=validate_idx+1) begin
            if (validate_idx < cfg_edge_count &&
                (edge_delay[validate_idx] == 2'd0))
                edges_valid = 1'b0;
        end
    end

    assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid &&
                           !s_axi_rvalid;
    assign s_axi_wready = aresetn && !w_pending && !s_axi_bvalid &&
                          !s_axi_rvalid;
    assign s_axi_arready = aresetn && !s_axi_rvalid && !s_axi_bvalid &&
                           !aw_pending && !w_pending &&
                           !s_axi_awvalid && !s_axi_wvalid;

    wire [11:0] write_offset = aw_addr_q - 12'h100;
    wire [4:0] write_neuron = write_offset[9:5];
    wire [2:0] write_word = write_offset[4:2];
    wire [11:0] read_offset = s_axi_araddr - 12'h100;
    wire [4:0] read_neuron = read_offset[9:5];
    wire [2:0] read_word = read_offset[4:2];
    wire [11:0] edge_write_offset = aw_addr_q - 12'h500;
    wire [2:0] edge_write_index = edge_write_offset[6:4];
    wire [1:0] edge_write_word = edge_write_offset[3:2];
    wire [11:0] edge_read_offset = s_axi_araddr - 12'h500;
    wire [2:0] edge_read_index = edge_read_offset[6:4];
    wire [1:0] edge_read_word = edge_read_offset[3:2];
    wire [11:0] syn_read_offset = s_axi_araddr - 12'hD00;
    wire [6:0] syn_read_index = syn_read_offset[8:2];
    wire [11:0] result_offset = s_axi_araddr - 12'h900;
    wire [4:0] result_neuron = result_offset[9:5];
    wire [2:0] result_word = result_offset[4:2];

    wire signed16_write = (w_data_q[31:16] == {16{w_data_q[15]}});
    wire config_valid =
        cfg_nonce != 0 && cfg_edge_count <= 4'd8 && neurons_valid && edges_valid;

    wire [6:0] compute_index = {neuron,tick};
    wire signed [31:0] prev_ext =
        {{16{membrane[neuron][15]}},membrane[neuron]};
    wire signed [31:0] half_trunc =
        prev_ext < 0 ? -((-prev_ext) >>> 1) : (prev_ext >>> 1);
    wire signed [31:0] three_scaled = prev_ext * 32'sd3;
    wire signed [31:0] three_quarter_trunc =
        three_scaled < 0 ? -((-three_scaled) >>> 2) : (three_scaled >>> 2);
    wire signed [31:0] leaked =
        cfg_decay == 0 ? 32'sd0 :
        cfg_decay == 1 ? half_trunc :
        cfg_decay == 2 ? prev_ext : three_quarter_trunc;
    wire signed [31:0] current_now = currents[compute_index];
    // No same-tick propagation: delay >= 1, so source history bit is
    // already committed at the time the destination tick is evaluated.
    // Thirty-two neurons * four ticks use 32 separate four-bit histories.
    // Signed64 sum ensures parallel weights are combined before saturation.
    always @* begin
        synaptic_sum = 64'sd0;
        for (route_idx=0;route_idx<8;route_idx=route_idx+1) begin
            if (route_idx < cfg_edge_count &&
                edge_post[route_idx] == neuron &&
                edge_delay[route_idx] != 0 &&
                {30'b0,tick} >= {30'b0,edge_delay[route_idx]} &&
                spike_mask[edge_pre[route_idx]][tick - edge_delay[route_idx]]) begin
                synaptic_sum = synaptic_sum +
                   $signed({{48{edge_weight[route_idx][15]}},edge_weight[route_idx]});
            end
        end
    end
    wire signed [63:0] total =
        $signed({{32{leaked[31]}},leaked}) +
        $signed({{48{cfg_bias[neuron][15]}},cfg_bias[neuron]}) +
        $signed({{32{current_now[31]}},current_now}) + synaptic_sum;
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
            cfg_nonce <= 0; cfg_decay <= 0; cfg_edge_count <= 0;
            for (i=0; i<8; i=i+1) begin
                edge_pre[i] <= 0;
                edge_post[i] <= 0;
                edge_weight[i] <= 0;
                edge_delay[i] <= 0;
            end
            neuron <= 0; tick <= 0;
            busy <= 0; done <= 0;
            result_nonce <= 0; run_count <= 0;
            for (i=0; i<32; i=i+1) begin
                cfg_initial[i] <= 0;
                cfg_bias[i] <= 0;
                cfg_threshold[i] <= 0;
                cfg_reset[i] <= 0;
                membrane[i] <= 0;
                spike_mask[i] <= 0;
            end
            for (i=0; i<128; i=i+1) begin
                currents[i] <= 0;
                trace_voltage[i] <= 0;
                trace_syn_current[i] <= 0;
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
            // propagation. All 32 neurons update even with zero input.
            if (busy) begin
                membrane[neuron] <= next_voltage;
                trace_voltage[compute_index] <= next_voltage;
                trace_syn_current[compute_index] <= synaptic_sum[31:0];
                spike_mask[neuron][tick] <= fired;
                if (neuron == 5'd31) begin
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
                else if (aw_addr_q >= 12'h100 &&
                         aw_addr_q < 12'h500) begin
                    case (write_word)
                        3'd0: if (signed16_write) cfg_initial[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd1: if (signed16_write) cfg_bias[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd2: if (signed16_write) cfg_threshold[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd3: if (signed16_write) cfg_reset[write_neuron] <= w_data_q[15:0];
                              else s_axi_bresp <= SLVERR;
                        3'd4: currents[{write_neuron,2'b00} + 7'd0] <= w_data_q;
                        3'd5: currents[{write_neuron,2'b00} + 7'd1] <= w_data_q;
                        3'd6: currents[{write_neuron,2'b00} + 7'd2] <= w_data_q;
                        3'd7: currents[{write_neuron,2'b00} + 7'd3] <= w_data_q;
                    endcase
                end else if (aw_addr_q >= 12'h500 &&
                             aw_addr_q < 12'h580) begin
                    case (edge_write_word)
                        2'd0: if (w_data_q <= 32'd31)
                                   edge_pre[edge_write_index] <= w_data_q[4:0];
                               else s_axi_bresp <= SLVERR;
                        2'd1: if (w_data_q <= 32'd31)
                                   edge_post[edge_write_index] <= w_data_q[4:0];
                               else s_axi_bresp <= SLVERR;
                        2'd2: if (signed16_write)
                                   edge_weight[edge_write_index] <= w_data_q[15:0];
                               else s_axi_bresp <= SLVERR;
                        2'd3: if (w_data_q >= 32'd1 && w_data_q <= 32'd3)
                                   edge_delay[edge_write_index] <= w_data_q[1:0];
                               else s_axi_bresp <= SLVERR;
                    endcase
                end else begin
                    case (aw_addr_q)
                        12'h00C: cfg_nonce <= w_data_q;
                        12'h020: if (w_data_q <= 32'd8)
                                     cfg_edge_count <= w_data_q[3:0];
                                 else s_axi_bresp <= SLVERR;
                        12'h010: if (w_data_q <= 32'd3)
                                     cfg_decay <= w_data_q[1:0];
                                 else s_axi_bresp <= SLVERR;
                        12'h014: begin
                            if (w_data_q != 32'd1 || !config_valid)
                                s_axi_bresp <= SLVERR;
                            else begin
                                for (i=0; i<32; i=i+1) begin
                                    membrane[i] <= cfg_initial[i];
                                    spike_mask[i] <= 0;
                                end
                                for (i=0; i<128; i=i+1) begin
                                    trace_voltage[i] <= 0;
                                    trace_syn_current[i] <= 0;
                                end
                                neuron <= 0; tick <= 0;
                                busy <= 1; done <= 0;
                                result_nonce <= cfg_nonce;
                            end
                        end

                        default: s_axi_bresp <= DECERR;
                    endcase
                end
            end
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1; s_axi_rresp <= OKAY;
                s_axi_rdata <= 0;
                if (s_axi_araddr[1:0] != 0) s_axi_rresp <= DECERR;
                else if (s_axi_araddr >= 12'h100 &&
                         s_axi_araddr < 12'h500) begin
                    case (read_word)
                        3'd0: s_axi_rdata <= {{16{cfg_initial[read_neuron][15]}},cfg_initial[read_neuron]};
                        3'd1: s_axi_rdata <= {{16{cfg_bias[read_neuron][15]}},cfg_bias[read_neuron]};
                        3'd2: s_axi_rdata <= {{16{cfg_threshold[read_neuron][15]}},cfg_threshold[read_neuron]};
                        3'd3: s_axi_rdata <= {{16{cfg_reset[read_neuron][15]}},cfg_reset[read_neuron]};
                        3'd4: s_axi_rdata <= currents[{read_neuron,2'b00} + 7'd0];
                        3'd5: s_axi_rdata <= currents[{read_neuron,2'b00} + 7'd1];
                        3'd6: s_axi_rdata <= currents[{read_neuron,2'b00} + 7'd2];
                        3'd7: s_axi_rdata <= currents[{read_neuron,2'b00} + 7'd3];
                    endcase
                end else if (s_axi_araddr >= 12'h500 &&
                              s_axi_araddr < 12'h580) begin
                    case (edge_read_word)
                        2'd0: s_axi_rdata <= {27'b0,edge_pre[edge_read_index]};
                        2'd1: s_axi_rdata <= {27'b0,edge_post[edge_read_index]};
                        2'd2: s_axi_rdata <= {{16{edge_weight[edge_read_index][15]}},
                                               edge_weight[edge_read_index]};
                        2'd3: s_axi_rdata <= {30'b0,edge_delay[edge_read_index]};
                    endcase
                end else if (s_axi_araddr >= 12'hD00 &&
                              s_axi_araddr < 12'hF00) begin
                    if (!done) s_axi_rresp <= SLVERR;
                    else s_axi_rdata <= trace_syn_current[syn_read_index];
                end else if (s_axi_araddr >= 12'h900 &&
                              s_axi_araddr < 12'hD00) begin
                    // Reserved result-window holes are DECERR even before
                    // DONE. Valid result registers are SLVERR until DONE.
                    if (result_word > 3'd4) s_axi_rresp <= DECERR;
                    else if (!done) s_axi_rresp <= SLVERR;
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
                        12'h020: s_axi_rdata <= {28'b0,cfg_edge_count};
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
