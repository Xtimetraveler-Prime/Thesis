`timescale 1ns/1ps

// FPGA-v3 P02.3b1 scalar-to-AXI burst coalescer.
//
// The accepted P02.3a page walker emits one semantically exact DDR transaction
// per resident-memory word (4, 8, 16, or 32 bytes).  This adapter preserves that
// request/response contract while transporting DDR traffic through 128-bit AXI4
// bursts.
//
// Layout-specific invariant used here:
//   - every P02 payload bank starts on a 4 KiB boundary;
//   - every P02 payload bank size is an integer multiple of 256 bytes.
//
// Therefore every page-walker bank stream can be partitioned exactly into
// 256-byte chunks. Each chunk maps to one 16-beat x 128-bit AXI4 INCR burst
// without crossing a 4 KiB boundary.
//
// Reads use a 256-byte prefetch cache. Writes coalesce sequential scalar writes
// until exactly 256 bytes are buffered, then commit one 16-beat AXI burst. The
// scalar request that completes a write burst is acknowledged only after the
// AXI B response, so burst errors are visible to the page walker.
module p02_axi128_burst_adapter (
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 clk CLK" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME clk, ASSOCIATED_BUSIF M_AXI, ASSOCIATED_RESET resetn, FREQ_HZ 100000000" *)
    input  wire         clk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 resetn RST" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME resetn, POLARITY ACTIVE_LOW" *)
    input  wire         resetn,

    // Scalar request side (P02.3a walker contract).
    input  wire         req,
    input  wire         req_write,
    input  wire [63:0]  req_addr,
    input  wire [5:0]   req_size_bytes,
    input  wire [255:0] req_wdata,
    output wire         busy,
    output reg          ack,
    output reg          rvalid,
    output reg          error,
    output reg  [255:0] rdata,

    // Observability.
    output reg  [31:0]  completed_read_bursts,
    output reg  [31:0]  completed_write_bursts,
    output reg  [63:0]  axi_bytes_moved,
    output wire [8:0]   pending_write_bytes,
    output reg          protocol_error,

    // AXI4 master, 128-bit data, one outstanding transaction.
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWID" *)
    (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME M_AXI, PROTOCOL AXI4, ADDR_WIDTH 49, DATA_WIDTH 128, ID_WIDTH 1, HAS_BURST 1, MAX_BURST_LENGTH 16, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, SUPPORTS_NARROW_BURST 0" *)
    output wire [0:0]   m_axi_awid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWADDR" *)
    output wire [48:0]  m_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWLEN" *)
    output wire [7:0]   m_axi_awlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWSIZE" *)
    output wire [2:0]   m_axi_awsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWBURST" *)
    output wire [1:0]   m_axi_awburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWLOCK" *)
    output wire         m_axi_awlock,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWCACHE" *)
    output wire [3:0]   m_axi_awcache,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWPROT" *)
    output wire [2:0]   m_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWQOS" *)
    output wire [3:0]   m_axi_awqos,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWVALID" *)
    output wire         m_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWREADY" *)
    input  wire         m_axi_awready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WDATA" *)
    output wire [127:0] m_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WSTRB" *)
    output wire [15:0]  m_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WLAST" *)
    output wire         m_axi_wlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WVALID" *)
    output wire         m_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WREADY" *)
    input  wire         m_axi_wready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BID" *)
    input  wire [0:0]   m_axi_bid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BRESP" *)
    input  wire [1:0]   m_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BVALID" *)
    input  wire         m_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BREADY" *)
    output wire         m_axi_bready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARID" *)
    output wire [0:0]   m_axi_arid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARADDR" *)
    output wire [48:0]  m_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARLEN" *)
    output wire [7:0]   m_axi_arlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARSIZE" *)
    output wire [2:0]   m_axi_arsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARBURST" *)
    output wire [1:0]   m_axi_arburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARLOCK" *)
    output wire         m_axi_arlock,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARCACHE" *)
    output wire [3:0]   m_axi_arcache,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARPROT" *)
    output wire [2:0]   m_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARQOS" *)
    output wire [3:0]   m_axi_arqos,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARVALID" *)
    output wire         m_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARREADY" *)
    input  wire         m_axi_arready,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RID" *)
    input  wire [0:0]   m_axi_rid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RDATA" *)
    input  wire [127:0] m_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RRESP" *)
    input  wire [1:0]   m_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RLAST" *)
    input  wire         m_axi_rlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RVALID" *)
    input  wire         m_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RREADY" *)
    output wire         m_axi_rready
);
    localparam [2:0] ST_IDLE       = 3'd0;
    localparam [2:0] ST_READ_AR    = 3'd1;
    localparam [2:0] ST_READ_DATA  = 3'd2;
    localparam [2:0] ST_READ_REPLY = 3'd3;
    localparam [2:0] ST_WRITE_AW   = 3'd4;
    localparam [2:0] ST_WRITE_DATA = 3'd5;
    localparam [2:0] ST_WRITE_RESP = 3'd6;

    reg [2:0] state;

    reg [2047:0] read_cache;
    reg          read_cache_valid;
    reg [63:0]   read_cache_base;
    reg [4:0]    read_beat_index;
    reg          read_error_seen;

    reg [63:0] pending_read_addr;
    reg [5:0]  pending_read_size;

    reg [2047:0] write_buffer;
    reg [63:0]   write_buffer_base;
    reg [8:0]    write_buffer_bytes;
    reg [4:0]    write_beat_index;

    assign busy = (state != ST_IDLE);
    assign pending_write_bytes = write_buffer_bytes;

    function request_size_valid;
        input [5:0] size_bytes;
        begin
            case (size_bytes)
                6'd4, 6'd8, 6'd16, 6'd32: request_size_valid = 1'b1;
                default: request_size_valid = 1'b0;
            endcase
        end
    endfunction

    function request_alignment_valid;
        input [63:0] address;
        input [5:0] size_bytes;
        begin
            case (size_bytes)
                6'd4: request_alignment_valid = (address[1:0] == 2'b00);
                6'd8: request_alignment_valid = (address[2:0] == 3'b000);
                6'd16: request_alignment_valid = (address[3:0] == 4'b0000);
                6'd32: request_alignment_valid = (address[4:0] == 5'b00000);
                default: request_alignment_valid = 1'b0;
            endcase
        end
    endfunction

    wire request_basic_valid =
        request_size_valid(req_size_bytes) &&
        request_alignment_valid(req_addr, req_size_bytes) &&
        (req_addr[63:49] == 15'd0);

    wire [63:0] read_request_end = req_addr + req_size_bytes;
    wire read_cache_hit =
        read_cache_valid &&
        (req_addr >= read_cache_base) &&
        (read_request_end <= (read_cache_base + 64'd256));

    wire [8:0] read_cache_offset = req_addr[7:0];
    wire [8:0] pending_read_cache_offset = pending_read_addr[7:0];

    reg [8:0] next_write_bytes;
    always @* begin
        next_write_bytes = write_buffer_bytes + req_size_bytes;
    end

    // Fixed AXI burst geometry: 16 beats x 16 bytes = 256 bytes.
    assign m_axi_awid = 1'b0;
    assign m_axi_awaddr = write_buffer_base[48:0];
    assign m_axi_awlen = 8'd15;
    assign m_axi_awsize = 3'd4;
    assign m_axi_awburst = 2'b01;
    assign m_axi_awlock = 1'b0;
    assign m_axi_awcache = 4'b0011;
    assign m_axi_awprot = 3'b000;
    assign m_axi_awqos = 4'b0000;
    assign m_axi_awvalid = (state == ST_WRITE_AW);

    assign m_axi_wdata = write_buffer[(write_beat_index * 128) +: 128];
    assign m_axi_wstrb = 16'hFFFF;
    assign m_axi_wlast = (write_beat_index == 5'd15);
    assign m_axi_wvalid = (state == ST_WRITE_DATA);
    assign m_axi_bready = (state == ST_WRITE_RESP);

    assign m_axi_arid = 1'b0;
    assign m_axi_araddr = read_cache_base[48:0];
    assign m_axi_arlen = 8'd15;
    assign m_axi_arsize = 3'd4;
    assign m_axi_arburst = 2'b01;
    assign m_axi_arlock = 1'b0;
    assign m_axi_arcache = 4'b0011;
    assign m_axi_arprot = 3'b000;
    assign m_axi_arqos = 4'b0000;
    assign m_axi_arvalid = (state == ST_READ_AR);
    assign m_axi_rready = (state == ST_READ_DATA);

    task return_read_data;
        input [8:0] cache_offset;
        input [5:0] size_bytes;
        begin
            rdata <= 256'd0;
            case (size_bytes)
                6'd4:
                    rdata[31:0] <= read_cache[(cache_offset * 8) +: 32];
                6'd8:
                    rdata[63:0] <= read_cache[(cache_offset * 8) +: 64];
                6'd16:
                    rdata[127:0] <= read_cache[(cache_offset * 8) +: 128];
                6'd32:
                    rdata <= read_cache[(cache_offset * 8) +: 256];
                default:
                    rdata <= 256'd0;
            endcase
        end
    endtask

    task append_write_data;
        input [8:0] buffer_offset;
        input [5:0] size_bytes;
        input [255:0] data;
        begin
            case (size_bytes)
                6'd4:
                    write_buffer[(buffer_offset * 8) +: 32] <= data[31:0];
                6'd8:
                    write_buffer[(buffer_offset * 8) +: 64] <= data[63:0];
                6'd16:
                    write_buffer[(buffer_offset * 8) +: 128] <= data[127:0];
                6'd32:
                    write_buffer[(buffer_offset * 8) +: 256] <= data;
                default: begin end
            endcase
        end
    endtask

    always @(posedge clk) begin
        if (!resetn) begin
            state <= ST_IDLE;
            read_cache <= 2048'd0;
            read_cache_valid <= 1'b0;
            read_cache_base <= 64'd0;
            read_beat_index <= 5'd0;
            read_error_seen <= 1'b0;
            pending_read_addr <= 64'd0;
            pending_read_size <= 6'd0;

            write_buffer <= 2048'd0;
            write_buffer_base <= 64'd0;
            write_buffer_bytes <= 9'd0;
            write_beat_index <= 5'd0;

            ack <= 1'b0;
            rvalid <= 1'b0;
            error <= 1'b0;
            rdata <= 256'd0;

            completed_read_bursts <= 32'd0;
            completed_write_bursts <= 32'd0;
            axi_bytes_moved <= 64'd0;
            protocol_error <= 1'b0;
        end else begin
            ack <= 1'b0;
            rvalid <= 1'b0;
            error <= 1'b0;

            case (state)
                ST_IDLE: begin
                    if (req) begin
                        if (!request_basic_valid) begin
                            ack <= 1'b1;
                            error <= 1'b1;
                            protocol_error <= 1'b1;
                        end else if (!req_write) begin
                            if (write_buffer_bytes != 0) begin
                                ack <= 1'b1;
                                error <= 1'b1;
                                protocol_error <= 1'b1;
                            end else if (read_cache_hit) begin
                                return_read_data(read_cache_offset, req_size_bytes);
                                ack <= 1'b1;
                                rvalid <= 1'b1;
                            end else begin
                                pending_read_addr <= req_addr;
                                pending_read_size <= req_size_bytes;
                                read_cache_base <= {req_addr[63:8], 8'd0};
                                read_cache_valid <= 1'b0;
                                read_beat_index <= 5'd0;
                                read_error_seen <= 1'b0;
                                state <= ST_READ_AR;
                            end
                        end else begin
                            // Writes invalidate prefetched read data.
                            read_cache_valid <= 1'b0;

                            if (write_buffer_bytes == 0) begin
                                if (req_addr[7:0] != 8'd0) begin
                                    ack <= 1'b1;
                                    error <= 1'b1;
                                    protocol_error <= 1'b1;
                                end else begin
                                    write_buffer_base <= req_addr;
                                    append_write_data(9'd0, req_size_bytes, req_wdata);
                                    write_buffer_bytes <= req_size_bytes;
                                    if (req_size_bytes == 6'd32 ||
                                        req_size_bytes == 6'd16 ||
                                        req_size_bytes == 6'd8 ||
                                        req_size_bytes == 6'd4) begin
                                        // First scalar request cannot fill 256 B.
                                        ack <= 1'b1;
                                    end
                                end
                            end else if (
                                req_addr !=
                                (write_buffer_base + write_buffer_bytes)
                            ) begin
                                ack <= 1'b1;
                                error <= 1'b1;
                                protocol_error <= 1'b1;
                            end else if (next_write_bytes > 9'd256) begin
                                ack <= 1'b1;
                                error <= 1'b1;
                                protocol_error <= 1'b1;
                            end else begin
                                append_write_data(
                                    write_buffer_bytes,
                                    req_size_bytes,
                                    req_wdata
                                );
                                if (next_write_bytes == 9'd256) begin
                                    write_buffer_bytes <= 9'd256;
                                    write_beat_index <= 5'd0;
                                    // Hold this scalar acknowledgement until
                                    // the AXI B response makes the whole burst
                                    // durable/failed as one transport unit.
                                    state <= ST_WRITE_AW;
                                end else begin
                                    write_buffer_bytes <= next_write_bytes;
                                    ack <= 1'b1;
                                end
                            end
                        end
                    end
                end

                ST_READ_AR: begin
                    if (m_axi_arready)
                        state <= ST_READ_DATA;
                end

                ST_READ_DATA: begin
                    if (m_axi_rvalid) begin
                        read_cache[(read_beat_index * 128) +: 128]
                            <= m_axi_rdata;

                        if (m_axi_rid != 1'b0 ||
                            m_axi_rresp != 2'b00)
                            read_error_seen <= 1'b1;

                        if (m_axi_rlast != (read_beat_index == 5'd15)) begin
                            read_error_seen <= 1'b1;
                            protocol_error <= 1'b1;
                        end

                        if (m_axi_rlast || read_beat_index == 5'd15) begin
                            if (
                                !(read_error_seen ||
                                  (m_axi_rid != 1'b0) ||
                                  (m_axi_rresp != 2'b00) ||
                                  (m_axi_rlast != 1'b1))
                            ) begin
                                read_cache_valid <= 1'b1;
                                completed_read_bursts
                                    <= completed_read_bursts + 32'd1;
                                axi_bytes_moved <= axi_bytes_moved + 64'd256;
                            end
                            state <= ST_READ_REPLY;
                        end else begin
                            read_beat_index <= read_beat_index + 5'd1;
                        end
                    end
                end

                ST_READ_REPLY: begin
                    ack <= 1'b1;
                    if (read_error_seen || !read_cache_valid) begin
                        error <= 1'b1;
                    end else begin
                        return_read_data(
                            pending_read_cache_offset,
                            pending_read_size
                        );
                        rvalid <= 1'b1;
                    end
                    state <= ST_IDLE;
                end

                ST_WRITE_AW: begin
                    if (m_axi_awready)
                        state <= ST_WRITE_DATA;
                end

                ST_WRITE_DATA: begin
                    if (m_axi_wready) begin
                        if (write_beat_index == 5'd15) begin
                            state <= ST_WRITE_RESP;
                        end else begin
                            write_beat_index <= write_beat_index + 5'd1;
                        end
                    end
                end

                ST_WRITE_RESP: begin
                    if (m_axi_bvalid) begin
                        ack <= 1'b1;
                        write_buffer_bytes <= 9'd0;
                        write_beat_index <= 5'd0;

                        if (m_axi_bid != 1'b0 ||
                            m_axi_bresp != 2'b00) begin
                            error <= 1'b1;
                        end else begin
                            completed_write_bursts
                                <= completed_write_bursts + 32'd1;
                            axi_bytes_moved <= axi_bytes_moved + 64'd256;
                        end
                        state <= ST_IDLE;
                    end
                end

                default: begin
                    state <= ST_IDLE;
                    ack <= 1'b1;
                    error <= 1'b1;
                    protocol_error <= 1'b1;
                    read_cache_valid <= 1'b0;
                    write_buffer_bytes <= 9'd0;
                end
            endcase
        end
    end
endmodule
