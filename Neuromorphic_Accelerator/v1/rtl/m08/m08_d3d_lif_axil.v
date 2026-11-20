// M08 D3.D.1: first real hardware-executed M02 signed16 LIF neuron.
// One neuron x 4 sequential ticks. No synapse routing, DDR, or paging.
// Exact M02 revision-1 arithmetic for supported decay modes {0, 1/2, 1}.
// AXI4-Lite accepts decoupled AW/W, one outstanding response, stable R/B.
// Only hardware can write output traces/spikes; all output reads before DONE
// return SLVERR and zero. This is not a fake BRAM echo or PC computed output.
// Address aperture 4KiB, word offsets 0x000..0x050.
module m08_d3d_lif_axil (
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
    localparam [31:0] MAGIC=32'h4D384C46; // "M8LF"
    localparam [31:0] VERSION=32'h00010000;
    reg aw_pending, w_pending;
    reg [11:0] aw_addr_q;
    reg [31:0] w_data_q;
    reg [3:0] w_strb_q;
    reg signed [15:0] cfg_initial, cfg_bias, cfg_threshold, cfg_reset;
    reg [1:0] cfg_decay;
    reg [31:0] cfg_nonce;
    reg signed [31:0] currents [0:3];
    reg signed [15:0] membrane;
    reg signed [15:0] trace_voltage [0:3];
    reg [3:0] spike_mask;
    reg [1:0] tick;
    reg busy, done;
    reg [31:0] result_nonce, run_count;
    integer i;

    assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid &&
                           !s_axi_rvalid;
    assign s_axi_wready  = aresetn && !w_pending && !s_axi_bvalid &&
                           !s_axi_rvalid;
    assign s_axi_arready = aresetn && !s_axi_rvalid && !s_axi_bvalid &&
                           !aw_pending && !w_pending &&
                           !s_axi_awvalid && !s_axi_wvalid;

    // Each tick computes from the *stored* membrane of the previous tick.
    wire signed [31:0] prev_ext = {{16{membrane[15]}}, membrane};
    // Signed /2 truncates toward zero, NOT Verilog/Python arithmetic floor.
    wire signed [31:0] half_trunc =
        (prev_ext < 0) ? -((-prev_ext) >>> 1) : (prev_ext >>> 1);
    wire signed [31:0] leaked = (cfg_decay == 2'd0) ? 32'sd0 :
                                (cfg_decay == 2'd1) ? half_trunc : prev_ext;
    wire signed [31:0] current_now = currents[tick];
    wire signed [63:0] total =
        $signed({{32{leaked[31]}}, leaked}) +
        $signed({{48{cfg_bias[15]}}, cfg_bias}) +
        $signed({{32{current_now[31]}}, current_now});
    wire signed [15:0] saturated =
        (total > 64'sd32767) ? 16'sd32767 :
        (total < -64'sd32768) ? -16'sd32768 : total[15:0];
    wire fired = saturated >= cfg_threshold;
    wire signed [15:0] next_voltage = fired ? cfg_reset : saturated;
    wire config_valid = cfg_nonce != 0 &&
                        cfg_threshold > 0 &&
                        cfg_reset < cfg_threshold && cfg_decay <= 2'd2;
    wire signed16_write = (w_data_q[31:16] == {16{w_data_q[15]}});

    always @(posedge aclk) begin
        if (!aresetn) begin
            aw_pending <= 0; w_pending <= 0; aw_addr_q <= 0;
            w_data_q <= 0; w_strb_q <= 0;
            s_axi_bvalid <= 0; s_axi_bresp <= OKAY;
            s_axi_rvalid <= 0; s_axi_rresp <= OKAY; s_axi_rdata <= 0;
            cfg_initial <= 0; cfg_bias <= 0; cfg_threshold <= 0;
            cfg_reset <= 0; cfg_decay <= 0; cfg_nonce <= 0;
            membrane <= 0; spike_mask <= 0; tick <= 0;
            busy <= 0; done <= 0; result_nonce <= 0; run_count <= 0;
            for (i=0; i<4; i=i+1) begin
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

            // Independent clocked hardware neuron execution (not AXI echo).
            if (busy) begin
                membrane <= next_voltage;
                trace_voltage[tick] <= next_voltage;
                spike_mask[tick] <= fired;
                if (tick == 2'd3) begin
                    tick <= 0;
                    busy <= 0;
                    done <= 1;
                    run_count <= run_count + 1;
                end else tick <= tick + 1'b1;
            end

            if (aw_pending && w_pending && !s_axi_bvalid) begin
                aw_pending <= 0;
                w_pending <= 0;
                s_axi_bvalid <= 1;
                s_axi_bresp <= OKAY;
                if (aw_addr_q[1:0] != 0) s_axi_bresp <= DECERR;
                else if (w_strb_q != 4'hF || busy) s_axi_bresp <= SLVERR;
                else begin
                    case (aw_addr_q)
                        12'h00C: cfg_nonce <= w_data_q;
                        12'h010: if (signed16_write) cfg_initial <= w_data_q[15:0];
                                  else s_axi_bresp <= SLVERR;
                        12'h014: if (signed16_write) cfg_bias <= w_data_q[15:0];
                                  else s_axi_bresp <= SLVERR;
                        12'h018: if (signed16_write) cfg_threshold <= w_data_q[15:0];
                                  else s_axi_bresp <= SLVERR;
                        12'h01C: if (signed16_write) cfg_reset <= w_data_q[15:0];
                                  else s_axi_bresp <= SLVERR;
                        12'h020: if (w_data_q <= 32'd2) cfg_decay <= w_data_q[1:0];
                                  else s_axi_bresp <= SLVERR;
                        12'h024: currents[0] <= w_data_q;
                        12'h028: currents[1] <= w_data_q;
                        12'h02C: currents[2] <= w_data_q;
                        12'h030: currents[3] <= w_data_q;
                        12'h034: begin
                            if (w_data_q != 32'd1 || !config_valid)
                                s_axi_bresp <= SLVERR;
                            else begin
                                membrane <= cfg_initial;
                                tick <= 0;
                                busy <= 1;
                                done <= 0;
                                spike_mask <= 0;
                                result_nonce <= cfg_nonce;
                                // Clear stale voltages on every accepted launch.
                                for (i=0; i<4; i=i+1)
                                    trace_voltage[i] <= 0;
                            end
                        end
                        default: s_axi_bresp <= DECERR;
                    endcase
                end
            end

            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1;
                s_axi_rresp <= OKAY;
                s_axi_rdata <= 0;
                if (s_axi_araddr[1:0] != 0)
                    s_axi_rresp <= DECERR;
                else begin
                    case(s_axi_araddr)
                        12'h000: s_axi_rdata <= MAGIC;
                        12'h004: s_axi_rdata <= VERSION;
                        12'h008: s_axi_rdata <= {30'b0, busy, done};
                        12'h00C: s_axi_rdata <= cfg_nonce;
                        12'h010: s_axi_rdata <= {{16{cfg_initial[15]}}, cfg_initial};
                        12'h014: s_axi_rdata <= {{16{cfg_bias[15]}}, cfg_bias};
                        12'h018: s_axi_rdata <= {{16{cfg_threshold[15]}}, cfg_threshold};
                        12'h01C: s_axi_rdata <= {{16{cfg_reset[15]}}, cfg_reset};
                        12'h020: s_axi_rdata <= {30'b0, cfg_decay};
                        12'h024: s_axi_rdata <= currents[0];
                        12'h028: s_axi_rdata <= currents[1];
                        12'h02C: s_axi_rdata <= currents[2];
                        12'h030: s_axi_rdata <= currents[3];
                        12'h038: if (done) s_axi_rdata <= result_nonce;
                                 else s_axi_rresp <= SLVERR;
                        12'h03C: if (done) s_axi_rdata <= {28'b0, spike_mask};
                                 else s_axi_rresp <= SLVERR;
                        12'h040: if (done) s_axi_rdata <= {{16{trace_voltage[0][15]}}, trace_voltage[0]};
                                 else s_axi_rresp <= SLVERR;
                        12'h044: if (done) s_axi_rdata <= {{16{trace_voltage[1][15]}}, trace_voltage[1]};
                                 else s_axi_rresp <= SLVERR;
                        12'h048: if (done) s_axi_rdata <= {{16{trace_voltage[2][15]}}, trace_voltage[2]};
                                 else s_axi_rresp <= SLVERR;
                        12'h04C: if (done) s_axi_rdata <= {{16{trace_voltage[3][15]}}, trace_voltage[3]};
                                 else s_axi_rresp <= SLVERR;
                        12'h050: s_axi_rdata <= run_count;
                        default: s_axi_rresp <= DECERR;
                    endcase
                end
            end
        end
    end
endmodule
