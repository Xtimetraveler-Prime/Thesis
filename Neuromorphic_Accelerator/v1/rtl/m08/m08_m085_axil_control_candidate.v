// M08.5 SOURCE-ONLY, SYNTHESIZABLE AXI4-Lite 32-bit FRONTEND FOR CSR v1.
// This is a protocol bridge, NOT a trustworthy PS HPM0 route, privilege
// firewall, kernel binding, physical DDR DMA, or AXI interconnect drain.
// Inputs csr_trusted/driver_bound_verified/control_route_verified and
// interconnect_drain_ack are SIMULATED and MUST come from independently
// proven external hardware/software before any physical admission.
// AW and W can arrive in either order; one response per complete pair;
// R and B are held until accepted. No assumed AXI channel co-arrival.
// PROT fields do NOT authenticate origin; never expose to user UIO.
// One-sided orphan writes wait for matching channel and embargo new work.
// Reset of this source block NEVER proves actual outstanding bus drain.
module m08_m085_axil_control_candidate #(
    parameter integer DRAIN_TIMEOUT_CYCLES=128
)(
    input wire clk, resetn,
    input wire [11:0] s_axi_awaddr,
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
    input wire [11:0] s_axi_araddr,
    input wire [2:0] s_axi_arprot,
    input wire s_axi_arvalid,
    output wire s_axi_arready,
    output reg [31:0] s_axi_rdata,
    output reg [1:0] s_axi_rresp,
    output reg s_axi_rvalid,
    input wire s_axi_rready,
    input wire csr_trusted,             // synthetic external trust, NOT AXI PROT
    input wire driver_bound_verified,  // synthetic driver identity
    input wire control_route_verified, // synthetic PS/PL routing provenance
    input wire interconnect_drain_ack, // synthetic independent drain claim
    input wire transport_idle,
    input wire bank_clean_idle,
    output wire admit_work,
    output wire stop_new_requests,
    output wire drain_request,
    output wire lease_granted,
    output wire lease_sealed,
    output wire lease_poisoned,
    output wire [31:0] active_generation,
    output wire [63:0] admitted_begin,
    output wire [63:0] admitted_end
);
    reg aw_pending, w_pending;
    reg [11:0] aw_addr_q;
    reg [31:0] w_data_q;
    reg [3:0] w_strb_q;

    // All five AXI-Lite channels use clocked VALID/READY handshakes.
    // AW and W capture independently; a new transaction waits for BRESP.
    assign s_axi_awready=resetn && !aw_pending && !s_axi_bvalid;
    assign s_axi_wready=resetn && !w_pending && !s_axi_bvalid;
    wire aw_take=s_axi_awready && s_axi_awvalid;
    wire w_take=s_axi_wready && s_axi_wvalid;
    wire write_commit=resetn && aw_pending && w_pending && !s_axi_bvalid;
    // Serialize reads behind pending writes: descriptor readback must reflect
    // completed (not half received) writes, and CSR has one combinational port.
    assign s_axi_arready=resetn && !s_axi_rvalid && !s_axi_bvalid &&
                         !aw_pending && !w_pending && !aw_take && !w_take;
    wire read_take=s_axi_arready && s_axi_arvalid;
    wire [11:0] selected_addr=write_commit ? aw_addr_q : s_axi_araddr;
    // High byte of the 4 KiB slave aperture MUST NOT alias low CSR offsets.
    // Illegal write -> invalid CSR offset -> sticky fault + SLVERR.
    wire [7:0] csr_addr=selected_addr[11:8]!=0 ? 8'hfc : selected_addr[7:0];
    wire csr_valid=write_commit || read_take;
    wire csr_write=write_commit;
    wire [31:0] csr_wdata=w_data_q;
    wire [3:0] csr_wstrb=w_strb_q;
    wire csr_ready, csr_error;
    wire [31:0] csr_rdata;
    wire csr_admit,csr_stop,csr_granted;
    wire [63:0] csr_begin,csr_end;
    // Even an orphaned AW/W, or a same-cycle asserted and accepted channel,
    // immediately embargoes NEW neural page/dispatch admissions. A partially
    // received STOP cannot allow further admissions while waiting for pairing.
    wire write_embargo=aw_pending || w_pending || aw_take || w_take;
    assign admit_work=csr_admit && !write_embargo;
    assign stop_new_requests=csr_stop || write_embargo;
    assign admitted_begin=admit_work ? csr_begin : 64'd0;
    assign admitted_end=admit_work ? csr_end : 64'd0;
    assign lease_granted=csr_granted && !write_embargo;

    // This is visibility policy only. Actual PS master exclusivity is NOT
    // established here. Public CAP/version are readable for diagnostics;
    // driver-only status/descriptor data is denied when trust is withdrawn.
    wire read_allowed=csr_trusted || s_axi_araddr==12'h000 ||
                      s_axi_araddr==12'h004;
    m08_m085_trusted_control_abi #(
        .DRAIN_TIMEOUT_CYCLES(DRAIN_TIMEOUT_CYCLES)
    ) control (
        .clk(clk),.resetn(resetn),
        .csr_valid(csr_valid),.csr_write(csr_write),
        .csr_addr(csr_addr),.csr_wdata(csr_wdata),
        .csr_wstrb(csr_wstrb),.csr_trusted(csr_trusted),
        .csr_ready(csr_ready),.csr_error(csr_error),.csr_rdata(csr_rdata),
        .driver_bound_verified(driver_bound_verified),
        .control_route_verified(control_route_verified),
        .interconnect_drain_ack(interconnect_drain_ack),
        .transport_idle(transport_idle),.bank_clean_idle(bank_clean_idle),
        .admit_work(csr_admit),.stop_new_requests(csr_stop),
        .drain_request(drain_request),
        .lease_granted(csr_granted),.lease_sealed(lease_sealed),
        .lease_poisoned(lease_poisoned),
        .active_generation(active_generation),
        .admitted_begin(csr_begin),.admitted_end(csr_end)
    );
    always @(posedge clk) begin
        if(!resetn) begin
            aw_pending<=0;w_pending<=0;
            aw_addr_q<=0;w_data_q<=0;w_strb_q<=0;
            s_axi_bvalid<=0;s_axi_bresp<=2'b00;
            s_axi_rvalid<=0;s_axi_rresp<=2'b00;s_axi_rdata<=0;
        end else begin
            if(aw_take)begin
                aw_pending<=1;
                aw_addr_q<=s_axi_awaddr;
            end
            if(w_take)begin
                w_pending<=1;
                w_data_q<=s_axi_wdata;
                w_strb_q<=s_axi_wstrb;
            end
            if(write_commit)begin
                aw_pending<=0;
                w_pending<=0;
                s_axi_bvalid<=1;
                // CSR samples same clock edge as this response. Illegal
                // writes become a sticky local/fence fault, NOT just BRESP.
                s_axi_bresp<=(!csr_ready || csr_error) ? 2'b10 : 2'b00;
            end else if(s_axi_bvalid && s_axi_bready)begin
                s_axi_bvalid<=0;
            end
            if(read_take)begin
                s_axi_rvalid<=1;
                s_axi_rresp<=(csr_error || !csr_ready || !read_allowed) ?
                            2'b10 : 2'b00;
                s_axi_rdata<=(csr_error || !csr_ready || !read_allowed) ?
                            32'd0 : csr_rdata;
            end else if(s_axi_rvalid && s_axi_rready)begin
                s_axi_rvalid<=0;
            end
        end
    end
endmodule
