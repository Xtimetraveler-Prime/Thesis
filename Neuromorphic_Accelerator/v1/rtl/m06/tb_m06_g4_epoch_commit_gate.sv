// G4 source-only original-candidate RTL safety gate, NO vendor HLS/DDR.
// Intentionally tests release-before-B, nonzero HLS status, read/write guard
// faults, out-of-order AXI read, and repeated start while quarantined.
module tb_m06_g4_epoch_commit_gate;
reg clk=0;
always #5 clk=~clk;
reg resetn=0;
reg epoch_begin=0, ap_done=0;
reg [31:0] ap_return=0;
reg read_fault=0,write_fault=0,aw=0,b=0,ar=0;
wire active,commit,poison;
wire [15:0] outstanding;
m06_g4_epoch_commit_gate #(.MAX_EPOCH_CYCLES(12)) dut(
  .aclk(clk),.aresetn(resetn),.epoch_begin(epoch_begin),
  .ap_done(ap_done),.ap_return(ap_return),
  .read_guard_fault(read_fault),.write_guard_fault(write_fault),
  .write_aw_fire(aw),.write_b_fire(b),.read_ar_fire(ar),
  .epoch_active(active),.commit_valid(commit),.poisoned(poison),
  .outstanding_writes(outstanding)
);
task automatic step;
begin
    @(posedge clk);
    #1;
    @(negedge clk);
end
endtask
task automatic reset_test;
begin
    resetn=0; epoch_begin=0; ap_done=0; ap_return=0;
    read_fault=0;write_fault=0;aw=0;b=0;ar=0;
    step(); step();
    resetn=1; step();
    if(active !== 0 || commit !== 0 || poison !== 0 || outstanding !== 0)
        $fatal(1,"M06_G4_GATE_FAIL RESET");
end
endtask
task automatic start_test;
begin
    epoch_begin=1; step(); epoch_begin=0;
end
endtask
task automatic done_test(input [31:0] status);
begin
    ap_return=status; ap_done=1; step(); ap_done=0; ap_return=0;
end
endtask
initial begin
    reset_test();
    // A valid HLS success MUST NOT publish while write responses are pending.
    start_test();
    if(active!==1 || commit!==0 || poison!==0)
        $fatal(1,"M06_G4_GATE_FAIL START");
    aw=1; step(); aw=0;
    if(outstanding!==1 || commit!==0)
        $fatal(1,"M06_G4_GATE_FAIL AW_COUNTER");
    b=1; step(); b=0;
    if(outstanding!==0 || poison!==0)
        $fatal(1,"M06_G4_GATE_FAIL ACK");
    ar=1; step(); ar=0;
    done_test(32'd0);
    if(commit!==0)
        $fatal(1,"M06_G4_GATE_FAIL EARLY_COMMIT_ON_AP_DONE");
    step(); // post-HLS completion guard fault settling cycle
    if(active!==0 || commit!==1 || poison!==0)
        $fatal(1,"M06_G4_GATE_FAIL CLEAN_COMMIT");

    // A new legal epoch clears previous clean commit visibility.
    start_test();
    if(commit!==0 || active!==1)
        $fatal(1,"M06_G4_GATE_FAIL STALE_COMMIT");
    done_test(32'd1);
    if(commit!==0 || poison!==1 || active!==0)
        $fatal(1,"M06_G4_GATE_FAIL BAD_RETURN");
    start_test(); // cannot start a poisoned canonical image
    if(commit!==0 || poison!==1 || active!==0)
        $fatal(1,"M06_G4_GATE_FAIL POISON_REUSE");

    reset_test();
    start_test();
    read_fault=1; step(); read_fault=0;
    done_test(32'd0);
    if(commit!==0 || poison!==1)
        $fatal(1,"M06_G4_GATE_FAIL READ_FAULT_QUARANTINE");

    reset_test();
    start_test();
    done_test(32'd0);
    // Registered guard fault arrives at the edge immediately after ap_done.
    // The commit token must NEVER pulse high for even one cycle.
    if(commit!==0)
        $fatal(1,"M06_G4_GATE_FAIL EARLY_FAULT_COMMIT");
    write_fault=1; step(); write_fault=0;
    if(commit!==0 || poison!==1)
        $fatal(1,"M06_G4_GATE_FAIL LATE_REGISTERED_GUARD_FAULT");

    reset_test();
    start_test();
    aw=1; step(); aw=0;
    done_test(32'd0); // HLS done but unacknowledged canonical write
    if(commit!==0 || poison!==1)
        $fatal(1,"M06_G4_GATE_FAIL UNACKED_WRITE");

    reset_test();
    start_test();
    aw=1; step(); aw=0;
    ar=1; step(); ar=0;
    if(commit!==0 || poison!==1)
        $fatal(1,"M06_G4_GATE_FAIL READ_BEFORE_B");

    reset_test();
    start_test();
    write_fault=1; ap_done=1; step();
    ap_done=0; write_fault=0;
    if(commit!==0 || poison!==1)
        $fatal(1,"M06_G4_GATE_FAIL SAME_CYCLE_WRITE_FAULT_DONE");

    reset_test();
    start_test();
    b=1; step(); b=0;
    if(commit!==0 || poison!==1)
        $fatal(1,"M06_G4_GATE_FAIL B_UNDERFLOW");

    reset_test();
    ap_done=1; step(); ap_done=0;
    if(commit!==0 || poison!==1)
        $fatal(1,"M06_G4_GATE_FAIL SPURIOUS_DONE");

    reset_test();
    start_test();
    // A lost AXI response can stall the genuine HLS ap_done forever.
    // Timeout must poison without relying on any HLS return or guard fault.
    repeat(16) step();
    if(commit!==0 || poison!==1 || active!==1)
        $fatal(1,"M06_G4_GATE_FAIL LOST_ACK_WATCHDOG");

    $display("M06_G4_EPOCH_COMMIT_FAULT_QUARANTINE_RTL_PASS NO_DDR_NO_BOARD NO_VENDOR_XSIM");
    $finish;
end
initial begin
    #100000;
    $fatal(1,"M06_G4_GATE_FAIL WATCHDOG");
end
endmodule
