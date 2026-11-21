// M08.5 REAL Icarus composed AXI4 + original bank, never physical DDR.
// All original input page words can be provided with +ORIGINAL_PAGE_HEX.
// No golden neural output injected; synthetic compute write is NOT SNN.
// Independent 128-bit AXI BFM keeps six 256B page memories and scores
// full read/write handshakes. A save MUST read back DDR before bank clears.
module tb_m08_m085_axi_neural_closed_loop;
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
    m08_m085_axi_bank_bridge #(
        .WINDOW_BEGIN(64'h1000),.WINDOW_END(64'h1700),
        .GUARD_WAIT_CYCLES(4096),.AXI_STALL_CYCLES(48),
        .HOST_WAIT_CYCLES(16),.ENABLE_EDGE_SLOT(1)
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
    // Existing M08.4 signed16 recurrent LIF engine, UNMODIFIED.
    // It is driven from the SAME physical 64-word bank that the AXI
    // transport must load, verify, dispatch, save and read back.
    m08_paged_m06_lif_engine neural_engine(
        .clk(clk),.resetn(resetn),.dispatch_accept(dispatch_accept),
        .compute_ack(compute_ack),.compute_rdata(compute_rdata),
        .compute_req(compute_req),.compute_write(compute_write),
        .compute_word(compute_word),.compute_wdata(compute_wdata),
        .compute_wstrb(compute_wstrb),.compute_done(compute_done),
        .compute_fault(compute_fault),
        .completed_neurons(neural_completed_neurons),
        .completed_pages(neural_completed_pages),
        .computed_synaptic_events(neural_synaptic_events)
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
    // Real 16-beat AXI plus real 64-word bank. No mock compute port.
    task start_page_request;
        input save;
        input integer slot,tick;
        begin
            @(negedge clk);
            request_page=slot;request_tick=tick;
            request_addr=64'h1000+slot*256;
            request_save=save;request=1;
            @(posedge clk);#1;
            @(negedge clk);request=0;
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
        end
    endtask
    task start_neural_dispatch;
        input integer slot;
        integer cycles;
        begin
            @(negedge clk);
            dispatch_logical=slot==6?32'hFFFFFFFF:slot;
            dispatch_req=1;
            @(posedge clk);#1;
            if(!dispatch_accept || !bank_valid || bank_dirty)
                $fatal(1,"real neural dispatch not accepted slot=%0d",slot);
            @(negedge clk);dispatch_req=0;
            for(cycles=0;cycles<5000 && !bank_dirty && !poisoned;cycles=cycles+1)begin
                @(posedge clk);#1;
            end
            if(!bank_dirty || bank_phase!==3'd4 || poisoned ||
               neural_engine.state===3'd5)
                $fatal(1,"real neural dispatch did not finish slot=%0d",slot);
        end
    endtask
    task setup_edges;
        begin
            start_page_request(0,6,0);
            wait_bank_transfer(0,6);
            start_neural_dispatch(6);
            if(!neural_engine.edge_configured ||
               neural_engine.edge_count!==4'd5 ||
               neural_completed_pages!==0 ||
               neural_engine.expected_page!==0 ||
               neural_engine.expected_tick!==0)
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
        case(case_id)
          0:begin
              setup_edges();
              for(t=0;t<4;t=t+1)begin
                  for(p=0;p<6;p=p+1)run_neural_page(t,p);
                  if(neural_engine.expected_tick!==t+1 ||
                     neural_engine.expected_page!==0)
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
                  if(neural_engine.global_spikes[n]!==expected_masks[n])
                      $fatal(1,"actual recursive spike history diverged neuron=%0d",n);
              // Each of 25 pages (1 M6EG + 24 M6NF) is read, written,
              // and read back: 25*3*256=19200 *simulated* AXI bytes.
              if(axi_bytes_completed_in_simulation!==32'd19200 ||
                 ar_seen!=50 || aw_seen!=25 ||r_seen!=800||
                 w_seen!=400 ||b_seen!=25)
                  $fatal(1,"real AXI4 bus handshake byte count drift bytes=%0d",axi_bytes_completed_in_simulation);
              $display("M08_5_REAL_LIF_AXI_BANK_M02_M03_512_PARITY_24_DISPATCHES_5_EDGES_PASS");
          end
          1,2:begin start_page_request(0,6,0);expect_fault();end
          3:begin // Edge config is a distinct slot, cannot alias a neuron.
              @(negedge clk);
              request_page=6;request_tick=0;request_addr=64'h1500;
              request_save=0;request=1;
              @(posedge clk);#1;
              @(negedge clk);request=0;
              expect_fault();
          end
          4:begin // Missing edge config must poison unchanged LIF engine.
              start_page_request(0,0,0);wait_bank_transfer(0,0);
              @(negedge clk);dispatch_logical=0;dispatch_req=1;
              @(posedge clk);#1;
              if(!dispatch_accept)$fatal(1,"missing-edge dispatch rejected before engine");
              @(negedge clk);dispatch_req=0;
              expect_fault();
              if(neural_engine.state!==3'd5)
                  $fatal(1,"missing edge setup did not fault LIF engine");
          end
          5:begin
              setup_edges();
              synthetic_ddr[0][2*32+:32]=0; // invalid positive threshold
              start_page_request(0,0,0);wait_bank_transfer(0,0);
              @(negedge clk);dispatch_logical=0;dispatch_req=1;
              @(posedge clk);#1;
              @(negedge clk);dispatch_req=0;
              expect_fault();
          end
          6:begin
              setup_edges();
              synthetic_ddr[0][63*32+:32]=2; // forbidden future tick
              start_page_request(0,0,0);expect_fault();
          end
          7:begin // fail readback when saving edge page: no false save.
              start_page_request(0,6,0);wait_bank_transfer(0,6);
              start_neural_dispatch(6);
              start_page_request(1,6,0);expect_fault();
          end
          default:$fatal(1,"unknown closed loop case=%0d",case_id);
        endcase
        $finish;
    end
    initial begin #80000000;$fatal(1,"closed-loop neural simulation timed out");end
endmodule
