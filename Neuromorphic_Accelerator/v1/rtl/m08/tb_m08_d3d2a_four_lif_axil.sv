// Real Icarus RTL four-neuron M02 edge-case regression.
// PC-only: NOT native Vivado and NOT a physical KV260 run.
module tb_m08_d3d2a_four_lif_axil;
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

    m08_d3d2a_four_lif_axil dut (.*);

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


    task automatic set_neuron(
        input integer idx,
        input [31:0] init_v, input [31:0] bias,
        input [31:0] thresh, input [31:0] reset_v,
        input [31:0] i0, input [31:0] i1,
        input [31:0] i2, input [31:0] i3
    );
    reg [11:0] base;
    begin
        base = 12'h040 + idx*32;
        write_reg(base+12'h000,init_v,4'hF,2'b00);
        write_reg(base+12'h004,bias,4'hF,2'b00);
        write_reg(base+12'h008,thresh,4'hF,2'b00);
        write_reg(base+12'h00C,reset_v,4'hF,2'b00);
        write_reg(base+12'h010,i0,4'hF,2'b00);
        write_reg(base+12'h014,i1,4'hF,2'b00);
        write_reg(base+12'h018,i2,4'hF,2'b00);
        write_reg(base+12'h01C,i3,4'hF,2'b00);
    end
    endtask

    task automatic verify_neuron(
        input integer idx,
        input [31:0] v0, input [31:0] v1,
        input [31:0] v2, input [31:0] v3,
        input [31:0] mask
    );
    reg [11:0] base;
    begin
        base = 12'h100 + idx*32;
        read_reg(base,v0,2'b00);
        read_reg(base+12'h004,v1,2'b00);
        read_reg(base+12'h008,v2,2'b00);
        read_reg(base+12'h00C,v3,2'b00);
        read_reg(base+12'h010,mask,2'b00);
    end
    endtask

    task automatic start_and_check(input [31:0] expected_nonce,
                                   input [31:0] expected_runs);
    begin
        write_reg(12'h014,32'd1,4'hF,2'b00);
        // The engine must genuinely clock through four times four updates.
        wait(dut.done === 1'b1);
        read_reg(12'h008,32'h00000001,2'b00);
        read_reg(12'h018,expected_nonce,2'b00);
        read_reg(12'h01C,expected_runs,2'b00);
    end
    endtask

    initial begin
        repeat(10) @(negedge aclk);
        aresetn=1;
        read_reg(12'h000,32'h4D344C46,2'b00);
        read_reg(12'h004,32'h00020000,2'b00);
        read_reg(12'h008,32'h00000000,2'b00);
        read_reg(12'h018,0,2'b10);
        read_reg(12'h100,0,2'b10);
        write_reg(12'h014,1,4'hF,2'b10); // invalid unconfigured START
        write_reg(12'h044,32'h0000FFFF,4'hF,2'b10); // not signed16
        write_reg(12'h010,32'd3,4'hF,2'b10); // invalid decay
        write_reg(12'h014,1,4'h7,2'b10); // partial strobe
        write_reg(12'h015,1,4'hF,2'b11); // unaligned
        write_reg(12'h100,32'hA5A55A5A,4'hF,2'b10); // no host output spoof
        read_reg(12'h114,0,2'b11); // unmapped result gap

        write_reg(12'h00C,32'hD2A00001,4'hF,2'b00);
        write_reg(12'h010,32'd1,4'hF,2'b00); // half decay
        set_neuron(0,32'hFFFFFFFB,1,5,32'hFFFFFFFE,3,7,32'hFFFFFFFC,0);
        set_neuron(1,32760,0,32767,32'hFFFFFFFB,
                   20000,32'hFFFF8000,32'hFFFFFFFE,32'hFFFFFFFE);
        set_neuron(2,0,3,6,0,0,0,32'hFFFFFFFA,0);
        set_neuron(3,32'hFFFFFFFF,32'hFFFFFFFF,9,32'hFFFFFFFE,
                   0,0,0,0);
        // Negative case: an invalid threshold must reject START, not mutate
        // any physical output; restore the valid threshold afterward.
        write_reg(12'h088,0,4'hF,2'b00);
        write_reg(12'h014,1,4'hF,2'b10);
        write_reg(12'h088,6,4'hF,2'b00);

        start_and_check(32'hD2A00001,1);
        verify_neuron(0,2,32'hFFFFFFFE,32'hFFFFFFFC,32'hFFFFFFFF,2);
        verify_neuron(1,32'hFFFFFFFB,32'hFFFF8000,32'hFFFFBFFE,
                      32'hFFFFDFFD,1);
        verify_neuron(2,3,4,32'hFFFFFFFF,3,0);
        verify_neuron(3,32'hFFFFFFFF,32'hFFFFFFFF,
                      32'hFFFFFFFF,32'hFFFFFFFF,0);
        $display("M08_D3D2A_FOUR_NEURON_HALF_DECAY_PARITY_PASS");

        write_reg(12'h00C,32'hD2A00002,4'hF,2'b00);
        write_reg(12'h010,32'd2,4'hF,2'b00); // unit decay
        set_neuron(0,0,3,6,0,0,0,32'hFFFFFFFA,0);
        set_neuron(1,32760,0,32767,32'hFFFFFFFB,
                   20,32'hFFFF8000,32'hFFFFFFFE,32'hFFFFFFFE);
        set_neuron(2,32'hFFFFFFFB,1,5,32'hFFFFFFFE,
                   3,7,32'hFFFFFFFC,0);
        set_neuron(3,32'hFFFFFFFF,32'hFFFFFFFF,9,32'hFFFFFFFE,
                   0,0,0,0);
        start_and_check(32'hD2A00002,2);
        verify_neuron(0,3,0,32'hFFFFFFFD,0,2);
        verify_neuron(1,32'hFFFFFFFB,32'hFFFF8000,32'hFFFF8000,
                      32'hFFFF8000,1);
        verify_neuron(2,32'hFFFFFFFF,32'hFFFFFFFE,32'hFFFFFFFB,
                      32'hFFFFFFFC,2);
        verify_neuron(3,32'hFFFFFFFE,32'hFFFFFFFD,32'hFFFFFFFC,
                      32'hFFFFFFFB,0);
        read_reg(12'h100,3,2'b00); // old result was overwritten, not echoed
        $display("M08_D3D2A_FOUR_NEURON_UNIT_DECAY_PARITY_PASS");
        $display("M08_D3D2A_AXIL_FOUR_NEURON_SOURCE_RTL_PASS");
        $finish;
    end
    initial begin
        #500000;
        $fatal(1,"D3D2A four-neuron RTL global timeout");
    end
endmodule
