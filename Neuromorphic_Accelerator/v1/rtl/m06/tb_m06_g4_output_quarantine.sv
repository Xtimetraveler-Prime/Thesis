// M06 existing G4 standalone synthesizable-candidate output quarantine bench.
// Functional Icarus against real local RTL only. No generated HLS/vendor/DDR.
module tb_m06_g4_output_quarantine;
reg clk=0;
always #5 clk=~clk;
reg resetn=0,start=0,commit=0,poison=0;
reg [31:0] expected=2;
reg [191:0] in_trace=0;
reg in_tv=0;
wire in_tr;
reg [255:0] in_metrics=0;
reg in_mv=0;
wire in_mr;
wire [191:0] out_trace;
wire out_tv;
reg out_tr=1;
wire [255:0] out_metrics;
wire out_mv;
reg out_mr=1;
wire quarantined,done,fault;
wire [31:0] buffered,published;
integer trace_out=0, metrics_out=0;
m06_g4_output_quarantine #(.MAX_TRACE(4)) dut(
    .aclk(clk),.aresetn(resetn),
    .epoch_begin(start),.expected_trace_count(expected),
    .commit_valid(commit),.poisoned(poison),
    .s_trace_tdata(in_trace),.s_trace_tvalid(in_tv),.s_trace_tready(in_tr),
    .s_metrics_tdata(in_metrics),.s_metrics_tvalid(in_mv),.s_metrics_tready(in_mr),
    .m_trace_tdata(out_trace),.m_trace_tvalid(out_tv),.m_trace_tready(out_tr),
    .m_metrics_tdata(out_metrics),.m_metrics_tvalid(out_mv),.m_metrics_tready(out_mr),
    .quarantined(quarantined),.published_done(done),
    .buffered_trace_count(buffered),.published_trace_count(published),
    .protocol_fault(fault)
);
always @(posedge clk) if(resetn) begin
    if(out_tv && out_tr) begin
        if(trace_out==0 && out_trace!==192'h1234)
            $fatal(1,"M06_G4_QUARANTINE_FAIL FIRST_OUTPUT");
        if(trace_out==1 && out_trace!==192'h2345)
            $fatal(1,"M06_G4_QUARANTINE_FAIL SECOND_OUTPUT");
        trace_out=trace_out+1;
    end
    if(out_mv && out_mr) begin
        if(out_metrics!==256'h12345678)
            $fatal(1,"M06_G4_QUARANTINE_FAIL METRICS_CONTENT");
        metrics_out=metrics_out+1;
    end
end
task automatic step;
begin
    @(posedge clk); #1; @(negedge clk);
end
endtask
task automatic reset_test;
begin
    resetn=0;start=0;commit=0;poison=0;in_tv=0;in_mv=0;
    expected=2;in_trace=0;in_metrics=0;
    trace_out=0;metrics_out=0;
    step();step();resetn=1;step();
    if(quarantined!==0 || done!==0 || fault!==0)
        $fatal(1,"M06_G4_QUARANTINE_FAIL RESET");
end
endtask
task automatic begin_epoch;
begin
    start=1;step();start=0;
end
endtask
task automatic send_trace(input [191:0] value);
begin
    if(in_tr!==1) $fatal(1,"M06_G4_QUARANTINE_FAIL INPUT_NOT_READY");
    in_trace=value;in_tv=1;step();in_tv=0;
end
endtask
task automatic send_metrics(input [255:0] value);
begin
    if(in_mr!==1) $fatal(1,"M06_G4_QUARANTINE_FAIL METRICS_NOT_READY");
    in_metrics=value;in_mv=1;step();in_mv=0;
end
endtask
initial begin
    reset_test();begin_epoch();
    send_trace(192'h1234);
    send_trace(192'h2345);
    send_metrics(256'h12345678);
    repeat(3) step();
    if(out_tv!==0 || out_mv!==0 || trace_out!==0 ||
       metrics_out!==0 || buffered!==2 || published!==0)
        $fatal(1,"M06_G4_QUARANTINE_FAIL PROVISIONAL_OUTPUT_LEAK");
    commit=1;step();commit=0;
    repeat(4) step();
    if(done!==1 || quarantined!==0 || fault!==0 ||
       trace_out!==2 || metrics_out!==1 || published!==2)
        $fatal(1,"M06_G4_QUARANTINE_FAIL CLEAN_RELEASE");

    reset_test();begin_epoch();
    send_trace(192'h1234);
    send_metrics(256'h12345678);
    poison=1;step();poison=0;
    commit=1;step();commit=0;
    repeat(3) step();
    if(done!==0 || quarantined!==1 || trace_out!==0 ||
       metrics_out!==0 || published!==0)
        $fatal(1,"M06_G4_QUARANTINE_FAIL POISON_DISCLOSED_DATA");
    start=1;step();start=0;
    if(quarantined!==1 || out_tv!==0 || out_mv!==0)
        $fatal(1,"M06_G4_QUARANTINE_FAIL POISON_REUSE");

    reset_test();begin_epoch();
    send_trace(192'h1234);
    send_metrics(256'h12345678);
    commit=1;step();commit=0;
    if(quarantined!==1 || fault!==1 || out_tv!==0 || out_mv!==0)
        $fatal(1,"M06_G4_QUARANTINE_FAIL TRACE_COUNT_MISMATCH");

    reset_test();begin_epoch();
    send_trace(192'h1234);
    send_trace(192'h2345);
    commit=1;step();commit=0;
    if(quarantined!==1 || fault!==1 || out_tv!==0 || out_mv!==0)
        $fatal(1,"M06_G4_QUARANTINE_FAIL MISSING_METRICS");

    reset_test();
    expected=5;begin_epoch();
    if(quarantined!==1 || fault!==1 || out_tv!==0 || out_mv!==0)
        $fatal(1,"M06_G4_QUARANTINE_FAIL CAPACITY_GUARD");

    $display("M06_G4_TRACE_METRICS_QUARANTINE_RTL_PASS NO_VENDOR_XSIM_NO_DDR_NO_BOARD");
    $finish;
end
initial begin
    #100000;
    $fatal(1,"M06_G4_QUARANTINE_FAIL WATCHDOG");
end
endmodule
