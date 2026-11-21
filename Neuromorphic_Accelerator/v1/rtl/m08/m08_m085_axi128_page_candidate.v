`timescale 1ns/1ps
// Source-only M08.5 composition: independent range/lease/page/tick admission
// plus first-party actual 128-bit AXI4 burst handshake engine.
// The 2048-bit payload is a deliberately EXTERNAL snapshot boundary;
// it is NOT connected to the existing m08_host_staged_page_bank and no
// PS S_AXI_HP0_FPD endpoint / DMA buffer exists in this candidate.
// Both admission and AXI transport default to no enabled DDR window.
module m08_m085_axi128_page_candidate #(
    parameter [63:0] WINDOW_BEGIN=64'd0,
    parameter [63:0] WINDOW_END=64'd0,
    parameter integer GUARD_WAIT_CYCLES=4096,
    parameter integer AXI_STALL_CYCLES=128,
    parameter integer LOGICAL_PAGES=6
)(
    input wire clk,
    input wire resetn,
    input wire owner_lease_active,
    input wire compute_idle,
    input wire page_bank_idle,
    input wire req,
    input wire req_write,
    input wire [63:0] req_addr,
    input wire [15:0] req_size_bytes,
    input wire [31:0] req_logical_page,
    input wire [31:0] req_tick,
    input wire [2047:0] req_write_page,
    output wire ack,
    output wire error,
    output wire busy,
    output wire poisoned,
    output wire [31:0] completed_page,
    output wire [31:0] completed_tick,
    output wire completed_write,
    output wire [31:0] completed_page_transfers,
    output wire read_page_valid,
    output wire [2047:0] read_page_data,
    output wire [31:0] completed_axi_read_bursts,
    output wire [31:0] completed_axi_write_bursts,
    output wire [31:0] completed_axi_bytes,
    output wire [0:0] m_axi_awid,
    output wire [48:0] m_axi_awaddr,
    output wire [7:0] m_axi_awlen,
    output wire [2:0] m_axi_awsize,
    output wire [1:0] m_axi_awburst,
    output wire m_axi_awlock,
    output wire [3:0] m_axi_awcache,
    output wire [2:0] m_axi_awprot,
    output wire [3:0] m_axi_awqos,
    output wire m_axi_awvalid,
    input wire m_axi_awready,
    output wire [127:0] m_axi_wdata,
    output wire [15:0] m_axi_wstrb,
    output wire m_axi_wlast,
    output wire m_axi_wvalid,
    input wire m_axi_wready,
    input wire [0:0] m_axi_bid,
    input wire [1:0] m_axi_bresp,
    input wire m_axi_bvalid,
    output wire m_axi_bready,
    output wire [0:0] m_axi_arid,
    output wire [48:0] m_axi_araddr,
    output wire [7:0] m_axi_arlen,
    output wire [2:0] m_axi_arsize,
    output wire [1:0] m_axi_arburst,
    output wire m_axi_arlock,
    output wire [3:0] m_axi_arcache,
    output wire [2:0] m_axi_arprot,
    output wire [3:0] m_axi_arqos,
    output wire m_axi_arvalid,
    input wire m_axi_arready,
    input wire [0:0] m_axi_rid,
    input wire [127:0] m_axi_rdata,
    input wire [1:0] m_axi_rresp,
    input wire m_axi_rlast,
    input wire m_axi_rvalid,
    output wire m_axi_rready
);
    wire forward_req,forward_write;
    wire [63:0] forward_addr;
    wire [15:0] forward_size_bytes;
    wire [31:0] forward_logical_page,forward_tick;
    wire engine_done,engine_read_complete,engine_error;
    wire engine_poisoned,engine_busy;
    wire [2047:0] engine_read_page;
    reg [2047:0] staged_write_page;
    wire guard_busy,guard_poisoned;
    // Latch the full page at acceptance. If the caller modifies its inputs
    // while AXI is stalled, all 16 W beats retain their accepted data.
    always @(posedge clk) begin
        if (!resetn) staged_write_page<=0;
        else if (req && !guard_busy && !guard_poisoned)
            staged_write_page<=req_write_page;
    end

    m08_m085_ddr_page_admission #(
        .WINDOW_BEGIN(WINDOW_BEGIN),.WINDOW_END(WINDOW_END),
        .MAX_WAIT_CYCLES(GUARD_WAIT_CYCLES),
        .LOGICAL_PAGES(LOGICAL_PAGES),.LOGICAL_TICKS(4)
    ) admission(
        .clk(clk),.resetn(resetn),
        .owner_lease_active(owner_lease_active),
        .compute_idle(compute_idle),.page_bank_idle(page_bank_idle),
        .req(req),.req_write(req_write),.req_addr(req_addr),
        .req_size_bytes(req_size_bytes),.req_logical_page(req_logical_page),
        .req_tick(req_tick),.forward_req(forward_req),
        .forward_write(forward_write),.forward_addr(forward_addr),
        .forward_size_bytes(forward_size_bytes),
        .forward_logical_page(forward_logical_page),
        .forward_tick(forward_tick),.downstream_done(engine_done),
        .downstream_error(engine_error || engine_poisoned),
        .downstream_rvalid(engine_read_complete),.ack(ack),.error(error),
        .busy(guard_busy),.poisoned(guard_poisoned),
        .completed_page(completed_page),.completed_tick(completed_tick),
        .completed_write(completed_write),
        .completed_page_transfers(completed_page_transfers)
    );

    m08_m085_axi128_page_engine #(
        .MAX_WAIT_CYCLES(AXI_STALL_CYCLES)
    ) engine(
        .clk(clk),.resetn(resetn),.req(forward_req),
        .req_write(forward_write),.req_addr(forward_addr),
        .req_write_page(staged_write_page),
        // A guard-level poison must also quarantine any outstanding AXI
        // burst before it can issue another beat or accept completion.
        .owner_lease_active(owner_lease_active && !guard_poisoned),
        .compute_idle(compute_idle),.page_bank_idle(page_bank_idle),
        .done(engine_done),.read_complete(engine_read_complete),
        .error(engine_error),.busy(engine_busy),
        .poisoned(engine_poisoned),.read_page(engine_read_page),
        .completed_read_bursts(completed_axi_read_bursts),
        .completed_write_bursts(completed_axi_write_bursts),
        .completed_axi_bytes(completed_axi_bytes),
        .m_axi_awid(m_axi_awid),.m_axi_awaddr(m_axi_awaddr),.m_axi_awlen(m_axi_awlen),
        .m_axi_awsize(m_axi_awsize),.m_axi_awburst(m_axi_awburst),
        .m_axi_awlock(m_axi_awlock),.m_axi_awcache(m_axi_awcache),
        .m_axi_awprot(m_axi_awprot),.m_axi_awqos(m_axi_awqos),
        .m_axi_awvalid(m_axi_awvalid),.m_axi_awready(m_axi_awready),
        .m_axi_wdata(m_axi_wdata),.m_axi_wstrb(m_axi_wstrb),
        .m_axi_wlast(m_axi_wlast),.m_axi_wvalid(m_axi_wvalid),
        .m_axi_wready(m_axi_wready),.m_axi_bid(m_axi_bid),
        .m_axi_bresp(m_axi_bresp),
        .m_axi_bvalid(m_axi_bvalid),.m_axi_bready(m_axi_bready),
        .m_axi_arid(m_axi_arid),.m_axi_araddr(m_axi_araddr),.m_axi_arlen(m_axi_arlen),
        .m_axi_arsize(m_axi_arsize),.m_axi_arburst(m_axi_arburst),
        .m_axi_arlock(m_axi_arlock),.m_axi_arcache(m_axi_arcache),
        .m_axi_arprot(m_axi_arprot),.m_axi_arqos(m_axi_arqos),
        .m_axi_arvalid(m_axi_arvalid),.m_axi_arready(m_axi_arready),
        .m_axi_rid(m_axi_rid),.m_axi_rdata(m_axi_rdata),.m_axi_rresp(m_axi_rresp),
        .m_axi_rlast(m_axi_rlast),.m_axi_rvalid(m_axi_rvalid),
        .m_axi_rready(m_axi_rready)
    );
    assign busy=guard_busy || engine_busy;
    assign poisoned=guard_poisoned || engine_poisoned;
    assign read_page_valid=ack && !completed_write && !poisoned;
    assign read_page_data=read_page_valid ? engine_read_page : 2048'd0;
endmodule
