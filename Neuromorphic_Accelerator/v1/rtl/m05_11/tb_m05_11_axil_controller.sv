// M05.11b AXI4-Lite session slave contract test; stand-alone bus model.
// No real Zynq PS, no AMD AXI DMA IP, no HLS kernel, no board.
module tb_m05_11_axil_controller;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0;
    reg [7:0] awaddr=0;
    reg [2:0] awprot=0;
    reg awvalid=0;
    wire awready;
    reg [31:0] wdata=0;
    reg [3:0] wstrb=4'hf;
    reg wvalid=0;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready=0;
    reg [7:0] araddr=0;
    reg [2:0] arprot=0;
    reg arvalid=0;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready=0;

    reg bridge_ready=1;
    reg finish_ready=0;
    reg packet_done=0, packet_fault=0;
    reg neuron_done=0, synapse_done=0, external_done=0;
    reg neuron_fault=0, synapse_fault=0, external_fault=0;
    reg [31:0] trace_rows=0, neuron_beats=0, synapse_beats=0, external_beats=0;
    wire bridge_start_pulse, bridge_finish_valid;
    wire [63:0] bridge_session_id;
    wire [31:0] bridge_expected_trace, bridge_neurons, bridge_synapses,
                 bridge_external, bridge_finish_status;
    wire [2:0] controller_state;
    integer cycles=0, launches=0, finalize_handshakes=0;

    m05_11_axil_session_controller dut(
        .clk(clk),.rst_n(rst_n),
        .s_axi_awaddr(awaddr),.s_axi_awprot(awprot),
        .s_axi_awvalid(awvalid),.s_axi_awready(awready),
        .s_axi_wdata(wdata),.s_axi_wstrb(wstrb),
        .s_axi_wvalid(wvalid),.s_axi_wready(wready),
        .s_axi_bresp(bresp),.s_axi_bvalid(bvalid),.s_axi_bready(bready),
        .s_axi_araddr(araddr),.s_axi_arprot(arprot),
        .s_axi_arvalid(arvalid),.s_axi_arready(arready),
        .s_axi_rdata(rdata),.s_axi_rresp(rresp),.s_axi_rvalid(rvalid),
        .s_axi_rready(rready),
        .bridge_start_ready(bridge_ready),
        .trace_finish_ready(finish_ready),.trace_packet_done(packet_done),
        .trace_packet_fault(packet_fault),
        .neuron_done(neuron_done),.synapse_done(synapse_done),
        .external_done(external_done),
        .neuron_fault(neuron_fault),.synapse_fault(synapse_fault),
        .external_fault(external_fault),
        .trace_rows(trace_rows),.neuron_beats(neuron_beats),
        .synapse_beats(synapse_beats),.external_beats(external_beats),
        .bridge_start_pulse(bridge_start_pulse),
        .bridge_session_id(bridge_session_id),
        .bridge_expected_trace(bridge_expected_trace),
        .bridge_neurons(bridge_neurons),
        .bridge_synapses(bridge_synapses),
        .bridge_external(bridge_external),
        .bridge_finish_valid(bridge_finish_valid),
        .bridge_finish_status(bridge_finish_status),
        .controller_state(controller_state)
    );

    always @(posedge clk) begin
        cycles <= cycles+1;
        if(cycles > 2000)
            $fatal(1, "AXIL_BRIDGE_FAIL timeout");
        if(rst_n) begin
            if(bridge_start_pulse) launches <= launches+1;
            if(bridge_finish_valid && finish_ready)
                finalize_handshakes <= finalize_handshakes+1;
        end
    end

    // order=0: send AW then W; order=1: W then AW. AXI allows independent
    // arrival; responses must be retained until BREADY.
    task automatic write_reg(input [7:0] addr, input [31:0] data,
                             input [3:0] strb, input order,
                             input [1:0] expected_resp);
    begin
        if(order==0) begin
            @(negedge clk);
            awaddr=addr; awvalid=1;
            wait(awready);
            @(posedge clk);
            @(negedge clk);
            awvalid=0;
            wdata=data; wstrb=strb; wvalid=1;
            wait(wready);
            @(posedge clk);
            @(negedge clk);
            wvalid=0;
        end else begin
            @(negedge clk);
            wdata=data; wstrb=strb; wvalid=1;
            wait(wready);
            @(posedge clk);
            @(negedge clk);
            wvalid=0;
            awaddr=addr; awvalid=1;
            wait(awready);
            @(posedge clk);
            @(negedge clk);
            awvalid=0;
        end
        wait(bvalid);
        repeat(3) begin
            @(negedge clk);
            if(!bvalid || bresp !== expected_resp)
                $fatal(1,"AXIL_BRIDGE_FAIL response changed under BREADY stall addr=%h",addr);
        end
        bready=1;
        @(posedge clk);
        @(negedge clk);
        bready=0;
    end
    endtask

    task automatic read_reg(input [7:0] addr, input [31:0] expected_data,
                            input [1:0] expected_resp);
    begin
        @(negedge clk);
        araddr=addr;
        arvalid=1;
        wait(arready);
        @(posedge clk);
        @(negedge clk);
        arvalid=0;
        wait(rvalid);
        repeat(3) begin
            @(negedge clk);
            if(!rvalid || rdata !== expected_data ||
               rresp !== expected_resp)
                $fatal(1,"AXIL_BRIDGE_FAIL RDATA/RRESP/RVALID changed while stalled addr=%h observed=%h",addr,rdata);
        end
        rready=1;
        @(posedge clk);
        @(negedge clk);
        rready=0;
    end
    endtask

    initial begin
        repeat(4) @(negedge clk);
        rst_n=1;
        read_reg(8'h38,32'h0005110b,2'b00);
        read_reg(8'h04,32'd0,2'b00);
        // START with unconfigured count must fail before any bridge pulses.
        write_reg(8'h00,1,4'hf,0,2'b10);
        if(launches!=0) $fatal(1,"AXIL_BRIDGE_FAIL unconfigured launch");
        write_reg(8'h08,32'h5678abcd,4'hf,0,2'b00);
        write_reg(8'h0c,32'h01234567,4'hf,1,2'b00);
        write_reg(8'h10,2,4'hf,0,2'b00);
        write_reg(8'h14,2,4'hf,1,2'b00);
        write_reg(8'h18,1,4'hf,0,2'b00);
        write_reg(8'h1c,1,4'hf,1,2'b00);
        // WSTRB update on session LOW register.
        write_reg(8'h08,32'h000000ef,4'b0001,1,2'b00);
        read_reg(8'h08,32'h5678abef,2'b00);
        // A misaligned AXI register address is rejected.
        write_reg(8'h09,7,4'hf,0,2'b10);
        read_reg(8'h09,32'h0,2'b10);
        // Four transport shims must acknowledge readiness together.
        bridge_ready=0;
        write_reg(8'h00,1,4'hf,1,2'b10);
        bridge_ready=1;
        write_reg(8'h00,1,4'hf,0,2'b00);
        repeat(2) @(negedge clk);
        if(launches!=1 || controller_state!=3'd1 ||
           bridge_session_id!==64'h012345675678abef ||
           bridge_expected_trace!==2 || bridge_neurons!==2 ||
           bridge_synapses!==1 || bridge_external!==1)
            $fatal(1,"AXIL_BRIDGE_FAIL start one-shot/config outputs");
        // No second START and no changes to counts while running.
        write_reg(8'h00,1,4'hf,0,2'b10);
        write_reg(8'h10,3,4'hf,1,2'b10);
        // A real PS would have read HLS ap_done/ap_return already.
        write_reg(8'h20,4,4'hf,0,2'b00);
        write_reg(8'h00,2,4'hf,1,2'b00);
        repeat(6) begin
            @(negedge clk);
            if(!bridge_finish_valid || bridge_finish_status!==4 ||
               controller_state!==3'd2)
                $fatal(1,"AXIL_BRIDGE_FAIL finish handshake did not persist under trace stall");
        end
        finish_ready=1;
        repeat(3) @(negedge clk);
        finish_ready=0;
        if(finalize_handshakes!=1 || bridge_finish_valid)
            $fatal(1,"AXIL_BRIDGE_FAIL finalize duplicate");
        trace_rows=1;
        packet_done=1;
        repeat(3) @(negedge clk);
        if(controller_state!=3'd4)
            $fatal(1,"AXIL_BRIDGE_FAIL nonzero HLS result did not quarantine");
        write_reg(8'h00,4,4'hf,0,2'b10);
        write_reg(8'h00,1,4'hf,0,2'b10);
        // Confirm a true reset is necessary after a failed transaction.
        @(negedge clk);
        rst_n=0;
        packet_done=0;
        repeat(3) @(negedge clk);
        rst_n=1;
        launches=0;
        finalize_handshakes=0;
        write_reg(8'h08,32'h00000020,4'hf,0,2'b00);
        write_reg(8'h0c,0,4'hf,0,2'b00);
        write_reg(8'h10,2,4'hf,0,2'b00);
        write_reg(8'h14,2,4'hf,0,2'b00);
        write_reg(8'h18,0,4'hf,0,2'b00);
        write_reg(8'h1c,0,4'hf,0,2'b00);
        neuron_done=0;
        synapse_done=0;
        external_done=0;
        trace_rows=0;
        finish_ready=0;
        write_reg(8'h00,1,4'hf,0,2'b00);
        repeat(2) @(negedge clk);
        if(launches!=1 || controller_state!==3'd1)
            $fatal(1,"AXIL_BRIDGE_FAIL second independent start");
        write_reg(8'h20,0,4'hf,0,2'b00);
        write_reg(8'h00,2,4'hf,0,2'b00);
        finish_ready=1;
        repeat(3) @(negedge clk);
        finish_ready=0;
        neuron_done=1; synapse_done=1; external_done=1;
        trace_rows=2; neuron_beats=2; synapse_beats=0; external_beats=0;
        packet_done=1;
        repeat(3) @(negedge clk);
        if(controller_state!==3'd3)
            $fatal(1,"AXIL_BRIDGE_FAIL complete not reached");
        read_reg(8'h24,2,2'b00);
        read_reg(8'h28,2,2'b00);
        read_reg(8'h2c,0,2'b00);
        read_reg(8'h30,0,2'b00);
        write_reg(8'h00,4,4'hf,0,2'b00);
        read_reg(8'h04,0,2'b00);
        if(launches!=1 || finalize_handshakes!=1)
            $fatal(1,"AXIL_BRIDGE_FAIL duplicate launch/finalize");
        $display("PASS: M05.11b AXI-Lite separated AW/W, persistent R/B backpressure, session START/FINISH/ACK, failure quarantine and clean restart");
        $finish;
    end
endmodule
