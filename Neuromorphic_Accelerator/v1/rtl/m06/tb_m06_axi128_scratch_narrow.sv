// M06 scratch 128-bit AXI4 memory target standalone Icarus testbench.
// NO original vendor SmartConnect, NO physical DDR, NO FPGA board.
`timescale 1ns/1ps
module tb_m06_axi128_scratch_narrow;
    reg clk = 0;
    always #5 clk = ~clk;
    reg resetn = 0;
    reg [48:0] awaddr=0, araddr=0;
    reg [7:0] awlen=0, arlen=0;
    reg [2:0] awsize=3'd4, arsize=3'd4;
    reg [1:0] awburst=2'b01, arburst=2'b01;
    reg awvalid=0, wvalid=0, arvalid=0, bready=0, rready=0;
    reg [127:0] wdata=0;
    reg [15:0] wstrb=0;
    reg wlast=0;
    reg inject_b=0, inject_r=0;
    wire awready, wready, arready;
    wire [1:0] bresp, rresp;
    wire bvalid, rvalid, rlast;
    wire [127:0] rdata;

    m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536)) dut(
        .aclk(clk), .aresetn(resetn),
        .s_axi_awaddr(awaddr), .s_axi_awlen(awlen),
        .s_axi_awsize(awsize), .s_axi_awburst(awburst),
        .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(wstrb), .s_axi_wlast(wlast),
        .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
        .s_axi_araddr(araddr), .s_axi_arlen(arlen),
        .s_axi_arsize(arsize), .s_axi_arburst(arburst),
        .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp),
        .s_axi_rlast(rlast), .s_axi_rvalid(rvalid), .s_axi_rready(rready),
        .inject_next_b_slverr(inject_b),
        .inject_next_r_slverr(inject_r)
    );
    reg [7:0] expected_memory [0:65535];
    integer i;
    integer observed_ready_stalls=0;
    integer observed_write_responses=0;
    integer observed_read_beats=0;

    function automatic [127:0] expected_word;
        input integer addr;
        integer b;
        begin
            expected_word=0;
            for (b=0; b<16; b=b+1)
                expected_word[8*b +:8] = expected_memory[addr+b];
        end
    endfunction

    task automatic issue_aw;
        input [48:0] addr;
        input [7:0] beats_minus_1;
        begin
            @(negedge clk);
            awaddr=addr;
            awlen=beats_minus_1;
            awvalid=1;
            @(posedge clk);
            while (!awready) begin
                observed_ready_stalls=observed_ready_stalls+1;
                @(posedge clk);
            end
            @(negedge clk);
            awvalid=0;
        end
    endtask

    task automatic issue_w;
        input [127:0] payload;
        input [15:0] mask;
        input integer addr;
        input last;
        input apply_to_expected;
        integer lane;
        begin
            @(negedge clk);
            wdata=payload;
            wstrb=mask;
            wlast=last;
            wvalid=1;
            @(posedge clk);
            while (!wready) begin
                observed_ready_stalls=observed_ready_stalls+1;
                @(posedge clk);
            end
            for (lane=0; lane<16; lane=lane+1) begin
                if (apply_to_expected && mask[lane])
                    expected_memory[addr+lane]=payload[8*lane +:8];
            end
            @(negedge clk);
            wvalid=0;
            wlast=0;
        end
    endtask

    task automatic expect_b;
        input [1:0] expected_resp;
        reg [1:0] held_resp;
        integer delay_cycles;
        begin
            @(posedge clk);
            while (!bvalid) @(posedge clk);
            held_resp=bresp;
            if (held_resp !== expected_resp)
                $fatal(1,"BAD B response got %b want %b",bresp,expected_resp);
            for (delay_cycles=0; delay_cycles<3; delay_cycles=delay_cycles+1) begin
                @(posedge clk);
                if (!bvalid || bresp !== held_resp)
                    $fatal(1,"BVALID/BRESP changed under BREADY stall");
            end
            @(negedge clk);
            bready=1;
            @(posedge clk);
            if (!bvalid || bresp !== expected_resp)
                $fatal(1,"B response changed on final B handshake");
            @(negedge clk);
            bready=0;
            observed_write_responses=observed_write_responses+1;
        end
    endtask

    task automatic issue_ar;
        input [48:0] addr;
        input [7:0] beats_minus_1;
        begin
            @(negedge clk);
            araddr=addr;
            arlen=beats_minus_1;
            arvalid=1;
            @(posedge clk);
            while (!arready) begin
                observed_ready_stalls=observed_ready_stalls+1;
                @(posedge clk);
            end
            @(negedge clk);
            arvalid=0;
        end
    endtask

    task automatic expect_r;
        input [127:0] wanted;
        input [1:0] wanted_resp;
        input last;
        reg [127:0] held;
        integer delay_cycles;
        begin
            @(posedge clk);
            while (!rvalid) @(posedge clk);
            held=rdata;
            if (rdata !== wanted || rresp !== wanted_resp ||
                rlast !== last)
                $fatal(1,"BAD R DATA/RESP/LAST data=%h resp=%b last=%b",rdata,rresp,rlast);
            for (delay_cycles=0; delay_cycles<2; delay_cycles=delay_cycles+1) begin
                @(posedge clk);
                if (!rvalid || rdata !== held ||
                    rresp !== wanted_resp || rlast !== last)
                    $fatal(1,"RDATA/RRESP/RLAST unstable while RREADY low");
            end
            @(negedge clk);
            rready=1;
            @(posedge clk);
            if (!rvalid || rdata !== wanted || rresp !== wanted_resp ||
                rlast !== last)
                $fatal(1,"R data changed before accepted R handshake");
            @(negedge clk);
            rready=0;
            observed_read_beats=observed_read_beats+1;
        end
    endtask

    initial begin
        for (i=0;i<65536;i=i+1)
            expected_memory[i] = (13*i+17) & 255;
        repeat (5) @(negedge clk);
        resetn=1;
        // Two downstream full-width INCR beats with noncontiguous strobes
        // proving low lane0/high lane15 and independent high/low halves.
        issue_aw(49'h120,8'd1);
        issue_w(128'hffeeddccbbaa99887766554433221100,16'h8001,16'h120,0,1);
        issue_w(128'h00112233445566778899aabbccddeeff,16'h00ff,16'h130,1,1);
        expect_b(2'b00);
        issue_ar(49'h120,8'd1);
        expect_r(expected_word('h120),2'b00,0);
        expect_r(expected_word('h130),2'b00,1);

        // Intentional unsupported crossing 4KiB AW and AR: must DECERR.
        issue_aw(49'hff0,8'd1);
        issue_w(128'h00,16'hffff,16'hff0,0,0);
        issue_w(128'h11,16'hffff,16'h1000,1,0);
        expect_b(2'b11);
        issue_ar(49'hff0,8'd1);
        expect_r(128'd0,2'b11,0);
        expect_r(128'd0,2'b11,1);

        // A completed physical W beat with SLVERR response can leave memory
        // modified. The future pager must quarantine unknown-commit state.
        @(negedge clk);
        inject_b=1;
        issue_aw(49'h300,8'd0);
        @(negedge clk);
        inject_b=0;
        issue_w(128'h0123456789abcdefabcdef0123456789,16'hffff,16'h300,1,1);
        expect_b(2'b10);
        @(negedge clk);
        inject_r=1;
        issue_ar(49'h300,8'd0);
        @(negedge clk);
        inject_r=0;
        expect_r(expected_word('h300),2'b10,1);
        issue_ar(49'h300,8'd0);
        expect_r(expected_word('h300),2'b00,1);

        if (observed_ready_stalls==0)
            $fatal(1,"READY backpressure was never observed");
        if (observed_write_responses!=3 || observed_read_beats!=6)
            $fatal(1,"scratch AXI scoreboard count mismatch W=%0d R=%0d",
                   observed_write_responses,observed_read_beats);
        $display("M06_AXI128_SCRATCH_STANDALONE_PASS writes=%0d reads=%0d stalls=%0d | NO_VENDOR_XSIM_NO_DDR",
                 observed_write_responses,observed_read_beats,
                 observed_ready_stalls);

        // Direct BFM regression of the corrected aligned narrow AXI subset.
        // These tests execute THIS real simulation-only memory model, not an
        // AMD converter/SmartConnect. Original full-width tests already PASS.
        arsize=3'd2;
        issue_ar(49'h0,0);
        expect_r(expected_word('h0),2'b00,1);
        issue_ar(49'hffc,0);
        expect_r(expected_word('hff0),2'b00,1);
        issue_ar(49'h1000,0);
        expect_r(expected_word('h1000),2'b00,1);
        issue_ar(49'hfffc,0);
        expect_r(expected_word('hfff0),2'b00,1);

        arsize=3'd4;
        issue_ar(49'hfff0,0);
        expect_r(expected_word('hfff0),2'b00,1);

        awsize=3'd2;
        issue_aw(49'hfffc,0);
        issue_w(128'hffeeddccbbaa99887766554433221100,
                16'h5000,'hfff0,1,1);
        expect_b(2'b00);
        arsize=3'd2;
        issue_ar(49'hfffc,0);
        expect_r(expected_word('hfff0),2'b00,1);
        arsize=3'd4;
        issue_ar(49'hfff0,0);
        expect_r(expected_word('hfff0),2'b00,1);

        awsize=3'd1; // 2-byte transfer at physical lanes 10 and 11
        issue_aw(49'h10a,0);
        issue_w(128'h1234567890abcdef0102030405060708,
                16'h0800,'h100,1,1);
        expect_b(2'b00);
        arsize=3'd4;
        issue_ar(49'h100,0);
        expect_r(expected_word('h100),2'b00,1);

        awsize=3'd3; // 8-byte narrow transfer in upper half of 128b beat
        issue_aw(49'h208,0);
        issue_w(128'h1234567890abcdef0102030405060708,
                16'hff00,'h200,1,1);
        expect_b(2'b00);
        arsize=3'd4;
        issue_ar(49'h200,0);
        expect_r(expected_word('h200),2'b00,1);

        // Six 4-byte beats: lane selection and burst stride must roll over
        // from one physical 16-byte word to the next without skipping bytes.
        arsize=3'd2;
        issue_ar(49'h118,8'd5);
        for (i=0;i<6;i=i+1)
            expect_r(expected_word(('h118+4*i)&'hfff0),2'b00,(i==5));

        // A WSTRB outside the addressed 4 byte lanes is not permitted.
        // This beat must not mutate any byte, and must return SLVERR.
        awsize=3'd2;
        issue_aw(49'h200,0);
        issue_w(128'hffffffffffffffffffffffffffffffff,
                16'h0010,'h200,1,0);
        expect_b(2'b10);
        arsize=3'd4;
        issue_ar(49'h200,0);
        expect_r(expected_word('h200),2'b00,1);

        // Too-wide AXI SIZE=5 is illegal on this 128-bit endpoint.
        awsize=3'd5;
        issue_aw(49'h220,0);
        issue_w(128'hffffffffffffffffffffffffffffffff,
                16'hffff,'h220,1,0);
        expect_b(2'b11);
        arsize=3'd4;
        issue_ar(49'h220,0);
        expect_r(expected_word('h220),2'b00,1);
        arsize=3'd5;
        issue_ar(49'h100,0);
        expect_r(128'd0,2'b11,1);

        // Unsupported unaligned 4B access, crossing 4KiB, beyond 64KiB.
        arsize=3'd2;
        issue_ar(49'h101,0);
        expect_r(128'd0,2'b11,1);
        issue_ar(49'hffc,8'd1);
        expect_r(128'd0,2'b11,0);
        expect_r(128'd0,2'b11,1);
        issue_ar(49'h10000,0);
        expect_r(128'd0,2'b11,1);

        if (observed_write_responses!=8 || observed_read_beats!=28)
            $fatal(1,"M06_AXI128_NARROW_FAIL COUNTS B=%0d R=%0d",
                   observed_write_responses,observed_read_beats);
        $display("M06_AXI128_NARROW_64K_PASS B=%0d R=%0d LAST_FFFC=1 4K_CROSS_DECERR=1 INVALID_WSTRB_SLVERR=1 NO_VENDOR_NO_BOARD",
                 observed_write_responses,observed_read_beats);
        $finish;
    end
    initial begin
        #120000;
        $fatal(1,"M06_AXI128_NARROW_FAIL WATCHDOG");
    end
endmodule
