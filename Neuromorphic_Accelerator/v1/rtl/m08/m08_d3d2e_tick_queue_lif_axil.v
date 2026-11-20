// M08 D3.D.2E.1 SOURCE CANDIDATE (NOT PHYSICALLY VERIFIED).
// New M32Q v6: 32-entry clocked FIFO, ordered tick service and guarded
// shadow sums. All M06 signed16 LIF/recurrent stages descend from accepted
// D3.D.2D, but this NEW source/image is NOT accepted for physical programming.
// Synchronous JTAG AXI-Lite only: no async clock-domain, DMA or real DDR.
// M08 D3.D.2D — new separate 32-neuron M06 raw external event-ingress RTL.
// Distinct M32E v5 JTAG AXI4-Lite control-plane ingress, NOT streamed AXI
// events, M05 HLS, DMA/DDR/paging, physical asynchronous delivery or PS MMIO.
// Host sends ORIGINAL 17 separate {neuron,tick,signed32 current} event tuples.
// Fabric accumulates them with signed33 overflow checks into 128 input slots.
// Any invalid tuple, overflow, >64 events, partial command or BUSY push is
// rejected with AXI SLVERR, without modifying counters/buckets. Event CLEAR
// permits replay; 32x4 M06 recurrent neural arithmetic is retained unchanged.
// New candidate MUST be independently routed/DRC/timing+image SHA-reviewed
// before one-shot owner physical attempt. D3.D.2C physical PASS is immutable.
module m08_d3d2e_tick_queue_lif_axil (
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
    localparam [31:0] MAGIC=32'h4D333251; // "M32Q" new queue ABI
    localparam [31:0] VERSION=32'h00060000;
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
    reg signed [31:0] currents [0:127]; // fabric-generated event bucket sums
    reg [4:0] event_neuron;
    reg [1:0] event_tick;
    reg signed [31:0] event_current;
    // D3.D.2E.1: acceptance and tick service are distinct clocked boundaries.
    // 32-entry power-of-two queue; accepted count remains bounded at 64.
    // shadow_current checks every signed prefix atomically at enqueue;
    // no accepted event can overflow later during FIFO service.
    reg signed [31:0] shadow_current [0:127];
    reg [4:0] fifo_neuron [0:31];
    reg [1:0] fifo_tick [0:31];
    reg signed [31:0] fifo_current [0:31];
    reg [4:0] fifo_wr_ptr, fifo_rd_ptr;
    reg [5:0] fifo_depth, fifo_high_watermark;
    reg [6:0] event_count;       // accepted lifetime count, <=64
    reg [6:0] serviced_count;    // actually removed from FIFO
    reg [6:0] per_tick_serviced [0:3];
    reg [3:0] serviced_tick_mask;
    reg [2:0] next_service_tick; // 0..4, advance only after service completes
    reg [1:0] active_service_tick;
    reg [1:0] last_accepted_tick;
    reg any_accepted;
    reg service_busy;
    wire [6:0] event_index={event_neuron,event_tick};
    wire [6:0] fifo_head_index={fifo_neuron[fifo_rd_ptr],fifo_tick[fifo_rd_ptr]};
    wire signed [32:0] event_sum_ext=
        $signed({shadow_current[event_index][31],shadow_current[event_index]}) +
        $signed({event_current[31],event_current});
    wire event_overflow=event_sum_ext[32] != event_sum_ext[31];
    reg signed [15:0] membrane [0:31];
    reg signed [15:0] trace_voltage [0:127];
    reg signed [31:0] trace_syn_current [0:127];
    reg [3:0] spike_mask [0:31];
    reg [4:0] neuron;
    reg [1:0] tick;
    reg busy, done;
    reg [31:0] result_nonce, run_count;
    integer i;
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
    // Exact signed20 width for eight signed16 contributions:
    // [-262144,+262136], leaving all five original M06 edges intact.
    reg signed [19:0] syn_accum;
    reg [3:0] route_slot;
    reg [2:0] update_phase;
    reg signed [16:0] leak_bias_stage;
    reg signed [33:0] external_stage;
    reg signed [33:0] total_stage;
    localparam [2:0] PHASE_ROUTE = 3'd0, PHASE_BASE = 3'd1,
        PHASE_EXT = 3'd2, PHASE_TOTAL = 3'd3, PHASE_COMMIT = 3'd4;

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
        cfg_nonce != 0 && cfg_edge_count <= 4'd8 &&
        event_count != 0 && serviced_count == event_count &&
        fifo_depth == 0 && serviced_tick_mask == 4'hF &&
        next_service_tick == 3'd4 && !service_busy &&
        neurons_valid && edges_valid;

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
    // No same-tick propagation: positive delay consults committed history.
    // Time-multiplex one synapse per fabric cycle. Only ONE 20-bit weight
    // addition occurs per edge clock; the post-synaptic sum and threshold
    // evaluation consume independently registered pipeline stages.
    wire edge_active_now =
        route_slot < cfg_edge_count &&
        edge_post[route_slot] == neuron &&
        edge_delay[route_slot] != 0 &&
        {30'b0,tick} >= {30'b0,edge_delay[route_slot]} &&
        spike_mask[edge_pre[route_slot]][tick - edge_delay[route_slot]];
    wire signed [19:0] selected_weight =
        {{4{edge_weight[route_slot][15]}},edge_weight[route_slot]};
    wire signed [15:0] saturated =
        total_stage > 34'sd32767 ? 16'sd32767 :
        total_stage < -34'sd32768 ? -16'sd32768 : total_stage[15:0];
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
            event_neuron <= 0; event_tick <= 0;
            event_current <= 0; event_count <= 0;
            serviced_count <= 0; fifo_wr_ptr <= 0; fifo_rd_ptr <= 0;
            fifo_depth <= 0; fifo_high_watermark <= 0;
            serviced_tick_mask <= 0; next_service_tick <= 0;
            active_service_tick <= 0; last_accepted_tick <= 0;
            any_accepted <= 0; service_busy <= 0;
            for (i=0; i<4; i=i+1) per_tick_serviced[i] <= 0;
            for (i=0; i<8; i=i+1) begin
                edge_pre[i] <= 0;
                edge_post[i] <= 0;
                edge_weight[i] <= 0;
                edge_delay[i] <= 0;
            end
            neuron <= 0; tick <= 0;
            syn_accum <= 0; route_slot <= 0; update_phase <= PHASE_ROUTE;
            leak_bias_stage <= 0; external_stage <= 0; total_stage <= 0;
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
                shadow_current[i] <= 0;
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
            // Serve one physical FIFO record per fabric clock, never in the
            // same edge as the host PUSH. The head determines the next tick.
            // An empty tick completes without manufacturing an event.
            if (service_busy) begin
                if (fifo_depth != 0 &&
                    fifo_tick[fifo_rd_ptr] == active_service_tick) begin
                    currents[fifo_head_index] <=
                        currents[fifo_head_index] + fifo_current[fifo_rd_ptr];
                    fifo_rd_ptr <= fifo_rd_ptr + 1'b1;
                    fifo_depth <= fifo_depth - 1'b1;
                    serviced_count <= serviced_count + 1'b1;
                    per_tick_serviced[active_service_tick] <=
                        per_tick_serviced[active_service_tick] + 1'b1;
                end else if (fifo_depth == 0 ||
                             fifo_tick[fifo_rd_ptr] > active_service_tick) begin
                    serviced_tick_mask[active_service_tick] <= 1'b1;
                    next_service_tick <= next_service_tick + 1'b1;
                    service_busy <= 0;
                end else begin
                    // Unexpected stale head: stop without advancing tick.
                    // No DONE is possible; owner must CLEAR and replay.
                    service_busy <= 0;
                end
            end
            // Time-multiplexed neuron execution: all 32 neurons and each
            // logical tick still update (zero input included). No direct
            // spike_mask -> trace_voltage register-to-register path.
            if (busy) begin
                case (update_phase)
                    PHASE_ROUTE: begin
                        if (route_slot < cfg_edge_count) begin
                            if (edge_active_now)
                                syn_accum <= syn_accum + selected_weight;
                            route_slot <= route_slot + 1'b1;
                        end else update_phase <= PHASE_BASE;
                    end
                    PHASE_BASE: begin
                        // Both operands signed16: exact signed17.
                        leak_bias_stage <=
                            $signed({leaked[15],leaked[15:0]}) +
                            $signed({cfg_bias[neuron][15],cfg_bias[neuron]});
                        update_phase <= PHASE_EXT;
                    end
                    PHASE_EXT: begin
                        // Signed17 plus signed32: exact in signed34.
                        external_stage <=
                            $signed({{17{leak_bias_stage[16]}},leak_bias_stage}) +
                            $signed({{2{current_now[31]}},current_now});
                        update_phase <= PHASE_TOTAL;
                    end
                    PHASE_TOTAL: begin
                        // Signed34 exact total, then one final saturate.
                        total_stage <= external_stage +
                            $signed({{14{syn_accum[19]}},syn_accum});
                        update_phase <= PHASE_COMMIT;
                    end
                    PHASE_COMMIT: begin
                        membrane[neuron] <= next_voltage;
                        trace_voltage[compute_index] <= next_voltage;
                        trace_syn_current[compute_index] <=
                            {{12{syn_accum[19]}},syn_accum};
                        spike_mask[neuron][tick] <= fired;
                        route_slot <= 0;
                        syn_accum <= 0;
                        update_phase <= PHASE_ROUTE;
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
                    default: begin
                        // Invalid pipeline state fails closed (no DONE).
                        route_slot <= 0;
                        syn_accum <= 0;
                        update_phase <= PHASE_ROUTE;
                        busy <= 0;
                    end
                endcase
            end
            if (aw_pending && w_pending && !s_axi_bvalid) begin
                aw_pending <= 0; w_pending <= 0;
                s_axi_bvalid <= 1; s_axi_bresp <= OKAY;
                if (aw_addr_q[1:0] != 0) s_axi_bresp <= DECERR;
                else if (w_strb_q != 4'hF || busy || service_busy)
                    s_axi_bresp <= SLVERR;
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
                        // Inputs are generated ONLY by service; no host bypass.
                        3'd4,3'd5,3'd6,3'd7: s_axi_bresp <= SLVERR;
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
                        12'h024: if (w_data_q <= 32'd31)
                                     event_neuron <= w_data_q[4:0];
                                 else s_axi_bresp <= SLVERR;
                        12'h028: if (w_data_q <= 32'd3)
                                     event_tick <= w_data_q[1:0];
                                 else s_axi_bresp <= SLVERR;
                        12'h02C: event_current <= w_data_q;
                        12'h030: begin
                            if (w_data_q != 32'd1 || event_count >= 7'd64 ||
                                fifo_depth == 6'd32 || event_overflow ||
                                serviced_tick_mask[event_tick] ||
                                {1'b0,event_tick} < next_service_tick ||
                                (any_accepted && event_tick < last_accepted_tick))
                                s_axi_bresp <= SLVERR;
                            else begin
                                // Atomic admission: depth/count/shadow update
                                // only if the full signed prefix fits int32.
                                fifo_neuron[fifo_wr_ptr] <= event_neuron;
                                fifo_tick[fifo_wr_ptr] <= event_tick;
                                fifo_current[fifo_wr_ptr] <= event_current;
                                fifo_wr_ptr <= fifo_wr_ptr + 1'b1;
                                fifo_depth <= fifo_depth + 1'b1;
                                if (fifo_depth + 1'b1 > fifo_high_watermark)
                                    fifo_high_watermark <= fifo_depth + 1'b1;
                                shadow_current[event_index] <= event_sum_ext[31:0];
                                event_count <= event_count + 1'b1;
                                any_accepted <= 1;
                                last_accepted_tick <= event_tick;
                            end
                        end
                        12'h038: begin
                            if (w_data_q != 32'd1) s_axi_bresp <= SLVERR;
                            else begin
                                for (i=0;i<128;i=i+1) begin
                                    currents[i] <= 0;
                                    shadow_current[i] <= 0;
                                end
                                event_count <= 0; serviced_count <= 0;
                                fifo_wr_ptr <= 0; fifo_rd_ptr <= 0;
                                fifo_depth <= 0; fifo_high_watermark <= 0;
                                serviced_tick_mask <= 0; next_service_tick <= 0;
                                active_service_tick <= 0; last_accepted_tick <= 0;
                                any_accepted <= 0;
                                for (i=0;i<4;i=i+1) per_tick_serviced[i] <= 0;
                                event_neuron <= 0; event_tick <= 0;
                                event_current <= 0;
                            end
                        end
                        12'h040: begin
                            // Ordered, explicit tick barrier, including empty ticks.
                            if (w_data_q > 32'd3 ||
                                {30'b0,next_service_tick} != w_data_q ||
                                serviced_tick_mask[next_service_tick[1:0]])
                                s_axi_bresp <= SLVERR;
                            else begin
                                active_service_tick <= w_data_q[1:0];
                                service_busy <= 1;
                            end
                        end
                        12'h034: s_axi_bresp <= SLVERR; // read-only event count
                        12'h03C: s_axi_bresp <= SLVERR; // read-only selected sum
                        12'h044,12'h048,12'h04C,12'h050,
                        12'h054,12'h058: s_axi_bresp <= SLVERR; // counters
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
                                syn_accum <= 0; route_slot <= 0;
                                update_phase <= PHASE_ROUTE;
                                leak_bias_stage <= 0; external_stage <= 0;
                                total_stage <= 0;
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
                        12'h024: s_axi_rdata <= {27'b0,event_neuron};
                        12'h028: s_axi_rdata <= {30'b0,event_tick};
                        12'h02C: s_axi_rdata <= event_current;
                        12'h030: s_axi_rresp <= SLVERR; // write-only PUSH
                        12'h034: s_axi_rdata <= {25'b0,event_count};
                        12'h038: s_axi_rresp <= SLVERR; // write-only CLEAR
                        12'h03C: s_axi_rdata <= currents[event_index];
                        12'h040: s_axi_rresp <= SLVERR; // write-only SERVICE
                        12'h044: s_axi_rdata <= {26'b0,fifo_depth};
                        12'h048: s_axi_rdata <= {26'b0,fifo_high_watermark};
                        12'h04C: s_axi_rdata <= {25'b0,serviced_count};
                        12'h050: s_axi_rdata <= {28'b0,serviced_tick_mask};
                        12'h054: s_axi_rdata <= {28'b0,next_service_tick,service_busy};
                        12'h058: s_axi_rdata <= {25'b0,per_tick_serviced[event_tick]};
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
