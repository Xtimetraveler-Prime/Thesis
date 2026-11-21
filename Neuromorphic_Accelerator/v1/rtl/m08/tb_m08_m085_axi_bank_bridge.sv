// M08.5 REAL Icarus composed AXI4 + original bank, never physical DDR.
// All original input page words can be provided with +ORIGINAL_PAGE_HEX.
// No golden neural output injected; synthetic compute write is NOT SNN.
// Independent 128-bit AXI BFM keeps six 256B page memories and scores
// full read/write handshakes. A save MUST read back DDR before bank clears.
module tb_m08_m085_axi_bank_bridge;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0,owner_lease_active=1,request=0,request_save=0;
    reg [63:0] request_addr=64'h1000;
    reg [31:0] request_page=0,request_tick=0;
    wire done,error,busy,poisoned,completed_save;
    wire [2:0] bank_phase;
    wire bank_dirty,bank_valid;
    wire [31:0] bank_logical;
    wire [8:0] bank_loaded_bytes;
    wire [31:0] axi_bytes_completed_in_simulation;
    reg dispatch_req=0;
    reg [31:0] dispatch_logical=0;
    wire dispatch_accept;
    reg compute_req=0,compute_write=0,compute_done=0,compute_fault=0;
    reg [5:0] compute_word=0;
    reg [31:0] compute_wdata=0;
    reg [3:0] compute_wstrb=0;
    wire compute_ack;
    wire [31:0] compute_rdata;
    wire [0:0] m_axi_awid;
    wire [48:0] m_axi_awaddr;
    wire [7:0] m_axi_awlen;
    wire [2:0] m_axi_awsize;
    wire [1:0] m_axi_awburst;
    wire m_axi_awlock;
    wire [3:0] m_axi_awcache;
    wire [2:0] m_axi_awprot;
    wire [3:0] m_axi_awqos;
    wire m_axi_awvalid;
    reg m_axi_awready;
    wire [127:0] m_axi_wdata;
    wire [15:0] m_axi_wstrb;
    wire m_axi_wlast;
    wire m_axi_wvalid;
    reg m_axi_wready;
    reg [0:0] m_axi_bid;
    reg [1:0] m_axi_bresp;
    reg m_axi_bvalid;
    wire m_axi_bready;
    wire [0:0] m_axi_arid;
    wire [48:0] m_axi_araddr;
    wire [7:0] m_axi_arlen;
    wire [2:0] m_axi_arsize;
    wire [1:0] m_axi_arburst;
    wire m_axi_arlock;
    wire [3:0] m_axi_arcache;
    wire [2:0] m_axi_arprot;
    wire [3:0] m_axi_arqos;
    wire m_axi_arvalid;
    reg m_axi_arready;
    reg [0:0] m_axi_rid;
    reg [127:0] m_axi_rdata;
    reg [1:0] m_axi_rresp;
    reg m_axi_rlast;
    reg m_axi_rvalid;
    wire m_axi_rready;
    reg [2047:0] synthetic_ddr [0:5];
    reg [31:0] original_hex_words [0:63];
    reg [1023:0] hex_path;
    reg [31:0] original_word0,modified_word0;
    integer page_id=2,case_id=0,other_page=0;
    integer i,aw_seen=0,ar_seen=0,w_seen=0,r_seen=0,b_seen=0;
    integer aw_slot=0,ar_slot=0,w_index=0,r_index=0;
    reg write_active=0,read_active=0,b_pending=0;
    reg allow_aw=1,allow_r=1;
    reg corrupt_verify=0;
    localparam [31:0] HEADER_MAGIC=32'h4D364E46;
    m08_m085_axi_bank_bridge #(
        .WINDOW_BEGIN(64'h1000),.WINDOW_END(64'h1600),
        .GUARD_WAIT_CYCLES(4096),.AXI_STALL_CYCLES(48),
        .HOST_WAIT_CYCLES(16)
    ) dut(
        .clk(clk),.resetn(resetn),.owner_lease_active(owner_lease_active),
        .request(request),.request_save(request_save),
        .request_addr(request_addr),.request_page(request_page),
        .request_tick(request_tick),.done(done),.error(error),
        .busy(busy),.poisoned(poisoned),.completed_save(completed_save),
        .bank_phase(bank_phase),.bank_dirty(bank_dirty),
        .bank_valid(bank_valid),.bank_logical(bank_logical),
        .bank_loaded_bytes(bank_loaded_bytes),
        .axi_bytes_completed_in_simulation(axi_bytes_completed_in_simulation),
        .dispatch_req(dispatch_req),.dispatch_logical(dispatch_logical),
        .dispatch_accept(dispatch_accept),
        .compute_req(compute_req),.compute_write(compute_write),
        .compute_word(compute_word),.compute_wdata(compute_wdata),
        .compute_wstrb(compute_wstrb),.compute_ack(compute_ack),
        .compute_rdata(compute_rdata),.compute_done(compute_done),
        .compute_fault(compute_fault),
        .m_axi_awid(m_axi_awid),
        .m_axi_awaddr(m_axi_awaddr),
        .m_axi_awlen(m_axi_awlen),
        .m_axi_awsize(m_axi_awsize),
        .m_axi_awburst(m_axi_awburst),
        .m_axi_awlock(m_axi_awlock),
        .m_axi_awcache(m_axi_awcache),
        .m_axi_awprot(m_axi_awprot),
        .m_axi_awqos(m_axi_awqos),
        .m_axi_awvalid(m_axi_awvalid),
        .m_axi_awready(m_axi_awready),
        .m_axi_wdata(m_axi_wdata),
        .m_axi_wstrb(m_axi_wstrb),
        .m_axi_wlast(m_axi_wlast),
        .m_axi_wvalid(m_axi_wvalid),
        .m_axi_wready(m_axi_wready),
        .m_axi_bid(m_axi_bid),
        .m_axi_bresp(m_axi_bresp),
        .m_axi_bvalid(m_axi_bvalid),
        .m_axi_bready(m_axi_bready),
        .m_axi_arid(m_axi_arid),
        .m_axi_araddr(m_axi_araddr),
        .m_axi_arlen(m_axi_arlen),
        .m_axi_arsize(m_axi_arsize),
        .m_axi_arburst(m_axi_arburst),
        .m_axi_arlock(m_axi_arlock),
        .m_axi_arcache(m_axi_arcache),
        .m_axi_arprot(m_axi_arprot),
        .m_axi_arqos(m_axi_arqos),
        .m_axi_arvalid(m_axi_arvalid),
        .m_axi_arready(m_axi_arready),
        .m_axi_rid(m_axi_rid),
        .m_axi_rdata(m_axi_rdata),
        .m_axi_rresp(m_axi_rresp),
        .m_axi_rlast(m_axi_rlast),
        .m_axi_rvalid(m_axi_rvalid),
        .m_axi_rready(m_axi_rready)
    );
    // The 128-bit AXI memory model is clocked independently from bridge
    // internal host-port operations. READY and VALID may stall arbitrarily.
    always @(negedge clk) begin
        m_axi_awready=resetn && allow_aw;
        m_axi_arready=resetn;
        m_axi_wready=resetn && write_active;
        m_axi_bvalid=resetn && b_pending && case_id!=4;
        m_axi_bresp=(case_id==12) ? 2'b10 : 2'b00;
        m_axi_bid=1'b0;
        m_axi_rvalid=resetn && read_active && allow_r;
        m_axi_rid=1'b0;
        m_axi_rresp=(case_id==13 && r_index==0) ? 2'b10:2'b00;
        m_axi_rlast=(case_id==11 && r_index==0) ||
                    (r_index==15 && case_id!=14);
        m_axi_rdata=synthetic_ddr[ar_slot][r_index*128 +:128];
        if(case_id==3 && ar_seen>=2 && r_index==4)
            m_axi_rdata[0]=~m_axi_rdata[0];
    end
    always @(posedge clk) begin
        if(resetn) begin
            if(m_axi_awvalid && m_axi_awready) begin
                if(m_axi_awlen!==8'd15||m_axi_awsize!==3'd4 ||
                   m_axi_awburst!==2'b01||m_axi_awaddr[7:0]!==0 ||
                   m_axi_awid!==1'b0)
                    $fatal(1,"invalid AW shape");
                aw_slot=m_axi_awaddr[10:8];
                if(aw_slot>=6 || write_active)$fatal(1,"bad write slot");
                write_active=1;w_index=0;aw_seen=aw_seen+1;
            end
            if(m_axi_wvalid && m_axi_wready) begin
                if(!write_active ||w_index>=16||m_axi_wstrb!==16'hFFFF ||
                   m_axi_wlast!==(w_index==15))
                    $fatal(1,"invalid W beat index=%0d",w_index);
                synthetic_ddr[aw_slot][w_index*128 +:128]=m_axi_wdata;
                w_index=w_index+1;w_seen=w_seen+1;
                if(w_index==16)begin write_active=0;b_pending=1;end
            end
            if(m_axi_bvalid && m_axi_bready)begin b_pending=0;b_seen=b_seen+1;end
            if(m_axi_arvalid && m_axi_arready) begin
                if(m_axi_arlen!==8'd15||m_axi_arsize!==3'd4 ||
                   m_axi_arburst!==2'b01||m_axi_araddr[7:0]!==0 ||
                   m_axi_arid!==1'b0||read_active)
                    $fatal(1,"invalid AR shape");
                ar_slot=m_axi_araddr[10:8];r_index=0;
                if(ar_slot>=6)$fatal(1,"bad read slot");
                ar_seen=ar_seen+1;read_active=1;
            end
            if(m_axi_rvalid && m_axi_rready) begin
                r_index=r_index+1;r_seen=r_seen+1;
                if(r_index==16)read_active=0;
            end
        end
    end
    task start_req;
        input save;
        input integer p;
        begin
            @(negedge clk);
            request_page=p;request_tick=0;
            request_addr=64'h1000+p*256;
            request_save=save;request=1;
            @(posedge clk);#1;
            @(negedge clk);request=0;
        end
    endtask
    task await_success;
        integer k;
        begin
            for(k=0;k<3000 && !done && !poisoned;k=k+1)begin
                @(posedge clk);#1;
            end
            if(!done || poisoned)
                $fatal(1,"bridge did not finish case=%0d phase=%0d",case_id,bank_phase);
            @(posedge clk);#1;
            if(done || completed_save)$fatal(1,"completion duplicated");
        end
    endtask
    task expect_fault;
        integer k;
        begin
            for(k=0;k<3000 && !poisoned;k=k+1)begin
                @(posedge clk);#1;
            end
            if(!poisoned || done || completed_save)
                $fatal(1,"failed to quarantine case=%0d",case_id);
            repeat(5)begin
                @(posedge clk);#1;
                if(!poisoned || done || completed_save ||
                   m_axi_awvalid || m_axi_arvalid || m_axi_wvalid)
                    $fatal(1,"fault allowed stale transfers case=%0d",case_id);
            end
            $display("M08_5_REAL_BANK_AXI_NEGATIVE_PASS case=%0d",case_id);
        end
    endtask
    task compute_mutate;
        begin
            @(negedge clk);
            dispatch_logical=page_id;dispatch_req=1;
            @(posedge clk);#1;
            if(!dispatch_accept || !bank_valid)
                $fatal(1,"bank compute dispatch rejected");
            @(negedge clk);dispatch_req=0;
            @(negedge clk);
            compute_req=1;compute_write=1;compute_word=0;
            compute_wdata=modified_word0;compute_wstrb=4'hF;
            @(posedge clk);#1;
            if(!compute_ack)$fatal(1,"bank compute state write failed");
            @(negedge clk);compute_req=0;
            @(posedge clk);#1;
            @(negedge clk);compute_done=1;
            @(posedge clk);#1;
            @(negedge clk);compute_done=0;
            if(!bank_dirty || bank_phase!=3'd4)
                $fatal(1,"compute did not mark page dirty");
        end
    endtask
    initial begin
        if(!$value$plusargs("CASE=%d",case_id))case_id=0;
        if(!$value$plusargs("PAGE=%d",page_id))page_id=2;
        if(page_id<0||page_id>=6)$fatal(1,"invalid page selected");
        other_page=(page_id+1)%6;
        for(i=0;i<6;i=i+1)begin
            synthetic_ddr[i]=0;
            synthetic_ddr[i][60*32 +:32]=HEADER_MAGIC;
            synthetic_ddr[i][61*32 +:32]=i;
            synthetic_ddr[i][62*32 +:32]=(i==5 ? 2 : 6);
            synthetic_ddr[i][63*32 +:32]=0;
        end
        if($value$plusargs("ORIGINAL_PAGE_HEX=%s",hex_path))begin
            $readmemh(hex_path,original_hex_words);
            for(i=0;i<64;i=i+1)
                synthetic_ddr[page_id][i*32 +:32]=original_hex_words[i];
        end else begin
            for(i=0;i<60;i=i+1)
                synthetic_ddr[page_id][i*32 +:32]=32'hA0000000+i;
        end
        original_word0=synthetic_ddr[page_id][0 +:32];
        modified_word0=original_word0^32'h00001234;
        if(case_id==1)
            synthetic_ddr[page_id][60*32 +:32]=32'hDEADBEEF;
        repeat(3)@(negedge clk);resetn=1;
        case(case_id)
            0: begin
                start_req(0,page_id);
                await_success();
                if(bank_phase!==3'd2 || !bank_valid || bank_dirty ||
                   bank_logical!==page_id || bank_loaded_bytes!==256 ||
                   axi_bytes_completed_in_simulation!==256 ||ar_seen!=1 ||
                   r_seen!=16)
                    $fatal(1,"verified LOAD failed original page=%0d",page_id);
                compute_mutate();
                start_req(1,page_id);
                // SAVE requires real 64 dirty bank reads, a B response
                // and a second independent AXI readback before clearing.
                await_success();
                if(bank_dirty||bank_phase!==3'd2||aw_seen!=1||ar_seen!=2||
                   w_seen!=16||r_seen!=32||b_seen!=1 ||
                   synthetic_ddr[page_id][0 +:32]!==modified_word0 ||
                   axi_bytes_completed_in_simulation!==768)
                    $fatal(1,"dirty state not verified through real bank+AXI");
                start_req(0,other_page);
                await_success();
                if(bank_logical!==other_page || bank_loaded_bytes!==256)
                    $fatal(1,"clean page replacement failed");
                start_req(0,page_id);
                await_success();
                if(bank_logical!==page_id || bank_dirty)
                    $fatal(1,"original page not reloaded");
                // Public compute port reads the restored state after the
                // full dirty save / clean replacement / reload sequence.
                @(negedge clk);dispatch_logical=page_id;dispatch_req=1;
                @(posedge clk);#1;
                if(!dispatch_accept)$fatal(1,"restored dispatch failed");
                @(negedge clk);dispatch_req=0;
                @(negedge clk);compute_req=1;compute_write=0;compute_word=0;
                @(posedge clk);#1;
                if(!compute_ack || compute_rdata!==modified_word0)
                    $fatal(1,"restored actual bank state mismatch");
                @(negedge clk);compute_req=0;
                if(axi_bytes_completed_in_simulation!=1280)
                    $fatal(1,"simulated AXI transfer accounting mismatch");
                $display("M08_5_REAL_BANK_AXI_256B_LOAD_DIRTY_SAVE_EVICT_RELOAD_PASS page=%0d",page_id);
            end
            1:begin start_req(0,page_id);expect_fault();end
            2:begin start_req(0,page_id);
                    @(negedge clk);owner_lease_active=0;
                    expect_fault();end
            3:begin start_req(0,page_id);await_success();compute_mutate();
                    start_req(1,page_id);expect_fault();end
            4:begin start_req(0,page_id);await_success();compute_mutate();
                    start_req(1,page_id);expect_fault();end
            5:begin start_req(1,page_id);expect_fault();end
            6:begin start_req(0,page_id);await_success();
                    start_req(1,page_id);expect_fault();end
            7:begin start_req(0,page_id);await_success();compute_mutate();
                    start_req(0,other_page);expect_fault();end
            8:begin start_req(0,page_id);
                    // A second request before load completion is unsafe.
                    start_req(0,other_page);expect_fault();end
            9:begin start_req(0,page_id);
                    @(negedge clk);dispatch_req=1;
                    expect_fault();end
            10:begin request_page=6;request_addr=64'h1500;
                     @(negedge clk);request=1;
                     @(posedge clk);#1;
                     @(negedge clk);request=0;
                     expect_fault();end
            11:begin start_req(0,page_id);expect_fault();end
            12:begin start_req(0,page_id);await_success();compute_mutate();
                     start_req(1,page_id);expect_fault();end
            13:begin start_req(0,page_id);expect_fault();end
            14:begin start_req(0,page_id);expect_fault();end
            15:begin allow_aw=0;start_req(0,page_id);await_success();
                     compute_mutate();start_req(1,page_id);expect_fault();end
            16:begin start_req(0,page_id);await_success();compute_mutate();
                     @(negedge clk);
                     request_page=page_id;request_tick=1;
                     request_addr=64'h1000+page_id*256;
                     request_save=1;request=1;
                     @(posedge clk);#1;
                     @(negedge clk);request=0;
                     expect_fault();end
            17:begin
                     @(negedge clk);
                     request_page=page_id;request_tick=0;
                     request_addr=64'h1000+other_page*256;
                     request_save=0;request=1;
                     @(posedge clk);#1;
                     @(negedge clk);request=0;
                     expect_fault();end
            18:begin synthetic_ddr[page_id][62*32 +:32]=32'd17;
                     start_req(0,page_id);expect_fault();end
            19:begin synthetic_ddr[page_id][63*32 +:32]=32'd1;
                     start_req(0,page_id);expect_fault();end
            default:$fatal(1,"unknown test case");
        endcase
        $finish;
    end
    initial begin #2000000;$fatal(1,"bridge simulation hung case=%0d",case_id);end
endmodule
