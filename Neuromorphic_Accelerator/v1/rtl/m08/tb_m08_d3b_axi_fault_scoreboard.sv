// M08 D3.2: ABSTRACT PS-clock AXI-Lite AR/R + AW/W/B protocol scoreboard.
// TESTBENCH-ONLY. NOT SYNTHESIZABLE PS ATB, AIB, CDC, SmartConnect, or driver.
// Events below are synthetic downstream handshakes, NOT vendor AXI traffic.
// A synthetic upstream error DOES NOT cancel accepted downstream obligations.
// "locally_drained" means counts reached zero in this mock, not AIB13 ACK.
// Only a *simulated full platform restart* clears fault/quarantine state.
// No firmware, JTAG, hardware MMIO, clock gating RTL or PS registers.
`timescale 1ns/1ps

module m08_d3b_abstract_axi_scoreboard(
    input wire ps_clk,
    input wire ps_resetn,
    input wire ar_fire, r_fire,
    input wire aw_fire, w_fire, b_fire,
    input wire synthetic_timeout,
    input wire isolation_request,
    input wire new_probe,
    input wire rvalid, rready,
    input wire [31:0] rdata,
    input wire [1:0] rresp,
    input wire bvalid, bready,
    input wire [1:0] bresp,
    output reg [5:0] pending_ar, pending_aw, pending_w,
    output reg fault_latched,
    output reg unsafe_isolation,
    output reg illegal_post_fault_probe,
    output reg orphan_response,
    output reg tracked_capacity_exceeded,
    output reg r_backpressure_violation,
    output reg b_backpressure_violation,
    output reg [5:0] late_r_retired, late_b_retired
);
    reg held_r, held_b;
    reg [31:0] held_rdata;
    reg [1:0] held_rresp, held_bresp;

    // This diagnostic deliberately does NOT expose a hardware-ready output.
    wire locally_drained = (pending_ar == 0 && pending_aw == 0 &&
                            pending_w == 0);
    always @(posedge ps_clk) begin
        if (!ps_resetn) begin
            pending_ar <= 0; pending_aw <= 0; pending_w <= 0;
            fault_latched <= 0;
            unsafe_isolation <= 0;
            illegal_post_fault_probe <= 0;
            orphan_response <= 0;
            tracked_capacity_exceeded <= 0;
            late_r_retired <= 0; late_b_retired <= 0;
            held_r <= 0; held_b <= 0;
            held_rdata <= 0; held_rresp <= 0; held_bresp <= 0;
            r_backpressure_violation <= 0;
            b_backpressure_violation <= 0;
        end else begin
            if (held_r && (!rvalid || rdata !== held_rdata ||
                           rresp !== held_rresp))
                r_backpressure_violation <= 1;
            if (held_b && (!bvalid || bresp !== held_bresp))
                b_backpressure_violation <= 1;
            held_r <= rvalid && !rready;
            if (rvalid && !rready) begin
                held_rdata <= rdata;
                held_rresp <= rresp;
            end
            held_b <= bvalid && !bready;
            if (bvalid && !bready)
                held_bresp <= bresp;

            if (synthetic_timeout)
                fault_latched <= 1;
            // Capture means the downstream can still hold AXI obligations.
            // A "successful" upstream SLVERR does not erase these counters.
            if (ar_fire) begin
                pending_ar <= pending_ar + 1'b1;
                if (pending_ar >= 6'd15) begin
                    tracked_capacity_exceeded <= 1;
                    fault_latched <= 1;  // stop at tracking limit
                end
                if (fault_latched) illegal_post_fault_probe <= 1;
            end
            if (aw_fire) begin
                pending_aw <= pending_aw + 1'b1;
                if (pending_aw >= 6'd15) begin
                    tracked_capacity_exceeded <= 1;
                    fault_latched <= 1;
                end
                if (fault_latched) illegal_post_fault_probe <= 1;
            end
            if (w_fire) begin
                pending_w <= pending_w + 1'b1;
                if (pending_w >= 6'd15) begin
                    tracked_capacity_exceeded <= 1;
                    fault_latched <= 1;
                end
                if (fault_latched) illegal_post_fault_probe <= 1;
            end
            if (r_fire) begin
                if (pending_ar == 0) orphan_response <= 1;
                else begin
                    pending_ar <= pending_ar - 1'b1;
                    if (fault_latched) late_r_retired <= late_r_retired + 1'b1;
                end
                if (!rvalid || !rready) orphan_response <= 1;
            end
            if (b_fire) begin
                if (pending_aw == 0 || pending_w == 0)
                    orphan_response <= 1;
                else begin
                    pending_aw <= pending_aw - 1'b1;
                    pending_w <= pending_w - 1'b1;
                    if (fault_latched) late_b_retired <= late_b_retired + 1'b1;
                end
                if (!bvalid || !bready) orphan_response <= 1;
            end
            // Reject a mock that responds upstream with SLVERR yet falsely
            // calls the physical downstream safe to isolate/release.
            if (isolation_request && (!locally_drained || fault_latched ||
                                      synthetic_timeout))
                unsafe_isolation <= 1;
            if (new_probe && (fault_latched || synthetic_timeout))
                illegal_post_fault_probe <= 1;
        end
    end
endmodule

module tb_m08_d3b_axi_fault_scoreboard;
    reg ps_clk = 0, ps_clock_running = 1;
    reg pl_clk = 0, pl_clock_running = 1;
    always #5 if (ps_clock_running) ps_clk=~ps_clk; else ps_clk=0;
    always #7 if (pl_clock_running) pl_clk=~pl_clk; else pl_clk=0;
    reg ps_resetn = 0;
    reg ar_fire=0, r_fire=0, aw_fire=0, w_fire=0, b_fire=0;
    reg synthetic_timeout=0, isolation_request=0, new_probe=0;
    reg rvalid=0, rready=0, bvalid=0, bready=0;
    reg [31:0] rdata=0;
    reg [1:0] rresp=0, bresp=0;
    wire [5:0] pending_ar, pending_aw, pending_w, late_r_retired, late_b_retired;
    wire fault_latched, unsafe_isolation, illegal_post_fault_probe;
    wire orphan_response, tracked_capacity_exceeded;
    wire r_backpressure_violation, b_backpressure_violation;
    integer i;
    integer pl_edges=0, old_pl_edges;
    always @(posedge pl_clk) pl_edges=pl_edges+1;

    m08_d3b_abstract_axi_scoreboard monitor(
        .ps_clk(ps_clk), .ps_resetn(ps_resetn),
        .ar_fire(ar_fire), .r_fire(r_fire), .aw_fire(aw_fire),
        .w_fire(w_fire), .b_fire(b_fire),
        .synthetic_timeout(synthetic_timeout),
        .isolation_request(isolation_request), .new_probe(new_probe),
        .rvalid(rvalid), .rready(rready), .rdata(rdata), .rresp(rresp),
        .bvalid(bvalid), .bready(bready), .bresp(bresp),
        .pending_ar(pending_ar), .pending_aw(pending_aw),
        .pending_w(pending_w), .fault_latched(fault_latched),
        .unsafe_isolation(unsafe_isolation),
        .illegal_post_fault_probe(illegal_post_fault_probe),
        .orphan_response(orphan_response),
        .tracked_capacity_exceeded(tracked_capacity_exceeded),
        .r_backpressure_violation(r_backpressure_violation),
        .b_backpressure_violation(b_backpressure_violation),
        .late_r_retired(late_r_retired), .late_b_retired(late_b_retired)
    );

    task restart_mock_full_platform;
        begin
            @(negedge ps_clk);
            ps_resetn=0;
            ar_fire=0; r_fire=0; aw_fire=0; w_fire=0; b_fire=0;
            synthetic_timeout=0; isolation_request=0; new_probe=0;
            rvalid=0; rready=0; bvalid=0; bready=0;
            repeat (3) @(posedge ps_clk);
            @(negedge ps_clk); ps_resetn=1;
            @(posedge ps_clk); #1;
            if(pending_ar!==0 || pending_aw!==0 || pending_w!==0 ||
               fault_latched!==0 || unsafe_isolation!==0 ||
               orphan_response!==0 || illegal_post_fault_probe!==0 ||
               tracked_capacity_exceeded!==0)
                $fatal(1,"mock restart did not clear scoreboard");
        end
    endtask

    task event_cycle;
        input do_ar, do_r, do_aw, do_w, do_b;
        input do_timeout, do_isolate, do_probe;
        begin
            @(negedge ps_clk);
            ar_fire=do_ar; r_fire=do_r; aw_fire=do_aw; w_fire=do_w;
            b_fire=do_b; synthetic_timeout=do_timeout;
            isolation_request=do_isolate; new_probe=do_probe;
            rvalid=do_r; rready=do_r;
            bvalid=do_b; bready=do_b;
            @(posedge ps_clk); #1;
            @(negedge ps_clk);
            ar_fire=0; r_fire=0; aw_fire=0; w_fire=0; b_fire=0;
            synthetic_timeout=0; isolation_request=0; new_probe=0;
            rvalid=0; rready=0; bvalid=0; bready=0;
        end
    endtask

    initial begin
        restart_mock_full_platform();
        // Normal read and split AW/W write; correct downstream retirement.
        event_cycle(1,0,0,0,0,0,0,0);
        event_cycle(0,0,1,0,0,0,0,0);
        if(pending_ar!==1 || pending_aw!==1 || pending_w!==0)
            $fatal(1,"partial write address state not tracked");
        event_cycle(0,0,0,1,0,0,0,0);
        event_cycle(0,1,0,0,0,0,0,0);
        event_cycle(0,0,0,0,1,0,0,0);
        if(pending_ar!==0 || pending_aw!==0 || pending_w!==0 ||
           orphan_response!==0)
            $fatal(1,"valid AR/R AW/W/B did not drain");
        $display("M08_D3_2_AXI_READ_WRITE_SPLIT_CHANNEL_DRAIN_PASS");

        // Accepted AR + synthetic timeout: mock must refuse isolation.
        restart_mock_full_platform();
        event_cycle(1,0,0,0,0,0,0,0);
        event_cycle(0,0,0,0,0,1,0,0);
        if(!fault_latched || pending_ar!==1)
            $fatal(1,"synthetic error falsely retired downstream AR");
        event_cycle(0,0,0,0,0,0,1,1);
        if(!unsafe_isolation || !illegal_post_fault_probe)
            $fatal(1,"unsafe mock synthetic SLVERR was not rejected");
        $display("M08_D3_2_AXI_SYNTHETIC_SLVERR_WITH_ORPHAN_AR_REJECTED_NEGATIVE");
        event_cycle(0,1,0,0,0,0,0,0);  // orphan relative to upstream, but late downstream
        if(pending_ar!==0 || late_r_retired!==1 || !fault_latched)
            $fatal(1,"late R failed to retire without automatic rearming");
        event_cycle(0,0,0,0,0,0,1,1);
        if(!unsafe_isolation || !illegal_post_fault_probe)
            $fatal(1,"cleared counters falsely rearmed first-fault lockdown");
        $display("M08_D3_2_AXI_LATE_R_DRAIN_NO_AUTO_RECOVERY_PASS");

        // AW without W, followed by both, but still no B: isolate prohibited.
        restart_mock_full_platform();
        event_cycle(0,0,1,0,0,0,0,0);
        event_cycle(0,0,0,0,0,0,1,0);
        if(pending_aw!==1 || !unsafe_isolation)
            $fatal(1,"orphan AW improperly judged quiescent");
        restart_mock_full_platform();
        event_cycle(0,0,0,1,0,0,0,0);
        event_cycle(0,0,0,0,0,0,1,0);
        if(pending_w!==1 || !unsafe_isolation)
            $fatal(1,"orphan W improperly judged quiescent");
        restart_mock_full_platform();
        event_cycle(0,0,1,1,0,0,0,0);
        event_cycle(0,0,0,0,0,1,0,0);
        event_cycle(0,0,0,0,0,0,1,0);
        if(!unsafe_isolation || pending_aw!==1 || pending_w!==1)
            $fatal(1,"missing B was falsely completed");
        event_cycle(0,0,0,0,1,0,0,0);
        if(pending_aw!==0 || pending_w!==0 || late_b_retired!==1 ||
           !fault_latched)
            $fatal(1,"late B failed to retire under quarantine");
        $display("M08_D3_2_AXI_AW_W_B_PARTIAL_AND_LATE_B_CONTAINMENT_PASS");

        // Unexpected downstream completions without any obligation.
        restart_mock_full_platform();
        event_cycle(0,1,0,0,0,0,0,0);
        event_cycle(0,0,0,0,1,0,0,0);
        if(!orphan_response || pending_ar!==0 || pending_aw!==0)
            $fatal(1,"unsolicited R/B not flagged");
        $display("M08_D3_2_AXI_UNSOLICITED_R_B_REJECTED_NEGATIVE");

        // Two concurrent, genuinely outstanding kinds of downstream traffic.
        restart_mock_full_platform();
        event_cycle(1,0,1,1,0,0,0,0);
        event_cycle(0,0,0,0,0,1,0,0);
        event_cycle(0,0,0,0,0,0,1,0);
        if(!unsafe_isolation || pending_ar!==1 || pending_aw!==1 ||
           pending_w!==1)
            $fatal(1,"concurrent AR+write outstanding was erased by timeout");
        $display("M08_D3_2_AXI_CONCURRENT_OUTSTANDING_NOT_SAFE_TO_ISOLATE_PASS");

        // Finite tracking budget, not a vendor-proven ATB implementation.
        restart_mock_full_platform();
        for(i=0;i<16;i=i+1)
            event_cycle(1,0,0,0,0,0,0,0);
        if(!tracked_capacity_exceeded || !fault_latched ||
           pending_ar!==16)
            $fatal(1,"finite abstract transaction tracking did not fail closed");
        $display("M08_D3_2_AXI_TRACKING_CAPACITY_EXCEEDED_NEGATIVE_PASS");

        // Data/response must remain stable during backpressure.
        restart_mock_full_platform();
        @(negedge ps_clk);
        rvalid=1; rready=0; rdata=32'h0000beef; rresp=2'b10;
        bvalid=1; bready=0; bresp=2'b10;
        repeat (3) @(posedge ps_clk);
        @(negedge ps_clk);
        rdata=32'hdeadcafe; bresp=2'b00;   // malicious slave violates stability
        @(posedge ps_clk); #1;
        if(!r_backpressure_violation || !b_backpressure_violation)
            $fatal(1,"response backpressure stability violations missed");
        $display("M08_D3_2_AXI_R_B_BACKPRESSURE_INSTABILITY_REJECTED_NEGATIVE");
        restart_mock_full_platform();

        // PL0 stopped before and after request: checker still needs PS clock.
        restart_mock_full_platform();
        @(negedge ps_clk); pl_clock_running=0;
        repeat(3) @(posedge ps_clk);
        old_pl_edges=pl_edges;
        event_cycle(1,0,0,0,0,0,0,0);
        event_cycle(0,0,0,0,0,1,0,0);
        if(pl_edges!==old_pl_edges || pending_ar!==1 || !fault_latched)
            $fatal(1,"stopped PL0 did not retain downstream outstanding state");
        $display("M08_D3_2_AXI_STOPPED_PL_CLOCK_OUTSTANDING_REMAINS_NEGATIVE");
        pl_clock_running=1;

        // PS clock itself stopped: no timeout/evidence accumulation.
        restart_mock_full_platform();
        event_cycle(1,0,0,0,0,0,0,0);
        @(negedge ps_clk);
        ps_clock_running=0;
        #2; synthetic_timeout=1; isolation_request=1;
        #120;
        if(fault_latched!==0 || unsafe_isolation!==0 || pending_ar!==1)
            $fatal(1,"stopped PS clock falsely counted a timeout");
        ps_clock_running=1;
        repeat(2) @(posedge ps_clk);
        #1;
        if(!fault_latched || !unsafe_isolation)
            $fatal(1,"resumed PS clock did not detect fault/unsafe isolation");
        $display("M08_D3_2_AXI_STOPPED_PS_CLOCK_UNPROTECTED_NEGATIVE");
        $display("M08_D3_2_AXI_ABSTRACT_BFM_ALL_PASS_NOT_VENDOR_ATB_AIB_OR_BOARD");
        $finish;
    end
    initial begin
        #150000;
        $fatal(1,"abstract AXI PS-domain scoreboard timed out");
    end
endmodule
