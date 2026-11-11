// Icarus directed AXI-Lite protocol tests for M08 standalone readonly probe.
// Pure local simulation; does NOT connect PS, DMA, physical DDR, or a KV260.
`timescale 1ns/1ps
module tb_m08_axil_readonly_identity;
    reg clk=0;
    always #5 clk=~clk;
    reg resetn=0;
    reg [7:0] awaddr=0;
    reg [2:0] awprot=0;
    reg awvalid=0;
    wire awready;
    reg [31:0] wdata=0;
    reg [3:0] wstrb=0;
    reg wvalid=0;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready=0;
    reg [7:0] araddr=0;
    reg [2:0] arprot=0;
    reg arvalid=0;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready=0;

    m08_axil_readonly_identity #(
        .BUILD_ID0(32'hA0B1C2D3),
        .BUILD_ID1(32'h11223344),
        .BUILD_ID2(32'h55667788),
        .BUILD_ID3(32'h99AABBCC)
    ) dut (
        .aclk(clk), .aresetn(resetn),
        .s_axi_awaddr(awaddr), .s_axi_awprot(awprot),
        .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(wstrb),
        .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
        .s_axi_araddr(araddr), .s_axi_arprot(arprot),
        .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid), .s_axi_rready(rready)
    );

    integer read_count=0;
    integer write_count=0;
    integer k;

    task automatic read_reg(
        input [7:0] address,
        input [31:0] expected,
        input [1:0] response
    );
        begin
            @(negedge clk);
            araddr=address;
            arvalid=1;
            if (!arready) $fatal(1,"ARREADY absent for fresh read");
            @(posedge clk);
            @(negedge clk);
            arvalid=0;
            if (!rvalid || rdata!==expected || rresp!==response)
                $fatal(1,"read mismatch addr=%h value=%h resp=%b",address,rdata,rresp);
            // Hold RVALID/RDATA/RRESP under downstream stall.
            repeat (3) begin
                @(posedge clk);
                if (!rvalid || rdata!==expected || rresp!==response)
                    $fatal(1,"R changed under backpressure addr=%h",address);
            end
            @(negedge clk);
            rready=1;
            @(posedge clk);
            @(negedge clk);
            rready=0;
            if (rvalid) $fatal(1,"RVALID not cleared after handshake");
            read_count=read_count+1;
        end
    endtask

    // mode 0=AW then W, 1=W then AW, 2=same-cycle AW+W.
    task automatic rejected_write(input integer mode, input [7:0] address);
        begin
            @(negedge clk);
            awaddr=address;
            wdata=32'hDEADBEEF;
            wstrb=4'hF;
            if (mode==0 || mode==2) awvalid=1;
            if (mode==1 || mode==2) wvalid=1;
            if (mode==2 && !(awready && wready))
                $fatal(1,"both write lanes not ready");
            @(posedge clk);
            @(negedge clk);
            if (mode==0 || mode==2) awvalid=0;
            if (mode==1 || mode==2) wvalid=0;
            if (mode==0) begin
                // AW alone must NOT produce an early B.
                if (bvalid) $fatal(1,"B before W");
                repeat (2) @(posedge clk);
                @(negedge clk);
                wvalid=1;
                if (!wready) $fatal(1,"W not ready after AW");
                @(posedge clk);
                @(negedge clk);
                wvalid=0;
            end else if (mode==1) begin
                if (bvalid) $fatal(1,"B before AW");
                repeat (2) @(posedge clk);
                @(negedge clk);
                awvalid=1;
                if (!awready) $fatal(1,"AW not ready after W");
                @(posedge clk);
                @(negedge clk);
                awvalid=0;
            end
            if (!bvalid || bresp!==2'b10)
                $fatal(1,"read-only write not rejected with SLVERR");
            repeat (3) begin
                @(posedge clk);
                if (!bvalid || bresp!==2'b10)
                    $fatal(1,"B changed during backpressure");
            end
            @(negedge clk);
            bready=1;
            @(posedge clk);
            @(negedge clk);
            bready=0;
            if (bvalid) $fatal(1,"BVALID retained after handshake");
            write_count=write_count+1;
        end
    endtask

    initial begin
        repeat (4) @(posedge clk);
        @(negedge clk);
        resetn=1;
        read_reg(8'h00,32'h4D303831,2'b00);
        read_reg(8'h04,32'h00010000,2'b00);
        read_reg(8'h08,32'h00000000,2'b00);  // no DMA-master capability
        read_reg(8'h0c,32'h00000000,2'b00);
        read_reg(8'h10,32'hA0B1C2D3,2'b00);
        read_reg(8'h14,32'h11223344,2'b00);
        read_reg(8'h18,32'h55667788,2'b00);
        read_reg(8'h1c,32'h99AABBCC,2'b00);
        read_reg(8'h20,32'h00000000,2'b11);  // unknown -> DECERR, no alias
        read_reg(8'h01,32'h00000000,2'b11);  // misalignment -> DECERR
        rejected_write(0,8'h00);
        rejected_write(1,8'h10);
        rejected_write(2,8'hff);
        read_reg(8'h00,32'h4D303831,2'b00);  // writes changed nothing
        read_reg(8'h10,32'hA0B1C2D3,2'b00);
        // Reset must drop a stale half-write. W alone after reset cannot
        // complete an old AW from the prior epoch.
        @(negedge clk); awvalid=1; awaddr=0;
        @(posedge clk);
        @(negedge clk); awvalid=0; resetn=0;
        repeat (2) @(posedge clk);
        @(negedge clk); resetn=1; wvalid=1;
        @(posedge clk);
        @(negedge clk); wvalid=0;
        if (bvalid) $fatal(1,"stale AW survived reset");
        // complete the new fresh W with fresh AW and check SLVERR.
        @(negedge clk); awvalid=1;
        @(posedge clk);
        @(negedge clk); awvalid=0;
        if (!bvalid || bresp!==2'b10)
            $fatal(1,"post-reset fresh AW/W did not reject");
        @(negedge clk); bready=1;
        @(posedge clk);
        @(negedge clk); bready=0;
        read_reg(8'h00,32'h4D303831,2'b00);
        if (read_count!=13 || write_count!=3)
            $fatal(1,"test count mismatch reads=%0d writes=%0d",read_count,write_count);
        $display("M08_AXIL_IDENTITY_STANDALONE_ICARUS_PASS READS=%0d REJECTED_WRITES=%0d NO_DMA",
                 read_count,write_count);
        $finish;
    end
    initial begin
        #50000;
        $fatal(1,"M08 standalone AXI-Lite identity timeout");
    end
endmodule
