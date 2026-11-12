// M08 D3.2 diagnostic liveness TB: genuine first-party heartbeat RTL.
// No AMD PS, independent physical monitor oscillator, ATB4/AIB13, MMIO,
// or Vivado implementation; do not interpret as protected HPM0 proof.
`timescale 1ns/1ps
module tb_m08_d3b_clock_liveness_probe;
    reg pl_clock=0, pl_running=1;
    reg monitor_clock=0, monitor_running=1;
    always #7 if(pl_running) pl_clock=~pl_clock; else pl_clock=0;
    always #5 if(monitor_running) monitor_clock=~monitor_clock; else monitor_clock=0;
    reg pl_resetn=0, monitor_resetn=0;
    wire clock_observed_alive, clock_failure_sticky;
    integer i;
    m08_d3b_clock_liveness_probe #(.HEARTBEAT_BITS(2),.QUIET_LIMIT(24)) dut (
        .pl_clock(pl_clock), .pl_resetn(pl_resetn),
        .monitor_clock(monitor_clock), .monitor_resetn(monitor_resetn),
        .clock_observed_alive(clock_observed_alive),
        .clock_failure_sticky(clock_failure_sticky)
    );
    initial begin
        repeat(4) @(negedge monitor_clock);
        if(clock_observed_alive!==0 || clock_failure_sticky!==0)
            $fatal(1,"liveness wrongly asserted under initial reset");
        pl_resetn=1;
        monitor_resetn=1;
        repeat(60) @(posedge monitor_clock);
        #1;
        if(clock_observed_alive!==1 || clock_failure_sticky!==0)
            $fatal(1,"liveness did not observe active PL heartbeat");
        $display("M08_D3B_LIVENESS_RUNNING_PL_EDGES_OBSERVED_PASS");

        @(negedge pl_clock); pl_running=0;
        repeat(45) @(posedge monitor_clock);
        #1;
        if(clock_observed_alive!==0 || clock_failure_sticky!==1)
            $fatal(1,"PL clock loss was not detected in active independent monitor");
        $display("M08_D3B_LIVENESS_PL0_STOPS_INDEPENDENT_MONITOR_DETECTS_PASS");

        pl_running=1;
        repeat(60) @(posedge monitor_clock);
        #1;
        if(clock_observed_alive!==0 || clock_failure_sticky!==1)
            $fatal(1,"liveness automatically rearmed after clock restored");
        $display("M08_D3B_LIVENESS_RESUME_DOES_NOT_CLEAR_STICKY_POISON_PASS");

        // Both clocks running, reset monitoring state, then prove clock loss
        // cannot be detected if the monitor itself stops. NEGATIVE control.
        @(negedge monitor_clock); monitor_resetn=0;
        repeat(4) @(negedge monitor_clock);
        monitor_resetn=1;
        repeat(50) @(posedge monitor_clock);
        #1;
        if(clock_observed_alive!==1 || clock_failure_sticky!==0)
            $fatal(1,"full monitor reset did not reinitialize live detector");
        @(negedge pl_clock); pl_running=0;
        @(negedge monitor_clock); monitor_running=0;
        #180;
        if(clock_observed_alive!==1 || clock_failure_sticky!==0)
            $fatal(1,"monitor clock loss unexpectedly advanced any timeout");
        $display("M08_D3B_LIVENESS_STOPPED_MONITOR_CLOCK_IS_UNPROTECTED_NEGATIVE_PASS");

        monitor_running=1;
        repeat(45) @(posedge monitor_clock);
        #1;
        if(clock_observed_alive!==0 || clock_failure_sticky!==1)
            $fatal(1,"monitor did not detect missing PL heartbeat when restored");
        $display("M08_D3B_LIVENESS_GENUINE_RTL_ALL_PASS_NOT_PS_ATB_OR_PHYSICAL_CLOCK_PROOF");
        $finish;
    end
    initial begin
        #30000;
        $fatal(1,"M08 D3B clock liveness diagnostic TB deadlocked");
    end
endmodule
