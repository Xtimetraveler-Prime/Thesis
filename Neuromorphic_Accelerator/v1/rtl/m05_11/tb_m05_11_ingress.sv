// Standalone no-HLS M05.11 256->128/192b ingress adapter XSim gate.
module tb_m05_11_ingress;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0;
    reg start_n=0, start_s=0;
    wire ready_start_n, ready_start_s;
    reg [31:0] expect_n=0, expect_s=0;
    reg [255:0] data_n=0, data_s=0;
    reg [31:0] keep_n=32'hffffffff, keep_s=32'hffffffff;
    reg last_n=0, last_s=0, valid_n=0, valid_s=0;
    wire ready_n, ready_s;
    wire [127:0] payload_n;
    wire [191:0] payload_s;
    wire valid_out_n, valid_out_s;
    reg ready_out_n=0, ready_out_s=0;
    wire done_n, done_s, fault_n, fault_s;
    wire [31:0] count_n, count_s;
    integer cycle=0, accepted_n=0, accepted_s=0, input_stalls=0;
    reg [127:0] goal_n0=128'h11223344, goal_n1=128'h55667788;
    reg [191:0] goal_s0=192'h778899aa;

    m05_ingress_dma_unpad #(.PAYLOAD_WIDTH(128)) u_neuron(
        .clk(clk), .rst_n(rst_n), .start_valid(start_n),
        .start_ready(ready_start_n), .start_expected_beats(expect_n),
        .s_dma_tdata(data_n), .s_dma_tkeep(keep_n),
        .s_dma_tlast(last_n), .s_dma_tvalid(valid_n),
        .s_dma_tready(ready_n), .m_hls_tdata(payload_n),
        .m_hls_tvalid(valid_out_n), .m_hls_tready(ready_out_n),
        .done(done_n), .fault(fault_n), .accepted_beats(count_n)
    );
    m05_ingress_dma_unpad #(.PAYLOAD_WIDTH(192)) u_synapse(
        .clk(clk), .rst_n(rst_n), .start_valid(start_s),
        .start_ready(ready_start_s), .start_expected_beats(expect_s),
        .s_dma_tdata(data_s), .s_dma_tkeep(keep_s),
        .s_dma_tlast(last_s), .s_dma_tvalid(valid_s),
        .s_dma_tready(ready_s), .m_hls_tdata(payload_s),
        .m_hls_tvalid(valid_out_s), .m_hls_tready(ready_out_s),
        .done(done_s), .fault(fault_s), .accepted_beats(count_s)
    );
    always @(posedge clk) begin
        cycle <= cycle + 1;
        if (cycle > 500) $fatal(1, "RTL_BRIDGE_FAIL ingress timeout");
        if (rst_n) begin
            if (valid_n && !ready_n) input_stalls <= input_stalls+1;
            if (valid_out_n && ready_out_n) begin
                if ((accepted_n==0 && payload_n !== goal_n0) ||
                    (accepted_n==1 && payload_n !== goal_n1) ||
                    accepted_n>=2)
                    $fatal(1, "RTL_BRIDGE_FAIL neuron payload/order");
                accepted_n <= accepted_n + 1;
            end
            if (valid_out_s && ready_out_s) begin
                if (payload_s !== goal_s0 || accepted_s!=0)
                    $fatal(1, "RTL_BRIDGE_FAIL synapse payload/order");
                accepted_s <= accepted_s + 1;
            end
        end
    end
    task automatic send_n(input [127:0] val, input last);
        integer j;
        reg ack;
    begin
        @(negedge clk);
        data_n={128'd0,val}; last_n=last; valid_n=1;
        ack=0;
        for(j=0;j<60;j=j+1) begin
            @(posedge clk);
            if(ready_n) begin ack=1; j=60; end
        end
        if(!ack) $fatal(1, "RTL_BRIDGE_FAIL neuron ingress never acknowledged");
        @(negedge clk);
        valid_n=0;
    end
    endtask
    initial begin
        repeat (4) @(negedge clk);
        rst_n=1;
        @(negedge clk);
        start_n=1; start_s=1; expect_n=2; expect_s=1;
        @(negedge clk);
        start_n=0; start_s=0;
        // Input VALID must be held stable while the HLS sink is stalled.
        @(negedge clk);
        data_n={128'd0,goal_n0}; last_n=0; valid_n=1;
        repeat (7) @(negedge clk);
        if(ready_n || !valid_out_n)
            $fatal(1, "RTL_BRIDGE_FAIL no genuine ingress TREADY stall");
        ready_out_n=1;
        @(negedge clk);
        valid_n=0;
        send_n(goal_n1,1);
        ready_out_s=1;
        @(negedge clk);
        data_s={64'd0,goal_s0}; last_s=1; valid_s=1;
        @(negedge clk);
        valid_s=0;
        repeat (3) @(negedge clk);
        if(!done_n || !done_s || count_n!=2 || count_s!=1 ||
           accepted_n!=2 || accepted_s!=1 || fault_n || fault_s)
            $fatal(1, "RTL_BRIDGE_FAIL normal ingresses not fully completed");
        // Zero-count synapse: no zero-byte DMA BTT should be armed.
        @(negedge clk);
        start_s=1; expect_s=0;
        @(negedge clk);
        start_s=0;
        if(!done_s || count_s!=0 || fault_s)
            $fatal(1, "RTL_BRIDGE_FAIL zero-input synapse channel");
        // Malformed last on first of two neuron beats: reject before HLS.
        @(negedge clk);
        start_n=1; expect_n=2;
        @(negedge clk);
        start_n=0;
        @(negedge clk);
        data_n={128'd0,goal_n0}; last_n=1; valid_n=1;
        @(negedge clk);
        valid_n=0;
        repeat (2) @(negedge clk);
        if(!fault_n || ready_start_n || valid_out_n || count_n!=0)
            $fatal(1, "RTL_BRIDGE_FAIL invalid early TLAST not quarantined");
        if(input_stalls<5)
            $fatal(1, "RTL_BRIDGE_FAIL ingress stall coverage");
        $display("PASS: M05.11 RTL ingress 128/192-bit unpad, exact TLAST and zero-count; input_stalls=%0d; early-TLAST quarantined", input_stalls);
        $finish;
    end
endmodule
