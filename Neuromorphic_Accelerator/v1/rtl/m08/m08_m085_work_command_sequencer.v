`timescale 1ns/1ps
// M08.5 OFFLINE SOURCE ONLY: kernel-intended work-command sequencer.
// This is NOT a Linux driver, privilege firewall, physical memory ownership,
// AXI outstanding-transaction proof, PS connectivity, or bus-isolation unit.
// Receives ONE completed 32-bit AXI-Lite register write from its frontend.
// Only the 7 frozen DMA slots are admitted by the independent lease fence.
// 0x24 slot RW, 0x28 tick RW, 0x2c command WO (1 load,2 dispatch,3 save),
// 0x30 status RO [0 busy,1 completed sticky,2 fault, 7:6 last op],
// 0x34 completed-command counter RO. Every successful command serializes
// full page/compute completion; each invalid write poisons irreversibly.
// A direct START pulse lasts exactly one clock. No user-chosen DMA address.
module m08_m085_work_command_sequencer #(
    parameter integer WORK_TIMEOUT_CYCLES=8192
)(
    input wire clk, resetn,
    input wire write_valid,
    input wire [7:0] write_addr,
    input wire [31:0] write_data,
    input wire [3:0] write_strb,
    input wire trusted_owner,     // synthetic, external protected owner needed
    input wire raw_lease_admit,   // underlying CSR fence admission before AW/W embargo
    input wire source_admit,      // no pending AW/W/B or stop
    input wire stop_new_requests,
    input wire neural_done,
    input wire neural_completed_save,
    input wire neural_busy,
    input wire neural_poisoned,
    input wire neural_bank_valid,
    input wire neural_bank_dirty,
    input wire [2:0] neural_bank_phase,
    input wire [31:0] neural_bank_logical,
    output wire write_error,
    input wire [7:0] read_addr,
    output reg [31:0] read_data,
    output wire read_error,
    output wire fault,
    output wire work_busy,
    output reg [31:0] completed_commands,
    output wire page_req,
    output wire page_save,
    output wire [31:0] page_slot,
    output wire [31:0] page_tick,
    output wire dispatch_req,
    output wire [31:0] dispatch_logical
);
    localparam [2:0] IDLE=0, PAGE_START=1, PAGE_WAIT=2,
                     DISPATCH_START=3, DISPATCH_WAIT=4, FAULT=5;
    reg [2:0] phase;
    reg sticky_done;
    reg [1:0] op_q;
    reg [31:0] slot_q,tick_q;
    reg [31:0] cycles;
    wire [31:0] expected_logical=slot_q==32'd6 ?
        32'hFFFFFFFF : slot_q;
    wire status_write=(write_addr==8'h24 || write_addr==8'h28);
    wire command_write=(write_addr==8'h2c);
    wire valid_slot=slot_q<=32'd6 &&
        tick_q<=32'd3 && (slot_q!=32'd6 || tick_q==32'd0);
    wire valid_load=write_data==32'd1 &&
        !neural_busy && !neural_bank_dirty;
    wire valid_dispatch=write_data==32'd2 &&
        !neural_busy && neural_bank_valid && !neural_bank_dirty &&
        neural_bank_phase==3'd2 && neural_bank_logical==expected_logical;
    wire valid_save=write_data==32'd3 &&
        !neural_busy && neural_bank_valid && neural_bank_dirty &&
        neural_bank_phase==3'd4 && neural_bank_logical==expected_logical;
    wire acceptable_write=trusted_owner && raw_lease_admit &&
        (write_strb==4'hf) && write_addr[1:0]==0 && phase==IDLE &&
        ((status_write) ||
         (command_write && valid_slot &&
             (valid_load || valid_dispatch || valid_save)));
    assign write_error=write_valid && !acceptable_write;
    assign read_error=!(read_addr==8'h24 || read_addr==8'h28 ||
                        read_addr==8'h30 || read_addr==8'h34);
    // Register neural poison before reflecting it back into session_poison:
    // no combinational cycle through the original bank's fault outputs.
    assign fault=phase==FAULT || write_error;
    assign work_busy=phase!=IDLE && phase!=FAULT;
    assign page_slot=slot_q;
    assign page_tick=tick_q;
    assign page_save=(op_q==2'd3);
    assign page_req=phase==PAGE_START && source_admit &&
        !stop_new_requests && !fault;
    assign dispatch_req=phase==DISPATCH_START && source_admit &&
        !stop_new_requests && !fault;
    assign dispatch_logical=expected_logical;

    always @* begin
        read_data=32'd0;
        case(read_addr)
            8'h24:read_data=slot_q;
            8'h28:read_data=tick_q;
            8'h30:read_data={24'd0,op_q,3'd0,fault,sticky_done,work_busy};
            8'h34:read_data=completed_commands;
            default:read_data=32'd0;
        endcase
    end
    always @(posedge clk) begin
        if(!resetn)begin
            phase<=IDLE;sticky_done<=0;op_q<=0;
            slot_q<=0;tick_q<=0;cycles<=0;
            completed_commands<=0;
        end else if(write_error || neural_poisoned ||
                    (work_busy && (!raw_lease_admit || stop_new_requests)))begin
            phase<=FAULT;sticky_done<=0;
        end else begin
            if(write_valid && acceptable_write)begin
                if(write_addr==8'h24)slot_q<=write_data;
                if(write_addr==8'h28)tick_q<=write_data;
                if(command_write)begin
                    op_q<=write_data[1:0];
                    sticky_done<=0;
                    cycles<=0;
                    phase<=write_data==32'd2 ? DISPATCH_START : PAGE_START;
                end
            end
            case(phase)
                PAGE_START: if(page_req)phase<=PAGE_WAIT;
                PAGE_WAIT:begin
                    if(neural_done)begin
                        if(neural_completed_save!=page_save ||
                           !neural_bank_valid || neural_bank_dirty ||
                           neural_bank_phase!=3'd2 ||
                           neural_bank_logical!=expected_logical)
                            phase<=FAULT;
                        else begin
                            phase<=IDLE;sticky_done<=1;
                            completed_commands<=completed_commands+1;
                        end
                    end else if(cycles>=WORK_TIMEOUT_CYCLES-1)
                        phase<=FAULT;
                    else cycles<=cycles+1;
                end
                DISPATCH_START:if(dispatch_req)phase<=DISPATCH_WAIT;
                DISPATCH_WAIT:begin
                    if(neural_bank_dirty && neural_bank_phase==3'd4 &&
                       neural_bank_logical==expected_logical)begin
                        phase<=IDLE;sticky_done<=1;
                        completed_commands<=completed_commands+1;
                    end else if(cycles>=WORK_TIMEOUT_CYCLES-1)
                        phase<=FAULT;
                    else cycles<=cycles+1;
                end
                FAULT:phase<=FAULT;
                default:begin end
            endcase
        end
    end
endmodule
