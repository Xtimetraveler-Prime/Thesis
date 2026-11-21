`timescale 1ns/1ps
// M08.5 SYNTHESIZABLE SOURCE-ONLY AXI4-Lite + CSR + original signed16 LIF.
// This top routes load/dispatch/save commands ONLY from its versioned
// AXI-Lite work register window (0x24...0x34); there are NO external page,
// compute or arbitrary DDR address request pins. The original signed16 LIF,
// one 64-word bank and 7-slot AXI4 DMA source engine are unchanged. External
// kernel owner, physical PS port, driver, protected firmware and real drain
// are NOT implemented. AWPROT/WSTRB is NOT privilege authentication.
// No Vivado PS/HPM0/HP0, IRQ, DMA-API, IOMMU, or KV260 is connected.
// Only base + transport-slot*256 drives AXI DDR addresses, never caller DDR.
// STOP and partial AXI-Lite writes immediately embargo new page/compute.
// A still-outstanding AXI transaction after timeout needs real isolation;
// this source top may NOT authorize memory freeing or physical reprogramming.
module m08_m085_axil_managed_neural_candidate #(
    parameter integer GUARD_WAIT_CYCLES=4096,
    parameter integer AXI_STALL_CYCLES=128,
    parameter integer HOST_WAIT_CYCLES=128,
    parameter integer WORK_TIMEOUT_CYCLES=8192
)(
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 clk CLK", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME clk, ASSOCIATED_BUSIF S_AXI:M_AXI, ASSOCIATED_RESET resetn" *)
    input wire clk,
    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 resetn RST", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME resetn, POLARITY ACTIVE_LOW" *)
    input wire resetn,
    output wire done,
    output wire error,
    output wire busy,
    output wire poisoned,
    output wire completed_save,
    output wire [2:0] bank_phase,
    output wire bank_dirty,
    output wire bank_valid,
    output wire [31:0] bank_logical,
    output wire [8:0] bank_loaded_bytes,
    output wire [31:0] axi_bytes_completed_in_simulation,
    output wire dispatch_accept,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWID", X_INTERFACE_PARAMETER = "XIL_INTERFACENAME M_AXI, PROTOCOL AXI4, DATA_WIDTH 128, ADDR_WIDTH 49, ID_WIDTH 1, HAS_BURST 1, MAX_BURST_LENGTH 16, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, SUPPORTS_NARROW_BURST 0" *)
    output wire [0:0] m_axi_awid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWADDR" *)
    output wire [48:0] m_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWLEN" *)
    output wire [7:0] m_axi_awlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWSIZE" *)
    output wire [2:0] m_axi_awsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWBURST" *)
    output wire [1:0] m_axi_awburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWLOCK" *)
    output wire m_axi_awlock,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWCACHE" *)
    output wire [3:0] m_axi_awcache,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWPROT" *)
    output wire [2:0] m_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI AWQOS" *)
    output wire [3:0] m_axi_awqos,
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
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BID" *)
    input wire [0:0] m_axi_bid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BRESP" *)
    input wire [1:0] m_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BVALID" *)
    input wire m_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI BREADY" *)
    output wire m_axi_bready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARID" *)
    output wire [0:0] m_axi_arid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARADDR" *)
    output wire [48:0] m_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARLEN" *)
    output wire [7:0] m_axi_arlen,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARSIZE" *)
    output wire [2:0] m_axi_arsize,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARBURST" *)
    output wire [1:0] m_axi_arburst,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARLOCK" *)
    output wire m_axi_arlock,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARCACHE" *)
    output wire [3:0] m_axi_arcache,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARPROT" *)
    output wire [2:0] m_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARQOS" *)
    output wire [3:0] m_axi_arqos,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARVALID" *)
    output wire m_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI ARREADY" *)
    input wire m_axi_arready,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RID" *)
    input wire [0:0] m_axi_rid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RDATA" *)
    input wire [127:0] m_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RRESP" *)
    input wire [1:0] m_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RLAST" *)
    input wire m_axi_rlast,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RVALID" *)
    input wire m_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 M_AXI RREADY" *)
    output wire m_axi_rready,
    output wire [31:0] neural_completed_neurons,
    output wire [31:0] neural_completed_pages,
    output wire [31:0] neural_synaptic_events,
    // PS HPM0 -> future SmartConnect width conversion -> THIS AXI-Lite port.
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
    output wire [1:0] s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI BVALID" *)
    output wire s_axi_bvalid,
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
    output wire [31:0] s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RRESP" *)
    output wire [1:0] s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RVALID" *)
    output wire s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 S_AXI RREADY" *)
    input wire s_axi_rready,
    input wire csr_trusted,
    input wire driver_bound_verified,
    input wire control_route_verified,
    input wire interconnect_drain_ack,
    output wire drain_request,
    output wire stop_new_requests,
    output wire work_busy,
    output wire work_fault,
    output wire [31:0] work_completed_commands,
    output wire lease_granted,
    output wire lease_sealed,
    output wire lease_poisoned,
    output wire [31:0] active_generation,
    output wire [63:0] admitted_begin,
    output wire [63:0] admitted_end
);
    wire lease_active,neural_poisoned;
    wire control_admit;
    wire request,request_save,dispatch_req;
    wire [31:0] request_page,request_tick,dispatch_logical;
    assign lease_active=control_admit;
    // No compute dispatch or memory request may escape a revoked,
    // ungranted or sealed lease. Poison on an unauthorized attempt.
    wire unauthorized_request=(request || dispatch_req) && !lease_active;
    wire restricted_request=request && lease_active && !lease_poisoned;
    wire restricted_dispatch=dispatch_req && lease_active && !lease_poisoned;
    wire [63:0] page_dma_address =
        admitted_begin+({32'd0,request_page}<<8);
    wire transport_idle= !busy && !request && !dispatch_req &&
        !m_axi_awvalid && !m_axi_arvalid && !m_axi_wvalid &&
        !m_axi_bready && !m_axi_rready;
    wire bank_clean_idle=(bank_phase==3'd0 || bank_phase==3'd2) &&
        !bank_dirty && !request && !dispatch_req;
    m08_m085_axil_control_candidate #(
        .ENABLE_WORK_COMMANDS(1),
        .WORK_TIMEOUT_CYCLES(WORK_TIMEOUT_CYCLES)
    ) control_plane (
        .clk(clk),.resetn(resetn),
        .s_axi_awaddr(s_axi_awaddr),.s_axi_awprot(s_axi_awprot),
        .s_axi_awvalid(s_axi_awvalid),.s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),.s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),.s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),.s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),.s_axi_arprot(s_axi_arprot),
        .s_axi_arvalid(s_axi_arvalid),.s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),.s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),.s_axi_rready(s_axi_rready),
        .csr_trusted(csr_trusted),
        .driver_bound_verified(driver_bound_verified),
        .control_route_verified(control_route_verified),
        .interconnect_drain_ack(interconnect_drain_ack),
        .transport_idle(transport_idle),
        .bank_clean_idle(bank_clean_idle),
        .admit_work(control_admit),
        .stop_new_requests(stop_new_requests),
        .drain_request(drain_request),
        .lease_granted(lease_granted),.lease_sealed(lease_sealed),
        .lease_poisoned(lease_poisoned),.active_generation(active_generation),
        .admitted_begin(admitted_begin),.admitted_end(admitted_end),
        .neural_done(done),.neural_completed_save(completed_save),
        .neural_busy(busy),.neural_poisoned(neural_poisoned),
        .neural_bank_valid(bank_valid),.neural_bank_dirty(bank_dirty),
        .neural_bank_phase(bank_phase),.neural_bank_logical(bank_logical),
        .work_page_req(request),.work_page_save(request_save),
        .work_page_slot(request_page),.work_page_tick(request_tick),
        .work_dispatch_req(dispatch_req),.work_dispatch_logical(dispatch_logical),
        .work_busy(work_busy),.work_fault(work_fault),
        .work_completed_commands(work_completed_commands)
    );
    m08_m085_axi_neural_shell #(
        .WINDOW_BEGIN(64'd0),.WINDOW_END(64'd0),
        .GUARD_WAIT_CYCLES(GUARD_WAIT_CYCLES),
        .AXI_STALL_CYCLES(AXI_STALL_CYCLES),
        .HOST_WAIT_CYCLES(HOST_WAIT_CYCLES),
        .USE_RUNTIME_WINDOW(1)
    ) neural(
        .clk(clk),
        .resetn(resetn),
        .request(restricted_request),
        .request_save(request_save),
        .request_page(request_page),
        .request_tick(request_tick),
        .done(done),
        .error(error),
        .busy(busy),
        .poisoned(neural_poisoned),
        .completed_save(completed_save),
        .bank_phase(bank_phase),
        .bank_dirty(bank_dirty),
        .bank_valid(bank_valid),
        .bank_logical(bank_logical),
        .bank_loaded_bytes(bank_loaded_bytes),
        .axi_bytes_completed_in_simulation(axi_bytes_completed_in_simulation),
        .dispatch_req(restricted_dispatch),
        .dispatch_logical(dispatch_logical),
        .dispatch_accept(dispatch_accept),
        .m_axi_awid(m_axi_awid),
        .m_axi_awaddr(m_axi_awaddr),
        .m_axi_awlen(m_axi_awlen),
        .m_axi_awsize(m_axi_awsize),
        .m_axi_awburst(m_axi_awburst),
        .m_axi_awlock(m_axi_awlock),
        .m_axi_awcache(m_axi_awcache),
        .m_axi_awprot(m_axi_awprot),
        .m_axi_awqos(m_axi_awqos),
        .m_axi_awvalid(m_axi_awvalid),
        .m_axi_awready(m_axi_awready),
        .m_axi_wdata(m_axi_wdata),
        .m_axi_wstrb(m_axi_wstrb),
        .m_axi_wlast(m_axi_wlast),
        .m_axi_wvalid(m_axi_wvalid),
        .m_axi_wready(m_axi_wready),
        .m_axi_bid(m_axi_bid),
        .m_axi_bresp(m_axi_bresp),
        .m_axi_bvalid(m_axi_bvalid),
        .m_axi_bready(m_axi_bready),
        .m_axi_arid(m_axi_arid),
        .m_axi_araddr(m_axi_araddr),
        .m_axi_arlen(m_axi_arlen),
        .m_axi_arsize(m_axi_arsize),
        .m_axi_arburst(m_axi_arburst),
        .m_axi_arlock(m_axi_arlock),
        .m_axi_arcache(m_axi_arcache),
        .m_axi_arprot(m_axi_arprot),
        .m_axi_arqos(m_axi_arqos),
        .m_axi_arvalid(m_axi_arvalid),
        .m_axi_arready(m_axi_arready),
        .m_axi_rid(m_axi_rid),
        .m_axi_rdata(m_axi_rdata),
        .m_axi_rresp(m_axi_rresp),
        .m_axi_rlast(m_axi_rlast),
        .m_axi_rvalid(m_axi_rvalid),
        .m_axi_rready(m_axi_rready),
        .neural_completed_neurons(neural_completed_neurons),
        .neural_completed_pages(neural_completed_pages),
        .neural_synaptic_events(neural_synaptic_events),
        .owner_lease_active(lease_active && !lease_poisoned),
        .runtime_window_begin(admitted_begin),
        .runtime_window_end(admitted_end),
        .session_poison(lease_poisoned || unauthorized_request),
        .request_addr(page_dma_address)
    );
    assign poisoned=neural_poisoned || lease_poisoned || unauthorized_request;
endmodule
