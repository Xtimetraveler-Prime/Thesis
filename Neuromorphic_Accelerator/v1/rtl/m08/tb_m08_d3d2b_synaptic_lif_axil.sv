// D3.D.2B genuine clocked RTL: 4 LIF neurons, 8 delayed recurrent edges,
// complete M02 hand-calculated voltages/spikes/synaptic sums for two cases.
// PC/CI ONLY; no Vivado FPGA configuration or physical JTAG assertion.
module tb_m08_d3d2b_synaptic_lif_axil;
    reg aclk=0;
    always #5 aclk=~aclk;
    reg aresetn=0;
    reg [11:0] s_axi_awaddr=0;
    reg [2:0] s_axi_awprot=0;
    reg s_axi_awvalid=0;
    wire s_axi_awready;
    reg [31:0] s_axi_wdata=0;
    reg [3:0] s_axi_wstrb=4'hF;
    reg s_axi_wvalid=0;
    wire s_axi_wready;
    wire [1:0] s_axi_bresp;
    wire s_axi_bvalid;
    reg s_axi_bready=0;
    reg [11:0] s_axi_araddr=0;
    reg [2:0] s_axi_arprot=0;
    reg s_axi_arvalid=0;
    wire s_axi_arready;
    wire [31:0] s_axi_rdata;
    wire [1:0] s_axi_rresp;
    wire s_axi_rvalid;
    reg s_axi_rready=0;
    integer n;
    reg [31:0] held;

    m08_d3d2b_synaptic_lif_axil dut (.*);

    task automatic write_reg(
        input [11:0] addr, input [31:0] data,
        input [3:0] strobe, input [1:0] expected_response
    );
    integer timeout_cycles;
    begin
        // Deliberately send AW before W to test decoupled AXI-Lite channels.
        @(negedge aclk);
        s_axi_awaddr=addr; s_axi_awvalid=1;
        timeout_cycles=0;
        begin : wait_aw
            forever begin
                @(posedge aclk);
                timeout_cycles=timeout_cycles+1;
                if (s_axi_awready) disable wait_aw;
                if (timeout_cycles>40) $fatal(1, "AW timeout addr=%h",addr);
            end
        end
        @(negedge aclk);
        s_axi_awvalid=0;
        @(negedge aclk);
        s_axi_wdata=data; s_axi_wstrb=strobe; s_axi_wvalid=1;
        timeout_cycles=0;
        begin : wait_w
            forever begin
                @(posedge aclk);
                timeout_cycles=timeout_cycles+1;
                if (s_axi_wready) disable wait_w;
                if (timeout_cycles>40) $fatal(1, "W timeout addr=%h",addr);
            end
        end
        @(negedge aclk);
        s_axi_wvalid=0;
        timeout_cycles=0;
        while (!s_axi_bvalid) begin
            @(posedge aclk);
            timeout_cycles=timeout_cycles+1;
            if (timeout_cycles>40) $fatal(1, "B timeout addr=%h",addr);
        end
        if (s_axi_bresp !== expected_response)
            $fatal(1,"B response mismatch addr=%h got=%h want=%h",
                   addr,s_axi_bresp,expected_response);
        repeat (2) @(posedge aclk);
        if (!s_axi_bvalid || s_axi_bresp !== expected_response)
            $fatal(1,"B response changed under backpressure");
        @(negedge aclk); s_axi_bready=1;
        @(negedge aclk); s_axi_bready=0;
    end
    endtask

    task automatic read_reg(input [11:0] addr,
                            input [31:0] expected_data,
                            input [1:0] expected_resp);
    integer timeout_cycles;
    begin
        @(negedge aclk);
        s_axi_araddr=addr; s_axi_arvalid=1;
        timeout_cycles=0;
        begin : wait_ar
            forever begin
                @(posedge aclk);
                timeout_cycles=timeout_cycles+1;
                if (s_axi_arready) disable wait_ar;
                if (timeout_cycles>40) $fatal(1,"AR timeout addr=%h",addr);
            end
        end
        @(negedge aclk); s_axi_arvalid=0;
        timeout_cycles=0;
        while (!s_axi_rvalid) begin
            @(posedge aclk);
            timeout_cycles=timeout_cycles+1;
            if (timeout_cycles>40) $fatal(1, "R timeout addr=%h",addr);
        end
        if (s_axi_rresp !== expected_resp ||
            s_axi_rdata !== expected_data)
            $fatal(1,"R response mismatch addr=%h got=%h/%h want=%h/%h",
                   addr,s_axi_rdata,s_axi_rresp,expected_data,expected_resp);
        held=s_axi_rdata;
        repeat (2) @(posedge aclk);
        if (!s_axi_rvalid || s_axi_rdata !== held ||
            s_axi_rresp !== expected_resp)
            $fatal(1,"R payload changed under backpressure addr=%h",addr);
        @(negedge aclk); s_axi_rready=1;
        @(negedge aclk); s_axi_rready=0;
    end
    endtask



    task automatic set_neuron(input integer n,
        input [31:0] initial_v,bias,threshold,reset_v,
        input [31:0] c0,c1,c2,c3);
        reg [11:0] base;
        begin
            base=12'h040+n*32;
            write_reg(base,initial_v,4'hF,2'b00);
            write_reg(base+4,bias,4'hF,2'b00);
            write_reg(base+8,threshold,4'hF,2'b00);
            write_reg(base+12,reset_v,4'hF,2'b00);
            write_reg(base+16,c0,4'hF,2'b00);
            write_reg(base+20,c1,4'hF,2'b00);
            write_reg(base+24,c2,4'hF,2'b00);
            write_reg(base+28,c3,4'hF,2'b00);
        end
    endtask

    task automatic set_edge(input integer e,
        input [31:0] pre,post,weight,delay);
        reg [11:0] base;
        begin
            base=12'h200+e*16;
            write_reg(base,pre,4'hF,2'b00);
            write_reg(base+4,post,4'hF,2'b00);
            write_reg(base+8,weight,4'hF,2'b00);
            write_reg(base+12,delay,4'hF,2'b00);
        end
    endtask

    task automatic verify_neuron(input integer n,
        input [31:0] v0,v1,v2,v3,mask);
        reg [11:0] base;
        begin
            base=12'h100+n*32;
            read_reg(base,v0,2'b00);
            read_reg(base+4,v1,2'b00);
            read_reg(base+8,v2,2'b00);
            read_reg(base+12,v3,2'b00);
            read_reg(base+16,mask,2'b00);
        end
    endtask

    task automatic verify_syn(input integer n,
        input [31:0] s0,s1,s2,s3);
        reg [11:0] base;
        begin
            base=12'h300+n*16;
            read_reg(base,s0,2'b00);
            read_reg(base+4,s1,2'b00);
            read_reg(base+8,s2,2'b00);
            read_reg(base+12,s3,2'b00);
        end
    endtask

    initial begin
        repeat (10) @(negedge aclk);
        aresetn=1;

    // Reject unwritten network; active delay slots must not be zero.
    read_reg(12'h000,32'h4D34534E,2'b00);
    read_reg(12'h004,32'h00030000,2'b00);
    read_reg(12'h300,0,2'b10); // results gated until DONE
    write_reg(12'h014,1,4'hF,2'b10); // invalid config
    write_reg(12'h020,9,4'hF,2'b10); // edge count > capacity
    write_reg(12'h20C,0,4'hF,2'b10); // zero-delay rejected
    write_reg(12'h208,32'h0000FFFF,4'hF,2'b10); // unextended weight
    write_reg(12'h200,4,4'hF,2'b10); // invalid source neuron
    write_reg(12'h20C,1,4'h7,2'b10); // partial strobe
    write_reg(12'h201,1,4'hF,2'b11); // unaligned
    write_reg(12'h300,32'hA5A55A5A,4'hF,2'b11); // no host-produced syn traces
    write_reg(12'h100,32'hA5A55A5A,4'hF,2'b10); // no host-produced voltages

    // Workload 1: CHAIN_RECURRENT — recurrent delay, duplicate edges, bias and inhibition.
    write_reg(12'h00C,32'hD2B00001,4'hF,2'b00);
    write_reg(12'h010,32'h00000002,4'hF,2'b00);
    write_reg(12'h020,32'd8,4'hF,2'b00);
    set_neuron(0,32'h00000000,32'h00000000,32'h00000004,32'h00000000,32'h00000004,32'h00000000,32'h00000000,32'h00000000);
    set_neuron(1,32'h00000000,32'h00000000,32'h00000003,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000000);
    set_neuron(2,32'h00000000,32'h00000000,32'h00000003,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000000);
    set_neuron(3,32'h00000000,32'h00000000,32'h00000004,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000000);
    set_edge(0,32'h00000000,32'h00000001,32'h00000004,32'h00000001);
    set_edge(1,32'h00000001,32'h00000002,32'h00000005,32'h00000001);
    set_edge(2,32'h00000002,32'h00000003,32'h00000004,32'h00000001);
    set_edge(3,32'h00000003,32'h00000000,32'h00000001,32'h00000001);
    set_edge(4,32'h00000000,32'h00000002,32'h00000002,32'h00000002);
    set_edge(5,32'h00000000,32'h00000002,32'hFFFFFFFE,32'h00000002);
    set_edge(6,32'h00000001,32'h00000001,32'h00000002,32'h00000002);
    set_edge(7,32'h00000002,32'h00000000,32'hFFFFFFFD,32'h00000001);
    write_reg(12'h014,1,4'hF,2'b00);
    wait(dut.done === 1'b1);
    read_reg(12'h008,1,2'b00);
    read_reg(12'h018,32'hD2B00001,2'b00);
    read_reg(12'h01C,32'h00000001,2'b00);
    verify_neuron(0,32'h00000000,32'h00000000,32'h00000000,32'hFFFFFFFD,32'h00000001);
    verify_neuron(1,32'h00000000,32'h00000000,32'h00000000,32'h00000002,32'h00000002);
    verify_neuron(2,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000004);
    verify_neuron(3,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000008);
    verify_syn(0,32'h00000000,32'h00000000,32'h00000000,32'hFFFFFFFD);
    verify_syn(1,32'h00000000,32'h00000004,32'h00000000,32'h00000002);
    verify_syn(2,32'h00000000,32'h00000000,32'h00000005,32'h00000000);
    verify_syn(3,32'h00000000,32'h00000000,32'h00000000,32'h00000004);
    $display("M08_D3D2B_CHAIN_RECURRENT_RTL_PASS");

    // Workload 2: INHIBITION_HALF_DECAY — recurrent delay, duplicate edges, bias and inhibition.
    write_reg(12'h00C,32'hD2B00002,4'hF,2'b00);
    write_reg(12'h010,32'h00000001,4'hF,2'b00);
    write_reg(12'h020,32'd8,4'hF,2'b00);
    set_neuron(0,32'hFFFFFFFD,32'h00000000,32'h00000005,32'hFFFFFFFE,32'h00000008,32'h00000000,32'h00000000,32'h00000000);
    set_neuron(1,32'h00000000,32'h00000003,32'h00000006,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000000);
    set_neuron(2,32'h00000000,32'h00000000,32'h00000005,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000000);
    set_neuron(3,32'hFFFFFFFF,32'hFFFFFFFF,32'h00000008,32'hFFFFFFFE,32'h00000000,32'h00000000,32'h00000000,32'h00000000);
    set_edge(0,32'h00000000,32'h00000001,32'h00000003,32'h00000001);
    set_edge(1,32'h00000000,32'h00000002,32'h00000006,32'h00000001);
    set_edge(2,32'h00000000,32'h00000002,32'hFFFFFFFA,32'h00000001);
    set_edge(3,32'h00000001,32'h00000002,32'h00000006,32'h00000001);
    set_edge(4,32'h00000001,32'h00000001,32'h00000004,32'h00000002);
    set_edge(5,32'h00000001,32'h00000000,32'hFFFFFFFC,32'h00000001);
    set_edge(6,32'h00000002,32'h00000003,32'h0000000A,32'h00000001);
    set_edge(7,32'h00000003,32'h00000000,32'hFFFFFFFE,32'h00000001);
    write_reg(12'h014,1,4'hF,2'b00);
    wait(dut.done === 1'b1);
    read_reg(12'h008,1,2'b00);
    read_reg(12'h018,32'hD2B00002,2'b00);
    read_reg(12'h01C,32'h00000002,2'b00);
    verify_neuron(0,32'hFFFFFFFE,32'hFFFFFFFF,32'hFFFFFFFC,32'hFFFFFFFE,32'h00000001);
    verify_neuron(1,32'h00000003,32'h00000000,32'h00000003,32'h00000000,32'h0000000A);
    verify_neuron(2,32'h00000000,32'h00000000,32'h00000000,32'h00000000,32'h00000004);
    verify_neuron(3,32'hFFFFFFFF,32'hFFFFFFFF,32'hFFFFFFFF,32'hFFFFFFFE,32'h00000008);
    verify_syn(0,32'h00000000,32'h00000000,32'hFFFFFFFC,32'h00000000);
    verify_syn(1,32'h00000000,32'h00000003,32'h00000000,32'h00000004);
    verify_syn(2,32'h00000000,32'h00000000,32'h00000006,32'h00000000);
    verify_syn(3,32'h00000000,32'h00000000,32'h00000000,32'h0000000A);
    $display("M08_D3D2B_INHIBITION_HALF_DECAY_RTL_PASS");

        // Probe immutable/read-only recorded synapse currents; M02 requires
        // on-device routing rather than host supplied already-summed current.
        read_reg(12'h340,0,2'b11); // outside trace window
        $display("M08_D3D2B_SYNAPTIC_ROUTING_RTL_ALL_PASS");
        $finish;
    end
    initial begin
        #800000;
        $fatal(1, "D3.D.2B RTL global timeout");
    end
endmodule
