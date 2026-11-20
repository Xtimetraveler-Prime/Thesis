// D3.D.2D source-only Icarus AXI protocol, not a board execution.
// Test ORIGINAL 17 distinct M06 raw external events sent one per AXI PUSH;
// verify 128 bucket sums are fabricated independently, not host coalesced.
// Then compare full real RTL 128 voltage+128 spikes+128 recurrent currents
// against independent M02 dense/event and M03 sparse M06 reference.
// Replay, clear, overflow atomic reject and write/read boundary negatives.
module tb_m08_d3d2d_raw_event_lif_axil;
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

    m08_d3d2d_raw_event_lif_axil dut (.*);

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

    reg [31:0] vectors [0:629];
    reg [1023:0] vector_path;
    integer base_word, edge_base, output_base, e, t, r;

    task automatic load_raw_events;
        integer ix;
        begin
            // Do not supply original software-summed input register values.
            // 17 individual M06 current event tuples must reach the FABRIC.
            for(ix=0;ix<17;ix=ix+1) begin
                write_reg(12'h024,vectors[579+3*ix],4'hF,2'b00);
                write_reg(12'h028,vectors[580+3*ix],4'hF,2'b00);
                write_reg(12'h02C,vectors[581+3*ix],4'hF,2'b00);
                write_reg(12'h030,1,4'hF,2'b00);
                read_reg(12'h034,ix+1,2'b00);
            end
        end
    endtask

    task automatic check_fabric_event_sums;
        integer idx,neuron_id,tick_id;
        reg [11:0] base_addr;
        begin
            // All 128 current registers must equal ORIGINAL independent M06
            // oracle after raw events were individually pushed in fabric.
            for(neuron_id=0;neuron_id<32;neuron_id=neuron_id+1) begin
                idx=3+neuron_id*8;
                base_addr=12'h100+neuron_id*32;
                for(tick_id=0;tick_id<4;tick_id=tick_id+1)
                    read_reg(base_addr+16+tick_id*4,
                             vectors[idx+4+tick_id],2'b00);
            end
            $display("M08_D3D2D_REAL_RTL_128_FPGA_EVENT_BUCKET_SUMS_PASS");
        end
    endtask

    task automatic check_neural_outputs(input integer run_seq);
        integer neuron_id,idx;
        begin
            read_reg(12'h008,1,2'b00);
            read_reg(12'h018,vectors[0]+run_seq-1,2'b00);
            read_reg(12'h01C,run_seq,2'b00);
            for(neuron_id=0;neuron_id<32;neuron_id=neuron_id+1) begin
                idx=291+neuron_id*9;
                verify_neuron(neuron_id,
                    vectors[idx+0],vectors[idx+1],
                    vectors[idx+2],vectors[idx+3],
                    vectors[idx+4]);
                verify_syn(neuron_id,
                    vectors[idx+5],vectors[idx+6],
                    vectors[idx+7],vectors[idx+8]);
            end
            $display("M08_D3D2D_M06_32X4_REAL_RTL_EVENT_PARITY_PASS run=%0d",run_seq);
        end
    endtask

    initial begin
        if (!$value$plusargs("M06_EVENT_VECTORS=%s",vector_path))
            $fatal(1,"missing original M06 630-word raw event oracle path");
        $readmemh(vector_path,vectors);
        if (vectors[0] !== 32'hD2C00001 ||
            vectors[1] !== 32'd3 ||
            vectors[2] !== 32'd5 ||
            vectors[579] === 32'hxxxxxxxx ||
            vectors[629] === 32'hxxxxxxxx)
            $fatal(1,"original M06 17 raw events missing/invalid");
        repeat (10) @(negedge aclk);
        aresetn=1;
        read_reg(12'h000,32'h4D333245,2'b00);
        read_reg(12'h004,32'h00050000,2'b00);
        read_reg(12'h900,0,2'b10);
        read_reg(12'hD00,0,2'b10);
        read_reg(12'h034,0,2'b00);
        write_reg(12'h014,1,4'hF,2'b10); // no valid events/config
        write_reg(12'h024,32,4'hF,2'b10); // invalid neuron
        write_reg(12'h028,4,4'hF,2'b10); // invalid tick
        write_reg(12'h030,0,4'hF,2'b10); // PUSH must equal one
        write_reg(12'h030,1,4'h7,2'b10); // atomic full-strobe only
        write_reg(12'h030,1,4'hF,2'b00); // initial zero-current PUSH
        read_reg(12'h034,1,2'b00);
        write_reg(12'h038,1,4'hF,2'b00); // clear mailbox currents
        read_reg(12'h034,0,2'b00);
        // Positive then negative case: overflow must not partially update
        // event bucket or the event_count; signed33 exact check.
        write_reg(12'h02C,32'h7fffffff,4'hF,2'b00);
        write_reg(12'h030,1,4'hF,2'b00);
        read_reg(12'h034,1,2'b00);
        read_reg(12'h03C,32'h7fffffff,2'b00);
        write_reg(12'h02C,1,4'hF,2'b00);
        write_reg(12'h030,1,4'hF,2'b10); // signed32 overflow rejected
        read_reg(12'h034,1,2'b00);
        read_reg(12'h03C,32'h7fffffff,2'b00);
        write_reg(12'h038,1,4'h7,2'b10); // invalid clear strobe
        write_reg(12'h038,2,4'hF,2'b10); // invalid clear value
        write_reg(12'h038,1,4'hF,2'b00);
        read_reg(12'h034,0,2'b00);
        read_reg(12'h03C,0,2'b00);
        read_reg(12'h030,0,2'b10); // PUSH read forbidden
        read_reg(12'h038,0,2'b10); // CLEAR read forbidden
        write_reg(12'h034,0,4'hF,2'b10); // count is read only
        write_reg(12'h03C,0,4'hF,2'b10); // sum is read only
        write_reg(12'h020,9,4'hF,2'b10); // >8 recurrent edges
        write_reg(12'h500,32,4'hF,2'b10);
        write_reg(12'h504,32,4'hF,2'b10);
        write_reg(12'h50C,0,4'hF,2'b10);
        write_reg(12'h508,32'h0000FFFF,4'hF,2'b10);
        write_reg(12'h501,1,4'hF,2'b11); // unaligned
        write_reg(12'h900,1,4'hF,2'b11); // output read only
        write_reg(12'hD00,1,4'hF,2'b11);

        write_reg(12'h00C,vectors[0],4'hF,2'b00);
        write_reg(12'h010,vectors[1],4'hF,2'b00);
        write_reg(12'h020,vectors[2],4'hF,2'b00);
        for(n=0;n<32;n=n+1) begin
            base_word=3+n*8;
            // Unlike D3.D.2C, ZERO all 128 external currents: they will
            // be computed ONLY by fabric via 17 individual event PUSH writes.
            set_neuron(n,
                vectors[base_word+0],vectors[base_word+1],
                vectors[base_word+2],vectors[base_word+3],0,0,0,0);
        end
        for(e=0;e<5;e=e+1) begin
            edge_base=259+e*4;
            set_edge(e,vectors[edge_base+0],vectors[edge_base+1],
                       vectors[edge_base+2],vectors[edge_base+3]);
        end
        // Must fail if there are no accepted external events.
        write_reg(12'h014,1,4'hF,2'b10);
        load_raw_events();
        check_fabric_event_sums();

        for(r=1;r<=3;r=r+1) begin
            if(r==3) begin
                write_reg(12'h038,1,4'hF,2'b00);
                read_reg(12'h034,0,2'b00);
                read_reg(12'h03C,0,2'b00);
                load_raw_events();
                check_fabric_event_sums();
            end
            if(r>1) write_reg(12'h00C,vectors[0]+r-1,4'hF,2'b00);
            write_reg(12'h014,1,4'hF,2'b00);
            read_reg(12'h008,2,2'b00);
            write_reg(12'h030,1,4'hF,2'b10); // PUSH forbidden while busy
            write_reg(12'h038,1,4'hF,2'b10); // CLEAR forbidden while busy
            read_reg(12'hD00,0,2'b10);
            wait(dut.done===1'b1);
            check_neural_outputs(r);
        end
        read_reg(12'h8FC,0,2'b11);
        read_reg(12'hF00,0,2'b11);
        $display("M08_D3D2D_FULL_128_BUCKET_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_RTL_PASS");
        $finish;
    end
    initial begin
        #1500000;
        $fatal(1,"M08 D3.D.2D M06 raw event AXI RTL global timeout");
    end
endmodule
