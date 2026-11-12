// M08 D3.2A: ABSTRACT PS/LINUX release policy testbench ONLY, NOT HARDWARE RTL.
// Seven qualified inputs symbolize independent evidence that is NOT currently
// available from real boot. No CDC, PS ATB4, AIB13, AXI hardware, PL clock
// sensor, Linux driver, firmware, fan controller, or I/O in this simulation.
// Admission is one probe per *simulated full PS restart*. After first normal
// completion, loss of any prerequisite, or timeout: latch lockdown.
// This is only a control-plane STATE-MACHINE CONTRACT; physical MMIO is BANNED.
`timescale 1ns/1ps

module m08_d3b_abstract_ps_release_policy(
    input wire ps_clock,
    input wire ps_resetn,
    input wire [6:0] independent_prerequisites,
    input wire read_request,
    output wire read_grant,
    input wire read_completed,
    input wire ps_atb_timeout,
    output reg fault_locked,
    output reg diagnostic_consumed,
    output reg [1:0] state
);
    localparam [1:0] BLOCKED=2'd0, ARMED=2'd1,
                     OUTSTANDING=2'd2, LOCKED=2'd3;
    wire all_ready = (&independent_prerequisites);
    // Combinational gate on abstract qualified signals.
    // DOES NOT guarantee a bus handshake or safety when ps_clock stops!
    assign read_grant = ps_resetn && all_ready &&
                        (state == ARMED) && read_request &&
                        !fault_locked && !diagnostic_consumed;
    always @(posedge ps_clock) begin
        if (!ps_resetn) begin
            state <= BLOCKED;
            fault_locked <= 0;
            diagnostic_consumed <= 0;
        end else if (ps_atb_timeout || (!all_ready && state != BLOCKED)) begin
            fault_locked <= 1;
            diagnostic_consumed <= 1;
            state <= LOCKED;
        end else begin
            case (state)
                BLOCKED: if (all_ready) state <= ARMED;
                ARMED: if (read_grant) state <= OUTSTANDING;
                OUTSTANDING: if (read_completed) begin
                    diagnostic_consumed <= 1;
                    state <= LOCKED; // ONE diagnostic per platform restart
                end
                LOCKED: state <= LOCKED; // no automatic retry or rearm
                default: begin
                    fault_locked <= 1;
                    state <= LOCKED;
                end
            endcase
        end
    end
endmodule

module tb_m08_d3b_ps_linux_release_policy;
    reg ps_clock = 0, clock_running = 1;
    always #5 if (clock_running) ps_clock=~ps_clock; else ps_clock=0;
    reg ps_resetn = 0;
    reg [6:0] independent_prerequisites = 0;
    reg read_request = 0, read_completed = 0, ps_atb_timeout = 0;
    wire read_grant, fault_locked, diagnostic_consumed;
    wire [1:0] state;
    integer index;
    m08_d3b_abstract_ps_release_policy dut(
        .ps_clock(ps_clock), .ps_resetn(ps_resetn),
        .independent_prerequisites(independent_prerequisites),
        .read_request(read_request), .read_grant(read_grant),
        .read_completed(read_completed), .ps_atb_timeout(ps_atb_timeout),
        .fault_locked(fault_locked), .diagnostic_consumed(diagnostic_consumed),
        .state(state)
    );

    task simulated_platform_restart;
        begin
            @(negedge ps_clock);
            ps_resetn=0; read_request=0; read_completed=0;
            ps_atb_timeout=0; independent_prerequisites=0;
            repeat(3) @(negedge ps_clock);
            ps_resetn=1;
            @(negedge ps_clock);
            if(state!==0 || fault_locked!==0 || diagnostic_consumed!==0 ||
               read_grant!==0)
                $fatal(1,"abstract full PS restart did not clear all policy state");
        end
    endtask

    task establish_all_prerequisites;
        begin
            @(negedge ps_clock);
            independent_prerequisites = 7'b1111111;
            repeat(2) @(negedge ps_clock);
            if(state!==1 || fault_locked!==0)
                $fatal(1,"abstract upstream prerequisites failed to arm");
        end
    endtask

    task request_one;
        begin
            @(negedge ps_clock);
            read_request=1;
            #1; // let combinational abstract qualification settle after request
            if(read_grant!==1)
                $fatal(1,"abstract one-shot grant unexpectedly refused");
            @(posedge ps_clock); #1;
            if(state!==2 || read_grant!==0)
                $fatal(1,"abstract one-shot permit did not enter outstanding");
            @(negedge ps_clock);
            read_request=0;
        end
    endtask

    initial begin
        simulated_platform_restart();
        read_request=1;
        repeat(3) @(posedge ps_clock);
        #1;
        if (read_grant!==0 || state!==0)
            $fatal(1,"unqualified Linux/PS access was admitted");
        @(negedge ps_clock);
        read_request=0;
        // Every one of SEVEN abstract upstream preconditions is necessary:
        // 0: boot ATB4, 1: AIB13 quiescence, 2: HPM0 128-bit AFI,
        // 3: PS-domain observed PL0 stable, 4: reset released,
        // 5: Linux FPGA-region sequencing, 6: independent cooling.
        for(index=0;index<7;index=index+1) begin
            independent_prerequisites=7'b1111111 ^ (7'b1 << index);
            repeat(2) @(negedge ps_clock);
            read_request=1;
            if(read_grant!==0 || state!==0)
                $fatal(1,"missing abstract prerequisite allowed register request");
            read_request=0;
        end
        $display("M08_D3B_EACH_MISSING_PREREQUISITE_BLOCKS_ACCESS_PASS");

        establish_all_prerequisites();
        request_one();
        // A modelled first PS ATB timeout MUST lock all future access,
        // regardless of late completion or readiness signals reappearing.
        @(negedge ps_clock);
        ps_atb_timeout=1;
        @(posedge ps_clock); #1;
        if(state!==3 || fault_locked!==1 || diagnostic_consumed!==1)
            $fatal(1,"PS-side timeout did not latch lifetime lockdown");
        @(negedge ps_clock);
        ps_atb_timeout=0; read_completed=1; read_request=1;
        repeat(4) @(posedge ps_clock);
        #1;
        if(read_grant!==0 || state!==3 || fault_locked!==1)
            $fatal(1,"late response or repeated request bypassed fault lockdown");
        $display("M08_D3B_FIRST_TIMEOUT_STICKY_QUARANTINE_NO_RETRY_PASS");

        simulated_platform_restart();
        establish_all_prerequisites();
        request_one();
        @(negedge ps_clock);
        read_completed=1;
        @(posedge ps_clock); #1;
        if(state!==3 || diagnostic_consumed!==1 ||
           fault_locked!==0 || read_grant!==0)
            $fatal(1,"successful probe did not consume one-shot budget");
        @(negedge ps_clock);
        read_completed=0; read_request=1;
        repeat(3) @(posedge ps_clock);
        #1;
        if(read_grant!==0) $fatal(1,"second probe allowed without platform reset");
        $display("M08_D3B_ONE_SUCCESSFUL_PROBE_PER_FULL_RESTART_PASS");

        simulated_platform_restart();
        establish_all_prerequisites();
        @(negedge ps_clock);
        independent_prerequisites[3]=0; // abstract PS-observed PL0 loss
        @(posedge ps_clock); #1;
        if(state!==3 || fault_locked!==1 || read_grant!==0)
            $fatal(1,"readiness loss did not quarantine even without a read");
        @(negedge ps_clock);
        independent_prerequisites=7'b1111111; read_request=1;
        @(posedge ps_clock); #1;
        if(read_grant!==0)
            $fatal(1,"clock restored without independent restart was rearmed");
        $display("M08_D3B_READINESS_LOSS_LOCKS_UNTIL_RESTART_PASS");

        // NEGATIVE: no PS clock means no new timeout or lock transition.
        simulated_platform_restart();
        establish_all_prerequisites();
        request_one();
        @(negedge ps_clock); clock_running=0;
        #2; // allow final falling edge to force ps_clock=0
        independent_prerequisites[3]=0; ps_atb_timeout=1;
        #120;
        if(state!==2 || fault_locked!==0 || diagnostic_consumed!==0)
            $fatal(1,"abstract policy advanced with a stopped PS clock");
        clock_running=1;
        repeat(2) @(posedge ps_clock);
        #1;
        if(state!==3 || fault_locked!==1)
            $fatal(1,"policy did not respond when PS clock resumed");
        $display("M08_D3B_STOPPED_PS_CLOCK_IS_UNPROTECTED_NEGATIVE_PASS");
        $display("M08_D3B_OFFLINE_PS_LINUX_POLICY_ALL_PASS_NOT_HARDWARE_ATB_OR_MMIO_PROOF");
        $finish;
    end
    initial begin
        #30000;
        $fatal(1,"M08 D3B offline policy simulation deadlocked");
    end
endmodule
