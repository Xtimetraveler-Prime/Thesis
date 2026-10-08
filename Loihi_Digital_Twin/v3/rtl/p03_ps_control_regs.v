`timescale 1ns/1ps

// FPGA-v3 P03.2 PS-visible AXI4-Lite control/status register block.
//
// This block replaces VIO as the command source for:
//   - DDR page commands;
//   - one-core dispatch commands;
//   - low-rate resident-context memory access.
//
// It deliberately does not implement the P03 scheduler/router itself.  P03.3
// software running on the Cortex-A53 drives this register contract.
//
// AXI4-Lite: 32-bit data, 40-bit system byte address, one outstanding
// read/write.  Internal register decode uses addr[11:0] for the fixed 4 KiB
// aperture.  Keeping the full HPM0 address width avoids relying on
// interconnect-side 40->12 address localization.
module p03_ps_control_regs (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 s_axi_aclk CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn" *)
    input  wire         s_axi_aclk,

    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 s_axi_aresetn RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input  wire         s_axi_aresetn,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWADDR" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME S_AXI, PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 40, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, SUPPORTS_NARROW_BURST 0, MAX_BURST_LENGTH 1, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1" *)
    input  wire [39:0]  s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWPROT" *)
    input  wire [2:0]   s_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWVALID" *)
    input  wire         s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI AWREADY" *)
    output wire         s_axi_awready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WDATA" *)
    input  wire [31:0]  s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WSTRB" *)
    input  wire [3:0]   s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WVALID" *)
    input  wire         s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI WREADY" *)
    output wire         s_axi_wready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BRESP" *)
    output wire [1:0]   s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output wire         s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BREADY" *)
    input  wire         s_axi_bready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARADDR" *)
    input  wire [39:0]  s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARPROT" *)
    input  wire [2:0]   s_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARVALID" *)
    input  wire         s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI ARREADY" *)
    output wire         s_axi_arready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RDATA" *)
    output wire [31:0]  s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output wire [1:0]   s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output wire         s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input  wire         s_axi_rready,

    // Page command/status.
    output reg          page_start,
    output reg          page_out,
    output reg          page_mutable_only,
    output reg  [1:0]   page_context_slot,
    output reg  [63:0]  page_record_base,
    input  wire         page_busy,
    input  wire         page_done,
    input  wire         page_start_blocked,
    input  wire [31:0]  page_bytes_transferred,
    input  wire [31:0]  page_completed_transfers,
    input  wire [63:0]  page_last_transfer_cycles,
    input  wire         page_error_command,
    input  wire         page_error_host,
    input  wire         page_error_ddr,
    input  wire [31:0]  page_completed_read_bursts,
    input  wire [31:0]  page_completed_write_bursts,
    input  wire [63:0]  page_axi_bytes_moved,
    input  wire         page_protocol_error,
    input  wire         page_range_error,
    input  wire [8:0]   page_pending_write_bytes,

    // Dispatch command/status.
    output reg          dispatch_start,
    output reg  [1:0]   dispatch_context_slot,
    output reg  [63:0]  dispatch_metadata,
    output reg  [31:0]  dispatch_timestep,
    output reg          dispatch_event_read_bank,
    input  wire         dispatch_busy,
    input  wire         dispatch_done,
    input  wire         dispatch_start_blocked,
    input  wire [1:0]   dispatch_active_context_slot,
    input  wire [6:0]   dispatch_active_logical_core_id,
    input  wire         dispatch_active_event_bank,
    input  wire [12:0]  dispatch_packet_count,
    input  wire [31:0]  dispatch_core_status,
    input  wire [31:0]  dispatch_completed,
    input  wire [63:0]  dispatch_last_cycles,
    input  wire         dispatch_error_metadata,
    input  wire         dispatch_error_packet_overflow,
    input  wire         dispatch_error_core_status,
    input  wire         dispatch_memory_address_error,

    // Low-rate resident-memory command/status.
    output reg          debug_req,
    output reg          debug_write,
    output reg  [1:0]   debug_context_slot,
    output reg  [3:0]   debug_bank,
    output reg  [14:0]  debug_addr,
    output reg  [255:0] debug_wdata,
    input  wire         debug_busy,
    input  wire         debug_ack,
    input  wire         debug_rvalid,
    input  wire         debug_error,
    input  wire [255:0] debug_rdata
);

    localparam [31:0] P03_MMIO_ID = 32'h4C54_3302; // "LT3" + P03.2
    localparam [31:0] P03_MMIO_VERSION = 32'h0001_0000;
    // Temporary P03.2c physical diagnostic: if a read reaches this slave but
    // misses every defined register/window, return a recognizable signature
    // carrying the received low 12 address bits instead of an ambiguous zero.
    localparam [31:0] P03_MMIO_UNMAPPED_SIGNATURE = 32'hD1A6_0000;

    // Register byte offsets.
    localparam [11:0] REG_ID                   = 12'h000;
    localparam [11:0] REG_VERSION              = 12'h004;
    localparam [11:0] REG_CAPABILITIES         = 12'h008;
    localparam [11:0] REG_GLOBAL_STATUS        = 12'h00C;

    localparam [11:0] REG_PAGE_CONFIG          = 12'h020;
    localparam [11:0] REG_PAGE_BASE_LO         = 12'h024;
    localparam [11:0] REG_PAGE_BASE_HI         = 12'h028;
    localparam [11:0] REG_PAGE_COMMAND         = 12'h02C;
    localparam [11:0] REG_PAGE_STATUS          = 12'h030;
    localparam [11:0] REG_PAGE_BYTES           = 12'h034;
    localparam [11:0] REG_PAGE_COMPLETED       = 12'h038;
    localparam [11:0] REG_PAGE_CYCLES_LO       = 12'h03C;
    localparam [11:0] REG_PAGE_CYCLES_HI       = 12'h040;
    localparam [11:0] REG_PAGE_READ_BURSTS     = 12'h044;
    localparam [11:0] REG_PAGE_WRITE_BURSTS    = 12'h048;
    localparam [11:0] REG_PAGE_AXI_BYTES_LO    = 12'h04C;
    localparam [11:0] REG_PAGE_AXI_BYTES_HI    = 12'h050;
    localparam [11:0] REG_PAGE_PENDING_BYTES   = 12'h054;

    localparam [11:0] REG_DISPATCH_CONFIG      = 12'h080;
    localparam [11:0] REG_DISPATCH_META_LO     = 12'h084;
    localparam [11:0] REG_DISPATCH_META_HI     = 12'h088;
    localparam [11:0] REG_DISPATCH_TIMESTEP    = 12'h08C;
    localparam [11:0] REG_DISPATCH_COMMAND     = 12'h090;
    localparam [11:0] REG_DISPATCH_STATUS      = 12'h094;
    localparam [11:0] REG_DISPATCH_PACKET_CNT  = 12'h098;
    localparam [11:0] REG_DISPATCH_CORE_STATUS = 12'h09C;
    localparam [11:0] REG_DISPATCH_COMPLETED   = 12'h0A0;
    localparam [11:0] REG_DISPATCH_CYCLES_LO   = 12'h0A4;
    localparam [11:0] REG_DISPATCH_CYCLES_HI   = 12'h0A8;
    localparam [11:0] REG_DISPATCH_ACTIVE      = 12'h0AC;

    localparam [11:0] REG_DEBUG_CONFIG         = 12'h100;
    localparam [11:0] REG_DEBUG_ADDR           = 12'h104;
    localparam [11:0] REG_DEBUG_COMMAND        = 12'h108;
    localparam [11:0] REG_DEBUG_STATUS         = 12'h10C;
    localparam [11:0] REG_DEBUG_WDATA0         = 12'h110;
    localparam [11:0] REG_DEBUG_RDATA0         = 12'h130;

    reg aw_pending;
    reg [39:0] awaddr_q;
    reg w_pending;
    reg [31:0] wdata_q;
    reg [3:0] wstrb_q;
    reg bvalid_q;
    reg rvalid_q;
    reg [31:0] rdata_q;

    reg page_done_latched;
    reg page_start_blocked_latched;
    reg dispatch_done_latched;
    reg dispatch_start_blocked_latched;

    reg debug_done_latched;
    reg debug_rvalid_latched;
    reg debug_error_latched;
    reg debug_start_blocked_latched;
    reg [255:0] debug_rdata_latched;

    wire page_any_error =
        page_error_command || page_error_host || page_error_ddr ||
        page_protocol_error || page_range_error;
    wire dispatch_any_error =
        dispatch_error_metadata || dispatch_error_packet_overflow ||
        dispatch_error_core_status || dispatch_memory_address_error;
    wire debug_any_error = debug_error_latched || debug_start_blocked_latched;

    wire write_fire = aw_pending && w_pending && !bvalid_q;
    wire [11:0] write_addr = {awaddr_q[11:2], 2'b00};

    assign s_axi_awready = !aw_pending && !bvalid_q;
    assign s_axi_wready = !w_pending && !bvalid_q;
    assign s_axi_bresp = 2'b00;
    assign s_axi_bvalid = bvalid_q;

    assign s_axi_arready = !rvalid_q;
    assign s_axi_rdata = rdata_q;
    assign s_axi_rresp = 2'b00;
    assign s_axi_rvalid = rvalid_q;

    wire unused_axi_prot = ^{s_axi_awprot, s_axi_arprot};

    function [31:0] apply_wstrb32;
        input [31:0] old_value;
        input [31:0] new_value;
        input [3:0] strobe;
        integer byte_index;
        begin
            apply_wstrb32 = old_value;
            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1) begin
                if (strobe[byte_index])
                    apply_wstrb32[byte_index*8 +: 8] =
                        new_value[byte_index*8 +: 8];
            end
        end
    endfunction

    function [31:0] read_register;
        input [11:0] addr;
        reg [31:0] value;
        integer word_index;
        begin
            value = 32'd0;
            case ({addr[11:2], 2'b00})
                REG_ID: value = P03_MMIO_ID;
                REG_VERSION: value = P03_MMIO_VERSION;
                REG_CAPABILITIES: begin
                    value[0] = 1'b1; // page command
                    value[1] = 1'b1; // dispatch command
                    value[2] = 1'b1; // resident-memory command
                    value[3] = 1'b1; // 64-bit DDR address
                    value[4] = 1'b1; // 256-bit resident data
                    value[10:8] = 3'd3; // resident slots
                    value[23:16] = 8'd1; // physical engines
                end
                REG_GLOBAL_STATUS: begin
                    value[0] = page_busy;
                    value[1] = dispatch_busy;
                    value[2] = debug_busy || debug_req;
                    value[3] = page_any_error;
                    value[4] = dispatch_any_error;
                    value[5] = debug_any_error;
                end

                REG_PAGE_CONFIG: begin
                    value[0] = page_out;
                    value[1] = page_mutable_only;
                    value[9:8] = page_context_slot;
                end
                REG_PAGE_BASE_LO: value = page_record_base[31:0];
                REG_PAGE_BASE_HI: value = page_record_base[63:32];
                REG_PAGE_STATUS: begin
                    value[0] = page_busy;
                    value[1] = page_done_latched;
                    value[2] = page_start_blocked_latched;
                    value[3] = page_error_command;
                    value[4] = page_error_host;
                    value[5] = page_error_ddr;
                    value[6] = page_protocol_error;
                    value[7] = page_range_error;
                end
                REG_PAGE_BYTES: value = page_bytes_transferred;
                REG_PAGE_COMPLETED: value = page_completed_transfers;
                REG_PAGE_CYCLES_LO: value = page_last_transfer_cycles[31:0];
                REG_PAGE_CYCLES_HI: value = page_last_transfer_cycles[63:32];
                REG_PAGE_READ_BURSTS: value = page_completed_read_bursts;
                REG_PAGE_WRITE_BURSTS: value = page_completed_write_bursts;
                REG_PAGE_AXI_BYTES_LO: value = page_axi_bytes_moved[31:0];
                REG_PAGE_AXI_BYTES_HI: value = page_axi_bytes_moved[63:32];
                REG_PAGE_PENDING_BYTES: value = {23'd0, page_pending_write_bytes};

                REG_DISPATCH_CONFIG: begin
                    value[1:0] = dispatch_context_slot;
                    value[8] = dispatch_event_read_bank;
                end
                REG_DISPATCH_META_LO: value = dispatch_metadata[31:0];
                REG_DISPATCH_META_HI: value = dispatch_metadata[63:32];
                REG_DISPATCH_TIMESTEP: value = dispatch_timestep;
                REG_DISPATCH_STATUS: begin
                    value[0] = dispatch_busy;
                    value[1] = dispatch_done_latched;
                    value[2] = dispatch_start_blocked_latched;
                    value[3] = dispatch_error_metadata;
                    value[4] = dispatch_error_packet_overflow;
                    value[5] = dispatch_error_core_status;
                    value[6] = dispatch_memory_address_error;
                end
                REG_DISPATCH_PACKET_CNT: value = {19'd0, dispatch_packet_count};
                REG_DISPATCH_CORE_STATUS: value = dispatch_core_status;
                REG_DISPATCH_COMPLETED: value = dispatch_completed;
                REG_DISPATCH_CYCLES_LO: value = dispatch_last_cycles[31:0];
                REG_DISPATCH_CYCLES_HI: value = dispatch_last_cycles[63:32];
                REG_DISPATCH_ACTIVE: begin
                    value[1:0] = dispatch_active_context_slot;
                    value[8] = dispatch_active_event_bank;
                    value[22:16] = dispatch_active_logical_core_id;
                end

                REG_DEBUG_CONFIG: begin
                    value[0] = debug_write;
                    value[9:8] = debug_context_slot;
                    value[15:12] = debug_bank;
                end
                REG_DEBUG_ADDR: value = {17'd0, debug_addr};
                REG_DEBUG_STATUS: begin
                    value[0] = debug_busy || debug_req;
                    value[1] = debug_done_latched;
                    value[2] = debug_rvalid_latched;
                    value[3] = debug_error_latched;
                    value[4] = debug_start_blocked_latched;
                end
                default: begin
                    if (({addr[11:2], 2'b00} >= REG_DEBUG_WDATA0) &&
                        ({addr[11:2], 2'b00} < REG_DEBUG_WDATA0 + 12'h020)) begin
                        word_index =
                            ({addr[11:2], 2'b00} - REG_DEBUG_WDATA0) >> 2;
                        value = debug_wdata[word_index*32 +: 32];
                    end else if (({addr[11:2], 2'b00} >= REG_DEBUG_RDATA0) &&
                                 ({addr[11:2], 2'b00} < REG_DEBUG_RDATA0 + 12'h020)) begin
                        word_index =
                            ({addr[11:2], 2'b00} - REG_DEBUG_RDATA0) >> 2;
                        value = debug_rdata_latched[word_index*32 +: 32];
                    end else begin
                        value = P03_MMIO_UNMAPPED_SIGNATURE | {20'd0, addr};
                    end
                end
            endcase
            read_register = value;
        end
    endfunction

    integer debug_word_index;
    reg [31:0] merged_value;

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            aw_pending <= 1'b0;
            awaddr_q <= 40'd0;
            w_pending <= 1'b0;
            wdata_q <= 32'd0;
            wstrb_q <= 4'd0;
            bvalid_q <= 1'b0;
            rvalid_q <= 1'b0;
            rdata_q <= 32'd0;

            page_start <= 1'b0;
            page_out <= 1'b0;
            page_mutable_only <= 1'b0;
            page_context_slot <= 2'd0;
            page_record_base <= 64'h0000_0000_4000_0000;
            page_done_latched <= 1'b0;
            page_start_blocked_latched <= 1'b0;

            dispatch_start <= 1'b0;
            dispatch_context_slot <= 2'd0;
            dispatch_metadata <= 64'd0;
            dispatch_timestep <= 32'd0;
            dispatch_event_read_bank <= 1'b0;
            dispatch_done_latched <= 1'b0;
            dispatch_start_blocked_latched <= 1'b0;

            debug_req <= 1'b0;
            debug_write <= 1'b0;
            debug_context_slot <= 2'd0;
            debug_bank <= 4'd0;
            debug_addr <= 15'd0;
            debug_wdata <= 256'd0;
            debug_done_latched <= 1'b0;
            debug_rvalid_latched <= 1'b0;
            debug_error_latched <= 1'b0;
            debug_start_blocked_latched <= 1'b0;
            debug_rdata_latched <= 256'd0;
        end else begin
            page_start <= 1'b0;
            dispatch_start <= 1'b0;

            if (page_done)
                page_done_latched <= 1'b1;
            if (page_start_blocked)
                page_start_blocked_latched <= 1'b1;

            if (dispatch_done)
                dispatch_done_latched <= 1'b1;
            if (dispatch_start_blocked)
                dispatch_start_blocked_latched <= 1'b1;

            // Resident-memory request is level-held until the arbiter's latched
            // response is observed.  This matches the final accepted P02
            // page/debug handshake.
            if (debug_req && debug_ack) begin
                debug_req <= 1'b0;
                debug_done_latched <= 1'b1;
                debug_rvalid_latched <= debug_rvalid;
                debug_error_latched <= debug_error;
                debug_rdata_latched <= debug_rdata;
            end

            if (s_axi_awvalid && s_axi_awready) begin
                aw_pending <= 1'b1;
                awaddr_q <= s_axi_awaddr;
            end
            if (s_axi_wvalid && s_axi_wready) begin
                w_pending <= 1'b1;
                wdata_q <= s_axi_wdata;
                wstrb_q <= s_axi_wstrb;
            end

            if (bvalid_q && s_axi_bready)
                bvalid_q <= 1'b0;

            if (write_fire) begin
                aw_pending <= 1'b0;
                w_pending <= 1'b0;
                bvalid_q <= 1'b1;

                case (write_addr)
                    REG_PAGE_CONFIG: begin
                        merged_value = apply_wstrb32(
                            {22'd0, page_context_slot, 6'd0,
                             page_mutable_only, page_out},
                            wdata_q, wstrb_q
                        );
                        page_out <= merged_value[0];
                        page_mutable_only <= merged_value[1];
                        page_context_slot <= merged_value[9:8];
                    end
                    REG_PAGE_BASE_LO:
                        page_record_base[31:0] <= apply_wstrb32(
                            page_record_base[31:0], wdata_q, wstrb_q
                        );
                    REG_PAGE_BASE_HI:
                        page_record_base[63:32] <= apply_wstrb32(
                            page_record_base[63:32], wdata_q, wstrb_q
                        );
                    REG_PAGE_COMMAND: begin
                        if (wstrb_q[0] && wdata_q[1]) begin
                            page_done_latched <= 1'b0;
                            page_start_blocked_latched <= 1'b0;
                        end
                        if (wstrb_q[0] && wdata_q[0]) begin
                            page_start <= 1'b1;
                            page_done_latched <= 1'b0;
                            page_start_blocked_latched <= 1'b0;
                        end
                    end

                    REG_DISPATCH_CONFIG: begin
                        merged_value = apply_wstrb32(
                            {23'd0, dispatch_event_read_bank, 6'd0,
                             dispatch_context_slot},
                            wdata_q, wstrb_q
                        );
                        dispatch_context_slot <= merged_value[1:0];
                        dispatch_event_read_bank <= merged_value[8];
                    end
                    REG_DISPATCH_META_LO:
                        dispatch_metadata[31:0] <= apply_wstrb32(
                            dispatch_metadata[31:0], wdata_q, wstrb_q
                        );
                    REG_DISPATCH_META_HI:
                        dispatch_metadata[63:32] <= apply_wstrb32(
                            dispatch_metadata[63:32], wdata_q, wstrb_q
                        );
                    REG_DISPATCH_TIMESTEP:
                        dispatch_timestep <= apply_wstrb32(
                            dispatch_timestep, wdata_q, wstrb_q
                        );
                    REG_DISPATCH_COMMAND: begin
                        if (wstrb_q[0] && wdata_q[1]) begin
                            dispatch_done_latched <= 1'b0;
                            dispatch_start_blocked_latched <= 1'b0;
                        end
                        if (wstrb_q[0] && wdata_q[0]) begin
                            dispatch_start <= 1'b1;
                            dispatch_done_latched <= 1'b0;
                            dispatch_start_blocked_latched <= 1'b0;
                        end
                    end

                    REG_DEBUG_CONFIG: begin
                        merged_value = apply_wstrb32(
                            {16'd0, debug_bank, 2'd0, debug_context_slot,
                             7'd0, debug_write},
                            wdata_q, wstrb_q
                        );
                        debug_write <= merged_value[0];
                        debug_context_slot <= merged_value[9:8];
                        debug_bank <= merged_value[15:12];
                    end
                    REG_DEBUG_ADDR: begin
                        merged_value = apply_wstrb32(
                            {17'd0, debug_addr}, wdata_q, wstrb_q
                        );
                        debug_addr <= merged_value[14:0];
                    end
                    REG_DEBUG_COMMAND: begin
                        if (wstrb_q[0] && wdata_q[1]) begin
                            debug_done_latched <= 1'b0;
                            debug_rvalid_latched <= 1'b0;
                            debug_error_latched <= 1'b0;
                            debug_start_blocked_latched <= 1'b0;
                            debug_rdata_latched <= 256'd0;
                        end
                        if (wstrb_q[0] && wdata_q[0]) begin
                            debug_done_latched <= 1'b0;
                            debug_rvalid_latched <= 1'b0;
                            debug_error_latched <= 1'b0;
                            debug_start_blocked_latched <= 1'b0;
                            debug_rdata_latched <= 256'd0;
                            if (!debug_req && !debug_busy) begin
                                debug_req <= 1'b1;
                            end else begin
                                debug_start_blocked_latched <= 1'b1;
                            end
                        end
                    end

                    default: begin
                        if ((write_addr >= REG_DEBUG_WDATA0) &&
                            (write_addr < REG_DEBUG_WDATA0 + 12'h020)) begin
                            debug_word_index =
                                (write_addr - REG_DEBUG_WDATA0) >> 2;
                            merged_value = apply_wstrb32(
                                debug_wdata[debug_word_index*32 +: 32],
                                wdata_q, wstrb_q
                            );
                            debug_wdata[debug_word_index*32 +: 32] <=
                                merged_value;
                        end
                    end
                endcase
            end

            if (rvalid_q && s_axi_rready)
                rvalid_q <= 1'b0;

            if (s_axi_arvalid && s_axi_arready) begin
                rdata_q <= read_register(s_axi_araddr[11:0]);
                rvalid_q <= 1'b1;
            end
        end
    end
endmodule
