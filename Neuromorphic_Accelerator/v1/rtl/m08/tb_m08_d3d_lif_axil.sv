// D3.D.1 genuine clocked RTL AXI4-Lite + M02 four-tick LIF testbench.
// Hardware outputs checked against independently calculated M02 fixtures.
// No JTAG/PS/DDR accessed; the owner native Vivado run is a separate gate.
module tb_m08_d3d_lif_axil;
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

    m08_d3d_lif_axil dut (.*);

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

    task automatic configure(
        input [31:0] nonce, input [31:0] initial_v,
        input [31:0] bias, input [31:0] threshold,
        input [31:0] reset_v, input [31:0] decay_mode,
        input [31:0] c0, input [31:0] c1,
        input [31:0] c2, input [31:0] c3
    );
    begin
        write_reg(12'h00C, nonce, 4'hF, 2'b00);
        write_reg(12'h010, initial_v, 4'hF, 2'b00);
        write_reg(12'h014, bias, 4'hF, 2'b00);
        write_reg(12'h018, threshold, 4'hF, 2'b00);
        write_reg(12'h01C, reset_v, 4'hF, 2'b00);
        write_reg(12'h020, decay_mode, 4'hF, 2'b00);
        write_reg(12'h024, c0, 4'hF, 2'b00);
        write_reg(12'h028, c1, 4'hF, 2'b00);
        write_reg(12'h02C, c2, 4'hF, 2'b00);
        write_reg(12'h030, c3, 4'hF, 2'b00);
    end
    endtask

    task automatic verify_run(
        input [31:0] nonce, input [31:0] mask,
        input [31:0] v0, input [31:0] v1,
        input [31:0] v2, input [31:0] v3,
        input [31:0] runs
    );
    begin
        write_reg(12'h034, 32'd1, 4'hF, 2'b00);
        read_reg(12'h008, 32'h00000001, 2'b00); // DONE=1, BUSY=0
        read_reg(12'h038, nonce, 2'b00);
        read_reg(12'h03C, mask, 2'b00);
        read_reg(12'h040, v0, 2'b00);
        read_reg(12'h044, v1, 2'b00);
        read_reg(12'h048, v2, 2'b00);
        read_reg(12'h04C, v3, 2'b00);
        read_reg(12'h050, runs, 2'b00);
    end
    endtask

    initial begin
        repeat(10) @(negedge aclk);
        aresetn=1;
        read_reg(12'h000, 32'h4D384C46, 2'b00);
        read_reg(12'h004, 32'h00010000, 2'b00);
        read_reg(12'h008, 32'h00000000, 2'b00);
        read_reg(12'h038, 32'h00000000, 2'b10); // output gated before DONE
        write_reg(12'h034, 32'd1, 4'hF, 2'b10); // invalid configuration
        write_reg(12'h018, 32'h00000005, 4'h7, 2'b10); // reject partial write
        write_reg(12'h014, 32'h0000FFFF, 4'hF, 2'b10); // reject mis-signed16
        write_reg(12'h035, 32'd1, 4'hF, 2'b11); // unaligned

        configure(32'hD3D00001, 32'hFFFFFFFB, 32'd1, 32'd5,
                  32'hFFFFFFFE, 32'd1, 32'd3, 32'd7, 32'hFFFFFFFC, 0);
        verify_run(32'hD3D00001, 32'h00000002,
                   32'd2, 32'hFFFFFFFE, 32'hFFFFFFFC, 32'hFFFFFFFF, 32'd1);
        write_reg(12'h040, 32'hA5A55A5A, 4'hF, 2'b11); // no result writes

        configure(32'hD3D00002, 32'd32760, 0, 32'd32767,
                  32'hFFFFFFFB, 32'd2, 32'd20,
                  32'hFFFF8000, 32'hFFFFFFFE, 32'hFFFFFFFE);
        verify_run(32'hD3D00002, 32'h00000001,
                   32'hFFFFFFFB, 32'hFFFF8000, 32'hFFFF8000,
                   32'hFFFF8000, 32'd2);

        configure(32'hD3D00003, 0, 32'd3, 32'd6,
                  0, 32'd2, 0, 0, 32'hFFFFFFFA, 0);
        verify_run(32'hD3D00003, 32'h00000002,
                   32'd3, 0, 32'hFFFFFFFD, 0, 32'd3);

        configure(32'hD3D00004, 32'hFFFFFFFF, 32'hFFFFFFFF,
                  32'd9, 32'hFFFFFFFE, 32'd1, 0, 0, 0, 0);
        verify_run(32'hD3D00004, 32'h00000000,
                   32'hFFFFFFFF, 32'hFFFFFFFF,
                   32'hFFFFFFFF, 32'hFFFFFFFF, 32'd4);

        read_reg(12'hFFF, 0, 2'b11); // unaligned/unmapped
        $display("M08_D3D_FOUR_FIXTURE_AXIL_M02_RTL_PASS");
        $finish;
    end
    initial begin
        #200000;
        $fatal(1,"D3D AXI-Lite RTL global timeout");
    end
endmodule
