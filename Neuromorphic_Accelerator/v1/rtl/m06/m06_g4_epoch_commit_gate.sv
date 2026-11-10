// M06 EXISTING G4: candidate fail-closed run acceptance supervisor.
// This does NOT modify the original generated-HLS RTL or original AMD IP.
// Intended for an independently owned, simulated canonical state image only.
// Actual G4 original-Vivado connected fault injection is UNVERIFIED.
// Trace/metrics consumers MUST buffer until commit_valid, discard when poisoned.
// Does NOT implement hardware-atomic physical DDR, persisted rollback,
// external ownership arbitration, watchdog, or crash consistency.
module m06_g4_epoch_commit_gate #(
    // Conservative bounded simulation/host-contract watchdog, NOT measured
    // physical FPGA or DDR service latency.
    parameter integer MAX_EPOCH_CYCLES = 10000000
) (
    input  wire         aclk,
    input  wire         aresetn,
    input  wire         epoch_begin,   // one accepted ap_start transaction
    input  wire         ap_done,       // completion of that HLS epoch
    input  wire [31:0]  ap_return,
    input  wire         read_guard_fault,
    input  wire         write_guard_fault,
    input  wire         write_aw_fire,
    input  wire         write_b_fire,
    input  wire         read_ar_fire,
    output reg          epoch_active,
    output reg          commit_valid,
    output reg          poisoned,
    output reg [15:0]   outstanding_writes
);
    reg [31:0] epoch_cycles;
    // Register one quiet cycle after ap_done before exposing commit token.
    // Original guard fault_seen is registered on the AXI response edge.
    reg settling_commit;
    wire timed_out=epoch_active &&
                   (epoch_cycles>=MAX_EPOCH_CYCLES);
    wire overflow = write_aw_fire && !write_b_fire &&
                    outstanding_writes==16'hffff;
    wire underflow = write_b_fire && !write_aw_fire &&
                     outstanding_writes==16'd0;
    wire [15:0] next_outstanding =
        outstanding_writes + {15'd0,write_aw_fire} -
                             {15'd0,write_b_fire};
    wire overlapping_read = read_ar_fire && (next_outstanding!=0);
    wire bad_response = read_guard_fault || write_guard_fault ||
                        overflow || underflow || overlapping_read || timed_out;

    always @(posedge aclk) begin
        if (!aresetn) begin
            epoch_active<=1'b0;
            commit_valid<=1'b0;
            poisoned<=1'b0;
            outstanding_writes<=16'd0;
            epoch_cycles<=32'd0;
            settling_commit<=1'b0;
        end else if (epoch_begin) begin
            // A fault/quarantined image cannot be reused by simply starting
            // another HLS kernel invocation. Require explicit RESET and an
            // external canonical-image discard/restore contract.
            if (epoch_active || settling_commit || poisoned || ap_done ||
                read_guard_fault || write_guard_fault) begin
                poisoned<=1'b1;
                commit_valid<=1'b0;
            end else begin
                epoch_active<=1'b1;
                commit_valid<=1'b0;
                outstanding_writes<=16'd0;
                epoch_cycles<=32'd0;
                settling_commit<=1'b0;
            end
        end else begin
            if (read_guard_fault || write_guard_fault) begin
                poisoned<=1'b1;
                commit_valid<=1'b0;
            end
            if (epoch_active) begin
                if (!timed_out) epoch_cycles<=epoch_cycles+32'd1;
                if (bad_response) begin
                    poisoned<=1'b1;
                    commit_valid<=1'b0;
                end
                if (overflow || underflow)
                    outstanding_writes<=16'd0; // poisoned; no wrap
                else
                    outstanding_writes<=next_outstanding;
                if (ap_done) begin
                    epoch_active<=1'b0;
                    if (poisoned || bad_response || ap_return!=32'd0 ||
                        next_outstanding!=16'd0) begin
                        poisoned<=1'b1;
                        commit_valid<=1'b0;
                        settling_commit<=1'b0;
                    end else begin
                        // NOT an immediate commit: allow registered guard
                        // RRESP/BRESP faults on this same edge to settle.
                        settling_commit<=1'b1;
                        commit_valid<=1'b0;
                    end
                end
            end else if (settling_commit) begin
                settling_commit<=1'b0;
                if (read_guard_fault || write_guard_fault || poisoned ||
                    ap_done || write_aw_fire || write_b_fire || read_ar_fire ||
                    outstanding_writes!=16'd0) begin
                    poisoned<=1'b1;
                    commit_valid<=1'b0;
                end else begin
                    commit_valid<=1'b1;
                end
            end else if (ap_done || write_aw_fire || write_b_fire ||
                         read_ar_fire) begin
                // No memory operation or completion outside an active epoch.
                poisoned<=1'b1;
                commit_valid<=1'b0;
            end
        end
    end
endmodule
