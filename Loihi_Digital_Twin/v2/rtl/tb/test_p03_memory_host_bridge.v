`timescale 1ns/1ps

module test_p03_memory_host_bridge;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg compute_busy = 1'b0;
    reg req = 1'b0;
    reg write = 1'b0;
    reg [3:0] bank = 4'd0;
    reg [14:0] addr = 15'd0;
    reg [255:0] wdata = 256'd0;

    wire host_busy;
    wire ack;
    wire rvalid;
    wire error;
    wire [255:0] rdata;

    wire config_words_enb;
    wire config_words_web;
    wire [9:0] config_words_addrb;
    wire [127:0] config_words_dinb;
    reg [127:0] config_words_doutb = 128'd0;

    wire state_words_enb;
    wire state_words_web;
    wire [9:0] state_words_addrb;
    wire [63:0] state_words_dinb;
    wire [63:0] state_words_doutb = 64'd0;

    wire axon_words_enb;
    wire axon_words_web;
    wire [11:0] axon_words_addrb;
    wire [63:0] axon_words_dinb;
    wire [63:0] axon_words_doutb = 64'd0;

    wire synapse_words_enb;
    wire synapse_words_web;
    wire [14:0] synapse_words_addrb;
    wire [63:0] synapse_words_dinb;
    wire [63:0] synapse_words_doutb = 64'd0;

    wire route_desc_words_enb;
    wire route_desc_words_web;
    wire [9:0] route_desc_words_addrb;
    wire [31:0] route_desc_words_dinb;
    wire [31:0] route_desc_words_doutb = 32'd0;

    wire route_words_enb;
    wire route_words_web;
    wire [11:0] route_words_addrb;
    wire [31:0] route_words_dinb;
    wire [31:0] route_words_doutb = 32'd0;

    wire input_events_enb;
    wire input_events_web;
    wire [11:0] input_events_addrb;
    wire [31:0] input_events_dinb;
    wire [31:0] input_events_doutb = 32'd0;

    wire trace_words_enb;
    wire trace_words_web;
    wire [9:0] trace_words_addrb;
    wire [255:0] trace_words_dinb;
    reg [255:0] trace_words_doutb = 256'd0;

    wire packet_words_enb;
    wire packet_words_web;
    wire [11:0] packet_words_addrb;
    wire [63:0] packet_words_dinb;
    wire [63:0] packet_words_doutb = 64'd0;

    reg [127:0] config_mem [0:1023];
    reg [255:0] trace_mem [0:1023];

    always @(posedge clk) begin
        if (config_words_enb) begin
            if (config_words_web)
                config_mem[config_words_addrb] <= config_words_dinb;
            config_words_doutb <= config_mem[config_words_addrb];
        end
        if (trace_words_enb) begin
            if (trace_words_web)
                trace_mem[trace_words_addrb] <= trace_words_dinb;
            trace_words_doutb <= trace_mem[trace_words_addrb];
        end
    end

    p03_memory_host_bridge dut (
        .clk(clk), .resetn(resetn), .compute_busy(compute_busy),
        .req(req), .write(write), .bank(bank), .addr(addr), .wdata(wdata),
        .host_busy(host_busy), .ack(ack), .rvalid(rvalid), .error(error), .rdata(rdata),
        .config_words_enb(config_words_enb), .config_words_web(config_words_web),
        .config_words_addrb(config_words_addrb), .config_words_dinb(config_words_dinb),
        .config_words_doutb(config_words_doutb),
        .state_words_enb(state_words_enb), .state_words_web(state_words_web),
        .state_words_addrb(state_words_addrb), .state_words_dinb(state_words_dinb),
        .state_words_doutb(state_words_doutb),
        .axon_words_enb(axon_words_enb), .axon_words_web(axon_words_web),
        .axon_words_addrb(axon_words_addrb), .axon_words_dinb(axon_words_dinb),
        .axon_words_doutb(axon_words_doutb),
        .synapse_words_enb(synapse_words_enb), .synapse_words_web(synapse_words_web),
        .synapse_words_addrb(synapse_words_addrb), .synapse_words_dinb(synapse_words_dinb),
        .synapse_words_doutb(synapse_words_doutb),
        .route_desc_words_enb(route_desc_words_enb), .route_desc_words_web(route_desc_words_web),
        .route_desc_words_addrb(route_desc_words_addrb), .route_desc_words_dinb(route_desc_words_dinb),
        .route_desc_words_doutb(route_desc_words_doutb),
        .route_words_enb(route_words_enb), .route_words_web(route_words_web),
        .route_words_addrb(route_words_addrb), .route_words_dinb(route_words_dinb),
        .route_words_doutb(route_words_doutb),
        .input_events_enb(input_events_enb), .input_events_web(input_events_web),
        .input_events_addrb(input_events_addrb), .input_events_dinb(input_events_dinb),
        .input_events_doutb(input_events_doutb),
        .trace_words_enb(trace_words_enb), .trace_words_web(trace_words_web),
        .trace_words_addrb(trace_words_addrb), .trace_words_dinb(trace_words_dinb),
        .trace_words_doutb(trace_words_doutb),
        .packet_words_enb(packet_words_enb), .packet_words_web(packet_words_web),
        .packet_words_addrb(packet_words_addrb), .packet_words_dinb(packet_words_dinb),
        .packet_words_doutb(packet_words_doutb)
    );

    reg start_request = 1'b0;
    reg core_ready = 1'b0;
    reg done = 1'b0;
    wire core_start;
    wire run_busy;
    wire start_seen;
    wire start_blocked;
    wire [63:0] last_run_cycles;
    wire [31:0] completed_runs;
    wire [31:0] heartbeat;

    p03_run_monitor monitor (
        .ap_clk(clk), .resetn(resetn), .start_request(start_request),
        .host_busy(host_busy), .core_ready(core_ready), .done(done),
        .core_start(core_start), .busy(run_busy), .start_seen(start_seen),
        .start_blocked(start_blocked), .last_run_cycles(last_run_cycles),
        .completed_runs(completed_runs), .heartbeat(heartbeat)
    );

    task pulse_host_request;
        begin
            @(negedge clk);
            req = 1'b1;
            @(negedge clk);
            req = 1'b0;
        end
    endtask

    task wait_for_ack;
        integer timeout;
        begin
            timeout = 0;
            while (!ack && timeout < 12) begin
                @(posedge clk);
                timeout = timeout + 1;
            end
            if (!ack) begin
                $display("FAIL: host request timed out");
                $finish(1);
            end
        end
    endtask

    initial begin
        repeat (3) @(posedge clk);
        resetn = 1'b1;
        repeat (2) @(posedge clk);

        // Write and read a 128-bit configuration word through bank 0.
        bank = 4'd0;
        addr = 15'd7;
        write = 1'b1;
        wdata = 256'h0;
        wdata[127:0] = 128'h0123456789abcdef_fedcba9876543210;
        pulse_host_request();
        wait_for_ack();
        if (error) begin
            $display("FAIL: config write returned error");
            $finish(1);
        end
        // JTAG can be much slower than the PL clock; completion must remain
        // visible after the single-cycle memory operation has retired.
        repeat (3) @(posedge clk);
        if (!ack || error) begin
            $display("FAIL: host completion was not sticky for debug polling");
            $finish(1);
        end

        bank = 4'd0;
        addr = 15'd7;
        write = 1'b0;
        wdata = 256'd0;
        pulse_host_request();
        wait_for_ack();
        if (!rvalid || error || rdata[127:0] !== 128'h0123456789abcdef_fedcba9876543210) begin
            $display("FAIL: config readback mismatch rvalid=%0d error=%0d data=%032h", rvalid, error, rdata[127:0]);
            $finish(1);
        end

        // Exercise the widest 256-bit bank to verify the superset data path.
        bank = 4'd7;
        addr = 15'd3;
        write = 1'b1;
        wdata = 256'h00112233445566778899aabbccddeeff_ffeeddccbbaa99887766554433221100;
        pulse_host_request();
        wait_for_ack();
        if (error) begin
            $display("FAIL: trace write returned error");
            $finish(1);
        end

        bank = 4'd7;
        addr = 15'd3;
        write = 1'b0;
        pulse_host_request();
        wait_for_ack();
        if (!rvalid || error || rdata !== 256'h00112233445566778899aabbccddeeff_ffeeddccbbaa99887766554433221100) begin
            $display("FAIL: trace readback mismatch");
            $finish(1);
        end

        // Out-of-range addresses are rejected without touching a bank.
        bank = 4'd0;
        addr = 15'd1024;
        write = 1'b0;
        pulse_host_request();
        wait_for_ack();
        if (!error) begin
            $display("FAIL: out-of-range host address was not rejected");
            $finish(1);
        end

        // A running compute transaction rejects host access.
        compute_busy = 1'b1;
        bank = 4'd0;
        addr = 15'd0;
        pulse_host_request();
        wait_for_ack();
        if (!error) begin
            $display("FAIL: host request was accepted while compute_busy");
            $finish(1);
        end
        compute_busy = 1'b0;

        // A simultaneous host request and compute-start request gives the host
        // request priority and emits start_blocked instead of core_start.
        bank = 4'd0;
        addr = 15'd1;
        write = 1'b0;
        @(negedge clk);
        req = 1'b1;
        start_request = 1'b1;
        @(posedge clk);
        #1;
        if (core_start || !start_blocked) begin
            $display("FAIL: host/start arbitration did not block compute start");
            $finish(1);
        end
        @(negedge clk);
        req = 1'b0;
        start_request = 1'b0;
        wait_for_ack();

        // ap_ready is intentionally low before the first ap_ctrl_hs
        // transaction. It must not block an otherwise legal start request.
        repeat (2) @(posedge clk);
        core_ready = 1'b0;
        @(negedge clk);
        start_request = 1'b1;
        @(posedge clk);
        #1;
        if (!core_start || !run_busy || start_blocked) begin
            $display("FAIL: legal start was incorrectly gated by core_ready");
            $finish(1);
        end
        @(negedge clk);
        start_request = 1'b0;

        // Model eventual HLS completion. completed_runs must remain observable
        // independently of the transient done/ap_ready pulses.
        repeat (4) @(posedge clk);
        core_ready = 1'b1;
        @(negedge clk);
        done = 1'b1;
        @(posedge clk);
        @(negedge clk);
        done = 1'b0;
        core_ready = 1'b0;
        repeat (2) @(posedge clk);
        if (run_busy || !start_seen || last_run_cycles == 0 || completed_runs != 32'd1) begin
            $display("FAIL: run monitor completion accounting is incorrect runs=%0d cycles=%0d", completed_runs, last_run_cycles);
            $finish(1);
        end

        $display("P03 host bridge RTL simulation passed");
        $finish(0);
    end
endmodule
