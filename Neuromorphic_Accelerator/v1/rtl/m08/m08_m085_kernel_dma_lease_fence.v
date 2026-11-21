`timescale 1ns/1ps
// M08.5 SOURCE-ONLY Linux/device DMA allocation lease INTERLOCK.
// The RTL CANNOT authenticate Linux DMA ownership. These pins must only
// eventually be driven by a VERSIONED kernel-bound and trusted control
// path, not a user UIO or GPIO. NO PS/DDR/driver/board is connected.
// Exactly seven 256-byte pages are exposed. Extra allocated DMA memory
// remains inaccessible. All malformed, changed, revoked or unquiescent
// leases fail closed; reset is NOT physical AXI drain or reuse permission.
//
// UNGRANTED -> ACTIVE by one validated grant -> SEALED by clean release;
// invalid release or mutation -> FAULT until full reset/quiescence.
// After clean release, no re-grant in same reset generation.
module m08_m085_kernel_dma_lease_fence #(
    parameter [63:0] ALLOWED_DMA_BYTES=64'd1792
)(
    input wire clk,
    input wire resetn,
    input wire kernel_dma_lease_valid, // future verified driver only
    input wire control_path_ready,     // future bound trusted control only
    input wire bus_quiescent,          // future actual outstanding drain ACK
    input wire transport_idle,         // no new AXI/page transaction
    input wire bank_clean_idle,        // no compute, no DIRTY/host activity
    input wire lease_grant,
    input wire lease_release,
    input wire [63:0] lease_dma_base,
    input wire [31:0] lease_allocation_bytes,
    input wire [31:0] lease_generation,
    output wire owner_lease_active,
    output wire [63:0] runtime_window_begin,
    output wire [63:0] runtime_window_end,
    output wire granted,
    output wire poisoned,
    output wire sealed,
    output reg error,
    output reg [31:0] latched_generation
);
    localparam [1:0] NONE=0, ACTIVE=1, SEALED=2, FAULT=3;
    localparam [64:0] AXI49_EXCLUSIVE=(65'd1 << 49);
    reg [1:0] state;
    reg [63:0] base_q;
    reg [31:0] bytes_q;
    wire [64:0] allocated_end =
        {1'b0,lease_dma_base} + {33'd0,lease_allocation_bytes};
    wire [64:0] used_end =
        {1'b0,lease_dma_base} + {1'b0,ALLOWED_DMA_BYTES};
    wire valid_descriptor =
        ALLOWED_DMA_BYTES == 64'd1792 &&
        lease_generation!=32'd0 &&
        lease_allocation_bytes>=ALLOWED_DMA_BYTES &&
        lease_dma_base[7:0]==8'd0 &&
        lease_dma_base[63:49]==15'd0 &&
        allocated_end[64]==1'b0 &&
        used_end[64]==1'b0 &&
        allocated_end < AXI49_EXCLUSIVE &&
        used_end < AXI49_EXCLUSIVE;
    wire live_record_matches =
        lease_dma_base==base_q &&
        lease_allocation_bytes==bytes_q &&
        lease_generation==latched_generation;
    wire trust_live=kernel_dma_lease_valid && control_path_ready &&
                    live_record_matches && valid_descriptor;
    // Combinational revoke prevents a new AXI address handshake on
    // the same cycle that trusted control/metadata is withdrawn.
    assign owner_lease_active=(state==ACTIVE) && trust_live &&
                              !lease_release && !lease_grant;
    assign runtime_window_begin=owner_lease_active ? base_q : 64'd0;
    assign runtime_window_end=owner_lease_active ?
        base_q+ALLOWED_DMA_BYTES : 64'd0;
    assign granted=(state==ACTIVE) && owner_lease_active;
    assign poisoned=(state==FAULT);
    assign sealed=(state==SEALED);
    always @(posedge clk) begin
        if(!resetn) begin
            state<=NONE;
            base_q<=0;bytes_q<=0;latched_generation<=0;error<=0;
        end else begin
            error<=1'b0;
            case(state)
                NONE: begin
                    if(lease_release)begin
                        state<=FAULT;error<=1;
                    end else if(lease_grant)begin
                        if(kernel_dma_lease_valid && control_path_ready &&
                           bus_quiescent && transport_idle && bank_clean_idle &&
                           valid_descriptor)begin
                            base_q<=lease_dma_base;
                            bytes_q<=lease_allocation_bytes;
                            latched_generation<=lease_generation;
                            state<=ACTIVE;
                        end else begin
                            state<=FAULT;error<=1;
                        end
                    end
                end
                ACTIVE: begin
                    if(!trust_live || lease_grant)begin
                        state<=FAULT;error<=1;
                    end else if(lease_release)begin
                        if(transport_idle && bank_clean_idle && bus_quiescent)
                            state<=SEALED;
                        else begin
                            state<=FAULT;error<=1;
                        end
                    end
                end
                SEALED:begin
                    if(lease_grant || lease_release)begin
                        state<=FAULT;error<=1;
                    end
                end
                FAULT:state<=FAULT;
                default:begin state<=FAULT;error<=1;end
            endcase
        end
    end
endmodule
