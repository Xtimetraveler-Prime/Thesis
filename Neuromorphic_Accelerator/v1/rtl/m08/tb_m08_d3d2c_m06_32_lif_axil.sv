// D3.D.2C source-only Icarus: actual 32-neuron M06 3/4 decay, five
// recurrent synapses, 17 M06 external events aggregated on PC.
// Full AXI4-Lite write/readback compares 128 voltages, masks and 128
// on-device delivered-synaptic-current words; no mock IP or board.
module tb_m08_d3d2c_m06_32_lif_axil;
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

    m08_d3d2c_m06_32_lif_axil dut (.*);

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
            base=12'h100+n*32;
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
            base=12'h500+e*16;
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
            base=12'h900+n*32;
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
            base=12'hD00+n*16;
            read_reg(base,s0,2'b00);
            read_reg(base+4,s1,2'b00);
            read_reg(base+8,s2,2'b00);
            read_reg(base+12,s3,2'b00);
        end
    endtask

    reg [31:0] vectors [0:578];
    reg [1023:0] vector_path;
    integer base_word, edge_base, output_base, e, t, r;
    initial begin
        if (!$value$plusargs("M06_VECTORS=%s",vector_path))
            $fatal(1,"missing generated M06 oracle path");
        $readmemh(vector_path,vectors);
        if (vectors[0] !== 32'hD2C00001 ||
            vectors[1] !== 32'd3 ||
            vectors[2] !== 32'd5)
            $fatal(1,"original M06 reference header invalid");
        repeat (10) @(negedge aclk);
        aresetn=1;
        read_reg(12'h000,32'h4D33324E,2'b00);
        read_reg(12'h004,32'h00040000,2'b00);
        read_reg(12'h900,0,2'b10);
        read_reg(12'hD00,0,2'b10);
        write_reg(12'h014,1,4'hF,2'b10); // no config
        write_reg(12'h020,9,4'hF,2'b10); // too many edges
        write_reg(12'h500,32,4'hF,2'b10); // invalid pre index >= 32
        write_reg(12'h504,32,4'hF,2'b10); // invalid post index >= 32
        write_reg(12'h50C,0,4'hF,2'b10); // no zero-delay route
        write_reg(12'h508,32'h0000FFFF,4'hF,2'b10); // weight must sign-extend
        write_reg(12'h50C,1,4'h7,2'b10); // no partial write
        write_reg(12'h501,1,4'hF,2'b11); // no unaligned write
        write_reg(12'h900,32'hA5A55A5A,4'hF,2'b11);
        write_reg(12'hD00,32'hA5A55A5A,4'hF,2'b11);
        write_reg(12'h00C,vectors[0],4'hF,2'b00);
        write_reg(12'h010,vectors[1],4'hF,2'b00);
        write_reg(12'h020,vectors[2],4'hF,2'b00);
        for(n=0;n<32;n=n+1) begin
            base_word=3+n*8;
            set_neuron(n,
                vectors[base_word+0],vectors[base_word+1],
                vectors[base_word+2],vectors[base_word+3],
                vectors[base_word+4],vectors[base_word+5],
                vectors[base_word+6],vectors[base_word+7]);
        end
        // Only five ACTIVE M06 edges may be written: unused slots must
        // remain reset instead of receiving an illegal zero delay.
        for(e=0;e<5;e=e+1) begin
            edge_base=259+e*4;
            set_edge(e,vectors[edge_base+0],vectors[edge_base+1],
                       vectors[edge_base+2],vectors[edge_base+3]);
        end
        read_reg(12'h500,vectors[259],2'b00);
        read_reg(12'h504,vectors[260],2'b00);
        read_reg(12'h50C,vectors[262],2'b00);
        read_reg(12'h100,vectors[3],2'b00);
        read_reg(12'h11C,vectors[10],2'b00);
        for(r=0;r<2;r=r+1) begin
            if(r!=0) write_reg(12'h00C,vectors[0]+r,4'hF,2'b00);
            write_reg(12'h014,1,4'hF,2'b00);
            read_reg(12'h008,2,2'b00); // still busy
            write_reg(12'h010,0,4'hF,2'b10); // config cannot change while busy
            read_reg(12'hD00,0,2'b10); // no early result publication
            wait(dut.done===1'b1);
            read_reg(12'h008,1,2'b00);
            read_reg(12'h018,vectors[0]+r,2'b00);
            read_reg(12'h01C,r+1,2'b00);
            for(n=0;n<32;n=n+1) begin
                output_base=291+n*9;
                verify_neuron(n,
                    vectors[output_base+0],vectors[output_base+1],
                    vectors[output_base+2],vectors[output_base+3],
                    vectors[output_base+4]);
                verify_syn(n,
                    vectors[output_base+5],vectors[output_base+6],
                    vectors[output_base+7],vectors[output_base+8]);
            end
            $display("M08_D3D2C_M06_32X4_REAL_RTL_PARITY_PASS run=%0d",r+1);
        end
        read_reg(12'h8FC,0,2'b11); // ABI gap
        read_reg(12'hF00,0,2'b11); // beyond synaptic trace
        $display("M08_D3D2C_M06_FULL_128_VOLTAGE_SPIKE_SYN_CURRENT_RTL_PASS");
        $finish;
    end
    initial begin
        #1200000;
        $fatal(1,"M08 D3.D.2C M06 RTL global timeout");
    end
endmodule
