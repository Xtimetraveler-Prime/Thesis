// Genuine Icarus M08.5 all-page/dispatch requests through REAL clocked
// AXI-Lite CSR work registers (no direct page/compute request TB signals).
// One ORIGINAL 64-word bank, 7 distinct synthetic DDR pages, 24 actual
// signed16 LIF dispatches and independent 512 M02/M03 output checks.
// Mock kernel-bound/route/drain & synthetic DDR: NO KV260 or kernel DMA.
module tb_m08_m085_axil_managed_neural_candidate;
    reg clk=0;always #5 clk=~clk;
    reg resetn=0;
    // Future PS 32-bit AXI4-Lite interface, driven only by TB here.
    reg [11:0] s_axi_awaddr=0,s_axi_araddr=0;
    reg [2:0] s_axi_awprot=0,s_axi_arprot=0;
    reg s_axi_awvalid=0,s_axi_wvalid=0,s_axi_bready=0;
    reg s_axi_arvalid=0,s_axi_rready=0;
    reg [31:0] s_axi_wdata=0;
    reg [3:0] s_axi_wstrb=4'hf;
    wire s_axi_awready,s_axi_wready,s_axi_bvalid,s_axi_arready,s_axi_rvalid;
    wire [1:0] s_axi_bresp,s_axi_rresp;
    wire [31:0] s_axi_rdata;
    reg csr_trusted=1,driver_bound_verified=1,control_route_verified=1;
    reg interconnect_drain_ack=1;
    wire drain_request,stop_new_requests,work_busy,work_fault;
    wire [31:0] work_completed_commands;
    reg kernel_dma_lease_valid=1,control_path_ready=1,bus_quiescent=1;
    reg lease_grant=0,lease_release=0;
    reg [63:0] lease_dma_base=64'h1000;
    reg [31:0] lease_allocation_bytes=4096,lease_generation=32'd1;
    wire lease_granted,lease_sealed,lease_poisoned;
    wire [31:0] active_generation;
    wire [63:0] admitted_begin,admitted_end;
    wire done,error,busy,poisoned,completed_save;
    wire [2:0] bank_phase;
    wire bank_dirty,bank_valid;
    wire [31:0] bank_logical;
    wire [8:0] bank_loaded_bytes;
    wire [31:0] axi_bytes_completed_in_simulation;
    wire dispatch_accept;
    wire compute_req,compute_write,compute_done,compute_fault;
    wire [5:0] compute_word;
    wire [31:0] compute_wdata;
    wire [3:0] compute_wstrb;
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
    reg [2047:0] synthetic_ddr [0:6];
    reg [31:0] original_hex_words [0:63];
    reg [1023:0] hex_path;
    reg [31:0] original_word0,modified_word0;
    integer page_id=2,case_id=0,other_page=0;
    integer i,aw_seen=0,ar_seen=0,w_seen=0,r_seen=0,b_seen=0;
    integer aw_slot=0,ar_slot=0,w_index=0,r_index=0;
    reg write_active=0,read_active=0,b_pending=0;
    reg allow_aw=1,allow_r=1;
    reg [31:0] golden[0:511];
    reg [31:0] page_source[0:63];
    reg [3:0] expected_masks[0:31];
    reg [1023:0] edge_path,golden_path,
        page0_path,page1_path,page2_path,page3_path,page4_path,page5_path;
    integer t,p,n,l,j,srcidx,wordidx,count;
    integer checked_current=0,checked_v=0,checked_spike=0,checked_syn=0;
    wire [31:0] neural_completed_neurons,neural_completed_pages,neural_synaptic_events;
    reg corrupt_verify=0;
    localparam [31:0] HEADER_MAGIC=32'h4D364E46;
    m08_m085_axil_managed_neural_candidate #(
        .GUARD_WAIT_CYCLES(4096),.AXI_STALL_CYCLES(48),
        .HOST_WAIT_CYCLES(16)
    ) dut(
        .clk(clk),.resetn(resetn),
        .s_axi_awaddr(s_axi_awaddr),.s_axi_awprot(s_axi_awprot),
        .s_axi_awvalid(s_axi_awvalid),.s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),.s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),.s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),.s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),.s_axi_arprot(s_axi_arprot),
        .s_axi_arvalid(s_axi_arvalid),.s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),.s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),.s_axi_rready(s_axi_rready),
        .csr_trusted(csr_trusted),
        .driver_bound_verified(driver_bound_verified),
        .control_route_verified(control_route_verified),
        .interconnect_drain_ack(interconnect_drain_ack),
        .drain_request(drain_request),.stop_new_requests(stop_new_requests),
        .work_busy(work_busy),.work_fault(work_fault),
        .work_completed_commands(work_completed_commands),
        .lease_granted(lease_granted),.lease_sealed(lease_sealed),
        .lease_poisoned(lease_poisoned),.active_generation(active_generation),
        .admitted_begin(admitted_begin),.admitted_end(admitted_end),
        .done(done),.error(error),
        .busy(busy),.poisoned(poisoned),.completed_save(completed_save),
        .bank_phase(bank_phase),.bank_dirty(bank_dirty),
        .bank_valid(bank_valid),.bank_logical(bank_logical),
        .bank_loaded_bytes(bank_loaded_bytes),
        .axi_bytes_completed_in_simulation(axi_bytes_completed_in_simulation),
        .dispatch_accept(dispatch_accept),
        .neural_completed_neurons(neural_completed_neurons),
        .neural_completed_pages(neural_completed_pages),
        .neural_synaptic_events(neural_synaptic_events),
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
        if(case_id==7 && ar_seen>=2 && r_index==4)
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
                if(aw_slot>=7 || write_active)$fatal(1,"bad write slot");
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
                if(ar_slot>=7)$fatal(1,"bad read slot");
                ar_seen=ar_seen+1;read_active=1;
            end
            if(m_axi_rvalid && m_axi_rready) begin
                r_index=r_index+1;r_seen=r_seen+1;
                if(r_index==16)read_active=0;
            end
        end
    end
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
    // Real 16-beat AXI plus real 64-word bank. No mock compute port.
    task write_axil;
        input [11:0] addr;
        input [31:0] data;
        integer cycles;
        begin
            @(negedge clk);
            s_axi_awaddr=addr;s_axi_awvalid=1;
            s_axi_wdata=data;s_axi_wstrb=4'hf;s_axi_wvalid=1;
            #1;
            if(!s_axi_awready || !s_axi_wready)
                $fatal(1,"32-bit AXI-Lite AW/W not ready");
            @(posedge clk);#1;
            @(negedge clk);s_axi_awvalid=0;s_axi_wvalid=0;
            for(cycles=0;cycles<16&&!s_axi_bvalid;cycles=cycles+1)
                begin @(posedge clk);#1;end
            if(!s_axi_bvalid || s_axi_bresp!==2'b00)
                $fatal(1,"trusted CSR write failed addr=%h",addr);
            @(negedge clk);s_axi_bready=1;
            @(posedge clk);#1;
            @(negedge clk);s_axi_bready=0;
            #1;
            if(s_axi_bvalid)$fatal(1,"AXI-Lite duplicated write response");
        end
    endtask
    task grant_dma_lease;
        begin
            // Managed register extension is ABI 1.1; a legacy v1.0
            // control-only image must never be mistaken for this design.
            @(negedge clk);s_axi_araddr=12'h004;s_axi_arvalid=1;
            #1;
            if(!s_axi_arready)$fatal(1,"ABI version AR not accepted");
            @(posedge clk);#1;
            @(negedge clk);s_axi_arvalid=0;
            #1;
            if(!s_axi_rvalid || s_axi_rresp!==2'b00 ||
               s_axi_rdata!==32'h00010001)
                $fatal(1,"managed-work ABI version must be 1.1");
            s_axi_rready=1;
            @(posedge clk);#1;
            @(negedge clk);s_axi_rready=0;
            write_axil(12'h010,32'h1000);
            write_axil(12'h014,32'd0);
            write_axil(12'h018,32'd4096);
            write_axil(12'h01c,32'd1);
            write_axil(12'h020,32'd1);
            repeat(3)begin @(posedge clk);#1;end
            if(!lease_granted || lease_poisoned || !dut.lease_active ||
               admitted_begin!==64'h1000 || admitted_end!==64'h1700 ||
               active_generation!==32'd1)
                $fatal(1,"AXI-Lite trusted CSR 7-slot lease not granted");
            $display("M08_5_AXIL_MANAGED_CSR_7_SLOT_NEURAL_GRANT_PASS");
        end
    endtask
    task read_work_status;
        input [31:0] expected_count;
        reg [31:0] snap;
        integer cycles;
        begin
            for(cycles=0;cycles<10000 && work_busy && !poisoned;cycles=cycles+1)begin
                @(posedge clk);#1;
            end
            if(work_busy || work_fault || poisoned || !lease_granted ||
               work_completed_commands!==expected_count)
                $fatal(1,"MMIO work completion timeout/counter=%0d expected=%0d",
                       work_completed_commands,expected_count);
            @(negedge clk);s_axi_araddr=12'h030;s_axi_arvalid=1;
            #1;
            if(!s_axi_arready)$fatal(1,"work status AR backpressured");
            @(posedge clk);#1;
            @(negedge clk);s_axi_arvalid=0;
            for(cycles=0;cycles<12 && !s_axi_rvalid;cycles=cycles+1)begin
                @(posedge clk);#1;
            end
            snap=s_axi_rdata;
            if(!s_axi_rvalid || s_axi_rresp!==2'b00 ||
               !snap[1] || snap[0] || snap[2])
                $fatal(1,"MMIO work STATUS incorrect status=%h",snap);
            @(negedge clk);s_axi_rready=1;
            @(posedge clk);#1;
            @(negedge clk);s_axi_rready=0;
            if(s_axi_rvalid)$fatal(1,"double MMIO RVALID work status");
        end
    endtask
    task start_page_request;
        input save;
        input integer slot,tick;
        begin
            write_axil(12'h024,slot);
            write_axil(12'h028,tick);
            write_axil(12'h02c,save ? 32'd3 : 32'd1);
            if(!work_busy && !done)$fatal(1,"MMIO page command not dispatched");
        end
    endtask
    task wait_bank_transfer;
        input save;
        input integer slot;
        integer cycles;
        reg [31:0] semantic;
        begin
            semantic=slot==6?32'hFFFFFFFF:slot;
            for(cycles=0;cycles<3500&&!done&&!poisoned;cycles=cycles+1)begin
                @(posedge clk);#1;
            end
            if(!done || poisoned || completed_save!==save ||
               bank_phase!==3'd2 || !bank_valid || bank_dirty ||
               bank_logical!==semantic || bank_loaded_bytes!==9'd256)
                $fatal(1,"bank/AXI transfer failed slot=%0d save=%0d phase=%0d",
                       slot,save,bank_phase);
            @(posedge clk);#1;
            if(done || completed_save)
                $fatal(1,"double completion slot=%0d",slot);
            read_work_status(work_completed_commands);
        end
    endtask
    task start_neural_dispatch;
        input integer slot;
        integer cycles;
        reg [31:0] old_count;
        begin
            old_count=work_completed_commands;
            write_axil(12'h024,slot);
            write_axil(12'h028,32'd0);
            write_axil(12'h02c,32'd2);
            for(cycles=0;cycles<5000 && work_completed_commands==old_count &&
                !poisoned;cycles=cycles+1)begin @(posedge clk);#1;end
            if(work_completed_commands!=old_count+1 || work_busy ||
               !bank_dirty || bank_phase!==3'd4 || poisoned ||
               dut.neural.neural_engine.state===3'd5)
                $fatal(1,"real LIF MMIO dispatch failed slot=%0d count=%0d",
                       slot,work_completed_commands);
            read_work_status(old_count+1);
        end
    endtask
    task setup_edges;
        begin
            start_page_request(0,6,0);
            wait_bank_transfer(0,6);
            start_neural_dispatch(6);
            if(!dut.neural.neural_engine.edge_configured ||
               dut.neural.neural_engine.edge_count!==4'd5 ||
               neural_completed_pages!==0 ||
               dut.neural.neural_engine.expected_page!==0 ||
               dut.neural.neural_engine.expected_tick!==0)
                $fatal(1,"five real recurrent edges not configured");
            start_page_request(1,6,0);
            wait_bank_transfer(1,6);
            if(synthetic_ddr[6][60*32+:32]!==32'h4D364547 ||
               synthetic_ddr[6][61*32+:32]!==32'hFFFFFFFF ||
               synthetic_ddr[6][62*32+:32]!==32'd5)
                $fatal(1,"original edge config lost from separate backing slot");
            $display("M08_5_M6EG_SEVENTH_SLOT_FIVE_EDGE_BOOTSTRAP_PASS");
        end
    endtask
    task run_neural_page;
        input integer tick,slot;
        integer localidx,idx,globalidx,oracleidx,base,neuroncount;
        reg [31:0] actual_mask;
        begin
            synthetic_ddr[slot][63*32+:32]=tick; // source owner advances tick
            start_page_request(0,slot,tick);
            wait_bank_transfer(0,slot);
            start_neural_dispatch(slot);
            start_page_request(1,slot,tick);
            wait_bank_transfer(1,slot);
            neuroncount=(slot==5)?2:6;
            for(localidx=0;localidx<neuroncount;localidx=localidx+1)begin
                globalidx=slot*6+localidx;
                oracleidx=(tick*32+globalidx)*4;
                base=localidx*10;
                if(synthetic_ddr[slot][(base+4+tick)*32+:32] !== golden[oracleidx])
                    $fatal(1,"original input-current mismatch tick=%0d neuron=%0d",
                           tick,globalidx);
                checked_current=checked_current+1;
                if(synthetic_ddr[slot][base*32+:32] !== golden[oracleidx+1])
                    $fatal(1,"original LIF membrane mismatch tick=%0d neuron=%0d",
                           tick,globalidx);
                checked_v=checked_v+1;
                actual_mask=expected_masks[globalidx] |
                            ((golden[oracleidx+2]&1)<<tick);
                if(synthetic_ddr[slot][(base+8)*32+:32] !== actual_mask)
                    $fatal(1,"real spike mask mismatch tick=%0d neuron=%0d",
                           tick,globalidx);
                expected_masks[globalidx]=actual_mask[3:0];
                checked_spike=checked_spike+1;
                if(synthetic_ddr[slot][(base+9)*32+:32] !== golden[oracleidx+3])
                    $fatal(1,"real synaptic current mismatch tick=%0d neuron=%0d",
                           tick,globalidx);
                checked_syn=checked_syn+1;
            end
            if(neural_completed_pages!==(tick*6+slot+1) ||
               neural_completed_neurons!==(tick*32+slot*6+neuroncount))
                $fatal(1,"real neural engine's page/neuron count drift tick=%0d page=%0d",
                       tick,slot);
            $display("M08_5_AXIDDR_REAL_SIGNED16_PAGE_PASS tick=%0d slot=%0d",tick,slot);
        end
    endtask
    task load_page_sources;
        integer slot,index;
        begin
            if(!$value$plusargs("edge=%s",edge_path) ||
               !$value$plusargs("golden=%s",golden_path) ||
               !$value$plusargs("page0=%s",page0_path) ||
               !$value$plusargs("page1=%s",page1_path) ||
               !$value$plusargs("page2=%s",page2_path) ||
               !$value$plusargs("page3=%s",page3_path) ||
               !$value$plusargs("page4=%s",page4_path) ||
               !$value$plusargs("page5=%s",page5_path))
                $fatal(1,"all six original M02/M03 neural pages, edge config and oracle required");
            $readmemh(golden_path,golden);
            for(slot=0;slot<7;slot=slot+1)begin
                case(slot)
                  0:$readmemh(page0_path,page_source);
                  1:$readmemh(page1_path,page_source);
                  2:$readmemh(page2_path,page_source);
                  3:$readmemh(page3_path,page_source);
                  4:$readmemh(page4_path,page_source);
                  5:$readmemh(page5_path,page_source);
                  6:$readmemh(edge_path,page_source);
                endcase
                synthetic_ddr[slot]=2048'd0;
                for(index=0;index<64;index=index+1)
                    synthetic_ddr[slot][index*32+:32]=page_source[index];
            end
        end
    endtask
    initial begin
        if(!$value$plusargs("CASE=%d",case_id))case_id=0;
        load_page_sources();
        for(i=0;i<32;i=i+1)expected_masks[i]=0;
        // Failure cases intentionally mutate source-only input snapshots,
        // NEVER the owner immutable physical evidence or oracle.
        if(case_id==1) synthetic_ddr[6][60*32+:32]=32'h4D364E46;
        if(case_id==2) synthetic_ddr[6][63*32+:32]=1;
        repeat(3)@(negedge clk);resetn=1;
        // Testbench pretends to be a trusted driver; NEVER provenance.
        grant_dma_lease();
        if(case_id!=0)$fatal(1,"AXI-Lite integrated test only CASE=0");
        begin
              setup_edges();
              for(t=0;t<4;t=t+1)begin
                  for(p=0;p<6;p=p+1)run_neural_page(t,p);
                  if(dut.neural.neural_engine.expected_tick!==t+1 ||
                     dut.neural.neural_engine.expected_page!==0)
                      $fatal(1,"mixed-epoch neural step tick=%0d",t);
                  $display("M08_5_AXIDDR_TICK_BARRIER_PASS tick=%0d",t);
              end
              if(checked_current!=128 || checked_v!=128 ||
                 checked_spike!=128 || checked_syn!=128 ||
                 neural_completed_neurons!==32'd128 ||
                 neural_completed_pages!==32'd24 ||
                 neural_synaptic_events===0)
                  $fatal(1,"512 original numerical checks not reproduced");
              for(n=0;n<32;n=n+1)
                  if(dut.neural.neural_engine.global_spikes[n]!==expected_masks[n])
                      $fatal(1,"actual recursive spike history diverged neuron=%0d",n);
              // Each of 25 pages (1 M6EG + 24 M6NF) is read, written,
              // and read back: 25*3*256=19200 *simulated* AXI bytes.
              if(axi_bytes_completed_in_simulation!==32'd19200 ||
                 ar_seen!=50 || aw_seen!=25 ||r_seen!=800||
                 w_seen!=400 ||b_seen!=25)
                  $fatal(1,"real AXI4 bus handshake byte count drift bytes=%0d",axi_bytes_completed_in_simulation);
              $display("M08_5_REAL_LIF_AXI_BANK_M02_M03_512_PARITY_24_DISPATCHES_5_EDGES_PASS");
              if(work_completed_commands!==32'd75 || work_busy || work_fault)
                  $fatal(1,"expected 25 load+dispatch+save MMIO work triplets");
              write_axil(12'h020,32'd2);
              @(negedge clk);interconnect_drain_ack=0;
              @(posedge clk);#1;
              @(negedge clk);interconnect_drain_ack=1;
              repeat(4)begin @(posedge clk);#1;end
              if(!lease_sealed || lease_poisoned || admitted_end!=0)
                  $fatal(1,"synthetic drain did not seal final owner lease");
              $display("M08_5_AXIL_MANAGED_75_COMMANDS_512_ORACLE_PASS");
          end

        $finish;
    end
    initial begin #80000000;$fatal(1,"closed-loop neural simulation timed out");end
endmodule
