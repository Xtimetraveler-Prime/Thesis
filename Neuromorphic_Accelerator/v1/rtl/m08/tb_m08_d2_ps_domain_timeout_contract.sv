// M08 D2: OFFLINE CONTRACT MODEL, NOT SYNTHESIZABLE PS ATB OR PL SAFETY RTL.
// The abstract PS-domain timeout runs ONLY if ps_clock runs. PL-side
// ARREADY/RVALID inputs here are already abstract, safe PS-clock observations;
// NO CDC is implemented. Not an AMD IP/SmartConnect/FPD bus functional model.
// After any timeout: emit synthetic SLVERR once, latch poison, block ALL
// subsequent reads. A downstream accepted AR may remain outstanding!
// Real hardware must prove ATB response/late-response handling and hardware
// quiescence/restart. Never transplant this to a PL-clocked FPGA "fix".
`timescale 1ns/1ps
module m08_d2_abstract_ps_read_guard #(
    parameter integer TIMEOUT_CYCLES = 6
)(
    input wire ps_clock,
    input wire ps_resetn,
    input wire s_arvalid,
    output wire s_arready,
    input wire [31:0] s_araddr,
    output reg s_rvalid,
    input wire s_rready,
    output reg [1:0] s_rresp,
    output reg [31:0] s_rdata,
    output wire m_arvalid,
    input wire m_arready,
    output wire [31:0] m_araddr,
    input wire m_rvalid,
    output wire m_rready,
    input wire [1:0] m_rresp,
    input wire [31:0] m_rdata,
    output reg fault_sticky,
    output reg [1:0] fault_phase
);
    localparam [2:0] IDLE=3'd0, WAIT_AR=3'd1,
                     WAIT_R=3'd2, HOLD_R=3'd3, POISON=3'd4;
    reg [2:0] state;
    reg [31:0] latched_addr;
    integer elapsed;

    assign s_arready = ps_resetn && (state == IDLE) && !fault_sticky;
    assign m_arvalid = ps_resetn && (state == WAIT_AR) && !fault_sticky;
    assign m_araddr = latched_addr;
    assign m_rready = ps_resetn && (state == WAIT_R) && !fault_sticky;

    initial begin
        if (TIMEOUT_CYCLES < 2)
            $fatal(1,"abstract timeout requires at least two PS cycles");
    end
    always @(posedge ps_clock) begin
        if (!ps_resetn) begin
            state <= IDLE;
            latched_addr <= 0;
            elapsed <= 0;
            s_rvalid <= 0;
            s_rresp <= 0;
            s_rdata <= 0;
            fault_sticky <= 0;
            fault_phase <= 0;
        end else begin
            case (state)
                IDLE: begin
                    if (s_arvalid && s_arready) begin
                        latched_addr <= s_araddr;
                        elapsed <= 0;
                        state <= WAIT_AR;
                    end
                end
                WAIT_AR: begin
                    if (m_arvalid && m_arready) begin
                        state <= WAIT_R;
                        elapsed <= 0;
                    end else if (elapsed == TIMEOUT_CYCLES-1) begin
                        s_rvalid <= 1;
                        s_rresp <= 2'b10; // synthetic SLVERR, not verified AMD response
                        s_rdata <= 0;
                        fault_sticky <= 1;
                        fault_phase <= 2'd1;
                        state <= HOLD_R;
                    end else elapsed <= elapsed+1;
                end
                WAIT_R: begin
                    if (m_rvalid && m_rready) begin
                        s_rvalid <= 1;
                        s_rresp <= m_rresp;
                        s_rdata <= m_rdata;
                        state <= HOLD_R;
                    end else if (elapsed == TIMEOUT_CYCLES-1) begin
                        s_rvalid <= 1;
                        s_rresp <= 2'b10;
                        s_rdata <= 0;
                        fault_sticky <= 1;
                        fault_phase <= 2'd2;
                        state <= HOLD_R;
                    end else elapsed <= elapsed+1;
                end
                HOLD_R: begin
                    if (s_rvalid && s_rready) begin
                        s_rvalid <= 0;
                        state <= fault_sticky ? POISON : IDLE;
                    end
                end
                POISON: begin
                    // No automatic rearm, even if a late PL response appears.
                    state <= POISON;
                end
                default: $fatal(1,"invalid PS guard state");
            endcase
        end
    end
endmodule

module tb_m08_d2_ps_domain_timeout_contract;
    reg ps_clock=0, ps_clock_running=1;
    reg pl_clock=0, pl_clock_running=1;
    always #5 if (ps_clock_running) ps_clock=~ps_clock; else ps_clock=0;
    always #7 if (pl_clock_running) pl_clock=~pl_clock; else pl_clock=0;

    integer ps_edges=0, pl_edges=0;
    always @(posedge ps_clock) ps_edges=ps_edges+1;
    always @(posedge pl_clock) pl_edges=pl_edges+1;

    reg ps_resetn=0;
    reg s_arvalid=0;
    reg [31:0] s_araddr=32'ha0000000;
    wire s_arready, s_rvalid;
    reg s_rready=0;
    wire [1:0] s_rresp;
    wire [31:0] s_rdata;
    wire m_arvalid, m_rready;
    wire [31:0] m_araddr;
    reg m_arready=0, m_rvalid=0;
    reg [1:0] m_rresp=0;
    reg [31:0] m_rdata=0;
    wire fault_sticky;
    wire [1:0] fault_phase;
    integer prior_ps_edges, prior_pl_edges, i;
    m08_d2_abstract_ps_read_guard #(.TIMEOUT_CYCLES(6)) guard_dut (
        .ps_clock(ps_clock),.ps_resetn(ps_resetn),
        .s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
        .s_rvalid(s_rvalid),.s_rready(s_rready),.s_rresp(s_rresp),
        .s_rdata(s_rdata),.m_arvalid(m_arvalid),.m_arready(m_arready),
        .m_araddr(m_araddr),.m_rvalid(m_rvalid),.m_rready(m_rready),
        .m_rresp(m_rresp),.m_rdata(m_rdata),.fault_sticky(fault_sticky),
        .fault_phase(fault_phase)
    );
    task full_ps_model_restart;
        begin
            // ONLY a simulated platform restart, not a safe Linux rearm.
            @(negedge ps_clock);
            ps_resetn=0; s_arvalid=0; s_rready=0;
            m_arready=0; m_rvalid=0; m_rresp=0; m_rdata=0;
            repeat(3) @(negedge ps_clock);
            ps_resetn=1;
            @(negedge ps_clock);
            if(s_rvalid!==0 || fault_sticky!==0 || s_arready!==1)
                $fatal(1,"reset of isolated abstract PS model did not finish");
        end
    endtask
    task issue_read;
        input [31:0] addr;
        begin
            @(negedge ps_clock);
            if(s_arready!==1) $fatal(1,"new read unexpectedly blocked");
            s_araddr=addr; s_arvalid=1;
            @(posedge ps_clock); #1;
            if(m_arvalid!==1 || m_araddr!==addr)
                $fatal(1,"PS model failed to latch expected read address");
            @(negedge ps_clock); s_arvalid=0;
        end
    endtask
    task expect_timeout;
        input [1:0] phase;
        begin
            repeat(9) @(posedge ps_clock);
            #1;
            if(s_rvalid!==1 || s_rresp!==2'b10 || s_rdata!==0 ||
               fault_sticky!==1 || fault_phase!==phase || m_arvalid!==0 ||
               m_rready!==0 || s_arready!==0)
                $fatal(1,"timeout did not bound and poison PS-side model");
            // RVALID/RRESP must remain unchanged if upstream cannot take the
            // synthetic error yet. A Python-side timer is NOT this guarantee.
            repeat(3) begin
                @(posedge ps_clock); #1;
                if(s_rvalid!==1 || s_rresp!==2'b10 || s_rdata!==0 ||
                   fault_sticky!==1 || s_arready!==0 || m_arvalid!==0)
                    $fatal(1,"synthetic timed-out error was not held under R backpressure");
            end
        end
    endtask
    task drain_error_and_assert_poison;
        begin
            @(negedge ps_clock); s_rready=1;
            @(posedge ps_clock); #1;
            if(s_rvalid!==0 || s_arready!==0 || m_arvalid!==0 ||
               fault_sticky!==1)
                $fatal(1,"timed-out read was automatically rearmed");
            @(negedge ps_clock); s_rready=0; s_arvalid=1;
            repeat(5) @(posedge ps_clock);
            #1;
            if(s_arready!==0 || m_arvalid!==0 || m_rready!==0 ||
               s_rvalid!==0 || fault_sticky!==1)
                $fatal(1,"subsequent read escaped sticky poison");
            @(negedge ps_clock); s_arvalid=0;
        end
    endtask
    initial begin
        full_ps_model_restart();

        // Normal response and RREADY backpressure, no poisoning.
        m_arready=1;
        issue_read(32'ha0000000);
        @(posedge ps_clock); #1;
        if(m_rready!==1 || m_arvalid!==0)
            $fatal(1,"normal downstream address handshake absent");
        @(negedge ps_clock);
        m_arready=0; m_rvalid=1;
        m_rresp=2'b00; m_rdata=32'h4d303831;
        @(posedge ps_clock); #1;
        if(s_rvalid!==1 || s_rdata!==32'h4d303831 ||
           s_rresp!==0 || fault_sticky!==0)
            $fatal(1,"good downstream response failed");
        @(negedge ps_clock); m_rvalid=0;
        repeat(4) begin
            @(posedge ps_clock); #1;
            if(s_rvalid!==1 || s_rdata!==32'h4d303831 || fault_sticky!==0)
                $fatal(1,"good response lost under upstream backpressure");
        end
        @(negedge ps_clock); s_rready=1;
        @(posedge ps_clock); #1;
        if(s_rvalid!==0 || s_arready!==1)
            $fatal(1,"normal read did not return to idle");
        $display("M08_D2_GUARD_NORMAL_READ_AND_BACKPRESSURE_PASS");

        // No downstream ARREADY while clocks otherwise run.
        full_ps_model_restart();
        issue_read(32'ha0000000);
        expect_timeout(2'd1);
        drain_error_and_assert_poison();
        $display("M08_D2_GUARD_MISSING_ARREADY_TIMEOUT_AND_POISON_PASS");

        // Downstream AR was accepted but RVALID never arrives.
        full_ps_model_restart();
        m_arready=1;
        issue_read(32'ha0000000);
        @(posedge ps_clock); #1;
        if(m_rready!==1) $fatal(1,"did not enter response wait");
        @(negedge ps_clock); m_arready=0;
        expect_timeout(2'd2);
        drain_error_and_assert_poison();
        // Unsolicited late response must NOT re-open the poisoned path.
        m_rvalid=1; m_rdata=32'hdeadbeef;
        repeat(3) @(posedge ps_clock);
        #1;
        if(m_rready!==0 || s_rvalid!==0 || s_arready!==0)
            $fatal(1,"late response reopened poison");
        @(negedge ps_clock); m_rvalid=0;
        $display("M08_D2_GUARD_MISSING_RVALID_LATE_RESPONSE_QUARANTINE_PASS");

        // PL clock removed BEFORE an AR handshake: PS ticks still time out.
        full_ps_model_restart();
        @(negedge ps_clock);
        pl_clock_running=0;
        repeat(2) @(posedge ps_clock);
        #1; prior_pl_edges=pl_edges; prior_ps_edges=ps_edges;
        issue_read(32'ha0000000);
        expect_timeout(2'd1);
        if(pl_edges!==prior_pl_edges || ps_edges<prior_ps_edges+6)
            $fatal(1,"PL loss did not demonstrate independent PS progress");
        drain_error_and_assert_poison();
        $display("M08_D2_GUARD_PL_CLOCK_ABSENT_UPSTREAM_BOUNDED_PASS");
        pl_clock_running=1;

        // PL clock removed AFTER address acceptance: no R, PS still bounds.
        full_ps_model_restart();
        m_arready=1;
        issue_read(32'ha0001000);
        @(posedge ps_clock); #1;
        if(m_rready!==1) $fatal(1,"response phase not reached");
        @(negedge ps_clock);
        m_arready=0; pl_clock_running=0; m_rvalid=0;
        repeat(2) @(posedge ps_clock);
        #1; prior_pl_edges=pl_edges;
        expect_timeout(2'd2);
        if(pl_edges!==prior_pl_edges)
            $fatal(1,"test PL clock unexpectedly active");
        drain_error_and_assert_poison();
        $display("M08_D2_GUARD_PL_STOPPED_AFTER_AR_TIMEOUT_PASS");
        pl_clock_running=1;

        // NEGATIVE: a PS-clocked timeout also dies if its PS clock dies.
        full_ps_model_restart();
        issue_read(32'ha0000000);
        @(negedge ps_clock);
        ps_clock_running=0;
        #120;
        if(s_rvalid!==0 || fault_sticky!==0 || m_arvalid!==1)
            $fatal(1,"PS clock loss incorrectly counted as guarded time");
        ps_clock_running=1;
        expect_timeout(2'd1);
        $display("M08_D2_GUARD_PS_CLOCK_ABSENT_IS_UNPROTECTED_NEGATIVE");
        $display("M08_D2_GUARD_ABSTRACT_PS_DOMAIN_CONTRACT_ALL_PASS_NO_HARDWARE_PROOF");
        $finish;
    end
    initial begin
        #50000;
        $fatal(1,"abstract PS-domain protection simulation deadlocked");
    end
endmodule
