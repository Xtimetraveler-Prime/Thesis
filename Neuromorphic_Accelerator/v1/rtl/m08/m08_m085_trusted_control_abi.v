// M08.5 OFFLINE SOURCE CANDIDATE: VERSIONED CSR COMMAND DECODER, NOT AXI-Lite.
// An actual PS HPM0 -> AXI-Lite endpoint, kernel-only access protection,
// platform/driver attestation, independent interconnect drain/reset controller,
// and physical AXI outstanding-transaction monitor DO NOT EXIST here.
// Inputs named *_verified and csr_trusted are synthetic in the testbench.
// Never treat this decoder as proof of DMA ownership or safe dma_free_coherent.
//
// ABI v1: 32-bit little-endian, aligned, full-WSTRB writes only.
// 00 CAP='M085' (read only); 04 VERSION=00010000 (read only)
// 08 STATUS (read only); 0c DRAIN (read only)
// 10 DMA_BASE_LO; 14 DMA_BASE_HI; 18 ALLOCATION_BYTES; 1c GENERATION
// 20 COMMAND (write only): 1=GRANT, 2=STOP_AND_DRAIN.
// No work may enter on STOP_AND_DRAIN, even before the next clock.
// Physical drain ACK must first DEASSERT after request, then REASSERT when
// the externally reviewed interconnect manager proves all late responses gone.
// Any malformed CSR write, owner loss, or drain timeout seals in FAULT.
module m08_m085_trusted_control_abi #(
    parameter integer DRAIN_TIMEOUT_CYCLES=128
)(
    input wire clk, resetn,
    input wire csr_valid, csr_write,
    input wire [7:0] csr_addr,
    input wire [31:0] csr_wdata,
    input wire [3:0] csr_wstrb,
    input wire csr_trusted,             // FUTURE protected decoder, FAKE in TB
    output wire csr_ready,
    output wire csr_error,
    output reg [31:0] csr_rdata,
    input wire driver_bound_verified,   // FUTURE kernel/device provenance
    input wire control_route_verified,  // FUTURE PS HPM0/AFI provenance
    input wire interconnect_drain_ack,  // FUTURE independent physical drain ACK
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
    localparam [2:0] CONFIG=0, GRANT_PENDING=1, RUN=2,
                     DRAIN_ACK_LOW=3, DRAIN_ACK_HIGH=4,
                     RELEASE_PENDING=5, SEALED=6, FAULT=7;
    localparam [31:0] CAP_MAGIC=32'h4d303835, ABI_VERSION=32'h00010000;
    reg [2:0] phase;
    reg [63:0] base_q;
    reg [31:0] bytes_q, generation_q;
    reg [3:0] written_mask;
    reg [31:0] drain_cycles;
    reg local_fault;
    // Exactly one CSR write per asserted VALID interval; ignore held VALID
    // after the accepting clock, even if the phase has now changed.
    reg write_armed;

    wire csr_wr=csr_valid && csr_write && write_armed;
    wire field_write=(csr_addr==8'h10 || csr_addr==8'h14 ||
                      csr_addr==8'h18 || csr_addr==8'h1c);
    wire full_trusted=csr_trusted && driver_bound_verified &&
                      control_route_verified && csr_wstrb==4'hf &&
                      csr_addr[1:0]==2'b00;
    wire can_grant=phase==CONFIG && written_mask==4'hf &&
                   interconnect_drain_ack && transport_idle && bank_clean_idle;
    wire grant_cmd=csr_wr && csr_addr==8'h20 && csr_wdata==32'd1 &&
                   full_trusted && can_grant;
    wire stop_cmd=csr_wr && csr_addr==8'h20 && csr_wdata==32'd2 &&
                  full_trusted && phase==RUN;
    wire good_write=full_trusted &&
        ((phase==CONFIG && field_write) || grant_cmd || stop_cmd);
    wire bad_write=csr_wr && !good_write;
    wire live_owner_loss=(phase==RUN || phase==DRAIN_ACK_LOW ||
                          phase==DRAIN_ACK_HIGH || phase==RELEASE_PENDING) &&
                         (!driver_bound_verified || !control_route_verified);
    wire fence_granted, fence_sealed, fence_poisoned, fence_error, fence_owner;
    wire [63:0] fence_begin, fence_end;
    // Both immediate loss and command races embargo work in the same cycle.
    assign stop_new_requests=(phase!=RUN) || stop_cmd || bad_write ||
                             live_owner_loss || local_fault || fence_poisoned;
    assign admit_work=fence_owner && !stop_new_requests;
    assign lease_granted=fence_granted && admit_work;
    assign lease_sealed=phase==SEALED && fence_sealed;
    assign lease_poisoned=local_fault || bad_write || live_owner_loss ||
                          fence_poisoned || phase==FAULT;
    assign admitted_begin=admit_work ? fence_begin : 64'd0;
    assign admitted_end=admit_work ? fence_end : 64'd0;
    assign drain_request=phase==DRAIN_ACK_LOW || phase==DRAIN_ACK_HIGH;
    assign csr_ready=csr_valid && (!csr_write || write_armed);
    assign csr_error=bad_write || (csr_valid && !csr_write &&
        !(csr_addr==8'h00 || csr_addr==8'h04 || csr_addr==8'h08 ||
          csr_addr==8'h0c || csr_addr==8'h10 || csr_addr==8'h14 ||
          csr_addr==8'h18 || csr_addr==8'h1c));
    wire release_pulse=phase==DRAIN_ACK_HIGH &&
        interconnect_drain_ack && transport_idle && bank_clean_idle &&
        !live_owner_loss && !local_fault;
    m08_m085_kernel_dma_lease_fence fence (
        .clk(clk),.resetn(resetn),
        .kernel_dma_lease_valid(driver_bound_verified && !bad_write && !local_fault),
        .control_path_ready(control_route_verified && !bad_write && !local_fault),
        .bus_quiescent(interconnect_drain_ack),
        .transport_idle(transport_idle),.bank_clean_idle(bank_clean_idle),
        .lease_grant(grant_cmd),.lease_release(release_pulse),
        .lease_dma_base(base_q),.lease_allocation_bytes(bytes_q),
        .lease_generation(generation_q),
        .owner_lease_active(fence_owner),
        .runtime_window_begin(fence_begin),.runtime_window_end(fence_end),
        .granted(fence_granted),.poisoned(fence_poisoned),
        .sealed(fence_sealed),.error(fence_error),
        .latched_generation(active_generation)
    );
    always @* begin
        csr_rdata=32'd0;
        case(csr_addr)
            8'h00:csr_rdata=CAP_MAGIC;
            8'h04:csr_rdata=ABI_VERSION;
            8'h08:csr_rdata={22'd0,lease_poisoned,lease_sealed,
                              lease_granted,stop_new_requests,3'd0,phase};
            8'h0c:csr_rdata={28'd0,bank_clean_idle,transport_idle,
                              interconnect_drain_ack,drain_request};
            8'h10:csr_rdata=base_q[31:0];
            8'h14:csr_rdata=base_q[63:32];
            8'h18:csr_rdata=bytes_q;
            8'h1c:csr_rdata=generation_q;
            default:csr_rdata=32'd0;
        endcase
    end
    always @(posedge clk) begin
        if(!resetn) begin
            phase<=CONFIG;
            base_q<=0;bytes_q<=0;generation_q<=0;
            written_mask<=0;drain_cycles<=0;local_fault<=0;
            write_armed<=1;
        end else begin
            if(!csr_valid)write_armed<=1;
            else if(csr_wr)write_armed<=0;
            if(bad_write || live_owner_loss || fence_poisoned || fence_error)begin
                phase<=FAULT;local_fault<=1;
            end else begin
            case(phase)
                CONFIG:begin
                    if(csr_wr && field_write)begin
                        case(csr_addr)
                            8'h10:begin base_q[31:0]<=csr_wdata;written_mask[0]<=1;end
                            8'h14:begin base_q[63:32]<=csr_wdata;written_mask[1]<=1;end
                            8'h18:begin bytes_q<=csr_wdata;written_mask[2]<=1;end
                            8'h1c:begin generation_q<=csr_wdata;written_mask[3]<=1;end
                        endcase
                    end
                    if(grant_cmd)phase<=GRANT_PENDING;
                end
                GRANT_PENDING:begin
                    if(fence_granted)phase<=RUN;
                    else begin phase<=FAULT;local_fault<=1;end
                end
                RUN:if(stop_cmd)begin
                    phase<=DRAIN_ACK_LOW;
                    drain_cycles<=0;
                end
                DRAIN_ACK_LOW:begin
                    if(!interconnect_drain_ack)phase<=DRAIN_ACK_HIGH;
                    else if(drain_cycles>=DRAIN_TIMEOUT_CYCLES-1)begin
                        phase<=FAULT;local_fault<=1;
                    end else drain_cycles<=drain_cycles+1;
                end
                DRAIN_ACK_HIGH:begin
                    if(release_pulse)phase<=RELEASE_PENDING;
                    else if(drain_cycles>=DRAIN_TIMEOUT_CYCLES-1)begin
                        phase<=FAULT;local_fault<=1;
                    end else drain_cycles<=drain_cycles+1;
                end
                RELEASE_PENDING:begin
                    if(fence_sealed)phase<=SEALED;
                    else begin phase<=FAULT;local_fault<=1;end
                end
                SEALED:phase<=SEALED;
                default:begin phase<=FAULT;local_fault<=1;end
            endcase
            end
        end
    end
endmodule
