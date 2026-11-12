// M08 D2: genuine first-party identity RTL in a controlled offline fault TB.
// Does NOT model AMD PS, SmartConnect, ATB, board clocks, Linux or physical MMIO.
// An absent clock cannot make this slave return an AXI response.  Separately,
// a deliberately silent mock demonstrates why a PS-facing timeout is required.
// Neither observation proves the root cause of the owner's RCU stall.
`timescale 1ns/1ps
module tb_m08_axil_identity_stall_forensics;
    reg aclk=0;
    reg clock_enabled=1;
    always #5 begin
        if (clock_enabled) aclk=~aclk;
        else aclk=0;
    end
    reg aresetn=0;
    reg [7:0] araddr=0;
    reg arvalid=0;
    wire arready;
    reg rready=0;
    wire rvalid;
    wire [31:0] rdata;
    wire [1:0] rresp;
    reg awvalid=0, wvalid=0, bready=0;
    wire awready, wready, bvalid;
    wire [1:0] bresp;

    m08_axil_readonly_identity #(.BUILD_ID0(32'h01234567)) dut (
        .aclk(aclk), .aresetn(aresetn),
        .s_axi_awaddr(8'd0), .s_axi_awprot(3'd0),
        .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(32'd0), .s_axi_wstrb(4'd0),
        .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
        .s_axi_araddr(araddr), .s_axi_arprot(3'd0),
        .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid), .s_axi_rready(rready)
    );

    // Intentional negative *mock*, NOT a PS/SmartConnect simulation.
    // With no ready and no response, a requesting master cannot complete.
    reg silent_arvalid=0;
    wire silent_arready=1'b0;
    wire silent_rvalid=1'b0;
    integer cycles;
    initial begin
        // Reset gating: a request held during reset must not be accepted.
        arvalid=1;
        araddr=8'h00;
        repeat (4) begin
            @(negedge aclk);
            if (arready!==1'b0 || rvalid!==1'b0)
                $fatal(1,"identity accepted AR / returned R during reset");
        end
        arvalid=0;
        aresetn=1;
        repeat (3) @(negedge aclk);
        if (rvalid!==1'b0) $fatal(1,"stale read survived reset release");
        $display("M08_D2_IDENTITY_RESET_SEQUENCE_ICARUS_PASS");

        // Accepted read: RVALID must remain stable throughout long RREADY=0.
        araddr=8'h10; arvalid=1;
        if (arready!==1'b1) $fatal(1,"fresh ARREADY absent");
        @(posedge aclk);
        @(negedge aclk);
        arvalid=0;
        if (rvalid!==1'b1 || rresp!==2'b00 || rdata!==32'h01234567)
            $fatal(1,"identity did not generate expected registered R");
        araddr=8'h00; arvalid=1;
        for (cycles=0;cycles<25;cycles=cycles+1) begin
            @(negedge aclk);
            if (rvalid!==1'b1 || arready!==1'b0 ||
                rresp!==2'b00 || rdata!==32'h01234567)
                $fatal(1,"response changed or new AR accepted under R stall");
        end
        arvalid=0; rready=1;
        @(posedge aclk);
        @(negedge aclk);
        rready=0;
        if (rvalid!==1'b0) $fatal(1,"RVALID retained after RREADY");
        $display("M08_D2_IDENTITY_R_BACKPRESSURE_ICARUS_PASS");

        // Reset with an outstanding RVALID discards old response.
        araddr=8'h00; arvalid=1;
        @(posedge aclk);
        @(negedge aclk);
        arvalid=0;
        if (rvalid!==1'b1) $fatal(1,"pre-reset response missing");
        aresetn=0;
        @(posedge aclk);
        @(negedge aclk);
        if (rvalid!==1'b0 || arready!==1'b0)
            $fatal(1,"reset failed to clear pending R");
        aresetn=1;
        repeat (3) @(negedge aclk);
        if (rvalid!==1'b0) $fatal(1,"ghost R after reset");
        $display("M08_D2_IDENTITY_MID_RESPONSE_RESET_ICARUS_PASS");

        // With aclk absent, combinational ARREADY is NOT proof of a
        // sampled address: RVALID cannot advance until clock returns.
        clock_enabled=0;
        araddr=8'h00; arvalid=1;
        #120;
        if (aclk!==1'b0 || rvalid!==1'b0 || arready!==1'b1)
            $fatal(1,"halted-clock model assumptions changed");
        $display("M08_D2_IDENTITY_STOPPED_CLOCK_NO_R_RESPONSE_EXPECTED");
        arvalid=0;
        clock_enabled=1;
        repeat (4) @(negedge aclk);
        if (rvalid!==1'b0)
            $fatal(1,"phantom response after stopped-clock interval");

        // Independent silent *slave* with running clock: no AR handshake and
        // no R response in 64 cycles. THIS IS AN EXPECTED UNPROTECTED STALL,
        // NOT a successful timeout, isolation mechanism or AXI-error test.
        silent_arvalid=1;
        for (cycles=0;cycles<64;cycles=cycles+1) begin
            @(posedge aclk);
            if (silent_arready!==1'b0 || silent_rvalid!==1'b0)
                $fatal(1,"silent slave unexpectedly acknowledged");
        end
        silent_arvalid=0;
        $display("M08_D2_SILENT_SLAVE_EXPECTED_NO_RESPONSE_NO_PROTECTION");
        $finish;
    end
    initial begin
        #20000;
        $fatal(1,"M08 D2 offline TB itself timed out");
    end
endmodule
