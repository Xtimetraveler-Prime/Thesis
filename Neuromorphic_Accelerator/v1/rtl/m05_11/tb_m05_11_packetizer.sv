// M05.11a pure RTL packetizer verification: no HLS generated Verilog, no PS/DMA.
// Test three normal terminal modes plus fail-closed output overproduction.
module tb_m05_11_packetizer;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg start_valid = 0;
    wire start_ready;
    reg [63:0] start_session_id = 0;
    reg [31:0] start_expected_rows = 0;
    reg finish_valid = 0;
    wire finish_ready;
    reg [31:0] finish_status = 0;
    reg [191:0] trace_tdata = 0;
    reg trace_tvalid = 0;
    wire trace_tready;
    wire [255:0] dma_tdata;
    wire [31:0] dma_tkeep;
    wire dma_tvalid;
    reg dma_tready = 0;
    wire dma_tlast, done, fault;
    wire [31:0] captured_rows;

    integer cycles = 0;
    integer output_stalls = 0;
    integer trace_beats = 0;
    integer footers = 0;
    integer goal_trace_rows = 0;
    reg [31:0] goal_status = 0;
    reg [63:0] goal_session = 0;
    reg stalled_last = 0;
    reg [255:0] prev_data = 0;
    reg prev_tlast = 0;
    reg [31:0] prev_keep = 0;

    m05_trace_dma_packetizer dut(
        .clk(clk), .rst_n(rst_n),
        .start_valid(start_valid), .start_ready(start_ready),
        .start_session_id(start_session_id),
        .start_expected_rows(start_expected_rows),
        .finish_valid(finish_valid), .finish_ready(finish_ready),
        .finish_status(finish_status), .trace_tdata(trace_tdata),
        .trace_tvalid(trace_tvalid), .trace_tready(trace_tready),
        .dma_tdata(dma_tdata), .dma_tkeep(dma_tkeep),
        .dma_tvalid(dma_tvalid), .dma_tready(dma_tready),
        .dma_tlast(dma_tlast), .done(done), .fault(fault),
        .captured_rows(captured_rows)
    );

    always @(posedge clk) begin
        cycles <= cycles + 1;
        if (cycles > 10000) $fatal(1, "RTL_BRIDGE_FAIL global timeout");
        if (!rst_n) begin
            stalled_last <= 0;
        end else begin
            if (stalled_last &&
                (!dma_tvalid || dma_tdata !== prev_data ||
                 dma_tlast !== prev_tlast || dma_tkeep !== prev_keep))
                $fatal(1, "RTL_BRIDGE_FAIL DMA VALID/data/LAST/KEEP changed under stall");
            stalled_last <= dma_tvalid && !dma_tready;
            prev_data <= dma_tdata;
            prev_tlast <= dma_tlast;
            prev_keep <= dma_tkeep;
            if (dma_tvalid && !dma_tready) output_stalls <= output_stalls + 1;
            if (dma_tvalid && dma_tready) begin
                if (dma_tkeep !== 32'hffffffff)
                    $fatal(1, "RTL_BRIDGE_FAIL DMA TKEEP invalid");
                if (!dma_tlast) begin
                    if (trace_beats >= goal_trace_rows)
                        $fatal(1, "RTL_BRIDGE_FAIL too many trace beats");
                    if (dma_tdata[255:192] !== 0 ||
                        dma_tdata[191:0] !== {160'd0, trace_beats[31:0]})
                        $fatal(1, "RTL_BRIDGE_FAIL trace payload value/order");
                    trace_beats <= trace_beats + 1;
                end else begin
                    if (dma_tdata[255:192] !== 64'h4d30353131454e44 ||
                        dma_tdata[191:128] !== goal_session ||
                        dma_tdata[127:96] !== goal_status ||
                        dma_tdata[95:64] !== trace_beats ||
                        dma_tdata[63:0] !== 0)
                        $fatal(1, "RTL_BRIDGE_FAIL footer status/count/session");
                    footers <= footers + 1;
                end
            end
        end
    end

    // ready 1 cycle out of 4, no dependence on neural data.
    always @(negedge clk) dma_tready = cycles % 4 == 1;

    task automatic start_case(input [63:0] sid, input [31:0] expected,
                              input integer n, input [31:0] status);
    begin
        @(negedge clk);
        if (!start_ready) $fatal(1, "RTL_BRIDGE_FAIL not idle for start");
        goal_session = sid;
        goal_trace_rows = n;
        goal_status = status;
        trace_beats = 0;
        footers = 0;
        start_session_id = sid;
        start_expected_rows = expected;
        start_valid = 1;
        @(negedge clk);
        start_valid = 0;
    end
    endtask

    task automatic send_beat(input [31:0] value);
        integer i;
        reg accepted;
    begin
        @(negedge clk);
        trace_tdata = {160'd0, value};
        trace_tvalid = 1;
        accepted = 0;
        for (i=0; i<100; i=i+1) begin
            @(posedge clk);
            if (trace_tready) begin
                accepted = 1;
                i = 100;
            end
        end
        if (!accepted) $fatal(1, "RTL_BRIDGE_FAIL input never ready");
        @(negedge clk);
        trace_tvalid = 0;
    end
    endtask

    task automatic finish_case(input [31:0] status);
        integer i;
        reg accepted;
    begin
        @(negedge clk);
        finish_status = status;
        finish_valid = 1;
        accepted = 0;
        for (i=0; i<100; i=i+1) begin
            @(posedge clk);
            if (finish_ready) begin
                accepted = 1;
                i = 100;
            end
        end
        if (!accepted) $fatal(1, "RTL_BRIDGE_FAIL finalize not ready");
        @(negedge clk);
        finish_valid = 0;
        wait(done);
        repeat (3) @(negedge clk);
        if (footers != 1 || fault || captured_rows != goal_trace_rows)
            $fatal(1, "RTL_BRIDGE_FAIL session footer/count/fault");
    end
    endtask

    initial begin
        repeat (5) @(negedge clk);
        rst_n = 1;
        start_case(64'h101, 3, 3, 0);
        send_beat(0);
        send_beat(1);
        send_beat(2);
        finish_case(0);
        start_case(64'h102, 2, 0, 4);
        finish_case(4); // zero-trace error: still one TLAST footer
        start_case(64'h103, 3, 1, 32'hffff0001);
        send_beat(0);
        finish_case(0); // short success must be explicitly marked invalid
        // Overproduction must never exceed the allocated DMA capacity.
        start_case(64'h104, 1, 1, 0);
        send_beat(0);
        @(negedge clk);
        trace_tdata = {160'd0, 32'd99};
        trace_tvalid = 1;
        repeat (4) @(negedge clk);
        if (!fault || trace_tready || dma_tvalid || start_ready)
            $fatal(1, "RTL_BRIDGE_FAIL output overrun did not fault closed");
        if (output_stalls < 4)
            $fatal(1, "RTL_BRIDGE_FAIL no meaningful output TREADY stalls");
        $display("PASS: M05.11 RTL packetizer 3 TLAST footers (success, zero-error, truncated-success); output_stalls=%0d; overflow quarantined", output_stalls);
        $finish;
    end
endmodule
