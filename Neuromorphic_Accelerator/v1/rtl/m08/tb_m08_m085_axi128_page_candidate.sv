`timescale 1ns/1ps
// Actual Icarus AXI4 handshake simulation, NOT fake 'downstream_done'.
// Read/write full 256B, every 128-bit lane, stalls, BRESP/RRESP/RLAST,
// invalid address/page/epoch, timeout, orphan response and lease failure.
// 0x1000 is only an abstract simulator range, NEVER a K26 address.
module tb_m08_m085_axi128_page_candidate;
    reg clk=0; always #5 clk=~clk;
    reg resetn=0,owner_lease_active=1,compute_idle=1,page_bank_idle=1;
    reg req=0,req_write=0;
    reg [63:0] req_addr=64'h1000;
    reg [15:0] req_size_bytes=256;
    reg [31:0] req_logical_page=2,req_tick=1;
    reg [2047:0] req_write_page=0;
    wire ack,error,busy,poisoned,completed_write,read_page_valid;
    wire [31:0] completed_page,completed_tick,completed_page_transfers;
    wire [31:0] completed_axi_read_bursts,completed_axi_write_bursts,completed_axi_bytes;
    wire [2047:0] read_page_data;
    wire [48:0] awaddr,araddr;
    wire [7:0] awlen,arlen;
    wire [2:0] awsize,arsize;
    wire [1:0] awburst,arburst;
    wire awvalid,wvalid,wlast,bready,arvalid,rready;
    wire [127:0] wdata;
    wire [15:0] wstrb;
    reg awready=0,wready=0,bvalid=0,arready=0,rvalid=0;
    reg [1:0] bresp=0,rresp=0;
    reg [127:0] rdata=0;
    reg rlast=0;
    reg [2047:0] accepted_write_page=0, expected_read=0;
    integer aw_count=0,w_count=0,b_count=0,ar_count=0,r_count=0;
    integer case_id=0,i,j;

    m08_m085_axi128_page_candidate #(
        .WINDOW_BEGIN(64'h1000),.WINDOW_END(64'h2000),
        .GUARD_WAIT_CYCLES(128),.AXI_STALL_CYCLES(8)
    ) dut(
        .clk(clk),.resetn(resetn),.owner_lease_active(owner_lease_active),
        .compute_idle(compute_idle),.page_bank_idle(page_bank_idle),
        .req(req),.req_write(req_write),.req_addr(req_addr),
        .req_size_bytes(req_size_bytes),.req_logical_page(req_logical_page),
        .req_tick(req_tick),.req_write_page(req_write_page),
        .ack(ack),.error(error),.busy(busy),.poisoned(poisoned),
        .completed_page(completed_page),.completed_tick(completed_tick),
        .completed_write(completed_write),
        .completed_page_transfers(completed_page_transfers),
        .read_page_valid(read_page_valid),.read_page_data(read_page_data),
        .completed_axi_read_bursts(completed_axi_read_bursts),
        .completed_axi_write_bursts(completed_axi_write_bursts),
        .completed_axi_bytes(completed_axi_bytes),
        .m_axi_awaddr(awaddr),.m_axi_awlen(awlen),.m_axi_awsize(awsize),
        .m_axi_awburst(awburst),.m_axi_awvalid(awvalid),
        .m_axi_awready(awready),
        .m_axi_wdata(wdata),.m_axi_wstrb(wstrb),.m_axi_wlast(wlast),
        .m_axi_wvalid(wvalid),.m_axi_wready(wready),
        .m_axi_bresp(bresp),.m_axi_bvalid(bvalid),.m_axi_bready(bready),
        .m_axi_araddr(araddr),.m_axi_arlen(arlen),.m_axi_arsize(arsize),
        .m_axi_arburst(arburst),.m_axi_arvalid(arvalid),
        .m_axi_arready(arready),
        .m_axi_rdata(rdata),.m_axi_rresp(rresp),.m_axi_rlast(rlast),
        .m_axi_rvalid(rvalid),.m_axi_rready(rready)
    );

    // Score actual AXI handshakes, not command assertions or cycles.
    always @(posedge clk) if(resetn) begin
        if(awvalid && awready) begin
            if (awlen!==8'd15 || awsize!==3'd4 || awburst!==2'b01 ||
                awaddr[7:0]!==8'd0)
                $fatal(1,"wrong AW shape");
            aw_count=aw_count+1;
        end
        if(wvalid && wready) begin
            if (w_count>=16 || wdata !== accepted_write_page[w_count*128 +:128]
                || wstrb!==16'hFFFF || wlast !== (w_count==15))
                $fatal(1,"write payload/lane/strobe/last mismatch beat=%0d",w_count);
            w_count=w_count+1;
        end
        if(bvalid && bready) b_count=b_count+1;
        if(arvalid && arready) begin
            if(arlen!==8'd15 || arsize!==3'd4 || arburst!==2'b01 ||
               araddr[7:0]!==8'd0)
                $fatal(1,"wrong AR shape");
            ar_count=ar_count+1;
        end
        if(rvalid && rready) r_count=r_count+1;
    end

    task launch;
        input direction;
        begin
            @(negedge clk); req_write=direction; req=1;
            @(posedge clk); #1;
            @(negedge clk); req=0;
        end
    endtask
    task handshake_aw;
        begin
            wait(awvalid);
            repeat(2) begin
                @(posedge clk); #1;
                if(!awvalid || awaddr!==req_addr[48:0])
                    $fatal(1,"AW failed stall stable");
            end
            @(negedge clk); awready=1;
            @(posedge clk); #1;
            @(negedge clk); awready=0;
        end
    endtask
    task handshake_ar;
        begin
            wait(arvalid);
            repeat(2) begin
                @(posedge clk); #1;
                if(!arvalid || araddr!==req_addr[48:0])
                    $fatal(1,"AR failed stall stable");
            end
            @(negedge clk); arready=1;
            @(posedge clk); #1;
            @(negedge clk); arready=0;
        end
    endtask
    task handshake_w;
        input integer beats;
        integer k;
        begin
            for(k=0;k<beats;k=k+1) begin
                // Stable under backpressure, including the final beat.
                repeat(2) begin
                    @(posedge clk); #1;
                    if(!wvalid || wdata !== accepted_write_page[k*128 +:128] ||
                       wlast !== (k==15) || wstrb!==16'hFFFF)
                        $fatal(1,"W changed while stalled, beat=%0d",k);
                end
                @(negedge clk);wready=1;
                @(posedge clk);#1;
                @(negedge clk);wready=0;
            end
        end
    endtask
    task handshake_b;
        input [1:0] response;
        begin
            if(!bready)$fatal(1,"no BREADY after last W");
            @(negedge clk);bvalid=1;bresp=response;
            @(posedge clk);#1;
            @(negedge clk);bvalid=0;
        end
    endtask
    task handshake_r;
        input integer index;
        input [1:0] response;
        input last;
        begin
            if(!rready)$fatal(1,"no RREADY after AR");
            @(negedge clk);
            rdata=expected_read[index*128 +:128];rresp=response;
            rlast=last;rvalid=1;
            @(posedge clk);#1;
            @(negedge clk);rvalid=0;rlast=0;
        end
    endtask
    task expect_accepted;
        input is_read;
        begin
            @(posedge clk);#1;
            if(!ack || poisoned || completed_page_transfers==0 ||
                read_page_valid !== is_read)
                $fatal(1,"accepted AXI not promoted through guard case=%0d",case_id);
            if(is_read && read_page_data!==expected_read)
                $fatal(1,"read page 256B bytes changed");
            @(posedge clk);#1;
            if(ack || read_page_valid || read_page_data!==2048'd0)
                $fatal(1,"page result reasserted after one pulse");
        end
    endtask
    task expect_poison;
        integer k;
        begin
            for(k=0;k<25 && !poisoned;k=k+1) begin
                @(posedge clk);#1;
            end
            if(!poisoned)
                $fatal(1,"no sticky fault case=%0d",case_id);
            @(negedge clk);
            req=0;awready=1;wready=1;arready=1;
            bvalid=0;rvalid=0;
            repeat(3) @(posedge clk);
            #1;
            if(!poisoned || ack || read_page_valid || busy ||
                awvalid || wvalid || arvalid ||
                completed_page_transfers != 0 || completed_axi_bytes!=0)
                $fatal(1,"fault leaked page or AXI request case=%0d",case_id);
            $display("M08_5_REAL_AXI128_256B_NEGATIVE_PASS case=%0d",case_id);
        end
    endtask

    initial begin
        if(!$value$plusargs("CASE=%d",case_id))case_id=0;
        for(i=0;i<256;i=i+1) begin
            req_write_page[i*8 +:8]=i[7:0]^8'hA5;
            expected_read[i*8 +:8]=i[7:0]^8'h5A;
        end
        accepted_write_page=req_write_page;
        repeat(3) @(negedge clk);
        resetn=1;
        @(posedge clk);#1;
        case(case_id)
            0: begin
                // Write exact 16 beats. Change external page after accepted
                // command and verify all captured W lanes remain unchanged.
                launch(1'b1);
                @(negedge clk);req_write_page=~accepted_write_page;
                handshake_aw();
                handshake_w(16);
                if(aw_count!=1||w_count!=16||b_count!=0||ack)
                    $fatal(1,"write acknowledged before B response");
                handshake_b(2'b00);
                expect_accepted(1'b0);
                if(completed_axi_write_bursts!=1||completed_axi_bytes!=256 ||
                   completed_page!=2 || completed_tick!=1 || !completed_write)
                    $fatal(1,"write receipt mismatched");
                // Read next page/tick, verify exact 2048-bit result at ACK.
                @(negedge clk);
                req_addr=64'h1100;req_logical_page=4;req_tick=3;
                launch(1'b0);
                handshake_ar();
                for(i=0;i<16;i=i+1)
                    handshake_r(i,2'b00,(i==15));
                expect_accepted(1'b1);
                if(ar_count!=1||r_count!=16 || completed_axi_read_bursts!=1 ||
                   completed_axi_write_bursts!=1 || completed_axi_bytes!=512 ||
                   completed_page_transfers!=2 || completed_write ||
                   completed_page!=4 || completed_tick!=3)
                    $fatal(1,"read/write real burst counters invalid");
                $display("M08_5_REAL_AXI128_256B_READ_WRITE_AND_512_BYTES_PASS");
            end
            1: begin req_addr=64'h1080;launch(0);expect_poison();end
            2: begin req_size_bytes=128;launch(0);expect_poison();end
            3: begin req_logical_page=6;launch(0);expect_poison();end
            4: begin req_tick=4;launch(0);expect_poison();end
            5: begin owner_lease_active=0;launch(0);expect_poison();end
            6: begin launch(1);handshake_aw();handshake_w(16);
                     handshake_b(2'b10);expect_poison();end
            7: begin launch(0);handshake_ar();handshake_r(0,0,1);
                     expect_poison();end
            8: begin launch(0);handshake_ar();
                     for(i=0;i<16;i=i+1)handshake_r(i,0,0);
                     expect_poison();end
            9: begin launch(0);handshake_ar();handshake_r(0,2'b10,0);
                     expect_poison();end
            10: begin launch(0);expect_poison();end // stalled ARREADY
            11: begin launch(1);handshake_aw();expect_poison();end // stalled WREADY
            12: begin launch(1);handshake_aw();handshake_w(16);
                      expect_poison();end // missing BVALID
            13: begin launch(0);handshake_ar();expect_poison();end // missing RVALID
            14: begin launch(0);handshake_ar();
                      @(negedge clk);owner_lease_active=0;
                      expect_poison();end
            15: begin launch(0);handshake_ar();
                      @(negedge clk);compute_idle=0;
                      expect_poison();end
            16: begin launch(1);handshake_aw();
                      @(negedge clk);page_bank_idle=0;
                      expect_poison();end
            17: begin @(negedge clk);bvalid=1;expect_poison();end
            18: begin @(negedge clk);rvalid=1;expect_poison();end
            19: begin launch(1);handshake_aw();
                      @(negedge clk);req=1;
                      expect_poison();end
            20: begin req_addr=64'h2000;launch(0);expect_poison();end
            21: begin req_addr=64'h0002_0000_0000_1000;launch(0);expect_poison();end
            22: begin launch(0);handshake_ar();
                      @(negedge clk);bvalid=1;expect_poison();end
            23: begin launch(1);handshake_aw();
                      @(negedge clk);rvalid=1;expect_poison();end
            default: $fatal(1,"unknown case");
        endcase
        $finish;
    end
    initial begin #100000; $fatal(1,"AXI source test timed out case=%0d",case_id);end
endmodule
