// M08.5 genuine Icarus RTL test for a SYNTHETIC kernel-only CSR producer.
// No AXI-Lite, PS/PL, Linux kernel driver, IOMMU or physical drain controller.
// The real m08_m085_kernel_dma_lease_fence is instantiated by the DUT.
module tb_m08_m085_trusted_control_abi;
    reg clk=0; always #5 clk=~clk;
    reg resetn=0;
    reg csr_valid=0,csr_write=0,csr_trusted=1;
    reg [7:0] csr_addr=0;
    reg [31:0] csr_wdata=0;
    reg [3:0] csr_wstrb=4'hf;
    reg driver_bound_verified=1,control_route_verified=1;
    reg interconnect_drain_ack=1,transport_idle=1,bank_clean_idle=1;
    wire csr_ready,csr_error,admit_work,stop_new_requests,drain_request;
    wire lease_granted,lease_sealed,lease_poisoned;
    wire [31:0] active_generation,csr_rdata;
    wire [63:0] admitted_begin,admitted_end;
    integer case_id=0;
    m08_m085_trusted_control_abi #(.DRAIN_TIMEOUT_CYCLES(8)) dut (
        .clk(clk),.resetn(resetn),.csr_valid(csr_valid),
        .csr_write(csr_write),.csr_addr(csr_addr),.csr_wdata(csr_wdata),
        .csr_wstrb(csr_wstrb),.csr_trusted(csr_trusted),
        .csr_ready(csr_ready),.csr_error(csr_error),.csr_rdata(csr_rdata),
        .driver_bound_verified(driver_bound_verified),
        .control_route_verified(control_route_verified),
        .interconnect_drain_ack(interconnect_drain_ack),
        .transport_idle(transport_idle),.bank_clean_idle(bank_clean_idle),
        .admit_work(admit_work),.stop_new_requests(stop_new_requests),
        .drain_request(drain_request),.lease_granted(lease_granted),
        .lease_sealed(lease_sealed),.lease_poisoned(lease_poisoned),
        .active_generation(active_generation),.admitted_begin(admitted_begin),
        .admitted_end(admitted_end)
    );
    task write_csr;
        input [7:0] addr;
        input [31:0] data;
        input [3:0] strb;
        input trusted;
        begin
            @(negedge clk);
            csr_valid=1;csr_write=1;csr_addr=addr;csr_wdata=data;
            csr_wstrb=strb;csr_trusted=trusted;
            #1;
            if(!csr_ready)$fatal(1,"CSR write never acknowledged");
            @(posedge clk);#1;
            @(negedge clk);csr_valid=0;csr_write=0;
            csr_trusted=1;csr_wstrb=4'hf;
        end
    endtask
    task descriptor;
        begin
            write_csr(8'h10,32'h00001000,4'hf,1);
            write_csr(8'h14,32'h00000000,4'hf,1);
            write_csr(8'h18,32'd4096,4'hf,1);
            write_csr(8'h1c,32'd77,4'hf,1);
        end
    endtask
    task grant;
        begin
            descriptor();
            write_csr(8'h20,32'd1,4'hf,1);
            repeat(2)begin @(posedge clk);#1;end
            if(!lease_granted || !admit_work || lease_poisoned ||
               active_generation!==32'd77 ||
               admitted_begin!==64'h1000 || admitted_end!==64'h1700)
                $fatal(1,"valid trusted grant refused or window incorrect");
        end
    endtask
    task stop_and_release;
        begin
            write_csr(8'h20,32'd2,4'hf,1);
            #1;
            if(!stop_new_requests || admit_work || !drain_request ||
               admitted_begin!=0 || admitted_end!=0)
                $fatal(1,"STOP failed to embargo new work while draining");
            // A stale high ACK must NOT count as a fresh drain after STOP.
            @(negedge clk);interconnect_drain_ack=0;
            @(posedge clk);#1;
            if(!drain_request || admit_work)
                $fatal(1,"ACK deassertion was not observed in drain handshake");
            @(negedge clk);interconnect_drain_ack=1;
            repeat(3)begin @(posedge clk);#1;end
            if(!lease_sealed || admit_work || lease_poisoned ||
               admitted_begin!=0 || admitted_end!=0)
                $fatal(1,"fresh ACK did not permit one-way clean release");
        end
    endtask
    task expect_fault;
        integer k;
        begin
            for(k=0;k<20 && !lease_poisoned;k=k+1)begin
                @(posedge clk);#1;
            end
            if(!lease_poisoned || admit_work || lease_granted ||
               admitted_begin!==0 || admitted_end!==0)
                $fatal(1,"fault not closed case=%0d",case_id);
            repeat(3)begin
                @(posedge clk);#1;
                if(!lease_poisoned || admit_work)
                    $fatal(1,"fault was not sticky case=%0d",case_id);
            end
            $display("M08_5_TRUSTED_CONTROL_NEGATIVE_PASS case=%0d",case_id);
        end
    endtask
    initial begin
        if(!$value$plusargs("CASE=%d",case_id))case_id=0;
        repeat(3)@(negedge clk);resetn=1;
        #1;csr_addr=8'h00;
        if(csr_rdata!==32'h4d303835)
            $fatal(1,"wrong CAP magic");
        csr_addr=8'h04;#1;
        if(csr_rdata!==32'h00010000)
            $fatal(1,"wrong version");
        case(case_id)
          0:begin
              grant();
              stop_and_release();
              $display("M08_5_TRUSTED_CONTROL_ABI_FRESH_DRAIN_PASS");
          end
          1:begin write_csr(8'h10,32'h1000,4'hf,0);expect_fault();end
          2:begin write_csr(8'h10,32'h1000,4'b0111,1);expect_fault();end
          3:begin write_csr(8'h00,32'd7,4'hf,1);expect_fault();end
          4:begin write_csr(8'h20,32'd1,4'hf,1);expect_fault();end
          5:begin
              descriptor();write_csr(8'h1c,32'd0,4'hf,1);
              write_csr(8'h20,32'd1,4'hf,1);expect_fault();
          end
          6:begin
              descriptor();write_csr(8'h10,32'h1080,4'hf,1);
              write_csr(8'h20,32'd1,4'hf,1);expect_fault();
          end
          7:begin
              descriptor();driver_bound_verified=0;
              write_csr(8'h20,32'd1,4'hf,1);expect_fault();
          end
          8:begin
              grant();@(negedge clk);driver_bound_verified=0;
              #1;if(admit_work)$fatal(1,"owner loss did not instantly embargo");
              expect_fault();
          end
          9:begin
              grant();@(negedge clk);control_route_verified=0;
              #1;if(admit_work)$fatal(1,"control route loss failed embargo");
              expect_fault();
          end
          10:begin grant();write_csr(8'h20,32'd1,4'hf,1);expect_fault();end
          11:begin grant();write_csr(8'h10,32'h2000,4'hf,1);expect_fault();end
          12:begin
              grant();write_csr(8'h20,32'd2,4'hf,1);
              bank_clean_idle=0;
              @(negedge clk);interconnect_drain_ack=0;
              @(negedge clk);interconnect_drain_ack=1;
              expect_fault();
          end
          13:begin
              grant();write_csr(8'h20,32'd2,4'hf,1);
              // ACK stays high from BEFORE STOP: never a fresh ACK.
              expect_fault();
          end
          14:begin
              grant();write_csr(8'h20,32'd2,4'hf,1);
              transport_idle=0;
              @(negedge clk);interconnect_drain_ack=0;
              @(negedge clk);interconnect_drain_ack=1;
              expect_fault();
          end
          15:begin
              grant();stop_and_release();
              write_csr(8'h20,32'd1,4'hf,1);expect_fault();
          end
          16:begin write_csr(8'h20,32'hDEADBEEF,4'hf,1);expect_fault();end
          17:begin
              grant();write_csr(8'h20,32'd2,4'hf,1);
              write_csr(8'h18,32'd8192,4'hf,1);expect_fault();
          end
          18:begin
              grant();
              @(negedge clk);csr_valid=1;csr_write=1;csr_trusted=0;
              csr_addr=8'h20;csr_wdata=32'd2;csr_wstrb=4'hf;
              #1;
              if(admit_work || !stop_new_requests || !csr_error)
                  $fatal(1,"forged control could issue work in same cycle");
              expect_fault();
          end
          19:begin
              descriptor();write_csr(8'h18,32'd1536,4'hf,1);
              write_csr(8'h20,32'd1,4'hf,1);expect_fault();
          end
          default:$fatal(1,"unknown ABI test case");
        endcase
        $finish;
    end
    initial begin #1000000;$fatal(1,"ABI simulation watchdog expired");end
endmodule
