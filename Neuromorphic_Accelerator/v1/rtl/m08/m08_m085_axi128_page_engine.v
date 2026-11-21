`timescale 1ns/1ps
// M08.5: 256-byte-only, 128-bit AXI4 page burst master.
// Accelerator-specific single-page staging: 16 beats, full strobes, one
// outstanding burst (read OR write). No general Loihi bank/page walker.
// Data uses little-endian 128-bit lanes: beat 0 = page[127:0].
// UNCONNECTED source candidate: no PS HP0 / DMA / Linux device binding.
// The 2048-bit page is a SNAPSHOT boundary, not a wired M08 resident bank.
// An external owner gate MUST validate the real DDR allocation/lifetime.
// A fault may leave an AXI transaction outstanding: quiesce/reset the entire
// future AXI fabric before reusing memory, NEVER just clear the sticky flag.
module m08_m085_axi128_page_engine #(
    parameter integer MAX_WAIT_CYCLES = 128
)(
    input wire clk,
    input wire resetn,
    input wire req,
    input wire req_write,
    input wire [63:0] req_addr,
    input wire [2047:0] req_write_page,
    input wire owner_lease_active,
    input wire compute_idle,
    input wire page_bank_idle,
    output reg done,
    output reg read_complete,
    output reg error,
    output wire busy,
    output wire poisoned,
    output reg [2047:0] read_page,
    output reg [31:0] completed_read_bursts,
    output reg [31:0] completed_write_bursts,
    output reg [31:0] completed_axi_bytes,

    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWADDR", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME M_AXI, PROTOCOL AXI4, ADDR_WIDTH 49, DATA_WIDTH 128, ID_WIDTH 0, HAS_BURST 1, MAX_BURST_LENGTH 16, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, SUPPORTS_NARROW_BURST 0" *)
    output wire [48:0] m_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWLEN" *)
    output wire [7:0] m_axi_awlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWSIZE" *)
    output wire [2:0] m_axi_awsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWBURST" *)
    output wire [1:0] m_axi_awburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWVALID" *)
    output wire m_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWREADY" *)
    input wire m_axi_awready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WDATA" *)
    output wire [127:0] m_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WSTRB" *)
    output wire [15:0] m_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WLAST" *)
    output wire m_axi_wlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WVALID" *)
    output wire m_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI WREADY" *)
    input wire m_axi_wready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BRESP" *)
    input wire [1:0] m_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BVALID" *)
    input wire m_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BREADY" *)
    output wire m_axi_bready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARADDR" *)
    output wire [48:0] m_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARLEN" *)
    output wire [7:0] m_axi_arlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARSIZE" *)
    output wire [2:0] m_axi_arsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARBURST" *)
    output wire [1:0] m_axi_arburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARVALID" *)
    output wire m_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARREADY" *)
    input wire m_axi_arready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RDATA" *)
    input wire [127:0] m_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RRESP" *)
    input wire [1:0] m_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RLAST" *)
    input wire m_axi_rlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RVALID" *)
    input wire m_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RREADY" *)
    output wire m_axi_rready
);
    localparam [2:0] IDLE=3'd0, AW=3'd1, W=3'd2, B=3'd3,
                     AR=3'd4, R=3'd5, FAULT=3'd6;
    reg [2:0] state;
    reg [48:0] address_q;
    reg [2047:0] write_page_q;
    reg [2047:0] read_staging;
    reg [3:0] beat;
    reg [31:0] wait_count;
    reg armed;
    wire aw_fire=m_axi_awvalid && m_axi_awready;
    wire w_fire=m_axi_wvalid && m_axi_wready;
    wire b_fire=m_axi_bvalid && m_axi_bready;
    wire ar_fire=m_axi_arvalid && m_axi_arready;
    wire r_fire=m_axi_rvalid && m_axi_rready;
    wire progress=aw_fire || w_fire || b_fire || ar_fire || r_fire;
    wire illegal_response =
        (m_axi_bvalid && state!=B) || (m_axi_rvalid && state!=R);
    wire live_owner=owner_lease_active && compute_idle && page_bank_idle;
    wire legal_addr=(!(|req_addr[63:49])) && (req_addr[7:0]==8'd0);
    assign busy=(state!=IDLE && state!=FAULT);
    assign poisoned=(state==FAULT);
    assign m_axi_awaddr=address_q;
    assign m_axi_awlen=8'd15;
    assign m_axi_awsize=3'd4; // 16 bytes per beat
    assign m_axi_awburst=2'b01; // INCR
    assign m_axi_awvalid=(state==AW);
    assign m_axi_wdata=write_page_q[beat*128 +: 128];
    assign m_axi_wstrb=16'hFFFF;
    assign m_axi_wlast=(beat==4'd15);
    assign m_axi_wvalid=(state==W);
    assign m_axi_bready=(state==B);
    assign m_axi_araddr=address_q;
    assign m_axi_arlen=8'd15;
    assign m_axi_arsize=3'd4;
    assign m_axi_arburst=2'b01;
    assign m_axi_arvalid=(state==AR);
    assign m_axi_rready=(state==R);

    always @(posedge clk) begin
        if (!resetn) begin
            state<=IDLE;address_q<=0;write_page_q<=0;
            read_staging<=0;read_page<=0;beat<=0;wait_count<=0;
            armed<=1'b1;done<=0;read_complete<=0;error<=0;
            completed_read_bursts<=0;completed_write_bursts<=0;
            completed_axi_bytes<=0;
        end else begin
            done<=1'b0;
            read_complete<=1'b0;
            error<=1'b0;
            if (!req) armed<=1'b1;
            if (state==FAULT) begin
                // Final result remains faulted; no new AXI handshakes.
                state<=FAULT;
            end else if (illegal_response ||
                         (busy && (!live_owner || (req && armed)))) begin
                state<=FAULT;
                error<=1'b1;
                read_staging<=0;
                read_page<=0;
            end else if (busy && !progress &&
                         (MAX_WAIT_CYCLES<1 ||
                          wait_count>=MAX_WAIT_CYCLES-1)) begin
                state<=FAULT;
                error<=1'b1;
                read_staging<=0;
                read_page<=0;
            end else begin
                if (busy) begin
                    if(progress) wait_count<=0;
                    else wait_count<=wait_count+32'd1;
                end
                case (state)
                    IDLE: if (req && armed) begin
                        armed<=1'b0;
                        if (!live_owner || !legal_addr || MAX_WAIT_CYCLES<1) begin
                            state<=FAULT;
                            error<=1'b1;
                        end else begin
                            address_q<=req_addr[48:0];
                            write_page_q<=req_write_page; // atomic pre-AW/AR snapshot
                            read_staging<=0;read_page<=0;
                            beat<=0;wait_count<=0;
                            state<=req_write ? AW : AR;
                        end
                    end
                    AW: if (aw_fire) begin
                        state<=W;
                        beat<=0;
                    end
                    W: if (w_fire) begin
                        if (beat==4'd15) state<=B;
                        else beat<=beat+4'd1;
                    end
                    B: if (b_fire) begin
                        if (m_axi_bresp!=2'b00) begin
                            state<=FAULT;
                            error<=1'b1;
                            read_page<=0;
                        end else begin
                            state<=IDLE;
                            done<=1'b1;
                            completed_write_bursts<=completed_write_bursts+32'd1;
                            completed_axi_bytes<=completed_axi_bytes+32'd256;
                        end
                    end
                    AR: if (ar_fire) begin
                        state<=R;
                        beat<=0;
                    end
                    R: if (r_fire) begin
                        if (m_axi_rresp!=2'b00 ||
                            m_axi_rlast!=(beat==4'd15)) begin
                            state<=FAULT;
                            error<=1'b1;
                            read_staging<=0;
                            read_page<=0;
                        end else if (beat==4'd15) begin
                            read_page<={m_axi_rdata,read_staging[1919:0]};
                            state<=IDLE;
                            done<=1'b1;
                            read_complete<=1'b1;
                            completed_read_bursts<=completed_read_bursts+32'd1;
                            completed_axi_bytes<=completed_axi_bytes+32'd256;
                        end else begin
                            read_staging[beat*128 +:128]<=m_axi_rdata;
                            beat<=beat+4'd1;
                        end
                    end
                    default: begin state<=FAULT;error<=1'b1;end
                endcase
            end
        end
    end
endmodule
