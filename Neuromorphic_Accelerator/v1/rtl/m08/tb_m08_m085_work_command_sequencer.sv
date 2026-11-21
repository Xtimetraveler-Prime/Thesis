// Genuine Icarus M08.5 work register and one-pulse sequencer fault matrix.
// This TB uses synthetic neural status / owner, not a real memory interface.
// The *separate* managed-neural TB drives 75 commands into actual LIF+AXI.
module tb_m08_m085_work_command_sequencer;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0;
    reg write_valid=0;
    reg [7:0] write_addr=0,read_addr=8'h30;
    reg [31:0] write_data=0;
    reg [3:0] write_strb=4'hf;
    reg trusted_owner=1,raw_lease_admit=1,source_admit=1;
    reg stop_new_requests=0;
    reg neural_done=0,neural_completed_save=0,neural_busy=0;
    reg neural_poisoned=0,neural_bank_valid=0,neural_bank_dirty=0;
    reg [2:0] neural_bank_phase=0;
    reg [31:0] neural_bank_logical=0;
    wire write_error,read_error,fault,work_busy,page_req,page_save;
    wire [31:0] read_data,completed_commands,page_slot,page_tick;
    wire dispatch_req;
    wire [31:0] dispatch_logical;
    integer case_id=0;
    m08_m085_work_command_sequencer #(
        .WORK_TIMEOUT_CYCLES(8)
    ) dut (
        .clk(clk),.resetn(resetn),
        .write_valid(write_valid),.write_addr(write_addr),
        .write_data(write_data),.write_strb(write_strb),
        .trusted_owner(trusted_owner),
        .raw_lease_admit(raw_lease_admit),.source_admit(source_admit),
        .stop_new_requests(stop_new_requests),
        .neural_done(neural_done),
        .neural_completed_save(neural_completed_save),
        .neural_busy(neural_busy),.neural_poisoned(neural_poisoned),
        .neural_bank_valid(neural_bank_valid),
        .neural_bank_dirty(neural_bank_dirty),
        .neural_bank_phase(neural_bank_phase),
        .neural_bank_logical(neural_bank_logical),
        .write_error(write_error),.read_addr(read_addr),
        .read_data(read_data),.read_error(read_error),
        .fault(fault),.work_busy(work_busy),
        .completed_commands(completed_commands),
        .page_req(page_req),.page_save(page_save),
        .page_slot(page_slot),.page_tick(page_tick),
        .dispatch_req(dispatch_req),
        .dispatch_logical(dispatch_logical)
    );
    task write_mmio;
        input [7:0] addr;
        input [31:0] data;
        input [3:0] strb;
        input expected_error;
        begin
            @(negedge clk);
            write_addr=addr;write_data=data;write_strb=strb;
            write_valid=1;
            #1;
            if(write_error!==expected_error)
                $fatal(1,"write error differs case=%0d addr=%h got=%b",
                       case_id,addr,write_error);
            @(posedge clk);#1;
            @(negedge clk);write_valid=0;
        end
    endtask
    task stage_neural0;
        begin
            write_mmio(8'h24,0,4'hf,0);
            write_mmio(8'h28,0,4'hf,0);
        end
    endtask
    task expect_fault;
        integer n;
        begin
            for(n=0;n<6 && !fault;n=n+1)begin @(posedge clk);#1;end
            if(!fault || page_req || dispatch_req || completed_commands!=0)
                $fatal(1,"fault did not seal work case=%0d",case_id);
            repeat(4)begin @(posedge clk);#1;
                if(!fault || page_req || dispatch_req)
                    $fatal(1,"fault not sticky case=%0d",case_id);
            end
            $display("M08_5_MMIO_WORK_ADVERSE_PASS case=%0d",case_id);
        end
    endtask
    task start_load;
        begin
            write_mmio(8'h2c,1,4'hf,0);
            #1;if(!page_req || page_save || !work_busy)
                $fatal(1,"LOAD request not one pulse");
            @(posedge clk);#1;
            if(page_req)$fatal(1,"LOAD request duplicate");
        end
    endtask
    task finish_load;
        begin
            @(negedge clk);
            neural_bank_valid=1;neural_bank_dirty=0;
            neural_bank_phase=3'd2;neural_bank_logical=0;
            neural_done=1;neural_completed_save=0;
            @(posedge clk);#1;
            if(work_busy || !read_data[1] || completed_commands!=1)
                $fatal(1,"LOAD MMIO completion not visible");
            @(negedge clk);neural_done=0;
        end
    endtask
    initial begin
        if(!$value$plusargs("CASE=%d",case_id))case_id=0;
        repeat(3)@(negedge clk);resetn=1;
        case(case_id)
        0:begin
            stage_neural0();
            start_load();
            finish_load();
            read_addr=8'h34;#1;
            if(read_error || read_data!=1)$fatal(1,"counter read incorrect");
            read_addr=8'h30;
            write_mmio(8'h2c,2,4'hf,0);
            #1;if(!dispatch_req || dispatch_logical!=0)
                $fatal(1,"DISPATCH request not asserted");
            @(posedge clk);#1;
            if(dispatch_req)$fatal(1,"DISPATCH duplicated");
            @(negedge clk);neural_bank_dirty=1;neural_bank_phase=3'd4;
            @(posedge clk);#1;
            if(work_busy || completed_commands!=2)
                $fatal(1,"DISPATCH not complete");
            write_mmio(8'h2c,3,4'hf,0);
            #1;if(!page_req || !page_save)$fatal(1,"SAVE not asserted");
            @(posedge clk);#1;
            if(page_req)$fatal(1,"SAVE duplicate");
            @(negedge clk);
            neural_bank_dirty=0;neural_bank_phase=3'd2;
            neural_done=1;neural_completed_save=1;
            @(posedge clk);#1;
            if(work_busy || completed_commands!=3 || fault)
                $fatal(1,"SAVE completion not clean");
            $display("M08_5_MMIO_WORK_LOAD_DISPATCH_SAVE_POSITIVE_PASS");
        end
        1:begin stage_neural0();raw_lease_admit=0;
                write_mmio(8'h2c,1,4'hf,1);expect_fault();end
        2:begin write_mmio(8'h24,7,4'hf,0);
                write_mmio(8'h2c,1,4'hf,1);expect_fault();end
        3:begin write_mmio(8'h28,4,4'hf,0);
                write_mmio(8'h2c,1,4'hf,1);expect_fault();end
        4:begin write_mmio(8'h24,6,4'hf,0);
                write_mmio(8'h28,1,4'hf,0);
                write_mmio(8'h2c,1,4'hf,1);expect_fault();end
        5:begin stage_neural0();
                write_mmio(8'h2c,99,4'hf,1);expect_fault();end
        6:begin write_mmio(8'h30,0,4'hf,1);expect_fault();end
        7:begin write_mmio(8'h24,0,4'b0111,1);expect_fault();end
        8:begin trusted_owner=0;
                write_mmio(8'h24,0,4'hf,1);expect_fault();end
        9:begin stage_neural0();
                write_mmio(8'h2c,2,4'hf,1);expect_fault();end
       10:begin stage_neural0();
                write_mmio(8'h2c,3,4'hf,1);expect_fault();end
       11:begin stage_neural0();start_load();
                write_mmio(8'h24,2,4'hf,1);expect_fault();end
       12:begin stage_neural0();start_load();
                @(negedge clk);raw_lease_admit=0;expect_fault();end
       13:begin stage_neural0();start_load();
                @(negedge clk);stop_new_requests=1;expect_fault();end
       14:begin stage_neural0();start_load();
                @(negedge clk);neural_poisoned=1;expect_fault();end
       15:begin stage_neural0();start_load();
                repeat(12)begin @(posedge clk);#1;end
                expect_fault();end
       16:begin stage_neural0();start_load();
                @(negedge clk);
                neural_done=1;neural_bank_valid=1;
                neural_bank_phase=3'd2;neural_bank_logical=5;
                expect_fault();end
       17:begin stage_neural0();
                neural_bank_valid=1;neural_bank_phase=3'd2;
                write_mmio(8'h2c,2,4'hf,0);
                repeat(12)begin @(posedge clk);#1;end
                expect_fault();end
       18:begin stage_neural0();start_load();
                @(negedge clk);
                neural_done=1;neural_completed_save=1;
                neural_bank_valid=1;neural_bank_phase=3'd2;
                expect_fault();end
       19:begin read_addr=8'hfc;#1;
                if(!read_error || read_data!=0)
                    $fatal(1,"bad work address not rejected");
                $display("M08_5_MMIO_WORK_ADVERSE_PASS case=19");end
        default:$fatal(1,"unknown MMIO work test");
        endcase
        $finish;
    end
    initial begin #100000;$fatal(1,"work sequencer test timed out case=%0d",case_id);end
endmodule
