// M08.5 OFFLINE-only integrated AXI4 256-byte M06 page + original 64x32
// M08 bank lifecycle. Built for 6 signed16 neural pages, one bank, 4 ticks.
// No Loihi signed24 512KiB context, no PS mapping or kernel DMA binding.
// This module is NOT in accepted M08.4 hardware, nor a routed K26 image.
//
// LOAD: 16 AXI R beats -> validate M6NF/page/count/tick ->
//        begin bank -> 64 genuine host writes -> 64 actual bank readbacks,
//        compare all 64 words -> commit only after full comparison.
// SAVE: read all 64 actual dirty words -> 16 AXI W beats + OKAY B ->
//       16 AXI R beats (independent DDR readback) -> compare all 256B ->
//       host_save_done, clearing dirty bank only AFTER matching readback.
// This still cannot prove a real OS-owned DDR allocation, cache coherence
// or persistent storage without an independently owned system interface.
// All faults quarantine both bank and AXI until FULL system quiesce/reset.
module m08_m085_axi_bank_bridge #(
    parameter [63:0] WINDOW_BEGIN=64'd0,
    parameter [63:0] WINDOW_END=64'd0,
    parameter integer GUARD_WAIT_CYCLES=4096,
    parameter integer AXI_STALL_CYCLES=128,
    parameter integer HOST_WAIT_CYCLES=128
)(
    input wire clk,
    input wire resetn,
    input wire owner_lease_active,
    input wire request,
    input wire request_save, // 0=load from DDR; 1=save current DIRTY bank to DDR
    input wire [63:0] request_addr,
    input wire [31:0] request_page,
    input wire [31:0] request_tick,
    output reg done,
    output reg error,
    output wire busy,
    output wire poisoned,
    output reg completed_save,
    output wire [2:0] bank_phase,
    output wire bank_dirty,
    output wire bank_valid,
    output wire [31:0] bank_logical,
    output wire [8:0] bank_loaded_bytes,
    output wire [31:0] axi_bytes_completed_in_simulation,
    input wire dispatch_req,
    input wire [31:0] dispatch_logical,
    output wire dispatch_accept,
    input wire compute_req,
    input wire compute_write,
    input wire [5:0] compute_word,
    input wire [31:0] compute_wdata,
    input wire [3:0] compute_wstrb,
    output wire compute_ack,
    output wire [31:0] compute_rdata,
    input wire compute_done,
    input wire compute_fault,
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
    localparam [4:0] IDLE=0, LOAD_AXI_START=1, LOAD_AXI_WAIT=2,
       BANK_BEGIN=3, LOAD_WRITE_ISSUE=4, LOAD_WRITE_WAIT=5,
       LOAD_WRITE_DROP=6, LOAD_READ_ISSUE=7, LOAD_READ_WAIT=8,
       LOAD_READ_DROP=9, BANK_COMMIT=10, BANK_COMMIT_CHECK=11,
       SAVE_READ_ISSUE=12, SAVE_READ_WAIT=13, SAVE_READ_DROP=14,
       SAVE_AXI_START=15, SAVE_AXI_WAIT=16,
       VERIFY_AXI_START=17, VERIFY_AXI_WAIT=18,
       BANK_SAVE=19, BANK_SAVE_CHECK=20, FAULT=31;
    reg [4:0] state;
    reg armed;
    reg [5:0] word_index;
    reg [31:0] wait_count;
    reg [63:0] address_q;
    reg [31:0] page_q,tick_q;
    reg [2047:0] page_snapshot;
    reg [2047:0] expected_save;
    wire [2:0] phase;
    wire bank_poisoned,bank_host_busy,bank_compute_busy,bank_page_valid;
    wire bank_page_dirty,bank_host_ack,bank_host_error;
    wire [31:0] bank_host_rdata;
    wire [31:0] real_bank_logical;
    wire [8:0] real_loaded;
    wire axi_ack,axi_error,axi_busy,axi_poisoned;
    wire axi_read_valid,axi_completed_write;
    wire [2047:0] axi_read_page;
    wire [31:0] axi_completed_page,axi_completed_tick;
    wire [31:0] axi_completed_transfers,axi_read_bursts,axi_write_bursts;
    wire [31:0] axi_bytes;
    wire host_req=(state==LOAD_WRITE_ISSUE || state==LOAD_READ_ISSUE ||
                   state==SAVE_READ_ISSUE);
    wire host_write=(state==LOAD_WRITE_ISSUE);
    wire host_begin=(state==BANK_BEGIN);
    wire host_commit=(state==BANK_COMMIT);
    wire host_save=(state==BANK_SAVE);
    wire [31:0] host_wdata=page_snapshot[word_index*32 +:32];
    wire [3:0] host_wstrb=host_write ? 4'hF : 4'h0;
    wire axi_req=(state==LOAD_AXI_START || state==SAVE_AXI_START ||
                  state==VERIFY_AXI_START);
    wire axi_write=(state==SAVE_AXI_START);
    wire local_fault=(state==FAULT) || axi_poisoned || bank_poisoned;
    wire compute_idle=!bank_compute_busy && !dispatch_req && !compute_req &&
                      !compute_done;
    wire bank_idle=!bank_host_busy && !host_req && !host_begin &&
                   !host_commit && !host_save;
    wire header_ok=(axi_read_page[60*32 +:32]==32'h4D364E46) &&
       (axi_read_page[61*32 +:32]==page_q) &&
       (axi_read_page[62*32 +:32]==(page_q==5 ? 32'd2 : 32'd6)) &&
       (axi_read_page[63*32 +:32]==tick_q);
    wire [64:0] directory_address =
        {1'b0,WINDOW_BEGIN} + ({33'd0,request_page} << 8);
    // This candidate binds six 256-byte pages to one contiguous,
    // independently OWNED future allocation. No arbitrary page/DDR alias.
    wire address_binding_ok =
        WINDOW_END>WINDOW_BEGIN &&
        WINDOW_BEGIN[7:0]==8'd0 &&
        (WINDOW_END-WINDOW_BEGIN)>=64'd1536 &&
        !directory_address[64] &&
        (request_addr==directory_address[63:0]);
    wire save_header_ok=(page_snapshot[60*32 +:32]==32'h4D364E46) &&
       (page_snapshot[61*32 +:32]==page_q) &&
       (page_snapshot[62*32 +:32]==(page_q==5 ? 32'd2 : 32'd6)) &&
       (page_snapshot[63*32 +:32]==tick_q);
    assign busy=(state!=IDLE && state!=FAULT);
    assign poisoned=local_fault;
    assign bank_phase=phase;
    assign bank_dirty=bank_page_dirty;
    assign bank_valid=bank_page_valid;
    assign bank_logical=real_bank_logical;
    assign bank_loaded_bytes=real_loaded;
    assign axi_bytes_completed_in_simulation=axi_bytes;

    // The prior original bank remains unchanged. Crucially, no host_commit
    // or save_done occurs without real 64-word host readback/DDR comparison.
    m08_host_staged_page_bank bank (
        .clk(clk),.resetn(resetn),
        .host_begin(host_begin),.host_begin_logical(page_q),
        .host_req(host_req),.host_write(host_write),.host_word(word_index),
        .host_wdata(host_wdata),.host_wstrb(host_wstrb),
        .host_commit(host_commit),.host_readback_verified(host_commit),
        .host_save_done(host_save),
        .host_ack(bank_host_ack),.host_error(bank_host_error),
        .host_rdata(bank_host_rdata),
        .dispatch_req(dispatch_req),.dispatch_logical(dispatch_logical),
        .dispatch_accept(dispatch_accept),
        .compute_req(compute_req),.compute_write(compute_write),
        .compute_word(compute_word),.compute_wdata(compute_wdata),
        .compute_wstrb(compute_wstrb),.compute_ack(compute_ack),
        .compute_rdata(compute_rdata),.compute_done(compute_done),
        .compute_fault(compute_fault),.fault_in(state==FAULT || axi_poisoned),
        .phase(phase),.poisoned(bank_poisoned),
        .host_busy(bank_host_busy),.compute_busy(bank_compute_busy),
        .page_valid(bank_page_valid),.page_dirty(bank_page_dirty),
        .page_logical(real_bank_logical),.loaded_byte_count(real_loaded)
    );
    m08_m085_axi128_page_candidate #(
        .WINDOW_BEGIN(WINDOW_BEGIN),.WINDOW_END(WINDOW_END),
        .GUARD_WAIT_CYCLES(GUARD_WAIT_CYCLES),
        .AXI_STALL_CYCLES(AXI_STALL_CYCLES)
    ) page_axi (
        .clk(clk),.resetn(resetn),
        .owner_lease_active(owner_lease_active && !local_fault),
        .compute_idle(compute_idle),.page_bank_idle(bank_idle),
        .req(axi_req),.req_write(axi_write),.req_addr(address_q),
        .req_size_bytes(16'd256),.req_logical_page(page_q),
        .req_tick(tick_q),.req_write_page(page_snapshot),
        .ack(axi_ack),.error(axi_error),.busy(axi_busy),
        .poisoned(axi_poisoned),.completed_page(axi_completed_page),
        .completed_tick(axi_completed_tick),
        .completed_write(axi_completed_write),
        .completed_page_transfers(axi_completed_transfers),
        .read_page_valid(axi_read_valid),.read_page_data(axi_read_page),
        .completed_axi_read_bursts(axi_read_bursts),
        .completed_axi_write_bursts(axi_write_bursts),
        .completed_axi_bytes(axi_bytes),
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
        .m_axi_rready(m_axi_rready)
    );
    always @(posedge clk) begin
        if(!resetn) begin
            state<=IDLE;armed<=1;word_index<=0;wait_count<=0;
            address_q<=0;page_q<=0;tick_q<=0;
            page_snapshot<=0;expected_save<=0;
            done<=0;error<=0;completed_save<=0;
        end else begin
            done<=0;error<=0;completed_save<=0;
            if(!request) armed<=1;
            if(state==FAULT) begin
                state<=FAULT;
            end else if(bank_poisoned || bank_host_error ||
                        axi_poisoned || axi_error ||
                        ((state!=IDLE) && !owner_lease_active) ||
                        (state!=IDLE && request && armed) ||
                        (state==IDLE && (bank_compute_busy || dispatch_req) &&
                         request)) begin
                state<=FAULT;error<=1;
            end else begin
                case(state)
                    IDLE: if(request && armed) begin
                        armed<=0;
                        if(!owner_lease_active || request_page>=6 ||
                           request_tick>=4 || !address_binding_ok ||
                           !compute_idle ||
                           bank_host_busy || axi_busy ||
                           (request_save && (!bank_page_dirty ||
                              real_bank_logical!=request_page)) ||
                           (!request_save && bank_page_dirty)) begin
                            state<=FAULT;error<=1;
                        end else begin
                            page_q<=request_page;tick_q<=request_tick;
                            address_q<=request_addr;word_index<=0;
                            page_snapshot<=0;expected_save<=0;
                            wait_count<=0;
                            state<=request_save ? SAVE_READ_ISSUE : LOAD_AXI_START;
                        end
                    end
                    LOAD_AXI_START:state<=LOAD_AXI_WAIT;
                    LOAD_AXI_WAIT: if(axi_ack) begin
                        if(!axi_read_valid || axi_completed_write ||
                           axi_completed_page!=page_q ||
                           axi_completed_tick!=tick_q || !header_ok) begin
                            state<=FAULT;error<=1;
                        end else begin
                            page_snapshot<=axi_read_page;
                            word_index<=0;
                            state<=BANK_BEGIN;
                        end
                    end
                    BANK_BEGIN:state<=LOAD_WRITE_ISSUE;
                    LOAD_WRITE_ISSUE:begin state<=LOAD_WRITE_WAIT;wait_count<=0;end
                    LOAD_WRITE_WAIT: if(bank_host_ack)state<=LOAD_WRITE_DROP;
                         else if(wait_count>=HOST_WAIT_CYCLES-1) begin
                             state<=FAULT;error<=1;
                         end else wait_count<=wait_count+1;
                    LOAD_WRITE_DROP: if(word_index==63) begin
                             word_index<=0;state<=LOAD_READ_ISSUE;
                         end else begin word_index<=word_index+1;state<=LOAD_WRITE_ISSUE;end
                    LOAD_READ_ISSUE:begin state<=LOAD_READ_WAIT;wait_count<=0;end
                    LOAD_READ_WAIT: if(bank_host_ack) begin
                        if(bank_host_rdata!==page_snapshot[word_index*32 +:32]) begin
                            state<=FAULT;error<=1;
                        end else state<=LOAD_READ_DROP;
                    end else if(wait_count>=HOST_WAIT_CYCLES-1) begin
                        state<=FAULT;error<=1;
                    end else wait_count<=wait_count+1;
                    LOAD_READ_DROP: if(word_index==63) state<=BANK_COMMIT;
                        else begin word_index<=word_index+1;state<=LOAD_READ_ISSUE;end
                    BANK_COMMIT:state<=BANK_COMMIT_CHECK;
                    BANK_COMMIT_CHECK:if(phase==3'd2 && bank_page_valid &&
                                      !bank_page_dirty && real_loaded==9'd256 &&
                                      real_bank_logical==page_q) begin
                        done<=1;state<=IDLE;
                    end else begin state<=FAULT;error<=1;end
                    SAVE_READ_ISSUE:begin state<=SAVE_READ_WAIT;wait_count<=0;end
                    SAVE_READ_WAIT:if(bank_host_ack) begin
                        page_snapshot[word_index*32 +:32]<=bank_host_rdata;
                        state<=SAVE_READ_DROP;
                    end else if(wait_count>=HOST_WAIT_CYCLES-1) begin
                        state<=FAULT;error<=1;
                    end else wait_count<=wait_count+1;
                    SAVE_READ_DROP:if(word_index==63) begin
                        if(!save_header_ok)begin
                            state<=FAULT;error<=1;
                        end else state<=SAVE_AXI_START;
                    end else begin word_index<=word_index+1;state<=SAVE_READ_ISSUE;end
                    SAVE_AXI_START:state<=SAVE_AXI_WAIT;
                    SAVE_AXI_WAIT:if(axi_ack) begin
                        if(!axi_completed_write || axi_completed_page!=page_q ||
                           axi_completed_tick!=tick_q) begin
                            state<=FAULT;error<=1;
                        end else begin
                            expected_save<=page_snapshot;
                            state<=VERIFY_AXI_START;
                        end
                    end
                    VERIFY_AXI_START:state<=VERIFY_AXI_WAIT;
                    VERIFY_AXI_WAIT:if(axi_ack) begin
                        if(!axi_read_valid || axi_completed_write ||
                           axi_completed_page!=page_q ||
                           axi_completed_tick!=tick_q ||
                           axi_read_page!==expected_save) begin
                            state<=FAULT;error<=1;
                        end else state<=BANK_SAVE;
                    end
                    BANK_SAVE:state<=BANK_SAVE_CHECK;
                    BANK_SAVE_CHECK:if(phase==3'd2 && bank_page_valid &&
                                    !bank_page_dirty &&
                                    real_bank_logical==page_q) begin
                        completed_save<=1;done<=1;state<=IDLE;
                    end else begin state<=FAULT;error<=1;end
                    default: begin state<=FAULT;error<=1;end
                endcase
            end
        end
    end
endmodule
