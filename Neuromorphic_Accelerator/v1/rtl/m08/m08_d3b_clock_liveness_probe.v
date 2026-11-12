// M08 D3.2 experimental diagnostic: two-clock PL0-edge observation.
// This is synthesizable Verilog, but NOT INTEGRATED INTO VIVADO OR A BITSTREAM.
// The monitor_clock MUST be independently running when pl_clock stops:
// this is NOT proven by existing K26/FSBL/Linux evidence. A stuck monitor
// clock is a negative failure mode; this RTL does NOT supply ATB4 protection,
// cannot safely complete HPM0 AXI transactions, and is NEVER an MMIO permit.
// heartbeat toggle crosses via two synchronizer flip-flops into monitor domain.
// CDC attributes do not replace a future genuine Vivado CDC/timing review.
module m08_d3b_clock_liveness_probe #(
    parameter integer HEARTBEAT_BITS = 2,
    parameter integer QUIET_LIMIT = 32
)(
    input wire pl_clock,
    input wire pl_resetn,
    input wire monitor_clock,
    input wire monitor_resetn,
    output reg clock_observed_alive,
    output reg clock_failure_sticky
);
    reg [HEARTBEAT_BITS-1:0] heartbeat_counter;
    reg heartbeat;
    always @(posedge pl_clock or negedge pl_resetn) begin
        if (!pl_resetn) begin
            heartbeat_counter <= 0;
            heartbeat <= 0;
        end else begin
            heartbeat_counter <= heartbeat_counter + 1'b1;
            if (&heartbeat_counter)
                heartbeat <= ~heartbeat;
        end
    end

    (* ASYNC_REG = "TRUE" *) reg sync_meta;
    (* ASYNC_REG = "TRUE" *) reg sync_stage2;
    reg sync_previous;
    reg [31:0] quiet_cycles;
    always @(posedge monitor_clock or negedge monitor_resetn) begin
        if (!monitor_resetn) begin
            sync_meta <= 0;
            sync_stage2 <= 0;
            sync_previous <= 0;
            quiet_cycles <= 0;
            clock_observed_alive <= 0;
            clock_failure_sticky <= 0;
        end else begin
            sync_meta <= heartbeat;
            sync_stage2 <= sync_meta;
            sync_previous <= sync_stage2;
            if (sync_stage2 != sync_previous) begin
                quiet_cycles <= 0;
                if (!clock_failure_sticky)
                    clock_observed_alive <= 1;
            end else if (quiet_cycles < QUIET_LIMIT) begin
                quiet_cycles <= quiet_cycles + 1;
            end
            if (quiet_cycles >= QUIET_LIMIT-1) begin
                clock_observed_alive <= 0;
                if (clock_observed_alive)
                    clock_failure_sticky <= 1;
            end
        end
    end
endmodule
