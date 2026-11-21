// Real Icarus AXI4-Lite 5-channel protocol test over the actual M08.5
// trusted CSR decoder + unchanged DMA lease fence. All platform attestation,
// DDR, and interconnect drain acknowledgments are FAKE testbench inputs.
// This does NOT program KV260, connect PS HPM0/HP0, or prove safe DMA release.
module tb_m08_m085_axil_control_candidate;
    reg clk=0; always #5 clk=~clk;
    reg resetn=0;
    reg [11:0] awaddr=0,araddr=0;
    reg [2:0] awprot=0,arprot=0;
    reg awvalid=0,wvalid=0,arvalid=0,bready=0,rready=0;
    reg [31:0] wdata=0;
    reg [3:0] wstrb=4'hf;
    wire awready,wready,arready,bvalid,rvalid;
    wire [1:0] bresp,rresp;
    wire [31:0] rdata;
    reg csr_trusted=1,driver_bound_verified=1,control_route_verified=1;
    reg interconnect_drain_ack=1,transport_idle=1,bank_clean_idle=1;
    wire admit_work,stop_new_requests,drain_request,lease_granted;
    wire lease_sealed,lease_poisoned;
    wire [31:0] active_generation;
    wire [63:0] admitted_begin,admitted_end;
    integer case_id=0,k;
    m08_m085_axil_control_candidate #(
        .DRAIN_TIMEOUT_CYCLES(16)
    ) dut(
        .clk(clk),.resetn(resetn),
        .s_axi_awaddr(awaddr),.s_axi_awprot(awprot),
        .s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),
        .s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
        .s_axi_araddr(araddr),.s_axi_arprot(arprot),
        .s_axi_arvalid(arvalid),.s_axi_arready(arready),
        .s_axi_rdata(rdata),.s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid),.s_axi_rready(rready),
        .csr_trusted(csr_trusted),
        .driver_bound_verified(driver_bound_verified),
        .control_route_verified(control_route_verified),
        .interconnect_drain_ack(interconnect_drain_ack),
        .transport_idle(transport_idle),.bank_clean_idle(bank_clean_idle),
        .admit_work(admit_work),.stop_new_requests(stop_new_requests),
        .drain_request(drain_request),.lease_granted(lease_granted),
        .lease_sealed(lease_sealed),.lease_poisoned(lease_poisoned),
        .active_generation(active_generation),
        .admitted_begin(admitted_begin),.admitted_end(admitted_end)
    );
    task send_aw;
        input [11:0] addr;
        begin
            @(negedge clk);
            awaddr=addr;awvalid=1;
            #1;
            if(!awready)$fatal(1,"unexpected AW backpressure");
            @(posedge clk);#1;
            @(negedge clk);awvalid=0;
        end
    endtask
    task send_w;
        input [31:0] data;
        input [3:0] strb;
        begin
            @(negedge clk);
            wdata=data;wstrb=strb;wvalid=1;
            #1;
            if(!wready)$fatal(1,"unexpected W backpressure");
            @(posedge clk);#1;
            @(negedge clk);wvalid=0;
        end
    endtask
    task send_same;
        input [11:0] addr;
        input [31:0] data;
        input [3:0] strb;
        begin
            @(negedge clk);
            awaddr=addr;awvalid=1;
            wdata=data;wstrb=strb;wvalid=1;
            #1;
            if(!awready || !wready)
                $fatal(1,"simultaneous AW/W not ready");
            @(posedge clk);#1;
            @(negedge clk);awvalid=0;wvalid=0;
        end
    endtask
    task await_b;
        input [1:0] expected;
        integer cycles;
        begin
            for(cycles=0;cycles<16 && !bvalid;cycles=cycles+1)
                begin @(posedge clk);#1;end
            if(!bvalid || bresp!==expected)
                $fatal(1,"BRESP mismatch case=%0d got=%b expected=%b",
                       case_id,bresp,expected);
            repeat(3)begin
                @(posedge clk);#1;
                if(!bvalid || bresp!==expected)
                    $fatal(1,"BVALID/BRESP did not hold under backpressure");
            end
            @(negedge clk);bready=1;
            @(posedge clk);#1;
            @(negedge clk);bready=0;
            #1;
            if(bvalid)$fatal(1,"duplicate B response");
        end
    endtask
    task write_axil;
        input integer order;
        input [11:0] addr;
        input [31:0] data;
        input [3:0] strb;
        input [1:0] expected_resp;
        begin
            if(order==0)begin send_aw(addr);send_w(data,strb);end
            else if(order==1)begin send_w(data,strb);send_aw(addr);end
            else send_same(addr,data,strb);
            await_b(expected_resp);
        end
    endtask
    task read_axil;
        input [11:0] addr;
        input [31:0] expected_data;
        input [1:0] expected_resp;
        integer cycles;
        begin
            @(negedge clk);araddr=addr;arvalid=1;
            #1;
            if(!arready)$fatal(1,"unexpected AR backpressure");
            @(posedge clk);#1;
            @(negedge clk);arvalid=0;
            for(cycles=0;cycles<16&&!rvalid;cycles=cycles+1)
                begin @(posedge clk);#1;end
            if(!rvalid || rdata!==expected_data || rresp!==expected_resp)
                $fatal(1,"RDATA/RRESP mismatch at %h: %h/%b expected %h/%b",
                       addr,rdata,rresp,expected_data,expected_resp);
            repeat(3)begin
                @(posedge clk);#1;
                if(!rvalid || rdata!==expected_data || rresp!==expected_resp)
                    $fatal(1,"RVALID/RDATA/RRESP not held under backpressure");
            end
            @(negedge clk);rready=1;
            @(posedge clk);#1;
            @(negedge clk);rready=0;
            #1;
            if(rvalid)$fatal(1,"duplicate R response");
        end
    endtask
    task descriptor;
        begin
            write_axil(0,12'h010,32'h00001000,4'hf,2'b00);
            write_axil(1,12'h014,32'h00000000,4'hf,2'b00);
            write_axil(2,12'h018,32'd4096,4'hf,2'b00);
            write_axil(0,12'h01c,32'd77,4'hf,2'b00);
        end
    endtask
    task grant;
        begin
            descriptor();
            write_axil(1,12'h020,32'd1,4'hf,2'b00);
            repeat(3)begin @(posedge clk);#1;end
            if(!lease_granted || !admit_work || stop_new_requests ||
               lease_poisoned || active_generation!==32'd77 ||
               admitted_begin!==64'h1000 || admitted_end!==64'h1700)
                $fatal(1,"AXI-Lite lease failed to grant");
        end
    endtask
    task expect_fault;
        integer cycles;
        begin
            for(cycles=0;cycles<24 && !lease_poisoned;cycles=cycles+1)
                begin @(posedge clk);#1;end
            if(!lease_poisoned || admit_work || lease_granted ||
               admitted_begin!==0 || admitted_end!==0)
                $fatal(1,"fault not sealed case=%0d",case_id);
            repeat(3)begin
                @(posedge clk);#1;
                if(!lease_poisoned || admit_work)
                    $fatal(1,"fault not sticky case=%0d",case_id);
            end
            $display("M08_5_AXIL_CONTROL_NEGATIVE_PASS case=%0d",case_id);
        end
    endtask
    task stop_and_release;
        begin
            write_axil(2,12'h020,32'd2,4'hf,2'b00);
            #1;
            if(!stop_new_requests || admit_work || !drain_request)
                $fatal(1,"AXI STOP failed to embargo");
            // Stale high interconnect ACK cannot release allocation.
            @(negedge clk);interconnect_drain_ack=0;
            @(posedge clk);#1;
            if(!drain_request)$fatal(1,"fresh ACK-low not requested");
            @(negedge clk);interconnect_drain_ack=1;
            repeat(3)begin @(posedge clk);#1;end
            if(!lease_sealed || admit_work || lease_poisoned)
                $fatal(1,"clean one-way drain/release failed");
        end
    endtask
    initial begin
        if(!$value$plusargs("CASE=%d",case_id))case_id=0;
        repeat(3)@(negedge clk);resetn=1;
        read_axil(12'h000,32'h4d303835,2'b00);
        read_axil(12'h004,32'h00010000,2'b00);
        case(case_id)
          0:begin
              grant();
              read_axil(12'h010,32'h1000,2'b00);
              read_axil(12'h014,32'h0000,2'b00);
              read_axil(12'h018,32'd4096,2'b00);
              read_axil(12'h01c,32'd77,2'b00);
              stop_and_release();
              if(!lease_sealed)$fatal(1,"not sealed");
              $display("M08_5_AXIL_CONTROL_POSITIVE_PASS");
          end
          1:begin write_axil(2,12'h010,32'h1000,4'b0111,2'b10);expect_fault();end
          2:begin write_axil(2,12'h110,32'h1000,4'hf,2'b10);expect_fault();end
          3:begin write_axil(0,12'h011,32'h1000,4'hf,2'b10);expect_fault();end
          4:begin read_axil(12'h024,32'd0,2'b10);
                    if(lease_poisoned)$fatal(1,"bad read poisoned engine");
                    $display("M08_5_AXIL_CONTROL_NEGATIVE_PASS case=%0d",case_id);
            end
          5:begin csr_trusted=0;
                   write_axil(0,12'h010,32'h1000,4'hf,2'b10);expect_fault();end
          6:begin driver_bound_verified=0;
                   write_axil(1,12'h010,32'h1000,4'hf,2'b10);expect_fault();end
          7:begin grant();
                   @(negedge clk);control_route_verified=0;
                   #1;if(admit_work || admitted_begin!==0)
                       $fatal(1,"route loss not immediate");
                   expect_fault();end
          8:begin grant();send_aw(12'h020);
                   #1;if(admit_work || !stop_new_requests || admitted_begin!==0)
                       $fatal(1,"orphan AW did not embargo work");
                   repeat(4)begin @(posedge clk);#1;
                       if(lease_granted || admit_work || bvalid)
                           $fatal(1,"AW-only wait leaked work/response");
                   end
                   send_w(32'd2,4'hf);await_b(2'b00);
                   @(negedge clk);interconnect_drain_ack=0;
                   @(posedge clk);#1;
                   @(negedge clk);interconnect_drain_ack=1;
                   repeat(3)begin @(posedge clk);#1;end
                   if(!lease_sealed)$fatal(1,"orphan AW STOP not released");
                   $display("M08_5_AXIL_CONTROL_NEGATIVE_PASS case=%0d",case_id);
            end
          9:begin grant();send_w(32'd2,4'hf);
                   #1;if(admit_work || !stop_new_requests || admitted_begin!==0)
                       $fatal(1,"orphan W did not embargo work");
                   repeat(4)begin @(posedge clk);#1;
                       if(lease_granted || admit_work || bvalid)
                           $fatal(1,"W-only wait leaked work/response");
                   end
                   send_aw(12'h020);await_b(2'b00);
                   @(negedge clk);interconnect_drain_ack=0;
                   @(posedge clk);#1;
                   @(negedge clk);interconnect_drain_ack=1;
                   repeat(3)begin @(posedge clk);#1;end
                   if(!lease_sealed)$fatal(1,"orphan W STOP not released");
                   $display("M08_5_AXIL_CONTROL_NEGATIVE_PASS case=%0d",case_id);
            end
          10:begin grant();write_axil(2,12'h020,32'd99,4'hf,2'b10);expect_fault();end
          11:begin write_axil(2,12'h020,32'd1,4'hf,2'b10);expect_fault();end
          12:begin descriptor();
                   write_axil(2,12'h01c,32'd0,4'hf,2'b00);
                   write_axil(2,12'h020,32'd1,4'hf,2'b00);
                   expect_fault();end
          13:begin grant();write_axil(0,12'h020,32'd2,4'hf,2'b00);
                   repeat(18)begin @(posedge clk);#1;end
                   expect_fault();end
          14:begin grant();write_axil(0,12'h020,32'd2,4'hf,2'b00);
                   @(negedge clk);interconnect_drain_ack=0;
                   @(posedge clk);#1;
                   @(negedge clk);driver_bound_verified=0;
                   expect_fault();end
          15:begin csr_trusted=0;
                   read_axil(12'h010,32'd0,2'b10);
                   if(lease_poisoned)$fatal(1,"rejected read caused fault");
                   $display("M08_5_AXIL_CONTROL_NEGATIVE_PASS case=%0d",case_id);
            end
          16:begin write_axil(0,12'h000,32'h9,4'hf,2'b10);expect_fault();end
          17:begin grant();
                   // Same-cycle AW+W accepted; cannot start new work even
                   // before delayed registered CSR command commits.
                   @(negedge clk);awaddr=12'h020;awvalid=1;
                   wdata=32'd2;wstrb=4'hf;wvalid=1;
                   #1;if(admit_work || !stop_new_requests)
                       $fatal(1,"same-cycle in-flight STOP work admitted");
                   @(posedge clk);#1;
                   @(negedge clk);awvalid=0;wvalid=0;
                   await_b(2'b00);
                   @(negedge clk);interconnect_drain_ack=0;
                   @(posedge clk);#1;
                   @(negedge clk);interconnect_drain_ack=1;
                   repeat(3)begin @(posedge clk);#1;end
                   if(!lease_sealed)$fatal(1,"same-cycle STOP not sealed");
                   $display("M08_5_AXIL_CONTROL_NEGATIVE_PASS case=%0d",case_id);
            end
          18:begin grant();bank_clean_idle=0;
                   write_axil(2,12'h020,32'd2,4'hf,2'b00);
                   @(negedge clk);interconnect_drain_ack=0;
                   @(posedge clk);#1;
                   @(negedge clk);interconnect_drain_ack=1;
                   repeat(18)begin @(posedge clk);#1;end
                   expect_fault();end
          19:begin grant();send_aw(12'h020);
                   @(negedge clk);araddr=12'h008;arvalid=1;
                   #1;if(arready)$fatal(1,"read bypassed orphan write");
                   @(negedge clk);arvalid=0;
                   send_w(32'd2,4'hf);await_b(2'b00);
                   @(negedge clk);interconnect_drain_ack=0;
                   @(posedge clk);#1;
                   @(negedge clk);interconnect_drain_ack=1;
                   repeat(3)begin @(posedge clk);#1;end
                   if(!lease_sealed)$fatal(1,"serialized stop not sealed");
                   $display("M08_5_AXIL_CONTROL_NEGATIVE_PASS case=%0d",case_id);
            end
          default:$fatal(1,"unsupported case %0d",case_id);
        endcase
        $finish;
    end
    initial begin
        #100000;
        $fatal(1,"AXI-Lite TB timeout case=%0d",case_id);
    end
endmodule
